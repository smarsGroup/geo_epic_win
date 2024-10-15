import os
import argparse
import pandas as pd
from geoEpic.io import ConfigParser
from geoEpic.utils import import_function
from glob import glob

# Fetch the base directory
parser = argparse.ArgumentParser(description="EPIC workspace")
parser.add_argument("-c", "--config", default= "./config.yml", help="Path to the configuration file")
args = parser.parse_args()

curr_dir = os.getcwd()

config = ConfigParser(args.config)

base_dir = curr_dir

plot = import_function(config['visualize'])
if plot is not None: 
    import geopandas as gpd    
    file_path = config["Fields_of_Interest"]
    exp_name = config["EXPName"]
    file_extension = (file_path.split('.'))[-1]
    if file_extension == 'shp':
        shp = gpd.read_file(file_path)
        shp['FieldID'] = shp['FieldID'].astype('int')
        plot(shp, exp_name)
    else:
        print('AOI has to be a shape file')