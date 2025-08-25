import numpy as np
import pandas as pd
import os
import sys
import importlib.util
import shutil
import struct
import mmap
import shortuuid

def read_gdb_layer(gdb_data, layer_name, columns = None, names = None):
    """
    Reads selected columns from a GDB layer and returns them in a pandas DataFrame.
    
    Args:
        gdb (gdb): The GDB file opened by ogr.
        layer_name (str): The name of the layer to read.
        columns (list, optional): List of column indices to read. If None, all columns are read.
        names (list, optional): List of column names corresponding to the indices in `columns`.
            If None, all column names are inferred from the layer definition.
    
    Returns:
        pd.DataFrame: The resulting dataframe.
    """
    layer = gdb_data.GetLayerByName(layer_name)
    layer_defn = layer.GetLayerDefn()

    if not columns:
        columns = list(range(layer_defn.GetFieldCount()))
        names = [layer_defn.GetFieldDefn(i).GetName() for i in columns]
    elif not names:
        names = [layer_defn.GetFieldDefn(i).GetName() for i in columns]

    features = []
    for feature in layer:
        attributes = {}
        for idx, name in zip(columns, names):
            field_defn = layer_defn.GetFieldDefn(idx)
            field_name = field_defn.GetName()
            attributes[name] = feature.GetField(field_name)
        features.append(attributes)
        
    return pd.DataFrame(features)


def filter_dataframe(df, expression):
    if expression is None: return df
    if expression.count('+') < 2:
        if expression.count('+') == 1:
            exp =  [i.strip() for i in expression.split('+')]
            # print(exp)
        else:
            exp = [expression]
        # print('EXP length', len(exp))
        filtered_dfs = []
        for expression in exp:
            expressions =  [i.strip() for i in expression.split(';')]
            df_copy = df.copy()
            for expression in expressions:
                # expression = expression.strip()
                # Handle expressions that are ranges (e.g., "Range(0.35, 0.8)")
                if expression.startswith("Range(") and expression.endswith(")"):
                    values = expression[6:-1].split(',')
                    low_fraction, high_fraction = float(values[0]), float(values[1])
                    
                    # Calculate the index range
                    total_length = len(df)
                    low_idx = np.floor(low_fraction * total_length).astype(int)
                    high_idx = np.ceil(high_fraction * total_length).astype(int)
                    
                    # Ensure indices are within bounds
                    low_idx = max(0, low_idx)
                    high_idx = min(total_length, high_idx)
                    
                    df_copy = df_copy.iloc[low_idx:high_idx]

                # Handle expressions that are random (e.g., "Random(0.1)")
                elif expression.startswith("Random(") and expression.endswith(")"):
                    frac = float(expression[7:-1])
                    df_copy = df_copy.sample(frac=frac)

                # Handle boolean expressions (e.g., "group == 1")
                else:
                    df_copy = df_copy.query(expression)
            filtered_dfs.append(df_copy)

        if len(filtered_dfs) == 1:
            return filtered_dfs[0]
        else:
            filtered_df = pd.concat(filtered_dfs)
            filtered_df = filtered_df.drop_duplicates(subset = 'FieldID', keep = 'last')
            return filtered_df

            
    return df.reset_index()
    


def import_function(cmd = None):
    """
    Loads a function from a module based on a path and function name specified in the config.
    
    Args:
        cmd (str): "/path/to/module.py function_name".

    Returns:
        function: The loaded function, or None if not found.
    """
    if cmd is None: return None

    path, function_name = cmd.split()

    # Ensure the path is in the right format and loadable
    module_name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None:
        print(f"Cannot find module {path}")
        return None

    # Load the module
    try:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error loading module: {e}")
        return None

    # Get the function and return it
    if hasattr(module, function_name):
        return getattr(module, function_name)
    else:
        print(f"Function {function_name} not found in {path}")
        return None
    


