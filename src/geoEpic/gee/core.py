import numpy as np
import pandas as pd
from ruamel.yaml import YAML
from concurrent.futures import ThreadPoolExecutor
from shapely.geometry import Polygon, MultiPolygon
from geoEpic.utils.workerpool import WorkerPool

import ee
from geoEpic.gee.initialize import ee_Initialize

project_name = ee_Initialize()

pool = WorkerPool(f'gee_global_lock_{project_name}')
# pool.open(40)

def extract_features(collection, aoi, date_range, resolution):
    # pool = WorkerPool(f'gee_global_lock_{project_name}')
    
    def map_function(image):
        # Function to reduce image region and extract data
        date = image.date().format()
        reducer = ee.Reducer.mode() if aoi.getInfo()['type'] != "Point" else ee.Reducer.first()
        reduction = image.reduceRegion(reducer=reducer, geometry=aoi, scale=resolution, maxPixels=1e9)
        return ee.Feature(None, reduction).set('Date', date)
    
    worker = pool.acquire()

    try:
        filtered_collection = collection.filterBounds(aoi)
        filtered_collection = filtered_collection.filterDate(*date_range)
        daily_data = filtered_collection.map(map_function)
        df = ee.data.computeFeatures({
                'expression': daily_data,
                'fileFormat': 'PANDAS_DATAFRAME'
            })
    finally: 
        pool.release(worker)
        # pass

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        if 'geo' in df.columns: df = df.drop(columns=['geo'])
        df = df.dropna(how='all', subset=[col for col in df.columns if col != 'Date'])
    return df

def apply_formula(image, var, formula, vars = None):
    """
    Apply a formula to an Earth Engine image and add the result as a new band.
    """
    var_dict = {}
    if vars:
        var_dict = {v: image.select(v) for v in vars}
    try:
        var_image = image.expression(formula, var_dict).rename(var).set('system:time_start', image.get('system:time_start'))
        return image.addBands(var_image).toFloat()
    except Exception as e:
        print(f"Error processing image {image.id()}: {e}")
        return image
                    
