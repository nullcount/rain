from datetime import datetime
from os import path
from box import Box

def get_creds(key: str) -> Box:
    f = "creds.yml" if not path.exists("creds.yaml") else "creds.yaml"
    yml = parse_yaml(f)
    return yml[key]

def parse_yaml(path: str) -> Box:
    return Box().from_yaml(filename=path)

def set_creds(key: str, new_box: Box) -> None:
    f = "creds.yml" if not path.exists("creds.yaml") else "creds.yaml"
    creds = parse_yaml(f)
    creds[key] = new_box
    creds.to_yaml(filename=f)

def log(level: str, message: str ) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {level.upper()}: {message}")