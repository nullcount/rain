import sys
from config import CHANNELS_CONFIG, PLAY_LOG, CREDS, channel_managers, swap_methods
from lnd import Lnd, LndCreds
from mempool import Mempool, MempoolCreds
from channels import ChannelState


def main(debug: bool):
    PLAY_LOG.info("Running...")

    lnd_creds = LndCreds(grpc_host=CREDS['LND']['grpc_host'], tls_cert_path=CREDS['LND']
                         ['tls_cert_path'], macaroon_path=CREDS['LND']['macaroon_path'])
    node = Lnd(lnd_creds, PLAY_LOG)

    mempool_creds = MempoolCreds(CREDS['MEMPOOL'])
    mempool = Mempool(mempool_creds, PLAY_LOG)

    for managed_peer in CHANNELS_CONFIG:
        if managed_peer == "DEFAULT":
            continue
        _config = CHANNELS_CONFIG[managed_peer]
        _config['config_label'] = managed_peer
        if _config['execute'] == '1' or _config['execute'].lower() == "true" or _config['execute'].lower() == 'yes':
            strategy = _config['strategy'].upper()

            # calculate sat per vbyte
            mempool_fee_rec = _config['mempool_fee_rec']
            mempool_fee_factor = float(_config['mempool_fee_factor'])
            sat_per_vbyte = int(mempool.get_fee(
            )[mempool_fee_rec]) * mempool_fee_factor

            manager = channel_managers[strategy]

            State = manager['state']
            Config = manager['config']
            Operator = manager['operator']

            # get channels for peer in ChannelState list
            open_chans = []
            lnd_active_chans = node.get_shared_channels(_config['pubkey'])
            lnd_pending_chans = [chan for chan in node.get_pending_channel_opens(
            ) if chan.remote_node_pub == _config['pubkey']]
            for chan in lnd_active_chans:
                open_chans.append(ChannelState(chan_id=chan.chan_id, pending=False, capacity=chan.capacity,
                                  local_balance=chan.local_balance, local_chan_reserve_sat=chan.local_chan_reserve_sat))
            for chan in lnd_pending_chans:
                open_chans.append(ChannelState(chan_id=chan.channel_point, pending=True, capacity=chan.capacity,
                                               local_balance=chan.local_balance, local_chan_reserve_sat=chan.local_chan_reserve_sat))

            if strategy == "SOURCE":
                source_config = Config(_config)
                swap_method_name = source_config.swap_method.upper()
                swap_creds = swap_methods[swap_method_name]['creds'](
                    CREDS[swap_method_name])
                swap_method = swap_methods[swap_method_name]['operator'](
                    swap_creds, PLAY_LOG)
                # get account balance
                account_balance = swap_method.get_account_balance()
                # create source chan state
                source_state = State(channels=open_chans, sat_per_vbyte=sat_per_vbyte,
                                     account_balance=account_balance, config=source_config, swap_method=swap_method)
                # create source chan operator
                source_operator = Operator(
                    state=source_state, node=node, log=PLAY_LOG)
                # execute the jobs
                jobs = source_operator.get_jobs()
                source_operator.execute(jobs, debug=debug)
            elif strategy == "SINK":
                sink_config = Config(_config)
                sink_state = State(
                    channels=open_chans, sat_per_vbyte=sat_per_vbyte, config=sink_config)
                sink_operator = Operator(
                    state=sink_state, node=node, log=PLAY_LOG)
                jobs = sink_operator.get_jobs()
                sink_operator.execute(jobs, debug=debug)


if __name__ == "__main__":
    main(debug="debug" in sys.argv)
