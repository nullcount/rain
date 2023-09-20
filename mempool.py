import requests
from const import MEMPOOL_API_URL
from config import get_creds, log
from typing import Any

class Mempool:
    def __init__(self) -> None:
        creds = get_creds('mempool')
        self.api_url = f"{creds.api_url}/api/v1" if creds.api_url else  MEMPOOL_API_URL

    def mempool_request(self, uri_path: str) -> dict[Any, Any]:
        req: dict[Any, Any] = requests.get(
            self.api_url + uri_path,
        ).json()
        return req
   
    def get_fee(self) -> dict[Any, Any]:
        return self.mempool_request("fees/recommended")