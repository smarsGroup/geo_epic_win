import os
import argparse
from geoEpic.core import Workspace
from glob import glob


# Fetch the base directory
parser = argparse.ArgumentParser(description="EPIC workspace")
parser.add_argument("-c", "--config", default= "./config.yml", help="Path to the configuration file")
parser.add_argument("-b", "--progress_bar", default = 'True', help = "Display Progress Bar")
args = parser.parse_args()

bar = (args.progress_bar == 'True')
exp = Workspace(args.config)
exp.run(progress_bar = bar)