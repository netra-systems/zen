import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Log(BaseModel):
    """
    Represents a structured log entry.
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

    def to_dict(self):
        """
        Converts the Log object to a dictionary, handling UUID and datetime serialization.
        """
        data = self.model_dump()
        data['request_id'] = str(data['request_id'])
        data['timestamp'] = data['timestamp'].isoformat()
        return data


class Logger:
    """
    A unified logger class for the application.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, service_name: str = "netra-core"):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)


    # Multiple logging streams, e.g. console, file, ClickHouse
    def setup_logging(self, level: str = "INFO", log_file_path: Optional[str] = None):
        """
        Configures the logging for the entire application.
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Console handler
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

        # File handler
        if log_file_path and not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None, exc_info=False):
        """
        Internal log method to create and dispatch logs.
        """
        # Get caller information
        frame = sys._getframe(2)
        module = frame.f_globals['__name__']
        function = frame.f_code.co_name
        line_no = frame.f_lineno

        log_entry = Log(
            level=level,
            message=message,
            module=module,
            function=function,
            line_no=line_no,
            process_name=logging.current_process().name,
            thread_name=logging.current_thread().name,
            extra=extra or {},
        )

        self.logger.log(
            getattr(logging, level.upper()),
            log_entry.model_dump_json(),
            exc_info=exc_info
        )
        return log_entry

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> Log:
        return self._log("INFO", message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> Log:
        return self._log("WARNING", message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info=True) -> Log:
        return self._log("ERROR", message, extra, exc_info=exc_info)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> Log:
        return self._log("DEBUG", message, extra)


# Create a singleton logger instance
logger = Logger()
