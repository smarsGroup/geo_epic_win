import os
import subprocess
from geoEpic.utils import find_nearest, raster_to_dataframe
    
def get_ssurgo_mukeys(coords, ssurgo_map, files_dir):
    ssurgo = raster_to_dataframe(ssurgo_map)
    soil_list = [int(f.split('.')[0]) for f in os.listdir(files_dir)]
    ssurgo = ssurgo[ssurgo['band_1'].isin(soil_list)]
    inds = find_nearest(coords, ssurgo[['lon', 'lat']].values)
    soil_ids = (ssurgo['band_1'].values)[inds]
    return soil_ids


def write_soil_file(soil_df, outdir, header = None, template_orig = None):
    if template_orig is not None:
        template = template_orig.copy()
    else:
        with open(f'{os.path.dirname(__file__)}/template.sol', 'r') as file:
            template = file.readlines()

    if header is None: header = soil_df.iloc[0]
    mukey = int(header['mukey'])
    with open(os.path.join(outdir, f"{mukey}.SOL"), 'w+') as file:
        soil_layer_key = soil_df[soil_df['mukey'] == mukey]
        soil_layer_key = soil_layer_key.sort_values(by = ['Layer_depth'])
        len_cols = len(soil_layer_key)
        
        # Generate first three lines of the file
        template[0] = f"ID: {mukey}\n"
        template[1] = '{:8.3f}{:8.3f}'.format(header['albedo'], header['hydgrp_conv']) + template[1][16:]
        template[2] = '{:8.3f}'.format(len_cols + 1) + template[2][8:]
        
        # Generate lines for each row in soil_layer_key dataframe
        vals = (soil_layer_key.iloc[:, 2:21].values).T
        len_rows = len(vals) 
        for i in range(len_rows):
            template[3 + i] = ''.join([f'{val:8.3f}' for val in vals[i]]) + '\n'
    
        # Fill remaining lines with padding
        padding = ['{:8.3f}'.format(0) for _ in range(23)]
        for i in range(len_rows + 3, 45):
            template[i] = ''.join(padding[:len_cols]) + '\n'
        
        file.writelines(template)