from os import path
from box import Box


def get_creds(key: str):
    f = "creds.yml" if not path.exists("creds.yaml") else "creds.yaml"
    yml = parse_yaml(f)
    return yml[key]


def parse_yaml(path: str) -> dict:
    return Box().from_yaml(filename=path)
