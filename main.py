from config import Config
from lnd import Lnd, Channel
from kraken import Kraken
from notify import Telegram, Logger
from mempool import Mempool


def main():
    log = Logger("logs/recharge-kraken-loop.log")
    log.info("Running...")

    CONFIG = Config().config
    LOOP_PUB = "021c97a90a411ff2b10dc2a8e32de2f29d2fa49d41bfbb52bd416e460db0747d0d"
    KRAKEN_PUB = "02f1a8c87607f415c8f22c00593002775941dea48869ce23096af27b0cfdcc0b69"

    CHAN_CAP_SATS = 100_000_000  # capacity of LOOP and Kraken channel
    MIN_ONCHAIN_BALANCE = 200_000  # maintain at least this much in the onchain wallet    

    lnd = Lnd(CONFIG["LND_NODE"], log)
    kraken = Kraken(CONFIG["KRAKEN"], log)
    mempool = Mempool(CONFIG["MEMPOOL"], log)
    tg = Telegram(CONFIG['TELEGRAM'], log)

    loop_chan_details = Channel(
        sat_per_vbyte=mempool.get_reccommended_fee()['halfHourFee'],
        node_pubkey=LOOP_PUB,
        local_funding_amount=CHAN_CAP_SATS,
        base_fee=0,
        fee_rate=9999,
        address="54.184.88.251:9735",
        min_htlc_sat=1000
    )

    lnd.get_channels()
    loop_chan = lnd.has_channel_with(LOOP_PUB)
    kraken_chan = lnd.has_channel_with(KRAKEN_PUB)
    confirmed = lnd.get_onchain_balance()
    unconfirmed = lnd.get_unconfirmed_balance()
    kraken_balance = kraken.get_account_balance()
    kraken_pending_widthdraw_sats = kraken.get_pending_widthdraw_sats()

    if loop_chan:
        if kraken_chan.local_balance >= kraken_chan.capactiy * 0.8:
    
            tg.send_message("Kraken channel full! Time to make a deposit!")
            log.info("Depositing to Kraken over LN")
            # TODO kraken needs to implement LN deposits
            # need to get the max_htlc for the channel
            #    and loop multiple deposits to kraken below the max_htlc
    else:
        if kraken_pending_widthdraw_sats:
            log.info("waiting for kraken widthdraw(s) to process: {} sats total".format(kraken_pending_widthdraw_sats))
            return 1
        if confirmed >= CHAN_CAP_SATS + MIN_ONCHAIN_BALANCE:
            lnd.open_channel(loop_chan_details)
            return 1
        if kraken_balance >= CHAN_CAP_SATS:
            fee = kraken.get_widthdraw_info(kraken_balance)['fee']
            if fee <= 1000:  # expected flat fee for kraken BTC widthdraws
                kraken.widthdraw_onchain(kraken_balance)
            else:
                log.warning("kraken widthdraw fee ({} sats) larger than expected".format(fee))
            return 1
        if unconfirmed + confirmed >= CHAN_CAP_SATS + MIN_ONCHAIN_BALANCE:
            log.info("waiting for {} unconfirmed sats to take action".format(unconfirmed))
            return 1
        if unconfirmed < 0:
            log.info("waiting for sent transaction {} sats to confirm".format(abs(unconfirmed)))
            return 1


if __name__ == "__main__":
    main()
