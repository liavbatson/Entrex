import json
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import rasterio
from affine import Affine
from loguru import logger
from rasterio.enums import Resampling
from shapely.affinity import affine_transform
from shapely.geometry import mapping

from hazut_hakol.algo.geo_utils.crs_projection import utm_to_geo
from hazut_hakol.apio.data_interfaces import MetadataFetcher, DataFetcher
from hazut_hakol.apio.data_interfaces.asset_sender import AssetSender
from hazut_hakol.apio.data_storage.data_storage_azure import DataStorageAzureNode
from hazut_hakol.core.classes.barak import Sweep
from hazut_hakol.core.utils import Environment
from projects.algo_projects.heimdall.cloud_detection.cloud_detector import (
    Detection,
    detect_bright_objects,
    to_reflectance,
)
from projects.core.etsc_interface import ETS_Interface, ETS_ConsumerInterface

MASK_FILENAME = "cloud_mask.png"
DETECTIONS_FILENAME = "cloud_detections.geojson"
ASSET_NAME = "cloud_mask"
# A full 10980x10980x3 tile is ~720MB in memory; decimating keeps the prototype
# interactive and costs little, since clouds are far larger than a few pixels.
DOWNSAMPLE_FACTOR = 4

IMAGES_CONTAINER = DataStorageAzureNode.AZURE_STORAGE_IMAGES_CONTAINER.value


def azure_stream_path(sweep: Sweep) -> str:
    return f"/vsiaz/{IMAGES_CONTAINER.container_name}/{sweep.image_path_in_azure}"


def azure_gdal_env() -> rasterio.Env:
    # Lets GDAL fetch byte ranges straight out of blob storage, so a decimated
    # read only transfers the overview level it needs.
    return rasterio.Env(
        AZURE_STORAGE_CONNECTION_STRING=IMAGES_CONTAINER.connection_string,
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        VSI_CACHE="TRUE",
        VSI_CACHE_SIZE=str(64 * 1024 * 1024)
    )


def read_rgb_decimated(image_path, downsample_factor: int) -> Tuple[np.ndarray, Affine, str]:
    with rasterio.open(image_path) as dataset:
        if dataset.count < 3:
            raise ValueError(f"Expected a 3-band RGB image, got {dataset.count} band(s) in {image_path}")

        out_height = dataset.height // downsample_factor
        out_width = dataset.width // downsample_factor
        bands = dataset.read(
            indexes=(1, 2, 3),
            out_shape=(3, out_height, out_width),
            resampling=Resampling.average
        )
        # Rescale the geotransform to match the decimated grid.
        pixel_to_crs = dataset.transform * dataset.transform.scale(
            dataset.width / out_width,
            dataset.height / out_height
        )
        crs = f"EPSG:{dataset.crs.to_epsg()}"

    return np.transpose(bands, (1, 2, 0)), pixel_to_crs, crs


def detections_to_geojson(detections: List[Detection], pixel_to_crs: Affine, crs: str) -> dict:
    # shapely wants (a, b, d, e, xoff, yoff); rasterio's Affine exposes (a, b, c, d, e, f).
    affine_coefficients = [
        pixel_to_crs.a, pixel_to_crs.b,
        pixel_to_crs.d, pixel_to_crs.e,
        pixel_to_crs.c, pixel_to_crs.f
    ]

    features = []
    for detection in detections:
        polygon_in_crs = affine_transform(detection.polygon_pixels, affine_coefficients)
        polygon_geo = utm_to_geo(polygon_in_crs, utm_crs=crs)
        features.append({
            "type": "Feature",
            "geometry": mapping(polygon_geo),
            "properties": {
                "area_pixels": detection.area_pixels,
                "mean_brightness": detection.mean_brightness
            }
        })

    return {"type": "FeatureCollection", "features": features}


class CloudDetectionTaskor(ETS_Interface):
    @classmethod
    def setup_taskor(cls, mode: Environment):
        super().setup_taskor(mode=mode)
        cls._metadata_fetcher = MetadataFetcher(mode=mode)
        cls._data_fetcher = DataFetcher(mode=mode)

    def extract(self):
        self._sweep = self._metadata_fetcher.fetch_sweeps([self._trigger_id])[0]
        self._image_path = self._stream_path_or_download()

    def _stream_path_or_download(self):
        # Streaming only pays off when the image carries overviews; without them
        # a decimated read still pulls every tile, so downloading in bulk wins.
        stream_path = azure_stream_path(self._sweep)
        try:
            with azure_gdal_env(), rasterio.open(stream_path) as dataset:
                has_overviews = bool(dataset.overviews(1))
            if has_overviews:
                logger.info(f"Streaming overviews from {stream_path}")
                return stream_path
            logger.warning(f"{stream_path} has no overviews, downloading the full image instead")
        except Exception as error:
            logger.warning(f"Cannot stream {stream_path} ({error}), downloading the full image instead")

        download_paths = self._data_fetcher.download_sweeps(sweeps=[self._sweep], output_dir=self._tmp_storage)
        return download_paths[self._sweep.sweep_gid]

    def transform(self):
        with azure_gdal_env():
            rgb_digital_numbers, pixel_to_crs, crs = read_rgb_decimated(self._image_path, DOWNSAMPLE_FACTOR)
        reflectance = to_reflectance(rgb_digital_numbers)

        self._mask, self._detections = detect_bright_objects(reflectance)
        self._geojson = detections_to_geojson(self._detections, pixel_to_crs, crs)
        self._coverage_fraction = float(self._mask.mean())

        logger.info(
            f"{self._sweep.sweep_gid}: {len(self._detections)} cloud region(s), "
            f"{self._coverage_fraction:.1%} of the scene"
        )

    def save(self):
        self._asset_sender = AssetSender(mode=self._mode, sweep=self._sweep, asset_name=ASSET_NAME)

        mask_local_path = self._tmp_storage / MASK_FILENAME
        cv2.imwrite(str(mask_local_path), self._mask * 255)

        detections_local_path = self._tmp_storage / DETECTIONS_FILENAME
        with open(detections_local_path, "w") as detections_file:
            json.dump(self._geojson, detections_file, indent=4)

        for local_path in (mask_local_path, detections_local_path):
            self._asset_sender.send_single_asset(local_path)


class CloudDetectionTaskorConsumer(ETS_ConsumerInterface):
    def __init__(self, mode: Environment):
        super().__init__(mode=mode)
        self._metadata_fetcher = MetadataFetcher(mode=mode)
        self._data_fetcher = DataFetcher(mode=mode)

    def consume_sweep_result(self, sweep_gid: str, output_dir: str) -> str:
        # Assets are sent next to the source image, so they are read back by
        # filename relative to the sweep rather than from a per-taskor service.
        sweep = self._metadata_fetcher.fetch_sweeps([sweep_gid])[0]
        download_paths = self._data_fetcher.download_sweep_asset_by_filename(
            sweep=sweep,
            output_dir=Path(output_dir),
            asset_filename=DETECTIONS_FILENAME
        )
        return download_paths[sweep_gid]
