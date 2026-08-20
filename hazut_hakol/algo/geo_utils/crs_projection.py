from typing import Union, Tuple

import numpy as np
from pyproj import Transformer
from shapely import Polygon, MultiPolygon, Point
from shapely.geometry.base import BaseGeometry

_initiated_transformers = {}


def geo_to_utm(points: Union[Point, Polygon, MultiPolygon, np.array], utm_crs: str = None):
    if utm_crs is None:
        utm_crs = estimate_best_utm_crs_from_geo(points)
    transformer = _initialize_geo_to_utm_transformer(utm_crs=utm_crs)
    if isinstance(points, (Polygon, MultiPolygon)):
        return _convert_crs_geometry(points, transformer)
    else:
        return _convert_crs_points(points, transformer)


def utm_to_geo(points: Union[Point, Polygon, MultiPolygon, np.array], utm_crs: str = None):
    transformer = _initialize_utm_to_geo_transformer(utm_crs=utm_crs)
    if isinstance(points, (Polygon, MultiPolygon)):
        return _convert_crs_geometry(points, transformer)
    else:
        return _convert_crs_points(points, transformer)


def estimate_best_utm_crs_from_geo(geo_object: Union[Tuple[int, int], BaseGeometry, np.ndarray]) -> str:
    if isinstance(geo_object, Tuple):
        geometry: BaseGeometry = Point(geo_object[0], geo_object[1])
    elif isinstance(geo_object, np.ndarray):
        if geo_object.ndim == 3:
            if geo_object.shape[2] == 2:
                geometry: BaseGeometry = Point(geo_object.mean(axis=(0, 1)))
            elif geo_object.shape[0] == 2:
                geometry: BaseGeometry = Point(geo_object.mean(axis=(1, 2)))
            else:
                raise NotImplementedError(f"np.ndarray shape is not expected {geo_object.shape}")
        else:
            raise NotImplementedError(f"np.ndarray shape is not expected {geo_object.shape}")
    else:
        geometry: BaseGeometry = geo_object

    centroid = geometry.centroid
    latitude = centroid.y
    longitude = centroid.x
    utm_zone = _get_utm_zone_number(longitude=longitude, latitude=latitude)
    crs_code = f"EPSG:{utm_zone}"
    return crs_code


def _get_utm_zone_number(longitude: np.ndarray, latitude: np.ndarray) -> int:
    zone_number = int((longitude + 180) / 6) + 1
    base_code = 32600 if latitude > 0 else 32700
    return base_code + zone_number


def _initialize_geo_to_utm_transformer(utm_crs: str) -> Transformer:
    crs_code = int(utm_crs.strip("EPSG:"))
    transformer_key = (4326, crs_code)
    if transformer_key not in _initiated_transformers:
        _initiated_transformers[transformer_key] = Transformer.from_crs(*transformer_key, always_xy=True)
    return _initiated_transformers[transformer_key]


def _initialize_utm_to_geo_transformer(utm_crs: str) -> Transformer:
    crs_code = utm_crs.strip("EPSG:")
    transformer_key = (crs_code, 4326)
    if transformer_key not in _initiated_transformers:
        _initiated_transformers[transformer_key] = Transformer.from_crs(*transformer_key, always_xy=True)
    return _initiated_transformers[transformer_key]


def _convert_crs_points(points, transformer):
    if isinstance(points, Point):
        return Point(transformer.transform(points.x, points.y))
    points = np.asarray(points)
    converted_points_flipped = transformer.transform(points[..., 0], points[..., 1])
    return np.asarray(converted_points_flipped).T


def _convert_crs_geometry(geometry, transformer):
    if isinstance(geometry, MultiPolygon):
        result = []
        for polygon in geometry.geoms:
            transformed_polygon = _convert_crs_geometry(polygon, transformer)
            result.append(transformed_polygon)
        return MultiPolygon(result)

    elif isinstance(geometry, Polygon):
        coords_list = list(geometry.exterior.coords)
        coords_array = np.array(coords_list)

        transformed_coords = _convert_crs_points(coords_array, transformer)
        return Polygon(transformed_coords)
    else:
        raise ValueError("Unsupported geometry type. Expected Polygon or MultiPolygon")
