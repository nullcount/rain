"""
I know I always hate to wait. Like even for a bus or somethin'.
-Bob Dylan
"""
from mempool import Mempool
from config import CREDS, LISTEN_LOG
from time import sleep

ALERTED = False


def wait_for_block_conf(tx_id, num_conf, alert_on_first=True):
    global ALERTED
    mp = Mempool(CREDS['MEMPOOL'], LISTEN_LOG)
    tx_status = mp.check_tx(tx_id)
    if tx_status["confirmed"]:
        conf_block_height = int(tx_status["block_height"])
        tip = int(mp.get_tip_height())
        diff = tip - conf_block_height + 1
        if diff == 1:
            if alert_on_first and not ALERTED:
                LISTEN_LOG.notify("Transaction: {} confirmed!".format(tx_id))
                ALERTED = True
        if diff >= num_conf:
            LISTEN_LOG.notify("Transaction: {} confirmed {} times!".format(tx_id, diff))
            return False
    return True


def main():
    tx_id = "0897a23304b76333a965d974158d538f044c6a62c3bf8864c4078bd75eb38f5d"
    num_conf = 1
    while wait_for_block_conf(tx_id, num_conf):
        print("Still waiting on confirmation")
        sleep(60)
    print("Done waiting.")
    LISTEN_LOG.notify("See you in 10 minutes!")
    sleep(600)
    LISTEN_LOG.notify("It's been 10 minutes")


if __name__ == '__main__':
    main()
