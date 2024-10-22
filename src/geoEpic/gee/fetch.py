import argparse
import os
import sys
from core import *
from geoEpic.utils import parallel_executor
import geopandas as gpd
from time import time


def fetch_data(config_file, location, output_path):
    collection = CompositeCollection(config_file)
    df = collection.extract([location])
    df.to_csv(f'{output_path}', index = False)

def fetch_data_wrapper(row):

    name = row['name']
    output_dir = row['out']
    if os.path.exists(f'{output_dir}/{name}.csv'):
        return
    collection = CompositeCollection(row['config_file'])
    df = collection. extract(row['geometry'])
    df.to_csv(f'{output_dir}/{name}.csv', index = False)
        
    
def fetch_list(config_file, input_data, output_dir):
    """
    Fetches soil data based on the input type which could be coordinates, a CSV file, or a shapefile.

    Args:
        input_data (str): Could be latitude and longitude as a string, path to a CSV file, or path to a shapefile.
        output_dir (str): Directory or file path where the output should be saved.
        raw (bool): Whether to save the results as raw CSV or .SOL file.
    """

    if input_data.endswith('.csv'):
        locations = pd.read_csv(input_data)
        if 'SiteID' in locations.columns:
            locations['name'] = locations['SiteID']
        elif 'FieldID' in locations.columns:
            locations['name'] = locations['FieldID']
        else:
            locations['name'] = list(range(len(locations)))
        locations['out'] = output_dir
        locations['config_file'] = config_file
        locations['geometry'] = locations.apply(lambda x: [[x['lon'], x['lat'] ]], axis = 1)
        locations_ls = locations.to_dict('records')
        parallel_executor(fetch_data_wrapper, locations_ls, max_workers=40)

    elif input_data.endswith('.shp'):
        shapefile = gpd.read_file(input_data)
        if 'SiteID' in shapefile.columns:
            shapefile['name'] = shapefile['SiteID']
        elif 'FieldID' in shapefile.columns:
            shapefile['name'] = shapefile['FieldID']
        else:
            shapefile['name'] = list(range(len(shapefile)))
        shapefile['out'] = output_dir
        shapefile['config_file'] = config_file
        shapefile_ls = shapefile.to_dict('records')
        parallel_executor(fetch_data_wrapper, shapefile_ls, max_workers=40)
    
    else:
        print('Input file type not Supported')
        
def main():
    parser = argparse.ArgumentParser(description="Fetch and output data from GEE")
    parser.add_argument('config_file', help='Path to the configuration file')
    parser.add_argument('--fetch', metavar='INPUT', nargs='+', help='Latitude and longitude as two floats, or a file path')
    parser.add_argument('--out', default='./', dest='output_path', help='Output directory or file path for the fetched data')

    args = parser.parse_args()
    
    try:
        if len(args.fetch) == 2:
            latitude, longitude = map(float, args.fetch)
            fetch_data(args.config_file, [longitude, latitude ], args.output_path)
            print(f'Data saved in {args.output_path}')
        else:
            fetch_list(args.config_file, args.fetch[0], args.output_path)
    except Exception as e:
        print(e)
        parser.print_help()


if __name__ == '__main__':
    main()