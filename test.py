import unittest
from strategies import SinkSource


class TestSinkSourceStrategy(unittest.TestCase):
    def test_default(self):
        # if everything is good, we still check to close
        #    empty sink channels
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "sink_budget": 100_000_000,
            "num_sink_channels_target": 2,
            "num_sink_channels": 2,
            "sink_close_ratio": 0.2,
            "min_onchain_balance": 200_000,
            "unconfirmed": 0,
            "confirmed": 140_000_000,
            "source_balance": 0,
            "source_pending_loop_out": 0,
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 70_000_000,
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 0
        }).execute()
        self.assertEqual(jobs, ["CLOSE_EMPTY_SINK_CHANNELS"])

    def test_empty_source_channels(self):
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "sink_budget": 100_000_000,
            "num_sink_channels_target": 2,
            "num_sink_channels": 2,
            "sink_close_ratio": 0.2,
            "min_onchain_balance": 200_000,
            "unconfirmed": 0,
            "confirmed": 140_000_000,
            "source_balance": 0,
            "source_pending_loop_out": 0,
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 80_000_001,  # source channel full
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 0
        }).execute()
        self.assertEqual(jobs, ["EMPTY_SOURCE_CHANNELS"])

    def test_wait_money_leaving(self):
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "sink_budget": 100_000_000,
            "num_sink_channels_target": 2,
            "num_sink_channels": 1,  # not enough channels
            "sink_close_ratio": 0.2,
            "min_onchain_balance": 200_000,
            "unconfirmed": -1,  # funds leaving node
            "confirmed": 140_000_000,
            "source_balance": 0,
            "source_pending_loop_out": 0,
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 80_000_001,  # source channel full
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 0
        }).execute()
        self.assertEqual(jobs, ["WAIT_MONEY_LEAVING"])

    def test_try_open_channel(self):
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "num_sink_channels_target": 2,
            "num_sink_channels": 1,  # does not have enough sink channels
            "sink_close_ratio": 0.2,
            "unconfirmed": 0,  # has no unconfirmed funds
            "sink_budget": 100_000_000,
            "min_onchain_balance": 200_000,
            "confirmed": 140_000_000,       # budget + min_balance < confirmed -> try open channel
            "source_balance": 0,
            "source_pending_loop_out": 0,
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 80_000_001,  # source channel full
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 0
        }).execute()
        self.assertEqual(jobs, ["TRY_OPEN_CHANNEL"])

    def test_wait_money_on_the_way(self):
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "num_sink_channels_target": 1,
            "num_sink_channels": 0,  # does not have enough sink channels
            "sink_close_ratio": 0.2,
            "sink_budget": 100_000_000,
            "min_onchain_balance": 200_000,
            "confirmed": 100_000_000,       # budget + min_balance > confirmed -> cant open channel
            "unconfirmed": 200_001,         # when these funds confirm, we can open a channel -> wait_money_on_the_way
            "source_pending_loop_out": 0,
            "source_balance": 0,
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 80_000_001,  # source channel full
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 0
        }).execute()
        self.assertEqual(jobs, ["WAIT_MONEY_ON_THE_WAY"])

    def test_source_send_onchain(self):
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "num_sink_channels_target": 1,
            "num_sink_channels": 0,  # does not have enough sink channels
            "sink_close_ratio": 0.2,
            "sink_budget": 100_000_000,
            "min_onchain_balance": 200_000,
            "confirmed": 100_000_000,       # budget + min_balance > confirmed -> cant open channel
            "unconfirmed": 200_000,         # even when these funds confirm, we still can't open a channel
            "source_pending_loop_out": 0,   # haven't sent onchain recently
            "source_balance": 200_000,      # by sending funds from the source, we'll have enough to open the channel
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 10_000_000,  # source channel not full
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 0
        }).execute()
        self.assertEqual(jobs, ["SOURCE_SEND_ONCHAIN"])

    def test_has_enough_sats_in_source_channels(self):
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "num_sink_channels_target": 1,
            "num_sink_channels": 0,  # does not have enough sink channels
            "sink_close_ratio": 0.2,
            "sink_budget": 100_000_000,
            "min_onchain_balance": 200_000,
            "confirmed": 100_000_000,       # budget + min_balance > confirmed -> cant open channel
            "unconfirmed": 200_000,         # even when these funds confirm, we still can't open a channel
            "source_pending_loop_out": 0,   # haven't sent onchain recently
            "source_balance": 200_000,      # by sending funds from the source, we'll have enough to open the channel
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 20_000_001,  # source channel full
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 0
        }).execute()
        self.assertEqual(jobs, ["EMPTY_SOURCE_CHANNELS"])

    def test_notify_send_more_sats(self):
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "num_sink_channels_target": 1,
            "num_sink_channels": 0,  # does not have enough sink channels
            "sink_close_ratio": 0.2,
            "sink_budget": 100_000_000,
            "min_onchain_balance": 200_000,
            "confirmed": 100, 
            "unconfirmed": 200_000,
            "source_pending_loop_out": 0,
            "source_balance": 200_000,
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 0,
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 0
        }).execute()
        self.assertEqual(jobs, ["NOTIFY_NEED_MORE_SATS"])

    def test_wait_channel_pending_open(self):
        jobs = SinkSource(mock=True, mock_state={
            "source_loop_fee": 1000,
            "num_sink_channels_target": 1,
            "num_sink_channels": 0,  # does not have enough sink channels
            "sink_close_ratio": 0.2,
            "sink_budget": 100_000_000,
            "min_onchain_balance": 200_000,
            "confirmed": 100, 
            "unconfirmed": 200_000,
            "source_pending_loop_out": 0,
            "source_balance": 200_000,
            "sat_per_vbyte": 23,
            "max_sat_per_vbyte": 30,
            "sats_in_source_channels": 0,
            "source_channels_capacity": 100_000_000,
            "source_channels_local_reserve_sats": 2_000_000,
            "num_pending_sink_channels": 1
        }).execute()
        self.assertEqual(jobs, ["WAIT_CHANNEL_PENDING_OPEN"])


if __name__ == '__main__':
    unittest.main()
