# /v2/app/logging_config.py
import logging
import logging.handlers
import sys
from typing import List, Dict, Any

from rich.logging import RichHandler

class MemoryHandler(logging.Handler):
    """A logging handler that stores logs in memory as structured objects."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logs: List[Dict[str, Any]] = []

    def emit(self, record: logging.LogRecord):
        """Captures a log record and stores it as a dictionary."""
        self.logs.append(self._format_record(record))

    def get_logs(self) -> List[Dict[str, Any]]:
        """Returns all captured logs."""
        return self.logs

    def clear(self):
        """Clears all logs from memory."""
        self.logs = []

    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Formats a LogRecord into a dictionary."""
        return {
            "timestamp": record.created,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

# Create a single, global instance of the memory handler
memory_handler = MemoryHandler()

def get_request_logs() -> List[Dict[str, Any]]:
    """Returns the logs captured by the MemoryHandler for the current context."""
    return memory_handler.get_logs()

def setup_logging():
    """
    Sets up a unified logging system for the entire application.

    - Clears any existing handlers on the root logger for a clean setup.
    - Adds a RichHandler for pretty, colorized console output during development.
    - Adds the global MemoryHandler to capture logs for database storage or API responses.
    """
    root_logger = logging.getLogger()
    
    # Clear any previously configured handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Configure RichHandler for beautiful console output
    console_handler = RichHandler(
        rich_tracebacks=True, 
        show_path=False,
        log_time_format="[%X]"
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    
    # Ensure the global memory handler is clear at setup
    memory_handler.clear()

    # Set the root logger's level and add the configured handlers
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(memory_handler)

    # Silence overly verbose libraries to keep logs clean
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# The setup_logging() function is called when this module is imported,
# ensuring logging is configured as soon as the application starts.
setup_logging()
