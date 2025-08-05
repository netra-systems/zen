
import logging
import sys
import json
from loguru import logger
from pydantic import BaseModel
from typing import Optional

class Log(BaseModel):
    level: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_no: Optional[int] = None
    process_name: Optional[str] = None
    thread_name: Optional[str] = None

class Formatter:
    def __init__(self):
        self.padding = 0
        self.json_format = '{{"timestamp":"{{time}}", "level":"{{level}}", "message":"{{message}}", "extra":{{extra}}}}'

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

# Optional: If you want to integrate with standard logging
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
