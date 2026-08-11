import shutil
from dataclasses import dataclass
from pathlib import Path

from azure.core.exceptions import HttpResponseError
from loguru import logger
from typing import List
from hazut_hakol.apio.data_storage.data_storage_interface import DataStorageInterface, MissingDataError, \
    DataStorageNodeEnum
from hazut_hakol.apio.interfaces.azure_storage_interface import AzureStorageInterface
from hazut_hakol.core.utils import Environment


@dataclass
class _AzureNodeInfo:
    connection_string: str
    container_name: str


class DataStorageAzureNode(DataStorageNodeEnum):
    AZURE_STORAGE_LB_CONTAINER = _AzureNodeInfo(
        connection_string=("DefaultEndpointsProtocol=https;AccountName=argosstrprod;AccountKey"
                           "=C8MyDqzeI4jLPDNphLV5cewx9ihVIEldQN1f6zCo7KvcvnZwF8rhWdWxG5Ssl1G+O9ZFleqAY0Pu+AStUGWt9w"
                           "==;EndpointSuffix=core.windows.net"),
        container_name="lb-container"
    )

    AZURE_STORAGE_ENTREX_CONTAINER = _AzureNodeInfo(
        connection_string=("DefaultEndpointsProtocol=https;AccountName=argosstrprod;AccountKey"
                           "=C8MyDqzeI4jLPDNphLV5cewx9ihVIEldQN1f6zCo7KvcvnZwF8rhWdWxG5Ssl1G+O9ZFleqAY0Pu+AStUGWt9w"
                           "==;EndpointSuffix=core.windows.net"),
        container_name="entrex"
    )


class DataStorageAzure(DataStorageInterface):
    def __init__(self, mode: Environment, is_persistent: bool = False,
                 data_storage_node: DataStorageAzureNode = DataStorageAzureNode.AZURE_STORAGE_ENTREX_CONTAINER):
        super().__init__(
            mode=mode,
            is_persistent=is_persistent,
            data_storage_node=data_storage_node
        )

        data_storage_node_info: _AzureNodeInfo = data_storage_node.value
        self._azure_storage_interface = AzureStorageInterface(
            connection_string=data_storage_node_info.connection_string,
            container_name=data_storage_node_info.container_name
        )

    def get_storage_path_for_service(self, service: str):
        return Path(service) / self._persistence_prefix

    def download_file(self, remote_file: str, local_file: Path, override: bool = True) -> Path:
        assert self._storage_service_path is not None
        remote_file_with_taskor = self._storage_service_path / remote_file
        logger.info(f"Started downloading {remote_file_with_taskor} to folder {str(local_file)}")
        if not override and local_file.exists():
            logger.info(f"Not overriding, skipped downloading {remote_file_with_taskor}")
        else:
            try:
                self._azure_storage_interface.download_file(blob_name=remote_file_with_taskor, download_path=str(local_file))
                logger.info(f"Ended downloading {remote_file_with_taskor}")
            except HttpResponseError as e:
                if e.status_code == 404:
                    raise MissingDataError(f"Azure missing file when trying to download {remote_file_with_taskor}")
                else:
                    raise
        return local_file

    def download_dir(self, remote_dir: str, local_dir: Path, override: bool = True, *, expect_tar: bool = True) -> Path:
        assert self._storage_service_path is not None
        remote_dir_with_taskor = self._storage_service_path / remote_dir
        logger.info(f"Started downloading {remote_dir_with_taskor} to folder {str(local_dir)}")
        if override:
            shutil.rmtree(path=local_dir, ignore_errors=True)
        if expect_tar:
            number_of_files = 1
            self._azure_storage_interface.download_file(blob_name=str(remote_dir_with_taskor.with_suffix(".tar")),
                                                        download_path=str(local_dir.with_suffix(".tar")))
            shutil.unpack_archive(
                filename=local_dir.with_suffix(".tar"),
                format='tar',
                extract_dir=local_dir
            )
        else:
            number_of_files = self._azure_storage_interface.download_dir(folder_prefix=str(remote_dir_with_taskor),
                                                                         local_folder=str(local_dir))
            if number_of_files == 0:
                raise MissingDataError(f"Azure have no files in requested folder {remote_dir_with_taskor}")
        logger.info(f"Ended downloading {remote_dir_with_taskor}, found {number_of_files} files")
        return local_dir

    def upload_file(self, local_file: Path, remote_file: str):
        assert self._storage_service_path is not None
        remote_file_with_taskor = self._storage_service_path / remote_file
        logger.info(f"Started uploading {local_file} to {remote_file_with_taskor}")
        self._azure_storage_interface.upload_file(local_file_path=str(local_file),
                                                  blob_name=str(remote_file_with_taskor))
        logger.info(f"Ended uploading {local_file}")

    def upload_dir(self, local_dir: Path, remote_dir: str, *, should_tar: bool = True) -> None:
        assert self._storage_service_path is not None
        remote_dir_with_taskor = self._storage_service_path / remote_dir
        logger.info(f"Started uploading {local_dir} to folder {remote_dir_with_taskor}")
        self._azure_storage_interface.delete_dir(blob_prefix=str(remote_dir_with_taskor))
        if should_tar:
            shutil.make_archive(
                base_name=str(local_dir),
                format='tar',
                root_dir=local_dir
            )
            self._azure_storage_interface.upload_file(blob_name=str(remote_dir_with_taskor.with_suffix(".tar")),
                                                      local_file_path=str(local_dir.with_suffix(".tar")))
        else:
            self._azure_storage_interface.upload_dir(local_dir_path=str(local_dir),
                                                     blobs_folder=str(remote_dir_with_taskor))
        logger.info(f"Ended uploading {local_dir}")

    def clean_storage_for_trigger_id(self, trigger_id: str, *, confirm_flag_for_production: bool = False):
        super().clean_storage_for_trigger_id(
            trigger_id=trigger_id,
            confirm_flag_for_production=confirm_flag_for_production
        )
        trigger_path = self._storage_service_path / trigger_id
        self._azure_storage_interface.delete_dir(blob_prefix=str(trigger_path))

    def get_stored_services_list(self) -> List[str]:
        return self._azure_storage_interface.list_directories()

    def does_trigger_exists(self, trigger_id: str) -> bool:
        assert self._storage_service_path is not None
        trigger_path = self._storage_service_path / trigger_id
        return self._azure_storage_interface.dir_exists(folder_name=str(trigger_path))

    def does_file_exists(self, trigger_id: str, file_name: str) -> bool:
        assert self._storage_service_path is not None
        file_path = self._storage_service_path / trigger_id / file_name
        return self._azure_storage_interface.file_exists(blob_name=str(file_path))

    def get_trigger_ids_in_stored_service(self, stored_service: str) -> List[str]:
        triggers_from_azure = self._azure_storage_interface.list_directories(
            prefix=f"{self.get_storage_path_for_service(stored_service)}/"
        )
        return [trigger.rstrip('/').split('/')[-1] for trigger in triggers_from_azure]
