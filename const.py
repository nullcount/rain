from box import Box
# trusted swap services
from kraken import Kraken
from nicehash import Nicehash
from wos import Wos
# bitcoin lightning nodes
from lnd import Lnd 
# admin chat services
from telegram import Telegram
from console import Console

COIN_SATS = 100_000_000
MILLION = 1_000_000
SAT_MSATS = 1_000

MESSAGE_SIZE_MB = 50 * 1024 * 1024

KRAKEN_API_URL = "https://api.kraken.com/"
NICEHASH_API_URL = "https://api2.nicehash.com/"
WOS_API_URL = "https://www.livingroomofsatoshi.com/"

TELEGRAM_API_URL = "https://api.telegram.org/"
MEMPOOL_API_URL = "https://mempool.space/api/v1/"

BITCOIN_LIGHTNING_NODES = Box({
    "lnd": Lnd
})

TRUSTED_SWAP_SERVICES = Box({
    "kraken": Kraken,
    "nicehash": Nicehash,
    "wos": Wos
})

ADMIN_NOTIFY_SERVICES = Box({
    "telegram": Telegram,
    "console": Console
})

LOG_ERROR = "ERROR " # pad with space
LOG_INFO = "INFO  " 
LOG_NOTIFY = "NOTIFY"
LOG_INPUT = "INPUT "

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
