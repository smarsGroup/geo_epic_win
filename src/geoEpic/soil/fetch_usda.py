import pandas as pd
from sda import SoilDataAccess
from sol import *
import geopandas as gpd
import os
import argparse
from geoEpic.utils import parallel_executor

    
def fetch_data(mukey):
    """
    Process a single location (mukey or WKT) and save the results.

    Args:
        input_data (str): The input data representing either a mukey (int) or a WKT location (str).
        output_dir (str): Directory where the results will be saved.
        raw (bool): Whether to save the results as raw CSV or .SOL file.
    """
    global output_dir, raw
    file_name = f"{mukey}.csv" if raw else f"{mukey}.SOL"
    file_path = os.path.join(output_dir, file_name)
    if not os.path.exists(file_path):
        if raw:
            df = SoilDataAccess.fetch_properties(int(mukey)) 
            df.to_csv(file_path, index=False)
        else: 
            SOL.from_sda(int(mukey)).save(file_path)
    else:
        print(f"File {file_path} already exists, skipping.")
        

def fetch_list(input_data):
    """
    Fetches soil data based on the input type which could be coordinates, a CSV file, or a shapefile.

    Args:
        input_data (str): Could be latitude and longitude as a string, path to a CSV file, or path to a shapefile.
        output_dir (str): Directory or file path where the output should be saved.
        raw (bool): Whether to save the results as raw CSV or .SOL file.
    """
    if input_data.endswith('.csv'):
        locations = pd.read_csv(input_data)
        point_strings = [f"point({row.longitude} {row.latitude})" for _, row in locations.iterrows()]
        locations['sol'], _ = parallel_executor(SoilDataAccess.get_mukey, point_strings, return_value = True, method = 'Thread') #[SoilDataAccess.get_mukey(point) for point in point_strings]
        locations.to_csv(input_data, index = False)
    elif input_data.endswith('.shp'):
        locations = gpd.read_file(input_data)
        locations['centroid'] = locations.geometry.centroid
        point_strings = locations['centroid'].apply(lambda x: f'point({x.x} {x.y})')
        locations['sol'], _ = parallel_executor(SoilDataAccess.get_mukey, point_strings, return_value = True, method = 'Thread')
        locations.to_file(input_data, index = False)
    else: 
        raise TypeError('Input file type not Supported')

    print("Fetching files")
    mukeys = locations['sol'].unique()
    parallel_executor(fetch_data, list(mukeys), method = 'Thread')

        
def main():
    parser = argparse.ArgumentParser(description="Fetch and output data from USDA SSURGO")
    parser.add_argument('--fetch', metavar='INPUT', nargs='+', help='Latitude and longitude as two floats, or a file path')
    parser.add_argument('--out', default='./', dest='output_path', help='Output directory for the fetched data')
    parser.add_argument('--raw', action='store_true', help='Save results as raw CSV instead of .SOL file')

    args = parser.parse_args()

    global output_dir, raw
    output_dir = args.output_path
    raw = args.raw
    
    if len(args.fetch) == 2:
        latitude, longitude = map(float, args.fetch)
        wkt = f'point({longitude} {latitude})'
        mukey = SoilDataAccess.get_mukey(wkt)
        fetch_data(wkt)
    else:
        fetch_list(args.fetch[0])


if __name__ == '__main__':
    # mukey = 642029
    # soil_properties_df = SoilDataAccess.fetch_properties(mukey)
    # print(soil_properties_df)
    # soil_properties_df.to_csv('soil.csv', index = False)
    # write_soil_file(soil_properties_df, './')
    main()
