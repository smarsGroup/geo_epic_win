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

To generate OPC files using the geo_epic **generate_opc** command, follow these steps:​

#### Prepare Required Files:

- **Crop Data CSV (crop_data.csv)**: Ensure this file contains the necessary columns: epic_code, planting_date, harvest_date, and year. Each row should represent a specific crop's data for a given year.​

- **Template Directory (crop_templates)**: This folder should include:​
  - Mapping File (Mapping): A CSV file mapping epic_code to corresponding template_code.
  - Template OPC Files: OPC files named according to the template_code values specified in the Mapping file.

#### Utilize Provided Templates:

The geoEpic/assets/ws_template/opc/crop_templates directory contains basic templates that you can use or customize for your specific needs.

#### Execute the Command:

Open your terminal and navigate to the directory containing your input files. Run the following command:

```bash
geo_epic generate_opc -c /path/to/crop_data.csv -t /path/to/crop_templates -o /path/to/output_directory
```

Replace `/path/to/crop_data.csv`, `/path/to/crop_templates`, and `/path/to/output_directory` with the actual paths to your crop data file, template directory, and desired output directory, respectively.

#### Optional Arguments:

- `-c` or `--crop_data`: Specifies the path to your crop data CSV file. Default is `./crop_data.csv`.​
- `-t` or `--template`: Specifies the path to your template directory. Default is `./crop_templates`.​
- `-o` or `--output`: Specifies the path to your output directory where the generated OPC files will be saved. Default is `./files`.​

#### Example Usage:

If your crop data CSV is located at `/home/user/data/crop_data.csv`, your templates are in `/home/user/data/crop_templates/`, and you want to save the output in `/home/user/data/output/`, you would run:​

```bash
geo_epic generate_opc -c /home/user/data/crop_data.csv -t /home/user/data/crop_templates -o /home/user/data/output/
```

Ensure that all paths provided are correct and that the command has the necessary permissions to read the input files and write to the output directory.​

For more detailed information on using the geo_epic generate_opc command, refer to the official documentation or the help command:​

```bash
geo_epic generate_opc --help
```
## Run Simulation

Once the input files are prepared, you can create a `Site` object and an `EPICModel` object to run your simulation. This section demonstrates how to set up and execute the EPIC model for your site.

### Import Required Classes

First, import the necessary classes from geoEpic:

```python
from geoEpic.core import Site, EPICModel
from geoEpic.io import ACY, DGN
```

### Create Site Object

Create a `Site` object by specifying paths to all the input files you prepared in the previous steps:

```python
site = Site(opc = './opc/files/umstead.OPC',
      dly = './weather/NCRDU.DLY',
      sol = './soil/files/umstead.SOL',
      sit = './sites/umstead.SIT')
print(site.site_id)
```

The output should display your site identifier:
```
umstead
```

### Configure and Run the Model

Next, create an `EPICModel` object and configure the simulation parameters:

```python
# Initialize the model with path to EPIC executable
model = EPICModel('./model/EPIC1102.exe')

# Set simulation timeframe
model.start_date = '2015-01-01'  # Simulation start date
model.duration = 5               # Simulation duration in years

# Specify which output files you want to generate
model.output_types = ['ACY', 'DGN']  # Annual crop yield and Daily general outputs
```

Now run the model for your defined site:

```python
# Execute the simulation
model.run(site)

# Close the model instance when finished
model.close()

# Path to output files is stored in the site.outputs dictionary
print(site.outputs)
```

## Process Outputs

After completing the simulation, you can analyze the results from the output files generated by the EPIC model. These files contain valuable information about crop performance, soil conditions, and other environmental factors.

### Reading Output Files

EPIC generates several types of output files. The most commonly used ones are:

- **ACY** (Annual Crop Yield): Contains yearly crop production data
- **DGN** (Daily General): Contains daily environmental and crop growth metrics

Use the appropriate classes from the `geoEpic.io` module to read and process these files:

```python
# Access the Annual Crop Yield data
yields = ACY(site.outputs['ACY']).get_var('YLDG')
print(yields)
```

This will display a DataFrame with the annual crop yield data:

```
  index    YR   CPNM    YLDG
0      0  2015   CORN   7.175
1      1  2016   CORN   4.735
2      2  2017   CORN   9.072
3      3  2018   CORN   7.829
4      4  2019   CORN   5.434
```

### Visualizing Results

You can create various visualizations to better understand the simulation results. For example, to plot the crop yields over time:

```python
import matplotlib.pyplot as plt
import pandas as pd

# Create a bar chart of annual yields
plt.figure(figsize=(10, 6))
plt.bar(yields['YR'], yields['YLDG'], color='green')
plt.title('Annual Corn Yield (2015-2019)')
plt.xlabel('Year')
plt.ylabel('Yield (t/ha)')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.xticks(yields['YR'])
plt.tight_layout()
plt.show()
```

Similarly, you can analyze daily metrics like Leaf Area Index (LAI) from the DGN file:

```python
# Access daily general data and plot Leaf Area Index
lai = DGN(site.outputs['DGN']).get_var('LAI')

plt.figure(figsize=(12, 6))
plt.plot(lai['Date'], lai['LAI'], color='darkgreen', linewidth=2)
plt.title('Leaf Area Index (LAI) Over Time')
plt.xlabel('Date')
plt.ylabel('LAI')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

### Advanced Analysis

For more complex analyses, you can combine multiple output variables:

```python
# Extract precipitation and soil moisture
dgn_data = DGN(site.outputs['DGN'])
precip = dgn_data.get_var('PRCP')
soil_water = dgn_data.get_var('SW')

# Merge the data on Date
merged_data = pd.merge(precip, soil_water, on='Date')

# Analyze the relationship between precipitation and soil moisture
# Add your analysis code here...
```

### Exporting Results

You can easily export the processed results for further analysis or reporting:

```python
# Export annual yields to CSV
yields.to_csv('corn_yields_2015_2019.csv', index=False)

# Export daily data to Excel
with pd.ExcelWriter('simulation_results.xlsx') as writer:
   yields.to_excel(writer, sheet_name='Annual_Yields', index=False)
   lai.to_excel(writer, sheet_name='Daily_LAI', index=False)
```

By following these steps, you can effectively process, visualize, and analyze the outputs from your EPIC model simulation to gain valuable insights about crop production and environmental conditions at your site.

