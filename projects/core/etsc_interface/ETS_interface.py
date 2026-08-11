from abc import abstractmethod, ABC
from pathlib import Path

from hazut_hakol.core.entrex_base_errors import EntrexDataError
from hazut_hakol.core.utils import Environment
from projects.core.entrex_graph_system.entrex_graph_node import EntrexGraphNode
from projects.core.on_demand_mutation_mechanism.taskor_mutation import TaskorMutationBaseModel
from projects.core.on_demand_mutation_mechanism.trigger_mutation_mixin import TriggerMutationMixin


class ETS_Interface(EntrexGraphNode, ABC):
    def __init__(self, trigger_id: str, tmp_storage: Path, **kwargs):
        allowed_kwargs = {"mutation_hash", "sweep_id", "mutation"}
        if kwargs and set(kwargs) - allowed_kwargs:
            raise ValueError(f"Unexpected keys: {set(kwargs) - allowed_kwargs}")
        self._trigger_id = trigger_id
        self._tmp_storage = tmp_storage
        self._tmp_storage.mkdir(parents=True, exist_ok=True)

        trigger_mutation = TriggerMutationMixin(trigger_id)
        self._mutation_hash: str = kwargs.get("mutation_hash") or trigger_mutation.get_on_demand_mutation_hash()
        self._sweep_id: str = kwargs.get("sweep_id") or trigger_mutation.get_clean_trigger_id() or self._trigger_id
        self._mutation: TaskorMutationBaseModel = kwargs.get("mutation")

    @abstractmethod
    def extract(self):
        ...

    @classmethod
    def setup_taskor(cls, mode: Environment):
        cls._mode = mode

    @abstractmethod
    def transform(self, **kwargs):
        ...

    @abstractmethod
    def save(self):
        ...


class ETS_ConsumerInterface:
    def __init__(self, mode: Environment):
        self._mode = mode


class BouncerError(EntrexDataError):
    pass


class BouncerInterface(EntrexGraphNode, ABC):
    def __init__(self, mode: Environment, trigger_id: str, tmp_storage: Path):
        self._mode = mode
        self._trigger_id = trigger_id
        self._tmp_storage = tmp_storage
        self._tmp_storage.mkdir(parents=True, exist_ok=True)

        self.should_bounce = False

    @abstractmethod
    def extract(self):
        pass

    @classmethod
    def setup_bounce(cls):
        ...

    @abstractmethod
    def bounce(self, **kwargs):
        pass
