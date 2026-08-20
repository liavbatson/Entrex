import shutil
from pathlib import Path
from loguru import logger

from hazut_hakol.core.utils import Environment
from projects.algo_projects.heimdall.clear_area.clear_area_taskor import ClearAreaTaskor
from projects.algo_projects.heimdall.cloud_detection.cloud_detection_taskor import CloudDetectionTaskor


if __name__ == "__main__":
    mode = Environment.DEVELOPMENT
    tmp_storage = Path("./tmp_cloud_detection")

    trigger_ids = [
        "S2B_MSIL2A_20260815T105619_N0512_R094_T31UES_20260815T133002"
    ]

    for trigger_id in trigger_ids:
        logger.info(f"Running Sentinel Cloud Detection On Sweep: {trigger_id}")
        cloud_detection_stage = CloudDetectionTaskor(trigger_id=trigger_id, tmp_storage=tmp_storage)

        logger.info("Setting up Cloud Detection Stage")
        cloud_detection_stage.setup_taskor(mode=mode)
        logger.info("Running Cloud Detection Stage")
        logger.info("Extract")
        cloud_detection_stage.extract()
        logger.info("Transform")
        cloud_detection_stage.transform()
        logger.info("Save")
        cloud_detection_stage.save()

        logger.info(f"Running Clear Area Extraction On Sweep: {trigger_id}")
        clear_area_stage = ClearAreaTaskor(trigger_id=trigger_id, tmp_storage=tmp_storage)

        logger.info("Setting up Clear Area Stage")
        clear_area_stage.setup_taskor(mode=mode)
        logger.info("Extract")
        clear_area_stage.extract()
        logger.info("Transform")
        clear_area_stage.transform()
        logger.info("Save")
        clear_area_stage.save()

        shutil.rmtree(tmp_storage)
