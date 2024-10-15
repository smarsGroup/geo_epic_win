import os
import numpy as np
import pandas as pd
from geoEpic.utils import parallel_executor
from geoEpic.utils import sample_raster_nearest
import argparse
import geopandas as gpd
from geoEpic.io import ConfigParser


parser = argparse.ArgumentParser(description="Generate Site files.")
parser.add_argument("-c", "--config", default= "./config.yml", help="Path to the configuration file")

# parser.add_argument("-o", "--out_dir", type=str, required=True, help="Output directory to save results.")
# parser.add_argument("-i", "--info_file", type=str, required=True, help="Path to the info file.")
# parser.add_argument("-ele", "--elevation", type=str, required=True, help="Path to the elevation.tif")
# parser.add_argument("-slope", "--slope", type=str, required=True, help="Path to the slope.tif")
# parser.add_argument("-sl", "--slope_len", type=str, required=True, help="Path to the slope_len.csv")
args = parser.parse_args()

config = ConfigParser(args.config)

site = config["site"]

out_dir = site['dir']
info_file = config['run_info']
elevation = site['elevation']
slope = site['slope']
slope_len = site['slope_length']

if info_file.lower().endswith('.csv'):
    data = pd.read_csv(info_file)
    required_columns_csv = {'SiteID', 'soil', 'lat', 'lon'}
    if not required_columns_csv.issubset(set(data.columns.str)):
        raise ValueError("CSV file missing one or more required columns: 'SiteID', 'soil', 'lat', 'lon'")
elif info_file.lower().endswith('.shp'):
    data = gpd.read_file(info_file)
    data = data.to_crs(epsg=4326)  # Convert to latitude and longitude projection
    data['lat'] = data.geometry.centroid.y
    data['lon'] = data.geometry.centroid.x
    required_columns_shp = {'SiteID', 'soil'}
    if not required_columns_shp.issubset(set(data.columns.str)):
        raise ValueError("Shapefile missing one or more required attributes: 'SiteID', 'soil'")
    data.drop(columns=['geometry'], inplace=True)
else:
    raise ValueError("Unsupported file format. Please provide a '.csv' or '.shp' file.")

info = data
coords = info[['lat', 'lon']].values

prefix = f'{os.path.dirname(__file__)}'

info['ele'] = sample_raster_nearest(elevation, coords)['band_1']
info['slope'] = sample_raster_nearest(slope, coords)['band_1']

info = info.fillna(0)
info['ssu'] = info['soil'].astype(int)
info['slope_steep'] = round(info['slope'] / 100, 2)

# Check if slope_len is a TIFF file or a CSV file
if slope_len.lower().endswith('.tif') or slope_len.lower().endswith('.tiff'):
    # Sample raster data for slope length
    slope_len_data = sample_raster_nearest(slope_len, coords)
    # Add slope length data directly to the info DataFrame
    info['slopelen_1'] = slope_len_data['band_1']  # Adjust 'band_1' as necessary
elif slope_len.lower().endswith('.csv'):
    # Read CSV file for slope length
    slope_len_df = pd.read_csv(slope_len)
    slope_len_df = slope_len_df[['mukey', 'slopelen_1']]
    slope_len_df['mukey'] = slope_len_df['mukey'].astype(int)
    slope_len_df['slopelen_1'] = slope_len_df['slopelen_1'].astype(float)
    # Merge the slope length data with the info DataFrame
    info = pd.merge(info, slope_len_df, how='left', left_on='ssu', right_on='mukey')
else:
    raise ValueError("Unsupported file format for slope_len. Expected .tif or .csv")

print("writing site files")
#site template
with open(f"{prefix}/template.sit", 'r') as f:
    template = f.readlines()

def write_site(row):
    with open(os.path.join(out_dir, f"{int(row['siteid'])}.SIT"), 'w') as f:
        # Modify the template lines
        template[0] = 'USA crop simulations\n'
        template[1] = 'Prototype\n'
        template[2] = f'ID: {int(row["siteid"])}\n'
        template[3] = f'{row["lat"]:8.2f}{row["lon"]:8.2f}{row["ele"]:8.2f}{template[3][24:]}'  # This will replace the first 24 characters
        template[4] = f'{template[4][:48]}{row["slopelen_1"]:8.2f}{row["slope_steep"]:8.2f}{template[4][64:]}'  # This will replace characters 49 to 64
        template[6] = '                                                   \n'
        # Write the modified template to the new file
        f.writelines(template)

info_ls = info.to_dict('records')
# print(info_ls)

parallel_executor(write_site, info_ls, max_workers = 80)