from lnd import ChannelTemplate


class ChannelState:
    def __init__(self, chan_id: str, pending: bool, capacity: int, local_balance: int, local_chan_reserve_sat: int):
        self.chan_id = chan_id
        self.pending = pending
        self.capacity = capacity
        self.local_balance = local_balance
        self.local_chan_reserve_sat = local_chan_reserve_sat

    def get_debug_str(self):
        attrs = vars(self)
        a = []
        for key, value in attrs.items():
            a.append(f'{key} = {value}')
        return "\n".join(a)


class Job:
    def __init__(self, name: str, do, do_when: bool, debug_str: str):
        self.name = name
        self.do = do
        self.do_when = do_when
        self.debug_str = debug_str


class Manager:
    def __init__(self):
        self.job_list = []

    def get_jobs(self):
        return [job for job in self.job_list if job.do_when]

    def execute(self, jobs=[], debug: bool = False):
        if not jobs:
            jobs = self.get_jobs()
        i = 1
        for job in jobs:
            if debug:
                print(
                    f"EVALUATION OF {self.state.config.config_label} RESULTS IN {job.name} ({i}/{len(jobs)})\n")
                print(job.debug_str)
                yn = input("\nPROCEED? (yN)\n")
                if yn in ["Y", "y", "yes"]:
                    print(f"\nDOING {job.name}...")
                    job.do()
                    print("DONE!\n")
                else:
                    print('BYE!\n')
            else:
                job.do()
            i = i + 1


class SinkNodeConfig:
    def __init__(self, config: dict):
        self.config_label = config['config_label']
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
        self.config_label = config['config_label']
        self.pubkey = config['pubkey']
        self.host = config['host']
        self.capacity = int(config['capacity'])
        self.num_channels = int(config['num_channels'])
        self.base_fee = int(config['base_fee'])
        self.fee_ppm = int(config['fee_ppm'])
        self.cltv_delta = int(config['cltv_delta'])
        self.min_htlc_sat = int(config['min_htlc_sat'])
        self.swap_method = config['swap_method']
        self.min_local_balance_ratio = float(config['min_local_balance_ratio'])
        self.max_local_balance_ratio = float(config['max_local_balance_ratio'])
        self.loop_out_backoff = float(config['loop_out_backoff'])
        self.loop_out_retries = int(config['loop_out_retries'])
        self.max_account_balance = int(config['max_account_balance'])
        self.mempool_fee_rec = config['mempool_fee_rec']
        self.mempool_fee_factor = float(config['mempool_fee_factor'])
        self.max_sat_per_vbyte = int(config['max_sat_per_vbyte'])
        self.max_account_onchain_fee = int(config['max_account_onchain_fee'])


class SinkNodeState:
    def __init__(self, channels: list[ChannelState], config: SinkNodeConfig, sat_per_vbyte: int):
        self.channels = channels
        self.sat_per_vbyte = int(sat_per_vbyte)
        self.config = config


class SourceNodeState:
    def __init__(self, channels: list[ChannelState], config: SourceNodeConfig, swap_method,
                 sat_per_vbyte: int, account_balance: int, account_onchain_fee: int):
        self.channels = channels
        self.sat_per_vbyte = int(sat_per_vbyte)
        self.account_balance = int(account_balance)
        self.account_onchain_fee = int(account_onchain_fee)
        self.config = config
        self.swap_method = swap_method


class SinkNodeManager(Manager):
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
                self.channels_to_close.append(chan)

        self.job_list = [
            Job(
                name="OPEN_CHANNEL",
                do=self.open_channel,
                do_when=len(self.state.channels) - len(self.channels_to_close)
                < self.state.config.num_channels,
                debug_str=self.open_channel_debug_msg()
            ),
            Job(
                name="CLOSE_EMPTY_CHANNELS",
                do=self.close_empty_channels,
                do_when=len(self.channels_to_close) > 0,
                debug_str=self.close_empty_channels_debug_msg()
            )
        ]

    def close_empty_channels_debug_msg(self):
        a = []
        i = 1
        for chan in self.channels_to_close:
            a.append(f"CHANNEL ({i}/{len(self.channels_to_close)})")
            a.append(chan.get_debug_str())
            i += 1
        return "\n".join(a)

    def close_empty_channels(self):
        for chan in self.channels_to_close:
            if self.state.config.max_sat_per_vbyte > self.state.sat_per_vbyte:
                if not self.mock:
                    self.node.close_channel(
                        chan.chan_id, self.state.sat_per_vbyte)
            else:
                self.log.notify(
                    f"Avoided opening a channel to {self.channel_template.node_pubkey}")

    def open_channel_debug_msg(self):
        return self.channel_template.get_debug_str()

    def open_channel(self):
        if self.state.config.max_sat_per_vbyte > self.state.sat_per_vbyte:
            self.log.info(
                f"Opening channel to {self.channel_template.node_pubkey}")
            if not self.mock:
                self.node.open_channel(self.channel_template)
        else:
            self.log.notify(
                f"Avoided opening a channel to {self.channel_template.node_pubkey}")


