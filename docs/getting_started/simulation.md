# **Simulation**
The GeoEPIC package facilitates running simulations and examining outputs, complementing its input file setup capabilities.

## Single Site Simulation

Follow these steps to run a simulation for an individual site:

1.  **Prepare the Site Object:**
    First, create a `Site` object. This object encapsulates necessary input file references: the crop management file (`OPC`), weather data file (`DLY`), soil file (`SOL`), and site file (`SIT`). The `Site``` object also keeps track of output files generated during the simulation, like the annual crop yield file (`ACY`).

    ```
    from geoEpic.core import Site, EPICModel
    from geoEpic.io import ACY, DGN

    site = Site(opc='./opc/files/umstead.OPC',
                dly='./weather/NCRDU.DLY',
                sol='./soil/files/umstead.SOL',
                sit='./sites/umstead.SIT')
    ```

2.  **Configure and Execute the EPIC Model:**
    Next, initialize an `EPICModel` object, providing the path to the EPIC executable file. Configure it with required settings such as the simulation start date, duration (in years), and the types of output files needed (e.g., `ACY`, `DGN`). Execute the simulation by passing the `Site` object to the model's `run` method. Remember to close the model instance afterwards. The package documentation describes multiple ways to initialize and configure the `EPICModel`.

    ```
    model = EPICModel('./model/EPIC1102.exe')
    model.start_date = '2015-01-01'
    model.duration = 5  # in years
    model.output_types = ['ACY', 'DGN']
    model.run(site)
    model.close()
    ```

3.  **Analyze Simulation Outputs:**
    Finally, examine the outputs. Use the class interfaces provided in the `io` module (like `ACY` and `DGN`) to easily read output files and extract data. These classes integrate with packages like `matplotlib` for generating figures.

    `
    yields = ACY(site.outputs['ACY']).get_var('YLDG')
    lai = DGN(site.outputs['DGN']).get_var('LAI')
    `
    The first line above uses the `ACY` class to get yearly yield values (`YLDG`) from the `ACY` output file. The second line uses the `DGN` class to retrieve the simulated daily Leaf Area Index (`LAI`) from the `DGN` file.

## Regional Simulation

The `Workspace` class streamlines managing and running EPIC simulations across many sites, ideal for regional studies. It's best used within a Jupyter notebook environment for interactive results exploration.

1.  **Initialize the Workspace:**
    Create a `Workspace` object using two main configuration elements:
    *   A configuration file (e.g., `config.yml`) specifying global settings (model path, dates, directories, etc.).
    *   A `sites_info` file (typically CSV) containing metadata and input file paths for each individual site.
    You can optionally clear previous logs and outputs before running.

    ```python
    from geoEpic.core import Workspace

    exp = Workspace('./config.yml')

    # Clear the logs and output directory (optional)
    exp.clear_logs()
    exp.clear_outputs()
    ```

2.  **Configure the Workspace (Example `config.yml`):**
    The configuration file defines the experiment settings. A template is usually provided.

    ```yaml
    # Experiment Name
    EXPName: Kansas Yield Estimation

    # Model configuration
    EPICModel: ./model/EPIC1102.exe
    start_date: '2014-01-01'
    duration: 6  # years
    output_types:
      - ACY  # Annual Crop data file
      - DGN  # Daily general output file
    log_dir: ./log
    output_dir: ./output

    # Path to folders containing input files
    weather_dir: ./weather/Daily
    soil_dir: ./soil/files
    site_dir: ./sites
    opc_dir: ./opc/files

    # Path to csv file with sites' input files info
    sites_info: ./info.csv
    # Select specific sites from the info file
    select: Random(0.1) # Selects 10% of sites randomly
    # Timeout for a simulation execution in seconds.
    timeout: 10
    ```
    The `sites_info` file referenced here contains paths to site-specific inputs. The `select` option allows flexible site filtering (e.g., `Random(0.1)` for 10% random sampling, `Range(0, 1)` for all sites).

3.  **Define Custom Post-Processing Routines (Optional):**
    You can attach custom functions to the `Workspace` object using the `@exp.routine` decorator. These functions execute automatically after each site's simulation completes, allowing for automated output processing, variable extraction, analysis, or custom saving.

    ```python
    import pandas as pd
    from geoEpic.core import Workspace
    from geoEpic.io import DGN, ACY

    exp = Workspace('./config.yml')
    exp.output_dir = None  # Set to None if you don't want standard EPIC outputs saved

    @exp.routine
    def save_lai(site):
        # This function runs after each site simulation
        lai = DGN(site.outputs['DGN']).get_var('LAI')
        lai.to_csv(f'./outputs/{site.site_id}.csv') # Save LAI to a site-specific CSV

    ```
    In this example, the `save_lai` function is registered as a routine. It reads LAI data from the `DGN` output and saves it to a CSV file named after the site ID. Setting `exp.output_dir = None` prevents the workspace from saving the raw EPIC output files (`ACY`, `DGN`, etc.), which is useful if you only need the results from your custom routine.

4.  **Run Multi-Site Simulations:**
    Execute the simulations for all selected sites defined in the workspace configuration. If custom routines are defined, they will run after each site simulation.

    ```python
    # Execute simulations (and routines, if defined)
    exp.run()
    ```

    Additionally, the `Workspace` provides `@exp.logger` and `@exp.objective` decorators for more advanced logging and objective function evaluation, which are detailed further in the package documentation.