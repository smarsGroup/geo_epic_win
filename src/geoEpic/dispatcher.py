import subprocess
import os
import sys

# Mapping of modules and functions to their respective relative paths
script_paths = {
    "init" : {
        "init" : "initialize.py"
    },
    "utility": {
        "gee": "gee/fetch.py"
    },
    "weather": {
        "gee": "weather/gee.py",
        "download_daily": "weather/download_daily.py",
    },
    "soil": {
        "process_gdb": "soil/ssurgo_gdb.py",
        "usda": "soil/fetch_usda.py"
    },
    "opc": {
        "generate": "opc/generate_opc.py"
    },
    "workspace": {
        "run": "workspace/run.py",
        "new": "workspace/create_ws.py",
        "copy": "workspace/parallel_copy.py",
    },
}

default_functions = {
    "weather": "gee",
    "soil": "usda",
    "workspace": "new",
    "init": "init",
    "opc": "generate",
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


def dispatch(module, func, options, wait=True):
    """Run the script for ``module``/``func`` in a subprocess.

    ``options`` is a list of argument strings (preferred) or a single string.
    Arguments are passed as a list, never through a shell, so paths with
    spaces (e.g. ``C:\\Program Files\\...``) work on every platform.
    """
    root_path = os.path.dirname(__file__)
    if isinstance(options, str):
        import shlex
        options = shlex.split(options, posix=(os.name != 'nt'))

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
    command = [sys.executable, script_path, *options]

    proc = subprocess.Popen(command, env=env)
    if wait:
        proc.wait()
    return proc


def print_expected_usage():
    print('''
    GeoEPIC Tool Kit CLI (v1.1, Windows/Linux)
            
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
            options = args[2:]
        else:
            if module in default_functions:
                func = default_functions[module]
                options = args[1:]
            else:
                print_expected_usage()
                return
    else:
        module, _ = find_function(first_arg)
        if module:
            func = first_arg
            options = args[1:]
        else:
            print_expected_usage()
            return

    dispatch(module, func, options)

if __name__ == '__main__':
    main()
