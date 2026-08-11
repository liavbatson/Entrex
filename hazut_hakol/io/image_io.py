import os
import subprocess
import uuid
from pathlib import Path
from typing import Union, Optional

import numpy as np
from loguru import logger

from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.entrex_base_errors import EntrexDataError


class ImageLoaderError(EntrexDataError):
    pass


try:
    from osgeo import gdal
    gdal.UseExceptions()
    import rasterio
    HAS_GDAL = True
except ImportError:
    logger.warning("No gdal found...")
    import cv2
    HAS_GDAL = False

UINT8_DYNAMIC_RANGE = 8
open_images = {}


def get_image_stats(input_img: Union[str, Path, np.ndarray]):
    if isinstance(input_img, np.ndarray):
        channels = input_img.shape[2] if len(input_img.shape) == 3 else 1
        min_input_value, max_input_value = input_img.min(), input_img.max()
        return channels, min_input_value, max_input_value
    elif isinstance(input_img, Path):
        input_img = str(input_img)

    ds = gdal.Open(input_img, gdal.GA_ReadOnly)
    channels = ds.RasterCount
    band = ds.GetRasterBand(1)
    stats = band.GetStatistics(False, True)

    min_input_value, max_input_value = stats[0], stats[1]
    return channels, min_input_value, max_input_value


def read_barak_image(
        input_file: Union[str, Path],
        barak_sweep: Sweep,
        dim_ordering_channels_last: bool = True,
        *,
        y_offset: int = 0,
        x_offset: int = 0,
        win_y_size: Optional[int] = None,
        win_x_size: Optional[int] = None,
        keep_open: bool = False
) -> np.ndarray:
    img = read_image(
        input_file=input_file,
        dim_ordering_channels_last=dim_ordering_channels_last,
        win_y_size=win_y_size if win_y_size else barak_sweep.height,
        win_x_size=win_x_size if win_y_size else barak_sweep.width,
        y_offset=y_offset,
        x_offset=x_offset,
        normalize_dynamic_range_to_uint8=True,
        keep_open=keep_open
    )
    return img


def read_image(
        input_file: Union[str, Path],
        y_offset: int = 0,
        x_offset: int = 0,
        win_y_size: Optional[int] = None,
        win_x_size: Optional[int] = None,
        dim_ordering_channels_last: bool = True,
        *,
        normalize_dynamic_range_to_uint8: bool = False,
        keep_open: bool = False
) -> np.ndarray:
    if HAS_GDAL:
        if isinstance(input_file, gdal.Dataset):
            dataset = input_file
        elif input_file in open_images:
            dataset = open_images[input_file]
        else:
            dataset = gdal.Open(str(input_file), gdal.GA_ReadOnly)

        if win_y_size is None:
            win_y_size = int(dataset.RasterYSize)
        if win_x_size is None:
            win_x_size = int(dataset.RasterXSize)

        y_offset = int(y_offset)
        x_offset = int(x_offset)

        win_y_size = int(min(dataset.RasterYSize - y_offset, win_y_size))
        win_x_size = int(min(dataset.RasterXSize - x_offset, win_x_size))

        try:
            img = dataset.ReadAsArray(x_offset, y_offset, win_x_size, win_y_size)
        except RuntimeError as e:
            raise ImageLoaderError(f"Corrupt image file provided by hoshen. {e}")

        if dim_ordering_channels_last and dataset.RasterCount >= 3:
            img = np.transpose(img, (1, 2, 0))

        if normalize_dynamic_range_to_uint8:
            band = dataset.GetRasterBand(1)
            try:
                dynamic_range = int(band.GetMetadataItem('NBITS', 'IMAGE_STRUCTURE'))
                img = img // (2 ** (dynamic_range - UINT8_DYNAMIC_RANGE))
                img = img.astype(np.uint8)
            except:
                stats = band.GetStatistics(0, 0)
                if stats[0] == stats[1] == 0.0:
                    img_max = img.max()
                else:
                    img_max = stats[1]

                if img_max > 255:
                    img = np.round(255 * (img / img_max)).astype(np.uint8)

        if keep_open:
            open_images[input_file] = dataset
        else:
            dataset = None

    else:
        img = cv2.imread(input_file, cv2.IMREAD_UNCHANGED)
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB if img.shape[2] == 3 else cv2.COLOR_BGRA2RGBA)

        if win_y_size is None:
            win_y_size = int(img.shape[0])
        if win_x_size is None:
            win_x_size = img(img.shape[1])

        y_offset = int(y_offset)
        x_offset = int(x_offset)

        win_y_size = int(min(img.shape[0] - y_offset, win_y_size))
        win_x_size = int(min(img.shape[1] - x_offset, win_x_size))

        img = img[y_offset: y_offset + win_y_size, x_offset: x_offset + win_y_size]

    return img


