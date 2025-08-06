from geoEpic.gee.initialize import ee_Initialize
from geoEpic.gee import CompositeCollection


class AgEra:
    @staticmethod
    def fetch(lat, lon):
        """
        This method leverages a predefined GEE CompositeCollection to extract
        data at specific coordinates.

        Args:
            lat (float): The latitude of the point of interest.
            lon (float): The longitude of the point of interest.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the extracted data.
        """
        
        collection = CompositeCollection("src/geoEpic/assets/gee_examples/hls.yml")
        return collection.extract([[lon, lat]])

if __name__ == "__main__":
    test_lat = 35.9768
    test_long = -90.1399

    dly = AgEra.fetch(test_lat, test_long)
    print(f"The output for {test_lat} and {test_long} is \n {dly}")