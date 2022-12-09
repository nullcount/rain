from config import Config, node_map, source_map
from lnd import ChannelTemplate
from mempool import Mempool
from report import Report

CREDS = Config('creds.config').config


class FeeMatch:
    def __init__(self, strategy_config, default_config, log):
        self.node = node_map[strategy_config['node']](CREDS[strategy_config['node']], log)
        self.log = log
        self.report = Report(self.node, log)
        self.match_key = strategy_config['match_key']
        self.premium_factor = strategy_config['premium_factor']
        self.tolerance_factor = strategy_config['tolerance_factor']
        self.cltv_delta = strategy_config['cltv_delta']
        self.base_fee = strategy_config['base_fee']
        self.min_htlc_sat = strategy_config['min_htlc_sat']
        self.max_htlc_ratio = strategy_config['max_htlc_ratio']
        self.channels = self.node.get_channels()

    def dump_state(self):
        return vars(self)

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
            match_fee = self.report.get_node_fee_stats(peer_pub)[self.match_key]
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
                "time_lock_delta": f"Update <{chan.chan_id}> time_lock_delta \
                        from {old_policy['time_lock_delta']} \
                        to {new_policy['time_lock_delta']}",
                "min_htlc": f"Update <{chan.chan_id}> min_htlc from \
                        {old_policy['min_htlc']} to {new_policy['min_htlc']}",
                "fee_rate_milli_msat": f"Update <{chan.chan_id}> fee_ppm from \
                        {old_policy['fee_rate_milli_msat']} to \
                        {new_policy['fee_rate_milli_msat']}",
                "max_htlc_msat": f"Update <{chan.chan_id}> max_htlc_msat from \
                        {old_policy['max_htlc_msat']} to \
                        {new_policy['max_htlc_msat']}",
                "fee_base_msat": f"Update <{chan.chan_id}> base_fee from \
                        {old_policy['fee_base_msat']} to \
                        {new_policy['fee_base_msat']}" 
            }
            needs_update = False
            for key in new_policy:
                if new_policy[key] != old_policy[key]:
                    if key == 'fee_rate_milli_msat':
                        ppm = self.pick_ppm(new_policy[key], old_policy[key])
                        new_policy[key] = ppm
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
    def __init__(self, strategy_config=None, default_config=None, log=None, mock=False, mock_state=None):
        self.source = source_map[strategy_config['source']](CREDS[strategy_config['source_config']], log) if not mock else None
        self.node = node_map[strategy_config['node']](CREDS[strategy_config['node']], log) if not mock else None
        self.log = log.info if not mock else print
        self.notify = log.notify if not mock else print
        self.mock = mock  # True if this is a test
        self.sink_pub = strategy_config['sink_pub'] if not mock else None
        self.sink_host = strategy_config['sink_host'] if not mock else None
        self.source_pub = strategy_config['source_pub'] if not mock else None
        self.source_host = strategy_config['source_host'] if not mock else None
        self.source_loop_fee = int(strategy_config['source_loop_fee']) if not mock else int(mock_state['source_loop_fee'])
        self.sink_budget = int(strategy_config['sink_budget']) if not mock else int(mock_state['sink_budget'])
        self.num_sink_channels_target = int(strategy_config['num_sink_channels_target']) if not mock else int(mock_state['num_sink_channels_target'])
        self.sink_channel_capacity = self.sink_budget / self.num_sink_channels_target
        self.mempool_fee = strategy_config['mempool_fee'] if not mock else None
        self.sink_close_ratio = float(strategy_config['sink_close_ratio']) if not mock else float(mock_state['sink_close_ratio'])
        self.min_onchain_balance = int(default_config['min_onchain_balance']) if not mock else int(mock_state['min_onchain_balance'])

        self.mempool = Mempool(CREDS["MEMPOOL"], self.log) if not mock else None
        self.node.get_channels() if not mock else None
        self.sink_channels = self.node.has_channel_with(self.sink_pub) if not mock else None
        self.source_channels = self.node.has_channel_with(self.source_pub) if not mock else None
        self.confirmed = self.node.get_onchain_balance() if not mock else int(mock_state['confirmed'])
        self.unconfirmed = self.node.get_unconfirmed_balance() if not mock else int(mock_state['unconfirmed'])
        self.source_balance = self.source.get_account_balance() if not mock else int(mock_state['source_balance'])
        self.source_pending_loop_out = self.source.get_pending_send_sats() if not mock else int(mock_state['source_pending_loop_out'])
        self.sat_per_vbyte = int(self.mempool.get_fee()[self.mempool_fee]) if not mock else int(mock_state['sat_per_vbyte'])
        self.max_sat_per_vbyte = int(strategy_config['max_sat_per_vbyte']) if not mock else int(mock_state['max_sat_per_vbyte'])
        self.sats_on_the_way = self.unconfirmed + self.source_pending_loop_out
        self.num_sink_channels = len(self.sink_channels) if not mock else int(mock_state['num_sink_channels'])

        self.sink_channel_template = ChannelTemplate(
            sat_per_vbyte=self.sat_per_vbyte,
            node_pubkey=self.sink_pub,
            local_funding_amount=int(self.sink_budget / self.num_sink_channels_target),
            base_fee=0,
            fee_rate=9999,
            address=self.sink_host,
            min_htlc_sat=1000
        )

        self.sats_required_for_sink_channel = \
            self.sink_channel_template.local_funding_amount + \
            self.min_onchain_balance
        self.sats_in_source_channels = 0.0
        self.source_channels_capacity = 0.0
        self.source_channels_local_reserve_sats = 0.0
        if not mock:
            for chan in self.source_channels:
                self.sats_in_source_channels += chan.local_balance
                self.source_channels_capacity += chan.capacity
                self.source_channels_local_reserve_sats += chan.local_chan_reserve_sat
        else:
            self.sats_in_source_channels = float(mock_state['sats_in_source_channels'])
            self.source_channels_capacity = float(mock_state['source_channels_capacity'])
            self.source_channels_local_reserve_sats = float(mock_state['source_channels_local_reserve_sats'])

        self.log_msg_map = {
                "avoid_close_fee_too_large": f"Channel close avoided: using {self.mempool_fee} at {self.sat_per_vbyte} sat/vbyte with max fee of {self.max_sat_per_vbyte} sat/vbyte",
                "source_fee_too_large": lambda fee: f"Source widthdrawl fee higher than expected. Found: {fee} sats Expected: {self.source_loop_fee}",
                "wait_money_leaving": f"Found unconfirmed sent transaction of {abs(self.unconfirmed)} sats. Assuming this is a channel open transaction.",
                "wait_money_on_the_way": f"Found enough sats to open channel in unconfirmed: {self.unconfirmed} sats and pending: {self.source_pending_loop_out} sats from source account.",
                "notify_need_more_sats": lambda sats_found, sats_needed: f"Need {sats_needed} sats for sink-source strategy to open channel. Found {sats_found} sats",
                "try_open_channel": "Attempting to open a new source channel...",
                "avoid_open_fee_too_large": f"Channel open avoided: using {self.mempool_fee} at {self.sat_per_vbyte} sat/vbyte with max fee of {self.max_sat_per_vbyte} sat/vbyte"
        }

    def dump_state(self):
        return vars(self)

    def is_money_leaving_node(self):
        return self.unconfirmed < 0

    def is_fee_in_budget(self):
        return self.max_sat_per_vbyte > self.sat_per_vbyte

    def has_enough_sats_for_new_sink_channel(self):
        return self.sats_required_for_sink_channel < self.confirmed

    def has_enough_sink_channels(self):
        return self.num_sink_channels >= self.num_sink_channels_target

    def has_source_channels_full(self):
        return self.sats_in_source_channels / self.source_channels_capacity \
                > (1.0 - self.sink_close_ratio)

    def has_source_channels_empty(self):
        return self.sats_in_source_channels / self.source_channels_capacity \
                < self.sink_close_ratio

    def has_enough_sats_on_the_way(self):
        return self.sats_required_for_sink_channel < self.sats_on_the_way \
            + self.confirmed

    def has_enough_sats_in_source_channels(self):
        return self.sats_on_the_way + self.confirmed + self.source_balance + \
                self.sats_in_source_channels \
                > self.sats_required_for_sink_channel

    def should_initiate_source_account_onchain_send(self):
        # we should only send on chain if we absolutely need the sats
        # flat fees are incurred so try to be maximally efficient
        # empty channels to source first
        if self.source_balance == 0:
            return False  # no money to send
        if self.source_pending_loop_out > 0:
            return False  # money already sent recently
        if self.sats_on_the_way + self.confirmed + self.source_balance > \
                self.sats_required_for_sink_channel:
            # the funds in acct would be enough to open a channel
            if self.has_source_channels_empty():
                return True  # ready to init send request
        return False

    def empty_source_channels(self):
        send_amt = self.sats_in_source_channels - self.source_channels_local_reserve_sats
        self.source.send_to_acct(send_amt, self.node)

    def close_empty_sink_channels(self):
        for chan in self.sink_channels:
            if chan.local_balance / chan.capacity < self.sink_close_ratio:
                if self.is_fee_in_budget():
                    self.node.close_channel(chan.chan_id, self.sat_per_vbyte)
                else:
                    self.notify(self.log_msg_map['avoid_close_fee_too_large'])

    def submit_send_request(self):
        fee = self.source.get_onchain_fee(self.source_balance)
        if fee <= self.source_loop_fee:
            self.source.send_onchain(self.source_balance)
        else:
            self.log(self.log_msg_map['source_fee_too_large'](fee))

    def wait_money_leaving(self):
        self.log(self.log_msg_map['wait_money_leaving'])

    def wait_money_on_the_way(self):
        self.log(self.log_msg_map['wait_money_on_the_way'])

    def notify_need_more_sats(self):
        sats_found = self.confirmed + self.sats_on_the_way + \
                    self.source_balance
        sats_needed = self.sats_required_for_sink_channel - sats_found
        self.notify(self.log_msg_map['notify_need_more_sats'](sats_found, sats_needed))

    def try_open_channel(self):
        if self.is_fee_in_budget():
            self.log(self.log_msg_map['try_open_channel'])
            self.node.open_channel(self.sink_channel_template)
        else:
            self.notify(self.log_msg_map['avoid_open_fee_too_large'])

    def source_send_onchain(self):
        self.source.send_onchain(self.source_balance)

    def run_jobs(self, jobs):
        map = {
            "EMPTY_SOURCE_CHANNELS": self.empty_source_channels,
            "CLOSE_EMPTY_SINK_CHANNELS": self.close_empty_sink_channels,
            "WAIT_MONEY_LEAVING": self.wait_money_leaving,
            "TRY_OPEN_CHANNEL": self.try_open_channel,
            "WAIT_MONEY_ON_THE_WAY": self.wait_money_on_the_way,
            "SOURCE_SEND_ONCHAIN": self.source_send_onchain,
            "NOTIFY_NEED_MORE_SATS": self.notify_need_more_sats,
        }
        for key in map:
            if key in jobs:
                map[key]()

    def execute(self):
        jobs = []
        if self.has_enough_sink_channels():
            if self.has_source_channels_full():
                jobs.append("EMPTY_SOURCE_CHANNELS")
            jobs.append("CLOSE_EMPTY_SINK_CHANNELS")
        # we need to open another sink channel
        elif self.is_money_leaving_node():
            jobs.append("WAIT_MONEY_LEAVING")
        elif self.has_enough_sats_for_new_sink_channel():
            jobs.append("TRY_OPEN_CHANNEL")
        elif self.has_enough_sats_on_the_way():
            jobs.append("WAIT_MONEY_ON_THE_WAY")
        elif self.should_initiate_source_account_onchain_send():
            jobs.append('SOURCE_SEND_ONCHAIN')
        elif self.has_enough_sats_in_source_channels():
            jobs.append("EMPTY_SOURCE_CHANNELS")
        else:
            # if we make it here, we need more sats!!!
            jobs.append("NOTIFY_NEED_MORE_SATS")
        self.log(f"Execution results in: {', '.join(jobs)}")
        if self.mock:
            return jobs
        else:
            self.run_jobs(jobs)
        self.log("Finished execution of sink/source strategy")
