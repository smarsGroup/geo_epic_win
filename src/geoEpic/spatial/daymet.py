from geoEpic.weather.daymet import *

class Daymet:
    @staticmethod
    def fetch(lat: float, lon: float, start: str = None, end: str = None) -> DLY:
        """
        Wrapper to produce a DLY object using Daymet (+GridMET ws) for a last full-year window by default.
        """
        if start is None or end is None:
            year = datetime.utcnow().year - 1
            start = f"{year}-01-01"
            end = f"{year}-12-31"
        return get_dly(lat, lon, start, end)
