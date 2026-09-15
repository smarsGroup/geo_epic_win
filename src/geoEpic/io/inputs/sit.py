import os
import numpy as np
import pandas as pd

from geoEpic.epicfiles import sit as light_sit

class SIT:
    def __init__(self, *args, **kwargs):
        """
        Initialize the SiteFile class.

        Supports two calling styles:
        1. SIT(elevation, slope) - as shown in PDF documentation
        2. SIT(site_info=dict) - for backward compatibility
        3. SIT({'elevation': val, 'slope_steep': val}) - dict as positional arg

        Parameters:
            elevation (float): Elevation in meters (first positional arg)
            slope (float): Slope steepness (second positional arg)
            site_info (dict): Dictionary containing site information (keyword arg)
        """
        self.template = []
        
        # Default site_info
        self.site_info = {
            "ID": 'Ne2',
            "lat": 0,
            "lon": 0,
            "elevation": 0,
            "slope_length": 0.0,
            "slope_steep": 0.0
        }

        # Parse arguments - support both calling styles
        if len(args) == 1 and isinstance(args[0], dict):
            # Called as SIT(site_info_dict)
            self.site_info.update(args[0])
        elif len(args) >= 1:
            # Called as SIT(elevation) or SIT(elevation, slope)
            self.site_info["elevation"] = float(args[0])
            if len(args) >= 2:
                self.site_info["slope_steep"] = float(args[1])
        
        # Also check for keyword arguments
        if 'site_info' in kwargs and kwargs['site_info'] is not None:
            self.site_info.update(kwargs['site_info'])
        if 'elevation' in kwargs:
            self.site_info["elevation"] = float(kwargs['elevation'])
        if 'slope' in kwargs:
            self.site_info["slope_steep"] = float(kwargs['slope'])
        

    @property
    def lat(self):
        """Get latitude value."""
        return self.site_info["lat"]
    
    @lat.setter
    def lat(self, value):
        """Set latitude value."""
        self.site_info["lat"] = float(value)
    
    @property
    def lon(self):
        """Get longitude value."""
        return self.site_info["lon"]
    
    @lon.setter
    def lon(self, value):
        """Set longitude value."""
        self.site_info["lon"] = float(value)

    @property
    def elevation(self):
        """Get elevation value."""
        return self.site_info["elevation"]
    
    @elevation.setter
    def elevation(self, value):
        """Set elevation value."""
        self.site_info["elevation"] = float(value)
    
    @property
    def slope(self):
        """Get slope steep value."""
        return self.site_info["slope_steep"]
    
    @slope.setter
    def slope(self, value):
        """Set slope steep value."""
        self.site_info["slope_steep"] = float(value)

    @classmethod
    def load(cls, file_path):
        """
        Class method to load the .sit file and return a SiteFile instance.

        Parameters:
        file_path (str): Path to the .sit file.

        Returns:
        SiteFile: An instance of the SiteFile class with loaded data.
        """
        instance = cls()
        with open(file_path, 'r') as file:
            instance.template = file.readlines()
            
        # print(file_path, instance.template)
        # Extract information based on the template positions
        instance.site_info["ID"] = instance.template[2].split(":")[1].strip()
        instance.site_info["lat"] = float(instance.template[3][0:8].strip())
        instance.site_info["lon"] = float(instance.template[3][8:16].strip())
        instance.site_info["elevation"] = float(instance.template[3][16:24].strip())
        instance.site_info["slope_length"] = float(instance.template[4][48:56].strip())
        instance.site_info["slope_steep"] = float(instance.template[4][56:64].strip())

        return instance

    def save(self, output_dir):
        """Save the current site information to a .SIT file.

        Rendering lives in the dependency-light writer so this class and the
        QGIS plugin cannot emit different bytes. Pinned by
        tests/fixtures/site_plain.SIT and site_edges.SIT.
        """
        if not self.site_info.get("ID"):
            raise ValueError("Site ID is not set. Cannot write to file.")
        if output_dir.endswith('.SIT') or output_dir.endswith('.sit'):
            output_file_path = output_dir.rsplit('.', 1)[0] + '.SIT'
        else:
            output_file_path = os.path.join(output_dir, f"{self.site_info['ID']}.SIT")
        directory = os.path.dirname(output_file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        light_sit.write(output_file_path, self.site_info,
                        template=self.template or None)

