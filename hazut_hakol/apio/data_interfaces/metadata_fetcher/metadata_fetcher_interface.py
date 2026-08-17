from abc import ABC, abstractmethod
from datetime import datetime
from math import inf
from typing import List, Union

from shapely import Polygon, MultiPolygon

from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.utils import Sensor, ImagingTechnique


class MetadataFetcherInterface(ABC):
    @abstractmethod
    def fetch_sweep(self, sweep_gid: str) -> Sweep:
        ...

    @abstractmethod
    def fetch_sweeps(self, sweep_gids: List[str]) -> List[Sweep]:
        ...

    @abstractmethod
    def fetch_sweeps_in_capture_time_range_and_multipolygon(self,
                                                            polygon: Union[Polygon, MultiPolygon],
                                                            start_date: datetime,
                                                            end_date: datetime,
                                                            sensors: List[Sensor],
                                                            imaging_technique: ImagingTechnique = None,
                                                            sweep_gids_ignore_list: List[str] = [],
                                                            sorties_ignore_list: List[str] = [],
                                                            limit_amount_sweeps: int = inf
                                                            ) -> List[Sweep]:
        ...

    @abstractmethod
    def fetch_sortie(self, sortie: str, sweep_gids_ignore_list: List[str] = [],
                     limit_amount_sweeps: int = inf) -> List[Sweep]:
        ...

    @abstractmethod
    def fetch_sweeps_starts_with(self, sweep_gid_prefix: str) -> List[Sweep]:
        ...

    @abstractmethod
    def fetch_sweeps_ends_with(self, sweep_gid_suffix: str) -> List[Sweep]:
        ...