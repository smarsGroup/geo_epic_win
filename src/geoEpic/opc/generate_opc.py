import pandas as pd
import numpy as np
import geopandas as gpd
from datetime import datetime, timedelta
import os
from geoEpic.utils import parallel_executor
from opc_class2 import OPC
from geoEpic.io import ConfigParser
import argparse
import sys

parser = argparse.ArgumentParser(description="OPC file creation utility")
parser.add_argument("-c", "--crop_data", default= "./crop_data.csv", help="Path to the year-wise crop data file")
parser.add_argument("-t", "--template", default= "./crop_templates", help="Path to the crop template folder")
parser.add_argument("-o", "--output", default= "./files", help="Path to the output folder")

args = parser.parse_args()
crop_data = args.crop_data
template_path = args.template
out_path = args.output
file_name = os.path.splitext(os.path.basename(crop_data))[0] + '.OPC'
if not os.path.isdir(out_path):
    file_name = os.path.basename(out_path)
    if not file_name.endswith('.OPC'):
        file_name = os.path.splitext(file_name)[0] + '.OPC'
    out_path = os.path.dirname(out_path)

# -------------------------------------------
# Validate CSV: Rename 'cdl_code' or 'epic_code' -> 'crop_code'
# -------------------------------------------
def validate_csv(file_path):
    try:
        # Read CSV file
        df = pd.read_csv(file_path)

        # Rename columns if needed
        if 'cdl_code' in df.columns:
            df.rename(columns={'cdl_code': 'crop_code'}, inplace=True)
        elif 'epic_code' in df.columns:
            df.rename(columns={'epic_code': 'crop_code'}, inplace=True)

        # Check required columns: crop_code and year must be present.
        required_columns = ['crop_code', 'year']
        for col in required_columns:
            if col not in df.columns:
                return False, f"Missing required column: {col}"

        # Validate crop_code and year (should be integer)
        if not pd.api.types.is_integer_dtype(df['crop_code']):
            return False, "crop_code column should contain integers"
        if not pd.api.types.is_integer_dtype(df['year']):
            return False, "year column should contain integers"

        # Optional: Validate date formats if planting_date and harvest_date exist
        date_columns = ['planting_date', 'harvest_date']
        for col in date_columns:
            if col in df.columns:
                try:
                    pd.to_datetime(df[col], format='%Y-%m-%d')
                except Exception as e:
                    return False, f"Column {col} should be in yyyy-mm-dd format"
        
        return True, "CSV file is valid", df

    except Exception as e:
        return False, f"An error occurred: {str(e)}", None

is_valid, message, crop_data_df = validate_csv(crop_data)
if not is_valid:
    print(f"crop_data is not valid: {message}")
    sys.exit()

# -------------------------------------------
# Validate Template Folder: Rename columns if necessary
# -------------------------------------------
def validate_template_folder(template_path):
    # Check if Mapping file exists
    mapping_file = os.path.join(template_path, 'MAPPING')
    if not os.path.isfile(mapping_file):
        return False, "Mapping file not found in the template folder"

    # Validate Mapping file contents
    try:
        df = pd.read_csv(mapping_file)
        # Rename if necessary
        if 'cdl_code' in df.columns:
            df.rename(columns={'cdl_code': 'crop_code'}, inplace=True)
        elif 'epic_code' in df.columns:
            df.rename(columns={'epic_code': 'crop_code'}, inplace=True)
        
        required_columns = ['crop_code', 'name']
        for col in required_columns:
            if col not in df.columns:
                return False, f"Mapping file is missing required column: {col}"

        if not pd.api.types.is_integer_dtype(df['crop_code']):
            return False, "crop_code column in Mapping file should contain integers"

    except Exception as e:
        return False, f"Error reading Mapping file: {str(e)}"

    # Check if FALLOW.OPC is present
    fallow_opc = os.path.join(template_path, 'FALLOW.OPC')
    if not os.path.isfile(fallow_opc):
        return False, "FALLOW.OPC file not found in the template folder. It's used as default OPC if crop_code is not present in template."

    return True, "Template folder validation successful"

is_valid, message = validate_template_folder(template_path)
if not is_valid:
    print(f"Template folder not valid: {message}")
    sys.exit()

# -------------------------------------------
# Get crop_code to template mapper
# -------------------------------------------
def get_crop_code_template_mapper(template_path):
    mapping_file_path = os.path.join(template_path, 'MAPPING')
    df = pd.read_csv(mapping_file_path)
    # Rename if necessary
    if 'cdl_code' in df.columns:
        df.rename(columns={'cdl_code': 'crop_code'}, inplace=True)
    elif 'epic_code' in df.columns:
        df.rename(columns={'epic_code': 'crop_code'}, inplace=True)
    mapper = dict(zip(df['crop_code'].astype(int), df['name']))
    return mapper

crop_code_mapper = get_crop_code_template_mapper(template_path)

# -------------------------------------------
# Build crop_info_list from CSV
# -------------------------------------------
crop_info_list = []
start_year = crop_data_df['year'].min()
end_year = crop_data_df['year'].max()

for year in range(start_year, end_year + 1):
    year_data = crop_data_df[crop_data_df['year'] == year]
    if not year_data.empty:
        crop_code = year_data.iloc[0]['crop_code']
        # Use get() to allow absence of planting_date/harvest_date
        planting_date = year_data.iloc[0].get('planting_date', None)
        harvest_date = year_data.iloc[0].get('harvest_date', None)
        template_code = crop_code_mapper.get(crop_code, 'FALLOW')
        crop_info_list.append({
            'name': template_code,
            'crop_code': crop_code,
            'planting_date': planting_date,
            'harvest_date': harvest_date,
            'year': year
        })
    else:
        crop_info_list.append({
            'name': 'FALLOW',
            'crop_code': None,
            'planting_date': None,
            'harvest_date': None,
            'year': year
        })

# -------------------------------------------
# Load OPC files and update crop season if dates are available
# -------------------------------------------
res_opc_file = None
for crop_info in crop_info_list:
    name = crop_info['name']
    crop_code = crop_info['crop_code']
    year_val = crop_info.get('year', datetime.now().year)
    # print(name, crop_code, year_val)

    # Try to parse dates if they are present and non-null
    if crop_info.get('planting_date') is not None and pd.notnull(crop_info.get('planting_date')):
        try:
            planting_date = datetime.strptime(crop_info['planting_date'], '%Y-%m-%d')
        except Exception as e:
            planting_date = None
    else:
        planting_date = None

    if crop_info.get('harvest_date') is not None and pd.notnull(crop_info.get('harvest_date')):
        try:
            harvest_date = datetime.strptime(crop_info['harvest_date'], '%Y-%m-%d')
        except Exception as e:
            harvest_date = None
    else:
        harvest_date = None

    # print(res_opc_file)
    
    if res_opc_file is None:
        res_opc_file = OPC.load(os.path.join(template_path, f'{name}.OPC'), year_val)
        res_opc_file.name = file_name
    else:
        template_opc = OPC.load(os.path.join(template_path, f'{name}.OPC'), year_val)
        res_opc_file = res_opc_file.append(template_opc)
        
    # Only edit crop season if both planting_date and harvest_date are provided
    if planting_date is not None and harvest_date is not None:
        res_opc_file.edit_crop_season(planting_date, harvest_date, crop_code)

res_opc_file.save(out_path)