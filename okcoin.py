import hmac
import base64
import requests
import json
from swap import SwapMethod
from creds import OkCreds

COIN_SATS = 100_000_000

API_URL = 'https://www.okcoin.com'
SERVER_TIMESTAMP_URL = '/api/general/v3/time'
WALLET_INFO = '/api/account/v3/wallet'
DEPOSIT_LI = '/api/account/v3/deposit-lightning'
WITHDRAWAL_LI = '/api/account/v3/withdrawal-lightning'
COIN_FEE = '/api/account/v3/withdrawal/fee'
TOP_UP_ADDRESS = '/api/account/v3/deposit/address'
COIN_WITHDRAW = '/api/account/v3/withdrawal'


class Okcoin(SwapMethod):

    def __init__(self, creds: OkCreds, log):
        self.log = log
        self.API_KEY = creds.api_token
        self.API_SECRET_KEY = creds.api_secret
        self.PASSPHRASE = creds.api_passphrase
        self.ADDRESS = creds.loop_out_address

    @staticmethod
    def sign(message, secret_key):
        mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(
            message, encoding='utf-8'), digestmod='sha256')
        d = mac.digest()
        return base64.b64encode(d)

    @staticmethod
    def pre_hash(timestamp, method, request_path, body):
        return str(timestamp) + str.upper(method) + request_path + body

    @staticmethod
    def get_header(api_key, sign, timestamp, passphrase):
        header = dict()
        header["Content-Type"] = "application/json"
        header["OK-ACCESS-KEY"] = api_key
        header["OK-ACCESS-SIGN"] = sign
        header["OK-ACCESS-TIMESTAMP"] = str(timestamp)
        header["OK-ACCESS-PASSPHRASE"] = passphrase

        return header

    @staticmethod
    def parse_params_to_str(params):
        url = '?'
        for key, value in params.items():
            url = url + str(key) + '=' + str(value) + '&'

        return url[0:-1]

    def _request(self, method, request_path, params):
        if method == "GET":
            request_path = request_path + self.parse_params_to_str(params)
        url = API_URL + request_path
        timestamp = self._get_timestamp()

        body = json.dumps(params) if method == "POST" else ""
        sign = self.sign(self.pre_hash(timestamp, method,
                         request_path, str(body)), self.API_SECRET_KEY)
        header = self.get_header(
            self.API_KEY, sign, timestamp, self.PASSPHRASE)
        response = None
        if method == "GET":
            response = requests.get(url, headers=header)
        elif method == "POST":
            response = requests.post(url, data=body, headers=header)
        elif method == "DELETE":
            response = requests.delete(url, headers=header)

        return response

    def _request_without_params(self, method, request_path):
        return self._request(method, request_path, {})

    def _request_with_params(self, method, request_path, params, cursor=False):
        return self._request(method, request_path, params, cursor)

    def _get_timestamp(self):
        url = API_URL + SERVER_TIMESTAMP_URL
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['iso']
        else:
            return ""

    def get_onchain_address(self):
        params = {'currency': 'BTC'}
        response = self._request_with_params('GET', TOP_UP_ADDRESS, params)
        return response

    def send_onchain(self, sats: int, fee: int):
        params = {'currency': "BTC", 'amount': sats / COIN_SATS,
                  'destination': self.ADDRESS, 'to_address': self.ADDRESS, 'fee': fee}
        response = self._request_with_params('POST', COIN_WITHDRAW, params)
        return response

    def get_account_balance(self):
        response = self._request_without_params('GET', WALLET_INFO)
        return response

    def pay_invoice(self, inv: str):
        params = {'currency': 'BTC', 'invoice': inv, 'memo': 'okcoin'}
        response = self._request_with_params('POST', WITHDRAWAL_LI, params)
        return response

    def get_lightning_invoice(self, amount: int):
        params = {'ccy': 'mnn', 'amount': amount, 'to': 'me'}
        response = self._request_with_params('GET', DEPOSIT_LI, params)
        return response

    def estimate_onchain_fee(self):
        params = {'currency': 'BTC'}
        response = self._request_with_params("GET", COIN_FEE, params)
        return response
