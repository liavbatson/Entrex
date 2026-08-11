import argparse
import json
from pathlib import Path

from loguru import logger

from hazut_hakol.apio.data_storage.data_storage_azure import DataStorageAzureNode
from hazut_hakol.apio.interfaces.azure_storage_interface import AzureStorageInterface
from hazut_hakol.apio.knowledge_center.knowledge_center import KnowledgeCenter
from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.utils import Environment

AZURE_INFO = DataStorageAzureNode.AZURE_STORAGE_ENTREX_CONTAINER.value
CONNECTION_STRING = AZURE_INFO.connection_string
CONTAINER_NAME = AZURE_INFO.container_name


class ImageUploader:
    def __init__(self, mode: Environment, input_folder: Path, image_suffix: str):
        self._knowledge_center = KnowledgeCenter(mode=mode)
        self._image_metadata_db_interface = self._knowledge_center.images_metadata_db_interface
        self._azure_storage_interface = AzureStorageInterface(connection_string=CONNECTION_STRING,
                                                              container_name=CONTAINER_NAME)
        self._input_folder = input_folder
        self._image_suffix = image_suffix

        self._json_file_path = [file for file in Path(self._input_folder).glob("*.json")][0]
        self._image_file_path = [file for file in Path(self._input_folder).glob(f"*.{self._image_suffix}")][0]

    def read_json_into_sweep_object(self) -> Sweep:
        with open(self._json_file_path, 'r') as file:
            data = json.load(file)
        sweep = Sweep.parse_from_barak_dict(data)
        return sweep

    def upload_to_db(self, blob_name: str) -> None:
        sweep = self.read_json_into_sweep_object()
        sweep.image_path_in_azure = blob_name
        logger.info(f"Uploading sweep: {sweep.sensor}:{sweep.sweep_gid} to DB")
        self._image_metadata_db_interface.add_image_metadata_to_db(image_metadata=sweep)

    def upload_to_azure_storage(self) -> str:
        sweep = self.read_json_into_sweep_object()
        logger.info(f"Uploading sweep: {sweep.sensor}:{sweep.sweep_gid} to AzureStorage")
        blob_name = f"images/{sweep.sensor.value}/{Path(self._image_file_path).name}"
        self._azure_storage_interface.upload_file(
            local_file_path=str(self._image_file_path),
            blob_name=blob_name,
            overwrite=False
        )
        return blob_name

    def upload_image(self) -> None:
        blob_name = self.upload_to_azure_storage()
        self.upload_to_db(blob_name=blob_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some images")
    parser.add_argument(
        "--input_folder",
        "-i",
        required=True,
        help="Path to folder contains image and metadata json file"
    )
    parser.add_argument(
        "--image_suffix",
        "-s",
        required=True,
        help="The image suffix (jpg, png, tiff ...)"
    )
    args = parser.parse_args()
    image_uploader = ImageUploader(mode=Environment.DEVELOPMENT,
                                   input_folder=args.input_folder,
                                   image_suffix=args.image_suffix)
    image_uploader.upload_image()
