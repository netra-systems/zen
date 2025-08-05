import logging
import sys
import json
from loguru import logger

class Formatter:
    def __init__(self):
        self.padding = 0
        self.json_format = '{{"timestamp":"{{time}}", "level":"{{level}}", "message":"{{message}}", "extra":{{extra}}}}"'

    def format(self, record):
        length = len("{level}".format(**record))
        self.padding = max(self.padding, length)
        record["extra"]["padding"] = self.padding
        return self.json_format + "\n"

def create_logger():
    logger.remove()
    log_format = Formatter()
    logger.add(sys.stdout, format=log_format.format)
    return logger

# Create a logger instance to be used across the application
app_logger = create_logger()