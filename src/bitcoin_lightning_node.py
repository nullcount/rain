"""
bitcoin_lighting_node.py
---
A lightning node with admin controls
usage: a base class for lightning node implementation wrappers
"""
from box import Box
from result import Result
from typing import List
from console import console
from const import LOG_GAP

class SendOnchainRequest:
    """
    Type used in BitcoinLightningNode.send_onchain()
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
    Type used in BitcoinLightningNode.open_channel() 
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
    Type used in BitcoinLightningNode.close_channel() 
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
    Type used in BitcoinLightningNode.pay_invoice() 
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
    Type used in BitcoinLightningNode.get_pending_open_channels() 
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
    Tyep used in BitcoinLightningNode.get_open_channels() 
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
    Type used in BitcoinLightningNode.decode_invoice() 
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
    def __init__(self) -> None:
        self.log = console.log
        self.logs = Box({
            "open_channel": {
                "ok": LOG_GAP.join(["{}", "open_channel", "response: {}, funding_txid: {}"]),
                "err": LOG_GAP.join(["{}", "open_channel", "{}", "response: {}"])
            },
            "close_channel": {
                "ok": LOG_GAP.join(["{}", "close_channel", "response: {}, closing_txid: {}"]),
                "err": LOG_GAP.join(["{}", "close_channel", "{}"])
            },
            "get_pending_open_channels": {
                "ok": LOG_GAP.join(["{}", "get_pending_open_channels", "response: {}"]),
                "err": LOG_GAP.join(["{}", "get_pending_open_channels", "{}"])
            },
            "get_opened_channels": {
                "ok": LOG_GAP.join(["{}", "get_opened_channels", "response: {}"]),
                "err": LOG_GAP.join(["{}", "get_opened_channels", "{}"])
            },
            "get_invoice": {
                "ok": LOG_GAP.join(["{}", "get_invoice", "sats: {}, invoice: {}"]),
                "err": LOG_GAP.join(["{}", "get_invoice", "{}"])
            },
            "pay_invoice": {
                "ok": LOG_GAP.join(["{}", "pay_invoice", "response: {}, preimage: {}"]),
                "err": LOG_GAP.join(["{}", "pay_invoice", "{}", "response: {}"])
            },
            "get_address": {
                "ok": LOG_GAP.join(["{}", "get_address", "address: {}"]),
                "err": LOG_GAP.join(["{}", "get_address", "{}"])
            }, 
            "send_onchain": {
                "ok": LOG_GAP.join(["{}", "send_onchain", "response: {}, txid: {}"]),
                "err": LOG_GAP.join(["{}", "send_onchain", "{}"])
            },
            "get_unconfirmed_balance": {
                "ok": LOG_GAP.join(["{}", "get_unconfirmed_balance", "unconfirmed_balance_sats: {}"]),
                "err": LOG_GAP.join(["{}", "get_unconfirmed_balance", "{}"])
            },
            "get_confirmed_balance": {
                "ok": LOG_GAP.join(["{}", "get_confirmed_balance", "confirmed_balance_sats: {}"]),
                "err": LOG_GAP.join(["{}", "get_confirmed_balance", "{}"])
            },
            "decode_invoice": {
                "ok": LOG_GAP.join(["{}", "decode_invoice", "invoice: {}, decoded_invoice: {}"]),
                "err": LOG_GAP.join(["{}", "decode_invoice", "{}"])
            },
            "sign_message": {
                "ok": LOG_GAP.join(["{}", "sign_message", "message: {}, signed_message: {}"]),
                "err": LOG_GAP.join(["{}", "sign_message", "{}"])
            },
            "get_pubkey": {
                "ok": LOG_GAP.join(["{}", "get_pubkey", "pubkey: {}"]),
                "err": LOG_GAP.join(["{}", "get_pubkey", "{}"])
            },
            "get_alias": {
                "ok": LOG_GAP.join(["{}", "get_alias", "pubkey: {}, alias: {}"]),
                "err": LOG_GAP.join(["{}", "get_alias", "{}"])
            }
        })

    def open_channel(self, req: OpenChannelRequest) -> Result[None, str]:
        """Ok(funding_txid)"""
        raise NotImplementedError
    
    def close_channel(self, req: CloseChannelRequest) -> Result[str, str]:
        """Ok(closing_txid)"""
        raise NotImplementedError
    
    def get_pending_open_channels(self) -> Result[List[PendingOpenChannel], str]:
        raise NotImplementedError
    
    def get_opened_channels(self) -> Result[List[ActiveOpenChannel], str]:
        raise NotImplementedError
    
    def get_invoice(self, sats: int) -> Result[str, str]:
        raise NotImplementedError
    
    def pay_invoice(self, req: PayInvoiceRequest) -> Result[str, str]:
        """Ok(preimage)"""
        raise NotImplementedError
    
    def get_address(self) -> Result[str, str]:
        raise NotImplementedError
    
    def send_onchain(self, req: SendOnchainRequest) -> Result[str, str]:
        """Ok(transaction_id)"""
        raise NotImplementedError
    
    def get_unconfirmed_balance(self) -> Result[int, str]:
        raise NotImplementedError

    def get_confirmed_balance(self) -> Result[int, str]:
        raise NotImplementedError
    
    def decode_invoice(self, invoice: str) -> Result[DecodedInvoice, str]:
        raise NotImplementedError
    
    def sign_message(self, message: str) -> Result[str, str]:
        raise NotImplementedError
    
    def get_own_pubkey(self) -> Result[str, str]:
        raise NotImplementedError

    def get_alias(self, pubkey: str) -> Result[str, str]:
        raise NotImplementedError