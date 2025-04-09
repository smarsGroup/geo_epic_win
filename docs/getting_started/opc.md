# **Operation Control (OPC) Module**

The crop management file (`.OPC`) in the EPIC model contains essential information about various management practices carried out on an agricultural field. Each row in the management file represents a specific management operation. These operations include planting a specific crop, fertilizer application, irrigation methods and timing, harvesting, and tillage details. The interpretation of entries in certain columns changes depending on the operation being simulated. This detailed setup enables the EPIC model to accurately simulate the effects of management decisions on crop yield and environmental impact. For more information on the structure of management files, refer to the EPIC user manual.

<img src="../../assets/opc.jpg" alt="OPC" width="100%"/>

## **1. Creating OPC File**

This section describes how to generate EPIC-ready operation control files (`.OPC`) using GeoEPIC tools.

### **1.1 Requirements and Configuration**

To generate an `.OPC` file using the GeoEPIC command-line utility, you need the following inputs:

*   **Crop Data CSV File:**
    *   A comma-separated values file (`.csv`) containing the crop rotation information for the simulation period.
    *   **Required Columns:** `year`, `crop_code`, `planting_date`, `harvest_date`.
    *   **Format Example:**
        ```
        year,crop_code,planting_date,harvest_date
        2006,2,2006-05-08,2006-12-05
        2007,1,2007-03-18,2007-12-18
        2008,2,2008-03-31,2008-12-05
        2009,1,2009-04-09,2009-10-25
        2010,2,2010-05-23,2010-12-03
        ```

*   **Templates Folder:**
    *   A folder containing template operation schedules for different crops.
    *   **Contents:**
        *   **Crop Template Files:** Individual `.OPC` files named according to the `template_code` used in the `MAPPING` file (e.g., `CORN.OPC`, `SOYB.OPC`). Each file details the standard sequence of operations for that crop, typically relative to a nominal planting date.
            *   **Example (`CORN.OPC` snippet):**
                ```
                 3  0
                 1  4 22   30    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
                 1  4 23   33    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
                 1  4 24   71    0    2   52 160.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
                 1  4 25    2    0    2    01700.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
                 1  9 25  650    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
                 1  9 26  740    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
                 1  9 27   41    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
                ```
        *   **Mapping File:** A file named `MAPPING` (case-sensitive, no extension) that links the `crop_code` from your CSV file to the corresponding `template_code` (which matches the template `.OPC` filename without the extension).
            *   **Required Columns:** `crop_code`, `template_code` (comma-separated).
            *   **Format Example (`MAPPING` file):**
                ```
                crop_code,template_code
                1,SOYB
                2,CORN
                3,GRSG
                4,COTS
                18,RICE
                ```

*   **Output Path:** A specified location and filename for the generated `.OPC` file.

**Note:** If you create a GeoEPIC workspace using its tools, a sample templates folder (`opc/template`) is often included, which you can adapt.

### **1.2 Using Command Line (CLI)**

The `geo_epic generate_opc` command assembles the final `.OPC` file based on your crop rotation CSV and the templates.

*   **Command Syntax:**
    ```
    geo_epic generate_opc -c /path/to/crop_data.csv -t /path/to/templates_folder -o /path/to/output_filename.OPC
    ```

*   **Arguments:**
    *   `-c` / `--cdl`: Path to the input crop data CSV file (as described in Sec 1.1).
    *   `-t` / `--template`: Path to the folder containing the crop template `.OPC` files and the `MAPPING` file (as described in Sec 1.1).
    *   `-o` / `--output`: Path where the final generated crop management file (`.OPC`) will be saved.

*   **Date Handling:** The command uses the `planting_date` and `harvest_date` from the input CSV (`-c`) file to adjust the relative dates/timing of operations defined within the corresponding crop template file found via the `MAPPING` file. If `planting_date` and `harvest_date` are *not* provided in the CSV for a given year/crop, the dates specified within the template `.OPC` file itself will be used directly without adjustment for that year's operations.

## **2. Editing OPC File**

Once an `.OPC` file is generated or obtained, you may need to modify specific operations or parameters. The `geoEpic.io.OPC` class provides methods to load, edit, and save these files programmatically.

**Key Concepts:**

*   The `.OPC` file represents management operations row by row.
*   The `geoEpic.io.OPC` class loads this file into an object that behaves like a `pandas.DataFrame`, allowing familiar data manipulation techniques alongside specialized methods.
*   Operations like adding, updating, or removing specific management practices can be performed programmatically.

**Example Usage:**

The following code demonstrates loading an `.OPC` file, modifying an irrigation parameter, adding a fertilizer application, removing that same application, and saving the changes.

```
from geoEpic.io import OPC

# Define file path
opc_file_path = './path/to/your/umstead.OPC'
output_opc_path = './path/to/your/umstead_modified.OPC' # Save changes to a new file

try:
    # Load the existing .OPC file
    opc = OPC.load(opc_file_path)

    # Modify a parameter: Select auto irrigation implement ID
    original_iaui = opc.IAUI
    opc.IAUI = 72
    print(f"Changed Auto Irrigation Implement ID (IAUI) from {original_iaui} to {opc.IAUI}")

    # Define a new fertilizer operation as a dictionary
    fertilizer_op = {'opID': 71, 'cropID': 2, 'fertID': 52,
                     'date': '2015-04-01', 'OPV1': 160}

    # Add/Update the fertilizer operation using the update method
    opc.update(fertilizer_op)
    print(f"Added/Updated fertilizer operation on {fertilizer_op['date']}")
    # Note: 'update' might replace an existing operation on the same date or add a new one,
    # depending on its implementation. Check documentation for specific behavior.

    # Remove the specific fertilizer operation just added
    # Use parameters that uniquely identify the operation to remove
    opc.remove(opID=71, date='2015-04-01')
    print(f"Removed operation with opID 71 on date 2015-04-01")

    # Save the OPC file with all accumulated changes
    opc.save(output_opc_path)
    print(f"Saved modified OPC file to {output_opc_path}")

except FileNotFoundError:
    print(f"Error: Input OPC file not found at {opc_file_path}")
except Exception as e:
    print(f"An error occurred during OPC file editing: {e}")

```

This example showcases key functionalities: loading an `.OPC` file, programmatically modifying general parameters (like `IAUI`), adding new operations (fertilizer application via `update`), removing specific operations (`remove`), and saving the modified file. Since the `OPC` class inherits from `pandas.DataFrame`, users can leverage familiar DataFrame operations in addition to these specialized methods.

For a comprehensive list of available methods and their specific behaviors, consult the GeoEPIC documentation. The structure, valid operation codes (`opID`), and parameter meanings (`OPV1` etc.) for `.OPC` files are detailed in the official EPIC user manual (e.g., EPIC 1102).