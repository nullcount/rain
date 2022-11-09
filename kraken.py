import time
import os
import requests


import urllib.parse
import hashlib
import hmac
import base64


class Kraken:
    def __init__(self, KRAKEN_CONFIG):
        self.api_url = "https://api.kraken.com/"
        self.api_key = KRAKEN_CONFIG['api_key']
        self.api_secret = KRAKEN_CONFIG['api_secret']

    @staticmethod
    def get_kraken_signature(urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def kraken_request(self, uri_path, data):
        headers = {}
        headers['API-Key'] = self.api_key
        headers['API-Sign'] = self.get_kraken_signature(
            uri_path,
            data,
            self.api_secret
        )
        req = requests.post(
            (self.api_url + uri_path),
            headers=headers,
            data=data
        )
        return req

    def get_lightning_invoice(self):
        return self.kraken_request('/0/private/DepositAddresses', {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT",
            "method": "Bitcoin Lightning",
            "new": True
        }).json()

    def get_onchain_address(self):
        return self.kraken_request('/0/private/DepositAddresses', {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT",
            "method": "Bitcoin",
        }).json()['result'][0]['address']
