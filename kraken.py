import sys
import time
import requests
import urllib.parse
import hashlib
import hmac
import base64
from base import TrustedSwapService
from const import COIN_SATS, KRAKEN_API_URL, LOG_ERROR, LOG_INFO, LOG_TRUSTED_SWAP_SERVICE as logs
import config
from typing import Dict
from result import Result, Ok, Err
from box import Box

class Kraken(TrustedSwapService):
    def __init__(self) -> None:
        self.creds = config.get_creds("kraken")

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
                config.log(LOG_ERROR, f"kraken responded with error: {err}\nendpoint: {endpoint}\npayload: {payload}")
            sys.exit()

    def kraken_request(self, uri_path: str, data: Dict) -> Box:
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
        msg = logs.get_address
        response = self.kraken_request(
            '0/private/DepositAddresses', 
            {
                "nonce": self.get_nonce(),
                "asset": "XBT",
                "method": "Bitcoin",
            }
        )
        if response.error:
            return Err(msg.err.format('kraken', response))
        addr: str = response[0].address
        config.log(LOG_INFO, msg.ok.format('kraken', addr))
        return Ok(addr)

    def send_onchain(self, sats: int, fee: int) -> Result[None, str]:
        """TrustedSwapService"""
        msg = logs.send_onchain
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
            return Err(msg.err.format('kraken', response))
        config.log(LOG_INFO, msg.ok.format('kraken', sats, fee))
        return Ok(None)

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        """TrustedSwapService"""
        msg = logs.get_onchain_fee
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
            return Err(msg.err.format('kraken', response))
        sats = int(float(response.amount) * COIN_SATS)
        fee = int(float(response.fee) * COIN_SATS)
        config.log(LOG_INFO, msg.ok.format('kraken', sats, fee))
        return Ok(fee)

    def get_balance(self) -> Result[int, str]:
        """TrustedSwapService"""
        msg = logs.get_balance
        response = self.kraken_request(
            '0/private/Balance', 
            {"nonce": self.get_nonce()}
        )
        if response.error:
            return Err(msg.err.format('kraken', response))
        balance = int(float(response.XXBT) * COIN_SATS)
        config.log(LOG_INFO, logs.get_balance.format('kraken', balance))
        return Ok(balance)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """TrustedSwapService"""
        msg = logs.get_invoice
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
            return Err(msg.err.format('kraken', response))
        invoice: str = response[0].address
        config.log(LOG_INFO, msg.ok.format('kraken', invoice, sats))
        return Ok(invoice)
    