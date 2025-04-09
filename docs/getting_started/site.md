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

### **1.2 Using Python API**

The `SIT` class within the `geoEpic.io` module allows for programmatic loading, modification, and saving of `.SIT` files.

**Key Components:**

*   **`SIT.load(filepath)`:** Reads an existing `.SIT` file into a structured `SIT` object.
*   **Direct Attribute Access:** Many common site parameters (like area, slope, coordinates, elevation) can be accessed and modified directly as attributes of the loaded `SIT` object (e.g., `sit_object.area`, `sit_object.slope`).
*   **`SIT.entries`:** Provides access to the underlying data structure (often a list of lists representing lines and values) for modifying parameters that don't have direct attribute access. This allows modification of any parameter in the file while maintaining the required format.
*   **`SIT.save(filepath)`:** Saves the current state of the `SIT` object (with any modifications) to a specified `.SIT` file, ensuring the correct EPIC format.

**Usage Example:**

The following code demonstrates loading a `.SIT` file, modifying several parameters (site area, slope, and a specific value using the `entries` list), and saving the changes to a new file.

```python
from geoEpic.io import SIT

# Define file paths
input_sit_path = './path/to/your/template_or_existing.SIT'
output_sit_path = './path/to/your/new_or_modified_site.SIT'

try:
    # Load the SIT file
    sit_file = SIT.load(input_sit_path)
    print(f"Loaded site file: {input_sit_path}")

    # Modify site attributes directly
    original_area = sit_file.area
    sit_file.area = 1.5  # site area in hectares
    print(f"Changed site area from {original_area} ha to {sit_file.area} ha")

    original_slope = sit_file.slope
    sit_file.slope = 0.02 # slope as a fraction (e.g., 0.02 for 2%)
    print(f"Changed slope from {original_slope} to {sit_file.slope}")

    # Modify a specific entry using the 'entries' list
    # Example: Change the value at Line 4, Field 1 (0-based indexing for fields might apply)
    # Check the SIT file structure and geoEpic documentation for exact indexing
    line_index = 4 # Assuming line 5 in the file (0-based index)
    field_index = 1 # Assuming the second value on that line
    if len(sit_file.entries) > line_index and len(sit_file.entries[line_index]) > field_index:
        original_entry_value = sit_file.entries[line_index][field_index]
        sit_file.entries[line_index][field_index] = 2.0
        print(f"Changed entry at Ln{line_index+1}-F{field_index+1} from {original_entry_value} to {sit_file.entries[line_index][field_index]}")
    else:
        print(f"Warning: Cannot access entry at Ln{line_index+1}-F{field_index+1}. File structure might differ.")

    # Save the changes to a new SIT file
    sit_file.save(output_sit_path)
    print(f"Saved modified site file to: {output_sit_path}")

except FileNotFoundError:
    print(f"Error: Input site file not found at {input_sit_path}")
except Exception as e:
    print(f"An error occurred during site file processing: {e}")

```

This example illustrates how the `SIT` class simplifies managing site characteristics. Direct property accessors provide an intuitive interface for common parameters, while the `entries` attribute offers flexibility for modifying any part of the file, ensuring compatibility with the EPIC model's requirements whether you are creating a new site configuration from a template or editing an existing one.