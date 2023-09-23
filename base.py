from result import Result
from typing import Callable, List
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

class OpenChannelRequest:
    """
    Used in BitcoinLightningNode.open_channel() 
    """
    def __init__(
            self, 
            peer_pubkey: str, 
            channel_capacity: int, 
            base_fee: int,
            ppm_fee: int,
            cltv_delta: int,
            min_htlc_sats: int,
            vbyte_sats: int,
            is_spend_unconfirmed: bool,
            is_unannounced: bool,
        ) -> None:
        self.peer_pubkey = peer_pubkey
        self.channel_capacity = channel_capacity
        self.base_fee = base_fee
        self.ppm_fee = ppm_fee
        self.cltv_delta = cltv_delta
        self.min_htlc_sats = min_htlc_sats
        self.vbyte_sats = vbyte_sats
        self.is_spend_unconfirmed = is_spend_unconfirmed
        self.is_unannounced = is_unannounced

class CloseChannelRequest:
    """
    Used in BitcoinLightningNode.close_channel() 
    """
    def __init__(
            self, 
            channel_point: str, 
            vbyte_sats: int,
            is_force: bool,
        ) -> None:
        self.channel_point = channel_point
        self.vbyte_sats = vbyte_sats
        self.is_force = is_force

class PayInvoiceRequest:
    """
    Used in BitcoinLightningNode.pay_invoice() 
    """
    def __init__(
            self,
            outgoing_channel_id: str,
            invoice: str,
            fee_limit_sats: int
    ) -> None:
        self.outgoing_channel_id = outgoing_channel_id
        self.invoice = invoice
        self.fee_limit_sats = fee_limit_sats

class PendingOpenChannel:
    """
    Used in BitcoinLightningNode.get_pending_open_channels() 
    """
    def __init__(
            self,
            peer_pubkey: str,
            channel_point: str,
            capacity: int,
            local_balance: int,
            initiator: str,
            private: bool,
    ) -> None:
        self.peer_pubkey = peer_pubkey
        self.channel_point = channel_point
        self.capacity = capacity
        self.local_balance = local_balance
        self.initiator = initiator
        self.private = private

class ActiveOpenChannel:
    """
    Used in BitcoinLightningNode.get_open_channels() 
    """
    def __init__(
            self,
            active: bool,
            channel_id: str,
            peer_pubkey: str,
            channel_point: str,
            capacity: int,
            local_balance: int,
            initiator: str,
            private: bool,
    ) -> None:
        self.active = active
        self.channel_id = channel_id
        self.peer_pubkey = peer_pubkey
        self.channel_point = channel_point
        self.capacity = capacity
        self.local_balance = local_balance
        self.initiator = initiator
        self.private = private

class DecodedInvoice:
    """
    Used in BitcoinLightningNode.decode_invoice() 
    """
    def __init__(
        self,
        dest_pubkey: str,
        payment_hash: str,
        amount_sats: int,
        description: str,
    ) -> None:
        self.dest_pubkey = dest_pubkey
        self.payment_hash = payment_hash
        self.amount_sats = amount_sats
        self.description = description    

class BitcoinLightingNode:
    """
    Extend with gRPC or API calls to a node
    """
    def open_channel(self, req: OpenChannelRequest) -> Result[None, str]:
        raise NotImplementedError
    
    def close_channel(self, req: CloseChannelRequest) -> Result[None, str]:
        raise NotImplementedError
    
    def get_pending_open_channels(self) -> Result[List[PendingOpenChannel], str]:
        raise NotImplementedError
    
    def get_opened_channels(self) -> Result[List[ActiveOpenChannel], str]:
        raise NotImplementedError
    
    def get_invoice(self, sats: int) -> Result[str, str]:
        raise NotImplementedError
    
    def pay_invoice(self, req: PayInvoiceRequest) -> Result[None, str]:
        raise NotImplementedError
    
    def get_address(self) -> Result[str, str]:
        raise NotImplementedError
    
    def send_onchain(self) -> Result[None, str]:
        raise NotImplementedError
    
    def get_unconfirmed_balance(self) -> Result[int, str]:
        raise NotImplementedError

    def get_confirmed_balance(self) -> Result[int, str]:
        raise NotImplementedError
    
    def decode_invoice(self, invoice: str) -> Result[DecodedInvoice, str]:
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
