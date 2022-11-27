from config import Config, node_map, source_map
from lnd import ChannelTemplate
from mempool import Mempool

CREDS = Config('creds.config').config


class FeeMatch:
    def __init__(self, strategy_config, default_config, log):
        self.node = node_map[strategy_config['node']](CREDS[strategy_config['node_config']], log)
        self.log = log
        self.match_key = strategy_config['match_key']
        self.premium_factor = strategy_config['premium_factor']
        self.tolerance_factor = strategy_config['tolerance_factor']
        self.cltv_delta = strategy_config['cltv_delta']
        self.base_fee = strategy_config['base_fee']
        self.min_htlc_sat = strategy_config['min_htlc_sat']
        self.max_htlc_ratio = strategy_config['max_htlc_ratio']
        self.channels = self.node.get_channels()

    def pick_ppm(self, new_ppm, old_ppm):
        diff = abs(new_ppm - old_ppm)
        tolerance = float(self.tolerance_factor) * old_ppm
        return new_ppm if diff > tolerance else old_ppm

    def execute(self):
        for chan in self.channels:
            chan_info = self.node.get_chan_info(chan.chan_id)
            my_pubkey = self.node.get_own_pubkey()
            peer_pub = chan_info.node2_pub if chan_info.node1_pub == my_pubkey else chan_info.node1_pub
            my_policy = chan_info.node1_policy if chan_info.node1_pub == my_pubkey else chan_info.node2_policy
            match_fee = self.node.get_node_fee_report(peer_pub)[self.match_key] 
            new_policy = {
                "time_lock_delta": int(self.cltv_delta),
                "min_htlc": int(self.min_htlc_sat) * 1_000,
                "fee_rate_milli_msat": match_fee + int(match_fee * float(self.premium_factor)),
                "max_htlc_msat": int(int(chan_info.capacity) * float(self.max_htlc_ratio)) * 1_000,
                "fee_base_msat": int(self.base_fee) * 1_000
            }
            old_policy = {
                "time_lock_delta": int(my_policy.time_lock_delta),
                "min_htlc": int(my_policy.min_htlc),
                "fee_rate_milli_msat": int(my_policy.fee_rate_milli_msat),
                "max_htlc_msat": int(my_policy.max_htlc_msat),
                "fee_base_msat": int(my_policy.fee_base_msat)
            }
            message = { 
                "time_lock_delta": f"Update <{chan.chan_id}> time_lock_delta from {old_policy['time_lock_delta']} to {new_policy['time_lock_delta']}",
                "min_htlc": f"Update <{chan.chan_id}> min_htlc from {old_policy['min_htlc']} to {new_policy['min_htlc']}",
                "fee_rate_milli_msat": f"Update <{chan.chan_id}> fee_ppm from {old_policy['fee_rate_milli_msat']} to {new_policy['fee_rate_milli_msat']}",
                "max_htlc_msat": f"Update <{chan.chan_id}> max_htlc_msat from {old_policy['max_htlc_msat']} to {new_policy['max_htlc_msat']}",
                "fee_base_msat": f"Update <{chan.chan_id}> base_fee from {old_policy['fee_base_msat']} to {new_policy['fee_base_msat']}" 
            }
            needs_update = False
            for key in new_policy:
                if new_policy[key] != old_policy[key]:
                    if key == 'fee_rate_milli_msat':
                        new_policy[key] = self.pick_ppm(new_policy[key], old_policy[key])
                        if new_policy[key] != old_policy[key]:   
                            needs_update = True
                            self.log.info(message[key])
                    else:
                        needs_update = True
                        self.log.info(message[key])
            if needs_update:
                self.log.info("Broadcasting new channel policy!")
                self.node.update_chan_policy(chan.chan_id, new_policy)


