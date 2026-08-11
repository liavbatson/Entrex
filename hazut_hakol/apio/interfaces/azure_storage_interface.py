import os
from pathlib import Path
from typing import Any, Union

from azure.storage.blob import BlobServiceClient
from loguru import logger


class AzureStorageInterface:
    def __init__(self, connection_string: str, container_name: str):
        self._connection_string = connection_string
        self._container_name = container_name

        self._blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    def list_file(self, prefix: str) -> Any:
        container_client = self._blob_service_client.get_container_client(self._container_name)
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return blobs

    def download_file(self, blob_name: Union[str, Path], download_path: Union[str, Path]) -> str:
        blob_name = str(blob_name)
        download_path = str(download_path)
        blob_client = self._blob_service_client.get_blob_client(
            container=self._container_name,
            blob=blob_name
        )
        with open(download_path, "wb") as file:
            download_stream = blob_client.download_blob()
            file.write(download_stream.readall())
        logger.info(f"Blob '{blob_name}' downloaded to '{download_path}'.")
        return download_path

    def download_dir(self, folder_prefix: str, local_folder: str) -> int:
        if folder_prefix and not folder_prefix.endswith("/"):
            folder_prefix += "/"

        blobs = self.list_file(folder_prefix)
        downloaded = 0

        for blob in blobs:
            relative_path = os.path.relpath(blob.name, folder_prefix)
            local_path = os.path.join(local_folder, relative_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.download_file(blob_name=blob.name, download_path=local_path)
            logger.info(f"Downloaded: {blob.name}")
            downloaded += 1

        logger.info(f"\nDownloaded {downloaded} file(s) to '{local_folder}'.")
        return downloaded

    def upload_file(self, local_file_path: str, blob_name: str, overwrite: bool = True):
        if not self.file_exists(blob_name=blob_name):
            blob_client = self._blob_service_client.get_blob_client(
                container=self._container_name,
                blob=blob_name,
            )
            with open(local_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=overwrite)
            logger.info(f"Uploaded '{local_file_path}' to '{blob_name}'.")
        else:
            logger.warning(f"File already exists in azure storage: {blob_name}")

    def upload_dir(self, local_dir_path: str, blobs_folder: str, overwrite: bool = True):
        local_dir_path = Path(local_dir_path)
        if blobs_folder and not blobs_folder.endswith("/"):
            blobs_folder += "/"

        container_client = self._blob_service_client.get_container_client(self._container_name)
        uploaded = 0

        for local_path in local_dir_path.glob("**/*"):
            if not local_path.is_file():
                continue

            relative_path = local_path.relative_to(local_dir_path)
            blob_name = f"{blobs_folder}{relative_path.as_posix()}"
            blob_client = container_client.get_blob_client(blob_name)
            with local_path.open("rb") as data:
                blob_client.upload_blob(data, overwrite=overwrite)
            logger.info(f"Uploaded: {blob_name}")
            uploaded += 1

        logger.info(f"\nUploaded {uploaded} file(s) from '{local_dir_path}'.")

    def delete_file(self, blob_name: str):
        blob_client = self._blob_service_client.get_blob_client(
            container=self._container_name,
            blob=blob_name,
        )
        blob_client.delete_blob()
        logger.info(f"Deleted '{blob_name}'.")

    def delete_dir(self, blob_prefix: str):
        if blob_prefix and not blob_prefix.endswith("/"):
            blob_prefix += "/"

        container_client = self._blob_service_client.get_container_client(self._container_name)
        deleted = 0

        for blob in container_client.list_blobs(name_starts_with=blob_prefix):
            container_client.delete_blob(blob.name)
            logger.info(f"Deleted: {blob.name}")
            deleted += 1

        logger.info(f"\nDeleted {deleted} blob(s) from '{blob_prefix}'.")

    def file_exists(self, blob_name: str):
        blob_client = self._blob_service_client.get_blob_client(
            container=self._container_name,
            blob=blob_name,
        )
        return blob_client.exists()

    def dir_exists(self, folder_name: str):
        if folder_name and not folder_name.endswith("/"):
            folder_name += "/"
        container_client = self._blob_service_client.get_container_client(self._container_name)
        blobs = container_client.list_blobs(
            name_starts_with=folder_name
        )
        return next(blobs, None) is not None

    def list_directories(self, prefix: str = ""):
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"

        container_client = self._blob_service_client.get_container_client(self._container_name)
        directories = []

        for item in container_client.walk_blobs(
                name_starts_with=prefix,
                delimiter="/",
        ):
            if hasattr(item, "name"):
                directories.append(item.name)
        return directories
