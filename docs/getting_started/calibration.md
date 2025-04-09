# Model Parameter Calibration using GeoEPIC

This guide explains how to use GeoEPIC's calibration module to tune EPIC model parameters based on observational data (e.g., yield, LAI, NEE). By adjusting parameters, the model can better reflect specific local conditions or experimental results. GeoEPIC integrates with the PyGMO library for access to various optimization algorithms.

This process assumes you have a workspace folder already set up with necessary EPIC input files and a target data file (e.g., `target_yields.csv` with `SiteID` and `Yield` columns).

Here are the steps involved:

## **1. Prepare Your Environment and Load Data**

Import necessary libraries, initialize the GeoEPIC workspace, and load your target observational data.

*   Import Python modules: `numpy` and `pandas` for data manipulation, GeoEPIC's `Parm`, `CropCom`, and `Workspace` for model interaction, `os` for file operations, and `pygmo` for the optimization algorithms.
*   Initialize the `Workspace` object by pointing it to your main configuration file (`config.yml`). Ensure this file has the correct paths and settings for your calibration experiment.
*   Optionally, clear previous logs and outputs to start fresh.
*   Load your target data (e.g., measured yields) into a pandas DataFrame and convert it into a dictionary format where keys are `SiteID`s and values are the target yields. Assign this dictionary to `exp.target_yields`.

```python
import numpy as np
import pandas as pd
from geoEpic.io import Parm, CropCom, ACY # Added ACY import here as it's used later
from geoEpic.core import Workspace
import os
import pygmo as pg

# Initiate the Workspace Class (edit config.yml first)
exp = Workspace('./config.yml')

# Clear the logs and output directory (optional)
exp.clear_logs()
exp.clear_outputs()

# Load Target Yields File (replace with your actual path)
target_yields = pd.read_csv('path/to/target.csv')
exp.target_yields = target_yields.set_index('SiteID')['yields'].to_dict()
```

## **2. Define Sensitive Parameters**

 Specify which parameters within the EPIC model's input files should be adjusted ('tuned') during the calibration process.
 
*   Load the relevant parameter files using GeoEPIC's `io` classes (e.g., `CropCom` for crop-specific parameters in `cropcom.DAT`, `Parm` for general parameters typically in `EPIC.PARM`). Load default versions usually kept in a separate calibration folder.
*   Use the `.set_sensitive()` method on these objects to mark parameters for calibration. You can specify parameters directly (like 'WA', 'HI' for a specific crop code in `CropCom`) or provide a path to a file listing sensitive parameters (useful for `Parm`).
*   Save the modified parameter files (which now know which parameters are sensitive) to your main model directory (`./model`), overwriting the existing ones.
*   You can verify which parameters are marked as sensitive by accessing the `.prms` attribute of the parameter objects.

```python
# Load default cropcom.DAT file from a calibration files directory
cropcom = CropCom('./calibration_files/defaults')

# Set 'WA', 'HI', 'WSYF' as sensitive for crop code 2 (e.g., corn)
cropcom.set_sensitive(['WA', 'HI', 'WSYF'], [2])

# Save the loaded cropcom.DAT to the model folder
cropcom.save(f'./model')

# Verify sensitive CropCom parameters (optional)
# cropcom.prms

# Load default general parameters (e.g., EPIC.PARM)
ieparm = Parm('./calibration_files/defaults')
# Set sensitive parameters based on a list in a file
ieparm.set_sensitive(['./calibration_files/sensitivity/parm_yld.csv'])
# Save the modified PARM file to the model folder
ieparm.save(f'./model')

# Verify sensitive general parameters (optional)
# ieparm.prms
```

## **3. Define the Objective Function**

Create functions that tell the optimization algorithm how 'good' a set of parameter values is by comparing simulation results to the target data.

