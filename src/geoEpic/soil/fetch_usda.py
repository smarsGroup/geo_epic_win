from utils import write_soil_file
import pandas as pd
from sda import SoilDataAccess
import geopandas as gpd
import os
import argparse
from geoEpic.utils import parallel_executor

    
def fetch_data(input_data, output_dir, raw):
    """
    Process a single location (mukey or WKT) and save the results.

    Args:
        input_data (str): The input data representing either a mukey (int) or a WKT location (str).
        output_dir (str): Directory where the results will be saved.
        raw (bool): Whether to save the results as raw CSV or .SOL file.
    """
    df = SoilDataAccess.fetch_properties(input_data)
    mukey = df['mukey'].iloc[0]
    
    if raw:
        csv_path = os.path.join(output_dir, f"{mukey}.csv")
        if not os.path.exists(csv_path):
            df.to_csv(csv_path, index=False)
        else:
            print(f"File {csv_path} already exists, skipping.")
    else:
        sol_path = os.path.join(output_dir, f"{mukey}.SOL")
        if not os.path.exists(sol_path):
           write_soil_file(df, output_dir)
        else:
            print(f"File {sol_path} already exists, skipping.")
        
        

def fetch_list(input_data, output_dir, raw):
    """
    Fetches soil data based on the input type which could be coordinates, a CSV file, or a shapefile.

    Args:
        input_data (str): Could be latitude and longitude as a string, path to a CSV file, or path to a shapefile.
        output_dir (str): Directory or file path where the output should be saved.
        raw (bool): Whether to save the results as raw CSV or .SOL file.
    """
    if input_data.endswith('.csv'):
        locations = pd.read_csv(input_data)
        point_strings = [f"point({row.latitude} {row.longitude})" for _, row in locations.iterrows()]
        parallel_executor(fetch_data, point_strings, output_dir, raw)
    elif input_data.endswith('.shp'):
        shapefile = gpd.read_file(input_data)
        shapefile['centroid'] = shapefile.geometry.centroid
        locations = shapefile['centroid'].apply(lambda x: f'point({x.x} {x.y})')
        parallel_executor(fetch_data, locations, output_dir, raw)
    else:
       fetch_data(input_data, output_dir, raw)
        
        
def main():
    parser = argparse.ArgumentParser(description="Fetch and output data from USDA SSURGO")
    parser.add_argument('--fetch', metavar='INPUT', nargs='+', help='Latitude and longitude as two floats, or a file path')
    parser.add_argument('--out', default='./', dest='output_path', help='Output directory or file path for the fetched data')
    parser.add_argument('--raw', action='store_true', help='Save results as raw CSV instead of .SOL file')

    args = parser.parse_args()
    
    if len(args.fetch) == 2:
        latitude, longitude = map(float, args.fetch)
        wkt = f'point({longitude} {latitude})'
        fetch_data(wkt, args.output_path, args.raw)
    else:
        fetch_list(args.fetch[0], args.output_path, args.raw)



if __name__ == '__main__':
    # mukey = 642029
    # soil_properties_df = SoilDataAccess.fetch_properties(mukey)
    # print(soil_properties_df)
    # soil_properties_df.to_csv('soil.csv', index = False)
    # write_soil_file(soil_properties_df, './')
    main()
