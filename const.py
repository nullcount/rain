from box import Box

COIN_SATS = 100_000_000
MILLION = 1_000_000
SAT_MSATS = 1_000

MESSAGE_SIZE_MB = 50 * 1024 * 1024

KRAKEN_API_URL = "https://api.kraken.com/"
NICEHASH_API_URL = "https://api2.nicehash.com/"
WOS_API_URL = "https://www.livingroomofsatoshi.com/"

TELEGRAM_API_URL = "https://api.telegram.org/"
MEMPOOL_API_URL = "https://mempool.space/api/v1/"

LOG_ERROR = "ERROR"
LOG_INFO = "INFO " # pad with space

LOG_TRUSTED_SWAP_SERVICE = Box({
    "get_address": {
        "ok": "{}    get_address     \{trusted_deposit_address\: {} \}",
        "err": "{}      {}"
    },
    "send_onchain": {
        "ok": "{}    send_onchain     \{sats\: {}, fee\: {}\}",
        "err": "{}      {}"
    },
    "get_balance": {
        "ok": "{}    get_balance    \{trusted_balance\: {}\}",
        "err": "{}      {}"
    },
    "pay_invoice": {
        "ok": "{}    pay_invoice    \{invoice\: {} sats\: {}\}",
        "err": "{}      {}"
    },
    "get_invoice": {
        "ok": "{}    get_invoice    \{invoice\: {}, sats\: {}\}",
        "err": "{}      {}"
    }, 
     "get_onchain_fee": {
        "ok": "{}    get_onchain_fee    \{sats\: {}, fee\: {}\}",
        "err": "{}      {}"
    },
})
