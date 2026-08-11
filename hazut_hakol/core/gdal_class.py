import importlib

GDAL_LIBRARIES = [
    "geopandas"
]


class GdalDependedClass:
    def __init__(self):
        self._check_gdal_installed()
        self._check_geopandas_installed()
        import geopandas
        self.gpd = geopandas
        from osgeo import gdal
        self.gdal = gdal

    def _check_gdal_installed(self):
        try:
            importlib.import_module('osgeo')
        except ImportError:
            raise ImportError(
                "GDAL is not installed. This class uses gdal methods, and hence requires environment with GDAL."
            )

    def _check_geopandas_installed(self):
        missing_libraries = []
        try:
            for library in GDAL_LIBRARIES:
                importlib.import_module(library)
        except ImportError:
            missing_libraries += library
        if len(missing_libraries):
            raise ImportError(
                f"GDAL libraries not installed but environment has GDAL. try: pip install {' '.join(missing_libraries)}"
            )