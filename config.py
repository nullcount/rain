from datetime import datetime
from box import Box

class config:

    @staticmethod
    def get_creds(creds_path: str, key: str) -> Box:
        return Box().from_yaml(filename=creds_path)[key]
    
    @staticmethod
    def get_config(config_path: str) -> Box:
        return Box().from_yaml(filename=config_path)
    
    @staticmethod
    def set_creds(creds_path: str, key: str, new_box: Box) -> None:
        creds = Box().from_yaml(filename=creds_path)
        creds[key] = new_box
        creds.to_yaml(filename=creds_path)

    @staticmethod
    def log(level: str, message: str ) -> None:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {level.upper()}: {message}")