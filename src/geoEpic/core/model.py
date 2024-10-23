import os
import shutil
import subprocess
# from glob import glob
# import pandas as pd
import numpy as np
from geoEpic.io import ConfigParser
import platform
import atexit
import signal     


class EPICModel:
    """
    A model class to handle the setup and execution of the EPIC model simulations.

    Attributes:
        base_dir (str): The base directory for model runs.
        executable (str): Path to the executable model file.
        path (str): Directory path where the executable is located.
        executable_name (str): Name of the executable file.
        output_dir (str): Directory to store model outputs.
        log_dir (str): Directory to store logs.
    """

    # Class attributes for line numbers
    PF_TOG1 = 14  # Line number for the first toggle in the print file
    PF_TOG2 = 15  # Line number for the second toggle in the print file
    PF_EXT1 = -2  # Line number for the first extension in the print file (counting from the end)
    PF_EXT2 = -1  # Line number for the second extension in the print file (counting from the end)
    EC_IRR = 3    # Line number for irrigation settings in the EPICCONT.DAT file
    EC_NIT = 4    # Line number for nitrogen settings in the EPICCONT.DAT file

    def __init__(self, path):
        """
        Initialize an EPICModel instance with the path to the executable model.

        Args:
            path (str): Path to the executable model file.
        """
        self.base_dir = os.getcwd()
        self.executable = path
        self.path = os.path.dirname(self.executable)
        self.executable_name = os.path.basename(self.executable)
        self._start_year = None
        self._duration = None
        self._output_types = None
        self.output_dir = os.path.dirname(self.path)
        self.log_dir = os.path.dirname(self.path)

        if platform.system() != "Windows":
            # On Unix-like systems, use chmod to make the file executable
            subprocess.Popen(f'chmod +x {self.executable}', shell=True).wait()

        # Define the path to the RAM-backed filesystem
        self.cache_path = os.path.join(self.base_dir, '.cache')#'/dev/shm'  # On Linux systems

        # Define the path to the lock file
        self.lock_file = os.path.join(self.path, '.model_lock')
        # Automatically acquire the lock when the instance is created
        self.acquire_lock()
        self.delete_after_run = True

        # register close to release it when the instance is deleted
        atexit.register(self.close)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Load file names from EPICFILE.DAT
        self._load_file_names()

    def _signal_handler(self, signum, frame):
        '''Release lock on exit'''
        self.close()

    def acquire_lock(self):
        """Acquire a lock on the model's directory by creating a lock file."""
        if os.path.exists(self.lock_file):
            raise RuntimeError(f"The model folder is currently in use by other process.")
    
        with open(self.lock_file, 'w') as f:
            f.write(f"Locked by process with PID {os.getpid()}")

    def close(self):
        """Release the lock on the model's directory by deleting the lock file."""
        os.remove(self.lock_file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def start_year(self):
        """
        Get the start year of the EPIC model simulation.

        Returns:
            int: The start year of the simulation.
        """
        with open('./EPICCONT.DAT', 'r') as file:
            line = file.readline()
            values = line.split()
            self._start_year = int(values[1])
        return self._start_year

    @start_year.setter
    def start_year(self, value):
        """
        Set the start year of the EPIC model simulation.

        Args:
            value (int): The new start year to set.
        """
        self._start_year = value
        with open('./EPICCONT.DAT', 'r+') as file:
            lines = file.readlines()
            values = lines[0].split()
            values[1] = f"{value:04d}"
            lines[0] = ' '.join(values) + '\n'
            file.seek(0)
            file.writelines(lines)

    @property
    def duration(self):
        """
        Get the duration of the EPIC model simulation.

        Returns:
            int: The duration of the simulation in years.
        """
        with open('./EPICCONT.DAT', 'r') as file:
            line = file.readline()
            values = line.split()
            self._duration = int(values[0])
        return self._duration

    @duration.setter
    def duration(self, value):
        """
        Set the duration of the EPIC model simulation.

        Args:
            value (int): The new duration to set in years.
        """
        self._duration = value
        with open('./EPICCONT.DAT', 'r+') as file:
            lines = file.readlines()
            values = lines[0].split()
            values[0] = f"{value:03d}"
            lines[0] = ' '.join(values) + '\n'
            file.seek(0)
            file.writelines(lines)

    @property
    def output_types(self):
        """
        Get the current output types of the EPIC model.

        Returns:
            list: A list of enabled output types.
        """
        print_file_path = os.path.join(self.path, self.file_names['FPRNT'])
        with open(print_file_path, 'r') as file:
            lines = file.readlines()
        exts = lines[self.PF_EXT1].replace('*', ' ').strip().split() + lines[self.PF_EXT2].replace('*', ' ').strip().split()
        toggles = lines[self.PF_TOG1].strip().split() + lines[self.PF_TOG2].strip().split()
        self._output_types = [ext for ext, toggle in zip(exts, toggles) if toggle == '1']
        return self._output_types

    @output_types.setter
    def output_types(self, value):
        """
        Set the output types for the EPIC model.

        Args:
            value (list): A list of output types to enable.
        """
        self.set_output_types(value)

    def _load_file_names(self):
        """Load file names from EPICFILE.DAT"""
        epicfile_path = os.path.join(self.path, 'EPICFILE.DAT')
        with open(epicfile_path, 'r') as f:
            lines = f.readlines()
        
        self.file_names = {}
        for line in lines:
            parts = line.split()
            if len(parts) == 2:
                self.file_names[parts[0]] = parts[1]

    def setup(self, config):
        """
        Set up the model run configurations based on provided settings.

        Args:
            config (dict): Configuration dictionary containing model settings.
        """
        self.start_year = config.get('start_year', 2014)
        self.duration = config.get('duration', 10)
        self.output_dir = config.get('output_dir', self.output_dir)
        self.log_dir = config.get('log_dir', self.log_dir)
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
        self.set_output_types(config.get('output_types', ['ACY']))

    @classmethod
    def from_config(cls, config_path):
        """
        Create an EPICModel instance from a configuration path.

        Args:
            config_path (str): Path to the configuration file.

        Returns:
            EPICModel: A configured instance of the EPICModel.
        """
        config = ConfigParser(config_path)
        instance = cls(config['EPICModel'])
        instance.base_dir = config.dir
        instance.setup(config)
        instance.set_output_types(config['output_types'])
        return instance

    def set_output_types(self, output_types):
        """
        Set the model output types and update the model's print file to enable specified outputs.

        Args:
            output_types (list of str): List of output types to be enabled.
        """
        self._output_types = output_types
        print_file_path = os.path.join(self.path, self.file_names['FPRNT'])
        outputs_to_enable = ' '.join(output_types).lower().split()
        with open(print_file_path, 'r') as file:
            lines = file.readlines()

        exts = lines[self.PF_EXT1].replace('*', ' ').strip().split() + lines[self.PF_EXT2].replace('*', ' ').strip().split()
        toggles = lines[self.PF_TOG1].strip().split() + lines[self.PF_TOG2].strip().split()

        for i, ext in enumerate(exts):
            toggles[i] = '1' if ext in outputs_to_enable else '0'

        lines[self.PF_TOG1] = '   ' + '   '.join(toggles[:len(lines[self.PF_TOG1].strip().split())]) + '\n'
        lines[self.PF_TOG2] = '   ' + '   '.join(toggles[len(lines[self.PF_TOG1].strip().split()):]) + '\n'
        with open(print_file_path, 'w') as file:
            file.writelines(lines)

    def run(self, site, dest = None):
        """
        Execute the model for the given site and manage outputs.

        This method performs the following steps:
        1. Set up the run directory
        2. Prepare the daily weather data
        3. Write necessary DAT files
        4. Run the EPIC executable
        5. Process and move output files
        6. Clean up temporary files

        Args:
            site (Site): A site instance containing site-specific configuration.
            dest (str, optional): Destination directory for the run. If None, a temporary directory is used.

        Raises:
            Exception: If any output file is not generated or is empty.
        """
        fid = site.site_id
        new_dir = os.path.join(self.cache_path, 'EPICRUNS', str(fid)) #if dest is None else dest

        if os.path.exists(new_dir):
            shutil.rmtree(new_dir)

        shutil.copytree(self.path, new_dir)
        os.chdir(new_dir)

        # Prepare weather data
        dly = site.get_dly()
        dly.save(fid)
        dly.to_monthly(fid)
        
        # Write configuration files
        self.writeDATFiles(site)

        # Run EPIC executable
        log_file = f"{fid}.out"
        with open(log_file, 'w') as log:
            subprocess.run([self.executable], stdout=log, stderr=log)

        # Process output files
        for out_type in self.output_types:
            out_path = f'{fid}.{out_type}'
            if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
                shutil.move(log_file, os.path.join(self.log_dir, f"{fid}.out"))
                os.chdir(self.base_dir)
                if self.delete_after_run or self.cache_path == '/dev/shm':
                    shutil.rmtree(new_dir)
                raise FileNotFoundError(f"Output file ({out_type}) not found or empty. Check {log_file} for details")
            dst = os.path.join(self.output_dir if dest is None else os.path.dirname(new_dir), out_path)
            shutil.move(out_path, dst)
            site.outputs[out_type] = dst

        # Clean up
        os.chdir(self.base_dir)
        if self.delete_after_run or self.cache_path == '/dev/shm':
            shutil.rmtree(new_dir)  

    def writeDATFiles(self, site):
        """
        Write configuration data files required for the model run.

        Args:
            site (Site): A Site object for which data files are being prepared.
        """
        with open('./EPICRUN.DAT', 'w') as ofile:
            fmt = '%8d %8d  0  0  0  %8d  %8d  %8d/'
            np.savetxt(ofile, [[int(site.site_id)]*5], fmt=fmt)

        with open(self.file_names['FSITE'], 'w') as ofile:
            fmt = '%8d    "%s"\n' % (site.site_id, site.sit_path)
            ofile.write(fmt)

        with open(self.file_names['FSOIL'], 'w') as ofile:
            fmt = '%8d    "%s"\n' % (site.site_id, site.sol_path)
            ofile.write(fmt)

        with open(self.file_names['FWLST'], 'w') as ofile:
            fmt = '%8d    "./%s.DLY"\n' % (site.site_id, site.site_id)
            ofile.write(fmt)

        with open(self.file_names['FWPM1'], 'w') as ofile:
            fmt = '%8d    "./%s.INP"   %.2f   %.2f  NB            XXXX\n' % (site.site_id, site.site_id, site.lon, site.lat)
            ofile.write(fmt)
        
        with open(self.file_names['FOPSC'], 'w') as ofile:
            fmt = '%8d    "%s"\n' % (site.site_id, site.opc_path)
            ofile.write(fmt)
    

    def auto_irrigation(self, bir, efi=None, vimx=None, armn=None, armx=None):
        """
        Update the irrigation settings in the EPICCONT.DAT file.
        Only BIR is required. Other parameters will be updated only if they are not None.

        :param file_path: Path to the EPICCONT.DAT file
        :param bir: Water stress factor to trigger automatic irrigation (BIR) - required
        :param efi: Runoff volume/Volume irrigation water applied (EFI) - optional
        :param vimx: Maximum annual irrigation volume (VIMX) in mm - optional
        :param armn: Minimum single application volume (ARMN) in mm - optional
        :param armx: Maximum single application volume (ARMX) in mm - optional
        """
        epiccont_path = os.path.join(self.path, 'EPICCONT.DAT')
        with open(epiccont_path, 'r+') as file:
            lines = file.readlines()
            if len(lines) < self.EC_IRR + 1:
                raise ValueError("File does not have enough lines to update irrigation parameters.")
            
            # Split existing line into list of values
            values = lines[self.EC_IRR].split()
            # Update mandatory BIR and optional parameters if provided
            values[5] = f"{bir:6.2f}"
            if efi is not None:
                values[6] = f"{efi:6.2f}"
            if vimx is not None:
                values[7] = f"{vimx:6.2f}"
            if armn is not None:
                values[8] = f"{armn:6.2f}"
            if armx is not None:
                values[9] = f"{armx:6.2f}"
            
            # Join back into a single string
            lines[self.EC_IRR] = '  ' + '  '.join([f"{float(v):6.2f}" for v in values]) + '\n'
            
            file.seek(0)
            file.writelines(lines)

    def auto_Nfertilization(self, bft0, fnp=None, fmx=None):
        """
        Update the nitrogen settings in the EPICCONT.DAT file.
        Only BFT0 is required. Other parameters will be updated only if they are not None.

        :param file_path: Path to the EPICCONT.DAT file
        :param bft0: Nitrogen stress factor to trigger auto fertilization (BFT0) - required
        :param fnp: Fertilizer application variable (FNP) - optional
        :param fmx: Maximum annual N fertilizer applied for a crop (FMX) - optional
        """
        epiccont_path = os.path.join(self.path, 'EPICCONT.DAT')
        with open(epiccont_path, 'r+') as file:
            lines = file.readlines()
            if len(lines) < self.EC_NIT + 1:
                raise ValueError("File does not have enough lines to update nitrogen parameters.")
            
            # Split existing line into list of values
            values = lines[self.EC_NIT].split()
            # Update mandatory BFT0 and optional parameters if provided
            values[0] = f"{bft0:6.2f}"
            if fnp is not None:
                values[1] = f"{fnp:6.2f}"
            if fmx is not None:
                values[2] = f"{fmx:6.2f}"
            
            # Join back into a single string
            lines[self.EC_NIT] = '  ' + '  '.join([f"{float(v):6.2f}" for v in values]) + '\n'
            
            file.seek(0)
            file.writelines(lines)
