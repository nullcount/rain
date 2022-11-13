import sys
import time
import requests
import urllib.parse
import hashlib
import hmac
import base64

COIN_SATS = 100_000_000


class Kraken:
    def __init__(self, KRAKEN_CONFIG, logger):
        self.log = logger
        self.api_url = "https://api.kraken.com/"
        self.api_key = KRAKEN_CONFIG['api_key']
        self.api_secret = KRAKEN_CONFIG['api_secret']
        self.widthdraw_key = KRAKEN_CONFIG['widthdraw_key']

    @staticmethod
    def get_kraken_signature(urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def check_errors(self, response, payload, endpoint):
        if response['errors']:
            for err in response['errors']:
                self.log.error("kraken responded with error: {}".format(err))
            self.log.error('using payload: {}'.format(payload))
            self.log.error('from : {}'.format(endpoint))
            sys.exit()

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
        self.check_errors(req, data, uri_path)
        return req

    def get_onchain_address(self):
        payload = {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT",
            "method": "Bitcoin",
        }
        res = self.kraken_request('/0/private/DepositAddresses', payload).json()
        addr = res['result'][0]['address']
        self.log.info("kraken deposit address: {}".format(addr))
        return addr

    def widthdraw_onchain(self, sats):
        payload = {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT",
            "key": self.widthdraw_key,
            "amount": sats / COIN_SATS
        }
        res = self.kraken_request('/0/private/Withdraw', payload)
        self.log.info("kraken initiated {} sat widthdrawl".format(sats))
        return res

    def get_widthdraw_info(self, sats):
        payload = {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT",
            "key": self.widthdraw_key,
            "amount": sats / COIN_SATS
        }
        res = self.kraken_request('/0/private/WithdrawInfo', payload).json()['result']
        fee_quote = {
            'amount': int(float(res['amount']) * COIN_SATS),
            'fee': int(float(res['fee']) * COIN_SATS)
        }
        self.log.info("kraken fee: {} sats widthdrawl amount: {} sats".format(fee_quote['fee'], sats))
        return fee_quote

    def get_recent_widthdraws(self):
        payload = {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT"
        }
        res = self.kraken_request('/0/private/WithdrawStatus', payload).json()
        return res

    def get_account_balance(self):
        payload = {"nonce": str(int(1000*time.time()))}
        res = self.kraken_request('/0/private/Balance', payload).json()
        balance = int(float(res['result']['XXBT']) * COIN_SATS)
        self.log.info("kraken account balance: {} sats".format(balance))
        return balance

    def pay_invoice(self, invoice_code):
        # TODO kraken hasn't implemented yet
        return

    def get_lightning_invoice(self):
        # TODO kraken needs to implement
        return
