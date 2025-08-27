from geoEpic.weather.daymet import *
class Daymet:
    @staticmethod
    def fetch(lat: float, lon: float, start_date: str = None, end_date: str = None) -> DLY:
        """
        Wrapper to produce a DLY object using Daymet (+GridMET ws) for a last full-year window by default.
        """
        if start_date is None and end_date is None:
            start_date = "2020-01-01"
            end_date = "2020-12-31"
        elif start_date is None and end_date is not None:
            end_year = end_date[:4]
            start_date = f"{end_year}-01-01"
        elif start_date is not None and end_date is None:
            start_year = start_date[:4]
            end_date = f"{start_year}-12-31"
        return get_dly(lat, lon, start_date, end_date)
