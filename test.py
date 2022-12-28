import unittest
from strategies import SinkSource


class TestSinkSourceStrategy(unittest.TestCase):

    def test_try_close_empty_sink_channels(self):
        jobs = SinkSource(mock=True, mock_state={
            "sink_budget": 375_000_000,
            "source_budget": 400_000_000,
            "sink_close_ratio": 0.1,
            "source_close_ratio": 0.0,
            "sink_channel_count": 3,
            "sink_channels_local_sats": 100_000_000,
            "source_channel_count": 1,
            "source_account_balance": 0,
            "num_sink_channels": 3,  # enough sink channels
            "num_source_channels": 1,
            "min_onchain_balance": 400_000,
            "confirmed": 100_000_000,
            "unconfirmed": 0,
            "sat_per_vbyte": 1,
            "HAS_EMPTY_SINK_CHANNELS": True,  # has empty sinks
            "max_sat_per_vbyte": 100,
            "source_channels_local_sats": 100_000,
            "sink_channels_capacity": 375_000_000
        }).execute()
        self.assertEqual(jobs, ["TRY_CLOSE_EMPTY_SINK_CHANNELS"])

    def test_try_close_empty_sink_channels_and_drain_source_channels(self):
        jobs = SinkSource(mock=True, mock_state={
            "sink_budget": 375_000_000,
            "source_budget": 400_000_000,
            "sink_close_ratio": 0.1,
            "source_close_ratio": 0.0,
            "sink_channel_count": 3,
            "sink_channels_local_sats": 100_000_000,
            "source_channel_count": 1,
            "source_account_balance": 0,
            "num_sink_channels": 3,  # enough sink channels
            "num_source_channels": 1,
            "min_onchain_balance": 400_000,
            "confirmed": 100_000_000,
            "unconfirmed": 0,
            "sat_per_vbyte": 1,
            "HAS_EMPTY_SINK_CHANNELS": True,  # has empty sinks
            "max_sat_per_vbyte": 100,
            "source_channels_local_sats": 100_000_000,  # has plenty in source channel for loop out
            "sink_channels_capacity": 375_000_000
        }).execute()
        self.assertEqual(jobs, ["TRY_CLOSE_EMPTY_SINK_CHANNELS", "TRY_DRAIN_SOURCE_CHANNEL"])

    def test_try_open_source_channel(self):
        jobs = SinkSource(mock=True, mock_state={
            "sink_budget": 375_000_000,
            "source_budget": 400_000_000,
            "sink_close_ratio": 0.1,
            "source_close_ratio": 0.0,
            "sink_channel_count": 3,
            "sink_channels_local_sats": 100_000_000,
            "source_channel_count": 1,
            "source_account_balance": 0,
            "num_sink_channels": 3,
            "num_source_channels": 0,  # not enough source channels
            "min_onchain_balance": 400_000,
            "confirmed": 500_000_000,  # plenty of sats confirmed
            "unconfirmed": 0,
            "sat_per_vbyte": 1,
            "HAS_EMPTY_SINK_CHANNELS": False,
            "max_sat_per_vbyte": 100,
            "source_channels_local_sats": 100_000_000,
            "sink_channels_capacity": 375_000_000
        }).execute()
        self.assertEqual(jobs, ["TRY_OPEN_SOURCE_CHANNEL"])

    def test_try_open_sink_channel(self):
        jobs = SinkSource(mock=True, mock_state={
            "sink_budget": 375_000_000,
            "source_budget": 400_000_000,
            "sink_close_ratio": 0.1,
            "source_close_ratio": 0.0,
            "sink_channel_count": 3,
            "sink_channels_local_sats": 10_000_000,
            "source_channel_count": 1,
            "source_account_balance": 0,
            "num_sink_channels": 1,  # not enough sink channels
            "num_source_channels": 1,
            "min_onchain_balance": 400_000,
            "confirmed": 200_000_000,  # plenty of confirmed funds for new channel
            "unconfirmed": 0,
            "sat_per_vbyte": 1,
            "max_sat_per_vbyte": 100,
            "HAS_EMPTY_SINK_CHANNELS": False,
            "source_channels_local_sats": 100_000_000,
            "sink_channels_capacity": 375_000_000
        }).execute()
        self.assertEqual(jobs, ["TRY_OPEN_SINK_CHANNEL"])

    def test_try_drain_source_channel(self):
        jobs = SinkSource(mock=True, mock_state={
            "sink_budget": 375_000_000,
            "source_budget": 400_000_000,
            "sink_close_ratio": 0.1,
            "source_close_ratio": 0.0,
            "sink_channel_count": 3,
            "sink_channels_local_sats": 100_000_000,
            "source_channel_count": 1,
            "source_account_balance": 0,
            "num_sink_channels": 2,  # not enough sink channels
            "num_source_channels": 1,
            "min_onchain_balance": 400_000,
            "confirmed": 100_000_000,
            "unconfirmed": 0,
            "sat_per_vbyte": 1,
            "max_sat_per_vbyte": 100,
            "HAS_EMPTY_SINK_CHANNELS": False,
            "source_channels_local_sats": 200_000_000,  # plenty of sats in source channels
            "sink_channels_capacity": 375_000_000
        }).execute()
        self.assertEqual(jobs, ["TRY_DRAIN_SOURCE_CHANNEL"])

    def test_try_harvest_sink_channels(self):
        jobs = SinkSource(mock=True, mock_state={
            "sink_budget": 375_000_000,
            "source_budget": 400_000_000,
            "sink_close_ratio": 0.1,
            "source_close_ratio": 0.0,
            "sink_channel_count": 3,
            "sink_channels_local_sats": 500_000_000,  # sink channels have plenty of sats
            "source_channel_count": 1,
            "source_account_balance": 0,
            "num_sink_channels": 5,  # plenty of sink channels
            "num_source_channels": 0, # not enough source channels
            "min_onchain_balance": 400_000,
            "confirmed": 100_000_000,
            "unconfirmed": 0,
            "sat_per_vbyte": 1,
            "max_sat_per_vbyte": 100,
            "HAS_EMPTY_SINK_CHANNELS": False,
            "source_channels_local_sats": 10_000_000,
            "sink_channels_capacity": 375_000_000
        }).execute()
        self.assertEqual(jobs, ["TRY_HARVEST_SINK_CHANNELS"])

    def test_source_account_send_onchain(self):
        jobs = SinkSource(mock=True, mock_state={
            "sink_budget": 375_000_000,
            "source_budget": 400_000_000,
            "sink_close_ratio": 0.1,
            "source_close_ratio": 0.0,
            "sink_channel_count": 3,
            "sink_channels_local_sats": 10_000_000,
            "source_channel_count": 1,
            "source_account_balance": 125_000_000,  # plenty of sats in account
            "num_sink_channels": 2,  # not enough sink channels
            "num_source_channels": 1,
            "min_onchain_balance": 400_000,
            "confirmed": 100_000_000,  # not enough confirmed
            "unconfirmed": 0,
            "sat_per_vbyte": 1,
            "max_sat_per_vbyte": 100,
            "HAS_EMPTY_SINK_CHANNELS": False,
            "source_channels_local_sats": 100_000_000,
            "sink_channels_capacity": 375_000_000
        }).execute()
        self.assertEqual(jobs, ["SOURCE_ACCOUNT_SEND_ONCHAIN"])


if __name__ == '__main__':
    unittest.main()
