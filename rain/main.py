#!/usr/bin/env python3

import argparse
import configparser
import sys
import os

import colorama

colorama.init()

from lnd import LND


def debug(message):
    sys.stderr.write(message + "\n")


def main():
    parser = argparse.ArgumentParser(description='Run  a simulation according to config.')
    parser.add_argument("--config", type=str, default="polar.conf")
    args = parser.parse_args()
    config_loc = args.config
    config = configparser.ConfigParser()
    config.read(config_loc)

    # few systems are not utf-8, force so we don't bomb out
    sys.stdout.reconfigure(encoding='utf-8')

    lnd = LND(config["DEFAULT"]["lnd_dir"],
              config["DEFAULT"]["grpc"],
              config["DEFAULT"]["tls_cert_path"],
              config["DEFAULT"]["macaroon_path"])
    if not lnd.valid:
        debug("Could not connect to gRPC endpoint")
        return False

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

    return True


success = main()
if success:
    sys.exit(0)
sys.exit(1)
