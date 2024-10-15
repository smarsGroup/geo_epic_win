import os
import argparse
from geoEpic.io import DLY
from geoEpic.utils import parallel_executor
from glob import glob

parser = argparse.ArgumentParser(description="Daily to Monthly")
parser.add_argument("-i", "--input", required = True, help="Path to the input file or folder")
parser.add_argument("-o", "--output", default = "./Monthly", help = "Path to the output dir")
parser.add_argument("-w", "--max_workers", default = 20, help = "No. of maximum workers")
args = parser.parse_args()

output_folder = args.output if args.output else "./Monthly"
os.makedirs(output_folder, exist_ok = True)

def convert_file(file_path):
    dly = DLY(file_path)
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    dly.to_monthly(os.path.join(output_folder, file_name))
        
if os.path.isfile(args.input):
    convert_file(args.input)
elif os.path.isdir(args.input):
    file_list = glob(args.input + '/*')
    parallel_executor(convert_file, file_list, max_workers = args.max_workers)
else:
    print("Invalid input. Please provide a valid file or folder path.")

