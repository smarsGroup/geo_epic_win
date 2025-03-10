# **Soil Module**

In agriculture simulations, such as those conducted using the EPIC model, soil data directly influences water availability, nutrient supply, and overall crop growth predictions. Soil input files to the model contain detailed information about the soil properties of a specific location, depth wise. 

<!-- <img src="../assets/sol.jpg" alt="soilg" width="90%"/> -->

## **Fetching Soil Data**

### **Using Command Line**
GeoEPIC helps in generating soil files required by the EPIC Model from two soil data sources: <br>

- **[USDA SSURGO](https://www.nrcs.usda.gov/resources/data-and-reports/soil-survey-geographic-database-ssurgo)**: which contains detailed surveys of U.S. soils. <br>
- **[ISRIC SoilGrids 250m](https://soilgrids.org/)** (adding soon): which offers global coverage in a grid format.

#### **USDA SSURGO**

The USDA Soil Survey Geographic **(SSURGO)** database is a comprehensive resource for soil data collected by the Natural Resources Conservation Service **(NRCS)** across the United States and the Territories. This database provides detailed information on soil properties and classifications. The data is collected through extensive field surveys and laboratory analysis. For more detailed information, visit the [USDA NRCS SSURGO](https://www.nrcs.usda.gov/resources/data-and-reports/soil-survey-geographic-database-ssurgo) page.

To fetch and output soil files using the USDA SSURGO database, following commands could be used. For a specific location, specify the latitude and longitude coordinates to generate a soil file named {mukey}.SOL. 

```bash
# Fetch and output soil files for a specific latitude and longitude
geo_epic soil usda --fetch {lat} {lon} --out {out_path}
```
```bash
# Fetch for a list of locations in a csv file with lat, lon
geo_epic soil usda --fetch {list.csv} --out {out_dir}
```
```bash
# Fetch for crop sequence boundaries shape file.
geo_epic soil usda --fetch {aoi_csb.shp} --out {out_dir}
```

**Note:** This command will write Soil IDs (mukeys) corresponding to each location as an attribute into the input file, when used with a CSV file or crop sequence boundary shapefile.

**Processing ssurgo gdb file**:

To process a SSURGO GDB file and generate soil files for all unique soils contained in it, follow these steps. For instance, if you require soil files for Maryland, navigate to the 'State Database - Soils' section, and download the 'gSSURGO_MD.zip' file. Once the download is complete, extract the contents and place the GDB file in the 'soil' folder within your workspace. Use the following command to generate the soil files for all mukeys. 

Link: [https://www.nrcs.usda.gov/resources/data-and-reports/gridded-soil-survey-geographic-gssurgo-database](https://www.nrcs.usda.gov/resources/data-and-reports/gridded-soil-survey-geographic-gssurgo-database)

```bash
geo_epic soil process_gdb -i {path/to/ssurgo.gdb} -o {out_dir} 
```

### **Using Python API**

To download soil data from the Soil Data Access (SDA) service, you can use the `SoilDataAccess` class. This class provides a method to fetch soil properties based on either a mukey (integer) or a WKT location (string).

#### **Usage Example**

```python
from soil_data_access import SoilDataAccess

# Fetch soil properties using a mukey (integer)
soil_data = SoilDataAccess.fetch_properties(123456)

# Fetch soil properties using a WKT location (string)
wkt_location = "POLYGON((-93.5 41.5, -93.5 41.6, -93.4 41.6, -93.4 41.5, -93.5 41.5))"
soil_data = SoilDataAccess.fetch_properties(wkt_location)
```

This method will return a DataFrame containing various soil properties such as bulk density, field capacity, sand content, and more, for the specified input.

## **Modifying Soil Data using Python API**

