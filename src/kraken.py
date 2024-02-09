"""
kraken.py
---
An implementation of Kraken Wallet API as a TrustedSwapService
usage: add your kraken credentials
"""
import sys
import time
import requests # type: ignore
import urllib.parse
import hashlib
import hmac
import base64
from trusted_swap_service import TrustedSwapService
from const import COIN_SATS, LOG_ERROR, LOG_INFO
from typing import Dict
from result import Result, Ok, Err
from box import Box

KRAKEN_API_URL = "https://api.kraken.com/"

class KrakenCreds:
    """
    create a kraken API key with funding permissions
        go to the onchain bitcoin widthdraw page on kraken.com and 
        add a new withdraw address, give it a description/name and use that 
        same description/name for the `funding_key` below
    """
    def __init__(self, api_key: str, api_secret: str, funding_key: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.funding_key = funding_key

class Kraken(TrustedSwapService):
    def __init__(self, creds: KrakenCreds) -> None:
        super().__init__() # init logger from parent class
        self.creds = creds
        self.alias = f"kraken-{creds.api_key[:5]}"

    @staticmethod
    def get_kraken_signature(urlpath: str, data: Dict, secret: str) -> str: # type: ignore
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    @staticmethod
    def get_nonce() -> str:
        return str(int(1000 * time.time()))

    def check_errors(self, response: Dict, payload: Dict, endpoint: str) -> None: # type: ignore
        if response['error']:
            for err in response['error']:
                self.log(LOG_ERROR, f"kraken responded with error: {err}\nendpoint: {endpoint}\npayload: {payload}")
            sys.exit()

    def kraken_request(self, uri_path: str, data: Dict) -> Box: # type: ignore
        headers = {}
        headers['API-Key'] = self.creds.api_key
        headers['API-Sign'] = self.get_kraken_signature(
            uri_path,
            data,
            self.creds.api_secret
        )
        res = requests.post(
            (KRAKEN_API_URL + uri_path),
            headers=headers,
            data=data
        ).json()['result']
        return Box(res)

    def get_address(self) -> Result[str, str]:
        """TrustedSwapService"""
        response = self.kraken_request(
            '0/private/DepositAddresses', 
            {
                "nonce": self.get_nonce(),
                "asset": "XBT",
                "method": "Bitcoin",
            }
        )
        if response.error:
            return Err(self.logs.get_address.err.format(self.alias, response))
        addr: str = response[0].address
        self.log(LOG_INFO, self.logs.get_address.ok.format(self.alias, addr))
        return Ok(addr)

    def send_onchain(self, sats: int, fee: int) -> Result[None, str]:
        """TrustedSwapService"""
        response = self.kraken_request(
            '0/private/Withdraw', 
            {
                "nonce": self.get_nonce(),
                "asset": "XBT",
                "key": self.creds.funding_key,
                "amount": sats / COIN_SATS
            }
        )
        if response.error:
            return Err(self.logs.send_onchain.err.format(self.alias, response))
        self.log(LOG_INFO, self.logs.send_onchain.ok.format(self.alias, sats, fee))
        return Ok(None)

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        """TrustedSwapService"""
        response = self.kraken_request(
            '0/private/WithdrawInfo', 
            {
                "nonce": self.get_nonce(),
                "asset": "XBT",
                "key": self.creds.funding_key,
                "amount": float(sats / COIN_SATS)
            }
        )
        if response.error:
            return Err(self.logs.get_onchain_fee.err.format(self.alias, response))
        sats = int(float(response.amount) * COIN_SATS)
        fee = int(float(response.fee) * COIN_SATS)
        self.log(LOG_INFO, self.logs.get_onchain_fee.ok.format(self.alias, sats, fee))
        return Ok(fee)

    def get_balance(self) -> Result[int, str]:
        """TrustedSwapService"""
        response = self.kraken_request(
            '0/private/Balance', 
            {"nonce": self.get_nonce()}
        )
        if response.error:
            return Err(self.logs.get_balance.err.format(self.alias, response))
        balance = int(float(response.XXBT) * COIN_SATS)
        self.log(LOG_INFO, self.logs.get_balance.format(self.alias, balance))
        return Ok(balance)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """TrustedSwapService"""
        response = self.kraken_request(
            '0/private/DepositAddresses', 
            {
                "nonce": self.get_nonce(),
                "asset": "XBT",
                "method": "Bitcoin Lightning",
                "new": True,
                "amount": sats / COIN_SATS
            }
        )
        if response.error:
            return Err(self.logs.get_invoice.err.format(self.alias, response))
        invoice: str = response[0].address
        self.log(LOG_INFO, self.logs.get_invoice.ok.format(self.alias, invoice, sats))
        return Ok(invoice)
    