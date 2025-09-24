import os
import numpy as np
import pandas as pd

class SIT:
    def __init__(self, site_info = None):
        """
        Initialize the SiteFile class with a dictionary of site information.

        Parameters:
        site_info (dict): Dictionary containing site information (optional).
        """
        # Load template from template.SIT file in the same directory as this Python file
        template_path = os.path.join(os.path.dirname(__file__), 'template.SIT')
        if os.path.exists(template_path):
            with open(template_path, 'r') as file:
                self.template = file.readlines()
        else:
            self.template = []
        
        self.site_info = {
            "ID": 'Ne2',
            "lat": 1,
            "lon": 1,
            "elevation": 1,
            "slope_length": 1,
            "slope_steep": 0.0
        }

        if site_info: self.site_info.update(site_info)
        

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
        """
        Save the current site information to a .SIT file.

        Parameters:
        output_dir (str): Directory where the .SIT file will be saved, or the full path including the .SIT extension.
        """
        try:
            if not self.site_info["ID"]:
                raise ValueError("Site ID is not set. Cannot write to file.")

            # Determine if output_dir already includes the .SIT extension
            if output_dir.endswith('.SIT'):
                output_file_path = output_dir
            elif output_dir.endswith('.sit'):
                output_file_path = output_dir[:-4] + '.SIT'
            else:
                output_file_path = os.path.join(output_dir, f"{self.site_info['ID']}.SIT")
            
            # Modify the template lines or create a new template if not read from a file
            if not self.template:
                self.template = [''] * 7  # Assuming the template has at least 7 lines
            
            # Ensure template has enough lines and none are None
            while len(self.template) < 7:
                self.template.append('')
            
            # Replace None values with empty strings
            for i in range(len(self.template)):
                if self.template[i] is None:
                    self.template[i] = ''
            
            self.template[0] = 'Crop Simulations\n'
            self.template[1] = 'Prototype\n'
            self.template[2] = f'ID: {self.site_info["ID"]}\n'
            
            # Handle template[3] - ensure it has enough characters or create default
            if len(self.template[3]) >= 24:
                self.template[3] = f'{self.site_info["lat"]:8.2f}{self.site_info["lon"]:8.2f}{self.site_info["elevation"]:8.2f}{self.template[3][24:]}'
            else:
                self.template[3] = f'{self.site_info["lat"]:8.2f}{self.site_info["lon"]:8.2f}{self.site_info["elevation"]:8.2f}\n'
            
            # Handle template[4] - ensure it has enough characters or create default
            if len(self.template[4]) >= 64:
                self.template[4] = f'{self.template[4][:48]}{self.site_info["slope_length"]:8.2f}{self.site_info["slope_steep"]:8.2f}{self.template[4][64:]}'
            else:
                # Create a default line with proper spacing
                padding = ' ' * 48  # 48 spaces before slope data
                self.template[4] = f'{padding}{self.site_info["slope_length"]:8.2f}{self.site_info["slope_steep"]:8.2f}\n'
            
            self.template[5] = '                                                   \n'
            # Write the modified template to the new file
            with open(output_file_path, 'w') as f:
                f.writelines(self.template)
        except:
            pass

        # print(f"File written to: {output_file_path}")