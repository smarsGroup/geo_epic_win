import os
from geoEpic.io import DLY, SIT, OPC, SOL
from geoEpic.utils import copy_file

class Site:
    """
    Represents a site (ex: agricultural field) with paths to it's corresponding EPIC input files.

    Attributes:
        opc_path (str): Path to the operational practice code file.
        dly_path (str): Path to the daily weather data file.
        sol_path (str): Path to the soil data file.
        sit_path (str): Path to the site information file.
        site_id (str): Identifier for the site, derived from the sit file name if not provided.
        outputs (dict): Dictionary to store output file paths.
    """

    def __init__(self, opc=None, dly=None, sol=None, sit=None, site_id=None):
        """
        Initializes a Site instance with paths to its operational files.

        Args:
            opc (str, optional): Path to the OPC file.
            dly (str, optional): Path to the DLY file.
            sol (str, optional): Path to the SOL file.
            sit (str, optional): Path to the SIT file.
            site_id (str, optional): An explicit identifier for the site.
        """
        self.opc_path = os.path.abspath(opc) if opc else None
        self.dly_path = os.path.abspath(dly) if dly else None
        self.sol_path = os.path.abspath(sol) if sol else None
        self.sit_path = os.path.abspath(sit) if sit else None
        self.site_id = site_id
        self.outputs = {}

        if sit:
            if not site_id:
                self.site_id = os.path.basename(sit).split('.')[0]
            self.sit = SIT.load(self.sit_path)
    
    @classmethod
    def from_config(cls, config, **site_info):
        """
        Factory method to create a Site instance from a configuration dictionary and additional site information.

        Args:
            config (dict): Configuration dictionary with paths and settings.
            **site_info (dict): Keyword arguments containing site-specific information such as 'opc', 'dly', 'soil', 'SiteID', 'lat', 'lon', and 'ele'.

        Returns:
            Site: An instance of the Site class configured according to the provided settings.
        """
        site_id = site_info.get('SiteID')
        if not site_id:
            raise ValueError("Missing required field: SiteID")

        # Define file configurations
        file_configs = {
            'opc': {'dir': config['opc_dir'], 'ext': '.OPC'},
            'dly': {'dir': config['weather']['dir'], 'ext': '.DLY'},
            'soil': {'dir': config['soil']['files_dir'], 'ext': '.SOL'},
        }

        paths = {}
        for key, cfg in file_configs.items():
            name = str(site_info.get(key, site_id))
            if not name.lower().endswith(cfg['ext'].lower()):
                name += cfg['ext']
            paths[key] = os.path.join(cfg['dir'], name)

        # Handle 'sit' separately
        sit_path = os.path.join(config['site']['dir'], f"{site_id}.SIT")
        paths['sit'] = sit_path

        # Check for missing files
        missing_files = [f"{key.upper()} file not found: {path}" for key, path in paths.items() if not os.path.exists(path)]
        if missing_files:
            raise FileNotFoundError("Missing required files:\n" + "\n".join(missing_files))

        return cls(opc=paths['opc'], dly=paths['dly'], sol=paths['soil'], sit=paths['sit'], site_id=site_id)

    @property
    def latitude(self):
        """Latitude of the site."""
        if hasattr(self, 'sit'):
            return self.sit.site_info.get('lat')
        return None

    @property
    def longitude(self):
        """Longitude of the site."""
        if hasattr(self, 'sit'):
            return self.sit.site_info.get('lon')
        return None

    @property
    def elevation(self):
        """Elevation of the site."""
        if hasattr(self, 'sit'):
            return self.sit.site_info.get('elevation')
        return None
    
    def get_dly(self):
        """
        Retrieve daily weather data from a DLY file.

        Returns:
            DailyWeather: An instance of the DailyWeather class containing weather data.

        Raises:
            FileNotFoundError: If the DLY file does not exist at the specified path.
        """
        if self.dly_path and os.path.exists(self.dly_path):
            return DLY.load(self.dly_path)
        else:
            raise FileNotFoundError(f"The DLY file at {self.dly_path} does not exist.")

    def get_opc(self):
        """
        Retrieve operation schedule data from an OPC file.

        Returns:
            Operation: An instance of the Operation class containing operation schedule data.

        Raises:
            FileNotFoundError: If the OPC file does not exist at the specified path.
        """
        if self.opc_path and os.path.exists(self.opc_path):
            return OPC.load(self.opc_path)
        else:
            raise FileNotFoundError(f"The OPC file at {self.opc_path} does not exist.")

    def get_sol(self):
        """
        Retrieve soil data from a SOL file.

        Returns:
            Soil: An instance of the Soil class containing soil data.

        Raises:
            FileNotFoundError: If the SOL file does not exist at the specified path.
        """
        if self.sol_path and os.path.exists(self.sol_path):
            return SOL.load(self.sol_path)
        else:
            raise FileNotFoundError(f"The SOL file at {self.sol_path} does not exist.")

    def get_sit(self):
        """
        Retrieve site data from a SIT file.

        Returns:
            Site: An instance of the Site class containing site data.

        Raises:
            FileNotFoundError: If the SIT file does not exist at the specified path.
        """
        if self.sit_path and os.path.exists(self.sit_path):
            return SIT.load(self.sit_path)
        else:
            raise FileNotFoundError(f"The SIT file at {self.sit_path} does not exist.")
    
    def copy(self, dest_folder, use_symlink=False):
        """
        Copy or symlink site files to a destination folder.

        Args:
            dest_folder (str): Destination folder path
            use_symlinks (bool, optional): If True, create symbolic links instead of copying files. Defaults to False.

        Returns:
            Site: A new Site instance pointing to the copied/linked files
        """
        # Create destination folder if it doesn't exist
        os.makedirs(dest_folder, exist_ok=True)

        # Copy/link each file
        new_opc = copy_file(self.opc_path, os.path.join(dest_folder, os.path.basename(self.opc_path)), 
                           symlink=use_symlink) if self.opc_path else None
        new_dly = copy_file(self.dly_path, os.path.join(dest_folder, os.path.basename(self.dly_path)),
                           symlink=use_symlink) if self.dly_path else None
        new_sol = copy_file(self.sol_path, os.path.join(dest_folder, os.path.basename(self.sol_path)),
                           symlink=use_symlink) if self.sol_path else None
        new_sit = copy_file(self.sit_path, os.path.join(dest_folder, os.path.basename(self.sit_path)),
                           symlink=use_symlink) if self.sit_path else None

        # Create new Site instance with copied/linked files
        new_site = Site(opc=new_opc, dly=new_dly,
                        sol=new_sol, sit=new_sit,
                        site_id=self.site_id)
        
        return new_site
    
    def __str__(self):
        return (f"Site ID: {self.site_id}\n"
                f"OPC Path: {self.opc_path}\n"
                f"DLY Path: {self.dly_path}\n"
                f"SOL Path: {self.sol_path}\n"
                f"SIT Path: {self.sit_path}")
