import configparser
from lnd import Lnd
from strategies import FeeMatch, SinkSource
from listeners import FundingListener, MempoolListener, HtlcStreamLogger, TelegramListener
from notify import Logger


class Config:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)


node_map = {
    "LND": Lnd
}
strategy_map = {
    'sink-source': SinkSource,
    'fee-match': FeeMatch
}
listen_map = {
    'HTLC_STREAM_LOGGER': HtlcStreamLogger,
    "TELEGRAM_ACTIONS": TelegramListener,
    "MEMPOOL_NOTIFY": MempoolListener,
    "FUNDING_NOTIFY": FundingListener
}

CREDS = Config('creds.config').config
PLAYBOOK = Config('playbook.config.example').config
LISTEN = Config('listen.config.example').config

LISTEN_LOG = Logger("logs/listen.log", CREDS['TELEGRAM'])
PLAYBOOK_LOG = Logger("logs/play.log", CREDS['TELEGRAM'])
RUN_LOG = Logger("logs/run.log", CREDS['TELEGRAM'])
