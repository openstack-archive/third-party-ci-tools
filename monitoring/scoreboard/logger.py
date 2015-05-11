import logging


def init(config):
    log_file = config.log_file() or 'scoreboard.log'
    logging.basicConfig(filename=log_file, level=logging.INFO)


def get(name):
    return logging.getLogger(name)