import sys
from config import PLAYBOOK, PLAYBOOK_LOG, CREDS, strategy_map, node_map


def main():
    DEFAULTS = PLAYBOOK['DEFAULT']
    node = node_map[DEFAULTS['node']](CREDS[DEFAULTS['node']], PLAYBOOK_LOG)
    PLAYBOOK_LOG.info("Running...")

    for play in PLAYBOOK:
        if play != 'DEFAULT':
            if PLAYBOOK[play]['execute'] == "1":
                strategy = strategy_map[PLAYBOOK[play]['strategy']](strategy_config=PLAYBOOK[play], DEFAULT=DEFAULTS, CREDS=CREDS, node=node, log=PLAYBOOK_LOG)
                strategy.execute()
                if "--debug" in sys.argv:
                    PLAYBOOK_LOG.info(strategy.dump_state())


if __name__ == "__main__":
    main()
