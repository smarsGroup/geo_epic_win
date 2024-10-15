Google Earth Engine (GEE) is a cloud-based platform for planetary-scale environmental data analysis. It hosts a vast collection of satellite imagery and other geospatial datasets, enabling users to perform large-scale data analysis. To explore the available datasets, visit [Google Earth Engine's dataset catalog](https://developers.google.com/earth-engine/datasets/) and [GEE Community Catalog](https://gee-community-catalog.org/projects/agera5_datasets/). Private assets can also be uploaded to Earth Engine, to use them in combination with existing datasets.

This module can be used to combine various datasets and extract the required timeseries directly from Google Earth Engine.

<img src="../assets/gee.png" alt="soil" width="80%"/>

### 1. Configuration file breakdown
This module utilizes a configuration file in YAML format to extract data from Google Earth Engine. The configuration file defines global parameters, Earth Engine collections, and derived variables. Below is a detailed explanation of each section.

```yaml 
# filename: config.yml

# Global parameters
global_scope:
  time_range: ['2016-01-01', '2021-12-31']
  variables: ['nir', 'red', 'green', 'ndvi']  
  resolution: 10

# Specify Earth Engine collections and their respective variables
collections:

  le07:
    collection: LANDSAT/LE07/C02/T1_L2
    select:  (b('QA_PIXEL') >> 6) & 1
    variables:
      nir: b('SR_B4')*0.0000275 - 0.2
      red: b('SR_B3')*0.0000275 - 0.2
      green: b('SR_B2')*0.0000275 - 0.2

# Derived variables
derived_variables:
  ndvi: '(nir - red)/(nir + red)'

```

#### a) Global Parameters

The `global_scope` section contains general settings applicable to the entire data extraction process.

- **`time_range`**: Specifies the period for which the satellite data should be fetched.

- **`variables`**: Lists the key variables to be extracted. These are typically satellite bands or derived products such as vegetation indices, or any other relevant parameters like tempurature etc.,

- **`resolution`**: Defines the spatial resolution (in meters) for the output data.

#### b) Earth Engine Collections

Each Earth Engine dataset is defined under its own subsection within collections. The key components are collection, select, and variables. Multiple datasets can be specified, and if data from multiple collections are present for the same day, the module will return the mean of the variables across all collections.

- **`collection`**: Refers to the specific Google Earth Engine dataset identifier.

- **`select`**: Defines a masking or selection condition for the data extraction.

- **`variables`**: Specifies the bands or parameters to extract, along with any scaling factors or transformations.

#### c) Derived Variables

Derived variables are calculated from the raw bands using mathematical expressions and functions available in numpy package.

---

### 2. Fetching the Data

You can use the following command-line interface to fetch time-series of required variables from Google Earth Engine into a CSV file:

```bash
geo_epic gee <config-file> --fetch <roi> --out <output-path>
```

The region of interest for fetching data can be provided in three formats:

   - **Latitude and Longitude:** Use direct coordinates [latitude, longitude]
```bash
geo_epic gee ./landsat_ndvi.yml --fetch 40.5677 98.5505 --out ./out/sample.csv
```
   - **Shapefile (.shp):** A shapefile containing the polygons of interest. It must contain a SiteID or FieldID column. The data will be stored in the name of FieldID or SiteID. Fetches one file for each polygon.
```bash
geo_epic gee ./landsat_ndvi.yml --fetch ./input/region.shp --out ./out
```

   - **CSV File:** A CSV file must contain a SiteID or FieldID column. Additionally, if using a CSV, it must include lat, lon columns. The data will be stored in the name of FieldID or SiteID.
```bash
geo_epic gee ./landsat_ndvi.yml --fetch ./input/region.csv --out ./out
```