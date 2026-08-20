"""Bright-object (cloud) detection on Sentinel-2 true-colour imagery.

Clouds are both *bright* and *spectrally flat*: they reflect red, green and blue
almost equally, whereas bright ground features (sand, bare soil, rooftops) keep a
colour cast. Thresholding brightness alone floods the mask with desert, so the
detector requires both a high brightness and a low spread across the three
channels. Thresholds are expressed in surface reflectance rather than raw DN, so
they stay meaningful across scenes.
"""

from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np
from shapely.geometry import Polygon

# Reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE. Both live in
# MTD_MSIL2A.xml; the offset is 0 for processing baselines before 04.00.
DEFAULT_QUANTIFICATION_VALUE = 10_000
DEFAULT_ADD_OFFSET = -1_000

BRIGHTNESS_THRESHOLD = 0.28
SPREAD_THRESHOLD = 0.055
MIN_AREA_PIXELS = 100
MORPH_KERNEL_SIZE = 5
CONTOUR_SIMPLIFY_EPSILON = 2.0


@dataclass
class Detection:
    polygon_pixels: Polygon
    area_pixels: float
    mean_brightness: float


def to_reflectance(
        digital_numbers: np.ndarray,
        quantification_value: int = DEFAULT_QUANTIFICATION_VALUE,
        add_offset: int = DEFAULT_ADD_OFFSET
) -> np.ndarray:
    # Cast before offsetting: the offset is negative and the input is unsigned.
    reflectance = (digital_numbers.astype(np.float32) + add_offset) / quantification_value
    return np.clip(reflectance, 0.0, None)


def detect_bright_objects(
        rgb_reflectance: np.ndarray,
        brightness_threshold: float = BRIGHTNESS_THRESHOLD,
        spread_threshold: float = SPREAD_THRESHOLD,
        min_area_pixels: int = MIN_AREA_PIXELS,
        morph_kernel_size: int = MORPH_KERNEL_SIZE
) -> Tuple[np.ndarray, List[Detection]]:
    if rgb_reflectance.ndim != 3 or rgb_reflectance.shape[2] != 3:
        raise ValueError(f"Expected an (H, W, 3) RGB array, got {rgb_reflectance.shape}")

    brightness = rgb_reflectance.mean(axis=2)
    spread = rgb_reflectance.max(axis=2) - rgb_reflectance.min(axis=2)
    # Tiles are only partly filled, and nodata is spectrally flat like cloud, so
    # exclude it explicitly rather than relying on the brightness test alone.
    is_valid = rgb_reflectance.max(axis=2) > 0

    mask = (is_valid & (brightness > brightness_threshold) & (spread < spread_threshold)).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    detections = _extract_detections(mask, brightness, min_area_pixels)
    return mask, detections


def _extract_detections(mask: np.ndarray, brightness: np.ndarray, min_area_pixels: int) -> List[Detection]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area_pixels:
            continue

        simplified = cv2.approxPolyDP(contour, CONTOUR_SIMPLIFY_EPSILON, True).reshape(-1, 2)
        if len(simplified) < 3:
            continue

        polygon = Polygon(simplified)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty:
            continue

        detections.append(Detection(
            polygon_pixels=polygon,
            area_pixels=area,
            mean_brightness=_mean_brightness_in_contour(contour, brightness)
        ))

    detections.sort(key=lambda detection: detection.area_pixels, reverse=True)
    return detections


def _mean_brightness_in_contour(contour: np.ndarray, brightness: np.ndarray) -> float:
    x, y, width, height = cv2.boundingRect(contour)
    contour_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(contour_mask, [contour - (x, y)], -1, 1, thickness=cv2.FILLED)
    return float(brightness[y: y + height, x: x + width][contour_mask.astype(bool)].mean())
