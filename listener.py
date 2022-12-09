from threading import Thread
from config import Config, node_map
from notify import Logger
from htlcstream import HtlcStreamLogger
from report import Report
from telegram import TelegramListener

def main():
    CONFIG = Config('listen.config.example').config
    CREDS = Config('creds.config').config
    DEFAULT = CONFIG['DEFAULT']

    log = Logger("logs/monitor.log", CREDS['TELEGRAM'])
    log.info("Running...")

    node = node_map[DEFAULT['node']](CREDS[DEFAULT['node']], log)

    monitor_actions_map = {
        'HTLC_STREAM_LOGGER': HtlcStreamLogger,
        "TELEGRAM_ACTIONS": TelegramListener
    }

    thread_pool = []

    for key in CONFIG:
        if key != 'DEFAULT':
            if CONFIG[key]['execute'] == "1":
                daemon = monitor_actions_map[key](CONFIG[key], node, log)
                thread_pool.append(Thread(target=daemon.mainLoop))

    for thread in thread_pool:
        thread.start()


if __name__ == "__main__":
    main()
