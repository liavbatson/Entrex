from pathlib import Path

import cv2

from hazut_hakol.apio.data_interfaces import MetadataFetcher, DataFetcher
from hazut_hakol.apio.data_storage.data_storage_azure import DataStorageAzure
from hazut_hakol.core.utils import Environment
from hazut_hakol.io.image_io import read_barak_image
from projects.core.etsc_interface import ETS_Interface, ETS_ConsumerInterface


class MockFirstTaskor(ETS_Interface):
    @classmethod
    def setup_taskor(cls, mode: Environment):
        super().setup_taskor(mode=mode)
        cls._metadata_fetcher = MetadataFetcher(mode=mode)
        cls._data_fetcher = DataFetcher(mode=mode)
        cls.data_storage = DataStorageAzure(mode).set_service(service=cls.get_taskor_name())

    def extract(self):
        self._sweep = self._metadata_fetcher.fetch_sweeps([self._trigger_id])[0]
        download_paths = self._data_fetcher.download_sweeps(sweeps=[self._sweep],
                                                            output_dir=self._tmp_storage)
        self._image_path = download_paths[self._sweep.sweep_gid]

    def transform(self):
        img = read_barak_image(self._image_path, self._sweep)
        self._mock_tensor_flipped_img = cv2.flip(img, -1)

    def save(self):
        self._flipped_image_local_path = self._tmp_storage / "flipped_img.png"
        cv2.imwrite(self._flipped_image_local_path, self._mock_tensor_flipped_img)
        self.data_storage.upload_file(self._flipped_image_local_path, f"{self._trigger_id}/flipped_img.png")


class MockFirstTaskorConsumer(ETS_ConsumerInterface):
    def __init__(self, mode: Environment):
        super().__init__(mode=mode)
        self.data_storage = DataStorageAzure(mode)

    def consume_sweep_result(self, sweep_gid: str, local_path: str):
        self.data_storage.set_service(MockFirstTaskor.get_taskor_name())
        assets_path = str(
            self.data_storage.download_file(remote_file=f"{sweep_gid}/flipped_img.png", local_file=Path(local_path)))
        return assets_path
