# Running one site in EPIC Model

This tutorial provides step-by-step guidance on setting up and running a single site in GeoEPIC.


1. [Set Up Environment](#set-up-environment)
2. [Prepare setup](#prepare-setup)
    - [Site File (.SIT)](#site-file-sit)
    - [Soil File (.SOL)](#soil-file-sol)
    - [Weather File (.DLY)](#weather-file-dly)
    - [Operation Schedule File (.OPC)](#operation-schedule-file-opc)
3. [Run Simulation](#run-simulation)
4. [Process Outputs](#process-outputs)

## Set Up Environment
To begin, you must set up the geo_epic environment. 

  1. **Download the setup script**:
   Download the [`epic_setup.bat`](https://smarsgroup.github.io/geo_epic_win/epic_setup.bat) script to your local machine.
  2. **Run the setup script**:
    Execute the downloaded script using the following command:
    ```bash
    call epic_setup.bat
    ```

For detailed instructions, please refer to the [installation page](/geo_epic_win/getting_started/installation/).

## Prepare Setup

Before running the simulation, you need to create the EPICModel folder with all necessary files. First, download the [workspace template](https://github.com/smarsGroup/geo_epic_win/tree/main/src/geoEpic/assets/workspace_win) folder to your local machine. Then prepare the four required input files: Site File (.SIT), Soil File (.SOL), Weather File (.DLY), and Operation Schedule File (.OPC). These files provide the model with specific data about the simulation environment and management practices. For detailed guidance on creating and formatting these input files, refer to the respective sections in the [getting_started](/geo_epic_win/getting_started/weather) menu.

### Site File (.SIT)
The site file contains information about the specific site you are simulating. It includes details such as location, slope, and other site-specific parameters. Assuming you have already necessary data. You can use [SIT](/geo_epic_win/pages/api/io/#io.SIT) class to use that information and create .SIT file

```python
from geoEpic.io import SIT

# Load a SIT file
sit_file = SIT.load('./umstead.SIT')

# Modify site attributes
sit_file.area = 1.5  # site area in hectares
sit_file.slope = 0.2
sit_file.entries[4][1] = 2.0  # entry at Ln4 - F1

# Save the changes to a new SIT file
sit_file.save('umstead_new.SIT')
```

You can also download slope information from [SoilDataAccess API](/geo_epic_win/api/soil/#soil.SoilDataAccess) if you don't already have slope data.

### Soil File (.SOL)
The soil file contains data about the soil properties at the site, such as soil texture, depth, and nutrient content. You can download soil data for a location from [SoilDataAccess](/geo_epic_win/api/soil/#soil.SoilDataAccess) class and store it in a SOL file.

```python
from geoEpic.io import SOL
from geoEpic.utils import Wicket

# Define the site location (latitude and longitude)
lat, lon = 35.890, -78.750  # Example coordinates for Umstead area

# Create a Wicket object for the location using WKT string format
wkt_string = f"POINT({lon} {lat})"
wicket = Wicket.from_wkt(wkt_string)

# Download soil data from SoilDataAccess API
soil_file = SOL.from_sda(wicket)

# Save the soil data to a SOL file
soil_file.save('./soil/files/umstead.SOL')
```

### Weather File (.DLY)
The weather file contains daily meteorological data for the site, such as temperature, precipitation, and solar radiation. You can download weather data using the [Weather module](/geo_epic_win/api/weather) in geoEpic.

```python
from geoEpic.weather import get_daymet_data
from geoEpic.io import DLY

# Define location and time period
lat, lon = 35.890, -78.750  # Example coordinates for Umstead area
start_date = '2015-01-01'
end_date = '2019-12-31'

# Download weather data from Daymet
df = get_daymet_data(lat, lon, start_date, end_date)

# Save as DLY file
DLY(df).save('./weather/NCRDU.DLY')
```

This code retrieves daily weather data from the Daymet dataset for the specified location and time period, then saves it in the EPIC-compatible .DLY format.

### Operation Schedule File (.OPC)
The operation schedule file outlines the management operations to be performed at the site, such as planting, fertilization, and irrigation schedules.



You can create an OPC file based on crop rotation data, for example, using the Cropland Data Layer (CDL) which provides information about what crops were grown in a specific location over time.

```python
from geoEpic.io import OPC
import os

# Path to crop templates
crop_templates_path = './crop_templates/'

# Get CDL data for the site location (assuming you have downloaded this from Google Earth Engine)
cdl_data = {
  2015: 'CORN',
  2016: 'SOYB',
  2017: 'WWHT',
  2018: 'CORN',
  2019: 'WWHT_SOYB'
}

# Set up parameters
start_year = 2015
opc_file_path = './opc/files/umstead.OPC'  # Output OPC file path

# Initialize result OPC file
res_opc_file = None
prev_code = ''

# Iterate through each year and create the OPC file with appropriate crop rotations
for year, code in cdl_data.items():
  # Load template OPC file for the crop
  template_opc = OPC.load(os.path.join(crop_templates_path, f'{code}.OPC'), start_year)
  plantation_row = template_opc.iloc[0]
  epic_code = plantation_row['CRP']
  
  # Append the template to the result OPC file
  if res_opc_file is None:
    res_opc_file = template_opc
  else:
    res_opc_file = res_opc_file.append(template_opc)
  
  # Keep track of previous crop for rotation logic
  prev_code = code

# Save the final OPC file
res_opc_file.save(opc_file_path)
```

This code demonstrates how to create a comprehensive operation schedule file that includes crop rotations, fertilizer applications, and irrigation settings based on historical crop data for your site. The resulting OPC file will contain a multi-year rotation schedule that matches the CDL data, with appropriate management operations for each crop.
## Run Simulation

nce the input files are prepared, you can create a `Site` object and an `EPICModn is complete, you can process and analyze the output files to examine the results, such as crop yields and leaf area index.

## Follow the below lines of code

Import the required classes from geoEpic

```python
from geoEpic.core import Site, EPICModel
from geoEpic.io import ACY, DGN
```

First create a `Site` object with the necessary input files. 


```python
site = Site(opc = './opc/files/umstead.OPC',
            dly = './weather/NCRDU.DLY',
            sol = './soil/files/umstead.SOL',
            sit = './sites/umstead.SIT')
print(site.site_id)
```
umstead
    

#### Define the EPICModel class
Now Let's create an `EPICModel` object and specify the start date, duration of the simulation.


```python
model = EPICModel('./model/EPIC1102.exe')
model.start_date = '2015-01-01'
model.duration = 5
model.output_types = ['ACY']
```

Run the model simulations at the required site

```python
model.run(site)
# Close the model instance
model.close()
# Path to output files is stored in the site.outputs dict
site.outputs
```

- EPICModel instance can also be created using a configuration file. 
Example config file:
```yaml
# Model details
EPICModel: ./model/EPIC1102.exe
start_year: '2015-01-01'
duration: 5
output_types:
  - ACY  # Annual Crop data file
  - DGN  # Daily general output file
log_dir: ./log
output_dir: ./output
```
- This method allows for easier management of model parameters.

#### Using EPICModel class with Configuration File

```python
model = EPICModel.from_config('./config.yml')
model.run(site)
model.close()

#using with context
with EPICModel.from_config('./config.yml') as model:
    model.run(site)
```

#### Examine the outputs
Finally, examine the outputs generated by the model run.


```python
yields = ACY(site.outputs['ACY']).get_var('YLDG')
yields
```


<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>index</th>
      <th>YR</th>
      <th>CPNM</th>
      <th>YLDG</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>0</td>
      <td>2015</td>
      <td>CORN</td>
      <td>7.175</td>
    </tr>
    <tr>
      <th>1</th>
      <td>1</td>
      <td>2016</td>
      <td>CORN</td>
      <td>4.735</td>
    </tr>
    <tr>
      <th>2</th>
      <td>2</td>
      <td>2017</td>
      <td>CORN</td>
      <td>9.072</td>
    </tr>
    <tr>
      <th>3</th>
      <td>3</td>
      <td>2018</td>
      <td>CORN</td>
      <td>7.829</td>
    </tr>
    <tr>
      <th>4</th>
      <td>4</td>
      <td>2019</td>
      <td>CORN</td>
      <td>5.434</td>
    </tr>
  </tbody>
</table>
</div>



Plot the simulated Leaf Area Index


```python
import matplotlib.pyplot as plt

lai = DGN(site.outputs['DGN']).get_var('LAI')

plt.figure(figsize=(12, 6))
plt.plot(lai['Date'], lai['LAI'])
plt.title('Leaf Area Index (LAI) Over Time')
plt.xlabel('Date')
plt.ylabel('LAI')
plt.grid(True)
plt.tight_layout()
plt.show()

```


    
![png](output_18_0.png)
    

