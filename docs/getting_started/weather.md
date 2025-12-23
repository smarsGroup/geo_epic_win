# Weather Module

Weather data is fundamental to agricultural simulation, providing environmental inputs crucial for modeling crop growth and yield. Reliable weather data ensures realistic simulation outcomes. The EPIC model specifically requires weather data formatted into two key input files:

1. **Daily Weather Files (`.DLY`):** Contain day-to-day meteorological data (solar radiation, temperature max/min, precipitation, relative humidity, wind speed). These drive the daily simulation processes.
2. **Monthly Weather Files (`.WP1`):** Summarize climate statistics, typically monthly averages or totals derived from daily data.

<img src="../../assets/weather.jpg" alt="soilg" width="100%"/>

## 1. Data Sources

Weather files can be created from various sources. GeoEPIC provides support for google earth engine sources.

- **Google Earth Engine (GEE):**
GEE is a cloud-based platform for planetary-scale geospatial analysis. It hosts a vast public data archive that includes numerous satellite imagery and climate datasets (like AgERA5, GRIDMET, CHIRPS, etc.), alongside capabilities to use your own private GEE assets. GeoEPIC leverages GEE to fetch data from these collections, allowing access to global or regional weather data often derived from satellite observations or climate reanalysis models.
    * Reference: [Google Earth Engine dataset catalog](https://developers.google.com/earth-engine/datasets/)
    * Reference: [GEE Community Catalog](https://gee-community-catalog.org/)

## 2. Creating Weather File

This section outlines the process for generating EPIC-compatible weather files (.DLY) using GeoEPIC.

### 2.1 Requirements and Configuration

When sourcing weather data from Google Earth Engine (GEE) collections (like AgERA5, GRIDMET, CHIRPS, or your private assets), a configuration file (typically `config.yml`) is essential. This file directs GeoEPIC on what data to retrieve, defining the time period, specific variables, target resolution, the GEE collection path, and how the source data bands should be mapped and potentially converted (e.g., units) to match EPIC's requirements.

**Example Configuration File (`config.yml`) using AgERA5:**

```yaml
# Global parameters
global_scope:
# Define the time period for data fetching
time_range: ['2002-01-01', '2022-12-31']
# List of standard EPIC weather variable names
variables: ['srad', 'tmax', 'tmin', 'prcp', 'rh', 'ws']
# Target resolution in meters (AgERA5 native is ~9km or 9600m)
resolution: 9600

# Specify Earth Engine (EE) collections and map their bands to EPIC variables
collections:
AgEra5:
# Path to the EE ImageCollection Asset
collection: 'projects/climate-engine-pro/assets/ce-ag-era5/daily'
# Define how EE bands map to EPIC variables
# b() refers to the image band
# Note: Unit conversions can be applied directly (e.g., Kelvin to Celsius)
variables:
srad: b('Solar_Radiation_Flux') # MJ/m^2/day (assuming source is daily total flux)
tmax: b('Temperature_Air_2m_Max_24h') - 273.15 # Convert K to °C
tmin: b('Temperature_Air_2m_Min_24h') - 273.15 # Convert K to °C
prcp: b('Precipitation_Flux') # mm/day (assuming source is daily total)
rh: b('Relative_Humidity_2m_06h') # % (using 6 AM value as representative)
ws: b('Wind_Speed_10m_Mean') # m/s
```

### 2.2 Command Line (CLI)

Use the `geo_epic weather` command with your configuration file and specify the location(s).

**Fetch for a Single Location (Latitude, Longitude):**

```bash
# Provide lat, lon coordinates directly
geo_epic weather config.yml --fetch 40.71 -74.00 --out ./output/NewYorkCity.DLY
```

**Fetch for Multiple Locations from a CSV File:**

```bash
# Specify input CSV and the column containing output file paths
# CSV must contain 'lat', 'lon', and the output path column (e.g., 'OutputFileColumn')
# GeoEPIC adds a 'wthgridid' column to the CSV
geo_epic weather config.yml --fetch locations.csv --out OutputFileColumn
```

**Fetch for Regions from a Shapefile:**

```bash
# Specify input Shapefile and the output directory for .DLY files
# GeoEPIC adds a 'wthgridid' attribute to the shapefile
geo_epic weather config.yml --fetch ./boundaries/fields.shp --out ./weather_output/
```

### 2.3 Python API

#### Direct Fetching with `geoEpic.spatial`

For simple single-location fetching, use the `Daymet` and `AgEra5` classes directly:

```python
from geoEpic.spatial import Daymet, AgEra5
from geoEpic.io import DLY

# Fetch weather data from Daymet or AgERA5
dly_daymet = Daymet.fetch(lat=35.9768, lon=-90.1399)
print(dly_daymet['srad'].head())

dly_era5 = AgEra5.fetch(lat=35.9768, lon=-90.1399)
dly_era5.save('era5_weather.DLY')

# Load and manipulate existing weather file
dly = DLY.load('./existing_weather.DLY')
dly.to_monthly()  # Saves as WP1 format
```

## 3. Editing Weather File

Once `.DLY` files are created, the `geoEpic.io.DLY` class allows loading, manipulation, and further processing. It acts like a `pandas.DataFrame` with added EPIC-specific features.

```python
from geoEpic.io import DLY

# Load and manipulate existing weather file
dly = DLY.load('./weather1.DLY')
print(dly['srad'].head())

# Generate monthly weather file (.WP1)
dly.to_monthly()
```

**Key `DLY` Class Features:**

* **Loading:** `DLY.load(filepath)` reads a `.DLY` file into a DLY object (DataFrame subclass).
* **Data Access:** Utilize standard `pandas.DataFrame` methods for analysis and modification.
* **Monthly Aggregation:** `dly.to_monthly()` calculates monthly statistics and saves as `.WP1` file.