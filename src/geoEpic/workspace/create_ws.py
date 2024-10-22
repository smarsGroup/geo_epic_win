import os
from parallel_copy import copy_mapped_files
import argparse


def main():
    parser = argparse.ArgumentParser(description="Create Workspace for EPIC package")
    parser.add_argument('-n', '--workspace_name', required=True, help='Directory where workspace will be created')
    args = parser.parse_args()

    copy_mapped_files('workspace_win', args.workspace_name, 5)

    print(f"Workspace set up at: {args.workspace_name}")

if __name__ == '__main__':
    main()
