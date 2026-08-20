from pathlib import Path

from hazut_hakol.apio.data_interfaces.asset_sender.asset_sender_interface import AssetSenderInterface
from hazut_hakol.apio.data_storage.data_storage_azure import DataStorageAzureNode
from hazut_hakol.apio.interfaces.azure_storage_interface import AzureStorageInterface
from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.utils import Environment

AZURE_INFO = DataStorageAzureNode.AZURE_STORAGE_IMAGES_CONTAINER.value
CONNECTION_STRING = AZURE_INFO.connection_string
CONTAINER_NAME = AZURE_INFO.container_name


class AssetSender(AssetSenderInterface):
    def __init__(self, mode: Environment, sweep: Sweep, asset_name: str):
        self._mode = mode
        self._azure_storage_interface = AzureStorageInterface(connection_string=CONNECTION_STRING,
                                                              container_name=CONTAINER_NAME)
        self._sweep = sweep
        self._asset_name = asset_name


    def send_single_asset(self, product_path: Path):
        self._azure_storage_interface.upload_file(
            local_file_path=product_path,
            blob_name=Path(self._sweep.image_path_in_azure).with_name(product_path.name)
        )