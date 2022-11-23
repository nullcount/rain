from config import Config
from notify import Logger
from strategy import SinkSource


def main():
    log = Logger("logs/strategy.log")
    log.info("Running...")

    CONFIG = Config('playbook.config.example').config
    DEFAULTS = CONFIG['DEFAULT']

    strategy_map = {
        'sink-source': SinkSource,
    }

    for key in CONFIG:
        if key != 'DEFAULT':
            strategy = strategy_map[CONFIG[key]['strategy']](CONFIG[key], DEFAULTS, log)
            strategy.execute()


if __name__ == "__main__":
    main()
