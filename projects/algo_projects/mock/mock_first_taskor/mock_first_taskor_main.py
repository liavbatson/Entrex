import os

from hazut_hakol.core.utils import Environment
from projects.algo_projects.mock.mock_first_taskor.mock_first_taskor import MockFirstTaskor
from projects.core.task_runners import TaskRunner


if __name__ == "__name__":
    if os.environ.get("ENV_MODE") is not None:
        mode = Environment(os.environ.get("ENV_MODE"))
    else:
        mode = Environment.DEVELOPMENT

    taskor = TaskRunner(mode=mode, taskor_class=MockFirstTaskor)
    taskor.run()
