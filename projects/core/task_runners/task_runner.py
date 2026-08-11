from typing import Type
from loguru import logger
from hazut_hakol.core.classes.trigger import TriggerStatus
from hazut_hakol.core.classes.trigger.trigger_error_info_object import TriggerErrorInfo
from hazut_hakol.core.entrex_base_errors import EntrexDataError
from hazut_hakol.core.utils import Environment
from hazut_hakol.utils.retry.retry import _retry
from .prod_runner import ProdRunner
from ..etsc_interface import ETS_interface
from ..on_demand_mutation_mechanism.taskor_mutation import TaskorMutationBaseModel, TaskorMutationMinimalSupportMixin, TaskorMutationMaximalSupportMixin

SIMPLE_RETRY_BACKOFF = 10.0


class TaskRunner(ProdRunner):
    def __init__(self, mode: Environment, taskor_class: Type[ETS_interface],
                 seconds_sleep_when_no_work: int = 5, enable_elastic: bool = False,
                 enable_s3_limiter: bool = False, enable_nfs_limiter: bool = False,
                 data_storages_percentage_limit: bool = False,
                 enable_simple_retry: bool = False):
        super(TaskRunner, self).__init__(
            mode=mode,
            taskor_class=taskor_class,
            seconds_sleep_when_no_work=seconds_sleep_when_no_work,
            enable_elastic=enable_elastic,
            enable_s3_limiter=enable_s3_limiter,
            enable_nfs_limiter=enable_nfs_limiter,
            data_storages_percentage_limit=data_storages_percentage_limit,
            enable_simple_retry=enable_simple_retry
        )

    def _get_mutation(self, mutation_hash: str) -> TaskorMutationBaseModel:
        mutation = None
        if self._trigger.get_on_demand_mutation_hash() is not None and issubclass(self._taskor_class, TaskorMutationMaximalSupportMixin):
            mutation_base_model_class = self._taskor_class.get_taskor_mutation_base_model()

        logger.info(f"Fetching mutation {mutation_hash}")
        mutation_raw = self._knowledge_center.mutation_db_interface.get_taskor_mutation(
            mutation_hash=mutation_hash,
            taskor_name=self._taskor_class.get_taskor_name()
        )
        if mutation_raw is not None:
            mutation = mutation_base_model_class(**mutation_raw)
        return mutation

    def _set_taskor_object(self) -> None:
        mutation_hash = self._trigger.get_on_demand_mutation_hash()
        sweep_id = self._trigger.get_clean_trigger_id()
        if issubclass(self._taskor_class, TaskorMutationMinimalSupportMixin):
            self._taskor_object = self._taskor_class(
                trigger_id=self._trigger.trigger_id,
                tmp_storage=self._trigger_temp_storage,
                mutation_hash=mutation_hash,
                sweep_id=sweep_id,
                mutation=self._get_mutation(mutation_hash)
            )
        else:
            super()._set_taskor_object()

    def _setup_taskor(self):
        self._taskor_class.setup_taskor(mode=self._mode)

    def _trigger_pipeline_handling(self):
        def _taskor_pipeline() -> None:
            with self._trigger.running_phase("extract"):
                logger.info("Starting _extract()")
                self._taskor_object.extract()

            with self._trigger.running_phase("transform"):
                logger.info("Starting _transform()")
                self._taskor_object.transform()

            with self._trigger.running_phase("save"):
                logger.info("Starting _save()")
                self._taskor_object.save()

        try:
            _retry(
                _taskor_pipeline,
                max_attempts=self._max_retry_attempts,
                backoff=SIMPLE_RETRY_BACKOFF,
                allowed_exceptions=(EntrexDataError, Exception),
                step_name="Taskor pipeline"
            )
            self._trigger.status = TriggerStatus.COMPLETED
        except EntrexDataError as e:
            self._trigger.status = TriggerStatus.FAILED
            self._trigger.fail_error_message = TriggerErrorInfo(exception_object=e)
            logger.error(self._trigger.fail_error_message.to_json())
        except Exception as e:
            self._trigger.status = TriggerStatus.FAILED
            self._trigger.fail_error_message = TriggerErrorInfo(exception_object=e)
            logger.error(self._trigger.fail_error_message.to_json())

        self._knowledge_center.trigger_db_interface.update_triggers(triggers=[self._trigger])