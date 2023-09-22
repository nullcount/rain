import requests
import time
import hmac
import hashlib
from base import TrustedSwapService
from const import COIN_SATS, WOS_API_URL, LOG_INFO, LOG_TRUSTED_SWAP_SERVICE as logs
import config
from typing import Any
from box import Box
from result import Result, Ok, Err

class Wos(TrustedSwapService):
    def __init__(self) -> None:
        self.session = requests.Session()
        self.creds = self.wos_register()
        self.onchain_fee = 0
        self.session.headers.update({"api-token": self.creds.api_token})
    
    def wos_register(self) -> Box:
        creds: Box = config.get_creds('wos')
        if not creds.api_secret == "YOUR_WOS_API_SECRET":
            return creds
        ext = "api/v1/wallet/account"
        data = {"referrer": "walletofsatoshi"}
        json = requests.post(WOS_API_URL + ext, json=data).json()
        creds = Box({
            'api_secret_generated': json['apiSecret'],
            'api_token_generated': json['apiToken'],
            'deposit_address_generated': json['btcDepositAddress'],
            'lightning_address_generated': json['lightningAddress'],
            'lnd_node_onchain_address': creds.lnd_node_onchain_address
        })
        config.set_creds('wos', creds)
        return creds

    def wos_request(self, ext: str, data_str: str, sign: bool) -> Box:
        path_url = WOS_API_URL + ext
        if sign and data_str:
            self.sign_session(ext, data_str)
        resp_json: dict[Any, Any] = self.session.post(
            path_url, data=data_str.encode("utf-8")).json()
        self.unsign_session()
        return Box(resp_json)

    def sign_session(self, ext: str, params: str) -> None:
        nonce = str(int(time.time() * 1000))
        api_token = self.creds.api_token
        api_secret = self.creds.api_secret
        m = ext + nonce + api_token + params
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
        msg = logs.get_address
        addr = str(self.creds.deposit_address_generated)
        # TODO: handle errors
        config.log(LOG_INFO, msg.ok.format('wos', addr))
        return Ok(addr)

    def get_balance(self) -> Result[int, str]:
        msg = logs.get_balance
        """TrustedSwapService"""
        ext = "api/v1/wallet/walletData"
        res = self.session.get(WOS_API_URL + ext)
                # TODO: handle errors
        balance = int(res.btc * COIN_SATS)
        config.log(LOG_INFO, msg.ok.format('wos', balance))
        return Ok(balance)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """TrustedSwapService"""
        msg = logs.get_invoice
        ext = "api/v1/wallet/createInvoice"
        data_str = '{{"amount":{:.7e},"description":"Wallet of Satoshi"}}'.format(
            sats / COIN_SATS)
        res = self.wos_request(ext, data_str, sign=True)
                # TODO: handle errors
        invoice: str = res.invoice
        config.log(LOG_INFO, msg.ok.format('wos', invoice, sats))
        return Ok(invoice)

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        """TrustedSwapService"""
        msg = logs.get_onchain_fee
        ext = "api/v1/wallet/feeEstimate"
        fee = self.session.get(
            WOS_API_URL + ext, 
            params={
                "address": self.creds.lnd_node_onchain_address,
                "amount": sats
            }
        ).json()['btcFixedFee']
                # TODO: handle errors
        fee = int(round(fee * COIN_SATS))
        self.onchain_fee = fee
        config.log(LOG_INFO, msg.ok.format('wos', sats, fee))
        return Ok(fee)

    def send_onchain(self, sats: int, fee: int) -> Result[None, str]:
        """TrustedSwapService"""
        msg = logs.send_onchain
        if not self.onchain_fee:
            self.estimate_onchain_fee(sats)
        amt = (sats - self.onchain_fee) / COIN_SATS
        ext = "api/v1/wallet/payment"
        data_str = '{{"address":"{}","currency":"BTC","amount":{:.7e},"sendMaxLightning":true,"description":null}}'.format(
            self.creds.lnd_node_onchain_address, amt)
        res: dict[Any, Any] = self.wos_request(ext, str(data_str), sign=True)
               # TODO: handle errors
        config.log(LOG_INFO, msg.ok.format('wos', sats, fee))
        return Ok(None)
