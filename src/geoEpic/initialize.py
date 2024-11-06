from geoEpic.io.config_parser import ConfigParser
import os
import urllib.request
import platform

home_dir = os.path.expanduser("~")
metadata_dir = os.path.join(home_dir, 'GeoEPIC')
root_path = os.path.dirname(__file__)

def setup_metadata():
    if not os.path.exists(metadata_dir):
        os.makedirs(metadata_dir)
    
    # List of files to download
    files_to_download = [
        "https://smarslab-files.s3.amazonaws.com/epic-utils/slope_us.tif",
        "https://smarslab-files.s3.amazonaws.com/epic-utils/SRTM_1km_US_project.tif",
        "https://smarslab-files.s3.amazonaws.com/epic-utils/SSURGO.tif",
    ]
    # Add Redis files for Windows platform
    if platform.system() == 'Windows':  # Check if running on Windows
        files_to_download += [
            "https://smarslab-files.s3.amazonaws.com/epic-utils/redis-server.exe",
            "https://smarslab-files.s3.amazonaws.com/epic-utils/redis.conf",
            "https://smarslab-files.s3.amazonaws.com/epic-utils/redis_win_license",
        ]
        
    # Download the files to the metadata directory if they don't already exist
    for file_url in files_to_download:
        filename = os.path.join(metadata_dir, os.path.basename(file_url))
        if not os.path.exists(filename):
            urllib.request.urlretrieve(file_url, filename)
        else:
            print(f"'{filename}' already exists, skipping download.")


def update_template_config_file():

    config = ConfigParser(os.path.join(root_path, 'assets', 'workspace_win', 'config.yml'))

    config.update({'soil' : {'soil_map': f'{metadata_dir}/SSURGO.tif',},
                    'site': {'elevation': f'{metadata_dir}/SRTM_1km_US_project.tif',
                             'slope': f'{metadata_dir}/slope_us.tif',
        }, })
    
setup_metadata()
update_template_config_file()

