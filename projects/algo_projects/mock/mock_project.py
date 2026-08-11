from hazut_hakol.core.classes.trigger import TriggerType
from hazut_hakol.core.utils import Sensor, ImagingTechnique
from projects.algo_projects.mock.mock_second_taskor.mock_second_taskor import MockSecondTaskor
from projects.core.project_information.entrex_project_information import ProjectInformation


class MockProject(ProjectInformation):
    project_name = "Mock Project"
    project_trigger_type = TriggerType.SWEEP
    project_name_hebrew = "מוק"
    allowed_sensors = [
        Sensor.SENTINEL,
        Sensor.TEST_SENSOR
    ]
    allowed_imaging_techniques = [ImagingTechnique.EO]
    ending_taskor = MockSecondTaskor.get_taskor_name()
