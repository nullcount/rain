from os import path
from config import parse_yaml, log
from lnd import Lnd
from mempool import Mempool

# trusted swap services
from kraken import Kraken
from nicehash import Nicehash
from wos import Wos

def main() -> None:
    ln: Lnd = Lnd()
    all_config = parse_yaml('config.yml' if path.exists('config.yml') else 'config.yaml')
    all_opened = ln.get_open_channels()
    all_pending = ln.get_pending_channels()
    for config in all_config.automated_channels:
        opened = [c for c in all_opened if c.remote_node_pub == config.peer_pubkey]
        pending = [c for c in all_pending if c.remote_node_pub == config.peer_pubkey]
        total = len(opened) + len(pending)
        if total < config.channel_count:
            # try to open a channel
            continue
        if config.automate_liquidity:
            # create an instance of TrustedSwapService
            trusted_swap_service = globals()[config.trusted_swap_service]()
            for chan in opened:
                local_balance_ratio = chan.local_balance / chan.capacity
                if local_balance_ratio > config.max_local_balance_ratio and config.decrease_local_balance:
                    # try to pay a ln invoice from the swap
                    continue
                if local_balance_ratio < config.min_local_balance_ratio and config.increase_local_balance:
                    # try to pay your own ln invoice using the swap's balance
                    continue


if __name__ == "__main__":
    main()
