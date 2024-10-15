import ee
import json
import os
from geoEpic.utils.redis import WorkerPool

def ee_Initialize():
    pool = WorkerPool('gee_global_lock')
    if pool.queue_len() is None: pool.open(40)
    # Get the directory where the script is located
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')
    config = None
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
           config = json.load(file)
    
    if config and 'project' in config:
        project_name = config['project']
    else:
        try:
            ee.Initialize()
            return
        except Exception as e:
            print(e)
        project_name = input("Please enter the GEE project: \n")
        config = {'project': project_name}
        with open(CONFIG_FILE, 'w') as file:
            json.dump(config, file, indent = 4)
        print(f"Initialized GEE with project: {project_name}")
    
    
    try:
        ee.Initialize(project=project_name, opt_url='https://earthengine-highvolume.googleapis.com')
    except Exception as e:
        print("Authentication required")
        ee.Authenticate()
        ee.Initialize(project=project_name, opt_url='https://earthengine-highvolume.googleapis.com')


def ee_ReInitialize():
    project_name = input("Enter the new GEE project name: \n")
    config = {'project': project_name}
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file, indent = 4)
        
    try:
        ee.Initialize(project=project_name, opt_url='https://earthengine-highvolume.googleapis.com')
        print(f"Reinitialized GEE with new project: {project_name}")
    except Exception as e:
        print("Authentication required.")
        ee.Authenticate()
        ee.Initialize(project=project_name, opt_url='https://earthengine-highvolume.googleapis.com')
        print(f"Reinitialized GEE with new project: {project_name}")