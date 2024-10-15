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

# Parse command line arguments
parser = argparse.ArgumentParser(description="NLDAS Script with Arguments")
parser.add_argument("-s", "--start_date", default="1981-01", help="Start date (YYYY-MM) for date range")
parser.add_argument("-e", "--end_date", default="2023-06", help="End date (YYYY-MM) for date range")
parser.add_argument("-b", "--extent", type=float, nargs=4, metavar=('LAT_MIN', 'LAT_MAX', 'LON_MIN', 'LON_MAX'), 
                        default = [39.8, 43.0, -104, -95.3], help = "Bounding box coordinates")
parser.add_argument("-o", "--working_dir", required=True, help="Working directory")
args = parser.parse_args()

# Access values using args.bbox
lat_min, lat_max, lon_min, lon_max = args.extent

args = parser.parse_args()

# Change working dir
os.makedirs(args.working_dir, exist_ok = True)
os.chdir(args.working_dir)

# Define date range from command-line arguments
dates = pd.date_range(start = args.start_date, end = args.end_date, freq = 'M')

# Latitude and longitude ranges from command-line arguments
lat_range = slice(lat_min, lat_max)
lon_range = slice(lon_min, lon_max)

# Construct the URL for the dataset # Select latitude and longitude range
dataset_url = f"http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_vs_1979_CurrentYear_CONUS.nc"
data_set = xr.open_dataset(dataset_url)
data_set = data_set.sel(lon = lon_range, lat = lat_range)

# Save NLDAS grid
h, w = len(data_set.lat), len(data_set.lon)
grid = np.arange(h * w).reshape(h, w)
# Convert to DataArray and Save as GeoTIFF
unique_values_da = xr.DataArray(grid, coords=[data_set.lat, data_set.lon], dims=['y', 'x'])
unique_values_da = unique_values_da.rio.write_crs("EPSG:4326")
unique_values_da.rio.to_raster('gridmet_grid.tif')

print('Downloading Wind speed data...')
os.makedirs('gridmet_data', exist_ok = True)

def download_func(date):
    """
    Downloads 'ws' data for the given date and saves it to an .npy file.
    """
    date_str = date.strftime('%Y-%m-%d')
    # Select the data for the day
    data = data_set.sel(time=f'{date_str}')
    ws_data = data['daily_mean_wind_speed'].values

    # Save the wind speed data to an .npy file
    np.save(f'gridmet_data/{date_str}.npy', ws_data)


# Use parallel execution to download data for all dates
parallel_executor(download_func, dates, max_workers = 8, return_value = False)

print('Writing windspeed data to CSV...')
os.makedirs('ws_csv', exist_ok = True)

# For each date, load the data and write to CSV
for date in tqdm(dates):
    date_str = date.strftime('%Y-%m')
    ws = np.load(f'gridmet_data/{date_str}.npy')
    days, h, w = ws.shape
    ws = ws.reshape(days, -1)
    
    # Function to write data to CSV
    def write_func(i):
        df = pd.DataFrame({'dates': pd.date_range(start = f'{date_str}-01', end = f'{date_str}-{days}', freq='D'),
                            'values': ws[:, i].flatten()})
        df.to_csv(f'ws_csv/{i}.csv', mode='a', header=False, index=False)
    
    # Use parallel execution to write data to CSV for all grid points
    parallel_executor(write_func, range(h*w), bar = False)



    
    
    