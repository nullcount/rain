import argparse
import configparser
from lnd import Lnd
from kraken import Kraken
from nicehash import Nicehash
from strategies import FeeMatch, SinkSource
from listeners import HtlcStreamLogger, TelegramListener
from notify import Logger


class Config:
    def __init__(self, config_file):
        self.parser = argparse.ArgumentParser(description='Execute from config')
        self.parser.add_argument("--config", type=str, default=config_file)
        self.parser.add_argument("--debug", type=bool, default=False)
        args = self.parser.parse_args()
        config_loc = args.config
        self.config = configparser.ConfigParser()
        self.config.read(config_loc)


source_map = {
    "kraken": Kraken,
    "nicehash": Nicehash
}
node_map = {
    "LND": Lnd
}

strategy_map = {
    'sink-source': SinkSource,
    'fee-match': FeeMatch
}

monitor_actions_map = {
    'HTLC_STREAM_LOGGER': HtlcStreamLogger,
    "TELEGRAM_ACTIONS": TelegramListener
}

CREDS = Config('creds.config').config
PLAYBOOK = Config('playbook.config.example').config
LISTEN = Config('listen.config.example').config

LISTEN_LOG = Logger("logs/listen.log", CREDS['TELEGRAM'])
PLAYBOOK_LOG = Logger("logs/play.log", CREDS['TELEGRAM'])
