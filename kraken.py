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
        self.funding_key = KRAKEN_CONFIG['funding_key']
        self.log_msg_map = {
            "get_onchain_address": lambda addr: f"kraken deposit address: {addr}",
            "send_onchain": lambda sats: f"kraken initiated {sats} sat widthdrawl",
            "get_onchain_fee": lambda fee, sats: f"kraken fee: {fee} sats widthdraw amount: {sats} sats",
            "get_pending_send_sats": lambda status, ref, amt : f"kraken [{status}] widthdraw #{ref} of {amt} sats",
            "get_account_balance": lambda sats: f"kraken account balance: {sats} sats",
            "send_to_acct": lambda sats: f"Hey boss, {int(sats)} sats ready for kraken deposit"
        }

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
                err_msg = f"kraken responded with error: {err}"
                self.log.error(err_msg)
                self.log.notify(err_msg)
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
        ).json()
        self.check_errors(req, data, uri_path)
        return req['result']

    def get_onchain_address(self):
        payload = {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT",
            "method": "Bitcoin",
        }
        res = self.kraken_request('/0/private/DepositAddresses', payload)
        addr = res[0]['address']
        self.log.info(self.log_msg_map['get_onchain_address'](addr))
        return addr

    def send_onchain(self, sats):
        payload = {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT",
            "key": self.funding_key,
            "amount": sats / COIN_SATS
        }
        res = self.kraken_request('/0/private/Withdraw', payload)
        self.log.info(self.log_msg_map['send_onchain'](sats))
        return res

    def get_onchain_fee(self, sats):
        payload = {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT",
            "key": self.funding_key,
            "amount": sats / COIN_SATS
        }
        res = self.kraken_request('/0/private/WithdrawInfo', payload)
        fee_quote = {
            'amount': int(float(res['amount']) * COIN_SATS),
            'fee': int(float(res['fee']) * COIN_SATS)
        }
        self.log.info(self.log_msg_map['get_onchain_address'](fee_quote['fee'], sats))
        return fee_quote['fee']

    def get_pending_send_sats(self):
        sends = self.get_recent_sends()
        pending_amt = 0
        for w in sends:
            if w['status'] in ['Initial']: # Pending status is considered unconfirmed
                pending_amt += int(float(w['amount']) * COIN_SATS)
                self.log.info(self.log_msg_map['get_pending_send_sats'](w['status'].lower(), w['refid'], w['amount']))
        return pending_amt

    def get_recent_sends(self):
        payload = {
            "nonce": str(int(1000*time.time())),
            "asset": "XBT"
        }
        res = self.kraken_request('/0/private/WithdrawStatus', payload)
        return res

    def get_account_balance(self):
        payload = {"nonce": str(int(1000*time.time()))}
        res = self.kraken_request('/0/private/Balance', payload)
        balance = int(float(res['XXBT']) * COIN_SATS)
        self.log.info(self.log_msg_map['get_account_balance'](balance))
        return balance

    def send_to_acct(self, sats, node):
        self.log.notify(self.log_msg_map['send_to_acct'](int(sats)))

    def pay_invoice(self, invoice_code):
        # TODO kraken hasn't implemented yet
        return

    def get_lightning_invoice(self):
        # TODO kraken needs to implement
        return
