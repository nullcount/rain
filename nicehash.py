from datetime import datetime
from time import mktime
import uuid
import hmac
import requests
import json
from hashlib import sha256
import sys

COIN_SATS = 100_000_000


class Nicehash:

    def __init__(self, NH_CONFIG, log):
        self.log = log
        self.key = NH_CONFIG['api_key']
        self.secret = NH_CONFIG['api_secret']
        self.organisation_id = NH_CONFIG['org_id']
        self.widthdraw_key = NH_CONFIG['widthdraw_key']
        self.host = "https://api2.nicehash.com"

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
            err_msg = f"Nicehash {response.status_code}: {response.reason}: {response.content}"
        else:
            err_msg = f"Nicehash {response.status_code}: {response.reason}"
        self.log.error(err_msg)
        self.log.notify(err_msg)
        self.log.error('using payload: {}'.format(payload))
        self.log.error('from : {}'.format(endpoint))
        sys.exit()

    def get_onchain_address(self):
        res = self.nicehash_request("GET", '/main/api/v2/accounting/depositAddresses', 'currency=BTC&walletType=BITGO', None)
        return res['list'][0]['address']

    def widthdraw_onchain(self, sats):
        amt = str(float(sats) / COIN_SATS)
        body = {
            "currency": "BTC",
            "amount": amt,
            "withdrawalAddressId": self.widthdraw_key
        }
        res = self.nicehash_request("POST", "/main/api/v2/accounting/withdrawal", '', body)
        self.log.info("nicehash initiated {} sat widthdrawl".format(sats))
        return res

    def get_widthdraw_fee(self, sats):
        res = self.nicehash_request("GET", "/main/api/v2/public/service/fee/info", '', None)
        fee = int(float(res['withdrawal']['BITGO']['rules']['BTC']['intervals'][0]['element']['sndValue']) * COIN_SATS)
        return fee

    def get_pending_widthdraw_sats(self):
        events = self.get_recent_widthdraws()['list']
        pending = 0
        for event in events:
            if event['status']['description'] in ['SUBMITTED', 'ACCEPTED']: # PROCESSING status is considered uncoinfirmed
                pending += float(event['amount'])
        return int(pending * COIN_SATS)

    def get_recent_widthdraws(self):
        res = self.nicehash_request("GET", "/main/api/v2/accounting/withdrawals/BTC", '', None)
        return res

    def get_account_balance(self):
        res = self.nicehash_request("GET", "/main/api/v2/accounting/account2/BTC", '', None)
        balance = int(float(res['available']) * COIN_SATS)
        self.log.info("nicehash account balance: {} sats".format(balance))
        return balance

    def pay_invoice(self, invoice_code):
        # TODO nicehash needs to implement LN widthdrawls
        return

    def get_lightning_invoice(self, sats):
        url = f"/main/api/v2/accounting/depositAddresses?currency=BTC&walletType=LIGHTNING&amount={float(sats) / COIN_SATS}"
        print(url)
        res = self.nicehash_request("GET", url, '', None)
        # TODO nicehash needs to implement LN deposits
        return res

        
