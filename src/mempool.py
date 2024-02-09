"""
mempool.py
---
An implementation of Mempool.space API as a TrustedSwapService
usage: add your mempool credentials to use a self-hosted instance
"""
import requests # type: ignore
from box import Box
from result import Result, Ok, Err
from const import LOG_GAP, LOG_INFO
from console import console

MEMPOOL_API_URL = "https://mempool.space/"

class MempoolCreds:
    """
    use a Mempool API for fee estimation
        use your own instance to avoid rate limits
    """
    def __init__(self, api_url: str = MEMPOOL_API_URL) -> None:
        self.api_url = api_url

class Mempool:
    def __init__(self, creds: MempoolCreds) -> None:
        self.api_url = f"{creds.api_url}api/v1/"
        self.alias = "MEMPOOL"
        self.log = console.log
        self.logs = Box({
            "api_request": {
                "ok": LOG_GAP.join(["{}", "api_request", "url: {}, response: {}"]),
                "err": LOG_GAP.join(["{}", "api_request", "url: {}, response: {}"]),
            },
            "get_fee": {
                "ok": LOG_GAP.join(["{}", "get_fee", "fastest: {}, halfHour: {}, hour: {}, economy: {}, minimum: {}"])
            }
        })

    def mempool_request(self, uri_path: str) -> Result[Box, str]:
        res = Box(requests.get(
            self.api_url + uri_path,
        ).json())
        # TODO: handle error
        self.log(LOG_INFO, self.logs.api_request.ok.format(self.alias, uri_path, res))
        return Ok(res)
   
    def get_fee(self) -> Result[Box, str]:
        # TODO LOG_INFO
        response = self.mempool_request("fees/recommended")
        res = response.unwrap()
        self.log(LOG_INFO, self.logs.get_fee.ok.format(self.alias, res.fastestFee, res.halfHourFee, res.hourFee, res.economyFee, res.minimumFee))
        return response
