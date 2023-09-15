import sys
import time
import requests
import urllib.parse
import hashlib
import hmac
import base64
from base import TrustedSwapService
from const import COIN_SATS, KRAKEN_API_URL


class Kraken(TrustedSwapService):
    def __init__(self, creds):
        self.creds = creds

    @staticmethod
    def get_kraken_signature(urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def check_errors(self, response, payload, endpoint):
        if response['error']:
            for err in response['error']:
                err_msg = f"kraken responded with error: {err}\nendpoint: {endpoint}\npayload: {payload}"
            sys.exit()

    def kraken_request(self, uri_path, data):
        headers = {}
        headers['API-Key'] = self.creds.api_key
        headers['API-Sign'] = self.get_kraken_signature(
            uri_path,
            data,
            self.creds.api_secret
        )
        req = requests.post(
            (KRAKEN_API_URL + uri_path),
            headers=headers,
            data=data
        ).json()
        self.check_errors(req, data, uri_path)
        return req['result']

    def get_address(self):
        payload = {
            "nonce": str(int(1000 * time.time())),
            "asset": "XBT",
            "method": "Bitcoin",
        }
        res = self.kraken_request('/0/private/DepositAddresses', payload)
        addr = res[0]['address']
        return addr

    def send_onchain(self, sats, _):
        # kraken does not use variable fee
        payload = {
            "nonce": str(int(1000 * time.time())),
            "asset": "XBT",
            "key": self.creds.funding_key,
            "amount": sats / COIN_SATS
        }
        res = self.kraken_request('/0/private/Withdraw', payload)
        return res

    def estimate_onchain_fee(self, amount: int):
        payload = {
            "nonce": str(int(1000 * time.time())),
            "asset": "XBT",
            "key": self.creds.funding_key,
            "amount": float(amount / COIN_SATS)
        }
        res = self.kraken_request('/0/private/WithdrawInfo', payload)
        fee_quote = {
            'amount': int(float(res['amount']) * COIN_SATS),
            'fee': int(float(res['fee']) * COIN_SATS)
        }
        return fee_quote['fee']

    def get_pending_send_sats(self):
        sends = self.get_recent_sends()
        pending_amt = 0
        for w in sends:
            if w['status'] in ['Initial', 'Pending']:
                pending_amt += int(float(w['amount']) * COIN_SATS)
        return pending_amt

    def get_recent_sends(self):
        payload = {
            "nonce": str(int(1000 * time.time())),
            "asset": "XBT"
        }
        res = self.kraken_request('/0/private/WithdrawStatus', payload)
        return res

    def get_balance(self):
        payload = {"nonce": str(int(1000 * time.time()))}
        res = self.kraken_request('/0/private/Balance', payload)
        balance = int(float(res['XXBT']) * COIN_SATS)
        return balance

    def get_invoice(self, amount_sats):
        print('todo')