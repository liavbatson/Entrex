from datetime import datetime
from typing import Dict, Optional

from shapely import Polygon, wkt

from hazut_hakol.core.classes.barak.barak_asset import BarakAsset
from hazut_hakol.core.utils import Sensor, ImagingTechnique


class Sweep:
    def __init__(
            self,
            sweep_gid: str,
            sensor: Sensor,
            imaging_technique: Optional[ImagingTechnique] = ImagingTechnique.EO,
            width: Optional[int] = None,
            height: Optional[int] = None,
            capture_time: Optional[datetime] = None,
            resolution: Optional[float] = None,
            trace: Optional[Polygon] = None,
            image_path_in_azure: Optional[str] = None
    ):
        self.sweep_gid = sweep_gid
        self.sensor = Sensor(sensor) if isinstance(sensor, str) else sensor
        self.imaging_technique = ImagingTechnique(imaging_technique) if isinstance(imaging_technique,
                                                                                   str) else imaging_technique
        self.width = int(width)
        self.height = int(height)
        self.capture_time = datetime.fromisoformat(capture_time) if isinstance(capture_time, str) else capture_time
        self.resolution = resolution
        self.trace = wkt.loads(trace) if isinstance(trace, str) else trace
        self.image_path_in_azure = image_path_in_azure

    def __eq__(self, other):
        if isinstance(other, Sweep):
            return self.sweep_gid == other.sweep_gid
        return False

    def __hash__(self):
        return hash(self.sweep_gid)

    def __repr__(self):
        return (
            f"Sweep(global_id={self.sweep_gid}, "
            f"sensor={self.sensor}, "
            f"imaging_technique={self.imaging_technique}), "
            f"width={self.width}, "
            f"height={self.height}, "
            f"capture_time={self.capture_time}, "
            f"resolution={self.resolution}, "
            f"trace={self.trace}, "
            f"image_path_in_azure={self.image_path_in_azure} "
        )

    def __str__(self):
        return (
            f"Global ID: {self.sweep_gid}\n"
            f"Sensor: {self.sensor}\n"
            f"Imaging Technique: {self.imaging_technique}\n"
            f"Capture Time: {self.capture_time}\n"
        )

    def to_dict(self) -> Dict:
        res_dict = self.__dict__.copy()
        for key, value in res_dict.items():
            if key == "assets":
                res_dict[key] = {asset_key: asset_value.to_dict() for asset_key, asset_value in value.items()}
            if hasattr(value, 'to_dict'):
                res_dict[key] = value.to_dict()
            if hasattr(value, 'wkt'):
                res_dict[key] = value.wkt
            if isinstance(value, datetime):
                res_dict[key] = value.isoformat()
        return res_dict

    @classmethod
    def from_dict(cls, sweep_metadata: Dict):
        cls_obj = cls(**sweep_metadata)
        return cls_obj

    @classmethod
    def parse_from_barak_dict(cls, sweep_metadata_raw: Dict):
        return Sweep(
            sweep_gid=sweep_metadata_raw["sweep_gid"],
            sensor=Sensor(sweep_metadata_raw["sensor"]),
            imaging_technique=ImagingTechnique(sweep_metadata_raw["imaging_technique"]),
            width=sweep_metadata_raw.get("width"),
            height=sweep_metadata_raw.get("height")
        )

    @classmethod
    def from_mongo_document(cls, sweep_metadata: Dict):
        sweep_metadata_instance = Sweep(
            sweep_gid=sweep_metadata["sweep_gid"],
            sensor=Sensor(sweep_metadata["sensor"]),
            imaging_technique=ImagingTechnique(sweep_metadata["imaging_technique"]),
            width=sweep_metadata["width"],
            height=sweep_metadata["height"],
            capture_time=sweep_metadata["capture_time"],
            resolution=sweep_metadata["resolution"],
            trace=sweep_metadata["trace"],
            image_path_in_azure=sweep_metadata["image_path_in_azure"]
        )
        return sweep_metadata_instance

    def to_mongo_document(self) -> Dict:
        doc = {
            "sweep_gid": self.sweep_gid,
            "sensor": self.sensor.value,
            "imaging_technique": self.imaging_technique.value,
            "width": self.width,
            "height": self.height,
            "capture_time": self.capture_time,
            "resolution": self.resolution,
            "trace": self.trace,
            "image_path_in_azure": self.image_path_in_azure
        }
        return doc


def to_barak_format_time(date: datetime) -> str:
    return date.strftime("%d%m%Y %H:%M:%S")


def from_barak_format_time(date: str) -> datetime:
    return datetime.strptime(date, "%d%m%Y %H:%M:%S")
