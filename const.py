"""
const.py
---
Constants 
usage: for the things that never change
"""
from box import Box

COIN_SATS = 100_000_000
MILLION = 1_000_000
SAT_MSATS = 1_000

KRAKEN_API_URL = "https://api.kraken.com/"
NICEHASH_API_URL = "https://api2.nicehash.com/"
WOS_API_URL = "https://www.livingroomofsatoshi.com/"

TELEGRAM_API_URL = "https://api.telegram.org/"
MEMPOOL_API_URL = "https://mempool.space/api/v1/"

LOG_ERROR = "ERROR " # pad with space
LOG_INFO = "INFO  " 
LOG_NOTIFY = "NOTIFY"
LOG_INPUT = "INPUT "

LOG_GAP = " " * 4

LOG_TRUSTED_SWAP_SERVICE = Box({
    "api_request": { # A trusted swap service usually has a dedicated method for making requests
        "ok": LOG_GAP.join(["{}", "api_request", "response_code: {}, url: {}, body: {}, response: {}"]),
        "err": LOG_GAP.join(["{}", "api_request", "response_code: {}, url: {}, body: {}, response: {}"]),
    },
    "get_address": {
        "ok": LOG_GAP.join(["{}", "get_address", "trusted_deposit_address: {}"]),
        "err": LOG_GAP.join(["{}", "get_address", "{}"])
    },
    "send_onchain": {
        "ok": LOG_GAP.join(["{}", "send_onchain", "sats: {}, fee: {}"]),
        "err": LOG_GAP.join(["{}", "send_onchain", "{}"])
    },
    "get_balance": {
        "ok": LOG_GAP.join(["{}", "get_balance", "trusted_balance: {}"]),
        "err": LOG_GAP.join(["{}", "get_balance", "{}"])
    },
    "pay_invoice": {
        "ok": LOG_GAP.join(["{}", "pay_invoice", "invoice: {} sats: {}"]),
        "err": LOG_GAP.join(["{}", "pay_invoice", "{}"])
    },
    "get_invoice": {
        "ok": LOG_GAP.join(["{}", "get_invoice", "invoice: {}, sats: {}"]),
        "err": LOG_GAP.join(["{}", "get_invoice", "{}"])
    }, 
     "get_onchain_fee": {
        "ok": LOG_GAP.join(["{}", "get_onchain_fee", "sats: {}, fee: {}"]),
        "err": LOG_GAP.join(["{}", "get_onchain_fee", "{}"])
    },
})

LOG_BITCOIN_LIGHTNING_NODE = Box({
    "open_channel": {
        "ok": LOG_GAP.join(["{}", "open_channel", "request: {}, funding_txid: {}"]),
        "err": LOG_GAP.join(["{}", "open_channel", "{}", "request: {}"])
    },
    "close_channel": {
        "ok": LOG_GAP.join(["{}", "close_channel", "request: {}, closing_txid: {}"]),
        "err": LOG_GAP.join(["{}", "close_channel", "{}"])
    },
    "get_pending_open_channels": {
        "ok": LOG_GAP.join(["{}", "get_pending_open_channels", "request: {}"]),
        "err": LOG_GAP.join(["{}", "get_pending_open_channels", "{}"])
    },
    "get_opened_channels": {
        "ok": LOG_GAP.join(["{}", "get_opened_channels", "request: {}"]),
        "err": LOG_GAP.join(["{}", "get_opened_channels", "{}"])
    },
    "get_invoice": {
        "ok": LOG_GAP.join(["{}", "get_invoice", "sats: {}, invoice: {}"]),
        "err": LOG_GAP.join(["{}", "get_invoice", "{}"])
    },
    "pay_invoice": {
        "ok": LOG_GAP.join(["{}", "pay_invoice", "request: {}, preimage: {}"]),
        "err": LOG_GAP.join(["{}", "pay_invoice", "{}", "request: {}"])
    },
    "get_address": {
        "ok": LOG_GAP.join(["{}", "get_address", "address: {}"]),
        "err": LOG_GAP.join(["{}", "get_address", "{}"])
    }, 
    "send_onchain": {
        "ok": LOG_GAP.join(["{}", "send_onchain", "request: {}, txid: {}"]),
        "err": LOG_GAP.join(["{}", "send_onchain", "{}"])
    },
    "get_unconfirmed_balance": {
        "ok": LOG_GAP.join(["{}", "get_unconfirmed_balance", "unconfirmed_balance_sats: {}"]),
        "err": LOG_GAP.join(["{}", "get_unconfirmed_balance", "{}"])
    },
    "get_confirmed_balance": {
        "ok": LOG_GAP.join(["{}", "get_confirmed_balance", "confirmed_balance_sats: {}"]),
        "err": LOG_GAP.join(["{}", "get_confirmed_balance", "{}"])
    },
    "decode_invoice": {
        "ok": LOG_GAP.join(["{}", "decode_invoice", "invoice: {}, decoded_invoice: {}"]),
        "err": LOG_GAP.join(["{}", "decode_invoice", "{}"])
    },
    "sign_message": {
        "ok": LOG_GAP.join(["{}", "sign_message", "message: {}, signed_message: {}"]),
        "err": LOG_GAP.join(["{}", "sign_message", "{}"])
    },
    "get_pubkey": {
        "ok": LOG_GAP.join(["{}", "get_pubkey", "pubkey: {}"]),
        "err": LOG_GAP.join(["{}", "get_pubkey", "{}"])
    },
    "get_alias": {
        "ok": LOG_GAP.join(["{}", "get_alias", "pubkey: {}, alias: {}"]),
        "err": LOG_GAP.join(["{}", "get_alias", "{}"])
    }
})