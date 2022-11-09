import argparse
import configparser


class Config:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Execute playbook from config')
        self.parser.add_argument("--config", type=str, default="rain.config")
        args = self.parser.parse_args()
        config_loc = args.config
        self.config = configparser.ConfigParser()
        self.config.read(config_loc)
