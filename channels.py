from lnd import ChannelTemplate


class ChannelState:
    def __init__(self, chan_id: str, capacity: int, local_balance: int, local_chan_reserve_sat: int):
        self.chan_id = chan_id
        self.capacity = capacity
        self.local_balance = local_balance
        self.local_chan_reserve_sat = local_chan_reserve_sat


class SinkNodeConfig:
    def __init__(self, config: dict):
        self.pubkey = config['pubkey']
        self.host = config['host']
        self.capacity = int(config['capacity'])
        self.num_channels = int(config['num_channels'])
        self.close_ratio = float(config['close_ratio'])
        self.base_fee = int(config['base_fee'])
        self.fee_ppm = int(config['fee_ppm'])
        self.cltv_delta = int(config['cltv_delta'])
        self.min_htlc_sat = int(config['min_htlc_sat'])
        self.mempool_fee_rec = config['mempool_fee_rec']
        self.mempool_fee_factor = float(config['mempool_fee_factor'])
        self.max_sat_per_vbyte = int(config['max_sat_per_vbyte'])


class SourceNodeConfig:
    def __init__(self, config: dict):
        self.pubkey = config['pubkey']
        self.host = config['host']
        self.capacity = int(config['capacity'])
        self.num_channels = int(config['num_channels'])
        self.base_fee = int(config['base_fee'])
        self.fee_ppm = int(config['fee_ppm'])
        self.cltv_delta = int(config['cltv_delta'])
        self.min_htlc_sat = int(config['min_htlc_sat'])
        self.swap_method = config['swap_method']
        self.loop_out_amount = int(config['loop_out_amount'])
        self.loop_out_backoff = float(config['loop_out_backoff'])
        self.max_account_balance = int(config['max_account_balance'])
        self.mempool_fee_rec = config['mempool_fee_rec']
        self.mempool_fee_factor = float(config['mempool_fee_factor'])
        self.max_sat_per_vbyte = int(config['max_sat_per_vbyte'])


class SinkNodeState:
    def __init__(self, channels: list[ChannelState], config: SinkNodeConfig, sat_per_vbyte: int):
        self.channels = channels
        self.sat_per_vbyte = sat_per_vbyte
        self.config = config


class SourceNodeState:
    def __init__(self, channels: list[ChannelState], config: SourceNodeConfig, swap_method,
                 sat_per_vbyte: int, account_balance: int):
        self.channels = channels
        self.sat_per_vbyte = sat_per_vbyte
        self.account_balance = account_balance
        self.config = config
        self.swap_method = swap_method


class SinkNodeManager:
    def __init__(self, state: SinkNodeState, node=None, log=None, mock: bool = False):
        self.node = node
        self.log = log
        self.mock = mock
        self.state = state

        self.channel_template = ChannelTemplate(
            sat_per_vbyte=self.state.sat_per_vbyte,
            node_pubkey=self.state.config.pubkey,
            local_funding_amount=self.state.config.capacity,
            base_fee=self.state.config.base_fee,
            fee_rate=self.state.config.fee_ppm,
            address=self.state.config.host,
            min_htlc_sat=self.state.config.min_htlc_sat,
            spend_unconfirmed=True
        )

        self.channels_to_close = []  # for storing empty channels
        for chan in self.state.channels:
            if float(chan.local_balance / chan.capacity) < self.state.config.close_ratio:
                self.channels_to_close.append(chan.chan_id)

    def close_empty_channels(self):
        for chan in self.channels_to_close:
            if self.state.config.max_sat_per_vbyte > self.state.sat_per_vbyte:
                if not self.mock:
                    self.node.close_channel(
                        chan.chan_id, self.state.sat_per_vbyte)
            else:
                self.log.notify(
                    f"Avoided opening a channel to {self.channel_template.node_pubkey}")

    def open_channel(self):
        if self.state.config.max_sat_per_vbyte > self.state.sat_per_vbyte:
            self.log(f"Opening channel to {self.channel_template.node_pubkey}")
            if not self.mock:
                self.node.open_channel(self.channel_template)
        else:
            self.log.notify(
                f"Avoided opening a channel to {self.channel_template.node_pubkey}")

    def get_jobs(self):
        jobs = []
        if len(self.channels_to_close) > 0:
            jobs.append("CLOSE_EMPTY_CHANNELS")
        if len(self.state.channels) - len(self.channels_to_close) \
                < self.state.config.num_channels:
            jobs.append("OPEN_CHANNEL")
        return jobs

    def execute(self, jobs=False):
        if not jobs:
            jobs = self.get_jobs()
        action_map = {
            "CLOSE_EMPTY_CHANNELS": self.close_empty_channels,
            "OPEN_CHANNEL": self.open_channel
        }
        for job in jobs:
            self.state = action_map[job]()
        return self.state


class SourceNodeManager:
    def __init__(self, state: SourceNodeState, node=None, log=None, mock: bool = False):
        self.state = state
        self.node = node
        self.log = log
        self.mock = mock

        self.channel_template = ChannelTemplate(
            sat_per_vbyte=self.state.sat_per_vbyte,
            node_pubkey=self.state.config.pubkey,
            local_funding_amount=self.state.config.capacity,
            base_fee=self.state.config.base_fee,
            fee_rate=self.state.config.fee_ppm,
            address=self.state.config.host,
            min_htlc_sat=self.state.config.min_htlc_sat,
            spend_unconfirmed=True
        )

        # get channels with enough to loop out
        self.channels_to_drain = []
        for chan in self.state.channels:
            if chan.local_balance > self.state.config.loop_out_amount:
                self.channels_to_drain.append(chan.chan_id)

    def open_channel(self):
        if self.state.config.max_sat_per_vbyte > self.state.sat_per_vbyte:
            self.log(f"Opening channel to {self.channel_template.node_pubkey}")
            if not self.mock:
                self.node.open_channel(self.channel_template)
        else:
            self.log.notify(
                f"Avoided opening a channel to {self.channel_template.node_pubkey}")

    def drain_channels(self):
        for chan_id in self.channels_to_loop_out:
            if not self.mock:
                for i in range(3):
                    invoice_amount = int(
                        self.state.config.loop_out_amount * (self.state.config.loop_out_backoff ** i))
                    bolt11_invoice = self.state.swap_method.get_lightning_invoice(
                        invoice_amount)
                    payment_response = self.node.pay_invoice(bolt11_invoice)
                    if not payment_response.payment_error:
                        break
                    elif "no_route" in payment_response.payment_error:
                        self.log("No route.")
                    else:  # no break
                        self.log.info("error no routes")

    def account_send_onchain(self):
        if not self.mock:
            self.state.swap_method.send_onchain(
                self.state.account_balance, self.state.sat_per_vbyte)

    def get_jobs(self):
        jobs = []
        if len(self.state.channels) < self.state.config.num_channels:
            jobs.append("OPEN_CHANNEL")
        if len(self.channels_to_drain) > 0:
            jobs.append("DRAIN_CHANNELS")
        if self.state.config.max_account_balance < self.state.account_balance:
            jobs.append("ACCOUNT_SEND_ONCHAIN")
        return jobs

    def execute(self, jobs=False):
        if not jobs:
            jobs = self.get_jobs()
        action_map = {
            "OPEN_CHANNEL": self.open_channel,
            "DRAIN_CHANNELS": self.drain_channels,
            "ACCOUNT_SEND_ONCHAIN": self.account_send_onchain,
        }
        for job in jobs:
            self.state = action_map[job]()
        return self.state
