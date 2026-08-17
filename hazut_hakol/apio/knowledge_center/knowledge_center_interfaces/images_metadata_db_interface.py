from datetime import datetime
from math import inf
from typing import List, Union

from loguru import logger
from pymongo.collection import Collection
from shapely import Polygon, MultiPolygon

from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.utils import ImagingTechnique, Sensor


class ImagesMetadataDBInterface:
    def __init__(self, images_metadata_collection: Collection):
        self._images_metadata_collection = images_metadata_collection

    def get_collection(self) -> Collection:
        return self._images_metadata_collection

    def _get_metadata(self) -> dict:
        return self._images_metadata_collection.find()[0] if self._images_metadata_collection.count_documents({}) > 0 else {}

    def image_exists(self, sweep_gid: str) -> bool:
        if self._images_metadata_collection.find_one({'sweep_gid': sweep_gid}):
            return True
        return False
    
    def add_image_metadata_to_db(self, image_metadata: Sweep) -> None:
        if not self.image_exists(sweep_gid=image_metadata.sweep_gid):
            self._images_metadata_collection.insert_one(document=image_metadata.to_mongo_document())
            logger.info(f"Sweep uploaded to db: {image_metadata.sweep_gid}")
        else:
            logger.warning(f"Sweep already exists in db: {image_metadata.sweep_gid}")

    def get_sweeps_metadata(self, sweeps_gids: List[str]) -> List[Sweep]:
        sweeps = self._images_metadata_collection.find({
            'sweep_gid': {"$in": sweeps_gids}
        })
        sweeps = [Sweep.from_mongo_document(sweep) for sweep in sweeps]
        return sweeps

    def delete_image_from_db(self, sweep_gid: str) -> None:
        self._images_metadata_collection.delete_one({'sweep_gid': sweep_gid})

    def get_sweeps_metadata_by_custom_query(self, query: dict, limit_amount_sweeps: int = inf) -> List[Sweep]:
        sweeps = self._images_metadata_collection.find(query)
        if limit_amount_sweeps != inf:
            sweeps = sweeps.limit(int(limit_amount_sweeps))

        sweeps = [Sweep.from_mongo_document(sweep) for sweep in sweeps]
        return sweeps

    def fetch_sweeps_starts_with(self, sweep_gid_prefix: str, limit_amount_sweeps: int = inf) -> List[Sweep]:
        query = {"sweep_gid": {"$regex": f"^{sweep_gid_prefix}"}}
        return self.get_sweeps_metadata_by_custom_query(query, limit_amount_sweeps)

    def fetch_sweeps_ends_with(self, sweep_gid_suffix: str, limit_amount_sweeps: int = inf) -> List[Sweep]:
        query = {"sweep_gid": {"$regex": f"{sweep_gid_suffix}$"}}
        return self.get_sweeps_metadata_by_custom_query(query, limit_amount_sweeps)

    def fetch_sortie(self, sortie: str, sweep_gids_ignore_list: List[str] = [],
                     limit_amount_sweeps: int = inf) -> List[Sweep]:
        query = {"sortie_id": sortie}
        if sweep_gids_ignore_list:
            query["sweep_gid"] = {"$nin": sweep_gids_ignore_list}
        sweeps = self.get_sweeps_metadata_by_custom_query(
            query=query,
            limit_amount_sweeps=limit_amount_sweeps
        )
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
        query = {
            "capture_time": {
                "$gte": start_date,
                "$lte": end_date
            },
            "sensor": {"$in": sensors}
        }

        if polygon is not None:
            query["trace"] = {
                "$geoWithin": {
                    "$geometry": polygon.__geo_interface__
                }
            }
        if imaging_technique is not None:
            query["imaging_technique"] = {"$in": imaging_technique.value}
        if sweep_gids_ignore_list:
            query["sweep_gid"] = {"$nin": sweep_gids_ignore_list}
        if sorties_ignore_list:
            query["sortie_id"] = {"$nin": sorties_ignore_list}

        sweeps = self.get_sweeps_metadata_by_custom_query(
            query=query,
            limit_amount_sweeps=limit_amount_sweeps
        )
        return sweeps