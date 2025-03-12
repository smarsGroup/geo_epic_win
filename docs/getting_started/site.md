# **Site**

In agricultural simulations, the site file contains essential information about the physical characteristics of the simulation location. The `SIT` class in GeoEPIC provides methods to access and modify site-specific parameters such as latitude, longitude, elevation, slope, and drainage area.

## **Modifying Site Data**

### **Using Python API**

To manage site data, you can use the `SIT` class. This class provides methods to load, modify, and save site-specific parameters.

#### **Usage Example**

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

The code above demonstrates how to load a SIT file, modify site attributes, and save the changes. The `SIT` class simplifies the process of managing site characteristics by providing direct access to commonly modified parameters through property accessors, while other parameters can be accessed and modified via the `entries` pointer. This approach maintains the EPIC-specific file format requirements while offering an intuitive interface.