from abc import ABC
from enum import Enum
from pathlib import Path
from typing import List

from hazut_hakol.core.entrex_base_errors import EntrexDataError
from hazut_hakol.core.utils import Environment


class MissingDataError(EntrexDataError):
    pass


class DataStorageNodeEnum(Enum):
    pass


class DataStorageInterface(ABC):
    def __init__(self, mode: Environment, is_persistent: bool, data_storage_node: DataStorageNodeEnum):
        self._mode = mode
        self._is_persistent = is_persistent
        self._data_storage_node_info = data_storage_node
        self._storage_service_path = None
        # In else fill the persistence prefix
        self._persistence_prefix = "" if is_persistent else ""

    def set_service(self, service: str):
        self._storage_service_path = self.get_storage_path_for_service(service)
        return self

    def get_storage_path_for_service(self, service: str):
        ...

    def download_dir(self, remote_dir: str, local_dir: Path, override: bool = True) -> Path:
        ...

    def download_file(self, remote_file: str, local_file: Path, override: bool = True) -> Path:
        ...

    def upload_dir(self, local_dir: Path, remote_dir: str) -> None:
        ...

    def upload_file(self, local_file: Path, remote_file: str):
        ...

    def clean_storage_for_trigger_id(self, trigger_id: str, *, confirm_flag_for_production: bool = False):
        assert self._storage_service_path is not None
        if self._mode == Environment.PRODUCTION:
            if not confirm_flag_for_production:
                raise PermissionError("Tried cleaning *PRODUCTION* folder with no permission")
        ...

    def get_stored_services_list(self) -> List[str]:
        ...

    def does_trigger_exists(self, trigger_id: str) -> bool:
        ...

    def get_trigger_ids_in_stored_service(self, stored_service: str) -> List[str]:
        ...