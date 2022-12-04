import unittest
from strategy import SinkSource


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
            }).execute()
        self.assertEqual(jobs, ["EMPTY_SOURCE_CHANNELS", "CLOSE_EMPTY_SINK_CHANNELS"])

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
            }).execute()
        self.assertEqual(jobs, ["WAIT_MONEY_LEAVING"])


if __name__ == '__main__':
    unittest.main()
