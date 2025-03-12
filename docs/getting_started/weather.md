# **Weather Module**

<!-- <img src="./../pages/assets/fg.jpg" alt="weather" width="90%"/> -->

Weather data is vital in providing essential environmental inputs that significantly influence crop growth and development. Reliable weather inputs ensure that agricultural simulations reflect realistic responses to climatic conditions. The EPIC model requires weather input files that detail daily and monthly climatic variables. Daily files provide day-to-day weather data, while monthly files summarize the average or total values per month. These files are crucial for driving the daily simulation processes in EPIC.
## **Fetching Weather Data**

### **Using Command Line**

GeoEPIC allows the integration of various weather and climate data sources on GEE. To explore the available datasets, visit [Google Earth Engine's dataset catalog](https://developers.google.com/earth-engine/datasets/) and [GEE Community Catalog](https://gee-community-catalog.org/projects/agera5_datasets/). Private assets can also be uploaded to Earth Engine, to use them in combination with existing datasets. Below is an example of configuration file that can be used to create weather input files.

**Example config files:**

- **using AgERA5**

```yaml
# Global parameters
global_scope:
  time_range: ['2002-01-01', '2022-12-31']
  variables: ['srad', 'tmax', 'tmin', 'prcp', 'rh', 'ws']  
  resolution: 9600

# Specify Earth Engine (EE) collections and their respective variables
collections:
  AgEra5:
    collection: 'projects/climate-engine-pro/assets/ce-ag-era5/daily'
    variables:
      srad: b('Solar_Radiation_Flux') 
      tmax: b('Temperature_Air_2m_Max_24h') - 273.15
      tmin: b('Temperature_Air_2m_Min_24h') - 273.15
      prcp: b('Precipitation_Flux') 
      rh: b('Relative_Humidity_2m_06h')
      ws: b('Wind_Speed_10m_Mean')
```

**Using the config file to get data:**

```bash
# Fetch and output weather input files for a specific latitude and longitude
geo_epic weather config.yml --fetch {lat} {lon} --out {out_path}
```
```bash
# Fetch for a list of locations in a csv file with lat, lon, out_path columns
geo_epic weather config.yml --fetch {list.csv} --out {column_name}
```
```bash
# Fetch for crop sequence boundaries shape file.
geo_epic weather config.yml --fetch {aoi_csb.shp} --out {out_dir}
```

**Note:** This command will write weather grid IDs corresponding to each location as an attribute into the input file, when used with a CSV file or crop sequence boundary shapefile.

### **Using Python API**

GeoEPIC also provides a Python API for fetching weather data. The `DLY` class provides methods for handling daily weather data—a critical input for crop growth modeling. Daily weather files include data on solar radiation (srad), temperature (tmax, tmin), precipitation (prcp), relative humidity (rh), and wind speed (ws) that influence crop development.

**Functions**

- **fetch_list**: Fetches weather data based on the input type which could be coordinates, a CSV file, or a shapefile.

```python
from geoEpic.io import fetch_list

# Fetch weather data
fetch_list(config_file='config.yml', input_data='coordinates', output_dir='./output', raw=False)
```

Parameters:

- **input_data**: Could be latitude and longitude as a string, path to a CSV file, or path to a shapefile.
- **output_dir**: Directory or file path where the output should be saved.
- **raw**: Whether to save as raw CSV (True) or DLY format (False). Defaults to False.

## **Modifying Weather Data Using Python API**

The `DLY` class inherits from pandas.DataFrame, providing familiar DataFrame functionality while adding EPIC-specific capabilities. In the example above, the weather data is loaded into a `DLY` object, allowing easy access to weather variables like solar radiation using standard pandas column indexing. The `to_monthly()` method aggregates the daily data into monthly averages and saves it in the EPIC-compatible WP1 format.

```python
from geoEpic.io import DLY

# Load daily weather data
dly = DLY.load('./NCRDU.DLY')

# Print daily solar radiation
print(dly['srad'])

# Aggregate daily data to monthly and save in WP1 format
dly.to_monthly()
```
