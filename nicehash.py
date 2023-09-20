from datetime import datetime
from time import mktime
import uuid
import hmac
import requests
import json
from hashlib import sha256
import sys
from base import TrustedSwapService
from const import COIN_SATS, NICEHASH_API_URL, LOG_ERROR, LOG_INFO, LOG_TRUSTED_SWAP_SERVICE as logs
from config import get_creds, log
from typing import Any, Dict

class Nicehash(TrustedSwapService):
    def __init__(self) -> None:
        self.creds = get_creds('nicehash')  

    def nicehash_request(self, method: str, path: str, query: str, body: Dict | None) -> dict[Any, Any]:
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
        headers: dict[str, Any] = {
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
        self.check_errors(response, body, url)
        res: dict[Any, Any] = response.json()
        return res
    
    @staticmethod
    def get_epoch_ms_from_now() -> int:
        now = datetime.now()
        now_ec_since_epoch = mktime(
            now.timetuple()) + now.microsecond / 1000000.0
        return int(now_ec_since_epoch * 1000)

    def check_errors(self, response, body: Dict, url: str) -> None:
        if response.content:
            err_msg = f"Nicehash {response.status_code} {url}: {response.reason}: {response.content}"
        else:
            err_msg = f"Nicehash {response.status_code} {url}: {response.reason}"
        #TODO self.log.notify(err_msg)
        log(LOG_ERROR, err_msg)
        sys.exit()

    def get_address(self) -> str:
        """TrustedSwapService"""
        res = self.nicehash_request("GET", 'main/api/v2/accounting/depositAddresses', 'currency=BTC&walletType=BITGO', None)
        addr: str = res['list'][0]['address']
        log(LOG_INFO, logs.get_address.format('nicehash', addr))
        return addr

    def send_onchain(self, sats: int, fee: int) -> dict[Any, Any]:
        """TrustedSwapService"""
        amount_sats = str(float(sats) / COIN_SATS)
        body = {
            "currency": "BTC",
            "amount": amount_sats,
            "withdrawalAddressId": self.creds.funding_key
        }
        response: dict[Any, Any] = self.nicehash_request(
            "POST", "main/api/v2/accounting/withdrawal", '', body)
        log(LOG_INFO, logs.send_onchain.format('nicehash', sats, fee))
        return response

    def get_onchain_fee(self, sats: int) -> int:
        """TrustedSwapService"""
        response = self.nicehash_request(
            "GET", "main/api/v2/public/service/fee/info", '', None)
        fee = int(float(response['withdrawal']['BITGO']['rules']['BTC']
                  ['intervals'][0]['element']['sndValue']) * COIN_SATS)
        log(LOG_INFO, logs.get_onchain_fee.format('nicehash', sats, fee))
        return fee

    def get_balance(self) -> int:
        """TrustedSwapService"""
        response = self.nicehash_request(
            "GET", "main/api/v2/accounting/account2/BTC", '', None)
        balance = int(float(response['available']) * COIN_SATS)
        log(LOG_INFO, logs.get_balance('nicehash', balance))
        return balance

    def get_invoice(self, sats: int) -> str:
        """TrustedSwapService"""
        response = self.nicehash_request(
            "GET", 
            "main/api/v2/accounting/depositAddresses",
            f'currency=BTC&walletType=LIGHTNING&amount={float(sats) / COIN_SATS}',
            None
        )
        invoice: str = response['list'][0]['address']
        log(LOG_INFO, logs.get_onchain_fee.format('nicehash', invoice, sats))
        return invoice
    
    def pay_invoice(self, invoice: str, sats: int) -> dict[Any, Any]:
        """TrustedSwapService"""
        #TODO implement
        log(LOG_INFO, logs.pay_invoice('nicehash', invoice, sats))
        return super().pay_invoice(invoice, sats)
