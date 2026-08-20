import os

from hazut_hakol.core.utils import Environment
from projects.algo_projects.heimdall.cloud_detection.cloud_detection_taskor import CloudDetectionTaskor
from projects.core.task_runners import TaskRunner


if __name__ == "__main__":
    if os.environ.get("ENV_MODE") is not None:
        mode = Environment(os.environ.get("ENV_MODE"))
    else:
        mode = Environment.DEVELOPMENT

    taskor = TaskRunner(mode=mode, taskor_class=CloudDetectionTaskor)
    taskor.run()
