from datetime import datetime
from time import mktime
import uuid
import hmac
import requests # type: ignore
import json
from hashlib import sha256
from base import TrustedSwapService
from const import COIN_SATS, NICEHASH_API_URL, LOG_ERROR, LOG_INFO, LOG_TRUSTED_SWAP_SERVICE as logs
from config import config
from typing import Any, Dict
from result import Result, Ok, Err
from box import Box

class Nicehash(TrustedSwapService):
    def __init__(self, creds_path: str) -> None:
        self.creds = config.get_creds(creds_path, 'nicehash')  

    def nicehash_request(self, method: str, path: str, query: str, body: Dict | None) -> Box: # type: ignore
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
        return Box(response.json())
    
    @staticmethod
    def get_epoch_ms_from_now() -> int:
        now = datetime.now()
        now_ec_since_epoch = mktime(
            now.timetuple()) + now.microsecond / 1000000.0
        return int(now_ec_since_epoch * 1000)

    def get_address(self) -> Result[str, str]:
        """TrustedSwapService"""
        msg = logs.get_address
        res = self.nicehash_request(
            "GET", 
            'main/api/v2/accounting/depositAddresses', 
            'currency=BTC&walletType=BITGO', 
            None # no body params
        )
        if res.content:
            return Err(msg.err.format('nicehash', res))
        addr: str = res.list[0].address
        config.log(LOG_INFO, msg.ok.format('nicehash', addr))
        return Ok(addr)

    def send_onchain(self, sats: int, fee: int) -> Result[None, str]:
        """TrustedSwapService"""
        msg = logs.send_onchain
        amount_sats = str(float(sats) / COIN_SATS)
        body = {
            "currency": "BTC",
            "amount": amount_sats,
            "withdrawalAddressId": self.creds.funding_key
        }
        res = self.nicehash_request(
            "POST", 
            "main/api/v2/accounting/withdrawal", 
            '', # no url params
            body
        )
        if res.content:
            return Err(msg.err.format('nicehash', res))
        config.log(LOG_INFO, msg.ok.format('nicehash', sats, fee))
        return Ok(None)

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        """TrustedSwapService"""
        msg = logs.get_onchain_fee
        res = self.nicehash_request(
            "GET", 
            "main/api/v2/public/service/fee/info", 
            '', # no url params
            None # no body params
        )
        if res.content:
            return Err(msg.err.format('nicehash', res))
        fee = int(float(res.withdrawal.BITGO.rules.BTC.intervals[0].element.sendValue) * COIN_SATS)
        config.log(LOG_INFO, msg.ok.format('nicehash', sats, fee))
        return Ok(fee)

    def get_balance(self) -> Result[int, str]:
        """TrustedSwapService"""
        msg = logs.get_balance
        res = self.nicehash_request(
            "GET",
            "main/api/v2/accounting/account2/BTC", 
            '', # no url params 
            None # no body params
        )
        if res.content:
            return Err(msg.err.format('nicehash', res))
        balance = int(float(res.available) * COIN_SATS)
        config.log(LOG_INFO, msg.ok('nicehash', balance))
        return Ok(balance)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """TrustedSwapService"""
        msg = logs.get_invoice
        res = self.nicehash_request(
            "GET", 
            "main/api/v2/accounting/depositAddresses",
            f'currency=BTC&walletType=LIGHTNING&amount={float(sats) / COIN_SATS}',
            None # no body params
        )
        if res.content:
            return Err(msg.err.format('nicehash', res))
        invoice: str = res.list[0].address
        config.log(LOG_INFO, msg.ok.format('nicehash', invoice, sats))
        return Ok(invoice)
  