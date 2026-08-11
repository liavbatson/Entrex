from pathlib import Path

import cv2
from loguru import logger

from hazut_hakol.apio.data_interfaces import MetadataFetcher
from hazut_hakol.apio.data_storage.data_storage_azure import DataStorageAzure
from hazut_hakol.core.utils import Environment
from hazut_hakol.io.image_io import read_barak_image
from projects.algo_projects.mock.mock_first_taskor.mock_first_taskor import MockFirstTaskor, MockFirstTaskorConsumer
from projects.core.etsc_interface import ETS_Interface


class MockSecondTaskor(ETS_Interface):
    _predecessors = [MockFirstTaskor]

    @classmethod
    def setup_taskor(cls, mode: Environment):
        super().setup_taskor(mode=mode)
        cls.data_storage = DataStorageAzure(mode=mode).set_service(cls.get_taskor_name())
        cls._mock_first_taskor_consumer = MockFirstTaskorConsumer(mode=mode)
        cls._metadata_fetcher = MetadataFetcher(mode=mode)

    def extract(self):
        self._sweep = self._metadata_fetcher.fetch_sweeps([self._trigger_id])[0]
        self._image = self._mock_first_taskor_consumer.consume_sweep_result(
            sweep_gid=self._trigger_id, local_path=str(self._tmp_storage / "flipped_img.png")
        )

    def transform(self):
        img = read_barak_image(self._image, self._sweep)
        self._tensor_grayscaled_flipped_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def save(self):
        self._grayscaled_flliped_img_local_path = self._tmp_storage / "gray_flipped_img.png"
        cv2.imwrite(self._grayscaled_flliped_img_local_path, self._tensor_grayscaled_flipped_img)
        self.data_storage.upload_file(self._grayscaled_flliped_img_local_path, f"{self._trigger_id}/gray_flipped_img.png")
