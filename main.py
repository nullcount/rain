from os import path
from config import parse_yaml
from lnd import Lnd
from mempool import Mempool

# trusted swap services
from kraken import Kraken
from nicehash import Nicehash
from wos import Wos

def main():
    config = parse_yaml('config.yml' if path.exists('config.yml') else 'config.yaml')
    node = Lnd()
    for _config in config.automated_channels:
        opened = node.get_shared_open_channels(_config.peer_pubkey)
        pending = node.get_shared_pending_channels(_config.peer_pubkey)
        total = len(opened) + len(pending)
        if len(total) < _config.channel_count:
            # try to open a channel
            continue
        if _config.automate_liquidity:
            # create an instance of TrustedSwapService
            trusted_swap_service = globals()[_config.trusted_swap_service]()
            for chan in opened:
                local_balance_ratio = chan.local_balance / chan.capacity
                if local_balance_ratio > _config.max_local_balance_ratio and _config.decrease_local_balance:
                    # try to pay a ln invoice from the swap
                    continue
                if local_balance_ratio < _config.min_local_balance_ratio and _config.increase_local_balance:
                    # try to pay your own ln invoice using the swap's balance
                    continue


if __name__ == "__main__":
    main()
