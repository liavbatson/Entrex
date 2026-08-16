from pathlib import Path

from loguru import logger

from hazut_hakol.apio.data_storage.data_storage_azure import DataStorageAzureNode
from hazut_hakol.apio.interfaces.azure_storage_interface import AzureStorageInterface
from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.utils import Environment

ASSETS_SENDER_URI = {
    Environment.PRODUCTION: "",
    Environment.STAGING: "",
    Environment.DEVELOPMENT: "",
    Environment.TESTING: "",
}

AZURE_INFO = DataStorageAzureNode.AZURE_STORAGE_IMAGES_CONTAINER.value
CONNECTION_STRING = AZURE_INFO.connection_string
CONTAINER_NAME = AZURE_INFO.container_name


class AssetSender:
    def __init__(self, mode: Environment, sweep: Sweep, asset_name: str):
        self._mode = mode
        self._service_uri = ASSETS_SENDER_URI[mode]
        if self._service_uri is None:
            logger.warning(f"Notice: Trying to use AssetsSender but no URL configured for environment: {self._service_uri}")

        self._azure_storage_interface = AzureStorageInterface(connection_string=CONNECTION_STRING,
                                                              container_name=CONTAINER_NAME)
        self._sweep = sweep
        self._asset_name = asset_name


    def send_single_asset(self, product_path: Path):
        if self._service_uri is None:
            logger.warning(
                f"Notice: Trying to use AssetsSender but no URL configured for environment: {self._service_uri}")
            return

        self._azure_storage_interface.upload_file(
            local_file_path=product_path,
            blob_name=Path(f"images/{self._sweep.sensor.value}/{self._sweep.sweep_gid}/{self._sweep.sweep_gid}_{self._asset_name}").with_suffix(product_path.suffix)
        )