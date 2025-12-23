import os
import shutil
import subprocess
# from glob import glob
# import pandas as pd
import numpy as np
from geoEpic.io import ConfigParser
import platform
from geoEpic.utils import FileLockHandle
from datetime import datetime, date
from weakref import finalize

class EPICModel:
    """
    This class handles the setup and execution of the EPIC model executable.

    Attributes:
        base_dir (str): The base directory for model runs.
        executable (str): Path to the executable model file.
        output_dir (str): Directory to store model outputs.
        log_dir (str): Directory to store logs.
        start_date (datetime.date): The start date of the EPIC model simulation.
        duration (int): The duration of the EPIC model simulation in years.
        output_types (list): A list of enabled output types for the EPIC model.
        model_dir (str): Directory path where the executable is located.
        executable_name (str): Name of the executable file.
    """

    # Class attributes for line numbers
    PF_TOG1 = 14  # Line number for the first toggle in the print file
    PF_TOG2 = 15  # Line number for the second toggle in the print file
    PF_EXT1 = -2  # Line number for the first extension in the print file (counting from the end)
    PF_EXT2 = -1  # Line number for the second extension in the print file (counting from the end)
    EC_IRR = 3    # Line number for irrigation settings in the EPICCONT.DAT file
    EC_NIT = 4    # Line number for nitrogen settings in the EPICCONT.DAT file

    def __init__(self, path_to_executable):
        """
        Initialize an EPICModel instance with the path to the executable model.

        Args:
            path_to_executable (str): Path to the executable model file.
        """
        self.base_dir = os.path.abspath(os.getcwd())
        self.executable = os.path.abspath(path_to_executable)
        self._model_dir = os.path.dirname(self.executable)
        self.path = os.path.dirname(self.executable)
        self.executable_name = os.path.basename(self.executable)
        self._start_date = None
        self._duration = None
        self.output_dir = os.path.dirname(self._model_dir)
        self.log_dir = os.path.dirname(self._model_dir)
        # Load file names from EPICFILE.DAT
        self._load_file_names()
        self.get_output_types()
        # Ensure ACY and DGN are always enabled by default
        for default_type in ['ACY', 'DGN']:
            if default_type not in self._output_types:
                self._output_types.append(default_type)
        self.set_output_types(self._output_types)

        if platform.system() != "Windows":
            # On Unix-like systems, use chmod to make the file executable
            subprocess.Popen(f'chmod +x {self.executable}', shell=True).wait()

        # Define the path to the RAM-backed filesystem
        self.cache_path = os.path.join(self.base_dir, '.cache')#'/dev/shm'  # On Linux systems
        # Delete Site Simulation folder in cache after runs
        self.delete_after_run = True
        
        # Automatically acquire the lock when the instance is created
        self._model_lock = FileLockHandle(self._model_dir)
        self._model_lock.acquire()
        
        # Use weakref finalizer instead of __del__
        self._finalizer = finalize(self, self.close)
        
    def close(self):
        """Release the lock on the model's directory by deleting the lock file."""
        self._model_lock.release()
        self._model_dir = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def model_dir(self):
        if self._model_dir is None:
            raise RuntimeError("Model closed or not initialized.")
        return self._model_dir

    @property
    def start_date(self):
        """
        Get the start date of the EPIC model simulation.

        Returns:
            datetime.date: The start date of the simulation.
        """
        epiccont_path = os.path.join(self.model_dir, 'EPICCONT.DAT')
        with open(epiccont_path, 'r') as file:
            line = file.readline()
            # Read by fixed 4-char positions: duration[0:4], year[4:8], month[8:12], day[12:16]
            year = int(line[4:8].strip())
            month = int(line[8:12].strip())
            day = int(line[12:16].strip())
            self._start_date = date(year, month, day)
        return self._start_date

    @start_date.setter
    def start_date(self, value):
        """
        Set the start date of the EPIC model simulation.

        Args:
            value (datetime.date, datetime.datetime, or str): The new start date to set. 
                If a string is provided, it should be in the format 'YYYY-MM-DD'.
                If a datetime object is provided, it will be converted to date.
        """
        if isinstance(value, str):
            try:
                parsed_date = datetime.strptime(value, '%Y-%m-%d')
                value = parsed_date.date()
            except ValueError:
                raise ValueError("Invalid date string. Please use the format 'YYYY-MM-DD'.")
        elif isinstance(value, datetime):
            value = value.date()
        
        if not isinstance(value, date):
            raise TypeError("Start date must be a datetime.date object, datetime.datetime object, or a string in 'YYYY-MM-DD' format.")
        
        self._start_date = value
        epiccont_path = os.path.join(self.model_dir, 'EPICCONT.DAT')
        with open(epiccont_path, 'r+') as file:
            lines = file.readlines()
            line0 = lines[0]
            # Read first 4 chars as duration (preserve it), replace chars 4-16 with year/month/day
            duration_part = line0[0:4]  # Keep original duration
            rest_of_line = line0[16:] if len(line0) > 16 else '\n'
            # Format year, month, day each as 4 chars
            formatted = f"{duration_part}{value.year:4d}{value.month:4d}{value.day:4d}"
            lines[0] = formatted + rest_of_line
            file.seek(0)
            file.writelines(lines)
            file.truncate()

    @property
    def duration(self):
        """
        Get the duration of the EPIC model simulation.

        Returns:
            int: The duration of the simulation in years.
        """
        epiccont_path = os.path.join(self.model_dir, 'EPICCONT.DAT')
        with open(epiccont_path, 'r') as file:
            line = file.readline()
            # Read by fixed 4-char position: duration[0:4]
            self._duration = int(line[0:4].strip())
        return self._duration

    @duration.setter
    def duration(self, value):
        """
        Set the duration of the EPIC model simulation.

        Args:
            value (int): The new duration to set in years.
        """
        self._duration = value
        epiccont_path = os.path.join(self.model_dir, 'EPICCONT.DAT')
        with open(epiccont_path, 'r+') as file:
            lines = file.readlines()
            line0 = lines[0]
            # Only replace first 4 chars (duration), keep rest unchanged
            rest_of_line = line0[4:] if len(line0) > 4 else '\n'
            lines[0] = f"{value:4d}" + rest_of_line
            file.seek(0)
            file.writelines(lines)
            file.truncate()

    @property
    def output_types(self):
        """
        Get the current output types of the EPIC model.

        Returns:
            list: A list of enabled output types.
        """
        return self.get_output_types()

    def get_output_types(self):
        print_file_path = os.path.join(self.model_dir, self.file_names['FPRNT'])
        with open(print_file_path, 'r') as file:
            lines = file.readlines()
        exts = lines[self.PF_EXT1].replace('*', ' ').strip().split() + lines[self.PF_EXT2].replace('*', ' ').strip().split()
        toggles = lines[self.PF_TOG1].strip().split() + lines[self.PF_TOG2].strip().split()
        self._output_types = [ext.upper() for ext, toggle in zip(exts, toggles) if toggle == '1']
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
        self.file_names = {}
        epicfile_path = os.path.join(self.model_dir, 'EPICFILE.DAT')
        with open(epicfile_path, 'r') as f:
            lines = f.readlines()
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
        # Only set if config explicitly provides a value (avoid read-then-write)
        if 'start_date' in config and config['start_date'] is not None:
            self.start_date = config['start_date']
        if 'duration' in config and config['duration'] is not None:
            self.duration = config['duration']
        
        self.output_dir = os.path.abspath(config.get('output_dir', self.output_dir))
        self.log_dir = os.path.abspath(config.get('log_dir', self.log_dir))
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
        
        if 'output_types' in config and config['output_types'] is not None:
            self.set_output_types(config['output_types'])

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
        instance.base_dir = os.path.abspath(config.dir)
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
        print_file_path = os.path.join(self.model_dir, self.file_names['FPRNT'])
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
            
    def run(self, site, verbose = False, dest = None):
        """
        Execute the model for the given site and handle output files.

        Args:
            site (Site): A site instance containing site-specific configuration.
            dest (str, optional): Destination directory for the run. If None, a temporary directory is used.

        Raises:
            Exception: If any output file is not generated or is empty.
        """
        fid = site.site_id
        dly = site.get_dly()
        if dest is not None:
            new_dir = dest
        else:
            new_dir = os.path.join(self.cache_path, 'EPICRUNS', str(fid))
        
        new_dir = os.path.abspath(new_dir)

        # Check if required outputs already exist in output_dir
        
        if 'ACY' not in self._output_types:
            self._output_types.append('ACY')
        out_root = self.output_dir if dest is None else dest
        all_outputs_exist = True
        for out_type in self._output_types:
            out_name = f"{fid}.{out_type}"
            dst = os.path.join(out_root, out_name)
            if not os.path.exists(dst) or os.path.getsize(dst) == 0:
                all_outputs_exist = False
                break
        
        # If all required outputs exist, populate site.outputs and return without executing
        if all_outputs_exist:
            for out_type in self._output_types:
                out_name = f"{fid}.{out_type}"
                dst = os.path.join(out_root, out_name)
                site.outputs[out_type] = dst
            if verbose:
                print(f"All required outputs for site {fid} already exist. Skipping execution.")
            return

        if os.path.exists(new_dir):
            shutil.rmtree(new_dir)

        shutil.copytree(self.model_dir, new_dir, ignore=lambda _, files: ['.lock'])
        
        try:
            # Prepare weather data directly into new_dir (APIs accept a PATH)
            dly.save(os.path.join(new_dir, '1'))
            dly.to_monthly(os.path.join(new_dir, '1'))

            # Copy virtual links and write configuration files into new_dir
            self._writeDATFiles(site.copy(new_dir), new_dir)
            
            # Build paths (all absolute)
            log_file = os.path.join(new_dir, f"{fid}.log")
            exe_src = os.path.join(new_dir, self.executable_name)
            exe_base, exe_ext = os.path.splitext(os.path.basename(self.executable_name))
            executable_with_site_id = os.path.join(new_dir, f"{exe_base}_{fid}{exe_ext}")

            # Copy/rename the executable inside the run directory
            shutil.copy2(exe_src, executable_with_site_id)
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    [executable_with_site_id],
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=log,
                    cwd=new_dir,
                    shell=False,
                )
                # Feed newlines in case the binary pauses on errors.
                process.communicate(input=(b'\r\n' * 20))
            
            # Process output files
            if not os.path.exists(out_root):
                os.makedirs(out_root, exist_ok=True)

            # Process output files
            for out_type in self._output_types:
                out_name = f"{fid}.{out_type}"
                out_path = os.path.join(new_dir, out_name)
                if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
                    log_file_dst = os.path.join(self.log_dir, f"{fid}.log")
                    shutil.move(log_file, log_file_dst)
                    raise FileNotFoundError(f"Output file ({out_type}) not found or empty. \n Check {log_file_dst} for details")
                dst = os.path.join(out_root, out_name)
                shutil.move(out_path, dst)
                site.outputs[out_type] = dst
        finally:
            # Clean up
            if self.delete_after_run or self.cache_path == '/dev/shm':
                try: shutil.rmtree(new_dir)
                except Exception: pass

    def _writeDATFiles(self, site, dest = None):
        """
        Write configuration data files required for the model run.

        Args:
            site (Site): A Site object for which data files are being prepared.
            dest (str, optional): Destination directory to write files. If None, writes to current directory.
        """
        # Determine the base directory for file operations
        base_dir = dest if dest is not None else '.'
        
        with open(os.path.join(base_dir, 'EPICRUN.DAT'), 'w') as ofile:
            fmt = '%s 1  0  0  0  1  1  1/'%(site.site_id)
            ofile.write(fmt)

        with open(os.path.join(base_dir, self.file_names['FSITE']), 'w') as ofile:
            fmt = '1    "./%s"\n' % (os.path.basename(site.sit_path))
            ofile.write(fmt)

        with open(os.path.join(base_dir, self.file_names['FSOIL']), 'w') as ofile:
            fmt = '1    "./%s"\n' % (os.path.basename(site.sol_path))
            ofile.write(fmt)

        with open(os.path.join(base_dir, self.file_names['FWLST']), 'w') as ofile:
            ofile.write('1    1.DLY\n')

        with open(os.path.join(base_dir, self.file_names['FWPM1']), 'w') as ofile:
            fmt = '1    1.WP1   %.2f   %.2f    %.2f\n' % (site.latitude, site.longitude, site.elevation)
            ofile.write(fmt)
        
        with open(os.path.join(base_dir, self.file_names['FWIND']), 'w') as ofile:
            fmt = '1    1.WND   %.2f   %.2f    %.2f\n' % (site.latitude, site.longitude, site.elevation)
            ofile.write(fmt)
            
        with open(os.path.join(base_dir, self.file_names['FOPSC']), 'w') as ofile:
            fmt = '1    "./%s"\n' % (os.path.basename(site.opc_path))
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
        epiccont_path = os.path.join(self.model_dir, 'EPICCONT.DAT')
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
        epiccont_path = os.path.join(self.model_dir, 'EPICCONT.DAT')
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
