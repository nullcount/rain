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

NICEHASH_API_URL = "https://api2.nicehash.com/"

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

    def nicehash_request(self, method, path, query, body):
        xtime = str(json.loads(requests.get('https://api2.nicehash.com/api/v2/time').text)['serverTime'])
        print(xtime)
        xnonce = str(uuid.uuid4())
        inpt = '{}\00{}\00{}\00\00{}\00\00{}\00{}\00{}'.format(self.creds.api_key, xtime, xnonce, self.creds.org_id, method, path, query)
        sig = hmac.new(self.creds.api_secret.encode(), inpt.encode(), sha256).hexdigest()
        xauth = '{}:{}'.format(self.creds.api_key, sig)
        r = requests.get('{}{}?{}'.format(NICEHASH_API_URL, path, query), headers={'X-Time': xtime, 'X-Nonce': xnonce, 'X-Organization-Id': self.creds.org_id, 'X-Request-Id': xnonce, 'X-Auth': xauth})
        data = json.loads(r.text)
        print(data)


    def nicehash_old_request(self, method: str, path: str, query: str, body: Dict | None) -> Box: # type: ignore
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
            'main/api/v2/accounting/depositAddresses', 
            'currency=BTC&walletType=BITGO', 
            None # no body params
        )
        if res.content:
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
            "main/api/v2/accounting/withdrawal", 
            '', # no url params
            body
        )
        if res.content:
            return Err(self.logs.send_onchain.err.format(self.alias, res))
        self.log(LOG_INFO, self.logs.send_onchain.ok.format(self.alias, sats, fee))
        return Ok(None)

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        """TrustedSwapService"""
        res = self.nicehash_request(
            "GET", 
            "main/api/v2/public/service/fee/info", 
            '', # no url params
            None # no body params
        )
        if res.content:
            return Err(self.logs.get_onchain_fee.err.format(self.alias, res))
        fee = int(float(res.withdrawal.BITGO.rules.BTC.intervals[0].element.sendValue) * COIN_SATS)
        self.log(LOG_INFO, self.logs.get_onchain_fee.ok.format(self.alias, sats, fee))
        return Ok(fee)

    def get_balance(self) -> Result[int, str]:
        """TrustedSwapService"""
        res = self.nicehash_request(
            "GET",
            "main/api/v2/accounting/account2/BTC", 
            '', # no url params 
            None # no body params
        )
        print(res)
        if res.content:
            return Err(self.logs.get_balance.err.format(self.alias, res))
        balance = int(float(res.available) * COIN_SATS)
        self.log(LOG_INFO, self.logs.get_balance.ok(self.alias, balance))
        return Ok(balance)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """TrustedSwapService"""
        res = self.nicehash_request(
            "GET", 
            "main/api/v2/accounting/depositAddresses",
            f'currency=BTC&walletType=LIGHTNING&amount={float(sats) / COIN_SATS}',
            None # no body params
        )
        if res.content:
            return Err(self.logs.get_invoice.err.format(self.alias, res))
        invoice: str = res.list[0].address
        self.log(LOG_INFO, self.logs.get_invoice.ok.format(self.alias, invoice, sats))
        return Ok(invoice)
  