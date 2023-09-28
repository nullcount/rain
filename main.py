from base import BitcoinLightingNode, AdminNotifyService, OpenChannelRequest
from const import LOG_INFO, LOG_GAP, LOG_ERROR, ADMIN_NOTIFY_SERVICES, BITCOIN_LIGHTNING_NODES, TRUSTED_SWAP_SERVICES
import config
from mempool import Mempool
from result import Result, Ok, Err

def main() -> Result[None, str]:
    cfg = config.get_config()
    node: BitcoinLightingNode = BITCOIN_LIGHTNING_NODES[cfg.lightning_node]()
    notify: AdminNotifyService = ADMIN_NOTIFY_SERVICES[cfg.notify_service]()
    mempool = Mempool()
    fee_estimate = mempool.get_fee()

    open_channels = node.get_opened_channels()
    pend_channels = node.get_pending_channels()
    
    # Maintain managed peers from config.yml
    for peer in cfg.managed_peers:
        peer_conf = cfg.managed_peers[peer]
        
        peer_open = [c for c in open_channels if c.remote_node_pub == peer_conf.peer.pubkey]
        peer_pend = [c for c in pend_channels if c.remote_node_pub == peer_conf.peer.pubkey]
        total_number = len(peer_open) + len(peer_pend)
        
        # check if there are enough channels with peer
        if  peer_conf.policy.num_channels < total_number:
            # check calculated fee is within limit
            vbyte_sats = fee_estimate[peer_conf.onchain_fee.target] * peer_conf.onchain_fee.fee_factor
            if vbyte_sats > peer_conf.onchain_fee.limit_vbyte_sats:
                confirmed_sats = node.get_confirmed_balance()
                unconfirmed_sats = node.get_unconfirmed_balance()
                # check if there are enough sats onchain to fund channel of required capacity
                if confirmed_sats + unconfirmed_sats > peer_conf.policy.channel_capacity:
                    # open the channel
                    node.open_channel(OpenChannelRequest(
                        peer_pubkey=peer_conf.peer.pubkey, 
                        peer_host=peer_conf.peer.host,
                        channel_capacity=peer_conf.policy.channel_capacity, 
                        base_fee=peer_conf.policy.base_fee,
                        ppm_fee=peer_conf.policy.ppm_fee,
                        cltv_delta=peer_conf.policy.cltv_delta,
                        min_htlc_sats=peer_conf.policy.min_htlc_sats,
                        vbyte_sats=vbyte_sats,
                        is_spend_unconfirmed=True,
                        is_unannounced=False, 
                    ))

        # create inbound using this peer
        if peer_conf.drain:
            for chan in peer_open:
                local_balance_ratio = chan.local_balance / chan.capacity
                
                # check if inbound ratio within limits
                if local_balance_ratio < peer_conf.drain.max:
                    config.log(LOG_ERROR, LOG_GAP.join(["rain", peer, f"{chan.id} has local balance ratio of {local_balance_ratio}"]))
                    continue
                
                # do a trusted swap
                trust_swap = TRUSTED_SWAP_SERVICES[peer_conf.drain.with_trust_swap]()
                drain_sats = chan.local_balance - (peer_conf.drain.min * chan.capacity)
                trust_invoice = trust_swap.get_invoice(drain_sats)
                #TODO log what you about to do
                #TODO use PaymentRequest
                node.pay_invoice(trust_invoice)

    # check custodial accounts to widthdraw sats if needed
    for trusted_swap in cfg.trusted_swaps:
        trust_conf = cfg.trusted_swaps[trusted_swap]

        # check custody balance is within limit
        trust_swap = TRUSTED_SWAP_SERVICES[trusted_swap]()
        trusted_balance = trust_swap.get_balance()
        if trusted_balance < trust_conf.limit_custody_sats:
            config.log(LOG_INFO, LOG_GAP.join(["rain", trusted_swap, "balance limit not reached"]))
            continue

        # check widthdraw fee is within limit
        onchain_swap_fee = trust_swap.get_onchain_fee(trusted_balance)
        if onchain_swap_fee > trust_swap.limit_onchain_fee_sats:
            notify.send_message(f"{trusted_swap} widthdraw fee of {onchain_swap_fee} sats is greater than limit {trust_swap.limit_onchain_fee_sats} sats Leaving {trusted_balance} sats in trusted custody with {trusted_swap}")
            config.log(LOG_ERROR, LOG_GAP.join(["rain", trusted_swap, "widthdraw fee limit reached"]))
            continue
        
        # widthdraw all sats in custody
        config.log(LOG_ERROR, LOG_GAP.join(["rain", trusted_swap, f"initiate widthdraw of {trusted_balance}"]))
        trusted_swap.send_onchain(sats=trusted_balance)


    return Ok(None)


if __name__ == "__main__":
    main()
