import os
import math
import sys
from typing import Optional, Union

try:
    from osgeo import gdal
except ImportError:
    print("ERROR: Could not import gdal")

gdal.UseExceptions()


class IDFJP2Converter:
    TILE_SIZE = 512
    PRECINCT_SIZE = 256
    CODEBLOCK_SIZE = 64
    NUM_QUALITY_LAYERS = 10
    FIRST_LAYER_BITRATE = 0.03125
    PROGRESSION_ORDER = "RPCL"
    MAX_TILE_PARTS = 4096

    BIT_DEPTHS = {
        gdal.GDT_Byte: 8,
        gdal.GDT_UInt16: 16,
        gdal.GDT_Int16: 16,
        gdal.GDT_UInt32: 32,
        gdal.GDT_Int32: 32,
        gdal.GDT_Float32: 32,
        gdal.GDT_Float64: 64
    }

    def __init__(self, input_path: str, output_path: Optional[str] = None,
                 compression_ratio: Optional[float] = None):
        self.input_path = input_path
        self.output_path = output_path or self._generate_output_path()
        self.compression_ratio = compression_ratio
        self.src_ds = None
        self.driver = None

    def _generate_output_path(self) -> str:
        base = os.path.splitext(self.input_path)[0]
        return f"{base}.jp2"

    def _validate_input(self) -> None:
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input not found: {self.input_path}")

    def _validate_driver(self) -> None:
        self.driver = gdal.GetDriverByName("JP2KAK")
        if not self.driver:
            raise RuntimeError(
                "Kakadu encoder (JP2KAK) not available. "
                "Install GDAL with kakadu support for full IDF compliance."
            )

    def _open_source(self) -> None:
        self.src_ds = gdal.Open(self.input_path, gdal.GA_ReadOnly)
        if not self.src_ds:
            raise RuntimeError(f"Failed to open: {self.input_path}")

    def _get_image_properties(self) -> dict:
        datatype = self.src_ds.GetRasterBand(1).DataType
        return {
            'width': self.src_ds.RasterXSize,
            'height': self.src_ds.RasterYSize,
            'bands': self.src_ds.RasterCount,
            'datatype': datatype,
            'bit_depth': self.BIT_DEPTHS.get(datatype, 16)
        }

    def _calculate_resolution_levels(self, width: int, height: int) -> int:
        max_dim = max(width, height)
        if max_dim <= 512:
            return 1
        return math.ceil(math.log2(max_dim / 512.0)) + 1

    def _calculate_tile_size(self, width: int, height: int,
                             num_resolutions: int) -> int:
        tile_size = self.TILE_SIZE
        while True:
            tile_count = math.ceil(width / tile_size) * math.ceil(height / tile_size)
            tile_parts = tile_count * num_resolutions
            if tile_parts <= self.MAX_TILE_PARTS or tile_size >= max(width, height):
                return tile_size
            tile_size *= 2

    def _calculate_quality_rates(self, bit_depth: int) -> Optional[list]:
        if not self.compression_ratio:
            return None
        final_bitrate = bit_depth / self.compression_ratio
        if final_bitrate <= self.FIRST_LAYER_BITRATE:
            raise ValueError(
                f"Compression ratio {self.compression_ratio} too aggresive. "
                f"Final bitrate {final_bitrate:.4f} < {self.FIRST_LAYER_BITRATE}"
            )
        rates = []
        for i in range(self.NUM_QUALITY_LAYERS):
            if i == 0:
                rates.append(self.FIRST_LAYER_BITRATE)
            elif i == self.NUM_QUALITY_LAYERS - 1:
                rates.append(final_bitrate)
            else:
                factor = i / (self.NUM_QUALITY_LAYERS - 1)
                rate = self.FIRST_LAYER_BITRATE * (final_bitrate / self.FIRST_LAYER_BITRATE) ** factor
                rates.append(rate)
        return rates

    def _build_creation_options(self, num_resolutions: int, tile_size: int, quality_rates: Optional[list],
                                reversible: bool) -> list:
        options = [
            f"BLOCKXSIZE={tile_size}",
            f"BLOCKYSIZE={tile_size}",
            f"Clevels={num_resolutions - 1}",
            f"Clayers={self.NUM_QUALITY_LAYERS}",
            f"Cprecincts={{{self.PRECINCT_SIZE}, {self.PRECINCT_SIZE}}}",
            f"Cblk={{{self.CODEBLOCK_SIZE}, {self.CODEBLOCK_SIZE}}}",
            f"Corder={self.PROGRESSION_ORDER}"
            f"Creversible={'yes' if reversible else 'no'}",
            "ORGgen_tlm=2",
            "ORGgen_plt=yes",
            "Cuse_sop=no",
            "Cuse_eph=no"
        ]
        if quality_rates:
            rates_str = ",".join(f"{r:.6f}" for r in quality_rates)
            options.append(f"Qfactor={rates_str}")
        return options

    def _copy_geospatial_metadata(self, dst_ds: gdal.Dataset) -> None:
        geo_transform = self.src_ds.GetGeoTransform()
        if geo_transform != (0.0, 1.0, 0.0, 0.0, 0.0, 1.0):
            dst_ds.SetGeoTransform(geo_transform)

        projection = self.src_ds.GetProjection()
        if projection:
            dst_ds.SetProjection(projection)

    def _copy_band(self, src_band: gdal.Band, dst_band: gdal.Band,
                   width: int, height: int) -> None:
        chuck_size = 1024
        for y in range(0, height, chuck_size):
            rows = min(chuck_size, height - y)
            for x in range(0, width, chuck_size):
                cols = min(chuck_size, width - x)
                data = src_band.ReadAsArray(x, y, cols, rows)
                dst_band.WriteArray(data, x, y)
        nodata = src_band.GetNoDataValue()
        if nodata is not None:
            dst_band.SetNoDataValue(nodata)
        dst_band.SetColorInterpretation(src_band.GetColorInterpretation())

    def _copy_all_bands(self, dst_ds: gdal.Dataset, width: int, height: int) -> None:
        for i in range(1, self.src_ds.RasterCount + 1):
            self._copy_band(self.src_ds.GetRasterBand(i),
                            dst_ds.GetRasterBand(i), width, height)

    def _create_jp2(self, options: list, width: int, height: int,
                    bands: int, datatype: int) -> None:
        dst_ds = self.driver.Create(self.output_path, width, height, bands, datatype, options)
        if not dst_ds:
            raise RuntimeError("Failed to create JP2")

        self._copy_geospatial_metadata(dst_ds)
        self._copy_all_bands(dst_ds, width, height)
        dst_ds.FlushCache()
        dst_ds = None

    def _cleanup(self) -> None:
        self.src_ds = None

    def _cleanup_on_error(self) -> None:
        self._cleanup()
        if os.path.exists(self.output_path):
            try:
                os.remove(self.output_path)
            except:
                pass

    def convert(self, return_bytes: bool = False) -> Union[str, bytes]:
        try:
            self._validate_input()
            self._validate_driver()
            self._open_source()

            props = self._get_image_properties()
            num_resolutions = self._calculate_resolution_levels(props['width'],
                                                               props['height'])
            tile_size = self._calculate_tile_size(props['width'], props['height'],
                                                  num_resolutions)
            reversible = self.compression_ratio is None
            quality_rates = self._calculate_quality_rates(props['bit_depth'])

            options = self._build_creation_options(num_resolutions, tile_size,
                                                   quality_rates, reversible)
            self._create_jp2(options, props['width'], props['height'],
                             props['bands'], props['datatype'])
            self._cleanup()

            if return_bytes:
                with open(self.output_path, 'rb') as f:
                    return f.read()
            return self.output_path

        except Exception as e:
            self._cleanup_on_error()
            raise RuntimeError(f"Conversion failed: {e}")


def convert_tiff_to_idf_jp2(input_tiff: str,
                            output_jp2: Optional[str] = None,
                            compression_ratio: Optional[float] = None,
                            return_bytes: bool = False) -> Union[str, bytes]:
    converter = IDFJP2Converter(input_tiff, output_jp2, compression_ratio)
    return converter.convert(return_bytes)
