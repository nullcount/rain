import argparse
from accounting import Accounting
from config import CREDS, RUN_LOG

parser = argparse.ArgumentParser(description="Tools for making it rain")

# Add a positional argument
parser.add_argument("sync", type=bool, help="Sync historical accounting data")

# Parse the arguments
args = parser.parse_args()
if args.sync:
    acc = Accounting(CREDS, RUN_LOG)
    acc.sync_history(progress=True)
