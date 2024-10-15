import os
import shutil
import warnings
import pandas as pd
from functools import wraps
from geoEpic.io import DataLogger, ConfigParser
from geoEpic.utils import parallel_executor, filter_dataframe
from .model import EPICModel
from .site import Site
import geopandas as gpd
from glob import glob
from geoEpic.utils.redis import WorkerPool
from shortuuid import uuid 
import signal
import atexit
import subprocess

class Workspace:
    """
    A class to manage the workspace for running simulations, handling configurations,
    and logging results.

    Attributes:
        config (dict): Configuration data loaded from a config file.
        base_dir (str): Base directory for the workspace.
        routines (dict): Dictionary to store functions as routines.
        objective_function (callable): Function to be executed as the objective.
        dataframes (dict): Cache for dataframes.
        delete_after_use (bool): Whether to delete temporary files after use.
        model (EPICModel): Instance of the EPIC model.
        data_logger (DataLogger): Instance of the DataLogger for logging data.
        run_info (pandas.DataFrame): DataFrame containing run information.
    """

    def __init__(self, config_path, cache_path = None):
        """
        Initialize the Workspace with a configuration file.

        Args:
            config_path (str): Path to the configuration file.
            cache_path (str): Path to store cahe, /dev/shm by default
        """
        config = ConfigParser(config_path)
        self.config = config.as_dict()
        self.base_dir = config.dir
        self.routines = {}
        self.objective_function = None
        self.dataframes = {}
        self.delete_after_use = True
        self.model = EPICModel.from_config(config_path)
        if cache_path is None:
            cache_path = '/dev/shm' 
        self.uuid = uuid()
        self.cache = os.path.join(cache_path, 'geo_epic', self.uuid)
        os.makedirs(self.cache, exist_ok=True)
        self._process_run_info(self.config['run_info'])
        self.data_logger = DataLogger(self.cache)
        model_pool = WorkerPool(self.uuid, os.path.join(self.cache, 'EPICRUNS'))
        model_pool.open(self.config["num_of_workers"]*2)
        
        if self.config["num_of_workers"] > os.cpu_count():
            warning_msg = (f"Workers greater than number of CPU cores ({os.cpu_count()}).")
            warnings.warn(warning_msg, RuntimeWarning)
        
        # Capture exit signals and clean up cahe
        atexit.register(self.cache_cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        '''Clean up cache while exiting'''
        self.cache_cleanup()
        exit(0)
    
    def cache_cleanup(self):
        model_pool = WorkerPool(self.uuid, os.path.join(self.cache, 'EPICRUNS'))
        model_pool.close()
        shutil.rmtree(self.cache)
    
    def _process_run_info(self, file_path):
        """
        Process the run information file, filtering and preparing data based on the file type.

        Args:
            file_path (str): Path to the CSV or SHP file containing run information.

        Raises:
            ValueError: If the file format is unsupported or required columns are missing.
        """
        if file_path.lower().endswith('.csv'):
            data = pd.read_csv(file_path)
            required_columns_csv = {'SiteID', 'soil', 'opc', 'dly', 'lat', 'lon'}
            if not required_columns_csv.issubset(set(data.columns.str)):
                raise ValueError("CSV file missing one or more required columns: 'SiteID', 'soil', 'opc', 'dly', 'lat', 'lon'")
        elif file_path.lower().endswith('.shp'):
            data = gpd.read_file(file_path)
            data = data.to_crs(epsg=4326)  # Convert to latitude and longitude projection
            data['lat'] = data.geometry.centroid.y
            data['lon'] = data.geometry.centroid.x
            required_columns_shp = {'SiteID', 'soil', 'opc', 'dly'}
            if not required_columns_shp.issubset(set(data.columns.str)):
                raise ValueError("Shapefile missing one or more required attributes: 'SiteID', 'soil', 'opc', 'dly'")
            data.drop(columns=['geometry'], inplace=True)
        else:
            raise ValueError("Unsupported file format. Please provide a '.csv' or '.shp' file.")
        
        # Check for OPC files
        opc_files = glob(f'{self.config["opc_dir"]}/*.OPC')
        present = [os.path.basename(f).split('.')[0] for f in opc_files]

        # Filter data to include only rows where 'opc' value has a corresponding .OPC file
        initial_count = len(data)
        data = data.loc[data['opc'].astype(str).isin(present)]
        final_count = len(data)

        # Check if the count of valid OPC files is less than the initial count of data entries
        if final_count < initial_count:
            missing_count = initial_count - final_count
            warning_msg = f"Warning: {missing_count} sites will not run due to missing .OPC files."
            warnings.warn(warning_msg, RuntimeWarning)
        path = os.path.join(self.cache, "info.csv")
        data.to_csv(path, index = False)
        self.run_info = path

    def logger(self, func):
        """
        Decorator to log the results of a function.

        Args:
            func (callable): The function to be decorated.

        Returns:
            callable: The decorated function that logs its output.
        """
        @wraps(func)
        def wrapper(site):
            result = func(site)
            if result is None: return
            elif not isinstance(result, dict):
                raise ValueError(f"{func.__name__} must return a dictionary.")
            self.data_logger.log_dict(func.__name__, {'SiteID': site.site_id, **result})
            return result

        self.routines[func.__name__] = wrapper
        return wrapper

    def objective(self, func):
        """
        Set the objective function to be executed after simulations.

        Args:
            func (callable): The objective function to be set.

        Returns:
            callable: The decorator function that sets the objective function.
        """
        @wraps(func)
        def wrapper(): return func()
        self.objective_function = wrapper
        return wrapper
    
    def fetch_log(self, func):
        """
        Retrieve the logs for a specific function.

        Args:
            func (str): The name of the function whose logs are to be retrieved.

        Returns:
            pandas.DataFrame: DataFrame containing the logs for the specified function.
        """
        return self.data_logger.get(func)

    def run_simulation(self, site_info):
        """
        Run simulation for a given site.

        Args:
            site_info (dict): Dictionary containing site information.
        """
        site = Site.from_config(self.config, **site_info)
        # Acquire a worker from the model pool
        model_pool = WorkerPool(self.uuid)
        dst_dir = model_pool.acquire()
        # Run the model and routines for the site
        self.model.run(site, dst_dir)
        # Release the worker back to the model pool
        model_pool.release(dst_dir)
        for func in self.routines.values():
            func(site)
        # Handle output files
        for out_path in site.outputs.values():
            if self.config['output_dir'] is None or (self.routines and self.delete_after_use):
                os.remove(out_path)
            else:
                dst = os.path.join(self.config['output_dir'], os.path.basename(out_path))
                shutil.move(out_path, dst)
                    

    def run(self, select_str = None, progress_bar = True):
        """
        Run simulations for all sites or filtered by a selection string.

        Args:
            select_str (str, optional): String to filter sites. Defaults to None.

        Returns:
            Any: The result of the objective function if set, otherwise None.
        """
        # Warn if outputs wont be saved
        if self.config['output_dir'] is None or (self.routines and self.delete_after_use):
            if progress_bar:
                print("Warning: Output files won't be saved")

        # Use provided select string or default from config
        select_str = select_str or self.config["select"]
        # Load and filter run information
        info = filter_dataframe(pd.read_csv(self.run_info), select_str)
        info_ls = info.to_dict('records')

        # Run first simulation for error check, if progress bar is enabled
        if progress_bar: self.run_simulation(info_ls.pop(0))
        # Execute simulations in parallel
        parallel_executor(
            self.run_simulation, 
            info_ls, 
            method='Process',
            max_workers=self.config["num_of_workers"],
            timeout=self.config["timeout"],
            bar=int(progress_bar)
        )

        # Return result of objective function if defined, else None
        return self.objective_function() if self.objective_function else None
    
    def clear_logs(self):
        """
        Clear all log files and temporary run directories.
        """
        log_dir = self.config.get('log_dir')
        if log_dir and os.path.exists(log_dir):
            subprocess.run(f"rm -rf {os.path.join(log_dir, '*')}", shell=True, check=True)

    def clear_outputs(self):
        """
        Clear all output files.
        """
        output_dir = self.config.get('output_dir')
        if output_dir and os.path.exists(output_dir):
            subprocess.run(f"rm -rf {os.path.join(output_dir, '*')}", shell=True, check=True)