import os
import codecs
import grpc
from grpc_generated import lightning_pb2_grpc, lightning_pb2 as ln
from grpc_generated import router_pb2_grpc as routerrpc, router_pb2 as router
from const import MESSAGE_SIZE_MB, LOG_ERROR, LOG_INFO, LOG_BITCOIN_LIGHTNING_NODE as logs
from config import config
from typing import List
from base import BitcoinLightningNode, OpenChannelRequest, CloseChannelRequest, PendingOpenChannel, ActiveOpenChannel, DecodedInvoice, PayInvoiceRequest, SendOnchainRequest
from result import Result, Ok, Err
from const import SAT_MSATS

class Lnd(BitcoinLightningNode):
    def __init__(self, creds_path: str) -> None:
        creds = config.get_creds(creds_path, "lnd")
        os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
        combined_credentials = self.get_credentials(
            creds.tls_cert_path, creds.macaroon_path)
        channel_options = [
            ('grpc.max_message_length', MESSAGE_SIZE_MB),
            ('grpc.max_receive_message_length', MESSAGE_SIZE_MB)
        ]
        grpc_channel = grpc.secure_channel(
            creds.grpc_host, combined_credentials, channel_options)
        self.stub = lightning_pb2_grpc.LightningStub(grpc_channel)  # type: ignore
        self.routerstub = routerrpc.RouterStub(grpc_channel)  # type: ignore

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

    def is_peer_with(self,pubkey:str) -> Result[bool,str]:
        list_peers_response:ln.ListPeersResponse = self.stub.ListPeers(ln.ListPeersRequest())
        peers = list_peers_response.peers
        return Ok(pubkey in peers)

    def add_peer(self, pubkey: str, address: str) -> Result[ln.ConnectPeerResponse, str]:
        ln_addr = ln.LightningAddress(pubkey=pubkey, host=address)
        connect_request = ln.ConnectPeerRequest(addr=ln_addr)
        try:
            res:ln.ConnectPeerResponse = self.stub.ConnectPeer(connect_request)
        except grpc._channel._InactiveRpcError as e:
            return Err(e.debug_error_string())
        return Ok(res)
    
    def get_txns(self, start_height: int, end_height: int) -> Result[ln.TransactionDetails, str]:
        txns: ln.TransactionDetails = self.stub.GetTransactions(ln.GetTransactionsRequest(
            start_height=start_height,
            end_height=end_height
        ))
        return Ok(txns)

    def open_channel(self, open_req: OpenChannelRequest) -> Result[None, str]:
        """BitcoinLightingNode"""
        msg = logs.open_channel
        is_peered = self.is_peer_with(open_req.peer_pubkey)
        if isinstance(is_peered, Err):
            return is_peered
        if not is_peered.unwrap():
            self.add_peer(open_req.peer_pubkey, open_req.peer_host)
        response = None
        try:
            response = self.stub.OpenChannelSync(
                ln.OpenChannelRequest(
                    node_pubkey_string=open_req.peer_pubkey,
                    local_funding_amount=open_req.capacity,
                    sat_per_vbyte=open_req.vbyte_sats,
                    min_htlc_msat=open_req.min_htlc_sats * SAT_MSATS,
                    spend_unconfirmed=open_req.is_spend_unconfirmed,
                    use_base_fee=True,
                    use_fee_rate=True,
                    base_fee=open_req.base_fee,
                    fee_rate=open_req.ppm_fee
                )
            )
        except Exception as e:
            if e.details: # type: ignore
                config.log(LOG_ERROR, msg.err.format('lnd', e.details(), open_req)) # type: ignore
                return Err(e.details()) # type: ignore
            config.log(LOG_ERROR, msg.err.format('lnd', e, open_req))
            return Err(e)
        config.log(LOG_INFO, msg.ok.format('lnd', open_req, response.funding_txid_bytes.hex()))
        return Ok(response)
    
    def close_channel(self, close_channel_req: CloseChannelRequest) -> Result[ln.ClosedChannelsResponse, str]:
        """BitcoinLightingNode"""
        msg = logs.close_channel    
        funding_txid_str, output_index = close_channel_req.channel_point.split(':')
        response = None
        try:
            response = self.stub.CloseChannel(
                ln.CloseChannelRequest(
                    channel_point=ln.ChannelPoint(
                        funding_txid_str=funding_txid_str, output_index=int(output_index)),
                    sat_per_vbyte=close_channel_req.vbyte_sats,
                    force=close_channel_req.is_force,
                )
            )
        except Exception as e:
            if e.details: # type: ignore
                config.log(LOG_ERROR, msg.err.format('lnd', e.details(), close_channel_req)) # type: ignore
                return Err(e.details()) # type: ignore
            config.log(LOG_ERROR, msg.err.format('lnd', e, close_channel_req))
            return Err(e)
        print(response)
        config.log(LOG_INFO, msg.ok.format('lnd', close_channel_req))
        return Ok(response) # TODO return txid 
      
    def get_pending_open_channels(self) -> Result[List[PendingOpenChannel], str]:
        """BitcoinLightingNode"""
        msg = logs.get_pending_open_channels
        request = ln.PendingChannelsRequest()
        response: ln.PendingChannelsResponse = self.stub.PendingChannels(request)
        chans = []
        for chan in response.pending_open_channels:
            chans.append(PendingOpenChannel(
                peer_pubkey=chan.channel.remote_node_pub,
                channel_point=chan.channel.channel_point,
                capacity=chan.channel.capacity,
                local_balance=chan.channel.local_balance
            ))
        config.log(LOG_INFO, msg.ok.format('lnd', len(chans)))
        return Ok(chans)

    def get_opened_channels(self) -> Result[List[ActiveOpenChannel], str]:
        """BitcoinLightingNode"""
        msg = logs.get_opened_channels
        request = ln.ListChannelsRequest()
        response: ln.ListChannelsResponse = self.stub.ListChannels(request)
        chans = []
        for chan in response.channels:
            chans.append(ActiveOpenChannel(
                channel_id=chan.chan_id,
                peer_pubkey=chan.remote_pubkey,
                channel_point=chan.channel_point,
                capacity=chan.capacity,
                local_balance=chan.local_balance,
            ))
        config.log(LOG_INFO, msg.ok.format('lnd', len(chans)))
        return Ok(chans)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """BitcoinLightingNode"""
        msg = logs.get_invoice
        invoice_response = self.stub.AddInvoice(ln.Invoice(value=sats))
        invoice = invoice_response.payment_request
        config.log(LOG_INFO, msg.ok.format('lnd', sats, invoice))
        return Ok(invoice)

    def pay_invoice(self, pay_invoice_req: PayInvoiceRequest) -> Result[str, str]:
        """BitcoinLightingNode"""
        msg = logs.pay_invoice
        args = {'payment_request': pay_invoice_req.invoice, 'fee_limit': ln.FeeLimit(fixed=pay_invoice_req.fee_limit_sats)}
        if pay_invoice_req.outgoing_channel_id:
            args['outgoing_chan_id'] = pay_invoice_req.outgoing_channel_id
        response = None
        try:
            response = self.stub.SendPaymentSync(ln.SendRequest(**args)) # type: ignore
        except Exception as e:
            if e.details: # type: ignore
                config.log(LOG_ERROR, msg.err.format('lnd', e.details(), pay_invoice_req)) # type: ignore
                return Err(e.details()) # type: ignore
            config.log(LOG_ERROR, msg.err.format('lnd', e, pay_invoice_req))
            return Err(e)
        if response.payment_error:
            config.log(LOG_ERROR, msg.err.format('lnd', response.payment_error, pay_invoice_req))
            return Err(response.payment_error)
        preimage = response.payment_preimage
        config.log(LOG_INFO, msg.ok.format('lnd', pay_invoice_req, preimage))
        return Ok(preimage)

    def get_address(self) -> Result[str, str]:
        """BitcoinLightingNode"""
        msg = logs.get_address
        new_address_request = ln.NewAddressRequest(type=ln.AddressType.UNUSED_TAPROOT_PUBKEY)
        new_address_response = self.stub.NewAddress(new_address_request)
        address = new_address_response.address
        config.log(LOG_INFO, msg.ok.format('lnd', address))
        return Ok(address)

    def send_onchain(self, send_onchain_req: SendOnchainRequest) -> Result[str, str]:
        """BitcoinLightingNode"""
        msg = logs.send_onchain
        send_request = ln.SendCoinsRequest(
            addr=send_onchain_req.dest_addr,
            amount=send_onchain_req.amount_sats,
            sat_per_vbyte=send_onchain_req.vbyte_sats
        )
        send_response = self.stub.SendCoins(send_request)
        txid: str = send_response.txid
        config.log(LOG_INFO, msg.ok.format('lnd', send_onchain_req, txid))
        return Ok(txid)

    def get_unconfirmed_balance(self) -> Result[int, str]:
        """BitcoinLightingNode"""
        msg = logs.get_unconfirmed_balance
        unconfirmed = 0
        txs = self.get_txns(start_height=0, end_height=-1).unwrap().transactions
        txns = list(filter(lambda x: x.num_confirmations == 0, txs))
        for tx in txns:
            unconfirmed += tx.amount
        config.log(LOG_INFO, msg.ok.format('lnd', unconfirmed))
        return Ok(unconfirmed)

    def get_confirmed_balance(self) -> Result[int, str]:
        """BitcoinLightingNode"""
        msg = logs.get_confirmed_balance
        balance_request = ln.WalletBalanceRequest()
        balance_response = self.stub.WalletBalance(balance_request)
        confirmed = int(balance_response.confirmed_balance)
        config.log(LOG_INFO, msg.ok.format('lnd', confirmed))
        return Ok(confirmed)

    def decode_invoice(self, invoice: str) -> Result[DecodedInvoice, str]:
        """BitcoinLightingNode"""
        msg = logs.decode_invoice
        request = ln.PayReqString(pay_req=invoice)
        decoded_req:ln.PayReq = self.stub.DecodePayReq(request)
        decoded = DecodedInvoice(
            decoded_req.destination,
            decoded_req.payment_hash,
            decoded_req.num_satoshis,
            decoded_req.description
        )
        config.log(LOG_INFO, msg.ok.format('lnd', invoice, decoded))
        return Ok(decoded)

    def sign_message(self, message: str) -> Result[str, str]:
        """BitcoinLightingNode"""
        msg = logs.sign_message
        request = ln.SignMessageRequest(
            msg=message.encode('utf-8')
        )
        response = self.stub.SignMessage(request)
        signed_message = response.signature
        config.log(LOG_INFO, msg.ok.format('lnd', message, signed_message))
        return Ok(signed_message)

    def get_alias(self, pubkey: str) -> Result[str, str]:
        """BitcoinLightingNode"""
        msg = logs.get_alias
        alias = self.stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=pubkey)).node.alias
        config.log(LOG_INFO, msg.ok.format('lnd', pubkey, alias))
        return Ok(alias)