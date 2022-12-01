import sys
from config import Config
from notify import Logger
from strategy import SinkSource, FeeMatch


def main():
    CONFIG = Config('playbook.config.example').config
    CREDS = Config('creds.config').config
    DEFAULTS = CONFIG['DEFAULT']

    log = Logger("logs/strategy.log", CREDS['TELEGRAM'])
    log.info("Running...")

    strategy_map = {
        'sink-source': SinkSource,
        'fee-match': FeeMatch
    }

    for key in CONFIG:
        if key != 'DEFAULT':
            if CONFIG[key]['execute'] == "1":
                _strategy = strategy_map[CONFIG[key]['strategy']](CONFIG[key], DEFAULTS, log)
                _strategy.execute()
                if "--debug" in sys.argv:
                    log.info(_strategy.dump_state())


if __name__ == "__main__":
    main()
