from collections import defaultdict
from typing import List, Dict
from loguru import logger

from .union_find import UnionFind
from ..entrex_context.entrex_context import EntrexProjectContext
from ..on_demand_mutation_mechanism.entrex_graph_mutation_mixin import EntrexGraphMutationMixin


class EntrexGraph(EntrexGraphMutationMixin):
    def __init__(self, entrex_project_context: EntrexProjectContext):
        self._entrex_taskors = entrex_project_context.taskors
        self._entrex_projects = entrex_project_context.projects
        self._taskor_to_predecessors: Dict[str, List[str]] = {}
        self._taskor_to_successors: Dict[str, List[str]] = {}
        self._taskor_to_all_predecessors: Dict[str, List[str]] = {}
        self._taskor_to_all_successors: Dict[str, List[str]] = defaultdict(list)

        self._project_to_taskors: Dict[str, List[str]] = {}
        self._taskor_to_connected_taskors: Dict[str, List[str]] = {}
        self._connected_components: List[List[str]] = []

        self._uf = UnionFind(list(self._entrex_taskors.keys()))
        self._build_graph()

        self._taskor_to_immediate_predecessors: Dict[str, List[str]] = {}
        self._build_immediate_predecessors()
        logger.info(f"Working on Entrex Graph {self.get_graph_json()}")
        self._setup_mutation_mixin()

    def _build_graph(self):
        for taskor_name, taskor_cls in self._entrex_taskors.items():
            self._taskor_to_predecessors[taskor_name] = []
            self._taskor_to_successors[taskor_name] = []

        for taskor_name, taskor_cls in self._entrex_taskors.items():
            required = taskor_cls.get_predecessors()
            for req in required:
                self._taskor_to_predecessors[taskor_name].append(req)
                self._taskor_to_successors[req].append(taskor_name)
                self._uf.union(taskor_name, req)

        components = self._uf.get_connected_components()
        self._connected_components = list(components.values())

        for taskor in self._entrex_taskors:
            self._taskor_to_connected_taskors[taskor] = self._uf.get_component(taskor)

        self._populate_all_predecessors()
        self._populate_all_successors_by_inverting_predecessors()

        for project_name, project_information in self._entrex_projects.items():
            self._project_to_taskors[project_name] = self._taskor_to_all_predecessors[project_information.ending_taskor] + [project_information.ending_taskor]

    def _populate_all_predecessors(self):
        for node in self._taskor_to_predecessors:
            self._taskor_to_all_predecessors[node] = set()
            self._get_all_predecessors_recursive(node, self._taskor_to_all_predecessors[node])
            self._taskor_to_all_predecessors[node] = list(self._taskor_to_predecessors[node])

    def _populate_all_successors_by_inverting_predecessors(self):
        for task, predecessors in self._taskor_to_all_predecessors.items():
            for predecessor in predecessors:
                self._taskor_to_all_successors[predecessor].append(task)

    def _get_all_predecessors_recursive(self, node, visited):
        for predecessor in self._taskor_to_predecessors[node]:
            if predecessor not in visited:
                visited.add(predecessor)
                self._get_all_predecessors_recursive(predecessor, visited)

    def find_next_in_order(self, taskor_name: str) -> List[str]:
        return self._taskor_to_successors[taskor_name]

    def previous_in_order_required(self, taskor_name: str) -> List[str]:
        return self._taskor_to_predecessors[taskor_name]

    def get_all_predecessors(self, taskor_name: str) -> List[str]:
        return self._taskor_to_all_predecessors[taskor_name]

    def get_all_successors(self, taskor_name: str) -> List[str]:
        return self._taskor_to_all_successors[taskor_name]

    def get_all_taskors_of_project(self, project_name: str) -> List[str]:
        return self._project_to_taskors[project_name]

    def get_connected_taskor(self, taskor_name: str) -> List[str]:
        return self._taskor_to_connected_taskors.get(taskor_name, [])

    def get_all_connected_components(self) -> List[List[str]]:
        return self._connected_components

    def is_taskor_leaf(self, taskor: str) -> bool:
        return 0 == len(self._taskor_to_predecessors[taskor])

    def get_project_graph_json(self, project_name: str) -> dict:
        project_taskors = self.get_all_taskors_of_project(project_name)
        project_predecessors = [
            {"name": taskor, "dependsOn": predecessors}
            for taskor, predecessors in self._taskor_to_immediate_predecessors.items() if taskor in project_taskors
        ]
        return {"tasks": project_predecessors}

    def get_graph_json(self) -> dict:
        project_predecessors = [
            {"name": taskor, "dependsOn": [predecessors]}
            for taskor, predecessors in self._taskor_to_immediate_predecessors.items()
        ]
        return {"tasks": project_predecessors}

    def _build_immediate_predecessors(self):
        for taskor_name, taskor_cls in self._entrex_taskors.items():
            predecessors = self._taskor_to_predecessors[taskor_name]
            immediate_taskors = set(predecessors)
            for predecessor in predecessors:
                predecessor_dependencies = set(self._taskor_to_all_predecessors[predecessor])
                immediate_taskors = immediate_taskors.difference(predecessor_dependencies)
            self._taskor_to_immediate_predecessors[taskor_name] = list(immediate_taskors)