class CompositeCollection:
    """
    A class to handle composite collection of Earth Engine data.

    This class initializes collections of Earth Engine based on a provided
    YAML configuration file, applies specified formulas and selections, and allows
    for the extraction of temporal data for a given Area of Interest (AOI).

    Methods:
        extract(aoi_coords):
            Extracts temporal data for a given AOI and returns it as a pandas DataFrame.
    """

    def __init__(self, yaml_file, start_date = None, end_date = None):
        # Initialize the CompositeCollection object
        self.global_scope = None
        with open(yaml_file, 'r') as file:
            self.config = YAML().load(file)
        self.global_scope = self.config.get('global_scope')
        self.collections_config = self.config.get('collections')
        self.collections = {}
        self.vars = {}
        self.args = []
        self.resolution = self.global_scope['resolution']
        # Override the global scope time range with the provided start and end dates
        if start_date:
            self.global_scope['time_range'][0] = start_date
        if end_date:
            self.global_scope['time_range'][1] = end_date
        self._initialize_collections()

    def _initialize_collections(self):
        # Initialize collections based on the configuration
        for name, config in self.collections_config.items():
            if 'time_range' in config.keys():
                start, end = config['time_range']
            else:
                start, end = self.global_scope['time_range']

            collection = ee.ImageCollection(config['collection'])
            if 'linkcollection' in config.keys():
                # Handle linked collections if specified in the configuration
                link_settings = config['linkcollection']
                collection2 = ee.ImageCollection(link_settings['collection'])
                collection = collection.linkCollection(collection2, link_settings['bands'])

            collection = collection.filterDate(start, end)
            
            if 'select' in config.keys():
                # Apply selection mask to the collection if specified
                mask_exp = config['select']
                def mask_util(image):
                    mask = image.expression(mask_exp)
                    return image.updateMask(mask)
                collection = collection.map(lambda image: mask_util(image))
                
            variables = config['variables']
            vars = []
            for var, formula in variables.items():
                collection = collection.map(lambda x: apply_formula(x, var, formula))
                vars.append(var)
            
            self.collections[name] = collection.select(vars)
            self.vars[name] = vars
            self.args.append((name, self.collections[name], (start, end)))
    
    def merged(self):
        """
        Merges all collections in self.collections into a single ImageCollection.

        Returns:
            ee.ImageCollection: A merged collection containing all images from all collections.
        """
        if not self.collections:
            raise ValueError("No collections to merge. Make sure collections are initialized.")

        # Convert the dictionary values (collections) to a list
        collection_list = list(self.collections.values())

        # Use the ee.ImageCollection.merge() method to merge all collections
        merged_collection = collection_list[0]
        for collection in collection_list[1:]:
            merged_collection = merged_collection.merge(collection)
        
        try:
            # Apply derived variables formulas if specified in the configuration
            derived = self.config.get('derived_variables')
            vars = merged_collection.first().bandNames().getInfo()
            for var, formula in derived.items():
                merged_collection = merged_collection.map(lambda x: apply_formula(x, var, formula, vars))
        except Exception as e:
            print(e)

        return merged_collection
        
    def extract(self, aoi_coords):
        """
        Extracts temporal data for a given Area of Interest (AOI).

        Args:
            aoi_coords (tuple/list): Coordinates representing the AOI, either as a Point or as vertices of a Polygon.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the extracted data.
        """
        # Convert coordinates to AOI geometry
        if isinstance(aoi_coords, (Polygon, MultiPolygon)):
            aoi_coords = aoi_coords.exterior.coords[:]
        if len(aoi_coords) == 1:
            aoi = ee.Geometry.Point(aoi_coords[0])
        else:
            aoi = ee.Geometry.Polygon(aoi_coords)
        
        def extract_features_wrapper(args):
            name, collection, date_range = args
            return extract_features(collection, aoi, date_range, self.resolution)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(extract_features_wrapper, self.args))

        #filter results
        results = [df for df in results if not df.empty]
        # Merge the results into a single DataFrame
        df_merged = results[0]
        for df in results[1:]:
            df_merged = pd.merge(df_merged, df, on='Date', how='outer')
            columns = df_merged.columns
            # Iterate over columns to find and calculate the mean for columns with suffixes
            for col in set(col.rsplit('_', 1)[0] for col in columns if '_' in col):
                if f"{col}_x" in columns and f"{col}_y" in columns:
                    df_merged[col] = df_merged[[f"{col}_x", f"{col}_y"]].mean(axis=1)
                    df_merged.drop(columns=[f"{col}_x", f"{col}_y"], inplace=True)
        
        df_merged = df_merged.groupby('Date').mean().reset_index()
        df_merged.sort_values(by='Date', inplace=True)

        try:
            # Apply derived variables formulas if specified in the configuration
            derived = self.config.get('derived_variables')
            for var_name, formula in derived.items():
                df_merged[var_name] = self._safe_eval(formula, df_merged)
        except Exception as e:
            print(e)
        
        # Filter and clean the DataFrame based on the global scope variables
        df_merged = df_merged[['Date'] + self.global_scope['variables']].copy()
        df_merged.dropna(inplace=True)
        df_merged = df_merged.reset_index(drop=True)
        numerical_cols = df_merged.select_dtypes(include=['number']).columns
        df_merged[numerical_cols] = df_merged[numerical_cols].astype(float).round(3)

        return df_merged
    

    def _safe_eval(self, expression, df):
        """
        Safely evaluate a mathematical expression using only functions from the math and numpy libraries.

        Args:
            expression (str): The expression to evaluate.
            df (pd.DataFrame): The DataFrame containing the data to evaluate against.

        Returns:
            pd.Series: The result of the evaluated expression.
        """
        safe_dict = np.__dict__
        safe_dict.update(df.to_dict(orient='series'))
        return eval(expression, {"__builtins__": None}, safe_dict)



class TimeSeries:

    def __init__(self, collection, vars, date_range = None):
        self.collection = collection.select(vars)
        self.vars = vars
        self.date_range = date_range
    
    def extract(self, aoi_coords, resolution = 30, date_range = None):
        """
        Extracts temporal data for a given Area of Interest (AOI).

        Args:
        aoi_coords (tuple/list): Coordinates representing the AOI, either as a Point or as vertices of a Polygon.

        Returns:
        pd.DataFrame: A pandas DataFrame containing the extracted data.
        """
        # Convert coordinates to AOI geometry
        if isinstance(aoi_coords, (Polygon, MultiPolygon)):
            aoi_coords = aoi_coords.exterior.coords[:]
        if len(aoi_coords) == 1:
            aoi = ee.Geometry.Point(aoi_coords[0])
        else:
            aoi = ee.Geometry.Polygon(aoi_coords)

        if date_range is None:
            date_range = self.date_range
        df = extract_features(self.collection, aoi, date_range, resolution)
        return df



if __name__ == '__main__':
    # yaml_file = 'weather_config.yml'
    # composite_collection = CompositeCollection(yaml_file)

    # from time import time
    # start = time()

    # parallel_executor(composite_collection.extract, [[[-98.114, 41.855]]]*10, method = 'Thread', return_value=True, max_workers=40)

    # end = time()
    # print(end - start)
    
    col = CompositeCollection('./landsat_lai.yml')
    df = col.extract([[-98.114, 41.855]])
    print(df)


    start, end = '2010-01-01', '2022-12-31'
    col =  ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')#.filterDate(start, end)
    tm = TimeSeries(col, ['SR_B4', 'SR_B5'])
    df = tm.extract([[-98.114, 41.855]], date_range = [start, end])
    print(df)