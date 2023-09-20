import requests
import time
import hmac
import hashlib
from base import TrustedSwapService
from const import COIN_SATS, WOS_API_URL, LOG_INFO, LOG_TRUSTED_SWAP_SERVICE as logs
from config import get_creds, set_creds, log
from typing import Any
from box import Box

class Wos(TrustedSwapService):
    def __init__(self) -> None:
        self.session = requests.Session()
        self.creds = self.wos_register()
        self.onchain_fee = 0
        self.session.headers.update({"api-token": self.creds.api_token})
    
    def wos_register(self) -> Box:
        creds: Box = get_creds('wos')
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
        set_creds('wos', creds)
        return creds

    def wos_request(self, ext: str, data_str: str, sign: bool) -> dict[Any, Any]:
        path_url = WOS_API_URL + ext
        if sign and data_str:
            self.sign_session(ext, data_str)
        resp_json: dict[Any, Any] = self.session.post(
            path_url, data=data_str.encode("utf-8")).json()
        self.unsign_session()
        #TODO handle errors with log(LOG_ERROR, msg)
        return resp_json

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

    def get_address(self) -> str:
        """TrustedSwapService"""
        addr = str(self.creds.deposit_address_generated)
        log(LOG_INFO, logs.get_address('wos', addr))
        return addr

    def get_balance(self) -> int:
        """TrustedSwapService"""
        ext = "api/v1/wallet/walletData"
        json = self.session.get(WOS_API_URL + ext).json()
        balance = int(json['btc'] * COIN_SATS)
        log(LOG_INFO, logs.get_balance('wos', balance))
        return balance

    def pay_invoice(self, invoice: str, sats: int) -> dict[Any, Any]:
        """TrustedSwapService"""
        ext = "api/v1/wallet/payment"
        data_str = '{"address":"%s","currency":"LIGHTNING","amount":%d,"sendMaxLightning":true,"description":""}' % invoice, float(
            sats / COIN_SATS)
        resp_json: dict[Any, Any] = self.wos_request(ext, str(data_str), sign=True)
        log(LOG_INFO, logs.pay_invoice('wos', invoice, sats))
        return resp_json

    def get_invoice(self, sats: int) -> str:
        """TrustedSwapService"""
        ext = "api/v1/wallet/createInvoice"
        data_str = '{{"amount":{:.7e},"description":"Wallet of Satoshi"}}'.format(
            sats / COIN_SATS)
        resp_json = self.wos_request(ext, data_str, sign=True)
        invoice: str = resp_json["invoice"]
        log(LOG_INFO, logs.get_invoice('wos', invoice, sats))
        return invoice

    def get_onchain_fee(self, sats: int) -> int:
        """TrustedSwapService"""
        ext = "api/v1/wallet/feeEstimate"
        params: dict[str, Any] = {
            "address": self.creds.lnd_node_onchain_address,
            "amount": sats
        }
        fee = self.session.get(
            WOS_API_URL + ext, params=params).json()['btcFixedFee']
        fee = round(fee * COIN_SATS)
        self.onchain_fee = fee
        log(LOG_INFO, logs.get_onchain_fee('wos', sats, fee))
        return int(fee)

    def send_onchain(self, sats: int, fee: int) -> dict[Any, Any]:
        """TrustedSwapService"""
        if not self.onchain_fee:
            self.estimate_onchain_fee(sats)
        print((sats - self.onchain_fee) / COIN_SATS)
        amt = (sats - self.onchain_fee) / COIN_SATS
        ext = "api/v1/wallet/payment"
        data_str = '{{"address":"{}","currency":"BTC","amount":{:.7e},"sendMaxLightning":true,"description":null}}'.format(
            self.creds.loop_out_address, amt)
        resp_json: dict[Any, Any] = self.wos_request(ext, str(data_str), sign=True)
        log(LOG_INFO, logs.send_onchain('wos', sats, fee))
        return resp_json
