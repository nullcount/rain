from datetime import datetime
from time import mktime
import uuid
import hmac
import requests
import json
from hashlib import sha256
import sys
from base import TrustedSwapService
from const import COIN_SATS, NICEHASH_API_URL


class Nicehash(TrustedSwapService):
    def __init__(self, creds):
        self.creds = creds   

    def nicehash_request(self, method, path, query, body):
        xtime = self.get_epoch_ms_from_now()
        xnonce = str(uuid.uuid4())
        message = bytearray(self.creds.api_key, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(str(xtime), 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(xnonce, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(self.creds.org_id, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(method, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(path, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(query, 'utf-8')
        if body:
            body_json = json.dumps(body)
            message += bytearray('\x00', 'utf-8')
            message += bytearray(body_json, 'utf-8')

        digest = hmac.new(bytearray(self.creds.api_secret,
                          'utf-8'), message, sha256).hexdigest()
        xauth = self.creds.api_key + ":" + digest
        headers = {
            'X-Time': str(xtime),
            'X-Nonce': xnonce,
            'X-Auth': xauth,
            'Content-Type': 'application/json',
            'X-Organization-Id': self.creds.org_id,
            'X-Request-Id': str(uuid.uuid4())
        }
        s = requests.Session()
        s.headers = headers
        url = NICEHASH_API_URL + path
        if query:
            url += '?' + query
        if body:
            response = s.request(method, url, data=body_json)
        else:
            response = s.request(method, url)
        if response.status_code == 200:
            return response.json()
        else:
            self.check_errors(response, body, url)

    def get_epoch_ms_from_now(self):
        now = datetime.now()
        now_ec_since_epoch = mktime(
            now.timetuple()) + now.microsecond / 1000000.0
        return int(now_ec_since_epoch * 1000)

    def check_errors(self, response, payload, endpoint):
        if response.content:
            err_msg = f"Nicehash {response.status_code} {endpoint}: {response.reason}: {response.content}"
        else:
            err_msg = f"Nicehash {response.status_code} {endpoint}: {response.reason}"
        #TODO self.log.notify(err_msg)
        sys.exit()

    def get_onchain_address(self):
        res = self.nicehash_request("GET", 'main/api/v2/accounting/depositAddresses', 'currency=BTC&walletType=BITGO',
                                    None)
        addr = res['list'][0]['address']
        #TODO: self.log.info(self.log_msg_map['get_onchain_address'](addr))
        return addr

    def send_onchain(self, sats, fee):
        amt = str(float(sats) / COIN_SATS)
        body = {
            "currency": "BTC",
            "amount": amt,
            "withdrawalAddressId": self.creds.funding_key
        }
        res = self.nicehash_request(
            "POST", "main/api/v2/accounting/withdrawal", '', body)
        #TODO: self.log.info(self.log_msg_map['send_onchain'](sats))
        return res

    def estimate_onchain_fee(self, amount: int):
        res = self.nicehash_request(
            "GET", "main/api/v2/public/service/fee/info", '', None)
        fee = int(float(res['withdrawal']['BITGO']['rules']['BTC']
                  ['intervals'][0]['element']['sndValue']) * COIN_SATS)
        #TODO:self.log.info(self.log_msg_map['get_onchain_fee'](amount, fee))
        return fee

    def get_recent_sends(self):
        res = self.nicehash_request(
            "GET", "main/api/v2/accounting/withdrawals/BTC", '', None)
        return res

    def get_account_balance(self):
        res = self.nicehash_request(
            "GET", "main/api/v2/accounting/account2/BTC", '', None)
        balance = int(float(res['available']) * COIN_SATS)
        #TODO:self.log.info(self.log_msg_map['get_account_balance'](balance))
        return balance

    def get_lightning_invoice(self, sats):
        res = self.nicehash_request("GET", "main/api/v2/accounting/depositAddresses",
                                    f'currency=BTC&walletType=LIGHTNING&amount={float(sats) / COIN_SATS}', None)
        invoice = res['list'][0]['address']
        #TODO:self.log.info(self.log_msg_map['get_lightning_invoice'](sats, invoice))
        return invoice
