import json
from pathlib import Path
from typing import List, Tuple

from loguru import logger
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from hazut_hakol.algo.geo_utils.crs_projection import estimate_best_utm_crs_from_geo, geo_to_utm
from hazut_hakol.algo.geo_utils.polygon_set_cover import union_all
from hazut_hakol.apio.data_interfaces import DataFetcher, MetadataFetcher
from hazut_hakol.apio.data_interfaces.asset_sender import AssetSender
from hazut_hakol.core.utils import Environment
from projects.algo_projects.heimdall.cloud_detection.cloud_detection_taskor import (
    CloudDetectionTaskor,
    CloudDetectionTaskorConsumer,
)
from projects.core.etsc_interface import ETS_Interface, ETS_ConsumerInterface

CLEAR_AREA_FILENAME = "clear_area.geojson"
STATS_FILENAME = "clear_area_stats.json"
ASSET_NAME = "clear_area"
SQUARE_METRES_PER_SQUARE_KM = 1e6


def as_multipolygon(geometry: BaseGeometry) -> MultiPolygon:
    if geometry.is_empty:
        return MultiPolygon()
    if isinstance(geometry, Polygon):
        return MultiPolygon([geometry])
    if isinstance(geometry, MultiPolygon):
        return geometry
    # A difference can come back as a GeometryCollection; only the polygonal
    # parts describe area, so lines and points from touching edges are dropped.
    polygons = [part for part in geometry.geoms if isinstance(part, Polygon) and not part.is_empty]
    return MultiPolygon(polygons)


def polygon_areas_km2(polygons: MultiPolygon, utm_crs: str) -> List[float]:
    # Areas must be measured in a projected CRS; square degrees are meaningless.
    if polygons.is_empty:
        return []
    projected = geo_to_utm(polygons, utm_crs)
    return [part.area / SQUARE_METRES_PER_SQUARE_KM for part in projected.geoms]


class ClearAreaTaskor(ETS_Interface):
    _predecessors = [CloudDetectionTaskor]

    @classmethod
    def setup_taskor(cls, mode: Environment):
        super().setup_taskor(mode=mode)
        cls._metadata_fetcher = MetadataFetcher(mode=mode)
        cls._cloud_detection_consumer = CloudDetectionTaskorConsumer(mode=mode)

    def extract(self):
        self._sweep = self._metadata_fetcher.fetch_sweeps([self._trigger_id])[0]
        detections_path = self._cloud_detection_consumer.consume_sweep_result(
            sweep_gid=self._trigger_id,
            output_dir=str(self._tmp_storage)
        )
        with open(detections_path) as detections_file:
            self._detections = json.load(detections_file)

    def transform(self):
        trace = self._sweep.trace
        if trace is None:
            raise ValueError(f"Sweep {self._sweep.sweep_gid} has no trace to subtract clouds from")
        if not trace.is_valid:
            trace = make_valid(trace)

        cloud_polygons = [shape(feature["geometry"]) for feature in self._detections["features"]]
        clouds = union_all(cloud_polygons) if cloud_polygons else MultiPolygon()

        self._clear_area, self._stats = self._measure(trace, clouds)
        logger.info(
            f"{self._sweep.sweep_gid}: {self._stats['clear_fraction']:.1%} clear "
            f"({self._stats['clear_area_km2']:.1f} of {self._stats['trace_area_km2']:.1f} km2), "
            f"{len(self._clear_area.geoms)} clear region(s)"
        )

    def _measure(self, trace: BaseGeometry, clouds: BaseGeometry) -> Tuple[MultiPolygon, dict]:
        utm_crs = estimate_best_utm_crs_from_geo(trace)
        trace_area_km2 = geo_to_utm(trace, utm_crs).area / SQUARE_METRES_PER_SQUARE_KM

        clear_area = as_multipolygon(trace.difference(clouds))
        areas_km2 = polygon_areas_km2(clear_area, utm_crs)

        # Keep the polygons and their areas in one order, largest first.
        ordered = sorted(zip(clear_area.geoms, areas_km2), key=lambda pair: pair[1], reverse=True)
        clear_area = MultiPolygon([polygon for polygon, _ in ordered])
        areas_km2 = [area for _, area in ordered]

        clear_area_km2 = sum(areas_km2)
        stats = {
            "sweep_gid": self._sweep.sweep_gid,
            "capture_time": self._sweep.capture_time.isoformat() if self._sweep.capture_time else None,
            "trace_area_km2": trace_area_km2,
            "clear_area_km2": clear_area_km2,
            # Derived from the difference rather than the cloud union, so cloud
            # polygons spilling outside the trace do not inflate it.
            "cloud_area_km2": max(trace_area_km2 - clear_area_km2, 0.0),
            "clear_fraction": clear_area_km2 / trace_area_km2 if trace_area_km2 else 0.0,
            "clear_region_count": len(areas_km2),
            "largest_clear_area_km2": areas_km2[0] if areas_km2 else 0.0,
            "cloud_region_count": len(self._detections["features"])
        }
        self._clear_areas_km2 = areas_km2
        return clear_area, stats

    def save(self):
        self._asset_sender = AssetSender(mode=self._mode, sweep=self._sweep, asset_name=ASSET_NAME)

        clear_area_path = self._tmp_storage / CLEAR_AREA_FILENAME
        with open(clear_area_path, "w") as clear_area_file:
            json.dump(self._to_geojson(), clear_area_file, indent=4)

        stats_path = self._tmp_storage / STATS_FILENAME
        with open(stats_path, "w") as stats_file:
            json.dump(self._stats, stats_file, indent=4)

        for local_path in (clear_area_path, stats_path):
            self._asset_sender.send_single_asset(local_path)

    def _to_geojson(self) -> dict:
        features = [
            {
                "type": "Feature",
                "geometry": mapping(polygon),
                "properties": {"area_km2": area_km2}
            }
            for polygon, area_km2 in zip(self._clear_area.geoms, self._clear_areas_km2)
        ]
        return {"type": "FeatureCollection", "features": features}


class ClearAreaTaskorConsumer(ETS_ConsumerInterface):
    def __init__(self, mode: Environment):
        super().__init__(mode=mode)
        self._metadata_fetcher = MetadataFetcher(mode=mode)
        self._data_fetcher = DataFetcher(mode=mode)

    def consume_sweep_result(self, sweep_gid: str, output_dir: str) -> str:
        sweep = self._metadata_fetcher.fetch_sweeps([sweep_gid])[0]
        download_paths = self._data_fetcher.download_sweep_asset_by_filename(
            sweep=sweep,
            output_dir=Path(output_dir),
            asset_filename=CLEAR_AREA_FILENAME
        )
        return download_paths[sweep_gid]
