from os import path
from box import Box


def parse_creds(key: str):
    f = "config.yml" if not path.exists("config.yaml") else "config.yaml"
    return parse_yaml(f)[key]


def parse_yaml(path: str) -> dict:
    return Box().from_yaml(filename=path)
