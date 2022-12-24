from datetime import datetime
from time import mktime
import uuid
import hmac
import requests
import json
from hashlib import sha256
import sys

COIN_SATS = 100_000_000
MAX_LN_DEPOSIT = 15_000_000
MIN_LN_DEPOSIT = 1_001


class Nicehash:
    def __init__(self, NH_CONFIG, log):
        self.log = log
        self.key = NH_CONFIG['api_key']
        self.secret = NH_CONFIG['api_secret']
        self.organisation_id = NH_CONFIG['org_id']
        self.funding_key = NH_CONFIG['funding_key']
        self.host = "https://api2.nicehash.com"
        self.log_msg_map = {
            "get_onchain_address": lambda addr: f"nicehash deposit address: {addr}",
            "send_onchain": lambda sats: f"nicehash initiated {sats} sat widthdrawl",
            "get_onchain_fee": lambda fee, sats: f"nicehash fee: {fee} sats widthdraw amount: {sats} sats",
            "get_pending_send_sats": lambda amt : f"nicehash widthdraw of {amt} sats",
            "get_account_balance": lambda sats: f"nicehash account balance: {sats} sats",
            "send_to_acct": lambda sats: f"sending {int(sats)} sats into nicehash account",
            "get_lightning_invoice": lambda sats, invoice: f"nicehash requests {sats} sats invoice: {invoice}"
        }

    def nicehash_request(self, method, path, query, body):
        xtime = self.get_epoch_ms_from_now()
        xnonce = str(uuid.uuid4())
        message = bytearray(self.key, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(str(xtime), 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(xnonce, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(self.organisation_id, 'utf-8')
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

        digest = hmac.new(bytearray(self.secret, 'utf-8'), message, sha256).hexdigest()
        xauth = self.key + ":" + digest
        headers = {
            'X-Time': str(xtime),
            'X-Nonce': xnonce,
            'X-Auth': xauth,
            'Content-Type': 'application/json',
            'X-Organization-Id': self.organisation_id,
            'X-Request-Id': str(uuid.uuid4())
        }
        s = requests.Session()
        s.headers = headers
        url = self.host + path
        if query:
            url += '?' + query
        if body:
            response = s.request(method, url, data=body_json)
        else:
            response = s.request(method, url)
        if response.status_code == 200:
            return response.json()
        else:
            self.check_errors(response, body, url)

    def get_epoch_ms_from_now(self):
        now = datetime.now()
        now_ec_since_epoch = mktime(now.timetuple()) + now.microsecond / 1000000.0
        return int(now_ec_since_epoch * 1000)

    def check_errors(self, response, payload, endpoint):
        if response.content:
            err_msg = f"Nicehash {response.status_code} {endpoint}: {response.reason}: {response.content}"
        else:
            err_msg = f"Nicehash {response.status_code} {endpoint}: {response.reason}"
        self.log.error(err_msg)
        self.log.notify(err_msg)
        sys.exit()

    def get_onchain_address(self):
        res = self.nicehash_request("GET", '/main/api/v2/accounting/depositAddresses', 'currency=BTC&walletType=BITGO', None)
        return res['list'][0]['address']

    def send_onchain(self, sats, fee):
        amt = str(float(sats) / COIN_SATS)
        body = {
            "currency": "BTC",
            "amount": amt,
            "withdrawalAddressId": self.funding_key
        }
        res = self.nicehash_request("POST", "/main/api/v2/accounting/withdrawal", '', body)
        self.log.info(self.log_msg_map['send_onchain'](sats))
        return res

    def get_onchain_fee(self, sats):
        res = self.nicehash_request("GET", "/main/api/v2/public/service/fee/info", '', None)
        fee = int(float(res['withdrawal']['BITGO']['rules']['BTC']['intervals'][0]['element']['sndValue']) * COIN_SATS)
        self.log.info(self.log_msg_map['get_onchain_fee'](sats, fee))
        return fee

    def get_pending_send_sats(self):
        events = self.get_recent_sends()['list']
        pending = 0
        for event in events:
            if event['status']['description'] in ['SUBMITTED', 'ACCEPTED']:  # PROCESSING status is considered uncoinfirmed
                pending += float(event['amount'])
        self.log.info(self.log_msg_map['get_pending_send_sats'](pending * COIN_SATS))
        return int(pending * COIN_SATS)

    def get_recent_sends(self):
        res = self.nicehash_request("GET", "/main/api/v2/accounting/withdrawals/BTC", '', None)
        return res

    def get_account_balance(self):
        res = self.nicehash_request("GET", "/main/api/v2/accounting/account2/BTC", '', None)
        balance = int(float(res['available']) * COIN_SATS)
        self.log.info(self.log_msg_map['get_account_balance'](balance))
        return balance

    def pay_invoice(self, invoice_code):
        # TODO nicehash needs to implement paying invoices
        return

    def send_to_acct(self, sats, node):
        # generate multiple invoices if needed
        invs = []
        self.log.info(self.log_msg_map['send_to_acct'](sats))
        while sats > MAX_LN_DEPOSIT:
            invs.append(self.get_lightning_invoice(MAX_LN_DEPOSIT))
            sats = sats - MAX_LN_DEPOSIT
        if (sats > MIN_LN_DEPOSIT):
            invs.append(self.get_lightning_invoice(sats))
        for inv in invs:
            node.pay_invoice(inv)

    def get_lightning_invoice(self, sats):
        res = self.nicehash_request("GET", "/main/api/v2/accounting/depositAddresses", f'currency=BTC&walletType=LIGHTNING&amount={float(sats) / COIN_SATS}', None)
        invoice = res['list'][0]['address']
        self.log.info(self.log_msg_map['get_lightning_invoice'](sats, invoice))
        return invoice
