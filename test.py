import unittest
from channels import ChannelState, SinkNodeConfig, SinkNodeState, SinkNodeManager, SourceNodeConfig, SourceNodeState, SourceNodeManager
from swap import SwapMethod

test_sink_config = SinkNodeConfig(
    config={
        'config_label': "test sink node config",
        'pubkey': 'testpubkeyanythingworkscauseitsatest',
        'host': '127.0.0.1:9385',
        'capacity': 100_000_000,
        'num_channels': 3,
        'close_ratio': 0.05,
        'base_fee': 0,
        'fee_ppm': 1000,
        'cltv_delta': 144,
        'min_htlc_sat': 100_000,
        'mempool_fee_rec': 'fastestFee',
        'mempool_fee_factor': 1.0,
        'max_sat_per_vbyte': 100,
    }
)


class TestSinkChannelManager(unittest.TestCase):
    def test_close_empty_channels(self):
        test_sink_state = SinkNodeState(
            channels=[
                ChannelState(
                    chan_id='test1',
                    capacity=100_000_000,
                    local_balance=2_000_000,  # empty channel
                    local_chan_reserve_sat=1_000_000,
                ),
                ChannelState(
                    chan_id='test2',
                    capacity=100_000_000,
                    local_balance=20_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
                ChannelState(
                    chan_id='test3',
                    capacity=100_000_000,
                    local_balance=20_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
                ChannelState(
                    chan_id='test4',
                    capacity=100_000_000,
                    local_balance=20_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
            ],
            sat_per_vbyte=10,
            config=test_sink_config
        )
        jobs = SinkNodeManager(state=test_sink_state,
                               node=None, log=None, mock=True).get_jobs()
        self.assertEqual([job.name for job in jobs], ["CLOSE_EMPTY_CHANNELS"])

    def test_open_channel(self):
        test_sink_state = SinkNodeState(
            channels=[  # not enough channels
                ChannelState(
                    chan_id='test3',
                    capacity=100_000_000,
                    local_balance=20_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
            ],
            sat_per_vbyte=10,
            config=test_sink_config
        )
        jobs = SinkNodeManager(state=test_sink_state,
                               node=None, log=None, mock=True).get_jobs()
        self.assertEqual([job.name for job in jobs], ["OPEN_CHANNEL"])


test_source_config = SourceNodeConfig(
    config={
        'config_label': 'test source node config',
        'pubkey': 'testpubkeyanythingworkscauseitsatest',
        'host': '127.0.0.1:9385',
        'capacity': 100_000_000,
        'num_channels': 1,
        'base_fee': 0,
        'fee_ppm': 1000,
        'cltv_delta': 144,
        'min_htlc_sat': 100_000,
        'swap_method': 'kraken',
        'loop_out_amount': 10_000_000,
        'loop_out_backoff': 0.93,
        'max_account_balance': 50_000_000,
        'mempool_fee_rec': 'fastestFee',
        'mempool_fee_factor': 1.0,
        'max_sat_per_vbyte': 100,
    }
)


class TestSourceChannelManager(unittest.TestCase):
    def test_open_channel(self):
        test_source_state = SourceNodeState(
            channels=[],  # not enough sources
            sat_per_vbyte=10,
            account_balance=0,
            config=test_source_config,
            swap_method=SwapMethod()
        )
        jobs = SourceNodeManager(
            state=test_source_state, node=None, log=None, mock=True).get_jobs()
        self.assertEqual([job.name for job in jobs], ['OPEN_CHANNEL'])

    def test_drain_channels(self):
        test_source_state = SourceNodeState(
            channels=[
                ChannelState(
                    chan_id='test3',
                    capacity=100_000_000,
                    local_balance=20_000_000,  # balance > loop_out_amount
                    local_chan_reserve_sat=1_000_000,
                ),
            ],
            sat_per_vbyte=10,
            account_balance=0,
            config=test_source_config,
            swap_method=SwapMethod()
        )
        jobs = SourceNodeManager(
            state=test_source_state, node=None, log=None, mock=True).get_jobs()
        self.assertEqual([job.name for job in jobs], ['DRAIN_CHANNELS'])

    def test_account_send_onchain(self):
        test_source_state = SourceNodeState(
            channels=[
                ChannelState(
                    chan_id='test3',
                    capacity=100_000_000,
                    local_balance=8_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
            ],
            sat_per_vbyte=10,
            account_balance=50_100_000,  # balance > max_account_balance
            config=test_source_config,
            swap_method=SwapMethod()
        )
        jobs = SourceNodeManager(
            state=test_source_state, node=None, log=None, mock=True).get_jobs()
        self.assertEqual([job.name for job in jobs], ['ACCOUNT_SEND_ONCHAIN'])


if __name__ == '__main__':
    unittest.main()
