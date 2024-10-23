from geoEpic.io.config_parser import ConfigParser
import os
import urllib.request

home_dir = os.path.expanduser("~")
metadata_dir = os.path.join(home_dir, 'GeoEPIC_metadata')
root_path = os.path.dirname(__file__)

def setup_metadata():
    if not os.path.exists(metadata_dir):
        os.makedirs(metadata_dir)
        # List of files to download
        files_to_download = [
            "https://smarslab-files.s3.amazonaws.com/epic-utils/slope_us.tif",
            "https://smarslab-files.s3.amazonaws.com/epic-utils/SRTM_1km_US_project.tif",
            "https://smarslab-files.s3.amazonaws.com/epic-utils/SSURGO.tif"
        ]
        # Download the files to the metadata directory
        for file_url in files_to_download:
            filename = os.path.join(metadata_dir, os.path.basename(file_url))
            urllib.request.urlretrieve(file_url, filename)
    else:
        print(f"'{metadata_dir}' already exists, skipping file downloads.")

def update_template_config_file():

    config = ConfigParser(os.path.join(root_path,'assets','workspace_win','config.yml'))

    config.update({'soil' : {'soil_map': f'{home_dir}/GeoEPIC_metadata/SSURGO.tif',},
                    'site': {'elevation': f'{home_dir}/GeoEPIC_metadata/SRTM_1km_US_project.tif',
                            'slope': f'{home_dir}/GeoEPIC_metadata/slope_us.tif',
        }, })
    
setup_metadata()
update_template_config_file()

