import requests

COIN_SATS = 100_000_000


class Mempool:
    def __init__(self, MEMPOOL_CONFIG, logger):
        self.log = logger
        self.api_url = MEMPOOL_CONFIG['api_url']

    def mempool_request(self, uri_path, data):
        req = requests.get(
            (self.api_url + uri_path),
            data=data
        ).json()
        return req

    def get_fee(self):
        return self.mempool_request("fees/recommended", {})