*   Use the `@exp.logger` decorator to define a function (e.g., `yield_error`) that runs *after each site simulation*. This function receives the `site` object, extracts the relevant simulated output (e.g., last year's yield using `ACY`), compares it to the target yield for that site (retrieved from `exp.target_yields`), calculates an error metric (e.g., absolute difference), and returns it in a dictionary. These logged values are stored by the workspace.
*   Use the `@exp.objective` decorator to define a function (e.g., `aggregate`) that runs *after all sites in an optimization iteration are simulated*. This function fetches the logged results (using `exp.fetch_log`), aggregates the errors across all sites (e.g., calculates the mean error), and returns a single value (or list of values for multi-objective optimization). This aggregated value is the 'fitness' score that the optimization algorithm tries to minimize.

``` python
@exp.logger
def yield_error(site):
  '''
  Calculates yield error for a single site after simulation.
  '''
  target_yield = exp.target_yields[site.site_id]
  # Ensure ACY is imported: from geoEpic.io import ACY
  simulated_yields = ACY(site.outputs['ACY']).get_var('YLDG')
  # Handle cases where simulation might not produce yield (e.g., return a large error or filter later)
  if simulated_yields is None or simulated_yields.empty:
      return {'error': np.inf} # Assign high error if no yield simulated
  last_year_yield = simulated_yields['YLDG'].iloc[-1] # Use iloc for position
  return {'error': np.abs(target_yield - last_year_yield)}

@exp.objective
def aggregate():
  '''
  Aggregates errors from all sites to provide a single fitness value.
  '''
  logged_data = exp.fetch_log('yield_error')
  logged_data = logged_data.dropna()
  # Handle case with no valid logged data
  if logged_data.empty or not np.isfinite(logged_data['error']).any():
      return [np.inf] # Return high fitness if no valid errors
  # Calculate mean of finite errors
  valid_errors = logged_data.loc[np.isfinite(logged_data['error']), 'error']
  return [valid_errors.mean()] if not valid_errors.empty else [np.inf]

```

## **4. Configure and Run the Calibration**

Set up the optimization algorithm using PyGMO, link it to the GeoEPIC workspace and parameters, and execute the calibration process.

*   Create a `PygmoProblem` object, passing it the initialized `Workspace` (`exp`) and the parameter objects (`cropcom`, `ieparm`) that have sensitive parameters defined. This wraps your setup for PyGMO.
*   Optionally, run `exp.run()` *before* optimization to see the initial fitness (error) using the default parameter values.
*   Choose a PyGMO optimization algorithm (e.g., `pg.pso_gen` for Particle Swarm Optimization) and configure its settings (e.g., number of generations `gen`). Set verbosity to control how much information the algorithm prints during execution.
*   Create an initial `population` for the algorithm. This represents the starting set of parameter combinations that the algorithm will evaluate and improve upon.
*   Run the optimization using `algo.evolve(population)`. This is the main calibration step where the algorithm iteratively adjusts the sensitive parameters, runs EPIC simulations via the workspace, evaluates the results using your objective function, and converges towards parameter values that minimize the error.
*   After the evolution completes, run `exp.run()` again. This will now use the *best* parameter set found by the optimization algorithm, showing the final, hopefully improved (lower), fitness value.

```python 
import pygmo as pg
from geoEpic.core import PygmoProblem

# Define pygmo problem linking workspace, CropCom, and Parm objects
problem = PygmoProblem(exp, cropcom, ieparm)

# Check initial fitness with default parameters (optional)
print('Fitness before Optimization:', exp.run())

# Choose an algorithm (PSO_gen) and settings
algo = pg.algorithm(pg.pso_gen(gen = 45, memory = True)) # 45 generations
algo.set_verbosity(1) # Print progress every generation

# Create initial population
print("Initial Population")
population = pg.population(problem, size = 50) # Population size of 50

# Run the optimization
print("Optimizing...")
population = algo.evolve(population)

# Check final fitness with optimized parameters
print('Fitness After Optimization:', exp.run())
```

## **Result of Calibration**

*   The primary result of the calibration is a set of **optimized parameter values** for the sensitive parameters you defined in Step 2. These optimized values are automatically written back into the corresponding parameter files (e.g., `cropcom.DAT`, `EPIC.PARM`) located in your `./model` directory.
*   The optimization process aims to find parameter values that minimize the objective function defined in Step 3 (e.g., minimize the average absolute error between simulated and target yields).
*   The final fitness value printed after optimization indicates how well the model reproduces the target data using the newly calibrated parameters. A lower fitness value generally signifies a better match between the simulation and the observations.