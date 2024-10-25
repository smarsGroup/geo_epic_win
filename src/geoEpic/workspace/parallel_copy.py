import os
import glob
import argparse
import subprocess
from geoEpic.utils import parallel_executor
from tqdm import tqdm
import platform

def rsync_copy(src_dst):
    os.makedirs(os.path.dirname(src_dst[1]), exist_ok=True)
    if platform.system() == "Windows":
        # Use robocopy for Windows
        robocopy_command = ["robocopy", os.path.dirname(src_dst[0]), os.path.dirname(src_dst[1]), os.path.basename(src_dst[0]), "/E", "/DCOPY:DA", "/COPY:DAT", "/R:3", "/W:3"]
        subprocess.run(robocopy_command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def parallel_copy(source_dir, destination_dir, max_workers=4, extension=None, level_one=False, exclude_dirs=False, progress_bar=True):
    """
    Copy files from source to destination directory using parallel processing.

    Args:
        source_dir (str): Path to the source directory.
        destination_dir (str): Path to the destination directory.
        max_workers (int): Number of parallel workers to use.
        extension (str): Specific file extension to filter (e.g., ".txt").
        level_one (bool): If True, only copy files from the top-level directory.
        exclude_dirs (bool): If True, exclude directories from the copying process.
        progress_bar (bool): Show a progress bar if True.
    """
    # Define the glob pattern based on the provided options
    if level_one:
        # Only get files in the top level (non-recursive)
        pattern = os.path.join(source_dir, '*')
    else:
        # Recursively get all files and directories
        pattern = os.path.join(source_dir, '**', '*')

    # Use glob to find matching files based on the pattern
    file_paths = glob.glob(pattern, recursive=not level_one)

    # Filter out files based on the extension and exclude directories if requested
    file_pairs = [
        (src, os.path.join(destination_dir, os.path.relpath(src, source_dir)))
        for src in file_paths
        if (os.path.isfile(src) or not exclude_dirs) and (not extension or src.endswith(extension))
    ]
    parallel_executor(rsync_copy, file_pairs, 
                      method='Thread', max_workers=max_workers,
                      timeout=20, bar=progress_bar)

# Define the dictionary mapping keys to lists of items
script_dir = os.path.dirname(os.path.abspath(__file__))
file_mapping = {
    'epic_editor': [os.path.join(script_dir, "../assets/EPICeditor.xlsm")],
    'calibration_utils': [
        os.path.join(script_dir, "../assets/calibration/calibration.py"),
        os.path.join(script_dir, "../assets/calibration/parms")
    ],
    'HLS.yml': [os.path.join(script_dir, "../gee/HLS.yml")],
    'daily_weather.yml': [os.path.join(script_dir, "../gee/daily_weather.yml")],
    'workspace_win': [os.path.join(script_dir, "../assets/workspace_win/")]
}

def copy_mapped_files(key, destination, max_workers):
    # Source is a key in the file mapping, use the mapped files
    file_pairs = [
        (src, os.path.join(destination, os.path.basename(src)))
        for src in file_mapping[key]
    ]
    parallel_executor(rsync_copy, file_pairs, 
                        method='Thread', max_workers=max_workers, 
                        timeout=20, bar = False)
        
def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Parallel file copy or add utilities to workspace.")
    parser.add_argument("source", help="Path to the source directory or file or a key for file mapping")
    parser.add_argument("destination", nargs='?', default=os.getcwd(), help="Path to the destination directory (default: current working directory)")
    parser.add_argument("-w", "--max-workers", type=int, default=10, help="Number of parallel workers to use (default: 10)")
    parser.add_argument("-e", "--extension", type=str, help="Copy only files with the specified extension (e.g., '.txt')")
    parser.add_argument("-l", "--level-one", action="store_true", help="Only copy files from the top-level directory")
    parser.add_argument("-x", "--exclude-dirs", action="store_true", help="Exclude directories from being copied")
    parser.add_argument("-np", "--no-progress", action="store_true", help="Do not show a progress bar")

    # Parse arguments
    args = parser.parse_args()

    # Check if the source is a dir
    if os.path.isdir(args.source):
        parallel_copy(
            source_dir=args.source,
            destination_dir=args.destination,
            max_workers=args.max_workers,
            extension=args.extension,
            level_one=args.level_one,
            exclude_dirs=args.exclude_dirs,
            progress_bar=not args.no_progress
        )
     # Check if the source is a file
    elif os.path.isfile(args.source):
        # If the source is a file, copy it directly to the destination
        destination_path = os.path.join(args.destination, os.path.basename(args.source))
        rsync_copy((args.source, destination_path))
        print(f"Copied file '{args.source}' to '{args.destination}'.")
    elif args.source in file_mapping:
        copy_mapped_files(args.source, args.destination, args.max_workers)
    else:
        print(f"Error: '{args.source}' is not a valid directory or file or recognized file mapping key.")

if __name__ == "__main__":
    main()
