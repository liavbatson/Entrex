import shutil
from pathlib import Path

from hazut_hakol.core.utils import Environment
from projects.algo_projects.mock.mock_first_taskor.mock_first_taskor import MockFirstTaskor
from projects.algo_projects.mock.mock_second_taskor.mock_second_taskor import MockSecondTaskor


if __name__ == "__main__":
    mode = Environment.DEVELOPMENT
    tmp_storage = Path("./tmp")

    trigger_ids = [
        "S2B_MSIL2A_20260807T081609_N0512_R121_T36RYT_20260807T122023",
        "S2A_MSIL2A_20260811T081021_N0512_R078_T36RYT_20260811T132655",
        "S2C_MSIL2A_20260809T080611_N0512_R078_T36RYT_20260809T115100"
    ]

    for trigger_id in trigger_ids:
        mock_first_stage = MockFirstTaskor(trigger_id=trigger_id, tmp_storage=tmp_storage)
        mock_second_stage = MockSecondTaskor(trigger_id=trigger_id, tmp_storage=tmp_storage)

        mock_first_stage.setup_taskor(mode=mode)
        mock_first_stage.extract()
        mock_first_stage.transform()
        mock_first_stage.save()

        mock_second_stage.setup_taskor(mode=mode)
        mock_second_stage.extract()
        mock_second_stage.transform()
        mock_second_stage.save()

        shutil.rmtree(tmp_storage)
