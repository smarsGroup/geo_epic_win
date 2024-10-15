import os
import argparse
import pandas as pd
from geoEpic.io import ConfigParser
from geoEpic.utils import parallel_executor
from geoEpic.utils.misc import import_function
from glob import glob

# Fetch the base directory
parser = argparse.ArgumentParser(description="EPIC workspace")
parser.add_argument("-c", "--config", default= "./config.yml", help="Path to the configuration file")
args = parser.parse_args()

curr_dir = os.getcwd()

config = ConfigParser(args.config)

base_dir = curr_dir

process_outputs = import_function(config["Process_outputs"])

output_dir = config['output_dir']
if output_dir is None:
    raise ValueError("Output directory not specified in configuration.")

if not os.path.exists(output_dir):
    raise Exception(f"Output folder not found: {output_dir}")
    

info = pd.read_csv('info.csv')

opc_files = glob(f'{config["opc_dir"]}/*.OPC')
present = [(os.path.basename(f).split('.'))[0] for f in opc_files]
info = info.loc[(info['opc'].astype(str)).isin(present)]

info_ls = list(info['FieldID'])

total = len(info_ls)
min_ind, max_ind = config["Range"]
min_ind, max_ind = int(min_ind*total), int(max_ind*total)
print('Total Field Sites:', max_ind-min_ind)

def wrap(fid):
    try:
        process_outputs(fid, base_dir)
    except FileNotFoundError:
        pass

os.chdir(output_dir)
wrap(info_ls[min_ind])
parallel_executor(wrap, info_ls[min_ind: max_ind], max_workers = config["num_of_workers"], timeout = config["timeout"])

