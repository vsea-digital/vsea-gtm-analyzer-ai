import logging
import sys

from pythonjsonlogger.json import JsonFormatter


class Logging:
    _configured = False

    def __init__(self):
        if not Logging._configured:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                JsonFormatter(
                    fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                )
            )
            logging.root.handlers = [handler]
            logging.root.setLevel(logging.INFO)
            Logging._configured = True

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)
