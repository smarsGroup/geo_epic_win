import os
import re
import ee
from geoEpic.utils import GeoInterface
from geoEpic.gee import ee_Initialize

class DEM:
    """
    Digital Elevation Module Class that fetches elevation and slope for both open source resource and file existing on the system.
    Args:
        datasource(str): Value can be a path of the file location stored locally or an open source image.
    """

    def __init__(self, datasource):
        """
        Separating the initialisation of DEM class based on the file path while calling the class.
        """
        
        if os.path.exists(datasource):
            self._initialise_for_path(datasource)
        else:
            self._initialise_for_open_source(datasource)

    def _initialise_for_path(self, datasource):
        """
        Initialisation function for DEM class if the argument passed is a file existing on the system already.

        _mode is a variable which stores "path" as value that is used for fetching data for this particular use case.
        """
        
        try:
            print("Initialising GeoInterface...")
            self.g = GeoInterface(datasource)
            self._mode = "path"
            print("GeoInterface Initialised")
        except ValueError as e:
            raise ValueError(f"GeoInterface failed to initialise {datasource} due to {e}") from e

    def _initialise_for_open_source(self, datasource):
        """
        Initialisation function for DEM class if the argument passed is an open source image.

        _mode is a variable which stores "open_source" as value that is used for fetching data for this particular use case.
        """

        self._mode = "open_source"
        ee_Initialize()
        self._datasource = datasource
        self._dem = ee.Image(self._datasource)

    def fetch(self, lat, lon):
        """
        Function exposed to fetch elevation and slope.

        Args: 
            latitude(float)
            longitude(float)

        Output:
            elevation(float)
            slope(float)
        """

        if self._mode == "path":
            return self._fetch_for_path(lat, lon)
        elif self._mode == "open_source":
            return self._fetch_for_open_source(lat, lon)

    def _fetch_for_path(self, lat, lon):
        """
        Fetch elevation and slope specifically for when the value passed during class initialisation is a file location.
        """

        pd_series = self.g.lookup(lat, lon)
        
        pattern = re.compile(r'^band_\d+$')
        matching_columns_mask = pd_series.index.str.match(pattern)

        band_series = pd_series[matching_columns_mask]
        
        return band_series

    def _fetch_for_open_source(self, lat, lon):
        """
        Fetch elevation and slope specifically for when the value passed during class initialisation is an open source image.
        """

        point = ee.Geometry.Point([lon, lat])
        
        elevation = self._dem.select('elevation')
        slope = ee.Terrain.slope(self._dem)

        combined_image = elevation.addBands(slope)
        feature = combined_image.sample(point, scale=30).first()
        data = feature.getInfo()['properties']

        elevation = data.get('elevation')
        slope = data.get('slope')
        return elevation, slope


if __name__ == "__main__":
    """
    Run either one
    First one is for file already existing on system.
    Second is for open source image.
    """

    # dem_srtm_path = DEM("/home/sachinv/GeoEPIC/SRTM_1km_US_project.tif")
    # print(dem_srtm_path.fetch(35.9768, -90.1399))

    dem_srtm = DEM("USGS/SRTMGL1_003")
    elevation, slope = dem_srtm.fetch(35.9768, -90.1399)
    print(f"elevation and slope are .....({elevation},{slope})")