def check_disk_space(output_dir, est, safety_margin=0.1):
    """
    Checks whether there is sufficient disk space available for saving output files.

    Args:
        output_dir (str): Directory where files will be saved.
        config (dict): Configuration dictionary with an "output_types" key.
        safety_margin (float): The safety margin to add to the estimated disk usage (default is 10%).

    Raises:
        Exception: If the free disk space is lower than the estimated required space.
    """
    # Retrieve disk space details for the specified output directory
    total_bytes, used_bytes, free_bytes = shutil.disk_usage(output_dir)
    
    # Convert free bytes to GiB for easy reading
    free_gib = free_bytes // (1024**3)

    # Adjust for the safety margin
    estimated_required_gib = int(est * (1 + safety_margin))

    # Check if there is sufficient free disk space
    if free_gib < estimated_required_gib:
        message = (f"Insufficient disk space in '{output_dir}'. Estimated required: {est} GiB, "
                   f"Available: {free_gib} GiB. Consider logging only required data.")
        raise Exception(message)
    
    
def copy_file(src, dest, symlink = False):
    """
    Copy a file from source to destination, optionally creating a symbolic link instead.

    Args:
        src (str): Path to the source file
        dest (str): Path to the destination file/link
        symlink (bool, optional): Whether to create a symbolic link instead of copying. 
            Defaults to False.

    Returns:
        str | None: Path to the destination file if successful, None if source doesn't exist

    Note:
        If symlink is True and the destination already exists, it will be removed first.
    """
    if not src: return None

    if symlink:
        if os.path.exists(dest):
            os.remove(dest)
        os.symlink(src, dest)
    else:
        shutil.copy2(src, dest)
    
    return dest


import platform
IS_WINDOWS = platform.system() == 'Windows'

if IS_WINDOWS:
    import msvcrt
else:
    import fcntl