def clean_open_images():
    open_images.clear()


def cli_tiff_to_jp2(
        tiff_path: Path,
        jp2_path: Path,
        block_size: int = 512,
        n_levels: int = 4,
        org_gen_tlm: int = 6
) -> Path:
    command = f'gdal_translate --config GDAL_CACHEMAX 1000 -strict -of JP2KAK -co RTProgression=yes ' \
              f'-co Clevels={n_levels} -co LAYERS=10 -co BLOCKXSIZE={block_size} -co BLOCKYSIZE={block_size} ' \
              f'-co Cprecincts="{{256,256}},{{256,256}},{{128,128}}" -co Corder=RPCL -co ORGgen_plt=yes ' \
              f'-co QUALITY=100 -co ORGtparts=R -co ORGgen_tlm={org_gen_tlm} {str(tiff_path)} {str(jp2_path)}'
    env = os.environ.copy()
    env["PATH"] = "/usr/local/bin:" + env["PATH"]
    jp2_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    if result.stderr:
        logger.warning(result.stderr.decode("utf-8"))

    return jp2_path


def cli_jp2_to_tif(
        jp2_path: Union[str, Path],
        tiff_path: Union[str, Path]
) -> str:
    command = f'gdal_translate {str(jp2_path)} {str(tiff_path)}'
    env = os.environ.copy()
    env["PATH"] = "/usr/local/bin:" + env["PATH"]
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    if result.stderr:
        logger.warning(result.stderr.decode("utf-8"))

    return jp2_path


def save_jp2_image(image: np.ndarray, file_name: Union[str, Path],
                   create_directories_if_needed: bool = True) -> None:
    jp2_path = Path(str(file_name))
    tiff_path = jp2_path.parent / f"tmp_{uuid.uuid4()}.tiff"
    save_tiff_image(image, tiff_path, create_directories_if_needed=create_directories_if_needed)
    cli_tiff_to_jp2(tiff_path, jp2_path)
    os.remove(tiff_path)


def save_tiff_image(
        image: np.ndarray,
        file_name: Path,
        y_offset: int = 0,
        x_offset: int = 0,
        compression="LZW",
        total_height: int = None,
        total_width: int = None,
        create_directories_if_needed: bool = True,
        keep_open: bool = False
):
    if image.dtype == bool:
        image = image.astype(dtype=np.uint8)
    if image.ndim == 3:
        if image.shape[0] <= 10:
            image = np.moveaxis(image, 0, -1)
        height, width, bands = image.shape
    else:
        height, width, bands = image.shape[0], image.shape[1], 1
        image = image[..., np.newaxis]

    dtype_map = {
        np.uint8: gdal.GDT_Byte,
        np.int8: gdal.GDT_Byte,
        np.uint16: gdal.GDT_UInt16,
        np.int16: gdal.GDT_UInt16,
        np.uint32: gdal.GDT_UInt32,
        np.int32: gdal.GDT_UInt32,
        np.float32: gdal.GDT_Float32,
        np.float64: gdal.GDT_Float64
    }

    gdal_dtype = dtype_map.get(image.dtype, gdal.GDT_Byte)
    driver = gdal.GetDriverByName('GTiff')
    options = [f'COMPRESS={compression}', 'TILED=YES', 'BLOCKXSIZE=512', 'BLOCKYSIZE=512']

    if file_name in open_images:
        dataset = open_images[file_name]
    elif file_name.exists():
        dataset = gdal.Open(str(file_name), gdal.GA_Update)
    else:
        if create_directories_if_needed:
            file_name.parent.mkdir(parents=True, exist_ok=True)
        total_height = total_height if total_height else height
        total_width = total_width if total_height else width
        dataset = driver.Create(str(file_name), total_width, total_height, bands, gdal_dtype, options=options)

    img_to_write = np.transpose(image, (2, 0, 1))
    dataset.WriteArray(img_to_write, yoff=y_offset, xoff=x_offset)
    dataset.FlushCache()

    if keep_open:
        open_images[file_name] = dataset
    else:
        dataset = None
