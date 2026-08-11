from datetime import datetime
from typing import List

from bson import ObjectId
from hazut_hakol.utils.ttl_cache import TTLCache, ttl_cache
from pymongo.collection import Collection
from shapely import MultiPolygon

from hazut_hakol.core.classes.roi import Roi, RoiStatus, RoiRunningMode

cache = TTLCache(default_ttl_seconds=300)


class RoiDBInterface:
    def __init__(self, roi_collection: Collection):
        self._roi_collection = roi_collection

    def get_collection(self) -> Collection:
        return self._roi_collection

    def add_roi(self, roi: Roi) -> None:
        self._roi_collection.insert_one(document=roi.to_mongo_document())

    def get_roi(self, roi_id: str) -> Roi:
        return Roi.from_mongo_document(self._roi_collection.find_one({"_id": roi_id}))

    def get_polygon_by_rois(self, roi_ids: List[str]) -> MultiPolygon:
        regions = []
        for roi in self._roi_collection.find({"_id": {"$in": roi_ids}}):
            roi_instance = Roi.from_mongo_document(roi)
            regions += list(roi_instance.region.geoms)
        combined_region = MultiPolygon(regions)
        return combined_region

    def get_rois_realtime_and_enabled(self) -> List[Roi]:
        roi_instances_list = []
        for roi in self._roi_collection.find(
                {
                    "status": RoiStatus.ENABLED.value,
                    "running_mode": RoiRunningMode.REALTIME.value
                }
        ):
            roi_instance = Roi.from_mongo_document(roi)
            roi_instances_list.append(roi_instance)
        return roi_instances_list

    def get_on_demand_rois_needing_deletion(self, older_than_datetime: datetime) -> List[Roi]:
        on_demand_rois_raws = list(self._roi_collection.find(
            {
                "creation_time": {"$lt": older_than_datetime},
                "running_mode": RoiRunningMode.ON_DEMAND.value
            }
        ))
        rois_to_delete = [Roi.from_mongo_document(on_demand_rois_raw) for on_demand_rois_raw in on_demand_rois_raws]
        return rois_to_delete

    def get_on_demand_rois(self) -> List[Roi]:
        on_demand_rois_raws = list(self._roi_collection.find(
            {
                "running_mode": RoiRunningMode.ON_DEMAND.value
            }
        ))
        return [Roi.from_mongo_document(on_demand_rois_raw) for on_demand_rois_raw in on_demand_rois_raws]

    def delete_rois(self, rois: List[Roi]):
        rois_ids = [roi._id for roi in rois]
        self._roi_collection.delete_many(
            filter={
                "_id": {"$in": rois_ids}
            }
        )

    @ttl_cache(cache)
    def get_rois(self, roi_ids: List[ObjectId]) -> List[Roi]:
        raw_rois = self._roi_collection.find({"_id": {"$in": roi_ids}})
        return [Roi.from_mongo_document(raw_roi) for raw_roi in raw_rois]