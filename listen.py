from multiprocessing import Process
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
        if CONFIG[key]['execute'] == "1":
            daemon = monitor_actions_map[key](CONFIG[key], node, log)
            thread_pool.append(Process(target=daemon.mainLoop))
    for process in thread_pool:
        process.start()     

if __name__ == "__main__":
    main()
