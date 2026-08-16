from datetime import datetime
from typing import List, Union

from ijson.backends.python import inf
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
        sensors = [sensor.value for sensor in sensors]
        # Base query
        query = {
            "capture_time": {
                "$gte": start_date,
                "$lte": end_date
            },
            "sensor": {"$in": sensors}
        }
        # Add polygon to query
        if polygon is not None:
            query["geometry"] = {
                "$geoWithin": {
                    "$geometry": polygon.__geo_interface__
                }
            }
        # Add imaging technique
        if imaging_technique is not None:
            query["imaging_technique"] = {"$in": imaging_technique.value}
        # Add sweep to ignore
        if sweep_gids_ignore_list:
            query["sweep_gid"] = {"$nin": sweep_gids_ignore_list}
        # Add sorties to ignore
        if sorties_ignore_list:
            query["sortie"] = {"$nin": sorties_ignore_list}

        cursor = self._images_metadata_collection.find(query)
        if limit_amount_sweeps != float('inf'):
            cursor = cursor.limit(int(limit_amount_sweeps))

        sweeps = []
        for document in cursor:
            sweep = Sweep.from_mongo_document(document)
            sweeps.append(sweep)

        return sweeps
    
    def fetch_sortie(self, sortie: str, sweep_gids_ignore_list: List[str] = [],
                     limit_amount_sweeps: int = inf) -> List[Sweep]:
        pass
    
    def fetch_sweeps_starts_with(self, sweep_gid_prefix: str) -> List[Sweep]:
        pass
    
    def fetch_sweeps_ends_with(self, sweep_gid_suffix: str) -> List[Sweep]:
        pass
