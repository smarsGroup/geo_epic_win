# GeoEPIC Regional Simulation Tutorial

This tutorial provides step-by-step guidance on setting up and running simulations for multiple sites across a region, often as part of a calibration process, using GeoEPIC.

1.  **Set Up Environment:**
    As with single-site simulations, the first step is to configure your local machine and install the necessary `geoEpic` components. This ensures your system is ready for both single-site and regional-scale tasks. For detailed instructions, please refer to the **[Installation Page](link-to-installation-page)**. Completing this step is a prerequisite for all subsequent `geoEpic` operations.

2.  **Prepare Input Files for Multiple Sites:**
    For regional simulations, you need the standard input files (Site - .SIT, Soil - .SOL, Weather - .DLY, Operation Schedule - .OPC) for *each* site within your study region. This typically involves batch processing or scripting to generate files for numerous locations. Consistent naming conventions (e.g., using site IDs) are crucial for managing these files.
    *   Refer to the **[Site File Section](link-to-sit-file-guide)**, **[Soil File Section](link-to-sol-file-guide)**, **[Weather File Section](link-to-dly-file-guide)**, and **[Operation Schedule File Section](link-to-opc-file-guide)** in the getting started menu for details on the format and generation of each file type.
    *   You might use scripts to loop through a list of site coordinates or identifiers to automate the generation and saving of these files. Example concept for downloading weather for multiple sites:
        ```
        from geoEpic.weather import get_daymet_data
        from geoEpic.io import DLY
        import os

        sites = [
            {'id': 'siteA', 'lat': 35.1, 'lon': -78.5},
            {'id': 'siteB', 'lat': 35.2, 'lon': -78.6},
            # ... more sites
        ]
        start_date, end_date = '2015-01-01', '2019-12-31'
        output_weather_dir = './workspace/weather/'
        os.makedirs(output_weather_dir, exist_ok=True)

        for site_info in sites:
            site_id = site_info['id']
            lat, lon = site_info['lat'], site_info['lon']
            print(f"Processing weather for {site_id}...")
            try:
                df = get_daymet_data(lat, lon, start_date, end_date)
                dly_path = os.path.join(output_weather_dir, f"{site_id}.DLY")
                DLY(df).save(dly_path)
            except Exception as e:
                print(f"Error processing {site_id}: {e}")
        ```
    Successfully preparing these files systematically for all sites is essential for regional analysis.

3.  **Set Up Workspace and Folder Structure:**
    Managing inputs and outputs for numerous sites requires an organized workspace. A well-defined folder structure is critical for regional runs and calibration workflows.
    *   It's recommended to create a main `workspace` directory. Inside, organize subdirectories for each input type and for outputs, often with further subdirectories per site or run configuration.
    *   Example Structure:
        ```
        workspace/
        ├── sites/             # .SIT files (e.g., siteA.SIT, siteB.SIT)
        ├── soil/              # .SOL files (e.g., siteA.SOL, siteB.SOL)
        ├── weather/           # .DLY files (e.g., siteA.DLY, siteB.DLY)
        ├── opc/               # .OPC files or templates
        │   ├── files/         # Generated .OPC files (e.g., siteA.OPC)
        │   └── templates/     # OPC templates if using generate_opc
        ├── model/             # EPIC executable (e.g., EPIC1102.exe)
        └── outputs/           # Simulation outputs, potentially nested
            ├── run_config_1/
            │   ├── siteA/     # Outputs for siteA (siteA.ACY, siteA.DGN)
            │   └── siteB/     # Outputs for siteB
            └── run_config_2/
                └── ...
        ```
    *   Refer to the **[Workspace Setup Guide](link-to-workspace-guide)** for best practices and potential templates provided by `geoEpic`. This organization facilitates batch processing and managing results across the region.

4.  **Run Regional Simulation / Calibration:**
    Executing simulations for multiple sites often involves looping through your site list, configuring the model for each, and running it. Calibration adds complexity by adjusting model parameters based on observed data, typically requiring iterative runs.
    *   This process usually involves scripting to automate the setup and execution for each site within your organized workspace. You might use Python loops, parallel processing libraries (like `multiprocessing` or `dask`), or specialized functions within `geoEpic` if available for batch runs.
    *   For detailed strategies on handling multiple sites, managing parameters during calibration, potentially using parallel execution, and interpreting calibration results, please consult the **[Regional Simulations and Calibration Guide](link-to-regional-calibration-guide)**. This guide covers the advanced techniques needed for efficient and effective regional modeling.

5.  **Process Outputs:**
    After running simulations for all sites, outputs (e.g., .ACY, .DGN files) will be available, likely organized within your workspace structure (e.g., in `workspace/outputs/run_config_X/siteY/`). Processing involves reading these numerous files, aggregating data, and performing regional analysis.

    *   **Reading Multiple Output Files:**
        Use scripts to loop through your output directories and load data for each site.
        ```
        import os
        import pandas as pd
        from geoEpic.io import ACY # Or DGN, etc.

        output_base_dir = './workspace/outputs/run_config_1/'
        sites_to_process = [d for d in os.listdir(output_base_dir) if os.path.isdir(os.path.join(output_base_dir, d))] # Get site folders

        all_yields = []

        for site_id in sites_to_process:
            acy_path = os.path.join(output_base_dir, site_id, f"{site_id}.ACY") # Assuming output ACY is named after site_id
            if os.path.exists(acy_path):
                try:
                    yield_df = ACY(acy_path).get_var('YLDG')
                    yield_df['site_id'] = site_id # Add site identifier
                    all_yields.append(yield_df)
                except Exception as e:
                    print(f"Error reading {acy_path}: {e}")

        # Combine data from all sites into a single DataFrame
        if all_yields:
            regional_yields = pd.concat(all_yields, ignore_index=True)
            print(regional_yields.head())
        else:
            print("No yield data processed.")
        ```

    *   **Regional Analysis and Visualization:**
        Analyze aggregated data to understand regional patterns, average performance, or variability.
        ```
        import matplotlib.pyplot as plt
        import seaborn as sns # For potentially more complex plots

        if 'regional_yields' in locals() and not regional_yields.empty:
            # Example: Boxplot of yields across sites for a specific year
            year_to_plot = 2017
            yields_year = regional_yields[regional_yields['YR'] == year_to_plot]

            if not yields_year.empty:
                 plt.figure(figsize=(12, 7))
                 sns.boxplot(x='site_id', y='YLDG', data=yields_year)
                 plt.title(f'Regional Corn Yield Distribution ({year_to_plot})')
                 plt.xlabel('Site ID')
                 plt.ylabel('Yield (t/ha)')
                 plt.xticks(rotation=45, ha='right')
                 plt.tight_layout()
                 plt.show()
            else:
                print(f"No data found for year {year_to_plot}")

            # Example: Calculate average yield per year across the region
            avg_regional_yield = regional_yields.groupby('YR')['YLDG'].mean().reset_index()
            print("\nAverage Regional Yield per Year:")
            print(avg_regional_yield)

        ```
        Visualizations might include maps of yields, comparative charts, or plots showing the range of outcomes across the region.

    *   **Exporting Aggregated Results:**
        Save the combined regional data for reporting or further analysis.
        ```
        if 'regional_yields' in locals() and not regional_yields.empty:
            regional_yields.to_csv('regional_corn_yields_summary.csv', index=False)

        # You could also save figures
        # plt.savefig('regional_yield_boxplot_2017.png')
        ```
    This final step transforms individual site outputs into meaningful regional insights, often crucial for calibration validation and understanding spatial patterns.