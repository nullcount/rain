"""
exports.py
---
Contains mappings of classes which are instances of the same base class
Usage: import the mappings to use the appropriate class from a key
"""

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