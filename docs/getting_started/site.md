# **Site Module**

In agricultural simulations using models like EPIC, the Site file (`.SIT`) contains essential information about the physical characteristics of the specific location being simulated. This includes parameters critical for hydrological and erosion calculations, such as geographic coordinates, elevation, slope steepness and length, and drainage area.

## **1. Managing Site Files (.SIT)**

GeoEPIC provides tools, primarily through its Python API, to manage `.SIT` files. This process typically involves loading an existing site file (which could be a generic template or a file from a previous simulation), modifying its parameters to match the desired location, and then saving the updated information.

### **1.1 Requirements and Configuration**

*   **Base Site File:** You need a starting `.SIT` file to modify. This could be:
    *   A default template provided with EPIC or GeoEPIC.
    *   A `.SIT` file from a similar location or previous run.
*   **Site Parameters:** You need the specific values for the site you want to simulate, such as:
    *   Latitude (`YLAT`) and Longitude (`XLON`)
    *   Elevation (`ELEV`)
    *   Site Area (`AR`) - usually in hectares
    *   Average Slope (`SLP`) - often as a percentage or fraction
    *   Slope Length (`SL`) - in meters
    *   Other parameters as required by the specific EPIC simulation setup (e.g., weather station details, drainage type). Refer to the EPIC manual for a full list and description of `.SIT` parameters.

### **1.2 Fetching Elevation and Slope**

The `DEM` class in the `geoEpic.spatial` module retrieves elevation and slope data from digital elevation models:

```python
from geoEpic.spatial import DEM
from geoEpic.io import SIT

# Defaults to GLO-30, can specify source="ASTER" or "SRTM"
elevation, slope = DEM.fetch(lat=35.9768, lon=-90.1399)

# Create new site file with fetched data
new_site = SIT({'elevation': elevation, 'slope_steep': slope, 'lat': 35.9768, 'lon': -90.1399})
new_site.save('new_site.SIT')
```

Supported DEM sources:
- **GLO-30** (default): Copernicus Global DEM at 30m resolution
- **SRTM**: NASA Shuttle Radar Topography Mission
- **ASTER**: Advanced Spaceborne Thermal Emission and Reflection Radiometer

### **1.3 Using Python API**

The `SIT` class within the `geoEpic.io` module allows for programmatic loading, modification, and saving of `.SIT` files.

**Key Components:**

*   **`SIT.load(filepath)`:** Reads an existing `.SIT` file into a structured `SIT` object.
*   **Direct Attribute Access:** Many common site parameters (like area, slope, coordinates, elevation) can be accessed and modified directly as attributes of the loaded `SIT` object (e.g., `sit_object.area`, `sit_object.slope`).
*   **`SIT.entries`:** Provides access to the underlying data structure (often a list of lists representing lines and values) for modifying parameters that don't have direct attribute access. This allows modification of any parameter in the file while maintaining the required format.
*   **`SIT.save(filepath)`:** Saves the current state of the `SIT` object (with any modifications) to a specified `.SIT` file, ensuring the correct EPIC format.

**Usage Example:**

The following example demonstrates loading and modifying a `.SIT` file:

```python
from geoEpic.io import SIT

# Load and modify existing file
sit_file = SIT.load('./site1.SIT')
sit_file.elevation = 335.0
sit_file.slope = 0.02
sit_file.save('./site1_modified.SIT')
```

This example illustrates how the `SIT` class simplifies managing site characteristics through direct property accessors.