class SourceNodeManager(Manager):
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
            if float(chan.local_balance / chan.capacity) > self.state.config.max_local_balance_ratio and not chan.pending:
                self.channels_to_drain.append(chan)

        self.job_list = [
            Job(
                name="OPEN_CHANNEL",
                do=self.open_channel,
                do_when=len(
                    self.state.channels) < self.state.config.num_channels,
                debug_str=self.open_channel_debug_msg()
            ),
            Job(
                name="DRAIN_CHANNELS",
                do=self.drain_channels,
                do_when=len(self.channels_to_drain) > 0,
                debug_str=self.drain_channels_debug_msg()
            ),
            Job(
                name="ACCOUNT_SEND_ONCHAIN",
                do=self.account_send_onchain,
                do_when=self.state.config.max_account_balance < self.state.account_balance,
                debug_str=self.account_send_onchain_debug_msg()
            )
        ]

    def open_channel_debug_msg(self):
        return self.channel_template.get_debug_str()

    def open_channel(self):
        if self.state.config.max_sat_per_vbyte > self.state.sat_per_vbyte:
            self.log.info(
                f"Opening channel to {self.channel_template.node_pubkey}")
            if not self.mock:
                self.node.open_channel(self.channel_template)
        else:
            self.log.notify(
                f"Avoided opening a channel to {self.channel_template.node_pubkey}")

    def drain_channels_debug_msg(self):
        a = []
        i = 1
        for chan in self.channels_to_drain:
            invoice_amount = chan.local_balance - \
                int(chan.capacity * self.state.config.min_local_balance_ratio)
            a.append(f"CHANNEL ({i}/{len(self.channels_to_drain)})")
            a.append(
                f"drain_amount_sats_target = {invoice_amount}")
            a.append(
                f"min_local_balance_ratio = {self.state.config.min_local_balance_ratio}")
            a.append(
                f"max_local_balance_ratio = {self.state.config.max_local_balance_ratio}")
            a.append(
                f"loop_out_backoff = {self.state.config.loop_out_backoff}")
            a.append(
                f"loop_out_retries = {self.state.config.loop_out_retries}")
            a.append(chan.get_debug_str())
            i += 1
        return "\n".join(a)

    def drain_channels(self):
        if self.mock:
            return
        for chan in self.channels_to_drain:
            for i in range(self.state.config.loop_out_retries):
                invoice_amount = (chan.local_balance - int(chan.capacity *
                                                           self.state.config.min_local_balance_ratio)) * (self.state.config.loop_out_backoff ** i)
                bolt11_invoice = self.state.swap_method.get_lightning_invoice(
                    invoice_amount)
                payment_response = self.node.pay_invoice(
                    invoice_string=bolt11_invoice, outgoing_chan_id=chan.chan_id)
                if not payment_response.payment_error:
                    break
                elif "no_route" in payment_response.payment_error:
                    self.log.info("No route.")
                else:  # no break
                    self.log.info("error no routes")

    def account_send_onchain_debug_msg(self):
        a = [f"amount_sats = {self.state.account_balance}",
             f"sat_per_vbyte = {self.state.sat_per_vbyte}",
             f"onchain_fee = {self.state.account_onchain_fee}",
             f"max_onchain_fee = {self.state.config.max_account_onchain_fee}"]
        return "\n".join(a)

    def account_send_onchain(self):
        if self.mock:
            return
        if self.state.account_onchain_fee > self.state.config.max_account_onchain_fee:
            self.log.notify(
                f"Avoided sending {self.state.account_balance} sats from {self.state.config.swap_method}. \
                        Max fee: {self.state.config.max_account_onchain_fee} Current fee: {self.state.account_onchain_fee}")
            return
        self.state.swap_method.send_onchain(
            self.state.account_balance, self.state.sat_per_vbyte)
