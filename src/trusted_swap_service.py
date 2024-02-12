"""
trusted_swap_service.py
---
A trusted custodial service that supports send/recieve on both onchain and lightning
usage: as a base class for wallet/exchange API wrappers
"""
from box import Box
from result import Result
from console import console
from const import LOG_GAP

class TrustedSwapService:
    """
    Extend with exchange/wallet APIs 
        to programatically give trusted nodes your sats
        and to automate widthdraws back to your node
    """
    def __init__(self) -> None:
        self.log = console.log
        self.logs = Box({
            "api_request": { # A trusted swap service usually has a dedicated method for making requests
                "ok": LOG_GAP.join(["{}", "api_request", "response_code: {}, url: {}, body: {}, response: {}"]),
                "err": LOG_GAP.join(["{}", "api_request", "response_code: {}, url: {}, body: {}, response: {}"]),
            },
            "get_address": {
                "ok": LOG_GAP.join(["{}", "get_address", "trusted_deposit_address: {}"]),
                "err": LOG_GAP.join(["{}", "get_address", "{}"])
            },
            "send_onchain": {
                "ok": LOG_GAP.join(["{}", "send_onchain", "sats: {}, fee: {}"]),
                "err": LOG_GAP.join(["{}", "send_onchain", "{}"])
            },
            "get_balance": {
                "ok": LOG_GAP.join(["{}", "get_balance", "trusted_balance: {}"]),
                "err": LOG_GAP.join(["{}", "get_balance", "{}"])
            },
            "pay_invoice": {
                "ok": LOG_GAP.join(["{}", "pay_invoice", "invoice: {} sats: {}, fee: {}"]),
                "err": LOG_GAP.join(["{}", "pay_invoice", "{}"])
            },
            "get_invoice": {
                "ok": LOG_GAP.join(["{}", "get_invoice", "invoice: {}, sats: {}"]),
                "err": LOG_GAP.join(["{}", "get_invoice", "{}"])
            }, 
            "get_onchain_fee": {
                "ok": LOG_GAP.join(["{}", "get_onchain_fee", "sats: {}, fee: {}"]),
                "err": LOG_GAP.join(["{}", "get_onchain_fee", "{}"])
            },
        })

    def get_address(self) -> Result[str, str]:
        # returns onchain address string to deposit into the third-party wallet/account balance
        raise NotImplementedError

    def send_onchain(self, sats: int, fee: int) -> Result[None, str]:
        # initiate a widthdrawl request for number of `sats` sent with `fee` sats/vbyte
        # not every api supports user-suggested feerates so `fee` may be unused
        raise NotImplementedError

    def get_balance(self) -> Result[int, str]:
        # returns total wallet/account balance in sats
        raise NotImplementedError

    def get_invoice(self, sats: int) -> Result[str, str]:
        # returns bolt11 invoice string requesting number of `sats`
        raise NotImplementedError

    def get_onchain_fee(self, sats: int) -> Result[int, str]:
        # returns the total fee in satoshis to widthdraw `sats` from balance
        raise NotImplementedError
    
    def pay_invoice(self, sats: int, invoice: str) -> Result[str, str]:
        # returns the total fees to pay the invoice
        raise NotImplementedError
