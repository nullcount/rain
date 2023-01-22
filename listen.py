from threading import Thread
from config import LISTEN_CONFIG, CREDS, LISTEN_LOG, listen_methods
from lnd import Lnd, LndCreds


def main():
    LISTEN_LOG.info("Running...")

    lnd_creds = LndCreds(grpc_host=CREDS['LND']['grpc_host'], tls_cert_path=CREDS['LND']
                         ['tls_cert_path'], macaroon_path=CREDS['LND']['macaroon_path'])
    node = Lnd(lnd_creds, LISTEN_LOG)

    thread_pool = []

    for key in LISTEN_CONFIG:
        if key != 'DEFAULT':
            if LISTEN_CONFIG[key]['execute'] == "1":
                daemon = listen_methods[key]['listener'](
                    config=listen_methods[key]['config'](LISTEN_CONFIG[key]), creds=CREDS, node=node, log=LISTEN_LOG)
                thread_pool.append(Thread(target=daemon.mainLoop))

    for thread in thread_pool:
        thread.start()


if __name__ == "__main__":
    main()
