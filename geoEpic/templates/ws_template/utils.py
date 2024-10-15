from epic_lib.io import ACY, DGN, CSVWriter
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

def reduce_outputs(run_id, base_dir):
  '''
  To Process EPIC outputs to extract required data.

    Args:
        run_id (str): The identifier for the run (mostly FieldID), used to locate the corresponding output file.
        base_dir (str): The base path of the workspace.
  '''

  # open ACY file and get Yield Column
  acy = ACY(f'{run_id}.ACY')  
  yld = acy.get_var('YLDG')
  
  #get the last year yield value and save in yield.csv
  last_year = np.round(yld.iloc[-1]['YLDG'], 2)
  with CSVWriter(f'{base_dir}/yield.csv', 'a') as writer:
    writer.write_row(run_id, last_year)

  
  
def spatial_plot(aoi, exp_name):
    '''
    Generates a spatial plot of requird data merged with Fields of interest geometries.

    Args:
        aoi (GeoDataFrame): The GeoDataFrame representing the Fields of interest.
        exp_name (str): The experiment name mentioned in the config file.
    '''
    
    # open saved yield.csv and visualize it.
    final = pd.read_csv('./yield.csv', header = None)
    final.columns = ['FieldID', 'yld']
    final = final.apply(pd.to_numeric, errors='coerce')
    
    merged_df = aoi.merge(final, on='FieldID', how='outer')
    merged_df = merged_df.to_crs(epsg=3857)

    fig, ax = plt.subplots(1, 1, figsize=(20, 20))
    merged_df.plot(ax=ax, column='yld', legend=True, legend_kwds={'shrink':0.4, 'aspect':100}, cmap = 'rainbow') 
    
    # Remove x and y axis visible ticks
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor('white')
    plt.title(exp_name)
    plt.show()
 
    
