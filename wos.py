import requests
from os.path import join
import sqlite3
import time
import base64
import hmac
import hashlib
import json
import urllib.parse as urlparse
from urllib.parse import urlencode


class Wos:
    def __init__(self, WOS_CRED, log):
        self.session = requests.Session()
        self.base_url = "https://www.livingroomofsatoshi.com"
        self.conn = None
        self.init_db()
        self.wallet = None
        self.load_wallet()
        if not self.wallet:
            self.create_account()
        print(self.get_account_balance())

    def wos_request(self, ext, data_str: str, sign: bool):
        path_url = self.base_url + ext
        if sign and data_str:
            self.sign_session(ext, data_str)
        resp_json = self.session.post(path_url, data=data_str.encode("utf-8")).json()
        self.unsign_session()
        return resp_json

    def load_wallet(self):
        cur = self.conn.cursor()
        cur.execute("SELECT apiSecret,apiToken,lightningAddress,btcDepositAddress FROM wallet")
        rows = cur.fetchall()
        if rows:
            self.wallet = dict(zip(["apiSecret", "apiToken", "lightningAddress", "btcDepositAddress"], rows[0]))
            self.session.headers.update({"api-token": self.wallet["apiToken"]})

    def init_db(self):
        db_file = "wos.db"
        self.conn = sqlite3.connect(db_file)
        sql_create_wallet_table = """CREATE TABLE IF NOT EXISTS wallet (
                                        apiToken text PRIMARY KEY,
                                        apiSecret text,
                                        btcDepositAddress text,
                                        lightningAddress text
                                    );"""
        c = self.conn.cursor()
        c.execute(sql_create_wallet_table)

    def sign_session(self, ext, params):
        nonce = str(int(time.time() * 1000))
        api_token = self.wallet["apiToken"]
        api_secret = self.wallet["apiSecret"]

        m = ext + nonce + api_token + params
        hmac_key = api_secret.encode("utf-8")
        signature = hmac.new(hmac_key, m.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

        self.session.headers.update({
            'signature': signature,
            'nonce': nonce,
            'api-token': api_token,
        })

    def unsign_session(self):
        self.session.headers.pop("signature", None)
        self.session.headers.pop("nonce", None)

    def insert_update_auth_data(self, json):
        api_secret = json["apiSecret"]
        api_token = json["apiToken"]
        lightning_address = json["lightningAddress"]
        bitcoin_address = json["btcDepositAddress"]
        sql = ''' INSERT OR REPLACE INTO wallet (apiSecret,apiToken,btcDepositAddress,lightningAddress)
                  VALUES(?,?,?,?) '''
        cur = self.conn.cursor()
        cur.execute(sql, (api_secret, api_token, bitcoin_address, lightning_address))
        self.conn.commit()

    def create_account(self):
        ext = "/api/v1/wallet/account"
        data = {
            "referrer": "walletofsatoshi"
        }
        json = self.session.post(self.base_url + ext, json=data).json()
        self.insert_update_auth_data(json)
        self.load_wallet()
        self.session.headers.update({"api-token": self.wallet["apiToken"]})

    def get_onchain_address(self):
        return self.wallet["btcDepositAddress"]

    def get_account_balance(self):
        ext = "/api/v1/wallet/walletData"
        json = self.session.get(self.base_url + ext).json()
        _sum = sum(map(float, [json[kwarg] for kwarg in ["btc", "lightning", "btcUnconfirmed"]]))
        return json["btc"], json["lightning"], json["btcUnconfirmed"]

    def pay_invoice(self, invoice: str, amount_btc: float):
        ext = "/api/v1/wallet/payment"
        data_str = '{"address":"%s","currency":"LIGHTNING","amount":%d,"sendMaxLightning":true,"description":""}' % invoice, amount_btc
        resp_json = self.wos_request(ext, str(data_str), sign=True)
        status = resp_json["status"]
        tx_id = resp_json["transactionId"]
        return status == "PAID", tx_id

    def get_lightning_invoice(self, sats):
        ext = "/api/v1/wallet/createInvoice"
        data_str = '{"amount":%d,"description":"Wallet of Satoshi"}' % sats
        resp_json = self.wos_request(ext, data_str, sign=True)
        invoice = resp_json["invoice"]
        return invoice

    def estimate_onchain_fee(self):
        ext = "/api/v1/wallet/feeEstimate"
        params = {
            "address": "34c5izdES7Wt4x38SEfnUCVtoNj6F2wPPe",
            "amount": 0
        }
        resp_json = self.session.get(self.base_url + ext, params=params).json()
        return resp_json["btcFixedFee"]

    def send_onchain(self, address: str, amount_btc: float):
        ext = "/api/v1/wallet/payment"
        data_str = '{"address":"%s","currency":"BTC","amount":%d,"sendMaxLightning":true,"description":null}' % address, amount_btc
        resp_json = self.wos_request(ext, str(data_str), sign=True)
        status = resp_json["status"]
        tx_id = resp_json["transactionId"]
        return status == "PAID", tx_id
