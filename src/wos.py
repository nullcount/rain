"""
wos.py
---
An implementation of WoS API as a TrustedSwapService
usage: add your wos credentials
"""
import requests # type: ignore
import time
import hmac
import json
import hashlib
from trusted_swap_service import TrustedSwapService
from const import COIN_SATS, SAT_MSATS, LOG_INFO
from box import Box
from result import Result, Ok

WOS_API_URL = "https://www.livingroomofsatoshi.com/"

class WosCreds:
    def __init__(self, api_key: str, api_secret: str, onchain_address: str, lightning_address: str, external_onchain_address: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.onchain_address = onchain_address
        self.lightning_address = lightning_address
        self.external_onchain_address = external_onchain_address
    
    def __str__(self) -> str:
        return f"WosCreds(api_key={self.api_key}, api_secret={self.api_secret}, onchain_address={self.onchain_address}, lightning_address={self.lightning_address}, external_onchain_address={self.external_onchain_address})"

class Wos(TrustedSwapService):
    def __init__(self, creds: WosCreds) -> None:
        super().__init__() # init logger from parent class
        self.session = requests.Session()
        self.creds = self.wos_register(creds)
        self.alias = f"WOS-{creds.api_key[:5]}"
        self.session.headers.update({"api-token": self.creds.api_key})
 
    @staticmethod
    def wos_register(creds: WosCreds) -> WosCreds:
        if any(hasattr(creds, key) for key in ['api_secret', 'api_key', 'onchain_address']):
            return creds
        if not creds.external_onchain_address:
            print("Init WoS with an external_onchain_address")
            return creds
        ext = "api/v1/wallet/account"
        data = {"referrer": "walletofsatoshi"}
        json = requests.post(WOS_API_URL + ext, json=data).json()
        return WosCreds(api_key=json['apiSecret'], api_secret=json['apiToken'], onchain_address=json['btcDepositAddress'], lightning_address=json['lightningAddress'], external_onchain_address=creds.external_onchain_address)

    def wos_request(self, method: str, ext: str, data_str: str = "", sign: bool = False) -> Box:
        path_url = WOS_API_URL + ext
        if sign and data_str:
            self.sign_session(ext, data_str)
        args = {'url': path_url}
        if data_str and method == "GET":
            args['params'] = json.loads(data_str)
        if data_str and method == "POST":
            args['data'] = data_str.encode("utf-8") # type: ignore
        if method == "GET":
            res = self.session.get(**args)
        else: 
            res = self.session.post(**args)
        self.unsign_session()
        if res.status_code != 200:
            # TODO general wos errors
            print()
        return Box(res.json())

    def sign_session(self, ext: str, params: str) -> None:
        nonce = str(int(time.time() * 1000))
        api_token = self.creds.api_key
        api_secret = self.creds.api_secret
        m = f"/{ext}{nonce}{api_token}{params}"
        hmac_key = api_secret.encode("utf-8")
        signature = hmac.new(hmac_key, m.encode("utf-8"),
                             digestmod=hashlib.sha256).hexdigest()
        self.session.headers.update({
            'signature': signature,
            'nonce': nonce,
            'api-token': api_token,
        })

    def unsign_session(self) -> None:
        self.session.headers.pop("signature", None)
        self.session.headers.pop("nonce", None)

    def get_address(self) -> Result[str, str]:
        """TrustedSwapService"""
        addr = str(self.creds.onchain_address)
        self.log(LOG_INFO, self.logs.get_address.ok.format(self.alias, addr))
        return Ok(addr)

    def get_balance(self) -> Result[int, str]:
        """TrustedSwapService"""
        res = self.wos_request("GET", "api/v1/wallet/walletData")
        # TODO: handle errors
        balance = int(res.btc * COIN_SATS)
        self.log(LOG_INFO, self.logs.get_balance.ok.format(self.alias, balance))
        return Ok(balance)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """TrustedSwapService"""
        user, url = self.creds.lightning_address.split('@')
        res = self.session.get(f"https://{url}/.well-known/lnurlp/{user}").json()
        res2 = self.session.get(f"{res['callback']}?amount={sats * SAT_MSATS}").json()
        # TODO: check errors
        self.log(LOG_INFO, self.logs.get_invoice.ok.format(self.alias, res2['pr'], sats))
        return Ok(res2['pr'])

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        """TrustedSwapService"""
        res = self.wos_request(
            "GET",
            "api/v1/wallet/feeEstimate",
            data_str=json.dumps({
                "address": self.creds.external_onchain_address,
                "amount": sats / COIN_SATS,
            })
        )
        # TODO: handle errors
        fee = int(round(res.btcFixedFee * COIN_SATS))
        self.log(LOG_INFO, self.logs.get_onchain_fee.ok.format(self.alias, sats, fee))
        return Ok(fee)

    def send_onchain(self, sats: int, fee: int) -> Result[None, str]:
        """TrustedSwapService"""
        amt = sats / COIN_SATS
        data_str = '{{"address":"{}","currency":"BTC","amount":{:.7e},"sendMaxLightning":false,"description":null}}'.format(self.creds.external_onchain_address, amt)
        
        res = self.wos_request(
            "POST",
            "api/v1/wallet/payment",
            data_str,
            sign=True
        )
        print("\n\n\n")
        print(data_str)
        print(res)
        print("\n\n\n")
        # TODO: handle errors
        self.log(LOG_INFO, self.logs.send_onchain.ok.format(self.alias, sats, fee))
        return Ok(None)
    
    def pay_invoice(self, invoice: str) -> Result[str, str]:
        """TrustedSwapService"""
        data_str = '{{"address":"{}","currency":"LIGHTNING","amount":{:.7e},"sendMaxLightning":false,"description":null}}'.format(invoice, 1000/COIN_SATS)
        res = self.wos_request(
            "POST",
            "api/v1/wallet/payment",
            data_str,
            sign=True
        )
        print("\n\n\n")
        print(data_str)
        print(res)
        print("\n\n\n")

        #config.log(LOG_ERROR, logs.pay_invoice.err.format(self.alias, "WOS PAY INVOICE FAILURE - TrustedSwapService.pay_invocie is not implemented"))
        preimage = ""

        return Ok(preimage)
