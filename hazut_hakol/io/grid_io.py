from pathlib import Path

import numpy as np
from loguru import logger
from tifffile import tifffile

from hazut_hakol.algo.geo_utils.crs_projection import geo_to_utm, estimate_best_utm_crs_from_geo
from hazut_hakol.core.classes.grid import Grid
from hazut_hakol.core.entrex_base_errors import EntrexDataError
from hazut_hakol.core.utils import Sensor


class GridLoaderError(EntrexDataError):
    pass


try:
    from osgeo import gdal
    HAS_GDAL = True
except ImportError:
    logger.warning("No gdal found...")
    HAS_GDAL = False

REQUIRED_GRID_DILATION = {
    Sensor.SENTINEL: True
}


def load_grid(grid_file: Path, sensor_for_dilation_check: Sensor) -> Grid:
    grid = _grid_to_array(grid_file)[:, :, :2]
    if np.any(np.isnan(grid)):
        raise GridLoaderError(
            f"Grid array of file {grid_file.name} contains nans, possible corrupt grid file in Hoshen."
        )
    grid_resolution = _get_grid_resolution(grid_file)
    if grid.shape == (2, 2, 2):
        grid_resolution = grid_resolution / 2
        grid = _expand_grid_2x2_to_3x3(grid)
    crs_code = _get_grid_crs(grid_file)

    if sensor_for_dilation_check is not None and sensor_for_dilation_check in REQUIRED_GRID_DILATION:
        if REQUIRED_GRID_DILATION[sensor_for_dilation_check]:
            grid = _expand_grid(grid)

    grid = Grid(
        grid_array=grid,
        crs=crs_code,
        grid_resolution=grid_resolution
    )
    return grid


def _get_grid_crs(grid_file):
    with tifffile.TiffFile(grid_file) as f:
        page = f.pages[0]
        crs_code = f"EPSG:{int(page.tags[47635].value[0])}"
    return crs_code


def _expand_grid(grid: np.ndarray) -> np.ndarray:
    new_grid = np.zeros((grid.shape[0] + 1, grid.shape[1] + 1, grid.shape[2]))
    col = (grid[:, -1] - grid[:, -2] + grid[:, -1])
    new_grid[:-1, :-1] = grid.copy()
    new_grid[:-1, -1] = col
    row = (new_grid[-2, :] - new_grid[-3, :] + new_grid[-2, :])
    new_grid[-1, :] = row
    return new_grid


def _grid_to_array(input_file, yoff=0, xoff=0, win_ysize=None, win_xsize=None, dtype='int32'):
    if HAS_GDAL:
        dataset = gdal.Open(str(input_file), gdal.GA_ReadOnly)
        if win_ysize is None:
            win_ysize = dataset.RasterYSize
        if win_xsize is None:
            win_xsize = dataset.RasterXSize

        grid = dataset.ReadAsArray(xoff, yoff, win_xsize, win_ysize)
        grid = np.transpose(grid, (1, 2, 0))
        try:
            gdal.Close(dataset)
        except AttributeError:
            del dataset
    else:
        grid = tifffile.imread(input_file)[:, :, :2]

    if grid.dtype in [np.uint32, np.uint16, np.uint8]:
        grid = np.frombuffer(bytes(grid), dtype=np.float32).reshape(grid.shape)

    return grid


def _get_grid_resolution(vis_grid_file):
    grid_vertical_resolution, grid_horizontal_resolution = 1, 1
    with tifffile.TiffFile(vis_grid_file) as tif:
        tags = tif.pages[0].tags.values()
        for tag in tags:
            if tag.name == "ModelPixelScaleTag":
                grid_horizontal_resolution = tag.value[0]
                grid_vertical_resolution = tag.value[1]
    return np.abs((grid_vertical_resolution, grid_horizontal_resolution))


def _expand_grid_2x2_3x3(grid):
    v00, v01 = grid[0, 0], grid[0, 1]
    v10, v11 = grid[1, 0], grid[1, 1]
    new_grid = np.zeros((3, 3, 2))
    for i in range(2):
        new_grid[0, 0, i] = v00[i]
        new_grid[0, 1, i] = (v00[i] + v01[i]) / 2
        new_grid[0, 2, i] = v01[i]
        new_grid[1, 0, i] = (v00[i] + v10[i]) / 2
        new_grid[1, 1, i] = (v00[i] + v01[i] + v10[i] + v11[i]) / 4
        new_grid[1, 2, i] = (v01[i] + v11[i]) / 2
        new_grid[2, 0, i] = v10[i]
        new_grid[2, 1, i] = (v10[i] + v11[i]) / 2
        new_grid[2, 2, i] = v11[i]

    return new_grid
