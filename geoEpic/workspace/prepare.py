import os
import argparse
import pandas as pd
import subprocess
import geopandas as gpd
from geoEpic.io import ConfigParser
from geoEpic.soil import get_ssurgo_mukeys
from geoEpic.dispatcher import dispatch
import numpy as np

parser = argparse.ArgumentParser(description="EPIC workspace")
parser.add_argument("-c", "--config", default= "./config.yml", help="Path to the configuration file")
args = parser.parse_args()

curr_dir = os.getcwd()

config = ConfigParser(args.config)

env = os.environ.copy()
root_path = os.path.dirname(os.path.dirname(__file__))
env["PYTHONPATH"] = root_path + ":" + env.get("PYTHONPATH", "")

print("\nPreparing data for", config["EXPName"])

print("\nProcessing fields of interest")

file_path = config["Fields_of_Interest"]
file_extension = (file_path.split('.'))[-1]
# Read the input file
if file_extension == 'csv':
    info_df = pd.read_csv(file_path)
    lon_min, lat_min = np.floor(info_df['x'].min() * 1e5)/1e5, np.floor(info_df['y'].min() * 1e5)/1e5
    lon_max, lat_max = np.ceil(info_df['x'].max() * 1e5)/1e5, np.ceil(info_df['y'].max() * 1e5)/1e5
elif file_extension == 'shp':
    info_df = gpd.read_file(file_path)
    # Prepare Info for Run
    info_df = info_df.to_crs(epsg=4326); 
    lon_min, lat_min, lon_max, lat_max = info_df.total_bounds
    info_df = calc_centroids(info_df)
    info_df.drop(['geometry', 'centroid'], axis=1, inplace=True)
else:
    raise ValueError("Unsupported file format. Only CSV and shapefile formats are supported.")

columns = set(info_df.columns)
ID_names = set(['OBJECTID', 'CSBID', 'FieldID', 'FIELDID', 'OBID', 'RUNID', 'RunID'])
IDs = ID_names & columns
ID = next(iter(IDs), None)
if ID is None:
    raise Exception("FieldID column not Found")
info_df['FieldID'] = info_df[ID]
# if ID != 'FieldID':
# info_df.drop(list(IDs), axis=1, inplace=True)

rot_names = set(['OPC', 'opc', 'RotID', 'rotID'])
rots = rot_names & columns
rot = next(iter(rots), None)
if rot is None:
    print("Using FieldID for opc files")
    rot = 'FieldID'
if config["opc_prefix"] is None: 
    info_df['opc'] = info_df[rot].apply(lambda x: x)
else:
    info_df['opc'] = info_df[rot].apply(lambda x: f'{config["opc_prefix"]}_{x}')

# Read from config file
soil = config["soil"]
weather = config["weather"]
region_code = config["code"]
site = config["site"]

if (weather['offline']) and (not os.path.exists(weather["dir"] + '/climate_grid.tif')):
    dispatch('weather', 'download_daily', '', True)
else:
    # Download Nldas data 
    if not os.path.exists(weather["dir"] + '/NLDAS_csv'):
        start_date = weather["start_date"]
        end_date = weather["end_date"]
        dispatch('weather', 'windspeed', f'-s {start_date} -e {end_date} \
                      -o {weather["dir"]} -b {lat_min} {lat_max} {lon_min} {lon_max}', True)



# create soil files 
if soil['files_dir'] is None:
    dispatch('soil', 'process_gdb', f'-r {region_code} -gdb {soil["ssurgo_gdb"]}', True)
    soil_dir = os.path.dirname(soil["ssurgo_gdb"])
    config.update_config({
    'soil': {
        'files_dir': f'{soil_dir}/files'
    },
    'site': {
        'slope_length': f'./{soil_dir}/{region_code}_slopelen_1.csv'
    }
    })
    soil_dir += "/files"
else:
    soil_dir = soil['files_dir']


coords = info_df[['x', 'y']].values
ssurgo_map = soil["soil_map"]
info_df['soil_id'] = get_ssurgo_mukeys(coords, ssurgo_map, soil_dir) 
info_df.to_csv(curr_dir + '/info.csv', index = False)

# create site files
dispatch('sites', 'generate', f'-o {site["dir"]} -i {curr_dir + "/info.csv"}\
    -ele {site["elevation"]} -slope {site["slope"]} -sl {site["slope_length"]}', False)

config.update_config({'Processed_Info': f'{curr_dir}/info.csv'})
