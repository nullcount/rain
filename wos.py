import requests # type: ignore
import time
import hmac
import json
import hashlib
from base import TrustedSwapService
from const import COIN_SATS, SAT_MSATS, WOS_API_URL, LOG_INFO, LOG_ERROR, LOG_TRUSTED_SWAP_SERVICE as logs
from config import config
from box import Box
from result import Result, Ok, Err

class Wos(TrustedSwapService):
    def __init__(self, creds_path: str, whoami: str = 'wos') -> None:
        self.session = requests.Session()
        self.creds = self.wos_register(creds_path, whoami)
        self.whoami = whoami
        self.session.headers.update({"api-token": self.creds.api_token_generated})
 
    @staticmethod
    def wos_register(creds_path: str, whoami: str) -> Box:
        creds = config.get_creds(creds_path, whoami)
        if any(key in creds for key in ['api_secret_generated', 'api_token_generated', 'deposit_address_generated']):
            return creds
        ext = "api/v1/wallet/account"
        data = {"referrer": "walletofsatoshi"}
        json = requests.post(WOS_API_URL + ext, json=data).json()
        creds = Box({
            'api_secret_generated': json['apiSecret'],
            'api_token_generated': json['apiToken'],
            'deposit_address_generated': json['btcDepositAddress'],
            'lightning_address_generated': json['lightningAddress'],
            'node_onchain_address': creds.node_onchain_address
        })
        config.set_creds(creds_path, whoami, creds)
        return creds

    def wos_request(self, method: str, ext: str, data_str: str = "", sign: bool = False) -> Box:
        path_url = WOS_API_URL + ext
        if sign and data_str:
            self.sign_session(ext, data_str)
        args = {'url': path_url}
        if data_str and method == "GET":
            args['params'] = json.loads(data_str)
        if data_str and method == "POST":
            args['data'] = data_str.encode("utf-8")
        if method == "GET":
            res = self.session.get(**args)
        else: 
            res = self.session.post(**args)
        self.unsign_session()
        if res.status_code == 200:
            return Box(res.json())
        # TODO general request errors

    def sign_session(self, ext: str, params: str) -> None:
        nonce = str(int(time.time() * 1000))
        api_token = self.creds.api_token_generated
        api_secret = self.creds.api_secret_generated
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
        config.log(LOG_INFO, msg.ok.format(self.whoami, addr))
        return Ok(addr)

    def get_balance(self) -> Result[int, str]:
        msg = logs.get_balance
        """TrustedSwapService"""
        res = self.wos_request("GET", "api/v1/wallet/walletData")
        # TODO: handle errors
        balance = int(res.btc * COIN_SATS)
        config.log(LOG_INFO, msg.ok.format(self.whoami, balance))
        return Ok(balance)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """TrustedSwapService"""
        msg = logs.get_invoice
        user, url = self.creds.lightning_address_generated.split('@')
        res = self.session.get(f"https://{url}/.well-known/lnurlp/{user}").json()
        res2 = self.session.get(f"{res['callback']}?amount={sats * SAT_MSATS}").json()
        # TODO: check errors
        config.log(LOG_INFO, msg.ok.format(self.whoami, res2['pr'], sats))
        return Ok(res2['pr'])

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        """TrustedSwapService"""
        msg = logs.get_onchain_fee
        res = self.wos_request(
            "GET",
            "api/v1/wallet/feeEstimate",
            data_str=json.dumps({
                "address": self.creds.node_onchain_address,
                "amount": sats / COIN_SATS,
            })
        )
        # TODO: handle errors
        fee = int(round(res.btcFixedFee * COIN_SATS))
        config.log(LOG_INFO, msg.ok.format(self.whoami, sats, fee))
        return Ok(fee)

    def send_onchain(self, sats: int, fee: int) -> Result[str, str]:
        """TrustedSwapService"""
        msg = logs.send_onchain
        amt = sats / COIN_SATS
        data_str = '{{"address":"{}","currency":"BTC","amount":{:.7e},"sendMaxLightning":true,"description":null}}'.format(self.creds.node_onchain_address, amt)
        
        # res = self.wos_request(
        #     "POST",
        #     "api/v1/wallet/payment",
        #     data_str,
        #     sign=True
        # )
        print("\n\n\n")
        print(data_str)
        #print(res)
        print("\n\n\n")
        # TODO: handle errors
        config.log(LOG_INFO, msg.ok.format(self.whoami, sats, fee))
        return Ok('')
    
    def pay_invoice(self, invoice: str) -> Result[str, str]:
        """TrustedSwapService"""
        #data_str = '{{"address":"{}","currency":"LIGHTNING","amount":0.0000 1,"sendMaxLightning":true,"description":null}}'.format(invoice, 1000/COIN_SATS)
        data_str = '{"address":"lnbc10u1pj3u23qpp5paav59ldev4qzf0hw20l7vvy7sj4rprlr3mr0dl57z3l3vme9qdsdp8fe5kxetgv9eksgzyv4cx7umfwssyjmnkda5kxegcqzysxqr8pqsp5qq3mapdksuqrmfx4smdpe4duw35e5casd3y8zy7ph7eq5hz7d27q9qyyssqrfedel2cygt4r834j3emgqxhhdatllzfdq0vrc7lwxcqvgf5mknna0dz0ulwm738hzh58hjaejlgpjud3srgdn8rvek0kqv000m3a2cqlt29ps","currency":"LIGHTNING","amount":1.0000000e+03,"sendMaxLightning":true,"description":null}'
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

        #config.log(LOG_ERROR, logs.pay_invoice.err.format(self.whoami, "WOS PAY INVOICE FAILURE - TrustedSwapService.pay_invocie is not implemented"))
        preimage = ""

        return Ok(preimage)
