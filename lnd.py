import os
import codecs
import grpc
from grpc_generated import lightning_pb2_grpc as lnrpc, lightning_pb2 as ln
from grpc_generated import router_pb2_grpc as routerrpc, router_pb2 as router
from const import MESSAGE_SIZE_MB
from config import get_creds, log
from typing import Any
from base import BitcoinLightingNode
from result import Result, Ok, Err

class Lnd(BitcoinLightingNode):
    def __init__(self) -> None:
        creds = get_creds("lnd")
        os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
        combined_credentials = self.get_credentials(
            creds.tls_cert_path, creds.macaroon_path)
        channel_options = [
            ('grpc.max_message_length', MESSAGE_SIZE_MB),
            ('grpc.max_receive_message_length', MESSAGE_SIZE_MB)
        ]
        grpc_channel = grpc.secure_channel(
            creds.grpc_host, combined_credentials, channel_options)
        self.stub = lnrpc.LightningStub(grpc_channel)
        self.routerstub = routerrpc.RouterStub(grpc_channel)
        
    @staticmethod
    def get_credentials(tls_cert_path: str, macaroon_path: str) -> Any:
        tls_certificate = open(tls_cert_path, 'rb').read()
        ssl_credentials = grpc.ssl_channel_credentials(tls_certificate)
        macaroon = codecs.encode(open(macaroon_path, 'rb').read(), 'hex')
        auth_credentials = grpc.metadata_call_credentials(
            lambda _, callback: callback([('macaroon', macaroon)], None))
        combined_credentials = grpc.composite_channel_credentials(
            ssl_credentials, auth_credentials)
        return combined_credentials

    def open_channel(self) -> Result[None, str]:
        """BitcoinLightingNode"""
        return Ok(None)
    
    def close_channel(self) -> Result[None, str]:
        """BitcoinLightingNode"""
        return Ok(None)
    
    def get_pending_channels(self) -> Result[Box, str]:
        """BitcoinLightingNode"""
        return 
    
    def get_opened_channels(self) -> Result[Box, str]:
        """BitcoinLightingNode"""
        return
    
    def get_invoice(self, sats: int) -> Result[str, str]:
        """BitcoinLightingNode"""
        invoice = ''
        return Ok(invoice)
    
    def pay_invoice(self) -> Result[None, str]:
        """BitcoinLightingNode"""
        return Ok(None)
    
    def get_address(self) -> Result[str, str]:
        """BitcoinLightingNode"""
        addr = ''
        return Ok(None)
    
    def send_onchain(self) -> Result[None, str]:
        """BitcoinLightingNode"""
        return Ok(None)
    
    def get_unconfirmed_balance(self) -> Result[int, str]:
        """BitcoinLightingNode"""
        unconfirmed = 0
        return Ok(unconfirmed)

    def get_confirmed_balance(self) -> Result[int, str]:
        """BitcoinLightingNode"""
        confirmed = 0
        return Ok(confirmed)
    
    def decode_invoice(self, invoice: str) -> Result[Box, str]:
        """BitcoinLightingNode"""
        return
    
    def sign_message(self, message: str) -> Result[str, str]:
        """BitcoinLightingNode"""
        signed_message = ''
        return Ok(signed_message)
    
    def get_alias(self, pubkey: str) -> Result[str, str]:
        """BitcoinLightingNode"""
        alias = ''
        return Ok(alias)





    def add_peer(self, pubkey, address):
        ln_addr = ln.LightningAddress(pubkey=pubkey, host=address)
        connectRequest = ln.ConnectPeerRequest(addr=ln_addr)
        res = None
        try:
            res = self.stub.ConnectPeer(connectRequest)
            # TODO self.log.info(f"LND connected to peer {pubkey}@{address}")
        except grpc._channel._InactiveRpcError as e:
            pass
            # TODO self.log.notify(f"An error occurred while adding peer: {e}")
        return res

    def get_graph(self, refresh=False):
        if self.graph is None or refresh:
            self.graph = self.stub.DescribeGraph(
                ln.ChannelGraphRequest(include_unannounced=True))
        return self.graph

    def get_own_pubkey(self):
        return self.get_info().identity_pubkey

    def get_alias(self, pubkey):
        return self.stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=pubkey)).node.alias

    def get_edges(self):
        return self.get_graph().edges

    def get_open_channels(self):
        if self.channels is None:
            request = ln.ListChannelsRequest()
            self.channels = self.stub.ListChannels(request).channels
        return self.channels

    def get_closed_channels(self):
        if self.closed_channels is None:
            req = ln.ClosedChannelsRequest()
            self.closed_channels = self.stub.ClosedChannels(req).channels
        return self.closed_channels

    def decode_invoice(self, invoice: str) -> dict[Any, Any]:
        request = ln.PayReqString(pay_req=invoice)
        decoded: dict[Any, Any] = self.stub.DecodePayReq(request)
        return decoded

    def pay_invoice(self, invoice_string, outgoing_chan_id=None, fee_limit=60000):
        #TODO self.log.info(f"LND found invoice to pay: {invoice_string}")
        args = {"payment_request": invoice_string}
        if outgoing_chan_id:
            args["outgoing_chan_id"] = outgoing_chan_id
        if fee_limit:
            args["fee_limit"] = ln.FeeLimit(fixed=fee_limit)
        send_request = ln.SendRequest(**args)
        send_response = self.stub.SendPaymentSync(send_request)
        #TODO self.log.info(f"LND pay invoice response: {send_response}")
        return send_response

    def send_onchain(self, send_request: ln.SendCoinsRequest) -> dict[Any, Any]:
        # send_request = ln.SendCoinsRequest(
        #     addr=dest_addr,
        #     amount=amount_sats,
        #     target_conf=target_conf,
        #     sat_per_vbyte=sat_per_vbyte
        # )
        send_response: dict[Any, Any] = self.stub.SendCoins(send_request)
        return send_response

    def open_channel(self, channel: ln.openChannelRequest) -> str:
        channel_point = None
        if not self.is_peer_with(channel.node_pubkey):
            self.add_peer(channel.node_pubkey, channel.address)
        try:
            channel_point = self.stub.OpenChannelSync(channel)
        except grpc._channel._InactiveRpcError as e:
            if "Number of pending channels exceed maximum" in e.debug_error_string():
                return channel_point  # done for now
            else:
                pass
                #TODO self.log.notify(f"An error occurred while opening channel: {e}")
        return channel_point

    def close_channel(self, chan_id, sat_per_vbyte, force=False, target_conf=None, delivery_address=None):
        if (not chan_id) or (not sat_per_vbyte):
            # TODO self.log.info(f"Must provide chan_id and sat_per_vbyte to close a channel. " f"chan_id: {chan_id}, sat_per_vbyte: {sat_per_vbyte}")
            return
        target_channels = list(
            filter(lambda channel: channel.chan_id == chan_id, self.get_open_channels()))
        if not len(target_channels) > 0:
            # TODO self.log.info(f"The channel id provided does not exist:  {chan_id}")
            return
        target_channel = target_channels[0]
        channel_point_str = target_channel.channel_point
        funding_txid_str, output_index = channel_point_str.split(':')

        close_channel_request = ln.CloseChannelRequest(
            channel_point=ln.ChannelPoint(
                funding_txid_str=funding_txid_str, output_index=int(output_index)),
            sat_per_vbyte=sat_per_vbyte,
            force=force,
            target_conf=target_conf,
            delivery_address=delivery_address)
        close_status_update_response = self.stub.CloseChannel(
            close_channel_request)
        return close_status_update_response

    def get_onchain_balance(self) -> int:
        balance_request = ln.WalletBalanceRequest()
        balance_response = self.stub.WalletBalance(balance_request)
        return int(balance_response.confirmed_balance)
        #TODO self.log.info("LND confirmed onchain balance: {} sats".format(confirmed))

    def get_onchain_address(self) -> str:
        """
        WITNESS_PUBKEY_HASH = 0;
        NESTED_PUBKEY_HASH = 1;
        UNUSED_WITNESS_PUBKEY_HASH = 2;
        UNUSED_NESTED_PUBKEY_HASH = 3;
        TAPROOT_PUBKEY = 4;
        UNUSED_TAPROOT_PUBKEY = 5;
        """
        new_address_request = ln.NewAddressRequest(type=2)
        new_address_response = self.stub.NewAddress(new_address_request)
        return str(new_address_response.address)
        #TODO self.log.info("LND generated deposit address: {}".format(addr))

    def add_lightning_invoice(self, amount: int, memo: str) -> str:
        add_invoice_request = ln.Invoice(value=amount, memo=memo)
        invoice_response = self.stub.AddInvoice(add_invoice_request)
        return str(invoice_response)

    def get_unconfirmed_txns(self) -> list[Any]:
        txs = self.get_txns(end_height=-1).transactions
        return list(filter(lambda x: x.num_confirmations == 0, txs))

    def get_unconfirmed_balance(self) -> int:
        total = 0
        txns = self.get_unconfirmed_txns()
        if len(txns) > 0:
            for tx in txns:
                total += tx.amount
        #TODO self.log.info("LND unconfirmed balance: {} sats".format(total))
        return total

    def get_pending_channels(self) -> list[Any]:
        pending_channels_request = ln.PendingChannelsRequest()
        pending_channels_response = self.stub.PendingChannels(
            pending_channels_request)
        pending_open_channels = pending_channels_response.pending_open_channels
        return list(
            map(lambda x: x.channel, pending_open_channels))