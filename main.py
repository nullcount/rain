from config import Config
from lnd import Lnd
from kraken import Kraken


def main():
    CONFIG = Config().config

    lnd = Lnd(CONFIG["LND_NODE"])
    kraken = Kraken(CONFIG["KRAKEN"])

    my_pubkey = lnd.get_own_pubkey()
    channels = lnd.get_channels()
    print(channels, my_pubkey)
    # send_response = lnd.pay_invoice(
    #     "lnbcrt500u1p3k4fhlpp5hmpp02r940ul677ew8u2lzftzcp64asahm8dy3tsgxpasccqapaqdqqcqzpgsp5y38y590dq2yay3pq09cz0hpch6tg73s2mwhnxel32le0nw8hdfxs9qyyssqk49p03kzrpfx2kjy0tgzpv923s0m7mvl7wl20ew8sqk494eyw45zfsf3yggemylkz9t7964rer4v4507dj3um8c59m7qlqt7wa0y2lqq4eemlp")
    # if send_response.payment_error:
    #     print(send_response.payment_error)
    # else:
    #     print("Payment Sent.")

    # send_response = lnd.send_onchain()
    # channel_point = lnd.open_channel(500, "02aa18102223332f68b9a3caa8e9c2dd1f614ac5057058e6839d1552f68120cda9",
    #                                  int(1e6), 3, 100, 1, 1)
    # print(channel_point)
    print(lnd.get_channels())
    print(lnd.get_onchain_balance())
    print(kraken.get_onchain_address())


if __name__ == "__main__":
    main()
