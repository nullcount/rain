from config import Config
from lnd import Lnd
from kraken import Kraken


def main():
    CONFIG = Config().config

    lnd = Lnd(CONFIG["LND_NODE"])
    kraken = Kraken(CONFIG["KRAKEN"])
    """
    # Exchange Drain Strategy
    # WHEN source is full
    pay_req = kraken.get_lightning_invoice()
    send_payment = lnd.pay_invoice(pay_req)
    # wait for confirmation
    node_addr = lnd.get_onchain_address()
    kraken.send_onchain(node_addr)
    # wait for confirmation
    channel_point = lnd.open_channel(500, "02aa18102223332f68b9a3caa8e9c2dd1f614ac5057058e6839d1552f68120cda9",
                                      int(1e6), 3, 100, 1, 1)
    my_pubkey = lnd.get_own_pubkey()
    channels = lnd.get_channels()
    print(lnd.get_onchain_address())
    print(lnd.add_lighting_invoice(1000).payment_request)
    """


if __name__ == "__main__":
    main()
