import os
import glob
import argparse
from tqdm import tqdm
import shutil

def shutil_copy(src_dst):
    src, dst = src_dst
    if os.path.isdir(src):
        # If destination exists, remove it first to ensure a clean copy
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

def parallel_copy(source_dir, destination_dir, max_workers=4, extension=None, level_one=False, exclude_dirs=False, progress_bar=True):
    """
    Copy files from source to destination directory using a for loop.

    Args:
        source_dir (str): Path to the source directory.
        destination_dir (str): Path to the destination directory.
        max_workers (int): Number of parallel workers to use (ignored, kept for compatibility).
        extension (str): Specific file extension to filter (e.g., ".txt").
        level_one (bool): If True, only copy files from the top-level directory.
        exclude_dirs (bool): If True, exclude directories from the copying process.
        progress_bar (bool): Show a progress bar if True.
    """
    if level_one:
        pattern = os.path.join(source_dir, '*')
    else:
        pattern = os.path.join(source_dir, '**', '*')

    file_paths = glob.glob(pattern, recursive=not level_one)

    file_pairs = []
    for src in file_paths:
        rel_path = os.path.relpath(src, source_dir)
        dst = os.path.join(destination_dir, rel_path)
        if os.path.isdir(src):
            if not exclude_dirs:
                file_pairs.append((src, dst))
        else:
            if not extension or src.endswith(extension):
                file_pairs.append((src, dst))

    iterator = tqdm(file_pairs, desc="Copying files") if progress_bar else file_pairs
    for pair in iterator:
        try:
            shutil_copy(pair)
        except Exception as e:
            print(f"Error copying {pair[0]} to {pair[1]}: {e}")

# Define the dictionary mapping keys to lists of items
script_dir = os.path.dirname(os.path.abspath(__file__))
file_mapping = {
    'epic_editor': [os.path.join(script_dir, "../assets/EPICeditor.xlsm")],
    'calibration_utils': [
        os.path.join(script_dir, "../assets/calibration/calibration_starter.ipynb"),
        os.path.join(script_dir, "../assets/calibration/calibration_files")
    ],
    'HLS.yml': [os.path.join(script_dir, "../gee/HLS.yml")],
    'daily_weather.yml': [os.path.join(script_dir, "../gee/daily_weather.yml")],
    'workspace_win': [os.path.join(script_dir, "../assets/workspace_win")]
}

def copy_mapped_files(key, destination, max_workers):
    """
    Copy mapped files or directories for a given key to the destination.
    Handles both files and directories.
    If the mapped item is a directory, copy only its contents (not the directory itself) into destination.
    """
    for src in file_mapping[key]:
        if os.path.isdir(src):
            # Copy only the contents of the directory, not the directory itself
            items = os.listdir(src)
            for item in items:
                item_src = os.path.join(src, item)
                item_dst = os.path.join(destination, item)
                try:
                    shutil_copy((item_src, item_dst))
                except Exception as e:
                    print(f"Error copying {item_src} to {item_dst}: {e}")
        else:
            dst = os.path.join(destination, os.path.basename(src))
            try:
                shutil_copy((src, dst))
            except Exception as e:
                print(f"Error copying {src} to {dst}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Parallel file copy or add utilities to workspace.")
    parser.add_argument("source", help="Path to the source directory or file or a key for file mapping")
    parser.add_argument("destination", nargs='?', default=os.getcwd(), help="Path to the destination directory (default: current working directory)")
    parser.add_argument("-w", "--max-workers", type=int, default=10, help="Number of parallel workers to use (default: 10)")
    parser.add_argument("-e", "--extension", type=str, help="Copy only files with the specified extension (e.g., '.txt')")
    parser.add_argument("-l", "--level-one", action="store_true", help="Only copy files from the top-level directory")
    parser.add_argument("-x", "--exclude-dirs", action="store_true", help="Exclude directories from being copied")
    parser.add_argument("-np", "--no-progress", action="store_true", help="Do not show a progress bar")

    args = parser.parse_args()

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
    elif os.path.isfile(args.source):
        destination_path = os.path.join(args.destination, os.path.basename(args.source))
        try:
            shutil_copy((args.source, destination_path))
            print(f"Copied file '{args.source}' to '{args.destination}'.")
        except Exception as e:
            print(f"Error copying {args.source} to {destination_path}: {e}")
    elif args.source in file_mapping:
        copy_mapped_files(args.source, args.destination, args.max_workers)
    else:
        print(f"Error: '{args.source}' is not a valid directory or file or recognized file mapping key.")

if __name__ == "__main__":
    main()
