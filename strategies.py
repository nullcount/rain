from lnd import ChannelTemplate
from mempool import Mempool
from report import Report
from kraken import Kraken
from nicehash import Nicehash
from muun import Muun
from lnd import Lnd


class FeeMatch:
    def __init__(self, strategy_config=None, DEFAULT=None, CREDS=None, node=None, log=None):
        self.node = node
        self.log = log
        self.report = Report(CREDS, self.node, log)
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
    def __init__(self, strategy_config=None, DEFAULT=None, CREDS=None, node: Lnd = None, log=None, mock=False,
                 mock_state=None):
        source_map = {
            "kraken": Kraken,
            "nicehash": Nicehash,
            "muun": Muun
        }
        self.source = source_map[strategy_config['source']](CREDS[strategy_config['source_config']], log) if not mock else None
        self.node: Lnd = node if not mock else None
        self.log = log.info if not mock else print
        self.notify = log.notify if not mock else print
        self.mock = mock  # True if this is a test
        self.sink_pub = strategy_config['sink_pub'] if not mock else None
        self.sink_host = strategy_config['sink_host'] if not mock else None
        self.sink_budget = int(strategy_config['sink_budget']) if not mock else int(mock_state['sink_budget'])
        self.sink_fee_ppm = int(strategy_config['sink_fee_ppm']) if not mock else 10_000
        self.source_fee_ppm = int(strategy_config['source_fee_ppm']) if not mock else 10_000
        self.sink_close_ratio = float(strategy_config['sink_close_ratio']) if not mock else float(mock_state['sink_close_ratio'])
        self.sink_channel_count = int(strategy_config['sink_channel_count']) if not mock else int(mock_state['sink_channel_count'])
        self.sink_channel_capacity = self.sink_budget / self.sink_channel_count
        self.source_host = strategy_config['source_host'] if not mock else None
        self.source_pub = strategy_config['source_pub'] if not mock else None
        self.source_budget = int(strategy_config['source_budget']) if not mock else int(mock_state['source_budget'])
        self.source_channel_count = int(strategy_config['source_channel_count']) if not mock else int(mock_state['source_channel_count'])
        self.source_channel_capacity = 0
        try:
            self.source_channel_capacity = self.source_budget / self.source_channel_count
        except ZeroDivisionError:
            self.log("There are no source channels")
        self.source_close_ratio = float(strategy_config['source_close_ratio']) if not mock else int(mock_state['source_close_ratio'])
        self.source_loop_out_amount = int(strategy_config['source_loop_out_amount']) if not mock else None
        self.source_loop_out_backoff = float(strategy_config['source_loop_out_backoff']) if not mock else None
        self.source_loop_out_attempts = int(strategy_config['source_loop_out_attempts']) if not mock else None
        self.min_onchain_balance = int(strategy_config['min_onchain_balance']) if not mock else int(mock_state['min_onchain_balance'])
        self.mempool_fee = strategy_config['mempool_fee'] if not mock else None
        self.mempool_fee_factor = float(strategy_config['mempool_fee_factor']) if not mock else None
        self.mempool = Mempool(CREDS["MEMPOOL"], self.log) if not mock else None
        self.confirmed = self.node.get_onchain_balance() if not mock else int(mock_state['confirmed'])
        self.unconfirmed = self.node.get_unconfirmed_balance() if not mock else int(mock_state['unconfirmed'])
        self.node.get_channels() if not mock else None
        self.sink_channels = self.node.has_channel_with(self.sink_pub) if not mock else None
        self.source_channels = self.node.has_channel_with(self.source_pub) if not mock else None
        self.num_sink_channels = len(self.sink_channels) if not mock else int(mock_state['num_sink_channels'])
        self.num_source_channels = len(self.source_channels) if not mock else int(mock_state['num_source_channels'])
        self.pending_sink_channels = filter(lambda x: x['channel']['remote_node_pub'] == self.sink_pub, self.node.get_pending_channel_opens()) if not mock else None
        self.source_account_balance = self.source.get_account_balance() if not mock else int(mock_state['source_account_balance'])
        self.sat_per_vbyte = int(self.mempool.get_fee()[self.mempool_fee] * self.mempool_fee_factor) if not mock else int(mock_state['sat_per_vbyte'])
        self.max_sat_per_vbyte = int(strategy_config['max_sat_per_vbyte']) if not mock else int(mock_state['max_sat_per_vbyte'])

        self.sink_channel_template = ChannelTemplate(
            sat_per_vbyte=self.sat_per_vbyte,
            node_pubkey=self.sink_pub,
            local_funding_amount=self.sink_channel_capacity,
            base_fee=0,  # zerobasefee
            fee_rate=self.sink_fee_ppm,
            address=self.sink_host,
            min_htlc_sat=1000,
            spend_unconfirmed=True
        )

        self.source_channel_template = ChannelTemplate(
            sat_per_vbyte=self.sat_per_vbyte,
            node_pubkey=self.source_pub,
            local_funding_amount=self.source_channel_capacity,
            base_fee=0,  # zerobasefee
            fee_rate=self.source_fee_ppm,
            address=self.source_host,
            min_htlc_sat=1000,
            spend_unconfirmed=True
        )

        self.sats_required_for_sink_channel = \
            self.source_channel_capacity + \
            self.min_onchain_balance
        self.sats_required_for_source_channel = \
            self.source_channel_capacity + \
            self.min_onchain_balance

        self.source_channel_local_sats = 0.0
        self.source_channels_local_reserve_sats = 0.0

        self.sink_channel_local_sats = 0.0
        self.sink_channels_capacity = 0.0
        self.sink_channels_local_reserve_sats = 0.0

        self.sink_channels_to_close = []
        self.source_channels_to_close = []
        if not mock:
            for chan in self.source_channels:
                if float(chan.local_balance / chan.capacity) < self.source_close_ratio:
                    self.source_channels_to_close.append(chan.chan_id)
                self.source_channel_local_sats += chan.local_balance
                self.source_channels_local_reserve_sats += chan.local_chan_reserve_sat
            for chan in self.sink_channels:
                if float(chan.local_balance / chan.capacity) < self.source_close_ratio:
                    self.sink_channels_to_close.append(chan.chan_id)
                self.sink_channel_local_sats += chan.local_balance
                self.sink_channels_capacity += chan.capacity
                self.sink_channels_local_reserve_sats += chan.local_chan_reserve_sat
        else:
            self.source_channel_local_sats = float(mock_state['source_channels_local_sats'])
            self.source_channels_local_reserve_sats = 0.0
            self.sink_channel_local_sats = float(mock_state['sink_channels_local_sats'])
            self.sink_channels_capacity = float(mock_state['sink_channels_capacity'])
            self.sink_channels_local_reserve_sats = 0.0
        self.log_msg_map = {
            "avoid_close_fee_too_large": f"Channel close avoided: using {self.mempool_fee} at {self.sat_per_vbyte} sat/vbyte with max fee of {self.max_sat_per_vbyte} sat/vbyte",
            "wait_money_leaving": f"Found unconfirmed sent transaction of {abs(self.unconfirmed)} sats. Assuming this is a channel open transaction.",
            "try_open_sink_channel": "Attempting to open a new sink channel...",
            "try_open_source_channel": "Attempting to open a new source channel...",
            "avoid_open_fee_too_large": f"Channel open avoided: using {self.mempool_fee} at {self.sat_per_vbyte} sat/vbyte with max fee of {self.max_sat_per_vbyte} sat/vbyte",
        }
        # MAIN EXECUTION PATH CONDITIONS
        self.sats_spendable_onchain = self.confirmed + self.unconfirmed - self.min_onchain_balance
        self.HAS_ENOUGH_SOURCE_CHANNELS = \
            self.num_source_channels >= self.source_channel_count
        self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_ONCHAIN = \
            self.sats_required_for_source_channel \
            < self.sats_spendable_onchain
        self.HAS_EMPTY_SINK_CHANNELS = len(self.sink_channels_to_close) > 0 if not mock else mock_state["HAS_EMPTY_SINK_CHANNELS"]
        self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_SINK_CHANNELS = \
            self.sats_spendable_onchain + self.sink_channel_local_sats \
            >= self.source_channel_capacity
        self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_ACCOUNT = \
            self.sats_spendable_onchain + self.source_account_balance \
            >= self.source_channel_capacity
        self.HAS_ENOUGH_SINK_CHANNELS = \
            (self.num_sink_channels - len(self.sink_channels_to_close)) \
            >= self.sink_channel_count
        self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_ONCHAIN = \
            self.sink_channel_capacity \
            < self.sats_spendable_onchain
        self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_SOURCE_CHANNELS = \
            self.source_channel_local_sats + self.sats_spendable_onchain \
            >= self.sink_channel_capacity
        self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_ACCOUNT = \
            self.sats_spendable_onchain + self.source_account_balance \
            >= self.sink_channel_capacity
        # END MAIN EXECUTION PATH CONDITIONS
        print(f"HAS_ENOUGH_SOURCE_CHANNELS: {self.HAS_ENOUGH_SOURCE_CHANNELS}")
        print(f"HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_ONCHAIN: {self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_ONCHAIN}")
        print(f"HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_SINK_CHANNELS: {self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_SINK_CHANNELS}")
        print(f"HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_ACCOUNT: {self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_ACCOUNT}")
        print(f"HAS_ENOUGH_SINK_CHANNELS: {self.HAS_ENOUGH_SINK_CHANNELS}")
        print(f"HAS_EMPTY_SINK_CHANNELS: {self.HAS_EMPTY_SINK_CHANNELS}")
        print(f"HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_ONCHAIN: {self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_ONCHAIN}")
        print(f"HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_SOURCE_CHANNELS: {self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_SOURCE_CHANNELS}")
        print(f"HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_ACCOUNT: {self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_ACCOUNT}")

    def dump_state(self):
        return vars(self)

    def is_chain_fee_in_budget(self):
        return self.max_sat_per_vbyte > self.sat_per_vbyte

    def try_close_empty_sink_channels(self):
        for chan in self.sink_channels_to_close:
            if self.is_chain_fee_in_budget():
                self.node.close_channel(chan.chan_id, self.sat_per_vbyte)
            else:
                self.notify(self.log_msg_map['avoid_close_fee_too_large'])

    def try_drain_source_channel(self):
        for i in range(self.source_loop_out_attempts):
            invoice_amount = int(self.source_loop_out_amount * (self.source_loop_out_backoff ** i))
            bolt11_invoice = self.source.get_lightning_invoice(invoice_amount)
            payment_response = self.node.pay_invoice(bolt11_invoice)
            if not payment_response.payment_error:
                break
            elif "no_route" in payment_response.payment_error:
                self.log("No route.")
        else:  # no break
            self.log.info("error no routes")

    def try_harvest_sink_channels(self):
        chans_to_harvest = []
        sorted_chans = sorted(self.sink_channels, key=lambda x: x.capacity, reverse=True)
        sats_so_far = 0
        sats_needed_for_source_channel = self.sats_required_for_source_channel \
                                         - (self.confirmed + self.unconfirmed)
        for chan in sorted_chans:
            sats_so_far += chan.capacity
            chans_to_harvest.append(chan.chan_id)
            if sats_so_far > sats_needed_for_source_channel:
                break
        for chan_id in chans_to_harvest:
            if self.is_chain_fee_in_budget():
                self.node.close_channel(chan_id, self.sat_per_vbyte)
            else:
                self.notify(self.log_msg_map['avoid_close_fee_too_large'])

    def notify_need_more_sats(self):
        sats_found = self.confirmed + self.unconfirmed + \
                    self.source_account_balance - self.min_onchain_balance
        sats_needed = self.sats_required_for_sink_channel - sats_found
        self.notify(self.log_msg_map['notify_need_more_sats'](sats_found, sats_needed))

    def try_open_sink_channel(self):
        if self.is_chain_fee_in_budget():
            self.log(self.log_msg_map['try_open_sink_channel'])
            self.node.open_channel(self.sink_channel_template)
        else:
            self.notify(self.log_msg_map['avoid_open_fee_too_large'])

    def try_open_source_channel(self):
        if self.is_chain_fee_in_budget():
            self.log(self.log_msg_map['try_open_source_channel'])
            self.node.open_channel(self.source_channel_template)
        else:
            self.notify(self.log_msg_map['avoid_open_fee_too_large'])

    def source_account_send_onchain(self):
        self.source.send_onchain(self.source_account_balance, self.sat_per_vbyte)

    def run_jobs(self, jobs):
        print(jobs)
        map = {
            "TRY_CLOSE_EMPTY_SINK_CHANNELS": self.try_close_empty_sink_channels,
            "TRY_OPEN_SOURCE_CHANNEL": self.try_open_source_channel,
            "TRY_OPEN_SINK_CHANNEL": self.try_open_sink_channel,
            "TRY_DRAIN_SOURCE_CHANNEL": self.try_drain_source_channel,
            "TRY_HARVEST_SINK_CHANNELS": self.try_harvest_sink_channels,
            "SOURCE_ACCOUNT_SEND_ONCHAIN": self.source_account_send_onchain,
        }
        for key in jobs:
            map[key]()

    def execute(self):
        jobs = []
        if self.HAS_ENOUGH_SOURCE_CHANNELS and self.HAS_EMPTY_SINK_CHANNELS:
            jobs.append("TRY_CLOSE_EMPTY_SINK_CHANNELS")

        if not self.HAS_ENOUGH_SINK_CHANNELS and \
                self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_ONCHAIN:
            jobs.append("TRY_OPEN_SINK_CHANNEL")

        if not self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_ONCHAIN and \
                self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_ACCOUNT:
            jobs.append("SOURCE_ACCOUNT_SEND_ONCHAIN")

        if not self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_ACCOUNT and \
                self.HAS_ENOUGH_SATS_FOR_SINK_CHANNEL_IN_SOURCE_CHANNELS:
            jobs.append("TRY_DRAIN_SOURCE_CHANNEL")

        if not self.HAS_ENOUGH_SOURCE_CHANNELS and \
                self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_ONCHAIN:
            jobs.append("TRY_OPEN_SOURCE_CHANNEL")

        if not self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_ONCHAIN and \
                self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_ACCOUNT:
            jobs.append("SOURCE_ACCOUNT_SEND_ONCHAIN")

        if not self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_ACCOUNT and \
                self.HAS_ENOUGH_SATS_FOR_SOURCE_CHANNEL_IN_SINK_CHANNELS:
            jobs.append("TRY_HARVEST_SINK_CHANNELS")

        self.log(f"Execution results in: {', '.join(jobs)}")
        if self.mock:
            return jobs
        else:
            self.run_jobs(jobs)
        self.log("Finished execution of sink/source strategy")
