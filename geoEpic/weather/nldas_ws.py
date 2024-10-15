import os
import numpy as np
import xarray as xr
import rioxarray as rio
import pandas as pd
from pydap.cas.urs import setup_session
from geoEpic.utils import parallel_executor
from geoEpic.utils.formule import windspd
from tqdm import tqdm
import argparse
from geoEpic.io import ConfigParser
import geopandas as gpd


# Parse command line arguments
parser = argparse.ArgumentParser(description="NLDAS Script with Arguments")
parser.add_argument("-c", "--config", default= "./config.yml", help="Path to the configuration file")
parser.add_argument("-w", "--max_workers", default = 4, help = "No. of maximum workers")
# parser.add_argument("-s", "--start_date", default="1981-01", help="Start date (YYYY-MM) for date range")
# parser.add_argument("-e", "--end_date", default="2023-06", help="End date (YYYY-MM) for date range")
# parser.add_argument("-b", "--extent", type=float, nargs=4, metavar=('LAT_MIN', 'LAT_MAX', 'LON_MIN', 'LON_MAX'), 
#                         default = [39.8, 43.0, -104, -95.3], help = "Bounding box coordinates")
# parser.add_argument("-o", "--working_dir", required=True, help="Working directory")
args = parser.parse_args()

config = ConfigParser(args.config)
max_workers = args.max_workers
weather = config["weather"]
aoi = config["Area_of_Interest"]
start_date = weather["start_date"]
end_date = weather["end_date"]
working_dir = weather["dir"]

# Access values using args.bbox
if aoi.endswith('.shp'):
    gdf = gpd.read_file(aoi)
    gdf = gdf.to_crs(epsg=4326)
    lon_min, lat_min, lon_max, lat_max = gdf.total_bounds
elif aoi.endswith('.csv'):
    gdf = pd.read_csv(aoi)
    lon_min, lat_min = np.floor(gdf['x'].min() * 1e5)/1e5, np.floor(gdf['y'].min() * 1e5)/1e5
    lon_max, lat_max = np.ceil(gdf['x'].max() * 1e5)/1e5, np.ceil(gdf['y'].max() * 1e5)/1e5

args = parser.parse_args()

# Change working dir
os.makedirs(working_dir, exist_ok = True)
os.chdir(working_dir)

# Define date range from command-line arguments
dates = pd.date_range(start = start_date, end = end_date, freq = 'BME')


# lat_min, lat_max, lon_min, lon_max = [39.8, 43.0, -104, -95.3]
# Latitude and longitude ranges from command-line arguments
lat_range = slice(lat_min, lat_max)
lon_range = slice(lon_min, lon_max)

username = 'bharathc'
password = '@Ce1one$28'

print('Connecting to the NLDAS dataset...')

# URL of the dataset
dataset_url = 'https://hydro1.gesdisc.eosdis.nasa.gov:443/dods/NLDAS_FORA0125_H.002'

# Setup a session to connect to the dataset
session = setup_session(username, password, check_url=dataset_url)
store = xr.backends.PydapDataStore.open(dataset_url, session=session)

# Open the dataset and select 'ugrd10m' and 'vgrd10m' variables
# Select latitude and longitude range
data_set = xr.open_dataset(store)[['ugrd10m', 'vgrd10m']]
data_set = data_set.sel(lon = lon_range, lat = lat_range)

# Save NLDAS grid
h, w = len(data_set.lat), len(data_set.lon)
grid = np.arange(h * w).reshape(h, w)
# Convert to DataArray and Save as GeoTIFF
unique_values_da = xr.DataArray(grid, coords=[data_set.lat, data_set.lon], dims=['y', 'x'])
unique_values_da = unique_values_da.rio.write_crs("EPSG:4326")
unique_values_da.rio.to_raster('nldas_grid.tif')

print('Downloading Wind speed data from NLDAS')
os.makedirs('NLDAS_data', exist_ok = True)

def download_func(date):
    """
    Downloads 'ugrd10m' and 'vgrd10m' data for the given date, computes the wind speed,
    and saves it to an .npy file.
    """

    date_str = date.strftime('%Y-%m')

    if( os.path.exists(f'NLDAS_data/{date_str}.npy') ):
        return
    # Select the data for the given month
    month_data = data_set.sel(time=f'{date_str}')

    # Extract ugrd10m and vgrd10m data for the month
    ugrd10m_data = month_data['ugrd10m'].values
    vgrd10m_data = month_data['vgrd10m'].values

    # Compute wind speed
    wind_speed = windspd(ugrd10m_data, vgrd10m_data)  
    # Compute daily mean for wind speed
    _, h, w = wind_speed.shape
    # Averaging over the hours
    daily_wind_speed = wind_speed.reshape((-1, 24, h, w)).mean(axis = 1)  
    # Save the wind speed data to an .npy file
    np.save(f'NLDAS_data/{date_str}.npy', daily_wind_speed)


# Use parallel execution to download data for all dates
parallel_executor(download_func, dates, max_workers = max_workers, return_value = False)

print('Writing windspeed data to CSV...')
os.makedirs('NLDAS_csv', exist_ok = True)

# For each date, load the data and write to CSV
for date in tqdm(dates):
    date_str = date.strftime('%Y-%m')
    ws = np.load(f'NLDAS_data/{date_str}.npy')
    days, h, w = ws.shape
    ws = ws.reshape(days, -1)
    
    # Function to write data to CSV
    def write_func(i):
        df = pd.DataFrame({'dates': pd.date_range(start = f'{date_str}-01', end = f'{date_str}-{days}', freq='D'),
                            'values': ws[:, i].flatten()})
        df.to_csv(f'NLDAS_csv/{i}.csv', mode='a', header=False, index=False)
    
    # Use parallel execution to write data to CSV for all grid points
    parallel_executor(write_func, range(h*w), max_workers=max_workers, return_value = False,bar=False)



    
    
    
