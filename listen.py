from threading import Thread
from config import LISTEN, CREDS, node_map, listen_map
from notify import Logger


def main():
    DEFAULT = LISTEN['DEFAULT']

    log = Logger("logs/monitor.log", CREDS['TELEGRAM'])
    log.info("Running...")

    node = node_map[DEFAULT['node']](LISTEN[DEFAULT['node']], log)

    thread_pool = []

    for key in LISTEN:
        if key != 'DEFAULT':
            if LISTEN[key]['execute'] == "1":
                daemon = listen_map[key](LISTEN[key], node, log)
                thread_pool.append(Thread(target=daemon.mainLoop))

    for thread in thread_pool:
        thread.start()


if __name__ == "__main__":
    main()
