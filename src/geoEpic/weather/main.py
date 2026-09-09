"""
Daily weather lookup helpers used by ``download_daily.py`` (ported from geo-epic).
"""
import os
import pandas as pd
from .daymet import get_dly, get_daymet_data
from geoEpic.io import DLY
from geoEpic.utils import GeoInterface


class DailyWeather:
    """Daymet-based daily weather; ``get`` returns (DLY, daymet_id) online or a cached DLY offline."""

    def __init__(self, path, start_date, end_date, offline=False):
        self.path = path
        self.start_date = start_date
        self.end_date = end_date
        self.offline = offline
        self.lookup = GeoInterface(os.path.join(path, 'climate_grid.tif'))

    def get_daymet_id(self, lat, lon):
        return int(self.lookup.lookup(lat, lon)['band_1'])

    def get(self, lat, lon):
        daymet_id = self.get_daymet_id(lat, lon)
        if not self.offline:
            return get_dly(lat, lon, self.start_date, self.end_date), daymet_id
        return DLY.load(os.path.join(self.path, 'Daily', str(daymet_id)))


class DailyWeather2(DailyWeather):
    """Daymet merged with NLDAS wind speed from ``<path>/NLDAS_csv/<nldas_id>.csv``."""

    def __init__(self, path, start_date, end_date, offline=False):
        super().__init__(path, start_date, end_date, offline)
        self.nldas_lookup = GeoInterface(os.path.join(path, 'nldas_grid.tif'))

    def get(self, lat, lon):
        daymet_id = self.get_daymet_id(lat, lon)
        if self.offline:
            return DLY.load(os.path.join(self.path, 'Daily', str(daymet_id)))
        nldas_id = int(self.nldas_lookup.lookup(lat, lon)['band_1'].item())
        nldas_df = pd.read_csv(os.path.join(self.path, 'NLDAS_csv', f'{nldas_id}.csv'))
        nldas_df.columns = ['date', 'ws']
        daymet = get_daymet_data(lat, lon, self.start_date, self.end_date)
        daymet['date'] = pd.to_datetime(daymet['date'])
        nldas_df['date'] = pd.to_datetime(nldas_df['date'])
        daymet = daymet.merge(nldas_df, on='date', how='inner')
        return DLY(daymet), daymet_id
