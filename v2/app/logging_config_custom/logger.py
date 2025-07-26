import logging
import sys
import uuid
import json
import multiprocessing
import threading
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

# --- Core Components ---

class Log(BaseModel):
    """
    Represents a structured log entry.

    This Pydantic model defines the schema for our JSON logs.
    Pydantic v2 automatically handles the serialization of `uuid.UUID` and `datetime`
    to JSON-compatible strings, so custom serializers or methods are no longer needed.
    """
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_no: Optional[int] = None
    process_name: Optional[str] = None
    thread_name: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class JsonFormatter(logging.Formatter):
    """
    Custom formatter to output log records as a single JSON string.
    
    This formatter assumes the message it receives is already a complete,
    serialized JSON string and simply passes it through. This prevents the
    logger from wrapping our JSON log in another data structure.
    """
    def format(self, record: logging.LogRecord) -> str:
        """
        Returns the record's message directly.
        """
        # The `getMessage()` method is used to retrieve the formatted log message.
        # In our case, it will be the JSON string from `Logger._log`.
        return record.getMessage()


# --- Main Logger Class ---

class Logger:
    """
    A simplified, structured JSON logger for the application.

    This class removes the complex singleton pattern (`__new__`) in favor of creating
    a single, module-level instance. This is a more common and Pythonic approach.
    """

    def __init__(self, service_name: str = "my-app", level: str = "INFO", file_path: Optional[str] = None):
        """
        Initializes and configures the logger instance upon creation.
        """
        self.logger = logging.getLogger(service_name)
        self.configure(level, file_path)

    def configure(self, level: str = "INFO", file_path: Optional[str] = None):
        """
        (Re)configures the logger's level and handlers. This is safe to call multiple times.

        Args:
            level (str): The minimum log level to process (e.g., "DEBUG", "INFO").
            file_path (Optional[str]): If provided, logs will also be written to this file.
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        # Clear any existing handlers to prevent duplicate log entries
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        formatter = JsonFormatter()

        # Set up a handler to print logs to the console
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

        # Set up an optional handler to write logs to a file
        if file_path:
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]], exc_info: bool) -> Log:
        """
        The internal method for creating and dispatching a structured log.
        """
        # We inspect the call stack to find the location where the log was initiated.
        # A depth of 2 steps out of this `_log` method and its public wrapper (e.g., `info`).
        try:
            frame = sys._getframe(2)
            module = frame.f_globals.get('__name__', '')
            function = frame.f_code.co_name
            line_no = frame.f_lineno
        except (ValueError, AttributeError):
            module, function, line_no = "(unknown)", "(unknown)", 0

        # Create the structured log entry using the Pydantic model
        log_entry = Log(
            level=level.upper(),
            message=message,
            module=module,
            function=function,
            line_no=line_no,
            process_name=multiprocessing.current_process().name,
            thread_name=threading.current_thread().name,
            extra=extra or {},
        )

        # Pass the serialized JSON object as the message to the underlying logger
        self.logger.log(
            level=getattr(logging, level.upper()),
            msg=log_entry.model_dump_json(),
            exc_info=exc_info
        )
        return log_entry

    # --- Public Logging Methods ---

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> Log:
        """Logs a message with level INFO."""
        return self._log("INFO", message, extra, exc_info=False)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> Log:
        """Logs a message with level WARNING."""
        return self._log("WARNING", message, extra, exc_info=False)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False) -> Log:
        """Logs a message with level ERROR."""
        return self._log("ERROR", message, extra, exc_info=exc_info)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> Log:
        """Logs a message with level DEBUG."""
        return self._log("DEBUG", message, extra, exc_info=False)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> Log:
        """Logs a message with level CRITICAL."""
        return self._log("CRITICAL", message, extra, exc_info=False)

# --- Module-level Singleton Instance ---

# Create a single instance of the Logger to be imported and used across the application.
logger = Logger()

# --- Example Usage ---
if __name__ == "__main__":
    print("--- Example Log Entries ---")
    
    # Basic logging
    logger.info("User logged in successfully.", extra={"user_id": 123, "ip_address": "192.168.1.1"})
    logger.warning("Disk space is running low.", extra={"free_space_gb": 5})
    
    # Example of reconfiguring the logger
    # logger.configure(level="DEBUG")
    logger.debug("This is a detailed debug message for developers.")
    
    # Example of logging an error with exception info
    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.error("An exception occurred during a calculation.", exc_info=True)
