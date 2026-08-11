from typing import List

from hazut_hakol.apio.knowledge_center.knowledge_center import KnowledgeCenter
from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.utils import Environment


class MetadataFetcher:
    def __init__(self, mode: Environment):
        self._mode = mode
        self._knowledge_center = KnowledgeCenter(mode=mode)
        self._images_metadata_interface = self._knowledge_center.images_metadata_db_interface

    def fetch_sweeps(self, sweeps_gids: List[str]) -> List[Sweep]:
        sweeps = self._images_metadata_interface.get_sweeps_metadata(sweeps_gids=sweeps_gids)
        return sweeps
