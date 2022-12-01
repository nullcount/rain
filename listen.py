from threading import Thread
from config import Config, node_map
from notify import Logger
from monitor import HtlcStreamLogger

def main():
    CONFIG = Config('monitor.config.example').config
    CREDS = Config('creds.config').config
    DEFAULT = CONFIG['DEFAULT']

    log = Logger("logs/monitor.log", CREDS['TELEGRAM'])
    log.info("Running...")

    node = node_map[DEFAULT['node']](CREDS[DEFAULT['node']], log)

    monitor_actions_map = {
        'HTLC_STREAM_LOGGER': HtlcStreamLogger,
    }

    thread_pool = []

    for key in CONFIG:
        if key != 'DEFAULT':
            if CONFIG[key]['execute'] == "1":
                daemon = monitor_actions_map[key](CONFIG[key], node, log)
              #  daemon.mainLoop()
                thread_pool.append(Thread(target = daemon.mainLoop))
   
    for thread in thread_pool:
        thread.start()     

if __name__ == "__main__":
    main()
