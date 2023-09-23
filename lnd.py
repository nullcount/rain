import os
import codecs
import grpc
from grpc_generated import lightning_pb2_grpc as lnrpc, lightning_pb2 as ln
from grpc_generated import router_pb2_grpc as routerrpc, router_pb2 as router
from const import MESSAGE_SIZE_MB
import config
from typing import Any,List
from base import BitcoinLightingNode,OpenChannelRequest,CloseChannelRequest,PendingOpenChannel,ActiveOpenChannel,DecodedInvoice,PayInvoiceRequest
from result import Result, Ok, Err


class Lnd(BitcoinLightingNode):
    def __init__(self) -> None:
        creds = config.get_creds("lnd")
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
    def get_credentials(tls_cert_path: str, macaroon_path: str) -> grpc.ChannelCredentials:
        tls_certificate = open(tls_cert_path, 'rb').read()
        ssl_credentials = grpc.ssl_channel_credentials(tls_certificate)
        macaroon = codecs.encode(open(macaroon_path, 'rb').read(), 'hex')
        auth_credentials = grpc.metadata_call_credentials(
            lambda _, callback: callback([('macaroon', macaroon)], None))
        combined_credentials = grpc.composite_channel_credentials(
            ssl_credentials, auth_credentials)
        return combined_credentials

    def open_channel(self,channel: OpenChannelRequest) -> Result[None, str]:
        """BitcoinLightingNode"""
        channel_point = None
        result = self.is_peer_with(channel.peer_pubkey)
        if isinstance(result,Ok):
            is_peers_with = result.value
            if not is_peers_with:
                self.add_peer(channel.peer_pubkey, channel.peer_host)
            try:
                channel_point = self.stub.OpenChannelSync(channel)
            except grpc._channel._InactiveRpcError as e:
                return Err(e.debug_error_string())
        return Ok(channel_point)

    def is_peer_with(self,pubkey:str) -> Result[bool,str]:
        list_peers_response:ln.ListPeersResponse = self.stub.ListPeers(ln.ListPeersRequest())
        peers = list_peers_response.peers
        return Ok(pubkey in peers)

    def add_peer(self, pubkey, address):
        ln_addr = ln.LightningAddress(pubkey=pubkey, host=address)
        connect_request = ln.ConnectPeerRequest(addr=ln_addr)
        try:
            res:ln.ConnectPeerResponse = self.stub.ConnectPeer(connect_request)
        except grpc._channel._InactiveRpcError as e:
            return Err(e.debug_error_string())
        return Ok(res)

    def close_channel(self,close_channel_req:CloseChannelRequest) -> Result[ln.ClosedChannelsResponse, str]:
        """BitcoinLightingNode"""
        channel_point = close_channel_req.channel_point
        sat_per_vbyte = close_channel_req.vbyte_sats
        if (not channel_point) or (not sat_per_vbyte):
            return Err("Must provide chan_id and sat_per_vbyte to close a channel.")
        open_channels_res = self.get_opened_channels()
        if isinstance(open_channels_res,Ok):
            open_channels = open_channels_res.unwrap()
            target_channels = list(filter(lambda channel: channel.channel_point == channel_point,open_channels))
            if not len(target_channels) > 0:
                return Err(f"The channel id provided does not exist:  {channel_point}")
            target_channel = target_channels[0]
            channel_point_str = target_channel.channel_point
            funding_txid_str, output_index = channel_point_str.split(':')

            close_channel_request = ln.CloseChannelRequest(
                channel_point=ln.ChannelPoint(
                    funding_txid_str=funding_txid_str, output_index=int(output_index)),
                sat_per_vbyte=sat_per_vbyte,
                force=close_channel_req.is_force,
            )
            close_status_update_response = self.stub.CloseChannel(close_channel_request)
            return Ok(close_status_update_response)
        else:
            return open_channels_res
        
    def get_pending_open_channels(self) -> Result[List[PendingOpenChannel], str]:
        """BitcoinLightingNode"""
        pending_channels_request = ln.PendingChannelsRequest()
        pending_channels_response:ln.PendingChannelsResponse = self.stub.PendingChannels(pending_channels_request)
        pending_open_channels = pending_channels_response.pending_open_channels
        # TODO convert channel list to PendingOpenChannel list
        return Ok(list(map(lambda x: x.channel, pending_open_channels)))

    def get_opened_channels(self) -> Result[List[ActiveOpenChannel], str]:
        """BitcoinLightingNode"""
        request = ln.ListChannelsRequest()
        response: ln.ListChannelsResponse = self.stub.ListChannels(request)
        # TODO convert to ActiveOpenChannel list
        return Ok(response.channels)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """BitcoinLightingNode"""
        invoice = ''
        raise NotImplementedError
        return Ok(invoice)

    def pay_invoice(self,pay_invoice_req: PayInvoiceRequest) -> Result[None, str]:
        """BitcoinLightingNode"""
        return Ok(None)

    def get_address(self) -> Result[str, str]:
        """BitcoinLightingNode"""
        new_address_request = ln.NewAddressRequest(type=5) # get unused taproot pubkey type
        new_address_response = self.stub.NewAddress(new_address_request)
        #TODO self.log.info("LND generated deposit address: {}".format(addr)
        return Ok(new_address_response.address)

    def send_onchain(self) -> Result[None, str]:
        """BitcoinLightingNode"""
        raise NotImplementedError
        return Ok(None)

    def get_unconfirmed_balance(self) -> Result[int, str]:
        """BitcoinLightingNode"""
        total = 0
        txs = self.get_txns(end_height=-1).transactions
        txns = list(filter(lambda x: x.num_confirmations == 0, txs))
        if len(txns) > 0:
            for tx in txns:
                total += tx.amount
        #TODO self.log.info("LND unconfirmed balance: {} sats".format(total))
        return Ok(total)

    def get_confirmed_balance(self) -> Result[int, str]:
        """BitcoinLightingNode"""
        balance_request = ln.WalletBalanceRequest()
        balance_response = self.stub.WalletBalance(balance_request)
        confirmed = int(balance_response.confirmed_balance)
        return Ok(confirmed)

    def decode_invoice(self, invoice: str) -> Result[DecodedInvoice, str]:
        """BitcoinLightingNode"""
        request = ln.PayReqString(pay_req=invoice)
        decoded:ln.PayReq = self.stub.DecodePayReq(request)
        return Ok(DecodedInvoice(decoded.destination,
                                 decoded.payment_hash,
                                 decoded.num_satoshis,
                                 decoded.description))

    def sign_message(self, message: str) -> Result[str, str]:
        """BitcoinLightingNode"""
        request = ln.SignMessageRequest(
            msg=message.encode('utf-8')
        )
        response = self.stub.SignMessage(request)
        signed_message = response.signature
        return Ok(signed_message)

    def get_alias(self, pubkey: str) -> Result[str, str]:
        """BitcoinLightingNode"""
        alias = self.stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=pubkey)).node.alias
        return Ok(alias)


"""
BELOW IS OLD lnd.py FOR REFERENCE
"""

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
        txns = self.get_txns(end_height=-1).transactions
        txns = list(filter(lambda x: x.num_confirmations == 0, txs))
        txns = self.get_unconfirmed_txns()
        if len(txns) > 0:
            for tx in txns:
                total += tx.amount
        #TODO self.log.info("LND unconfirmed balance: {} sats".format(total))
        return total