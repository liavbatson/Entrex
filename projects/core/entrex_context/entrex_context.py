from typing import Dict, Optional, Type

from hazut_hakol.core.utils import Environment
from ..project_information.entrex_project_information import ProjectInformation

from ..entrex_graph_system.entrex_graph_node import EntrexGraphNode
from .taskors_list import ENTREX_TASKOR_LIST
from .projects_list import ENTREX_PROJECT_LIST


class EntrexProjectContext:
    def __init__(self, mode: Environment):
        self._mode = mode
        self._taskor_list = ENTREX_TASKOR_LIST[mode]
        self._project_list = ENTREX_PROJECT_LIST[mode]

        self._taskors: Dict[str, Type[EntrexGraphNode]] = {taskor_class.get_taskor_name(): taskor_class
                                                           for taskor_class in self._taskor_list}
        self._projects: Dict[str, Type[ProjectInformation]] = {project.project_name: project
                                                               for project in self._project_list}
        self._hebrew_projects = {project.project_name_hebrew: project
                                 for project in self._project_list}

    @property
    def taskors(self) -> Dict[str, Type[EntrexGraphNode]]:
        return self._taskors

    @property
    def projects(self) -> dict[str, Type[ProjectInformation]]:
        return self._projects

    def get_taskor_by_name(self, name: str) -> Optional[Type[EntrexGraphNode]]:
        return self._taskors.get(name)

    def get_project_by_name(self, name: str) -> Optional[Type[ProjectInformation]]:
        return self._projects.get(name)
