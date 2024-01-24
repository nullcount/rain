"""
config.py
---
Helper methods for read/write of config files and for logging 
usage: anywhere configs or logs are needed
"""
from datetime import datetime
from box import Box
from os import path

def check_yml_yaml(creds_path: str) -> str:
    f = creds_path
    if '.yml' in f and not path.exists(f):
        f.replace('.yml', '.yaml')
    return f


class config:

    @staticmethod
    def get_creds(creds_path: str, key: str) -> Box:
        return Box().from_yaml(filename=check_yml_yaml(creds_path))[key] # type: ignore
    
    @staticmethod
    def get_config(config_path: str) -> Box:
        return Box().from_yaml(filename=check_yml_yaml(config_path))
    
    @staticmethod
    def set_creds(creds_path: str, key: str, new_box: Box) -> None:
        creds_path = check_yml_yaml(creds_path)
        creds = Box().from_yaml(filename=creds_path)
        creds[key] = new_box
        creds.to_yaml(filename=creds_path)

    @staticmethod
    def log(level: str, message: str ) -> None:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {level.upper()}: {message}")