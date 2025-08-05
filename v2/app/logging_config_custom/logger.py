import logging
import sys
import json
import os
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
        self.log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n{exception}"
        )

    def format(self, record):
        return self.log_format

def create_logger():
    logger.remove()
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    log_format = Formatter()
    
    # Filter out verbose debug messages
    def is_not_verbose(record):
        verbose_patterns = [
            "loaded lazy attr",
            "registered 'bcrypt' handler",
            "Using orjson library for writing JSON byte strings",
            "Looking up time zone info from registry",
        ]
        # Filter out sqlalchemy info messages
        if record["name"] == "sqlalchemy.engine" and record["level"].name == "INFO":
            return False
        return not any(pattern in record["message"] for pattern in verbose_patterns)

    logger.add(sys.stdout, level=log_level, format=log_format.format, filter=is_not_verbose)
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
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)


def setup_logging(config_path='logging_config.json'):
    with open(config_path, 'rt') as f:
        config = json.load(f)
    logging.config.dictConfig(config)

def get_logger(name):
    return logging.getLogger(name)
