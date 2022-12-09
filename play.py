import sys
from config import PLAYBOOK, PLAYBOOK_LOG, strategy_map


def main():
    DEFAULTS = PLAYBOOK['DEFAULT']

    PLAYBOOK_LOG.info("Running...")

    for play in PLAYBOOK:
        if play != 'DEFAULT':
            if PLAYBOOK[play]['execute'] == "1":
                strategy = strategy_map[PLAYBOOK[play]['strategy']](strategy_config=PLAYBOOK[play], default_config=DEFAULTS, log=PLAYBOOK_LOG)
                strategy.execute()
                if "--debug" in sys.argv:
                    PLAYBOOK_LOG.info(strategy.dump_state())


if __name__ == "__main__":
    main()
