import os
import pandas as pd

class Soil:
    def __init__(self, soil_id=None, hydgrp=None, properties_df=None):
        """
        Initialize the Soil class with soil ID (mukey), hydrological group, and properties DataFrame.
        """
        self.soil_id = soil_id          # mukey
        self.hydgrp = hydgrp            # Hydrological group
        self.properties_df = properties_df  # DataFrame with soil properties

    @classmethod
    def from_sda(cls, query):
        """
        Class method to create a Soil object from Soil Data Access using a query.
        """
        # Assume SoilDataAccess is a module that provides soil data querying functionality
        merged = SoilDataAccess.query(query)
        
        # Process hydrological group
        merged['hydgrp'] = merged['hydgrp'].replace('', 'C').fillna('C').str.slice(stop=1)
        merged['Hydgrp_conv'] = merged['hydgrp'].map({'A': 1, 'B': 2, 'C': 3, 'D': 4})
        for col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0)
        
        # Create the properties DataFrame
        properties_df = pd.DataFrame({
            'Layer_number': merged['desgnvert'],
            'Layer_depth': merged['hzdepb_r'] * 0.01,
            'Bulk_Density': merged['dbthirdbar_r'],
            'Wilting_capacity': merged['wfifteenbar_r'] * 0.01,
            'Field_Capacity': merged['wthirdbar_r'] * 0.01,
            'Sand_content': merged['sandtotal_r'],
            'Silt_content': merged['silttotal_r'],
            'N_concen': 0,
            'pH': merged['ph1to1h2o_r'],
            'Sum_Bases': merged['sumbases_r'],
            'Organic_Carbon': merged['om_r'] * 0.58,
            'Calcium_Carbonate': merged['caco3_r'],
            'Cation_exchange': merged['cec7_r'],
            'Course_Fragment': 100 - (merged['sieveno10_r'] + merged['fraggt10_r'] + merged['frag3to10_r']),
            'cnds': 0,
            'pkrz': 0,
            'rsd': 0,
            'Bulk_density_dry': merged['dbovendry_r'],
            'psp': 0,
            'Saturated_conductivity': merged['ksat_r'] * 3.6,
            'albedo': merged['albedodry_r'] * 0.625,
            'slope_length': merged['slopelenusle_r'],
            'hydgrp_conv': merged['Hydgrp_conv']
        })
        
        # Process the properties DataFrame
        properties_df['rounded_layer'] = (properties_df['Layer_depth'] * 10).round() / 10
        properties_df = properties_df.groupby(['rounded_layer']).median().reset_index()
        properties_df = properties_df.drop(columns=['rounded_layer'])
        properties_df = properties_df.round(4)
        
        # Get mukey and hydgrp from merged DataFrame
        soil_id = int(merged['mukey'].iloc[0])
        hydgrp = merged['hydgrp'].iloc[0]
        
        return cls(soil_id=soil_id, hydgrp=hydgrp, properties_df=properties_df)
    
    def save(self, filepath, template=None):
        """
        Save the soil data to a file using a template.
        """
        if self.properties_df is None:
            raise ValueError("Soil properties DataFrame is empty. Nothing to save.")
        
        if template is not None:
            template_lines = template.copy()
        else:
            with open(f'{os.path.dirname(__file__)}/template.sol', 'r') as file:
                template_lines = file.readlines()
        
        # Prepare header
        template_lines[0] = f"ID: {self.soil_id}\n"
        template_lines[1] = '{:8.3f}{:8.3f}'.format(self.properties_df['albedo'].iloc[0], self.properties_df['hydgrp_conv'].iloc[0]) + template_lines[1][16:]
        template_lines[2] = '{:8.3f}'.format(len(self.properties_df)) + template_lines[2][8:]
        
        # Generate lines for each soil layer
        # Ensure columns are in the correct order
        columns_order = [
            'Layer_depth', 'Bulk_Density', 'Wilting_capacity', 'Field_Capacity',
            'Sand_content', 'Silt_content', 'N_concen', 'pH', 'Sum_Bases',
            'Organic_Carbon', 'Calcium_Carbonate', 'Cation_exchange', 'Course_Fragment',
            'cnds', 'pkrz', 'rsd', 'Bulk_density_dry', 'psp', 'Saturated_conductivity',
            'albedo', 'slope_length', 'hydgrp_conv'
        ]
        self.properties_df = self.properties_df[columns_order]
        vals = self.properties_df.values.T
        len_rows = len(vals)
        for i in range(len_rows):
            template_lines[3 + i] = ''.join([f'{val:8.3f}' for val in vals[i]]) + '\n'
        
        # Fill remaining lines with zeros
        padding = ['{:8.3f}'.format(0) for _ in range(len(columns_order))]
        for i in range(len_rows + 3, 45):
            template_lines[i] = ''.join(padding) + '\n'
        
        # Write to file
        with open(filepath, 'w+') as file:
            file.writelines(template_lines)
    
    @classmethod
    def load(cls, filepath):
        """
        Load soil data from a file and return a Soil object.
        """
        with open(filepath, 'r') as file:
            lines = file.readlines()
        
        # Parse soil_id from the first line
        first_line = lines[0]
        soil_id_str = first_line.strip().split(":")[1].strip()
        soil_id = int(soil_id_str)
        
        # Parse hydgrp_conv from the second line
        second_line = lines[1]
        hydgrp_conv_str = second_line[8:16].strip()
        hydgrp_conv = float(hydgrp_conv_str)
        # Map hydgrp_conv back to hydgrp
        hydgrp_map = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
        hydgrp = hydgrp_map.get(int(hydgrp_conv), 'C')  # Default to 'C' if not found
        
        # Read properties
        # Number of layers from third line
        third_line = lines[2]
        num_layers_str = third_line[0:8].strip()
        num_layers = int(float(num_layers_str))
        
        # Read layer data
        # Each layer has values per line, starting from line index 3
        properties_data = []
        for i in range(num_layers):
            line_index = 3 + i
            line = lines[line_index]
            # Assuming each value is 8 characters long
            num_values = len(line.strip()) // 8
            values = [float(line[j*8:(j+1)*8]) for j in range(num_values)]
            properties_data.append(values)
        
        # Create properties DataFrame
        columns = [
            'Layer_depth', 'Bulk_Density', 'Wilting_capacity', 'Field_Capacity',
            'Sand_content', 'Silt_content', 'N_concen', 'pH', 'Sum_Bases',
            'Organic_Carbon', 'Calcium_Carbonate', 'Cation_exchange', 'Course_Fragment',
            'cnds', 'pkrz', 'rsd', 'Bulk_density_dry', 'psp', 'Saturated_conductivity',
            'albedo', 'slope_length', 'hydgrp_conv'
        ]
        properties_df = pd.DataFrame(properties_data, columns=columns)
        
        return cls(soil_id=soil_id, hydgrp=hydgrp, properties_df=properties_df)

