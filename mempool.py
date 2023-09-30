import requests
from const import MEMPOOL_API_URL
from config import config
from typing import Any
from box import Box
from result import Result, Ok, Err

class Mempool:
    def __init__(self, creds_path: str) -> None:
        creds = config.get_creds(creds_path, 'mempool')
        self.api_url = f"{creds.api_url}/api/v1" if creds.api_url else  MEMPOOL_API_URL

    def mempool_request(self, uri_path: str) -> Result[Box, str]:
        res = Box(requests.get(
            self.api_url + uri_path,
        ).json())
        # TODO: handle error
        return Ok(res)
   
    def get_fee(self) -> Result[Box, str]:
        return self.mempool_request("fees/recommended")