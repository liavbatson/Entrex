from typing import Type
from loguru import logger
from hazut_hakol.core.classes.trigger import TriggerStatus
from hazut_hakol.core.classes.trigger.trigger_error_info_object import TriggerErrorInfo
from hazut_hakol.core.utils import Environment
from hazut_hakol.utils.retry.retry import _retry
from .prod_runner import ProdRunner
from ..entrex_context.entrex_context import EntrexProjectContext
from ..entrex_graph_system.entrex_graph import EntrexGraph
from ..etsc_interface.ETS_interface import BouncerInterface, BouncerError

SIMPLE_RETRY_BACKOFF = 2


class BouncerRunner(ProdRunner):
    def __init__(self, mode: Environment, bouncer_class: Type[BouncerInterface],
                 seconds_sleep_when_no_work: int = 5, enable_elastic: bool = False,
                 enable_s3_limiter: bool = False, enable_nfs_limiter: bool = False,
                 data_storages_percentage_limit: int = 95,
                 enable_simple_retry: bool = False, bounced_trigger_delete: bool = False):
        super(BouncerRunner, self).__init__(
            mode=mode,
            taskor_class=bouncer_class,
            seconds_sleep_when_no_work=seconds_sleep_when_no_work,
            enable_elastic=enable_elastic,
            enable_s3_limiter=enable_s3_limiter,
            enable_nfs_limiter=enable_nfs_limiter,
            data_storages_percentage_limit=data_storages_percentage_limit,
            enable_simple_retry=enable_simple_retry
        )
        self._entrex_project_context = EntrexProjectContext(mode=self._mode)
        self._entrex_graph = EntrexGraph(entrex_project_context=self._entrex_project_context)

        self._bounced_trigger_delete = bounced_trigger_delete
        self._bouncer_successors = self._entrex_graph.get_all_successors(self._taskor_class.get_taskor_name())

        self._bounce_trigger: bool

    def _setup_taskor(self):
        self._taskor_class.setup_bounce()

    def _trigger_pipeline_handling(self):
        def _bouncer_pipeline() -> None:
            with self._trigger.running_phase("extract"):
                logger.info(f"Starting _extract()")
                self._taskor_object.extract()

            with self._trigger.running_phase("bounce"):
                logger.info(f"Starting _bounce()")
                self._taskor_object.bounce()

        try:
            _retry(
                _bouncer_pipeline,
                max_attempts=self._max_retry_attempts,
                backoff=SIMPLE_RETRY_BACKOFF,
                allowed_exceptions=(BouncerError, Exception),
                step_name="Taskor pipeline"
            )
            self._trigger.status = TriggerStatus.COMPLETED

        except BouncerError as e:
            if self._bounced_trigger_delete:
                successors_triggers_to_update = self._knowledge_center.trigger_db_interface.find_triggers_for_id(
                    self._trigger.trigger_id, self._bouncer_successors
                )
                successors_triggers_to_update = successors_triggers_to_update + [self._trigger]
                self._knowledge_center.trigger_db_interface.delete_triggers(triggers=successors_triggers_to_update)
                logger.info(f"Deleting trigger and trigger successors")
            else:
                self._trigger.status = TriggerStatus.FAILED
                self._trigger.fail_error_message = TriggerErrorInfo(exception_object=e)
                logger.error(self._trigger.fail_error_message.to_json())
        except Exception as e:
            self._trigger.status = TriggerStatus.FAILED
            self._trigger.fail_error_message = TriggerErrorInfo(exception_object=e)
            logger.error(self._trigger.fail_error_message.to_json())

        self._knowledge_center.trigger_db_interface.update_triggers(triggers=[self._trigger])
