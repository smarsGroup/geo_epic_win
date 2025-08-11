from shapely.geometry import Point
from geoEpic.io import SOL

class SSURGO:
    """
    Class for retrieving a soil from Soil Data Access based on latitude and longitude.

    Args:
        lat(float)
        lon(float)
    """

    @staticmethod
    def fetch(lat, lon):
        # Point expects longitude as first parameter and latitude as second
        point = Point(lon, lat)
        
        # convert to WKT format
        point_wkt_format = point.wkt

        return SOL.from_sda(point_wkt_format)

if __name__ == "__main__":
    print(SSURGO.fetch(35.9768, -90.1399).layers_df)

