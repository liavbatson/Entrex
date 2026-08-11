import importlib
from functools import lru_cache


@lru_cache(maxsize=None)
def module_lazy_load(module_path: str):
    try:
        return importlib.import_module(module_path)
    except ImportError as e:
        raise RuntimeError(f"Module {module_path} is required but not installed") from e


def get_gdal():
    return module_lazy_load("osgeo.gdal")
