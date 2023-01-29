import requests
import time
import hmac
import hashlib
from swap import SwapMethod
from creds import WosCreds

BASE_URL = "https://www.livingroomofsatoshi.com"
COIN_SATS = 100_000_000


def create_wos_account():
    ext = "/api/v1/wallet/account"
    data = {
        "referrer": "walletofsatoshi"
    }
    json = requests.post(BASE_URL + ext, json=data).json()
    print("[WOS]")
    print("\n".join([f"api_secret = {json['apiSecret']}", f"api_token = {json['apiToken']}",
          f"btc_deposit_address = {json['btcDepositAddress']}", f"lightning_address = {json['lightningAddress']}", f"loop_out_address = <put your address to recieve from WoS here>"]))


class Wos(SwapMethod):
    def __init__(self, creds: WosCreds, log):
        self.log = log
        self.session = requests.Session()
        self.creds = creds
        self.onchain_fee = None
        self.session.headers.update({"api-token": self.creds.api_token})
        self.log_msg_map = {
            "get_onchain_address": lambda addr: f"WoS deposit address: {addr}",
            "send_onchain": lambda sats, txid: f"WoS initiated {sats} sat widthdrawl txid: {txid}",
            "get_onchain_fee": lambda fee, sats: f"WoS fee: {fee} sats widthdraw amount: {sats} sats",
            "get_account_balance": lambda sats: f"WoS account balance: {sats} sats",
            "get_lightning_invoice": lambda sats, invoice: f"WoS requests {sats} sats invoice: {invoice}"
        }

    def wos_request(self, ext, data_str: str, sign: bool):
        path_url = BASE_URL + ext
        if sign and data_str:
            self.sign_session(ext, data_str)
        resp_json = self.session.post(
            path_url, data=data_str.encode("utf-8")).json()
        self.unsign_session()
        return resp_json

    def sign_session(self, ext, params):
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

    def unsign_session(self):
        self.session.headers.pop("signature", None)
        self.session.headers.pop("nonce", None)

    def get_onchain_address(self):
        return self.creds.btc_deposit_address

    def get_account_balance(self):
        ext = "/api/v1/wallet/walletData"
        json = self.session.get(BASE_URL + ext).json()
        balance = int(json['btc'] * COIN_SATS)
        self.log.info(self.log_msg_map['get_account_balance'](balance))
        return balance

    def pay_invoice(self, invoice: str, amount: int):
        ext = "/api/v1/wallet/payment"
        data_str = '{"address":"%s","currency":"LIGHTNING","amount":%d,"sendMaxLightning":true,"description":""}' % invoice, float(
            amount / COIN_SATS)
        resp_json = self.wos_request(ext, str(data_str), sign=True)
        status = resp_json["status"]
        tx_id = resp_json["transactionId"]
        return status == "PAID", tx_id

    def get_lightning_invoice(self, sats: int):
        ext = "/api/v1/wallet/createInvoice"
        data_str = '{{"amount":{:.8e},"description":"Wallet of Satoshi"}}'.format(
            sats / COIN_SATS)
        resp_json = self.wos_request(ext, data_str, sign=True)
        invoice = resp_json["invoice"]
        self.log.info(self.log_msg_map['get_lightning_invoice'](sats, invoice))
        return invoice

    def estimate_onchain_fee(self, amount: int):
        ext = "/api/v1/wallet/feeEstimate"
        params = {
            "address": self.creds.loop_out_address,
            "amount": amount
        }
        fee = self.session.get(
            BASE_URL + ext, params=params).json()['btcFixedFee']
        self.onchain_fee = fee
        self.log.info(self.log_msg_map['get_onchain_fee'](fee, amount))
        return int(fee * COIN_SATS)

    def send_onchain(self, sats: int, _: int):
        if not self.onchain_fee:
            self.estimate_onchain_fee(sats)
        amt = (sats / COIN_SATS) - self.onchain_fee
        ext = "/api/v1/wallet/payment"
        data_str = '{{"address":"{}","currency":"BTC","amount":{:e},"sendMaxLightning":true,"description":null}}'.format(
            self.creds.loop_out_address, amt)
        resp_json = self.wos_request(ext, str(data_str), sign=True)
        status = resp_json["status"]
        tx_id = resp_json["transactionId"]
        self.log.info(self.log_msg_map['send_onchain'](amt, tx_id))
        return status == "PAID", tx_id
