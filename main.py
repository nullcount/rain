from base import BitcoinLightingNode, AdminNotifyService
from const import ADMIN_NOTIFY_SERVICES, BITCOIN_LIGHTNING_NODES, TRUSTED_SWAP_SERVICES
import config
from mempool import Mempool
from result import Result, Ok, Err

def main() -> Result[None, str]:
    cfg = config.get_config()
    node: BitcoinLightingNode = BITCOIN_LIGHTNING_NODES[cfg.lightning_node]()
    notify: AdminNotifyService = ADMIN_NOTIFY_SERVICES[cfg.notify_service]()
    mempool = Mempool()

    open_channels = node.get_opened_channels()
    pend_channels = node.get_pending_channels()
    
    # Maintain managed peers from config.yml
    for peer in cfg.managed_peers:
        peer_conf = cfg.managed_peers[peer]
        
        peer_open = [c for c in open_channels if c.remote_node_pub == peer_conf.peer.pubkey]
        peer_pend = [c for c in pend_channels if c.remote_node_pub == peer_conf.peer.pubkey]
        total_number = len(peer_open) + len(peer_pend)
        
        # Open channels to this peer
        if  peer_conf.policy.num_channels < total_number:
            # TODO: check mempool fees
            node.open_channel() # TODO pass args

        # Create inbound using this peer
        if peer_conf.drain:
            for chan in peer_open:
                local_balance_ratio = chan.local_balance / chan.capacity
                if local_balance_ratio < peer_conf.drain.max:
                    continue
                trust_swap = TRUSTED_SWAP_SERVICES[peer_conf.drain.with_trust_swap]()
                drain_sats = chan.local_balance - (peer_conf.drain.min * chan.capacity)
                trust_invoice = trust_swap.get_invoice(drain_sats)
                node.pay_invoice(trust_invoice)

    # TODO: check all trusted swaps and initiate onchain widthdraws
    return Ok(None)


if __name__ == "__main__":
    main()
