import argparse
import configparser
from lnd import Lnd
from kraken import Kraken


class Config:
    def __init__(self, config_file):
        self.parser = argparse.ArgumentParser(description='Execute playbook from config')
        self.parser.add_argument("--config", type=str, default=config_file)
        args = self.parser.parse_args()
        config_loc = args.config
        self.config = configparser.ConfigParser()
        self.config.read(config_loc)


source_map = {
    "kraken": Kraken
}
node_map = {
    "LND": Lnd
}
