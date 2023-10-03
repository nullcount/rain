import requests # type: ignore
from const import MEMPOOL_API_URL
from config import config
from typing import List
from box import Box
from result import Result, Ok, Err


class Mempool:
    # TODO make a base class for mempool/block explorer api generalized
    def __init__(self, creds_path: str, whoami: str = 'mempool') -> None:
        creds = config.get_creds(creds_path, whoami)
        self.api_url = f"{creds.api_url}/api/v1" if creds.api_url else  MEMPOOL_API_URL
        self.whoami = whoami

    def mempool_request(self, uri_path: str) -> Result[Box, str]:
        res = Box(requests.get(
            self.api_url + uri_path,
        ).json())
        # TODO: handle error
        return Ok(res)
   
    def get_fee(self) -> Result[Box, str]:
        # TODO LOG_INFO
        return self.mempool_request("fees/recommended")
    

class BitcoinCore:
    def __init__(self, creds_path: str) -> None:
        self.creds = config.get_creds(creds_path, 'bitcoincore')

    def rpc_request(self, method: str, params: List) -> Result[Box, str]: # type: ignore
        url = f"http://{self.creds.rpc_user}:{self.creds.rpc_password}@{self.creds.rpc_host}:{self.creds.rpc_port}"
        payload = { 'method': method, 'params': params, 'jsonrpc': '2.0', 'id': '1' }
        response = requests.post(url, json=payload)
        response_json = response.json()
        if 'error' in response_json and response_json['error'] != None:
            return Err(response_json['error'])        
        return Box(response_json)