from datetime import datetime
from math import inf
from typing import List, Union

from shapely import Polygon, MultiPolygon

from hazut_hakol.apio.data_interfaces.metadata_fetcher.metadata_fetcher_interface import MetadataFetcherInterface
from hazut_hakol.apio.knowledge_center.knowledge_center import KnowledgeCenter
from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.utils import Environment, Sensor, ImagingTechnique


class MetadataFetcher(MetadataFetcherInterface):
    def __init__(self, mode: Environment):
        self._mode = mode
        self._knowledge_center = KnowledgeCenter(mode=mode)
        self._images_metadata_db_interface = self._knowledge_center.images_metadata_db_interface
        self._images_metadata_collection = self._images_metadata_db_interface.get_collection()
        
    def fetch_sweep(self, sweep_gid: str) -> Sweep:
        sweep = self._images_metadata_db_interface.get_sweeps_metadata([sweep_gid])[0]
        return sweep

    def fetch_sweeps(self, sweep_gids: List[str]) -> List[Sweep]:
        sweeps = self._images_metadata_db_interface.get_sweeps_metadata(sweeps_gids=sweep_gids)
        return sweeps
    
    def fetch_sweeps_in_capture_time_range_and_multipolygon(self,
                                                            polygon: Union[Polygon, MultiPolygon],
                                                            start_date: datetime,
                                                            end_date: datetime,
                                                            sensors: List[Sensor],
                                                            imaging_technique: ImagingTechnique = None,
                                                            sweep_gids_ignore_list: List[str] = [],
                                                            sorties_ignore_list: List[str] = [],
                                                            limit_amount_sweeps: int = inf
                                                            ) -> List[Sweep]:
        return self._images_metadata_db_interface.fetch_sweeps_in_capture_time_range_and_multipolygon(
            polygon=polygon,
            start_date=start_date,
            end_date=end_date,
            sensors=sensors,
            imaging_technique=imaging_technique,
            sweep_gids_ignore_list=sweep_gids_ignore_list,
            sorties_ignore_list=sorties_ignore_list,
            limit_amount_sweeps=limit_amount_sweeps
        )
    
    def fetch_sortie(self, sortie: str, sweep_gids_ignore_list: List[str] = [],
                     limit_amount_sweeps: int = inf) -> List[Sweep]:
        return self._images_metadata_db_interface.fetch_sortie(
            sortie=sortie,
            sweep_gids_ignore_list=sweep_gids_ignore_list,
            limit_amount_sweeps=limit_amount_sweeps
        )
    
    def fetch_sweeps_starts_with(self, sweep_gid_prefix: str,
                                 limit_amount_sweeps: int = inf) -> List[Sweep]:
        return self._images_metadata_db_interface.fetch_sweeps_starts_with(
            sweep_gid_prefix=sweep_gid_prefix,
            limit_amount_sweeps=limit_amount_sweeps
        )
    
    def fetch_sweeps_ends_with(self, sweep_gid_suffix: str,
                               limit_amount_sweeps: int = inf) -> List[Sweep]:
        return self._images_metadata_db_interface.fetch_sweeps_ends_with(
            sweep_gid_suffix=sweep_gid_suffix,
            limit_amount_sweeps=limit_amount_sweeps
        )
