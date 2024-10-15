import os
import argparse
import numpy as np
import pandas as pd
from epic_lib.io import ConfigParser

# Fetch the base directory
parser = argparse.ArgumentParser(description="EPIC workspace")
parser.add_argument("-c", "--config", default= "./config.yml", help="Path to the configuration file")
args = parser.parse_args()

curr_dir = os.getcwd()
config = ConfigParser(args.config)

info_df = pd.read_csv(config['Processed_Info'])

with open(f'./ieSite.DAT', 'w') as ofile:
    fmt = '%8d    "./sites/%d.sit"'
    np.savetxt(ofile, info_df[['FieldID', 'FieldID']].values, fmt=fmt)

with open(f'./ieSllist.DAT', 'w') as ofile:
    fmt = '%8d    "./soils/%d.SOL"'
    np.savetxt(ofile, info_df[['FieldID', 'soil_id']].values, fmt=fmt)

if 'dly' not in info_df.columns:
    info_df['dly'] = info_df['FieldID'].values 


with open(f'./ieWedlst.DAT', 'w') as ofile:
    fmt = '%8d    "./Daily/%d.DLY"'
    np.savetxt(ofile, info_df[['FieldID', 'dly']].values, fmt=fmt)

with open(f'./ieWealst.DAT', 'w') as ofile:
    fmt = '%8d    "./Monthly/%d.INP"   %.2f   %.2f  NB            XXXX'
    np.savetxt(ofile, info_df[['FieldID', 'dly', 'x', 'y']].values, fmt=fmt)

with open(f'./ieOplist.DAT', 'w') as ofile:
    fmt = '%8d    "./opc/%s.OPC"'
    np.savetxt(ofile, info_df[['FieldID', 'opc']].values, fmt=fmt)