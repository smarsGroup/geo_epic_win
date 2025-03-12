# Model Parameter Calibration

The calibration module in GeoEPIC was developed to assist in tuning the parameters involved in the EPIC model based on observational data, such as Leaf Area Index (LAI), Net Ecosystem Exchange (NEE), crop yield, or biomass. This allows the model parameters to be refined to better reflect specific local conditions or experimental results. GeoEPIC interfaces with the PyGMO library (Biscani and Izzo (2020)), providing access to a wide range of optimization algorithms, including Particle Swarm Optimization (PSO), Differential Evolution (DE), and various genetic algorithms. This integration enables users to experiment with different optimization strategies and configurations to find the most effective approach for their specific calibration needs. This section demonstrates how to set up a calibration workflow using GeoEPIC.

<img src="../../assets/calibration.png" alt="calibration" width="85%"/>

### Getting Started

- If the package is installed in a conda environment, activate it in the command prompt with:
  ```bash
  conda activate epic_env
  ```
- By this point, the workspace folder must be set up with all the required input files.
- Let's say, `target_yields.csv` has reported yield values with `SiteID`, `Yield` as columns, we would like to calibrate a few parameters so that the simulated yields match the target yields.
- Add files required for Calibration from geo_epic with:
   ```bash
   cd [your_workspace folder]
   geo_epic copy calibration_utils
   ```
- Refer to `calibration_starter.ipynb`, which has the following lines of code.

### Import Required Modules

```python
import numpy as np
import pandas as pd
from geoEpic.io import Parm, CropCom
from geoEpic.core import Workspace
import os
import pygmo as pg
```

### Initiate the Workspace Class
- Edit the required options in the `config.yml` file.

```python
exp = Workspace('./config.yml')

# Clear the logs and output directory
exp.clear_logs()
exp.clear_outputs() 
```

### Load Parameter Files and Set Sensitive Parameters

```python
# Load default cropcom.DAT file from the calibration folder
cropcom = CropCom('./calibration_files/defaults')

# Set a few parameters as sensitive for calibration.
cropcom.set_sensitive(['WA', 'HI', 'WSYF'], [2]) # here 2 is the crop code for corn

# Save the loaded cropcom.DAT to the model folder
cropcom.save(f'./model')
```

##### Verify Sensitive Parameters

```python
cropcom.prms
```

```python
ieparm = Parm('./calibration_files/defaults')
ieparm.set_sensitive(['./calibration_files/sensitivity/parm_yld.csv'])
ieparm.save(f'./model')
```

```python
ieparm.prms
```

### Load Target Yields File

```python
target_yields = pd.read_csv('path/to/target.csv')
exp.target_yields = target_yields.set_index('SiteID')['yields'].to_dict()
```

### Define an Objective Function
- `@exp.logger` routine is called after every site simulation and the site object is passed as input. Logger outputs are saved for later use.
- `@exp.objective` routine is called after finishing simulation on all sites. It is useful to get the fitness for optimization.

```python
@exp.logger
def yield_error(site):
  '''
  Process EPIC outputs to extract data and carry out required computation.
  '''
  target_yield = exp.target_yields[site.site_id]
  simulated_yields = ACY(site.outputs['ACY']).get_var('YLDG')
  last_year_yield = simulated_yields['YLDG'].values[-1]
  return {'error': np.abs(target_yield - last_year_yield)}

@exp.objective
def aggregate():
  '''
  Aggregate all the logged error values to return as objective 
  '''
  logged_data = exp.fetch_log('yield_error')
  logged_data = logged_data.dropna()
  return [logged_data['error'].mean()]
```

### Run Calibration
- Choose necessary settings and optimization algorithm.
- Follow this link for [pygmo docs](https://esa.github.io/pygmo2/overview.html).

```python
import pygmo as pg
from geoEpic.core import PygmoProblem

# Define pygmo problem with workspace and parameter files
problem = PygmoProblem(exp, cropcom, parm)
print('Fitness before Optimization:', exp.run())
```

```python
# Choose an algorithm and settings
algo = pg.algorithm(pg.pso_gen(gen = 45, memory = True))
algo.set_verbosity(1) 

print("Initial Population")
population = pg.population(problem, size = 50)

print("Optimizing...")
population = algo.evolve(population) 
```

```python
print('Fitness After Optimization:', exp.run())
```
