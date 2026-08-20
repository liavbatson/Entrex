import argparse
import json
from pathlib import Path
import rasterio
from datetime import datetime
import xml.etree.ElementTree as ET

from rasterio.enums import Resampling
from shapely.geometry import Polygon

from hazut_hakol.core.utils import ImagingTechnique, Sensor

BLUE_SUFFIX = "B02_10m.jp2"
GREEN_SUFFIX = "B03_10m.jp2"
RED_SUFFIX = "B04_10m.jp2"
PRODUCT_XML_NAME = "MTD_MSIL2A.xml"
TILE_XML_GLOB = "MTD_TL.xml"
TARGET_RESOLUTION = "10"

# Written as a cloud-optimised GeoTIFF: internal tiling plus overviews let a
# consumer pull one reduced-resolution level over the network instead of the
# whole 700MB tile. DEFLATE rather than ZSTD so any GDAL build can read it.
COG_BLOCK_SIZE = 512
COG_COMPRESSION = "deflate"
OVERVIEW_FACTORS = [2, 4, 8, 16]


class SentinelPreProcess:
    def __init__(self, input_dir: str, output_dir: str):
        self._input_dir = Path(input_dir)
        self._output_dir = Path(output_dir)

    def extract_metadata_from_xml(self) -> dict:
        sweep_metadata = {
            "sensor": Sensor.SENTINEL.value,
            "imaging_technique": ImagingTechnique.EO.value
        }

        sweep_metadata.update(self._extract_product_metadata())
        sweep_metadata.update(self._extract_tile_metadata())

        return sweep_metadata

    def _extract_product_metadata(self) -> dict:
        xml_metadata_file = self._input_dir / PRODUCT_XML_NAME
        root = ET.parse(xml_metadata_file).getroot()

        metadata = {}
        for elem in root.iter():
            if "PRODUCT_URI" in elem.tag and elem.text is not None:
                # Sweep gid
                metadata["sweep_gid"] = elem.text.split('.')[0]
            if elem.tag.endswith("Datatake") and "datatakeIdentifier" in elem.attrib:
                # Sortie id: shared by every tile captured in the same satellite pass
                metadata["sortie_id"] = elem.attrib["datatakeIdentifier"]
            if elem.tag.endswith("EXT_POS_LIST") and elem.text is not None:
                metadata["trace"] = self._parse_footprint(elem.text)

        return metadata

    def _extract_tile_metadata(self) -> dict:
        tile_xml_files = list(self._input_dir.glob(TILE_XML_GLOB))
        if not tile_xml_files:
            raise FileNotFoundError(f"Could not find MTD_TL.xml under {self._input_dir}")

        root = ET.parse(tile_xml_files[0]).getroot()

        metadata = {}
        for elem in root.iter():
            if elem.tag.endswith("Size") and elem.attrib.get("resolution") == TARGET_RESOLUTION:
                height = elem.find("./NROWS")
                width = elem.find("./NCOLS")
                if height is not None and width is not None:
                    metadata["height"] = int(height.text)
                    metadata["width"] = int(width.text)
            if elem.tag.endswith("SENSING_TIME") and elem.text is not None:
                # The trailing timestamp in PRODUCT_URI is the processing time, not
                # the acquisition time; SENSING_TIME is when the tile was imaged.
                metadata["capture_time"] = self._parse_sensing_time(elem.text)

        missing = {"height", "width", "capture_time"} - set(metadata)
        if missing:
            raise ValueError(f"Could not find {sorted(missing)} in {tile_xml_files[0]}")

        return metadata

    @staticmethod
    def _parse_sensing_time(sensing_time: str) -> str:
        capture_time = datetime.strptime(sensing_time.strip(), "%Y-%m-%dT%H:%M:%S.%fZ")
        return capture_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _parse_footprint(ext_pos_list: str) -> Polygon:
        values = [float(value) for value in ext_pos_list.split()]
        # EXT_POS_LIST is a flat "lat lon lat lon ..." list; Polygon expects (lon, lat) pairs
        coordinates = [(values[i + 1], values[i]) for i in range(0, len(values), 2)]
        return Polygon(coordinates)

    def create_single_image(self, sweep_gid: str):
        red_image = next(self._input_dir.glob(f"*{RED_SUFFIX}"))
        green_image = next(self._input_dir.glob(f"*{GREEN_SUFFIX}"))
        blue_image = next(self._input_dir.glob(f"*{BLUE_SUFFIX}"))

        with rasterio.open(red_image) as red:
            red_data = red.read(1)
            profile = red.profile
        with rasterio.open(green_image) as green:
            green_data = green.read(1)
        with rasterio.open(blue_image) as blue:
            blue_data = blue.read(1)

        profile.update(
            driver="GTiff",
            count=3,
            dtype=red_data.dtype,
            tiled=True,
            blockxsize=COG_BLOCK_SIZE,
            blockysize=COG_BLOCK_SIZE,
            compress=COG_COMPRESSION,
            predictor=2,
            BIGTIFF="IF_SAFER"
        )

        output_path = self._output_dir / f"{sweep_gid}.tif"
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(red_data, 1)
            dst.write(green_data, 2)
            dst.write(blue_data, 3)
            dst.build_overviews(OVERVIEW_FACTORS, Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")

    def create_metadata_file(self, metadata: dict):
        metadata = {**metadata, "trace": metadata["trace"].wkt}

        output_path = self._output_dir / "metadata.json"
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=4)

    def run_preprocess(self):
        metadata = self.extract_metadata_from_xml()
        self.create_single_image(metadata["sweep_gid"])
        self.create_metadata_file(metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel preprocess, get folder of raw sentinel data and create single image and metadata json file")
    parser.add_argument(
        "--input_dir",
        "-i",
        required=True,
        help="Path to input_dir contains sentinel raw data"
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        required=True,
        help="Path to output_dir, will contains single image and metadata json file"
    )
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    preprocessor = SentinelPreProcess(args.input_dir, args.output_dir)
    preprocessor.run_preprocess()