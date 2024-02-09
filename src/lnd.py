"""
lnd.py
---
An implementation of Lightning Network Daemon (LND) gRPC as a BitcoinLightningNode
usage: add your lnd credentials
"""
import os
import codecs
import grpc
from grpc_generated import lightning_pb2_grpc, lightning_pb2 as ln
from grpc_generated import router_pb2_grpc as routerrpc, router_pb2 as router
from const import SAT_MSATS, LOG_ERROR, LOG_INFO
from typing import List
from bitcoin_lightning_node import BitcoinLightningNode, OpenChannelRequest, CloseChannelRequest, PendingOpenChannel, ActiveOpenChannel, DecodedInvoice, PayInvoiceRequest, SendOnchainRequest
from result import Result, Ok, Err

class LndCreds:
    """
    connect an LND node using an admin macaroon, tls cert, and grpc host:port
        if connecting a remote lnd, you may need to add extratls=<IP_OF_LND> to your lnd.conf
    """
    def __init__(self, tls_cert_path: str = 'tls.cert', macaroon_path: str = 'admin.macroon', grpc_host: str = '127.0.0.1:10009') -> None:
        self.grpc_host = grpc_host
        self.macaroon_path = macaroon_path
        self.tls_cert_path = tls_cert_path

class Lnd(BitcoinLightningNode):
    def __init__(self, creds: LndCreds) -> None:
        super().__init__() # init logger from parent class
        MESSAGE_SIZE_MB = 50 * 1024 * 1024
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
        self.alias = self.get_alias(self.get_pubkey().unwrap()).unwrap()

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
                self.log(LOG_ERROR, self.logs.open_channel.err.format(self.alias, e.details(), open_req)) # type: ignore
                return Err(e.details()) # type: ignore
            self.log(LOG_ERROR, self.logs.open_channel.err.format(self.alias, e, open_req))
            return Err(str(e))
        self.log(LOG_INFO, self.logs.open_channel.ok.format(self.alias, open_req, response.funding_txid_bytes.hex()))
        return Ok(response)
    
    def close_channel(self, close_channel_req: CloseChannelRequest) -> Result[str, str]:
        """BitcoinLightingNode"""
        funding_txid_str, output_index = close_channel_req.channel_point.split(':')
        args = {'channel_point': ln.ChannelPoint(funding_txid_str=funding_txid_str, output_index=int(output_index)), 'max_fee_per_vbyte': 1000}
        if close_channel_req.is_force:
            args['force'] = True 
        else:
            args['sat_per_vbyte'] = close_channel_req.vbyte_sats
            args['force'] = False
        txid = ''
        try:
            for response in self.stub.CloseChannel(ln.CloseChannelRequest(**args)): # type: ignore
                txid = response.close_pending.txid.hex()
                self.log(LOG_INFO, self.logs.close_channel.ok.format(self.alias, close_channel_req, txid))
        except Exception as e:
            if 'details' in e: # type: ignore
                self.log(LOG_ERROR, self.logs.close_channel.err.format(self.alias, e.details(), close_channel_req)) # type: ignore
                return Err(e.details()) # type: ignore
            self.log(LOG_ERROR, self.logs.close_channel.err.format(self.alias, e, close_channel_req))
            return Err(str(e))
        return Ok(txid)
      
    def get_pending_open_channels(self) -> Result[List[PendingOpenChannel], str]:
        """BitcoinLightingNode"""
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
        self.log(LOG_INFO, self.logs.get_pending_open_channels.ok.format(self.alias, len(chans)))
        return Ok(chans)

    def get_opened_channels(self) -> Result[List[ActiveOpenChannel], str]:
        """BitcoinLightingNode"""
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
        self.log(LOG_INFO, self.logs.get_opened_channels.ok.format(self.alias, len(chans)))
        return Ok(chans)

    def get_invoice(self, sats: int) -> Result[str, str]:
        """BitcoinLightingNode"""
        invoice_response = self.stub.AddInvoice(ln.Invoice(value=sats))
        invoice = invoice_response.payment_request
        self.log(LOG_INFO, self.logs.get_invoiceg.ok.format(self.alias, sats, invoice))
        return Ok(invoice)

    def pay_invoice(self, pay_invoice_req: PayInvoiceRequest) -> Result[str, str]:
        """BitcoinLightingNode"""
        args = {'payment_request': pay_invoice_req.invoice, 'fee_limit': ln.FeeLimit(fixed=pay_invoice_req.fee_limit_sats)}
        if pay_invoice_req.outgoing_channel_id:
            args['outgoing_chan_id'] = pay_invoice_req.outgoing_channel_id
        response = None
        try:
            response = self.stub.SendPaymentSync(ln.SendRequest(**args)) # type: ignore
        except Exception as e:
            if e.details: # type: ignore
                self.log(LOG_ERROR, msg.err.format(self.alias, e.details(), pay_invoice_req)) # type: ignore
                return Err(e.details()) # type: ignore
            self.log(LOG_ERROR, self.logs.pay_invoice.err.format(self.alias, e, pay_invoice_req))
            return Err(str(e))
        if response.payment_error:
            self.log(LOG_ERROR, self.logs.pay_invoice.err.format(self.alias, response.payment_error, pay_invoice_req))
            return Err(response.payment_error)
        preimage = response.payment_preimage.hex()
        self.log(LOG_INFO, self.logs.pay_invoice.ok.format(self.alias, pay_invoice_req, preimage))
        return Ok(preimage)

    def get_address(self) -> Result[str, str]:
        """BitcoinLightingNode"""
        new_address_request = ln.NewAddressRequest(type=ln.AddressType.UNUSED_TAPROOT_PUBKEY)
        new_address_response = self.stub.NewAddress(new_address_request)
        address = new_address_response.address
        self.log(LOG_INFO, self.logs.get_address.ok.format(self.alias, address))
        return Ok(address)

    def send_onchain(self, send_onchain_req: SendOnchainRequest) -> Result[str, str]:
        """BitcoinLightingNode"""
        send_request = ln.SendCoinsRequest(
            addr=send_onchain_req.dest_addr,
            amount=send_onchain_req.amount_sats,
            sat_per_vbyte=send_onchain_req.vbyte_sats
        )
        send_response = self.stub.SendCoins(send_request)
        txid: str = send_response.txid
        self.log(LOG_INFO, self.logs.send_onchain.ok.format(self.alias, send_onchain_req, txid))
        return Ok(txid)

    def get_unconfirmed_balance(self) -> Result[int, str]:
        """BitcoinLightingNode"""
        unconfirmed = 0
        txs = self.get_txns(start_height=0, end_height=-1).unwrap().transactions
        txns = list(filter(lambda x: x.num_confirmations == 0, txs))
        for tx in txns:
            unconfirmed += tx.amount
        self.log(LOG_INFO, self.logs.get_unconfirmed_balance.ok.format(self.alias, unconfirmed))
        return Ok(unconfirmed)

    def get_confirmed_balance(self) -> Result[int, str]:
        """BitcoinLightingNode"""
        balance_request = ln.WalletBalanceRequest()
        balance_response = self.stub.WalletBalance(balance_request)
        confirmed = int(balance_response.confirmed_balance)
        self.log(LOG_INFO, self.logs.get_confirmed_balance.ok.format(self.alias, confirmed))
        return Ok(confirmed)

    def decode_invoice(self, invoice: str) -> Result[DecodedInvoice, str]:
        """BitcoinLightingNode"""
        request = ln.PayReqString(pay_req=invoice)
        decoded_req:ln.PayReq = self.stub.DecodePayReq(request)
        decoded = DecodedInvoice(
            decoded_req.destination,
            decoded_req.payment_hash,
            decoded_req.num_satoshis,
            decoded_req.description
        )
        self.log(LOG_INFO, self.logs.decode_invoice.ok.format(self.alias, invoice, decoded))
        return Ok(decoded)

    def sign_message(self, message: str) -> Result[str, str]:
        """BitcoinLightingNode"""
        request = ln.SignMessageRequest(
            msg=message.encode('utf-8')
        )
        response = self.stub.SignMessage(request)
        signed_message = response.signature
        self.log(LOG_INFO, self.logs.sign_message.ok.format(self.alias, message, signed_message))
        return Ok(signed_message)

    def get_pubkey(self) -> Result[str, str]:
        """BitcoinLightningNode"""
        info = self.stub.GetInfo(ln.GetInfoRequest())
        self.log(LOG_INFO, self.logs.get_pubkey.ok.format('LND', info.identity_pubkey))
        return Ok(info.identity_pubkey)

    def get_alias(self, pubkey: str) -> Result[str, str]:
        """BitcoinLightingNode"""
        alias = self.stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=pubkey)).node.alias
        self.log(LOG_INFO, self.logs.get_alias.ok.format(alias, pubkey, alias))
        return Ok(alias)