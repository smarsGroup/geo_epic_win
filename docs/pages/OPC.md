<!-- ## Agricultural Management  -->


The crop management file in the EPIC model contains essential information about various management practices carried out on an agricultural field. Each row in the management file (.OPC) represents a specific management operation. These operations include planting a specific crop,  fertilizer application, irrigation methods and timing, harvesting and tillage details. The interpretation of entries in certain columns changes depending on the operation being simulated. This detailed setup enables the EPIC model to accurately simulate the effects of management decisions on crop yield and environmental impact. For more information on the structure of management files, refer to the EPIC user manual.


<img src="../assets/opc.jpg" alt="OPC" width="80%"/>

### 1. Generating Crop Management File

To generate an OPC file, the following command line utility can be used:

```bash
geo_epic generate_opc -c /path/to/cdl.csv -t /path/to/templates_folder -o /path/to/output.OPC
```

 - **`-c`**: Path to the crop data CSV file. This file should contain crop information for each year with the following columns (comma-separated):


    ``` 
    year, crop_code, planting_date, harvest_date
    2006, 2, 2006-05-08, 2006-12-05
    2007, 1, 2007-03-18, 2007-12-18
    2008, 2, 2008-03-31, 2008-12-05
    2009, 1, 2009-04-09, 2009-10-25
    2010, 2, 2010-05-23, 2010-12-03
    ```

 - **`-t`**: Path to the folder which contains operations template for each crop. This folder should contain:
    - {Crop}.OPC files for each required crop, detailing common management practices specific to that crop.

        ```
            Corn
            3  0
            1  4 22   30    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
            1  4 23   33    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
            1  4 24   71    0    2   52 160.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
            1  4 25    2    0    2    01700.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
            1  9 25  650    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
            1  9 26  740    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
            1  9 27   41    0    2    0   0.000    0.00    0.00   0.000    0.00    0.00    0.00    0.00
        ```

    - A MAPPING file that provides mapping from crop_code to template_name for each crop.

        ```
            crop_code,template_code
            1,SOYB
            2,CORN
            3,GRSG
            4,COTS
            18,RICE
        ```

    - The management file is generated by adjusting all operations relative to the specified planting and harvest dates in the cdl.csv. If plating date and harvest are not provided, The output files will contain the dates used in the crop template file.

    **Note**: If you create a workspace, you can see a sample template folder under the opc directory.

 - **`-o`**: Path where the output crop management file will be saved.


