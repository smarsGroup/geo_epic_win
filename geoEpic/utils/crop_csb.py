import argparse
import subprocess
import numpy as np
import os
from us import states

def get_state_fips(state_name):
    state = states.lookup(state_name)
    if state:
        return state.fips
    else:
        return None

def run_ogr2ogr(args):
    base_command = "ogr2ogr -t_srs EPSG:4326"
    input_file = args.input_file
    output_file = args.output_file
    
    if args.center:
        # Calculate bounding box from center and extent
        center_lat, center_lon = map(float, args.center.split(','))
        h, w = map(float, args.extent.split('x'))
        # Convert km to degrees approximately (very rough estimate)
        lat_extent = h / 110.574
        lon_extent = w / (111.320 * np.cos(np.radians(center_lat)))
        bbox = [
            center_lon - lon_extent / 2, center_lat - lat_extent / 2,
            center_lon + lon_extent / 2, center_lat + lat_extent / 2
        ]
        clip_option = f"-clipdst {' '.join(map(str, bbox))}"
    
    elif args.bbox:
        clip_option = f"-clipdst {' '.join(args.bbox.split(','))}"
    

    elif args.state_fips or args.county_fips or args.state_name:
        where_clause = []
        if args.state_name:
            state_fips = get_state_fips(args.state_name.strip())
            where_clause.append(f"STATEFIPS = '{state_fips}'")
        elif args.state_fips:
            where_clause.append(f"STATEFIPS = '{args.state_fips}'")
        if args.county_fips:
            where_clause.append(f"CNTYFIPS = '{args.county_fips}'")
        clip_option = f"-where \"{' AND '.join(where_clause)}\""
    
    elif args.county_name:
        county_name, state_name = args.county_name.split(',')
        state_fips = get_state_fips(state_name.strip())
        clip_option = f"-where \"CNTY = '{county_name.strip()}' AND STATEFIPS = '{state_fips}'\""
    
    else:
        clip_option = ""

    
    full_command = f"{base_command} {clip_option} {output_file} {input_file}"
    print("You might have to wait longer based on the query")
    print('Executing command:', full_command)
    subprocess.run(full_command, shell=True)
    

parser = argparse.ArgumentParser(description='Filter CSB GDB file to a specific region.')
parser.add_argument('input_file', type=str, help='Input GDB file path')
parser.add_argument('output_file', type=str, help='Output SHP file path')
parser.add_argument('--center', type=str, help='Center latitude and longitude "lat,lon"')
parser.add_argument('--extent', type=str, help='Extent height and width in km "hkm x wkm"')
parser.add_argument('--bbox', type=str, help='Bounding box "minLon,minLat,maxLon,maxLat"')
parser.add_argument('--state_fips', type=str, help='State FIPS code')
parser.add_argument('--state_name', type=str, help='State name')
parser.add_argument('--county_fips', type=str, help='County FIPS code')
parser.add_argument('--county_name', type=str, help='County name followed by state name "County, State"')

args = parser.parse_args()

run_ogr2ogr(args)
