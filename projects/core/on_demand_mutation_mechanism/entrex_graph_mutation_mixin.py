from typing import List, Dict, Type, Any

from loguru import logger
from pydantic import BaseModel

from ..entrex_graph_system.entrex_graph_node import EntrexGraphNode
from ..on_demand_mutation_mechanism.taskor_mutation import TaskorMutationMinmalSupportMixin, TaskorMutationMaximalSupportMixin


class EntrexGraphMutationMixin:
    _is_project_support_mutated_runs: Dict[str, bool] = {}
    _project_mutation_sub_models: Dict[str, Dict[str, BaseModel]] = {}

    _project_to_taskors: Dict[str, List[str]]
    _entrex_taskors: Dict[str, Type[EntrexGraphNode]]

    def _setup_mutation_mixin(self):
        logger.debug("EntrexGraph mutation mixin initializing.")
        for project_name, taskor_names in self._project_to_taskors.items():
            minimal_support_status: List[str] = []
            maximal_support_base_models: Dict[str, BaseModel] = {}

            for taskor_name in taskor_names:
                taskor_class: Type[EntrexGraphNode]
                taskor_class = self._entrex_taskors[taskor_name]
                is_minimal_support = issubclass(taskor_class, TaskorMutationMinmalSupportMixin)
                is_maximal_support = issubclass(taskor_class, TaskorMutationMaximalSupportMixin)

                if is_minimal_support:
                    minimal_support_status.append(taskor_name)
                if is_maximal_support:
                    taskor_class: TaskorMutationMaximalSupportMixin
                    maximal_support_base_models[taskor_name] = taskor_class.get_taskor_mutation_base_model().model_json_schema()

            if len(minimal_support_status) != len(self._project_to_taskors):
                self._is_project_support_mutated_runs[project_name] = False
                self._project_mutation_sub_models[project_name] = maximal_support_base_models
            else:
                self._is_project_support_mutated_runs[project_name] = True
                self._project_mutation_sub_models[project_name] = maximal_support_base_models
        logger.debug(f"Projects supporting mutated runs: {list(self._project_mutation_sub_models.keys())}")