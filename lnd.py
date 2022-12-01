import os
import codecs
import grpc
import sys
import re
import time
import statistics

from grpc_generated import rpc_pb2_grpc as lnrpc, rpc_pb2 as ln
from grpc_generated import router_pb2_grpc as routerrpc, router_pb2 as router

MESSAGE_SIZE_MB = 50 * 1024 * 1024
SAT_MSATS = 1000


def debug(message):
    sys.stderr.write(message + "\n")


class ChannelTemplate:
    def __init__(self, node_pubkey, local_funding_amount, address, sat_per_vbyte, base_fee, fee_rate, min_htlc_sat):
        self.node_pubkey = node_pubkey
        self.local_funding_amount = local_funding_amount
        self.sat_per_vbyte = sat_per_vbyte
        self.min_htlc_sat = min_htlc_sat
        self.base_fee = base_fee
        self.fee_rate = fee_rate
        self.address = address

    def get_open_req(self):
        return ln.OpenChannelRequest(
            node_pubkey_string=self.node_pubkey,
            local_funding_amount=self.local_funding_amount,
            sat_per_vbyte=self.sat_per_vbyte,
            min_htlc_msat=self.min_htlc_sat * SAT_MSATS
        )


class Lnd:
    def __init__(self, LND_NODE_CONFIG, logger):
        self.log = logger
        grpc_host = LND_NODE_CONFIG['grpc_host']
        tls_cert_path = LND_NODE_CONFIG['tls_cert_path']
        macaroon_path = LND_NODE_CONFIG['macaroon_path']

        os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
        combined_credentials = self.get_credentials(tls_cert_path, macaroon_path)
        channel_options = [
            ('grpc.max_message_length', MESSAGE_SIZE_MB),
            ('grpc.max_receive_message_length', MESSAGE_SIZE_MB)
        ]
        grpc_channel = grpc.secure_channel(grpc_host, combined_credentials, channel_options)
        self.stub = lnrpc.LightningStub(grpc_channel)
        self.routerstub = routerrpc.RouterStub(grpc_channel)
        self.graph = None
        self.info = None
        self.channels = None
        self.peers = None
        self.node_info = {}
        self.chan_info = {}
        self.fwdhistory = {}
        self.valid = True
        self.peer_channels = {}
        try:
            self.feereport = self.get_feereport()
        except grpc._channel._InactiveRpcError:
            self.valid = False

    @staticmethod
    def get_credentials(tls_cert_path, macaroon_path):
        tls_certificate = open(tls_cert_path, 'rb').read()
        ssl_credentials = grpc.ssl_channel_credentials(tls_certificate)
        macaroon = codecs.encode(open(macaroon_path, 'rb').read(), 'hex')
        auth_credentials = grpc.metadata_call_credentials(lambda _, callback: callback([('macaroon', macaroon)], None))
        combined_credentials = grpc.composite_channel_credentials(ssl_credentials, auth_credentials)
        return combined_credentials

    def get_info(self):
        if self.info is None:
            self.info = self.stub.GetInfo(ln.GetInfoRequest())
        return self.info

    def get_node_channels(self, nodeid):
        g = self.get_graph()
        channels = []
        for c in g.edges:
            if c.node1_pub == nodeid or c.node2_pub == nodeid:
                channels.append(c)
        return channels

    def get_node_fee_report(self, nodeid):
        channels = self.get_node_channels(nodeid)
        in_ppm = []
        out_ppm = []
        for c in channels:
            policy = []
            if c.node1_pub == nodeid:
                out_ppm.append(c.node1_policy.fee_rate_milli_msat)
                in_ppm.append(c.node2_policy.fee_rate_milli_msat)
            else:
                out_ppm.append(c.node2_policy.fee_rate_milli_msat)
                in_ppm.append(c.node1_policy.fee_rate_milli_msat)
        # remove outliers
        corrected_in_ppm = list(filter(lambda x: x > 0 and x < 10_000, in_ppm))
        corrected_out_ppm = list(filter(lambda x: x > 0 and x < 10_000, out_ppm))
        return {"in_min": min(in_ppm), "in_max": max(in_ppm), "in_avg": int(statistics.mean(in_ppm)), "in_corrected_avg": int(statistics.mean(corrected_in_ppm)), "in_med": int(statistics.median(in_ppm)), "in_std": int(statistics.stdev(in_ppm)), "out_min": min(out_ppm), "out_max": max(out_ppm), "out_avg": int(statistics.mean(out_ppm)), "out_corrected_avg": int(statistics.mean(corrected_out_ppm)), "out_med": int(statistics.median(out_ppm)), "out_std": int(statistics.stdev(out_ppm))}

    def get_peers(self):
        if self.peers is None:
            self.peers = self.stub.ListPeers(ln.ListPeersRequest()).peers
        return self.peers

    def is_peer_with(self, peer_pubkey):
        if self.peers is None:
            self.get_peers()
        for peer in self.peers:
            if peer.pub_key == peer_pubkey:
                self.log.info("LND is already peered with {}".format(peer_pubkey))
                return True
        return False

    def subscribe_htlc_events(self):
        req = router.SubscribeHtlcEventsRequest()
        return self.routerstub.SubscribeHtlcEvents(req)

    def add_peer(self, pubkey, address):
        ln_addr = ln.LightningAddress(pubkey=pubkey, host=address)
        connectRequest = ln.ConnectPeerRequest(addr=ln_addr)
        res = self.stub.ConnectPeer(connectRequest)
        self.log.info("LND connected to peer {}@{}".format(pubkey, address))
        return res

    def get_feereport(self):
        feereport = self.stub.FeeReport(ln.FeeReportRequest())
        feedict = {}
        for channel_fee in feereport.channel_fees:
            feedict[channel_fee.chan_id] = (channel_fee.base_fee_msat, channel_fee.fee_per_mil)
        return feedict

    # query the forwarding history for a channel covering the last # of seconds
    def get_forward_history(self, chanid, seconds):
        # cache all history to avoid stomping on lnd
        last_time = self.fwdhistory['last'] if 'last' in self.fwdhistory else int(time.time())

        start_time = int(time.time()) - seconds
        leeway = 5  # don't call lnd on each second boundary
        if start_time < last_time - leeway:
            # retrieve (remaining) for the queried period
            index_offset = 0
            done = False
            thishistory = {}
            while not done:
                forwards = self.stub.ForwardingHistory(ln.ForwardingHistoryRequest(
                    start_time=start_time, end_time=last_time, index_offset=index_offset))
                if forwards.forwarding_events:
                    for forward in forwards.forwarding_events:
                        if not forward.chan_id_out in thishistory:
                            thishistory[forward.chan_id_out] = {'in': [], 'out': []}
                        if not forward.chan_id_in in thishistory:
                            thishistory[forward.chan_id_in] = {'in': [], 'out': []}
                        # most recent last
                        thishistory[forward.chan_id_out]['out'].append(forward)
                        thishistory[forward.chan_id_in]['in'].append(forward)
                    index_offset = forwards.last_offset_index
                else:
                    done = True

            # add queried to existing cache and keep time order
            for i in thishistory.keys():
                if not i in self.fwdhistory:
                    self.fwdhistory[i] = {'in': [], 'out': []}
                self.fwdhistory[i]['in'] = thishistory[i]['in'] + self.fwdhistory[i]['in']
                self.fwdhistory[i]['out'] = thishistory[i]['out'] + self.fwdhistory[i]['out']

            self.fwdhistory['last'] = start_time

        chan_data = self.fwdhistory[chanid] if chanid in self.fwdhistory else {'in': [], 'out': []}
        result = {'htlc_in': 0, 'htlc_out': 0, 'sat_in': 0, 'sat_out': 0, 'last_in': 0, 'last_out': 0}

        for fwd in reversed(chan_data['in']):
            if fwd.timestamp < start_time:
                break
            result['htlc_in'] = result['htlc_in'] + 1
            result['sat_in'] = result['sat_in'] + fwd.amt_in
            result['last_in'] = fwd.timestamp

        for fwd in reversed(chan_data['out']):
            if fwd.timestamp < start_time:
                break
            result['htlc_out'] = result['htlc_out'] + 1
            result['sat_out'] = result['sat_out'] + fwd.amt_out
            result['last_out'] = fwd.timestamp

        return result

    def get_node_info(self, nodepubkey):
        if not nodepubkey in self.node_info:
            self.node_info[nodepubkey] = self.stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=nodepubkey))
        return self.node_info[nodepubkey]

    def get_chan_info(self, chanid):
        if not chanid in self.chan_info:
            try:
                self.chan_info[chanid] = self.stub.GetChanInfo(ln.ChanInfoRequest(chan_id=chanid))
            except:
                print("Failed to lookup {}".format(chanid), file=sys.stderr)
                return None
        return self.chan_info[chanid]

    def update_chan_policy(self, chanid, policy):
        base_fee_msat = policy['fee_base_msat']
        fee_ppm = policy['fee_rate_milli_msat']
        min_htlc_msat = policy['min_htlc']
        max_htlc_msat = policy['max_htlc_msat']
        time_lock_delta = policy['time_lock_delta']
        
        chan_info = self.get_chan_info(chanid)
        if not chan_info:
            return None
        channel_point = ln.ChannelPoint(
            funding_txid_str=chan_info.chan_point.split(':')[0],
            output_index=int(chan_info.chan_point.split(':')[1])
        )
        my_policy = chan_info.node1_policy if chan_info.node1_pub == self.get_own_pubkey() else chan_info.node2_policy
        
        base_fee_msat = (base_fee_msat if base_fee_msat is not None else my_policy.fee_base_msat)
        fee_rate = fee_ppm if fee_ppm is not None else my_policy.fee_rate_milli_msat
        min_htlc_msat = (min_htlc_msat if min_htlc_msat is not None else my_policy.min_htlc)
        max_htlc_msat = (max_htlc_msat if max_htlc_msat is not None else my_policy.max_htlc_msat)
        time_lock_delta = (time_lock_delta if time_lock_delta is not None else my_policy.time_lock_delta)
    
        self.log.info(f"base_fee_msat: {base_fee_msat} ppm: {fee_rate} min_htlc_msat: {min_htlc_msat} max_htlc_msat: {max_htlc_msat} time_lock_delta: {time_lock_delta}")

        res = self.stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(
            chan_point=channel_point,
            base_fee_msat=base_fee_msat,
            fee_rate=(fee_rate / 1_000_000),
            min_htlc_msat=min_htlc_msat,
            max_htlc_msat=max_htlc_msat,
            time_lock_delta=time_lock_delta
        ))
        return res

    def get_txns(self, start_height=None, end_height=None):
        return self.stub.GetTransactions(ln.GetTransactionsRequest(
            start_height=start_height,
            end_height=end_height
        ))

    def get_graph(self):
        if self.graph is None:
            self.graph = self.stub.DescribeGraph(ln.ChannelGraphRequest(include_unannounced=True))
        return self.graph

    def get_own_pubkey(self):
        return self.get_info().identity_pubkey

    def get_node_alias(self, pubkey):
        return self.stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=pubkey)).node.alias

    def get_edges(self):
        return self.get_graph().edges

    def get_channels(self):
        if self.channels is None:
            request = ln.ListChannelsRequest()
            self.channels = self.stub.ListChannels(request).channels
        return self.channels
    
    def get_closed_channels(self):
        if self.closed_channels is None:
            req = ln.ClosedChannelsRequest()
            self.closed_channels = self.stub.ClosedChannels(req).channels
        return self.closed_channels

    # Get all channels shared with a node
    def get_shared_channels(self, peerid):
        # See example: https://github.com/lightningnetwork/lnd/issues/3930#issuecomment-596041700
        byte_peerid = bytes.fromhex(peerid)
        if peerid not in self.peer_channels:
            request = ln.ListChannelsRequest(peer=byte_peerid)
            self.peer_channels[peerid] = self.stub.ListChannels(request).channels
        return self.peer_channels[peerid]

    def min_version(self, major, minor, patch=0):
        p = re.compile("(\d+)\.(\d+)\.(\d+).*")
        m = p.match(self.get_info().version)
        if m is None:
            return False
        if major > int(m.group(1)):
            return False
        if minor > int(m.group(2)):
            return False
        if patch > int(m.group(3)):
            return False
        return True

    def update_chan_status(self, chanid, disable):
        chan_info = self.get_chan_info(chanid)
        if not chan_info:
            return None
        channel_point = ln.ChannelPoint(
            funding_txid_str=chan_info.chan_point.split(':')[0],
            output_index=int(chan_info.chan_point.split(':')[1])
        )
        my_policy = chan_info.node1_policy if chan_info.node1_pub == self.get_own_pubkey() else chan_info.node2_policy
        # ugly code, retries with 'AUTO' if channel turns out not to be active.
        # Alternative is to iterate or index the channel list, just to get active status
        try:
            action = 'DISABLE' if disable else 'ENABLE'
            self.routerstub.UpdateChanStatus(router.UpdateChanStatusRequest(
                chan_point=channel_point,
                action=action
            ))
        except:
            action = 'DISABLE' if disable else 'AUTO'
            self.routerstub.UpdateChanStatus(router.UpdateChanStatusRequest(
                chan_point=channel_point,
                action=action
            ))

    @staticmethod
    def hex_string_to_bytes(hex_string):
        decode_hex = codecs.getdecoder("hex_codec")
        return decode_hex(hex_string)[0]

    def pay_invoice(self, invoice_string):
        send_request = ln.SendRequest(payment_request=invoice_string)
        send_response = self.stub.SendPaymentSync(send_request)
        self.log.info(f"LND pay invoice response: {send_response}")
        return send_response

    def send_onchain(self, dest_addr, amount_sats, target_conf, sat_per_vbyte):
        send_request = ln.SendCoinsRequest(
            addr=dest_addr,
            amount=amount_sats,
            target_conf=target_conf,
            sat_per_vbyte=sat_per_vbyte
        )
        send_response = self.stub.SendCoins(send_request)
        return send_response

    def open_channel(self, channel: ChannelTemplate):
        if not self.is_peer_with(channel.node_pubkey):
            self.add_peer(channel.node_pubkey, channel.address)
        channel_point = self.stub.OpenChannelSync(channel.get_open_req())
        self.log.info(f"LND open channel {channel.local_funding_amount} sats with peer: {channel.node_pubkey}")
        return channel_point

    def close_channel(self, chan_id, sat_per_vbyte):
        return

    def get_onchain_balance(self):
        balance_request = ln.WalletBalanceRequest()
        balance_response = self.stub.WalletBalance(balance_request)
        confirmed = balance_response.confirmed_balance
        self.log.info("LND confirmed onchain balance: {} sats".format(confirmed))
        return confirmed

    def get_onchain_address(self):
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
        addr = new_address_response.address
        self.log.info("LND generated deposit address: {}".format(addr))
        return addr

    def add_lighting_invoice(self, amount):
        add_invoice_request = ln.Invoice(value=amount)
        invoice_response = self.stub.AddInvoice(add_invoice_request)
        return invoice_response

    def get_unconfirmed_txns(self):
        txs = self.get_txns(end_height=-1).transactions
        return list(filter(lambda x: x.num_confirmations == 0, txs))

    def get_unconfirmed_balance(self):
        total = 0
        txns = self.get_unconfirmed_txns()
        if len(txns) > 0:
            for tx in txns:
                total += tx.amount
        self.log.info("LND unconfirmed balance: {} sats".format(total))
        return total

    def has_channel_with(self, peer_pubkey):
        chans = []
        for chan in self.channels:
            if chan.remote_pubkey == peer_pubkey:
                chans.append(chan)
        return chans