class FileLockHandle:
    """A class to handle file locking across different platforms."""

    def __init__(self, file_path):
        """Initialize with file path."""
        self.file_path = file_path
        self.file_handle = None
        if os.path.isdir(file_path):
            self.lock_file = os.path.join(file_path, '.lock')
        else:
            self.lock_file = file_path

    def acquire(self, mode='a+'):
        """Acquire a lock on the file."""
        try:
            # Open file in specified mode (default append mode) to preserve contents if it exists
            self.file_handle = open(self.lock_file, mode)
            if IS_WINDOWS:
                msvcrt.locking(self.file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self.file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self.file_handle
        except (IOError, OSError):
            # Clean up if lock acquisition failed
            if self.file_handle:
                self.file_handle.close()
            raise RuntimeError(f" \"{self.file_path}\" is in use by another process")
        
    def release(self):
        """Release the lock on the file."""
        try:
            if self.file_handle:
                if IS_WINDOWS:
                    msvcrt.locking(self.file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self.file_handle, fcntl.LOCK_UN)
                self.file_handle.close()
                self.file_handle = None
        except (IOError, OSError):
            pass  # File may already be unlocked or removed

    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


if IS_WINDOWS:
    import win32event
    import win32con
    import win32api

class WorkerPoolWin:
    """
    Cross-process, Windows-only worker pool keyed by pool_key.
    Mirrors the API of your Redis/LMDB version:
      - __init__(pool_key=None, base_dir=None)
      - open(max_resources)
      - acquire()
      - release(resource)
      - queue_len()
      - close()
    Resources are simple indices 0..max_resources-1, optionally materialized
    as subfolders under base_dir.
    """

    _HDR_SIZE = 12   # 3×uint32: [capacity, head, tail]

    def __init__(self, pool_key: str = None, base_dir: str = None):
        self.pool_key = pool_key or f"worker_pool_{shortuuid.uuid()}"
        self.base_dir  = base_dir
        self._inited   = False
        self._mem      = None
        self._sem      = None
        self._mtx      = None

    def open(self, max_resources: int):
        """
        Initialize or reinitialize the pool to hold max_resources slots.
        Any existing pool with the same pool_key in this session will be reused.
        """
        self.capacity = max_resources
        self._map_size = self._HDR_SIZE + 4 * self.capacity

        tag           = f"Local\\WP_{self.pool_key}"
        self._map_name = tag + "_MMF"
        self._sem_name = tag + "_SEM"
        self._mtx_name = tag + "_MTX"

        # create base_dir and its slot subfolders if requested
        if self.base_dir:
            os.makedirs(self.base_dir, exist_ok=True)
            for i in range(self.capacity):
                slot_dir = os.path.join(self.base_dir, str(i))
                os.makedirs(slot_dir, exist_ok=True)

        # 1) open or create the named mmap
        self._mem = mmap.mmap(-1, self._map_size, tagname=self._map_name)

        # 2) read existing capacity, ensure it matches or init
        existing_cap, = struct.unpack_from("I", self._mem, 0)
        if existing_cap not in (0, self.capacity):
            raise ValueError(
                f"Pool '{self.pool_key}' already exists with capacity={existing_cap}"
            )

        # 3) open/create Win32 semaphore & mutex
        #    initial sem count=0 if first opener
        self._sem = win32event.CreateSemaphore(None, 0, self.capacity, self._sem_name)
        self._mtx = win32event.CreateMutex   (None, False,           self._mtx_name)

        # 4) first opener zero-initializes the ring and sem count
        if existing_cap == 0:
            # write [capacity, head=0, tail=capacity]
            struct.pack_into("I", self._mem, 0, self.capacity)
            struct.pack_into("I", self._mem, 4, 0)                # head
            struct.pack_into("I", self._mem, 8, self.capacity)    # tail

            # fill slots with their own indices
            buf_off = self._HDR_SIZE
            for i in range(self.capacity):
                struct.pack_into("I", self._mem, buf_off + 4 * i, i)

            # release all slots onto the semaphore
            win32event.ReleaseSemaphore(self._sem, self.capacity)

        self._inited = True

    def acquire(self, block: bool = True, timeout: float = None) -> str:
        """
        Block until a slot is free, then pop it.
        Returns the resource (index or path) as string, or None on timeout/non-block.
        """
        if not self._inited:
            raise RuntimeError("Pool not open: call open(max_resources) first.")
        
        interval_ms = 200  # poll every 200ms
        timeout_ms  = int(timeout * 1000) if timeout is not None else None
        elapsed_ms  = 0

        while True:
            # Wait for the shorter of the polling interval or remaining timeout
            wait_ms = interval_ms if timeout_ms is None else min(interval_ms, timeout_ms - elapsed_ms)
            rc = win32event.WaitForSingleObject(self._sem, wait_ms)
            if rc == win32con.WAIT_OBJECT_0: break
            elif rc == win32con.WAIT_TIMEOUT:
                if timeout_ms is not None:
                    elapsed_ms += wait_ms
                    if elapsed_ms >= timeout_ms:
                        return None
            else: return None

        # proceed with normal dequeue
        win32event.WaitForSingleObject(self._mtx, win32event.INFINITE)
        head, tail = struct.unpack_from("II", self._mem, 4)
        slot_off   = self._HDR_SIZE + 4 * head
        idx,       = struct.unpack_from("I", self._mem, slot_off)

        # bump head (circular)
        head = (head + 1) % self.capacity
        struct.pack_into("I", self._mem, 4, head)
        win32event.ReleaseMutex(self._mtx)
        return os.path.join(self.base_dir, str(idx)) if self.base_dir else str(idx)

    def release(self, resource: str):
        """
        Push a slot back into the pool and signal waiting acquirers.
        `resource` should be the string returned by acquire().
        """
        if not self._inited:
            raise RuntimeError("Pool not open: call open(max_resources) first.")

        # parse the original index
        idx = int(os.path.basename(resource)) if self.base_dir else int(resource)
        win32event.WaitForSingleObject(self._mtx, win32con.INFINITE)
        head, tail = struct.unpack_from("II", self._mem, 4)
        slot_off   = self._HDR_SIZE + 4 * tail
        struct.pack_into("I", self._mem, slot_off, idx)

        # bump tail (circular)
        tail = (tail + 1) % self.capacity
        struct.pack_into("I", self._mem, 8, tail)
        win32event.ReleaseMutex(self._mtx)
        win32event.ReleaseSemaphore(self._sem, 1)

    def queue_len(self) -> int:
        """Return the current number of free slots in the pool."""
        if not self._inited: return 0
        head, tail = struct.unpack_from("II", self._mem, 4)
        return (tail - head) % self.capacity

    def close(self, cleanup_dirs: bool = False):
        """
        Drain and optionally delete per-slot directories, then close handles.
        Windows will automatically clean up named objects once no handles remain.
        """
        if self._inited:
            # drain without blocking
            while True:
                slot = self.acquire(block=False)
                if slot is None: break
                if cleanup_dirs and self.base_dir and os.path.exists(slot):
                    shutil.rmtree(slot, ignore_errors=True)

        # tear down handles
        if self._mem: self._mem.close()
        if self._sem: win32api.CloseHandle(self._sem)
        if self._mtx: win32api.CloseHandle(self._mtx)
        self._inited = False
