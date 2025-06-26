import os
import re
from geoEpic.utils import GeoInterface


class DEM:
    def __init__(self, datasource):
        if os.path.exists(datasource):
            self._initialise_for_path(datasource)
        else:
            self._initialise_for_open_source(datasource)

    def _initialise_for_path(self, datasource):
        try:
            self.g = GeoInterface(datasource)
            self._mode = "path"
        except ValueError as e:
            raise ValueError(f"GeoInterface failed to initialise {datasource} due to {e}") from e

    def fetch(self, lat, lon):
        if self._mode == "path":
            return self._fetch_for_path(lat, lon)
        elif self._mode == "open_source":
            self._fetch_for_open_source(lat, lon)

    def _fetch_for_path(self, lat, lon):
        pd_series = self.g.lookup(lat, lon)
        
        pattern = re.compile(r'^band_\d+$')
        matching_columns_mask = pd_series.index.str.match(pattern)

        band_series = pd_series[matching_columns_mask]
        
        return band_series

    def _fetch_for_open_source(self, lat, lon):
        pass


if __name__ == "__main__":
    dem = DEM("/home/sachinv/GeoEPIC/SRTM_1km_US_project.tif")
    print(dem.fetch(35.9768, -90.1399))