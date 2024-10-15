import numpy as np
import pandas as pd
import requests
from io import StringIO
from geoEpic.utils.formule import rh_vappr

def get_daymet_data(lat: float, lon: float, start: str, end: str):
    """
    Fetches Daymet weather data for the specified coordinates and time period.
    """
    # Define the URL
    url = f"https://daymet.ornl.gov/single-pixel/api/data?lat={lat}&lon={lon}&vars=dayl,prcp,srad,swe,tmax,tmin,vp&start={start}&end={end}"

    # Get response and raise an exception for HTTP errors
    response = requests.get(url)
    response.raise_for_status()  

    # Convert response content to StringIO for compatibility with pandas read_csv
    data_content = StringIO(response.text)

    # Read and format the data
    data = pd.read_csv(data_content, skiprows=7, names=['year','yday','dayl','prcp','srad','swe','tmax','tmin','vp'])
    # data.drop(columns=['swe'], inplace=True)

    # get leap year between start and end years and add a column for 60th day
    start_year = int(start.split('-')[0])
    end_year = int(end.split('-')[0])
    years = np.arange(start_year, end_year+1, dtype=np.int64)
    leap_years = years[np.where((years % 4 == 0) & (years % 100 != 0) | (years % 400 == 0))]

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
    data['month'] = data['date'].dt.month
    data['day'] = data['date'].dt.day
    # Drop the 'date' and 'yday' columns
    data.drop(['date', 'yday'], axis = 1, inplace=True)

    data['srad'] =  (data['srad'] * data['dayl']) / 1e6  # Convert W/m2 to MJ/m2/day
    data['rh'] = rh_vappr(data['vp'], data['tmax'], data['tmin'])
    data = data[['year', 'month', 'day', 'srad', 'tmax', 'tmin', 'prcp', 'rh']]

    return data

# Test the function
if __name__ == '__main__':
    data = get_daymet_data(35.9621, -84.2916, '1981-01-01', '2020-12-31')
    print(data)
