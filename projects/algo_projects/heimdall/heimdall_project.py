from hazut_hakol.core.classes.trigger import TriggerType
from hazut_hakol.core.utils import Sensor, ImagingTechnique
from projects.algo_projects.heimdall.clear_area.clear_area_taskor import ClearAreaTaskor
from projects.core.project_information.entrex_project_information import ProjectInformation


class HeimdallProject(ProjectInformation):
    project_name = "Heimdall"
    project_trigger_type = TriggerType.SWEEP
    project_name_hebrew = "היימדל"
    allowed_sensors = [Sensor.SENTINEL]
    allowed_imaging_techniques = [ImagingTechnique.EO]
    ending_taskor = ClearAreaTaskor.get_taskor_name()
