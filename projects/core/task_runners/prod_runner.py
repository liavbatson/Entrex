import datetime
import shutil
import signal
import socket
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from time import sleep
from typing import Type, Union

from loguru import logger

from hazut_hakol.apio.data_storage.data_storage_nfs import STORAGE_ROOT_PATH
from hazut_hakol.apio.knowledge_center.knowledge_center import KnowledgeCenter
from hazut_hakol.core.classes.trigger import TriggerStatus, Trigger
from hazut_hakol.core.utils import Environment
from hazut_hakol.logger.elastic_logger import ElasticLogger
from ..etsc_interface import ETS_interface
from ..etsc_interface.ETS_interface import BouncerInterface

SIMPLE_RETRY_BACKOFF = 10.0
SIMPLE_MAX_ATTEMPTS = 3


class ProdRunner(ABC):
    _trigger: Trigger
    _trigger_temp_storage: Path
    _taskor_object: Union[ETS_interface, BouncerInterface]

    def __init__(self, mode: Environment, taskor_class: Union[Type[Environment], Type[BouncerInterface]],
                 seconds_sleep_when_no_work: int = 5, enable_elastic: bool = False,
                 enable_s3_limiter: bool = False, enable_nfs_limiter: bool = False,
                 data_storages_percentage_limit: int = 95, enable_simple_retry: bool = False):
        self._mode = mode
        self._taskor_class = taskor_class
        self._knowledge_center = KnowledgeCenter(mode=mode)
        self._seconds_sleep_when_no_work = seconds_sleep_when_no_work
        self._data_storages_percentage_limit = float(data_storages_percentage_limit)
        self._root_temp_storage = Path("./tmp")
        self._enable_s3_limiter = enable_s3_limiter
        self._enable_nfs_limiter = enable_nfs_limiter
        self._max_retry_attempts = SIMPLE_MAX_ATTEMPTS if enable_simple_retry else 1

        self._trigger: Trigger
        if enable_elastic:
            self._elastic_logger = ElasticLogger(mode=self._mode, taskor_name=self._taskor_class.get_taskor_name())

        signal.signal(signal.SIGINT, self._handle_sigterm)
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    @abstractmethod
    def _setup_taskor(self):
        pass

    @abstractmethod
    def _trigger_pipeline_handling(self):
        pass

    def run(self, *, is_run_single_iteration: bool = False):
        logger.info("Algo Runner Running ...")
        logger.info("Running _setup_taskor()")
        self._setup_taskor()

        keep_alive_thread = threading.Thread(target=self._heartbeat, daemon=True)
        keep_alive_thread.start()

        while True:
            self._trigger = None
            self._trigger_temp_storage = None
            self._taskor_object = None

            if self._enable_nfs_limiter:
                total, used, free = shutil.disk_usage(STORAGE_ROOT_PATH[self._mode])
                used_percentage = (used / total) * 100

                if used_percentage >= self._data_storages_percentage_limit:
                    logger.warning(f"NFS is {used_percentage}% full, locking it when > {self._data_storages_percentage_limit}")
                    logger.debug(f"NFS locked! Sleeping for {self._seconds_sleep_when_no_work} seconds.")
                    sleep(self._seconds_sleep_when_no_work)
                    continue

            logger.debug(f"Starting _find_trigger()")
            self._find_trigger()
            if self._trigger is None:
                logger.debug(f"No triggers found. Going to sleep for {self._seconds_sleep_when_no_work} seconds.")
                sleep(self._seconds_sleep_when_no_work)
                continue

            if self._elastic_logger:
                self._elastic_logger.set_working_trigger(self._trigger.trigger_id)

            self._trigger_temp_storage = self._root_temp_storage / Path(f"{self._trigger.trigger_id}")
            self._set_taskor_object()

            self._trigger_pipeline_handling()

            self._cleaning()
            if self._elastic_logger:
                self._elastic_logger.send_bulk()
                self._elastic_logger.clear_working_trigger()

            if is_run_single_iteration:
                break

    def _set_taskor_object(self) -> None:
        self._taskor_object = self._taskor_class(
            trigger_id=self._trigger.trigger_id,
            tmp_storage=self._trigger_temp_storage
        )

    def _heartbeat(self) -> None:
        while True:
            pod_name = socket.gethostname()
            self._knowledge_center.taskor_heartbeat_db_interface.update_heartbeat(
                taskor_name=self._taskor_class.get_taskor_name(),
                pod_name=pod_name,
                heartbeat_time=datetime.datetime.now(datetime.timezone.utc)
            )
            sleep(60)

    def _find_trigger(self):
        self._trigger = self._knowledge_center.trigger_db_interface.get_pending_trigger_and_acknowledge(
            taskor_name=self._taskor_class.get_taskor_name()
        )

    def _handle_sigterm(self, signum, frame):
        logger.info(f"Received signal! {signum}")
        if self._trigger is not None:
            self._trigger.status = TriggerStatus.PENDING
            self._knowledge_center.trigger_db_interface.update_triggers(
                triggers=[self._trigger]
            )
            self._trigger = None
        sys.exit(0)

    def _cleaning(self):
        if self._trigger_temp_storage:
            _remove_temp_folder(self._trigger_temp_storage)


def _remove_temp_folder(folder_path):
    try:
        logger.info(f"Trying to remove temp folder '{folder_path}'")
        shutil.rmtree(folder_path)
        logger.info(f"Folder removed successfully.")
    except FileNotFoundError:
        logger.info(f"Ignoring non-existent temp folder '{folder_path}'")
    except PermissionError:
        logger.info(f"Permission denied to remove temp folder '{folder_path}'")
    except Exception:
        logger.exception("Failed removing temp folder")
        