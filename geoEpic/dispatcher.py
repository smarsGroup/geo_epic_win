import subprocess
import os
import sys

# Mapping of modules and functions to their respective relative paths
script_paths = {
    "utility": {
        "crop_csb": "utils/crop_csb.py",
        "gee": "gee/fetch.py"
    },
    "weather": {
        "gee": "weather/gee.py",
        "windspeed": "weather/nldas_ws.py",
        "daymet": "weather/download_daymet.py",
        "download_daily": "weather/download_daily.py",
        "daily2monthly": "weather/daily2monthly.py"
    },
    "soil": {
        "process_gdb": "soil/ssurgo_gdb.py",
        "usda": "soil/fetch_usda.py"
    },
    "sites": {
        "generate": "sites/generate.py"
    },
    "workspace": {
        "prepare": "workspace/prepare.py",
        "run": "workspace/run.py",
        "listfiles": "workspace/listfiles.py",
        "new": "workspace/create_ws.py",
        "copy": "workspace/add.py",
        "post_process": "workspace/post_process.py",
        "visualize": "workspace/visualize.py"
    },
}

default_functions = {
    "weather": "gee",
    "soil": "usda",
    "sites": "generate",
    "workspace": "run",
}

class DispatchError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message
    

def find_function(func_name):
    for module, funcs in script_paths.items():
        if func_name in funcs:
            return module, funcs[func_name]
    return None, None


def dispatch(module, func, options_str, wait=True):
    root_path = os.path.dirname(__file__)
    command = f'{sys.executable} {{script_path}} {options_str}'

    if not module:
        module, relative_path = find_function(func)
        if not relative_path:
            raise DispatchError(f"Function '{func}' not found in any module.")
    else:
        if not func: func = default_functions.get(module, {})
        relative_path = script_paths.get(module, {}).get(func, {})

    if relative_path:
        script_path = os.path.join(root_path, relative_path)
    else:
        raise DispatchError(f"Command '{module} {func}' not found.")

    env = os.environ.copy()
    command = command.format(script_path=script_path)

    if wait:
        subprocess.Popen(command, shell=True, env=env).wait()
    else:
        subprocess.Popen(command, shell=True, env=env)


def print_expected_usage():
    print('''
GeoEPIC Tool Kit CLI
          
usage: geo_epic [module] [function] [options] 

Refer GeoEPIC documentation for available functionality''')
    
    
def main():
    args = sys.argv[1:]  # Ignore the script name itself
    if not args:
        print_expected_usage()
        return

    first_arg = args[0]
    module, func = None, None

    if first_arg in script_paths:
        module = first_arg
        if len(args) > 1 and args[1] in script_paths[module]:
            func = args[1]
            options_str = " ".join(args[2:])
        else:
            if module in default_functions:
                func = default_functions[module]
                options_str = " ".join(args[1:])
            else:
                print_expected_usage()
                return
    else:
        module, _ = find_function(first_arg)
        if module:
            func = first_arg
            options_str = " ".join(args[1:])
        else:
            print_expected_usage()
            return

    dispatch(module, func, options_str)

if __name__ == '__main__':
    main()
