from shapely.geometry import Point
from geoEpic.io import SOL

class SSURGO:
    def fetch( lat, lon):
        # Point expects longitude as first parameter and latitude as second
        point = Point(lon, lat)
        # convert to WKT format
        point_wkt_format = point.wkt

        print(SOL.from_sda(point_wkt_format).layers_df)\
        return SOL.from_sda(point_wkt_format)

if __name__ == "__main__":
    SSURGO.fetch(35.9768, -90.1399)

