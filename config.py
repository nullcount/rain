import configparser
from listeners import FundingListenerConfig, FundingListener, MempoolListenerConfig, MempoolListener, \
    HtlcStreamLoggerConfig, HtlcStreamLogger
from channels import SinkNodeConfig, SinkNodeState, SinkNodeManager, SourceNodeConfig, SourceNodeState, \
    SourceNodeManager
from notify import Logger
from kraken import Kraken
from nicehash import Nicehash
from muun import Muun
from creds import *


class Config:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)


swap_methods = {
    "KRAKEN": {
        'creds': KrakenCreds,
        'operator': Kraken
    },
    "NICEHASH": {
        'creds': NicehashCreds,
        'operator': Nicehash
    },
    "MUUN": {
        'creds': MuunCreds,
        'operator': Muun
    }
}

listen_methods = {
    'HTLC_STREAM_LOGGER': {
        'config': HtlcStreamLoggerConfig,
        'listener': HtlcStreamLogger
    },
    "MEMPOOL_NOTIFY": {
        'config': MempoolListenerConfig,
        'listener': MempoolListener
    },
    "FUNDING_NOTIFY": {
        'config': FundingListenerConfig,
        'listener': FundingListener
    }
}

channel_managers = {
    'SINK': {
        'config': SinkNodeConfig,
        'state': SinkNodeState,
        'operator': SinkNodeManager
    },
    'SOURCE': {
        'config': SourceNodeConfig,
        'state': SourceNodeState,
        'operator': SourceNodeManager
    }
}

CREDS = Config('creds.config').config
LISTEN_CONFIG = Config('listen.config').config
CHANNELS_CONFIG = Config('channels.config').config

tg_creds = TelegramCreds(CREDS['TELEGRAM']['api_token'], CREDS['TELEGRAM']['chat_id'])

PLAY_LOG = Logger("logs/play.log", tg_creds)
LISTEN_LOG = Logger('logs/listen.log', tg_creds)
