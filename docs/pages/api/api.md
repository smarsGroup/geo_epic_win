

GeoEPIC provides a command-line interface to execute various tasks. 
<br>
The general command structure is as follows:

```bash
geo_epic {module} {func} [options]
```

**Example usage:**
```bash
geo_epic workspace new -n Test
```

### Modules and Functions

#### **workspace**
- **new**: Create a new workspace with a predefined template structure.
- **copy**: Copy files between different folders.
- **run**: Execute simulations within the workspace.

#### **utility**
- **gee**: Download required time-series data from Google Earth Engine.

#### **weather**
- **ee**: Retrieve weather data from Earth Engine.
- **download_daily**: Download daily weather data from Daymet.

#### **soil**
- **usda**: Fetch soil data from USDA SSURGO.
- **process_gdb**: Process SSURGO geodatabase (GDB) files.

#### **sites**
- **generate**: Generate site files from processed data.

For more details on each command and its available options, use the following command:

```bash
geo_epic {module} {func} --help
```
