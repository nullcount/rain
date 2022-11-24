from config import Config, node_map, source_map, notify_map
from lnd import ChannelTemplate
from mempool import Mempool

CREDS = Config('rain.config').config

class FeeMatch:
    def __init__(self, strategy_config, default_config, log):
        self.node = node_map[strategy_config['node']](CREDS[strategy_config['node_config']], log)
        self.notify = notify_map[strategy_config['notify']](CREDS[strategy_config['notify_config']], log)
        self.log = log
        self.match_key = strategy_config['match_key']
        self.premium_factor = strategy_config['premium_factor']
        self.tolerance_factor = strategy_config['tolerance_factor']
        self.cltv_delta = strategy_config['cltv_delta']
        self.base_fee = strategy_config['base_fee']
        self.min_htlc_sat = strategy_config['min_htlc_sat']
        self.max_htlc_ratio = strategy_config['max_htlc_ratio']

        self.channels = self.node.get_channels()

    def exeute(self):
        for chan in self.channels:
            print(chan) 
        
class SinkSource:
    def __init__(self, strategy_config, default_config, log):
        self.notify = notify_map[strategy_config['notify']](CREDS[strategy_config['notify_config']], log)
        self.source = source_map[strategy_config['source']](CREDS[strategy_config['source_config']], log)
        self.node = node_map[strategy_config['node']](CREDS[strategy_config['node_config']], log)
        self.log = log
        self.sink_pub = strategy_config['sink_addr'].split("@")[0]
        self.sink_host = strategy_config['sink_addr'].split("@")[1]
        self.source_pub = strategy_config['source_addr'].split("@")[0]
        self.source_host = strategy_config['source_addr'].split("@")[1]
        self.source_loop_fee = strategy_config['source_loop_fee']
        self.sink_budget = strategy_config['sink_budget']
        self.num_sink_chanels = strategy_config['num_sink_channels']
        self.sink_channel_capacity = self.sink_budget / self.num_sink_chanels
        self.mempool_fee = strategy_config['mempool_fee']
        self.sink_close_ratio = strategy_config['sink_close_ratio']
        self.min_onchain_balance = default_config['min_onchain_balance']

        self.mempool = Mempool(CREDS["MEMPOOL"], self.log)
        self.node.get_channels()
        self.sink_channels = self.node.has_channel_with(self.sink_pub)
        self.source_channels = self.node.has_channel_with(self.source_pub)
        self.confirmed = self.node.get_onchain_balance()
        self.unconfirmed = self.node.get_unconfirmed_balance()
        self.source_balance = self.source.get_account_balance()
        self.source_pending_loop_out = self.source.get_pending_widthdraw_sats()

        self.sink_channel_template = ChannelTemplate(
            sat_per_vbyte=self.mempool.get_reccomended_fee()[self.mempool_fee],
            node_pubkey=self.sink_pub,
            local_funding_amount=self.sink_budget / self.num_sink_channels,
            base_fee=0,
            fee_rate=9999,
            address=self.sink_host,
            min_htlc_sat=1000
        )

    def execute(self):
        sats_in_source_channels = 0
        source_channels_capacity = 0
        for chan in self.source_channels:
            sats_in_source_channles += chan.local_balance
            source_channels_capacity += chan.capacity

        if len(self.sink_channels) < self.num_sink_channels:
            self.log.info(f`Required sink channels not met. Target of {self.num_sink_chanels} channels, but found {len(self.sink_channels)}`)

            if unconfirmed < 0:
                self.log.info(f`Found unconfirmed sent transaction of {abs(unconfirmed)} sats and assuming its a channel open.`)
                self.log.info(f`Waiting for unconfirmed sent transaction...`)
                return 1
            channel_sats_required = self.sink_channel_template.local_funding_amount + self.min_onchain_balance

            if self.confirmed > channel_sats_required:
                self.node.open_channel(self.sink_channel_template)
            else:
                self.log.info(f`Missing required sats to open another channel as specified. Required: {channel_sats_required} sats, but found {self.confirmed}`)
                sats_needed_for_channel = (self.sink_channel_template.local_funding_amount + self.min_onchain_balance) - self.confirmed
                missing_sats = sats_needed_for_channel - self.confirmed
                sats_accounted_for = 0
                actions = [] 
                # are there funds on the way on chain 
                if self.unconfirmed > 0:
                    self.log.info(f`Found {self.unconfirmed} unconfirmed sats`)
                    sats_accounted_for += self.unconfirmed
                # are there funds on the way from source
                if self.source_pending_loop_out:
                    # TODO determine overlap with unconfirmed
                    print('mmmm')
                # are there funds on the source account
                if self.source_balance:
                    sats_accounted_for += self.source_balance
                    actions.append("WIDTHDRAW_FROM_SOURCE")
                    fee = self.source.get_widthdraw_info(kraken_balance)['fee']
                    if fee <= self.source_loop_fee:
                        self.source.widthdraw_onchain(self.source_balance)
                    else:
                        self.log.warning(f`Source withdraw fee higher than expected. Found: {fee} sats Expected: {self.source_loop_fee}`)

                if sats_accounted_for > missing_sats:
                    self.log.info(`Missing sats will arrive on chain`)
                    return 1
                # are there funds in a channel to the source
                sats_accounted_for += sats_in_source_channels
                if sats_accounted_for > missing_sats:
                    self.log.info(f`Found {sats_in_source_channels} sats in local balance of source channels`)
                    self.log.info(f`Notifying the operator to deposit into source accounts`)
                    self.notify.send_message(f`Need {missing_sats} to open required channels for sink/source automation. Found {sats_in_source_channels} availible to {self.source_pub}`)
                    # TODO kraken/nicehash needs to implement LN deposits API
        else:
            # required channels are opened and operational
            # check if the source channels need drained
            if sats_in_source_channels / source_channels_capacity > 0.8:
                self.log.info(f`Source channels are above 50% full`)
                self.log.info(f`Notifying the operator to deposit into source accounts`)
                self.notify.send_message(f`Source channels are getting full, consider making a deposit to free up inbound`)
                # TODO kraken/nicehash needs to implement LN deposits API
            for chan in self.sink_channels:
                if chan.local_balance / chan.capacity < self.sink_close_ratio:
                    self.log.info('tryna close a channel')
                    # TODO initiate a channel 

