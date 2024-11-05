import pandas as pd
import numpy as np
import geopandas as gpd
from datetime import datetime, timedelta
import os
from geoEpic.utils import parallel_executor
from geoEpic.io import OPC
from geoEpic.io import ConfigParser
import argparse
import sys

parser = argparse.ArgumentParser(description="soil file creation script")
parser.add_argument("-c", "--crop_data", default= "./crop_data.csv", help="Path to the cdl file")
parser.add_argument("-t", "--template", default= "./crop_templates", help="Path to the cdl file")
parser.add_argument("-o", "--output", default= "./files", help="Path to the cdl file")

args = parser.parse_args()

crop_data = args.crop_data
template_path = args.template
out_path = args.output

crop_data_df = pd.read_csv(crop_data)

def validate_csv(file_path):
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)

        # Check if all required columns are present
        required_columns = ['epic_code', 'planting_date', 'harvest_date', 'year']
        if not all(col in df.columns for col in required_columns):
            return False, "Missing one or more required columns"

        # Validate epic_code (should be int)
        if not pd.api.types.is_integer_dtype(df['epic_code']):
            return False, "epic_code column should contain integers"

        # Validate year (should be int)
        if not pd.api.types.is_integer_dtype(df['year']):
            return False, "year column should contain integers"

        # Validate date formats
        date_columns = ['planting_date', 'harvest_date']
        for col in date_columns:
            try:
                pd.to_datetime(df[col], format='%Y-%m-%d')
            except ValueError:
                return False, f"{col} should be in yyyy-mm-dd format"

        return True, "CSV file is valid"

    except Exception as e:
        return False, f"An error occurred: {str(e)}"

try:
    is_valid, message = validate_csv(crop_data)

    if not is_valid:
        print(f"crop_data is not valid: {message}")
        sys.exit()
except Exception as e:
    print(f'Crop Data is invalid : {e}')
    sys.exit()

def validate_template_folder(template_path):
    # Check if Mapping file exists
    mapping_file = os.path.join(template_path, 'Mapping')
    if not os.path.isfile(mapping_file):
        return False, "Mapping file not found in the template folder"

    # Validate Mapping file contents
    try:
        df = pd.read_csv(mapping_file)
        required_columns = ['epic_code', 'template_code']
        if not all(col in df.columns for col in required_columns):
            return False, "Mapping file is missing one or more required columns"

        # Check if epic_code is integer
        if not pd.api.types.is_integer_dtype(df['epic_code']):
            return False, "epic_code column in Mapping file should contain integers"

    except Exception as e:
        return False, f"Error reading Mapping file: {str(e)}"

    # Check if FALLOW.OPC is present
    fallow_opc = os.path.join(template_path, 'FALLOW.OPC')
    if not os.path.isfile(fallow_opc):
        return False, "FALLOW.OPC file not found in the template folder. It's used as default OPC if epic_code is not present in template. "

    return True, "Template folder validation successful"

try:
    is_valid, message = validate_template_folder(template_path)
    if not is_valid:
        print(f"Template folder not valid: {message}")
        sys.exit()
except Exception as e:
    print(f'Template folder not valid: {e}')
    sys.exit()


def get_epic_code_template_mapper(template_path):
    mapping_file_path = os.path.join(template_path, 'Mapping')
    df = pd.read_csv(mapping_file_path, names=['epic_code', 'template_code'], skiprows=1)
    epic_code_mapper = dict(zip(df['epic_code'].astype(int), df['template_code']))
    return epic_code_mapper

epic_code_mapper = get_epic_code_template_mapper(template_path)

crop_info_list=[]

start_year = crop_data_df['year'].min()
end_year = crop_data_df['year'].max()

for year in range(start_year, end_year + 1):
    year_data = crop_data_df[crop_data_df['year'] == year]
    
    if not year_data.empty:
        epic_code = year_data.iloc[0]['epic_code']
        plantation_date = year_data.iloc[0]['planting_date']
        harvest_date = year_data.iloc[0]['harvest_date']
        template_code = epic_code_mapper.get(epic_code, 'FALLOW')
        crop_info_list.append({
            'template_code': template_code,
            'epic_code':epic_code,
            'planting_date': plantation_date,
            'harvest_date': harvest_date
        })
    else:
        crop_info_list.append({
            'template_code': 'FALLOW',
            'epic_code':epic_code,
            'planting_date': None,
            'harvest_date': None
        })
res_opc_file = None
for crop_info in crop_info_list:
    template_code = crop_info['template_code']
    epic_code = crop_info['epic_code']
    planting_date = datetime.strptime(crop_info['planting_date'], '%Y-%m-%d')
    harvest_date = datetime.strptime(crop_info['harvest_date'], '%Y-%m-%d')
    if res_opc_file is None:
        res_opc_file = OPC.load(os.path.join(template_path,f'{template_code}.OPC'),harvest_date.year)
    else:
        template_opc = OPC.load(os.path.join(template_path,f'{template_code}.OPC'),harvest_date.year)
        res_opc_file = res_opc_file.append(template_opc)
    res_opc_file.edit_crop_season(planting_date,harvest_date,epic_code)

res_opc_file.save(out_path)