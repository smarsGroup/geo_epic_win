# Running the Model
#### <ToDo\>

``` py
from geoEpic import Site, EpicModel

# initialise a site object
site = Site(opc = './continuous_corn.OPC',  # management file
            dly = './1123455.DLY',          # daily weather file 
            sol = './Andisol.SOL',          # soil file
            sit = './1.SIT')                # site file


# initialise the EPIC model
model = EpicModel(path = './model/EPIC2301dt20230820')
model.setup(start_year = 2014, duration = 10)
model.set_output_types(['ACY', 'DGN'])

# run the simulation for the site
model.run(site)

# get the required outputs
acy = model.outputs['ACY']
model.close()
```


**Loading from config files:**

```python
site = Site.from_config(lat = , lon = , config = './config.yml')
model = EpicModel.from_config(config = './config.yml')

model.run(site)
model.close()
```

**Example config file:**
```yaml
# Model details
EPICModel: ./model/EPIC2301dt20230820
start_year: 1995
duration: 25
output_types:
  - ACY  # Annual Crop data file
  - DGN  # Daily general output file
log_dir: ./log
output_dir: ./output

```

- To edit the OPC, SOL or files in the epic model folder, you could use the epic_editor. the following command will copy the epiceditor in to your current folder.

```bash
>> GeoEPIC workspace add epic_editor
```
