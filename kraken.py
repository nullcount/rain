import sys
import time
import requests
import urllib.parse
import hashlib
import hmac
import base64
from base import TrustedSwapService
from const import COIN_SATS, KRAKEN_API_URL, LOG_ERROR, LOG_INFO, LOG_TRUSTED_SWAP_SERVICE as logs
from config import get_creds, log
from typing import Dict, Any

class Kraken(TrustedSwapService):
    def __init__(self) -> None:
        self.creds = get_creds("kraken")

    @staticmethod
    def get_kraken_signature(urlpath: str, data: Dict, secret: str) -> str:
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    @staticmethod
    def get_nonce() -> str:
        return str(int(1000 * time.time()))

    @staticmethod
    def check_errors(response: Dict, payload: Dict, endpoint: str) -> None:
        if response['error']:
            for err in response['error']:
                log(LOG_ERROR, f"kraken responded with error: {err}\nendpoint: {endpoint}\npayload: {payload}")
            sys.exit()

    def kraken_request(self, uri_path: str, data: Dict) -> dict[Any, Any]:
        headers = {}
        headers['API-Key'] = self.creds.api_key
        headers['API-Sign'] = self.get_kraken_signature(
            uri_path,
            data,
            self.creds.api_secret
        )
        req: dict[Any, Any] = requests.post(
            (KRAKEN_API_URL + uri_path),
            headers=headers,
            data=data
        ).json()['result']
        self.check_errors(req, data, uri_path)
        return req

    def get_address(self) -> str:
        """TrustedSwapService"""
        payload: dict[str, Any] = {
            "nonce": self.get_nonce(),
            "asset": "XBT",
            "method": "Bitcoin",
        }
        response = self.kraken_request('0/private/DepositAddresses', payload)
        addr: str = response[0]['address']
        log(LOG_INFO, logs.get_address.format('kraken', addr))
        return addr

    def send_onchain(self, sats: int, fee: int | None) -> dict[Any, Any]:
        """TrustedSwapService"""
        payload: dict[str, Any] = {
            "nonce": self.get_nonce(),
            "asset": "XBT",
            "key": self.creds.funding_key,
            "amount": sats / COIN_SATS
        }
        response = self.kraken_request('0/private/Withdraw', payload)
        log(LOG_INFO, logs.send_onchain.format('kraken', sats, fee))
        return response

    def get_onchain_fee(self, sats: int) -> int:
        """TrustedSwapService"""
        payload: dict[str, Any] = {
            "nonce": self.get_nonce(),
            "asset": "XBT",
            "key": self.creds.funding_key,
            "amount": float(sats / COIN_SATS)
        }
        response = self.kraken_request('0/private/WithdrawInfo', payload)
        sats = int(float(response['amount']) * COIN_SATS)
        fee = int(float(response['fee']) * COIN_SATS)
        log(LOG_INFO, logs.get_onchain_fee.format('kraken', sats, fee))
        return fee

    def get_balance(self) -> int:
        """TrustedSwapService"""
        payload = {"nonce": self.get_nonce()}
        response = self.kraken_request('0/private/Balance', payload)
        balance = int(float(response['XXBT']) * COIN_SATS)
        log(LOG_INFO, logs.get_balance.format('kraken', balance))
        return balance

    def get_invoice(self, sats: int) -> str:
        """TrustedSwapService"""
        payload: dict[str, Any] = {
            "nonce": self.get_nonce(),
            "asset": "XBT",
            "method": "Bitcoin Lightning",
            "new": True,
            "amount": sats / COIN_SATS
        }
        response = self.kraken_request('0/private/DepositAddresses', payload)
        invoice: str = response[0]['address']
        log(LOG_INFO, logs.get_invoice.format('kraken', invoice, sats))
        return invoice
    
    def pay_invoice(self, invoice: str, sats: int) -> dict[Any, Any]:
        """TrustedSwapService"""
        #TODO implement
        log(LOG_INFO, logs.format('kraken', invoice, sats))
        return super().pay_invoice(invoice, sats)