# Weather Module

<!-- ![weather](./assets/fg.jpg) -->
<img src="../assets/fg.jpg" alt="weather" width="90%"/>

Weather data is vital in providing essential environmental inputs that significantly influence crop growth and development. Reliable weather inputs ensure that agricultural simulations reflect realistic responses to climatic conditions. The EPIC model requires weather input files that detail daily and monthly climatic variables. Daily files provide day-to-day weather data, while monthly files summarize the average or total values per month. These files are crucial for driving the daily simulation processes in EPIC.


### Fetching Weather Data

GeoEPIC streamlines the process of fetching and organizing weather data essential for EPIC simulations. It supports the creation of weather input files from daymet, and also from sophisticated datasets available through Google Earth Engine. One can define a composite collection in the config file, detailing the specific variables to select from each data source, tailoring the dataset to meet the needs of their simulations. 


#### Using GEE collections
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
<!-- 
- **Daymet and Gridmet**

```yml
# Global parameters
global_scope:
  time_range: ['2002-01-01', '2022-12-31']
  variables: ['srad', 'tmax', 'tmin', 'prcp', 'rh', 'ws']  
  resolution: 1000


# Specify Earth Engine (EE) collections and their respective variables
collections:
  daymet:
    collection: NASA/ORNL/DAYMET_V4
    variables:
      srad: b('srad') 
      tmax: b('tmax') 
      tmin: b('tmin') 
      prcp: b('prcp') 
      
  gridmet:
    collection: 'IDAHO_EPSCOR/GRIDMET'
    variables:
      ws: b('vs')

# Derived variables
derived_variables:
  rh: '100 * exp((17.625 * {srad}) / (243.04 + {srad})) / exp((17.625 * {tmax}) / (243.04 + {tmax}))'
```
 -->



**Using the config file to get data:**


```
# Fetch and output weather input files for a specific latitude and longitude
>> GeoEPIC weather config.yml --fetch {lat} {lon} --out {out_path}

# Fetch for a list of locations in a csv file with lat, lon, out_path columns
>> GeoEPIC weather config.yml --fetch {list.csv} --out {column_name}

# Fetch for crop sequence boundaries shape file.
>> GeoEPIC weather config.yml --fetch {aoi_csb.shp} --out {out_dir}
```

**Note:** This command will write weather grid IDs corresponding to each location as an attribute into the input file, when used with a CSV file or crop sequence boundary shapefile.

#### From Daymet and NLDAS

To fetch weather data for a specific latitude and longitude using the Daymet dataset, start by downloading the windspeed data from the NLDAS dataset and saving it to the specified directory. Afterward, fetch the other required weather data from the Daymet dataset.

```bash
# To download windspeed data, use the following command
>> GeoEPIC weather windspeed -bbox <bounding_box> -start <start_date> -end <end_date> -out './weather'

# To fetch and output weather input files for a specific latitude and longitude
>> GeoEPIC weather daymet --fetch {lat} {lon} -start <start_date> -end <end_date> --out './weather'
```

<!-- 

### Sources

- **DAYMET** : [https://daymet.ornl.gov/](https://daymet.ornl.gov/) 
- **NLDAS** : [https://climatedataguide.ucar.edu/climate-data/nldas-north-american-land-data-assimilation-system/](https://climatedataguide.ucar.edu/climate-data/nldas-north-american-land-data-assimilation-system/)  -->

