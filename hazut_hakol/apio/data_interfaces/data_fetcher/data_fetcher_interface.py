from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from hazut_hakol.core.classes.barak import Sweep


class DataFetcherInterface(ABC):
    @abstractmethod
    def download_sweep(self, sweep: Sweep, output_dir: Path) -> dict:
        ...

    @abstractmethod
    def download_sweeps(self, sweeps: List[Sweep], output_dir: Path, raise_on_missing: bool = False) -> dict:
        ...

    @abstractmethod
    def download_sweep_asset_by_filename(self,
                                         sweep: Sweep,
                                         output_dir: Path,
                                         asset_filename: str,
                                         raise_on_missing: bool = False
    ):
        ...

    @abstractmethod
    def download_sweeps_asset_by_filename(self,
                                          sweeps: List[Sweep],
                                          output_dir: Path,
                                          asset_filename: str,
                                          raise_on_missing: bool = False
    ):
        ...

    @abstractmethod
    def download_grids(self, sweeps: List[Sweep], output_dir: Path, raise_on_missing: bool = False):
        ...