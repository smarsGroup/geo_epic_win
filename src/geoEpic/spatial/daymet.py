import xarray as xr
import numpy as np
import pandas as pd
import requests
from io import StringIO

import urllib3
from geoEpic.io import DLY

# Disable warnings about insecure requests (only for testing!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_daymet_data(lat: float, lon: float, start: str, end: str):
    """
    Fetches Daymet weather data for the specified coordinates and time period.
    """
    # Define the URL
    url = f"https://daymet.ornl.gov/single-pixel/api/data?lat={lat}&lon={lon}&vars=dayl,prcp,srad,swe,tmax,tmin,vp&start={start}&end={end}"

    # Get response and raise an exception for HTTP errors
    response = requests.get(url, verify=False)
    response.raise_for_status()  

    # Convert response content to StringIO for compatibility with pandas read_csv
    data_content = StringIO(response.text)

    # Read and format the data
    data = pd.read_csv(data_content, skiprows=7, names=['year','yday','dayl','prcp','srad','swe','tmax','tmin','vp'])

    # get leap year between start and end years and add a column for 60th day
    start_year = int(start.split('-')[0])
    end_year = int(end.split('-')[0])
    years = np.arange(start_year, end_year+1, dtype=np.int64)
    leap_years = years[(years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))]

    # add 1 to 'yday' for ydays >= 60 for leap years
    data.loc[(data['year'].isin(leap_years)) & (data['yday'] >= 60), 'yday'] += 1
    # get data for 59th and 61st days for leap years and average them
    day_59 = data[(data['year'].isin(leap_years)) & (data['yday'] == 59)].copy().reset_index(drop=True)
    day_61 = data[(data['year'].isin(leap_years)) & (data['yday'] == 61)].copy().reset_index(drop=True)
    avg_leap_days = (day_59 + day_61) / 2
    avg_leap_days['year'] = day_59['year']
    avg_leap_days['yday'] = 60  

    data = pd.concat([data, avg_leap_days]).sort_values(['year', 'yday'])

    # Convert the 'yday' column to datetime, and extract month and day
    data['date'] = pd.to_datetime(data['year'].astype(str) + '-' + data['yday'].astype(str), format='%Y-%j')
    data['srad'] =  (data['srad'] * data['dayl']) / 1e6  # Convert W/m2 to MJ/m2/day
    data['rh'] = rh_vappr(data['vp'], data['tmax'], data['tmin'])

    data.drop(['yday', 'vp', 'dayl', 'swe'], axis = 1, inplace=True)

    return data


def get_gridmet_data(lat: float, lon: float, start: str, end: str, vars=['ws']):
    """
    Fetch GRIDMET data for specified variables and location within a time range.
    For 'rh', fetch rmax and rmin, then average to get daily mean RH.
    """
    # Mapping from short variable names to GRIDMET dataset names
    variables_map = {
        'ws': 'vs',   # Wind speed
        'tmax': 'tmmx',  # Maximum temperature
        'tmin': 'tmmn',  # Minimum temperature
        'srad': 'srad',  # Solar radiation
        'prcp': 'pr',    # Precipitation
        'rmax': 'rmax',  # Relative humidity max
        'rmin': 'rmin'   # Relative humidity min
    }

    # Efficiently determine which variables to fetch (expand 'rh' to rmax/rmin)
    fetch_vars = []
    for v in vars:
        if v == 'rh':
            fetch_vars.extend(['rmax', 'rmin'])
        else:
            fetch_vars.append(v)
    fetch_vars = list(dict.fromkeys(fetch_vars))  # Remove duplicates, preserve order

    var_dfs = {}
    for variable in fetch_vars:
        if variable not in variables_map:
            raise ValueError(f"Variable {variable} not recognized.")
        
        # Construct the URL for the dataset
        dataset_url = f"http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_{variables_map[variable]}_1979_CurrentYear_CONUS.nc"
        data = xr.open_dataset(dataset_url)
        
        # Select the nearest location data and time slice
        data = data.sel(lon=lon, lat=lat, method='nearest')
        data = data.sel(day=slice(start, end))
        
        # Extract the variable as a DataFrame and round the values
        var_df = data[list(data.data_vars)[0]].to_dataframe().drop(['lat', 'lon'], axis=1)
        var_df.rename(columns={list(data.data_vars)[0]: variable}, inplace=True)
        var_df.reset_index(inplace=True)
        var_dfs[variable] = var_df

    # Merge all variable DataFrames on 'day'
    df = None
    for var_df in var_dfs.values():
        if df is None:
            df = var_df
        else:
            df = df.merge(var_df, on='day', how='outer')

    # For 'rh', average rmax and rmin, then drop them
    if 'rh' in vars:
        if 'rmax' not in df.columns or 'rmin' not in df.columns:
            raise ValueError("rmax and rmin must be present to calculate rh")
        df['rh'] = (df['rmax'] + df['rmin']) / 2
        df['rh'] = df['rh'] / 100
        df = df.drop(columns=[col for col in ['rmax', 'rmin'] if col in df.columns])

    # Convert tmax and tmin from Kelvin to Celsius if present
    if 'tmax' in df.columns:
        df['tmax'] = df['tmax'] - 273.15
    if 'tmin' in df.columns:
        df['tmin'] = df['tmin'] - 273.15

    # Convert srad from W/m2 to MJ/m2/day if present
    if 'srad' in df.columns:
        df['srad'] = df['srad'] * 0.0864

    df = df.rename(columns={'day': 'date'})
    return df.round(2)


def get_dly(lat: float, lon: float, start_date: str, end_date: str):
    # Get Daymet data for the requested period (all variables except ws)
    daymet = get_daymet_data(lat, lon, start_date, end_date)
    # Find the last date available in Daymet
    last_daymet_date = daymet['date'].max()
    requested_end_date = pd.to_datetime(end_date)
    # If Daymet does not cover the full requested period, fill the gap with Gridmet for only the missing days
    if last_daymet_date < requested_end_date:
        # Get all variables from Gridmet for only the missing days
        missing_start = (last_daymet_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        all_vars = ['srad', 'tmax', 'tmin', 'prcp', 'rh']
        gridmet = get_gridmet_data(lat, lon, missing_start, end_date, vars=all_vars)
        # Concatenate Daymet and Gridmet (missing days only)
        data = pd.concat([daymet, gridmet], ignore_index=True)
        data = data.sort_values('date').reset_index(drop=True)
    else:
        # Use Daymet for most variables, but NOT ws
        data = daymet.copy()
    # Always get ws from Gridmet for the full requested period
    ws_gridmet = get_gridmet_data(lat, lon, start_date, end_date, vars=['ws'])
    # Merge ws into the data on date
    data = pd.merge(data, ws_gridmet[['date', 'ws']], on='date', how='left')
    data['year'] = data['date'].dt.year
    data['month'] = data['date'].dt.month
    data['day'] = data['date'].dt.day
    data = data[['year', 'month', 'day', 'srad', 'tmax', 'tmin', 'prcp', 'rh', 'ws']]
    return DLY(data)
