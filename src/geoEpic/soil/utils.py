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
