import os
import shutil
import argparse

def copy_items(items):
    for source_item in items:
        target_dir = os.getcwd()
        
        # Ensure the source_item exists
        if not os.path.exists(source_item):
            print(f"Error:'{source_item} not found.")
            return
            
        item = (source_item.split('/'))[-1]
        target_item = os.path.join(target_dir, item)
        
        if os.path.isdir(source_item):
            shutil.copytree(source_item, target_item, dirs_exist_ok=True)
        else:
            shutil.copy2(source_item, target_item)

        print(f"{item} copied to workspace ")


script_dir = os.path.dirname(os.path.dirname(__file__))

# Define the dictionary mapping keys to lists of items
file_mapping = {
    'epic_editor': [os.path.join(script_dir, "templates/EPICeditor.xlsm")],
    'calibration_utils': [
        os.path.join(script_dir, "templates/calibration/calibration.py"),
        os.path.join(script_dir, "templates/calibration/parms")
    ],
    'HLS.yml':  [os.path.join(script_dir, "gee/HLS.yml")],
    'daily_weather.yml':  [os.path.join(script_dir, "gee/daily_weather.yml")],
}



def main():
    parser = argparse.ArgumentParser(description="Add Utilities to EPIC Workspace")
    parser.add_argument('-f', '--files', required=True, help='Files to add to this workspace (calibration, epic_editor)')
    args = parser.parse_args()

    if args.files in file_mapping:
        copy_items(file_mapping[args.files])
    else:
        print(f"Unknown file: {args.files}")
        
    

if __name__ == '__main__':
    main()
