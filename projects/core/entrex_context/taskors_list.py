from typing import List, Dict, Type

from hazut_hakol.core.utils import Environment
from ..entrex_graph_system.entrex_graph_node import EntrexGraphNode


ENTREX_TASKOR_LIST: Dict[Environment, List[Type[EntrexGraphNode]]] = {
    Environment.PRODUCTION: [],
    Environment.STAGING: [],
    Environment.DEVELOPMENT: [],
    Environment.TESTING: []
}