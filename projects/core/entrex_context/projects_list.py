from typing import Dict, List, Type

from projects.core.project_information.entrex_project_information import ProjectInformation
from hazut_hakol.core.utils import Environment

ENTREX_PROJECT_LIST: Dict[Environment, List[Type[ProjectInformation]]] = {
    Environment.PRODUCTION: [],
    Environment.STAGING: [],
    Environment.DEVELOPMENT: [],
    Environment.TESTING: []
}
