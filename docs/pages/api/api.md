

GeoEPIC allows you to run various commands. The structure is as show below:

```bash
geo_epic {module} {func} -options
```
example usage:
```bash
geo_epic workspace new -n Test
```

### List of Modules and Functions:

#### **workspace**
  - **new**: Create a new workspace with a template structure.
  - **prepare**: Prepare the input files using config file.
  - **run**: Execute the simulations.
#### **utility**
  - **gee**: Download required time-series from Google Earth Engine.
#### **weather**
  - **ee**: Get the required weather data from earth engine.
  - **windspeed**: 
  - **download_daily**: Download daily weather data. 
#### **soil**
  - **usda**: Get Soil data from USDA SSURGO.
  - **process_gdb**: Process ssurgo gdb file.
#### **sites**
  - **generate**: Generate site files from processed data.

For more details on each command and its options, use:
```bash
geo_epic {module} {func} --help
```
