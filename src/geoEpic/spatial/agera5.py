from geoEpic.gee.initialize import ee_Initialize
from geoEpic.gee import CompositeCollection
import os
from geoEpic.io import DLY
import pandas as pd 


class AgEra5:
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
        current_dir = os.path.dirname(__file__)
        yml_path = os.path.join(current_dir, "..", "assets", "gee_examples", "daily_weather.yml")
        collection = CompositeCollection(yml_path)
        dly =  collection.extract([[lon, lat]])
        # print(dly)
        dly['Date'] = pd.to_datetime(dly['Date'])
        dly['year'] = dly['Date'].dt.year
        dly['month'] = dly['Date'].dt.month
        dly['day'] = dly['Date'].dt.day
        return DLY(dly)

if __name__ == "__main__":
    test_lat = 35.9768
    test_long = -90.1399

    dly = AgEra.fetch(test_lat, test_long)
    print(f"The output for {test_lat} and {test_long} is \n {dly}")