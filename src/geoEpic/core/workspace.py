import os
import shutil
import stat
import warnings
import pandas as pd
from functools import wraps
from geoEpic.io import DataLogger, ConfigParser
from geoEpic.utils import parallel_executor, run_with_timeout, filter_dataframe
from .model import EPICModel
from .site import Site
import geopandas as gpd
from glob import glob
# from geoEpic.utils.redis import WorkerPool
from shortuuid import uuid 
import weakref
# import subprocess
import platform
from .calibration import Problem_Wrapper
import time
import atexit
from weakref import finalize

class Workspace:
    """
    This class organises the workspace for executing simulations, saving required results.

    Attributes:
        uuid (str): Unique ID assigned to each workspace instance
        config (dict): Configuration data loaded from a config file.
        base_dir (str): Base directory for the workspace.
        routines (dict): Dictionary to store functions as routines.
        objective_function (callable): Function to be executed as the objective.
        dataframes (dict): Cache for dataframes.
        delete_after_use (bool): Whether to delete temporary files after use.
        model (EPICModel): Instance of the EPIC model.
        data_logger (DataLogger): Instance of the DataLogger for logging data.
    """

    def __init__(self, config_path, cache_path=None, debug=False):
        """
        Initialize the Workspace with a configuration file.

        Args:
            config_path (str): Path to the configuration file.
            cache_path (str): Path to store cahe, /dev/shm by default
            debug (bool): If True, print debug statements. Defaults to False.
        """
        self.debug = debug
        if self.debug:
            print(f"Initializing Workspace with config: {config_path}")
        self.uuid = uuid() 
        config = ConfigParser(config_path)
        self.config = config.as_dict()
        self.base_dir = config.dir
        self.routines = {}
        self.objective_function = None
        self.dataframes = {}
        self.delete_after_use = False
        
        if self.debug:
            print(f"Loading model from config...")
        self.model = EPICModel.from_config(config_path)
        
        # Create Cache folders on RAM or local storage
        username = os.getlogin()
        if cache_path is None: 
            if os.path.exists('/dev/shm'): cache_path = '/dev/shm'
            else: cache_path = os.path.join(self.base_dir, '.cache')
        self.cache = os.path.join(cache_path, f'geo_epic_{username}', self.uuid)
        os.makedirs(self.cache, exist_ok=True)
        if self.debug:
            print(f"Cache configured at: {self.cache}")
        self.model.cache_path = self.cache

        # Process run info
        if self.debug:
            print(f"Processing run info...")
        self._process_run_info(self.config['run_info'])

        # Initialise DataLogger
        # if platform.system() == "Windows":
        self.data_logger = DataLogger(self.cache, backend = 'sql')
        # else:
            # self.data_logger = DataLogger(self.cache, backend = 'redis')

        self.num_of_workers = 8

        # --- register cleanup WITHOUT capturing a bound method ---
        self_ref = weakref.ref(self)
        atexit.register(Workspace._cleanup_via_ref, self_ref)
        self._finalizer = finalize(self, Workspace._cleanup_via_ref, self_ref)

    @staticmethod
    def _cleanup_via_ref(self_ref):
        obj = self_ref()
        if obj is not None:
            obj.cache_cleanup()

    def close(self):
        """Explicit cleanup (use this in notebooks)."""
        self.cache_cleanup()
        # disarm finalizer so it won't run later
        if self._finalizer.alive: self._finalizer()

    def cache_cleanup(self):
        # Close resources first (important on Windows)
        if hasattr(self, 'model') and self.model:
            self.model.close()
        # Delete the cache (handles read-only files)
        if hasattr(self, 'cache') and self.cache and os.path.exists(self.cache):
            shutil.rmtree(self.cache)

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

    def routine(self, func):
        """
        Decorator to add a function as a routine without logging or returning values.

        Args:
            func (callable): The function to be decorated.

        Returns:
            callable: The decorated function that executes without logging.
        """
        @wraps(func)
        def wrapper(site): func(site)
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
    
    def fetch_log(self, func, keep = False):
        """
        Retrieve the logs for a specific function.

        Args:
            func (str): The name of the function whose logs are to be retrieved.
            keep (bool): If True, preserve the logs after retrieval. If False, logs are deleted after reading. Defaults to False.

        Returns:
            pandas.DataFrame: DataFrame containing the logs for the specified function.
        """
        return self.data_logger.get(func, keep)

    def run_simulation(self, site_or_info):
        """
        Run simulation for a given site or site information.

        Args:
            site_or_info (Site or dict): A Site object or a dictionary containing site information.

        Returns:
            dict: The results from the post-processing routines. Output files are saved based on the options selected
        """
        if isinstance(site_or_info, Site):
            site = site_or_info
        elif isinstance(site_or_info, dict):
            site = Site.from_config(self.config, **site_or_info)
        else:
            raise ValueError("Input must be a Site object or a dictionary containing site information.")

        self.model.run(site)
        
        # Post Process Simulation outcomes
        for func in self.routines.values():
            func(site)
        # Handle output files
        for out_path in site.outputs.values():
            if self.config['output_dir'] is None or (self.routines and self.delete_after_use):
                os.remove(out_path)
            else:
                dst = os.path.join(self.config['output_dir'], os.path.basename(out_path))
                shutil.move(out_path, dst)
        # return results
                    

    def run(self, select_str = None, progress_bar = True):
        """
        Run simulations for all sites or filtered by a selection string.

        Args:
            select_str (str, optional): String to filter sites. Defaults to None.

        Returns:
            Any: The result of the objective function if set, otherwise None.
        """
        if self.debug:
            print("Starting Workspace.run()...")
        if self.num_of_workers > os.cpu_count():
            warning_msg = (f"Workers greater than number of CPU cores ({os.cpu_count()}).")
            warnings.warn(warning_msg, RuntimeWarning)
            
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
        if progress_bar: 
            run_with_timeout(
                self.run_simulation, 
                args=(info_ls.pop(0),), 
                timeout=self.config["timeout"]
            )
        temp = self.model._model_lock
        self.model._model_lock = None
        # Execute simulations in parallel

        parallel_executor(
            self.run_simulation, 
            info_ls, 
            method='Thread',
            max_workers=self.num_of_workers,
            timeout=self.config["timeout"],
            bar=int(progress_bar),
            
        )
        # Sequential execution as fallback
        # for info in info_ls:
        #     self.run_simulation(info)
        self.model._model_lock = temp

        # Return result of objective function if defined, else None
        return self.objective_function() if self.objective_function else None
    
    def clear_logs(self):
        """
        Clear all log files and temporary run directories.
        """
        log_dir = self.config.get('log_dir')
        if log_dir and os.path.exists(log_dir):
            shutil.rmtree(log_dir)
            os.makedirs(log_dir)

    def clear_outputs(self):
        """
        Clear all output files.
        """
        output_dir = self.config.get('output_dir')
        if output_dir and os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)
    
    def make_problem(self, *dfs):
        """
        Create a PygmoProblem instance after validating inputs.

        Args:
            *dfs: Variable number of dataframes to pass to PygmoProblem

        Returns:
            PygmoProblem: A configured optimization problem instance

        Raises:
            ValueError: If no dataframes provided or if any dataframe lacks constraints
        """
        if self.objective_function is None:
            raise ValueError("Objective function not defined")
            
        if len(dfs) == 0:
            raise ValueError("At least one parameter object must be provided")
            
        for df in dfs:
            if not hasattr(df, 'constraints') or len(df.constraints()) == 0:
                raise ValueError("All parameter objects must have at least one sensitive variable")
        
        import pygmo as pg
        
        # Temporarily disable model lock to allow problem creation
        temp = self.model._model_lock
        self.model._model_lock = None
        # Create pygmo problem instance
        prob = Problem_Wrapper(self, *dfs)
        # Restore original model lock
        self.model._model_lock = temp
        # Return the problem instance, not the lock
        return prob
        
    

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
            required_columns_csv = {'SiteID', 'soil', 'dly', 'lat', 'lon'}
            if not required_columns_csv.issubset(set(data.columns)):
                raise ValueError("CSV file missing one or more required columns: 'SiteID', 'soil', 'opc', 'dly', 'lat', 'lon'")
        elif file_path.lower().endswith('.shp'):
            data = gpd.read_file(file_path)
            data = data.to_crs(epsg=4326)  # Convert to latitude and longitude projection
            data['lat'] = data.geometry.centroid.y
            data['lon'] = data.geometry.centroid.x
            required_columns_shp = {'SiteID', 'soil', 'dly'}
            if not required_columns_shp.issubset(set(data.columns)):
                raise ValueError("Shapefile missing one or more required attributes: 'SiteID', 'soil', 'opc', 'dly'")
            data.drop(columns=['geometry'], inplace=True)
        else:
            raise ValueError("Unsupported file format. Please provide a '.csv' or '.shp' file.")
        # Strip and normalize
        site_ids = data['SiteID'].astype(str).str.strip()
        # Vectorized checks
        invalid_mask = (data['SiteID'].isna() | (site_ids == '') | (~site_ids.str.match(r'^[A-Za-z0-9]+$')) | (site_ids.str.len() > 9))
        if invalid_mask.any():
            raise ValueError("Invalid SiteID: must be non-empty, alphanumeric and length ≤ 9")
        # write back to the DataFrame
        data['SiteID'] = site_ids  
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