import logging


def get_logger(name):
    logging.basicConfig(
        filename='logs/{}.log'.format(name),
        filemode='a',
        format='[%(asctime)s] %(levelname)-8s %(message)s'
    )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    return logger
