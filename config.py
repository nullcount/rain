import configparser
from lnd import Lnd
from strategies import FeeMatch, SinkSource
from listeners import FundingListener, MempoolListener, HtlcStreamLogger, TelegramListener
from notify import Logger


class Config:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)


class SwapMethod:
    def get_onchain_address(self):
        # returns address string
        raise NotImplementedError

    def send_onchain(self):
        # sends entire account balance to saved onchain address
        raise NotImplementedError

    def get_account_balance(self):
        # returns total balance in sats
        raise NotImplementedError

    def pay_invoice(self, inv):
        # attempts to pay the invoice using account balance
        raise NotImplementedError

    def get_lightning_invoice(self):
        # returns bolt11 invoice string
        raise NotImplementedError

    def estimate_onchain_fee(self):
        # returns the total fee in satoshis
        raise NotImplementedError


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
PLAYBOOK = Config('playbook.config').config
LISTEN = Config('listen.config').config

LISTEN_LOG = Logger("logs/listen.log", CREDS['TELEGRAM'])
PLAYBOOK_LOG = Logger("logs/play.log", CREDS['TELEGRAM'])
RUN_LOG = Logger("logs/run.log", CREDS['TELEGRAM'])