class SinkSource:
    def __init__(self, strategy_config, default_config, log):
        self.source = source_map[strategy_config['source']](CREDS[strategy_config['source_config']], log)
        self.node = node_map[strategy_config['node']](CREDS[strategy_config['node_config']], log)
        self.log = log
        self.sink_pub = strategy_config['sink_pub']
        self.sink_host = strategy_config['sink_host']
        self.source_pub = strategy_config['source_pub']
        self.source_host = strategy_config['source_host']
        self.source_loop_fee = int(strategy_config['source_loop_fee'])
        self.sink_budget = int(strategy_config['sink_budget'])
        self.num_sink_channels = int(strategy_config['num_sink_channels'])
        self.sink_channel_capacity = self.sink_budget / self.num_sink_channels
        self.mempool_fee = strategy_config['mempool_fee']
        self.sink_close_ratio = float(strategy_config['sink_close_ratio'])
        self.min_onchain_balance = int(default_config['min_onchain_balance'])

        self.mempool = Mempool(CREDS["MEMPOOL"], self.log)
        self.node.get_channels()
        self.sink_channels = self.node.has_channel_with(self.sink_pub)
        self.source_channels = self.node.has_channel_with(self.source_pub)
        self.confirmed = self.node.get_onchain_balance()
        self.unconfirmed = self.node.get_unconfirmed_balance()
        self.source_balance = self.source.get_account_balance()
        self.source_pending_loop_out = self.source.get_pending_widthdraw_sats()
        self.sat_per_vbyte = self.mempool.get_reccomended_fee()[self.mempool_fee]

        self.sink_channel_template = ChannelTemplate(
            sat_per_vbyte=self.sat_per_vbyte,
            node_pubkey=self.sink_pub,
            local_funding_amount=self.sink_budget / self.num_sink_channels,
            base_fee=0,
            fee_rate=9999,
            address=self.sink_host,
            min_htlc_sat=1000
        )

    def submit_widthdrawl_request(self):
        fee = self.source.get_widthdraw_fee(self.source_balance)
        if fee <= self.source_loop_fee:
            self.source.widthdraw_onchain(self.source_balance)
        else:
            self.log.warning(f"Source withdraw fee higher than expected. Found: {fee} sats Expected: {self.source_loop_fee}")

    def execute(self):
        sats_in_source_channels = 0
        source_channels_capacity = 0
        for chan in self.source_channels:
            sats_in_source_channels += chan.local_balance
            source_channels_capacity += chan.capacity
        actions = []
        # do we have enough sink channels open?
        if len(self.sink_channels) < self.num_sink_channels:
            self.log.info(f"Required sink channels not met. Target of {self.num_sink_channels} channels, but found {len(self.sink_channels)}")
            if self.unconfirmed < 0:
                self.log.info(f"Found unconfirmed sent transaction of {abs(unconfirmed)} sats and assuming its a channel open.")
                self.log.info(f"Waiting for unconfirmed sent transaction...")
                # just wait -- low time preference
                return 1
            # do we have enough sats on chain to open another sink channel?
            channel_sats_required = self.sink_channel_template.local_funding_amount + self.min_onchain_balance
            if self.confirmed > channel_sats_required:
                self.node.open_channel(self.sink_channel_template)
            else:
                missing_sats = (self.sink_channel_template.local_funding_amount + self.min_onchain_balance) - self.confirmed
                sats_accounted_for = 0
                self.log.info(f"Missing required sats to open another channel as specified. Required: {channel_sats_required} sats, but found {self.confirmed}")
                self.log.info(f"Need to find {missing_sats} and move them on chain!")
                # are there unconfirmed funds coming in our wallet?
                if self.unconfirmed > 0:
                    self.log.info(f"Found {self.unconfirmed} unconfirmed sats")
                    sats_accounted_for += self.unconfirmed
                # are there funds pending approval to widthdraw to our wallet?
                if self.source_pending_loop_out:
                    self.log.info(f"Found {self.source_pending_loop_out} sats requested to leave source")
                    sats_accounted_for += self.source_pending_loop_out
                # have we found all the sats yet? 
                if sats_accounted_for > missing_sats:
                    self.log.info(f"{sats_accounted_for} sats will arrive on chain")
                    # just wait -- low time preference
                    return 1
                # are there funds sitting in the source account?
                if self.source_balance:
                    sats_accounted_for += self.source_balance
                    self.log.info(f"{self.source_balance} sats in source account")
                    actions.append("WIDTHDRAW_FROM_SOURCE")
                # include funds in our local balance of source channels
                sats_accounted_for += sats_in_source_channels
                # have we found all the sats yet?
                if sats_accounted_for > missing_sats:
                    self.log.info(f"Found {sats_in_source_channels} sats in local balance of source channels")
                    self.log.info(f"Notifying the operator to deposit into source accounts")
                    self.log.notify(f"Need {missing_sats} to open required channels for sink/source automation. Found {sats_in_source_channels} availible to {self.source_pub}")
                    actions.append("DEPOSIT_INTO_SOURCE")
                else: # we need more sats!!!
                    actions.append("ASK_FOR_MORE_CAPITAL")
                    msg = f"Sink/Source strategy needs {missing_sats - sats_accounted_for} sats to open another source channel. Either adjust your config or seposit more sats"
                    self.log.notify(msg)
                    self.log.warning(msg)
        else: # expected number of source channels are present    
            # check if the source channels need drained
            if sats_in_source_channels / source_channels_capacity > 0.8:
                self.log.info(f"Source channels are above 50% full")
                self.log.info(f"Notifying the operator to deposit into source accounts")
                self.log.notify(f"Source channels are getting full, consider making a deposit to free up inbound")
                actions.append("DEPOSIT_INTO_SOURCE")
            # close empty sink channels
            for chan in self.sink_channels:
                if chan.local_balance / chan.capacity < self.sink_close_ratio:
                    self.node.close_channel(chan.chan_id, self.sat_per_vbyte)

        if "DEPOSIT_INTO_SOURCE" in actions:
            # TODO deposit over LN into the source account
            self.log.info("Should deposit into accounts...")
        elif "WIDTHDRAW_FROM_SOURCE" in actions:
            fee = self.source.get_widthdraw_fee(self.source_balance)
            if fee <= self.source_loop_fee:
                self.source.widthdraw_onchain(self.source_balance)
            else:
                self.log.warning(f"Source withdraw fee higher than expected. Found: {fee} sats Expected: {self.source_loop_fee}")
 
