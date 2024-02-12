"""
nicehash.py
---
An implementation of Nicehash Wallet API as a TrustedSwapService
usage: add your nicehash credentials
"""
from datetime import datetime
from time import mktime
import uuid
import hmac
import requests # type: ignore
import json
from hashlib import sha256
from trusted_swap_service import TrustedSwapService
from const import COIN_SATS, LOG_ERROR, LOG_INFO
from typing import Any, Dict
from result import Result, Ok, Err
from box import Box

NICEHASH_API_URL = "https://api2.nicehash.com"

class NicehashCreds:
    """
    create a nicehash API key with wallet permissions
        add a whitelisted withdrawl address and use the API to find the withdrawlAddressId
        after adding, click "Edit" to reveal the id for funding_key 
        should look like xxxxxxxx-xxxx-xxxx-xxxxx-xxxxxxxxxxxx
        nicehash will delay your first widthdraw to a new address for many hours
    """
    def __init__(self, api_key: str, api_secret: str, org_id: str, funding_key: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.org_id = org_id
        self.funding_key = funding_key

class Nicehash(TrustedSwapService):
    def __init__(self, creds: NicehashCreds) -> None:
        super().__init__() # init logger from parent class
        self.creds = creds 
        self.alias = f"NICEHASH-{creds.api_key[:5]}"

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
        res = self.nicehash_request(
            "GET", 
            '/main/api/v2/accounting/depositAddresses', 
            'currency=BTC&walletType=BITGO', 
            None # no body params
        )
        if hasattr(res, "content"):
            return Err(self.logs.get_address.err.format(self.alias, res))
        addr: str = res.list[0].address
        self.log(LOG_INFO, self.logs.get_address.ok.format(self.alias, addr))
        return Ok(addr)

    def send_onchain(self, sats: int, fee: int) -> Result[None, str]:
        """TrustedSwapService"""
        amount_sats = str(float(sats) / COIN_SATS)
        body = {
            "currency": "BTC",
            "amount": amount_sats,
            "withdrawalAddressId": self.creds.funding_key
        }
        res = self.nicehash_request(
            "POST", 
            "/main/api/v2/accounting/withdrawal", 
            '', # no url params
            body
        )
        if hasattr(res, "content"):
            return Err(self.logs.send_onchain.err.format(self.alias, res))
        self.log(LOG_INFO, self.logs.send_onchain.ok.format(self.alias, sats, fee))
        return Ok(None)

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        """TrustedSwapService"""
        res = self.nicehash_request(
            "GET", 
            "/main/api/v2/public/service/fee/info", 
            '', # no url params
            None # no body params
        )
        if hasattr(res, "content"):
            return Err(self.logs.get_onchain_fee.err.format(self.alias, res))
        fee = int(float(res.withdrawal.BITGO.rules.BTC.intervals[0].element.sendValue) * COIN_SATS)
        self.log(LOG_INFO, self.logs.get_onchain_fee.ok.format(self.alias, sats, fee))
        return Ok(fee)

    def get_balance(self) -> Result[int, str]:
        """TrustedSwapService"""
        res = self.nicehash_request(
            "GET",
            "/main/api/v2/accounting/account2/BTC", 
            '', # no url params 
            None # no body params
        )
        if hasattr(res, 'content'):
            return Err(self.logs.get_balance.err.format(self.alias, res))
        balance = int(float(res.available) * COIN_SATS)
        self.log(LOG_INFO, self.logs.get_balance.ok.format(self.alias, balance))
        return Ok(balance)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """TrustedSwapService"""
        res = self.nicehash_request(
            "GET", 
            "/main/api/v2/accounting/depositAddresses",
            f'currency=BTC&walletType=LIGHTNING&amount={float(sats) / COIN_SATS}',
            None # no body params
        )
        if hasattr(res, "content"):
            return Err(self.logs.get_invoice.err.format(self.alias, res))
        invoice: str = res.list[0].address.split(":")[1]
        self.log(LOG_INFO, self.logs.get_invoice.ok.format(self.alias, invoice, sats))
        return Ok(invoice)
  
    def pay_invoice(self, sats: int, invoice: str) -> Result[str, str]:
        """TrustedSwapService"""
        body1 = {
            "address": invoice,
            "currency": "BTC",
            "name": "Lightning Invoice code",
            "type": "LIGHTNING"
        }
        res1 = self.nicehash_request("POST", "/main/api/v2/accounting/withdrawalAddress", '', body1)
        if not hasattr(res1, 'id'):
            return Err(self.logs.pay_invoice.err.format(self.alias, res1))
        amount_sats = str(float(sats) / COIN_SATS)
        body2 = {
            "currency": "BTC",
            "amount": amount_sats,
            "withdrawalAddressId": res1.id,
            "walletType": "LIGHTNING"
        }
        res2 = self.nicehash_request(
            "POST", 
            "/main/api/v2/accounting/withdrawal", 
            '', # no url params
            body2
        )
        if hasattr(res2, "content"):
            return Err(self.logs.pay_invoice.err.format(self.alias, res2))
        res3 = self.nicehash_request("GET", f"/main/api/v2/accounting/withdrawal2/BTC/{res2.id}", "", {})
        fee = int((res3.amount - res3.amountReceived) * COIN_SATS)
        self.log(LOG_INFO, self.logs.pay_invoice.ok.format(self.alias, invoice, sats, fee))
        return Ok(None)