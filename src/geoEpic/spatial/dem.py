import os
import re
import ee
from geoEpic.utils import GeoInterface
from geoEpic.gee import ee_Initialize

import math

class DEM:
    """
    Digital Elevation Module Class that fetches elevation and slope for both open source resource and file existing on the system.
    Args:
        datasource(str): Value can be a path of the file location stored locally or an open source image.
    """

    def __new__(cls, datasource=None):
        """
        Factory method that returns different instances based on the datasource type.
        """
        if datasource is None:
            # Return a StaticDEM instance for static fetch methods
            return StaticDEM()
        elif os.path.exists(datasource):
            return LocalDEM(datasource)
        else:
            return RemoteDEM(datasource)

    @staticmethod
    def fetch(lat, lon, source="GLO-30"):
        """
        Static method to fetch elevation and slope from open source DEM data.

        Args: 
            lat(float): latitude
            lon(float): longitude
            source(str): DEM source - "GLO-30", "ASTER", or "SRTM"

        Returns:
            tuple: (elevation, slope)
        """
        ee_Initialize()
        
        # Define your point using the lat, lon variables
        point = ee.Geometry.Point(lon, lat)

        # Select DEM source
        if source == "ASTER":
            dem = ee.Image('ASTER/GDEM/ASTGTM')
        elif source == "SRTM":
            dem = ee.Image('USGS/SRTMGL1_003')
        else:  # Default to GLO-30
            dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').select('DEM').median()

        # Compute slope
        slope_deg = ee.Terrain.slope(dem)
        # Convert slope from degrees to mm⁻¹ (rise/run, unitless, but often called "mm⁻¹" in soil science)
        # Slope (mm⁻¹) = tan(slope_deg in radians)
        slope_rad = slope_deg.multiply(math.pi / 180)
        slope_mm1 = slope_rad.tan()

        # Combine bands and sample
        combo = dem.addBands([slope_deg, slope_mm1]).rename(['elevation', 'slope_deg', 'slope_mm1'])
        ee_result = combo.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=30
        ).getInfo()

        elevation = ee_result.get('elevation')
        slope = ee_result.get('slope_mm1')
        return elevation, slope


class StaticDEM:
    """
    Static DEM class for static method access.
    """
    
    def fetch(self, lat, lon, source="GLO-30"):
        """
        Instance method that delegates to the static method.
        """
        return DEM.fetch(lat, lon, source)


class LocalDEM:
    """
    Local DEM class for file-based DEM data.
    """
    
    def __init__(self, datasource):
        """
        Initialisation function for DEM class if the argument passed is a file existing on the system already.
        """
        self.g = GeoInterface(datasource)

    def fetch(self, lat, lon):
        """
        Fetch elevation and slope specifically for when the value passed during class initialisation is a file location.
        """
        pd_series = self.g.lookup(lat, lon)
        
        pattern = re.compile(r'^band_\d+$')
        matching_columns_mask = pd_series.index.str.match(pattern)

        band_series = pd_series[matching_columns_mask]
        
        return band_series


class RemoteDEM:
    """
    Remote DEM class for open source DEM data.
    """
    
    def __init__(self, datasource):
        """
        Initialisation function for DEM class if the argument passed is an open source image.
        """
        ee_Initialize()
        self._datasource = datasource
        self._dem = ee.Image(self._datasource)

    def fetch(self, lat, lon):
        """
        Fetch elevation and slope specifically for when the value passed during class initialisation is an open source image.
        """
        # Define your point using the lat, lon variables
        point = ee.Geometry.Point(lon, lat)

        # Load DEM and compute slope
        dem = ee.Image(self._datasource)
        slope_deg = ee.Terrain.slope(dem)
        # Convert slope from degrees to mm⁻¹ (rise/run, unitless, but often called "mm⁻¹" in soil science)
        # Slope (mm⁻¹) = tan(slope_deg in radians)
        slope_rad = slope_deg.multiply(math.pi / 180)
        slope_mm1 = slope_rad.tan()

        # Combine bands and sample
        combo = dem.addBands([slope_deg, slope_mm1]).rename(['elevation', 'slope_deg', 'slope_mm1'])
        ee_result = combo.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=30
        ).getInfo()

        elevation = ee_result.get('elevation')
        slope = ee_result.get('slope_mm1')
        return elevation, slope


if __name__ == "__main__":
    """
    Run either one
    First one is for file already existing on system.
    Second is for open source image.
    """

    # dem_srtm_path = DEM("/home/sachinv/GeoEPIC/SRTM_1km_US_project.tif")
    # print(dem_srtm_path.fetch(35.9768, -90.1399))

    # dem_srtm = DEM("USGS/SRTMGL1_003")
    # elevation, slope = dem_srtm.fetch(35.9768, -90.1399)
    # print(f"elevation and slope are .....({elevation},{slope})")