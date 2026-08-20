"""Turn a Sentinel-2 reflectance GeoTIFF into a plain 8-bit image you can open anywhere.

Sentinel-2 L2A stores reflectance as DN = reflectance * 10000 + 1000, so a normal
scene only occupies roughly DN 1500-5000 out of uint16's 0-65535. A viewer that
maps the full range linearly therefore shows an almost flat grey rectangle. This
rescales the range the data actually uses into 0-255 and writes a PNG.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
import rasterio

DEFAULT_MAX_DIMENSION = 2000
DEFAULT_STRETCH_PERCENTILES = (2.0, 98.0)


def read_decimated_rgb(image_path: Path, max_dimension: int) -> np.ndarray:
    with rasterio.open(image_path) as dataset:
        if dataset.count < 3:
            raise ValueError(f"Expected a 3-band RGB image, got {dataset.count} band(s)")

        scale = max(1, max(dataset.height, dataset.width) // max_dimension)
        bands = dataset.read(
            indexes=(1, 2, 3),
            out_shape=(3, dataset.height // scale, dataset.width // scale)
        )
    return np.transpose(bands, (1, 2, 0))


def stretch_to_uint8(rgb: np.ndarray, percentiles: tuple) -> np.ndarray:
    # Nodata is stored as 0 and would drag the low end of the stretch down.
    is_valid = rgb.max(axis=2) > 0
    if not is_valid.any():
        raise ValueError("Image contains no valid pixels")

    low, high = np.percentile(rgb[is_valid], percentiles)
    if high <= low:
        raise ValueError(f"Degenerate stretch range: {low}..{high}")

    scaled = np.clip((rgb.astype(np.float32) - low) / (high - low), 0.0, 1.0)
    scaled[~is_valid] = 0.0
    return (scaled * 255).astype(np.uint8)


def make_quicklook(image_path: Path, output_path: Path, max_dimension: int, percentiles: tuple) -> None:
    rgb = read_decimated_rgb(image_path, max_dimension)
    quicklook = stretch_to_uint8(rgb, percentiles)
    cv2.imwrite(str(output_path), cv2.cvtColor(quicklook, cv2.COLOR_RGB2BGR))
    print(f"Wrote {output_path} ({quicklook.shape[1]}x{quicklook.shape[0]})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write a viewable 8-bit PNG from a Sentinel-2 GeoTIFF")
    parser.add_argument("--input_image", "-i", required=True, help="Path to the Sentinel RGB GeoTIFF")
    parser.add_argument("--output_image", "-o", help="Output PNG path (defaults to <input>_quicklook.png)")
    parser.add_argument("--max_dimension", "-d", type=int, default=DEFAULT_MAX_DIMENSION,
                        help="Longest side of the output image in pixels")
    args = parser.parse_args()

    input_image = Path(args.input_image)
    output_image = Path(args.output_image) if args.output_image else \
        input_image.with_name(f"{input_image.stem}_quicklook.png")

    make_quicklook(input_image, output_image, args.max_dimension, DEFAULT_STRETCH_PERCENTILES)
