from pathlib import Path
from typing import List

from hazut_hakol.apio.data_interfaces.data_fetcher.data_fetcher_interface import DataFetcherInterface
from hazut_hakol.apio.data_storage.data_storage_azure import DataStorageAzureNode
from hazut_hakol.apio.interfaces.azure_storage_interface import AzureStorageInterface
from hazut_hakol.core.classes.barak.barak_sweep import Sweep
from hazut_hakol.core.entrex_base_errors import EntrexDataError
from hazut_hakol.core.utils import Environment


class DataFetcherException(EntrexDataError):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def create_folder_if_needed(output_dir: Path):
    if not output_dir.exists():
        output_dir.mkdir(exist_ok=True, parents=True)


class DataFetcher(DataFetcherInterface):
    def __init__(self, mode: Environment):
        self._mode = mode
        connection_string = DataStorageAzureNode.AZURE_STORAGE_IMAGES_CONTAINER.value.connection_string
        container_name = DataStorageAzureNode.AZURE_STORAGE_IMAGES_CONTAINER.value.container_name
        self._azure_storage_interface = AzureStorageInterface(connection_string=connection_string,
                                                              container_name=container_name)

    def download_sweep(self, sweep: Sweep, output_dir: Path) -> dict:
        create_folder_if_needed(output_dir=output_dir)
        sweeps_dict = {}
        azure_path = Path(sweep.image_path_in_azure)
        self._azure_storage_interface.download_file(
            blob_name=sweep.image_path_in_azure,
            download_path=str(output_dir / azure_path.name)
        )
        sweeps_dict[sweep.sweep_gid] = str(output_dir / azure_path.name)
        return sweeps_dict

    def download_sweeps(self, sweeps: List[Sweep], output_dir: Path, raise_on_missing: bool = False) -> dict:
        create_folder_if_needed(output_dir=output_dir)
        sweeps_dict = {}
        for sweep in sweeps:
            azure_path = Path(sweep.image_path_in_azure)
            self._azure_storage_interface.download_file(
                blob_name=sweep.image_path_in_azure,
                download_path=str(output_dir / azure_path.name)
            )
            sweeps_dict[sweep.sweep_gid] = str(output_dir / azure_path.name)
        return sweeps_dict

    def download_sweep_asset_by_filename(self,
                                         sweep: Sweep,
                                         output_dir: Path,
                                         asset_filename: str,
                                         raise_on_missing: bool = False
    ):
        create_folder_if_needed(output_dir=output_dir)
        sweeps_dict = {}
        file_to_download = Path(Path(sweep.image_path_in_azure).with_name(asset_filename))
        self._azure_storage_interface.download_file(
            blob_name=file_to_download,
            download_path=str(output_dir / file_to_download.name)
        )
        sweeps_dict[sweep.sweep_gid] = str(output_dir / file_to_download.name)
        return sweeps_dict

    def download_sweeps_asset_by_filename(self,
                                          sweeps: List[Sweep],
                                          output_dir: Path,
                                          asset_filename: str,
                                          raise_on_missing: bool = False
    ):
        create_folder_if_needed(output_dir=output_dir)
        sweeps_dict = {}
        for sweep in sweeps:
            file_to_download = Path(Path(sweep.image_path_in_azure).with_name(asset_filename))
            self._azure_storage_interface.download_file(
                blob_name=file_to_download,
                download_path=str(output_dir / file_to_download.name)
            )
            sweeps_dict[sweep.sweep_gid] = str(output_dir / file_to_download.name)
        return sweeps_dict

    def download_grids(self, sweeps: List[Sweep], output_dir: Path, raise_on_missing: bool = False):
        pass
