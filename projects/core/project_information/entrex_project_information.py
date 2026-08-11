from dataclasses import dataclass
from typing import List

from hazut_hakol.core.classes.trigger import TriggerType
from hazut_hakol.core.utils import ImagingTechnique, Sensor


@dataclass
class ProjectInformation:
    project_name: str = None
    project_name_hebrew: str = None
    project_trigger_type: TriggerType = None
    allowed_sensors: List[Sensor] = None
    allowed_imaging_techniques: List[ImagingTechnique] = None
    ending_taskor: str = None

    @classmethod
    def to_dict(cls) -> dict:
        return {
            "project_name": cls.project_name,
            "project_name_hebrew": cls.project_name_hebrew,
            "trigger_type": cls.project_trigger_type.value,
            "allowed_sensors": [sensor.value for sensor in cls.allowed_sensors],
            "allowed_imaging_techniques": [imaging_technique.value for imaging_technique in cls.allowed_imaging_techniques],
            "ending_taskor": cls.ending_taskor
        }