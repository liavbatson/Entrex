from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict
from bson import ObjectId
from shapely import Polygon
from shapely.geometry import MultiPolygon
from shapely.validation import make_valid
from hazut_hakol.core.utils import Sensor, ImagingTechnique


class RoiRunningMode(Enum):
    ON_DEMAND = "on_demand"
    REALTIME = "realtime"

    @property
    def hebrew(self):
        hebrew_enum = {
            RoiRunningMode.ON_DEMAND: "ריצות ידניות",
            RoiRunningMode.REALTIME: "ריצות אוטומטיות"
        }
        return hebrew_enum[self]


class RoiStatus(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"

    @property
    def hebrew(self):
        hebrew_enum = {
            RoiStatus.ENABLED: "מופעל",
            RoiStatus.DISABLED: "מושבת"
        }
        return hebrew_enum[self]


class Roi:
    def __init__(
            self,
            user_id: str,
            roi_name: str,
            region: MultiPolygon,
            project_name: str,
            sensors: List[Sensor],
            imaging_technique: ImagingTechnique,
            priority: int,
            creation_time: datetime,
            running_mode: RoiRunningMode = RoiRunningMode.REALTIME,
            status: RoiStatus = RoiStatus.ENABLED,
            optimize_polygon_selection: bool = False,
            _id: ObjectId = None,
            mutation_id: Optional[str] = None
    ):
        if not region.is_valid:
            region = make_valid(region)
        self._id = _id if _id else ObjectId()
        self.user_id = user_id
        self.roi_name = roi_name
        self.region = region
        self.project_name = project_name
        self.sensors = sensors
        self.imaging_technique = imaging_technique
        self.priority = priority
        self.creation_time = creation_time
        self.running_mode = running_mode
        self.status = status
        self.optimize_polygon_selection = optimize_polygon_selection
        self.mutation_id = mutation_id

    def __str__(self):
        return (
            f"Roi(roi_id={self._id}, roi_name={self.roi_name}, region={self.region}, "
            f"project_name={self.project_name}, sensors={self.sensors}, priority={self.priority}"
            f"creation_time={self.creation_time}"
        )

    def __repr__(self):
        return (
            f"Roi(roi_id={self._id}, roi_name={self.roi_name}, region={self.region}, "
            f"project_name={self.project_name}, sensors={self.sensors}, priority={self.priority}"
            f"creation_time={self.creation_time}"
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Roi) and self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    @classmethod
    def from_mongo_document(cls, roi: Dict):
        polygons = []
        for polygon in roi["region"]:
            polygon_obj = Polygon(polygon)
            polygons.append(polygon_obj)
        multi_polygon = MultiPolygon(polygons)
        roi_sensors = [Sensor(sensor) for sensor in roi["sensors"]]

        roi_instance = Roi(
            _id=roi["_id"],
            user_id=roi.get("user_id", None),
            roi_name=roi["roi_name"],
            region=multi_polygon,
            project_name=roi["project_name"],
            sensors=roi_sensors,
            imaging_technique=ImagingTechnique(roi["imaging_technique"]),
            priority=int(roi["priority"]),
            creation_time=roi["creation_time"].replace(tzinfo=timezone.utc),
            running_mode=RoiRunningMode(roi["running_mode"]),
            status=RoiStatus(roi["status"]),
            optimize_polygon_selection=roi.get("optimize_polygon_selection", False),
            mutation_id=roi.get("mutation_id")
        )
        return roi_instance

    def to_mongo_document(self) -> Dict:
        array = []
        for polygon in self.region.geoms:
            polygon_coords = []
            for coord in polygon.exterior.coords:
                polygon_coords.append([coord[0], coord[1]])
            array.append(polygon_coords)
        sensors_values = [sensor.value for sensor in self.sensors]

        doc = {
            "_id": self._id,
            "user_id": self.user_id,
            "roi_name": self.roi_name,
            "region": array,
            "project_name": self.project_name,
            "sensors": sensors_values,
            "imaging_technique": self.imaging_technique.value,
            "priority": self.priority,
            "creation_time": self.creation_time,
            "running_mode": self.running_mode.value,
            "status": self.status.value,
            "optimize_polygon_selection": self.optimize_polygon_selection
        }

        if self.mutation_id is not None:
            doc["mutation_id"] = self.mutation_id

        return doc
