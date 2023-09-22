from result import Result
from typing import Callable
from box import Box

class AdminNotifyService:
    """
    Extend with chat protocol APIs
        to notify node operator (admin) of events
        and ask for approval/confirmation of actions
    """
    def send_message(self, message: str) -> Result[None, str]:
        raise NotImplementedError
    
    def await_confirm(self, prompt: str, callback: Callable) -> Result[None, str]:
        raise NotImplementedError
    

class BitcoinLightingNode:
    """
    Extend with gRPC or API calls to a node
    """
    def open_channel(self) -> Result[None, str]:
        raise NotImplementedError
    
    def close_channel(self) -> Result[None, str]:
        raise NotImplementedError
    
    def get_pending_channels(self) -> Result[Box, str]:
        raise NotImplementedError
    
    def get_opened_channels(self) -> Result[Box, str]:
        raise NotImplementedError
    
    def get_invoice(self, sats: int) -> Result[str, str]:
        raise NotImplementedError
    
    def pay_invoice(self) -> Result[None, str]:
        raise NotImplementedError
    
    def get_address(self) -> Result[str, str]:
        raise NotImplementedError
    
    def send_onchain(self) -> Result[None, str]:
        raise NotImplementedError
    
    def get_unconfirmed_balance(self) -> Result[int, str]:
        raise NotImplementedError

    def get_confirmed_balance(self) -> Result[int, str]:
        raise NotImplementedError
    
    def decode_invoice(self, invoice: str) -> Result[Box, str]:
        raise NotImplementedError
    
    def sign_message(self, message: str) -> Result[str, str]:
        raise NotImplementedError
    
    def get_alias(self, pubkey: str) -> Result[str, str]:
        raise NotImplementedError
    

class TrustedSwapService:
    """
    Extend with exchange/wallet APIs 
        to programatically give trusted nodes your sats
        and to automate widthdraws back to your node
    """
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
