import os
import pandas as pd
from geoEpic.soil.sda import SoilDataAccess

class SOL:
    def __init__(self, soil_id=None, albedo=None, hydgrp=None, num_layers=None, properties_df=None):
        """
        Initialize the Soil class with soil properties.

        Args:
            soil_id (int): Soil ID (mukey).
            albedo (float): Soil albedo.
            hydgrp (str): Hydrological group.
            num_layers (int): Number of soil layers.
            properties_df (pd.DataFrame): DataFrame with soil properties.
                Columns: Layer_depth, Bulk_Density, Wilting_capacity, Field_Capacity,
                Sand_content, Silt_content, N_concen, pH, Sum_Bases, Organic_Carbon,
                Calcium_Carbonate, Cation_exchange, Course_Fragment, cnds, pkrz, rsd,
                Bulk_density_dry, psp, Saturated_conductivity
        """
        self.soil_id = soil_id
        self.albedo = albedo
        self.hydgrp = hydgrp
        self.num_layers = num_layers
        self.properties_df = properties_df

    @classmethod
    def from_sda(cls, query):
        """
        Create a Soil object from Soil Data Access using a query.

        Args:
            query (int or str): Query string for SoilDataAccess. (mukey or WKT str)

        Returns:
            Soil: A new Soil object populated with data from SDA.
        """
        properties_df = SoilDataAccess.fetch_properties(query)
        
        soil_id = int(properties_df['mukey'].iloc[0])
        albedo = properties_df['albedo'].iloc[0]
        hydgrp = properties_df['hydgrp'].iloc[0]
        num_layers = len(properties_df)
        
        return cls(soil_id=soil_id, albedo=albedo, hydgrp=hydgrp, num_layers=num_layers, properties_df=properties_df)
    
    def save(self, filepath, template=None):
        """
        Save the soil data to a file using a template.

        Args:
            filepath (str): Path to save the soil file.
            template (list): Optional list of template lines.

        Raises:
            ValueError: If soil properties DataFrame is empty.
        """
        if self.properties_df is None:
            raise ValueError("Soil properties DataFrame is empty. Nothing to save.")
        
        if template is not None:
            template_lines = template.copy()
        else:
            with open(f'{os.path.dirname(__file__)}/template.SOL', 'r') as file:
                template_lines = file.readlines()
        
        template_lines[0] = f"ID: {self.soil_id}\n"
        hydgrp_conv = {'A': 1, 'B': 2, 'C': 3, 'D': 4}.get(self.hydgrp, 3)  # Default to 3 if not found
        template_lines[1] = '{:8.3f}{:8.3f}'.format(self.albedo, hydgrp_conv) + template_lines[1][16:]
        template_lines[2] = '{:8.3f}'.format(10) + template_lines[2][8:]
        
        columns_order = [
            'Layer_depth', 'Bulk_Density', 'Wilting_capacity', 'Field_Capacity',
            'Sand_content', 'Silt_content', 'N_concen', 'pH', 'Sum_Bases',
            'Organic_Carbon', 'Calcium_Carbonate', 'Cation_exchange', 'Course_Fragment',
            'cnds', 'pkrz', 'rsd', 'Bulk_density_dry', 'psp', 'Saturated_conductivity',
        ]
        self.properties_df = self.properties_df[columns_order]
        self.properties_df = self.properties_df.sort_values(by='Layer_depth', ascending=True)
        self.properties_df = self.properties_df.reset_index(drop=True)
        self.properties_df = self.properties_df.fillna(0)
        vals = self.properties_df.values.T
        len_rows = len(vals)
        for i in range(len_rows):
            template_lines[3 + i] = ''.join([f'{val:8.3f}' for val in vals[i]]) + '\n'
        
        padding = ['{:8.3f}'.format(0) for _ in range(23)]
        for i in range(len_rows + 3, 45):
            template_lines[i] = ''.join(padding[:self.num_layers]) + '\n'
        
        with open(filepath, 'w+') as file:
            file.writelines(template_lines)
    
    @classmethod
    def load(cls, filepath):
        """
        Load soil data from a file and return a Soil object.

        Args:
            filepath (str): Path to the soil file.

        Returns:
            Soil: A new Soil object populated with data from the file.
        """
        with open(filepath, 'r') as file:
            lines = file.readlines()
        
        soil_id = int(lines[0].strip().split(":")[1].strip())
        
        albedo = float(lines[1][0:8].strip())
        hydgrp_conv = float(lines[1][8:16].strip())
        hydgrp_map = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
        hydgrp = hydgrp_map.get(int(hydgrp_conv), 'C')
        
        num_layers = len(lines[3].split())
        
        properties_data = [[] for _ in range(num_layers)]
        for i in range(3, 3 + 19):
            line = lines[i]
            values = [float(line[i:i+8]) for i in range(0, len(line.strip()), 8)]
            for j, value in enumerate(values):
                if j < num_layers:
                    properties_data[j].append(value)
        max_length = max(len(prop) for prop in properties_data)
        properties_data = [prop + [None] * (max_length - len(prop)) for prop in properties_data]
        
        columns = [
            'Layer_depth', 'Bulk_Density', 'Wilting_capacity', 'Field_Capacity',
            'Sand_content', 'Silt_content', 'N_concen', 'pH', 'Sum_Bases',
            'Organic_Carbon', 'Calcium_Carbonate', 'Cation_exchange', 'Course_Fragment',
            'cnds', 'pkrz', 'rsd', 'Bulk_density_dry', 'psp', 'Saturated_conductivity',
        ]
        properties_df = pd.DataFrame(properties_data, columns=columns)
        
        return cls(soil_id=soil_id, albedo=albedo, hydgrp=hydgrp, num_layers=num_layers, properties_df=properties_df)


if __name__ == "__main__":
    s1 = SOL.load('template.SOL')
    print(s1.properties_df)
    s1.save('test2.SOL')