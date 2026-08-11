from dataclasses import dataclass
from typing import Tuple

import numpy as np

from hazut_hakol.algo.geo_utils.crs_projection import geo_to_utm, estimate_best_utm_crs_from_geo, utm_to_geo

GEO_CRS = "EPSG:4326"


@dataclass
class Grid:
    grid_array: np.ndarray
    crs: str
    grid_resolution: Tuple[float, float]

    def __post_init__(self):
        if self.crs == GEO_CRS:
            if np.abs(self.grid_array[:, :, 0].max()) >= 180 or np.abs(self.grid_array[:, :, 1].mean()) >= 90:
                self.grid_array = self.grid_array / 3600

    def to_utm(self, crs: str = None):
        if self.crs.startswith("EPSG:326") or self.crs.startswith("EPSG:327"):
            return self
        elif self.crs != GEO_CRS:
            raise NotImplementedError()

        if crs is None:
            crs = estimate_best_utm_crs_from_geo(self.grid_array)

        utm_grid_array = geo_to_utm(
            points=self.grid_array.reshape((-1, 2)),
            utm_crs=crs
        ).reshape(self.grid_array.shape)

        utm_grid = Grid(
            grid_array=utm_grid_array,
            crs=crs,
            grid_resolution=self.grid_resolution
        )
        return utm_grid

    def to_geo(self):
        if self.crs == GEO_CRS:
            return self

        geo_grid_array = utm_to_geo(
            points=self.grid_array.reshape((-1, 2)),
            utm_crs=self.crs
        ).reshape(self.grid_array.shape)
        geo_grid = Grid(
            grid_array=geo_grid_array,
            crs="EPSG:4326",
            grid_resolution=self.grid_resolution
        )
        return geo_grid
