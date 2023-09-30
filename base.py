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

class SendOnchainRequest:
    """
    Used in BitcoinLightningNode.send_onchain()
    """
    def __init__(
            self,
            dest_addr: str,
            amount_sats: int,
            vbyte_sats: int
    ) -> None:
        self.dest_addr = dest_addr
        self.amount_sats = amount_sats
        self.vbyte_sats = vbyte_sats
    
    def __str__(self) -> str:
        return f"SendOnchainRequest(dest_addr={self.dest_addr}, amount_sats={self.amount_sats}, vbyte_sats={self.vbyte_sats})"

class OpenChannelRequest:
    """
    Used in BitcoinLightningNode.open_channel() 
    """
    def __init__(
            self, 
            peer_pubkey: str, 
            peer_host: str,
            capacity: int, 
            base_fee: int,
            ppm_fee: int,
            cltv_delta: int,
            min_htlc_sats: int,
            vbyte_sats: int,
            is_spend_unconfirmed: bool = True,
            is_unannounced: bool = False,
        ) -> None:
        self.peer_pubkey = peer_pubkey
        self.peer_host = peer_host
        self.capacity = capacity
        self.base_fee = base_fee
        self.ppm_fee = ppm_fee
        self.cltv_delta = cltv_delta
        self.min_htlc_sats = min_htlc_sats
        self.vbyte_sats = vbyte_sats
        self.is_spend_unconfirmed = is_spend_unconfirmed
        self.is_unannounced = is_unannounced

    def __str__(self) -> str:
        return f"OpenChannelRequest(peer_pubkey={self.peer_pubkey}, peer_host={self.peer_host}, channel_capacity={self.capacity}, base_fee={self.base_fee}, ppm_fee={self.ppm_fee}, cltv_delta={self.cltv_delta}, min_htlc_sats={self.min_htlc_sats}, vbyte_sats={self.vbyte_sats}, is_spend_unconfirmed={self.is_spend_unconfirmed}, is_unannounced={self.is_unannounced})"

class CloseChannelRequest:
    """
    Used in BitcoinLightningNode.close_channel() 
    """
    def __init__(
            self, 
            channel_point: str, 
            vbyte_sats: int,
            is_force: bool = False,
        ) -> None:
        self.channel_point = channel_point
        self.vbyte_sats = vbyte_sats
        self.is_force = is_force

    def __str__(self) -> str:
        return f"CloseChannelRequest(channel_point={self.channel_point}, vbyte_sats={self.vbyte_sats}, is_force={self.is_force})"

class PayInvoiceRequest:
    """
    Used in BitcoinLightningNode.pay_invoice() 
    """
    def __init__(
            self,
            invoice: str,
            fee_limit_sats: int,
            outgoing_channel_id: int | None = None,
    ) -> None:
        self.outgoing_channel_id = outgoing_channel_id
        self.invoice = invoice
        self.fee_limit_sats = fee_limit_sats
    
    def __str__(self) -> str:
        return f"PayInvoiceRequest(outgoing_channel_id={self.outgoing_channel_id}, invoice={self.invoice}, fee_limit_sats={self.fee_limit_sats})"

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
    ) -> None:
        self.peer_pubkey = peer_pubkey
        self.channel_point = channel_point
        self.capacity = capacity
        self.local_balance = local_balance
    
    def __str__(self) -> str:
        return f"PendingOpenChannel(peer_pubkey={self.peer_pubkey}, channel_point={self.channel_point}, capacity={self.capacity}, local_balance={self.local_balance})"

class ActiveOpenChannel:
    """
    Used in BitcoinLightningNode.get_open_channels() 
    """
    def __init__(
            self,
            channel_id: str,
            peer_pubkey: str,
            channel_point: str,
            capacity: int,
            local_balance: int,
    ) -> None:
        self.channel_id = channel_id
        self.peer_pubkey = peer_pubkey
        self.channel_point = channel_point
        self.capacity = capacity
        self.local_balance = local_balance
    
    def __str__(self) -> str:
        return f"ActiveOpenChannel(channel_id={self.channel_id}, peer_pubkey={self.peer_pubkey}, channel_point={self.channel_point}, capacity={self.capacity}, local_balance={self.local_balance})"

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

    def __str__(self) -> str:
        return f"DecodedInvoice(dest_pubkey={self.dest_pubkey}, payment_hash={self.payment_hash}, amount_sats={self.amount_sats}, description={self.description})"

class BitcoinLightningNode:
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
    
    def send_onchain(self, req: SendOnchainRequest) -> Result[None, str]:
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
