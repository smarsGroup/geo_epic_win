import os
from geoEpic.weather import DailyWeather
from geoEpic.io import DLY, SIT

class Site:
    """
    Represents a simulation site with paths to relevant operational files and site details.

    Attributes:
        opc_path (str): Path to the operational practice code file.
        dly_path (str): Path to the daily weather data file.
        sol_path (str): Path to the soil data file.
        sit_path (str): Path to the site information file.
        site_id (str): Identifier for the site, derived from the sit file name if not provided.
        outputs (dict): Dictionary to store output file paths.
        lat (float): Latitude of the site.
        lon (float): Longitude of the site.
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
        self.opc_path = opc
        self.dly_path = dly
        self.sol_path = sol
        self.sit_path = sit
        self.site_id = site_id
        self.outputs = {}

        if sit:
            if not site_id:
                self.site_id = os.path.basename(sit).split('.')[0]
            self.sit = SIT.load(self.sit_path)
            self.lat = self.sit.site_info.get('lat')
            self.lon = self.sit.site_info.get('lon')

    def __str__(self):
        return (f"Site ID: {self.site_id}\n"
                f"OPC Path: {self.opc_path}\n"
                f"DLY Path: {self.dly_path}\n"
                f"SOL Path: {self.sol_path}\n"
                f"SIT Path: {self.sit_path}")
    
    @classmethod
    def from_config(cls, config, **site_info):
        """
        Factory method to create a Site instance from a configuration dictionary and additional site information.

        Args:
            config (dict): Configuration dictionary with paths and settings.
            **site_info (dict): Keyword arguments containing site-specific information such as 'opc', 'dly', 'soil', and 'SiteID'.

        Returns:
            Site: An instance of the Site class configured according to the provided settings.
        """
        # Validate all necessary components are present before setting paths
        opc_path = None
        if 'opc' in site_info:
            opc_extension = '.OPC' if not str(site_info['opc']).lower().endswith('.opc') else ''
            opc_path = os.path.join(config['opc_dir'], f"{site_info['opc']}{opc_extension}")

        dly_path = None
        if 'dly' in site_info:
            dly_extension = '.DLY' if not str(site_info['dly']).lower().endswith('.dly') else ''
            dly_path = os.path.join(config['weather']['dir'], 'Daily', f"{site_info['dly']}{dly_extension}")

        sol_path = None
        if 'soil' in site_info:
            sol_extension = '.SOL' if not str(site_info['soil']).lower().endswith('.sol') else ''
            sol_path = os.path.join(config['soil']['files_dir'], f"{site_info['soil']}{sol_extension}")

        sit_path = os.path.join(config['site']['dir'], f"{site_info['SiteID']}.SIT")

        instance = cls(
            opc=opc_path,
            dly=dly_path,
            sol=sol_path,
            sit=None,
            site_id=site_info['SiteID']
        )

        # Assigning latitude and longitude if available
        instance.sit_path = os.path.join(config['site']['dir'], f"{site_info['SiteID']}.SIT")
        instance.lat = site_info['lat']
        instance.lon = site_info['lon']

        return instance
    
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
