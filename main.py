from config import Config
from lnd import Lnd
from kraken import Kraken
from log import get_logger


def main():
    log = get_logger("recharge-kraken-loop")
    log.info("Running...") 

    CONFIG = Config().config
    LOOP_PUB = "021c97a90a411ff2b10dc2a8e32de2f29d2fa49d41bfbb52bd416e460db0747d0d"
    KRAKEN_PUB = "02f1a8c87607f415c8f22c00593002775941dea48869ce23096af27b0cfdcc0b69"

    CHAN_CAP_SATS = 25_000_000 # capacity of LOOP and Kraken channel
    RAIN_AMT_SATS = 16_000_000 # amount to loop-out through Kraken
    MIN_ONCHAIN_BALANCE = 200_000 # maintain at least this much in the onchain wallet

    LOOP_CHAN_CONFIG = {
        'peer_pubkey': LOOP_PUB,
        'local_funding_amount': CHAN_CAP_SATS,
        'sat_per_vbyte': 1,
        'target_conf': 3,
        'min_htlc_sat': 1000
    }

    lnd = Lnd(CONFIG["LND_NODE"], log)
    kraken = Kraken(CONFIG["KRAKEN"], log)
    lnd.get_channels()
    loop_chan = lnd.has_channel_with(LOOP_PUB)
    kraken_chan = lnd.has_channel_with(KRAKEN_PUB)

    if loop_chan:
        if kraken_chan.local_balance >= kraken_chan.capactiy * 0.8:
            log.info("Depositing to Kraken over LN")
    else:
        confirmed = lnd.get_onchain_balance()
        unconfirmed = lnd.get_unconfirmed_balance()
        if confirmed >= CHAN_CAP_SATS + MIN_ONCHAIN_BALANCE:
            lnd.open_channel(LOOP_CHAN_CONFIG)
        if kraken.get_account_balance() >= RAIN_AMT_SATS:
            fee = kraken.get_widthdraw_info(CHAN_CAP_SATS)['fee']
            if fee <= 1000:
                kraken.widthdraw_onchain(RAIN_AMT_SATS)
            else:
                log.info("kraken widthdraw fee ({} sats) larger than expected".format(fee))
        if unconfirmed + confirmed >= CHAN_CAP_SATS + MIN_ONCHAIN_BALANCE:
            log.info("waiting for all or some of {} unconfirmed sats to take action".format(unconfirmed))


if __name__ == "__main__":
    main()
