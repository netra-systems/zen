import logging
import sys
import os
import json
import warnings
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from logging import Handler
import asyncio

# Suppress the specific Pydantic UserWarning
warnings.filterwarnings("ignore", category=UserWarning, message=".*is not a Python type.*")

# ClickHouse
from app.db.clickhouse_base import ClickHouseDatabase
from app.config import settings
from app.websocket import manager

class LogEntry(BaseModel):
    """Pydantic model for a single log entry."""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
    source: str = "backend"
    user_id: Optional[str] = None

class ClickHouseSink:
    """A Loguru sink that writes logs to ClickHouse."""
    def __init__(self, db: ClickHouseDatabase, table_name: str):
        self.db = db
        self.table_name = table_name

    def write(self, message):
        if not message:
            return
        try:
            log_entry = LogEntry.parse_raw(message)
            self.db.insert_log(log_entry, self.table_name)
        except Exception as e:
            print(f"Failed to log to ClickHouse: {e}", file=sys.stderr)

class FrontendStreamSink:
    """A Loguru sink that streams logs to the frontend."""
    def write(self, message):
        if not message:
            return
        try:
            log_entry = LogEntry.parse_raw(message)
            asyncio.create_task(manager.broadcast(log_entry.json()))
        except Exception as e:
            print(f"Failed to stream log to frontend: {e}", file=sys.stderr)

class CentralLogger:
    def __init__(self):
        self.logger = logger
        self.clickhouse_db = None

        self._configure_loguru()
        self._initialize_services()

    def _configure_loguru(self):
        """Configures Loguru to intercept standard logging and add custom handlers."""
        self.logger.remove()
        log_level = settings.log_level.upper()

        # This filter will be used by the console logger to handle structured logs
        # It serializes the 'log_entry' and puts it in 'pretty_data'
        # then it removes the original 'log_entry' to prevent recursion errors
        def console_structured_log_filter(record):
            if "log_entry" in record["extra"]:
                try:
                    # Use .dict() for pydantic models and json.dumps with default=str
                    # to handle any non-serializable objects within the data.
                    pretty_data = json.dumps(record["extra"]["log_entry"].dict(), indent=2, default=str)
                    record["extra"]["pretty_data"] = f"\n{pretty_data}"
                except Exception as e:
                    record["extra"]["pretty_data"] = f"\nCould not serialize log_entry: {e}"
                # IMPORTANT: remove the original object that causes the recursion
                del record["extra"]["log_entry"]
            else:
                record["extra"]["pretty_data"] = ""
            return True

        def formatter(record):
            if record["level"].name == "ERROR":
                # Red for errors, including traceback
                return "<red>{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}{extra[pretty_data]}\n{exception}</red>"
            
            # Default format for other levels
            return "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}{extra[pretty_data]}</level>"

        # Basic console logger for development and debugging
        self.logger.add(
            sys.stdout,
            level=log_level,
            format=formatter,
            colorize=True,
            filter=console_structured_log_filter
        )

        # Intercept standard logging
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]

    def _initialize_services(self):
        """Initializes external logging services like Langfuse and ClickHouse."""
        # ClickHouse
        if settings.clickhouse_logging.enabled:
            try:
                self.clickhouse_db = ClickHouseDatabase(
                    host=settings.clickhouse_https_dev.host,
                    port=settings.clickhouse_https_dev.port,
                    user=settings.clickhouse_https_dev.user,
                    password=settings.clickhouse_https_dev.password,
                    database=settings.clickhouse_https_dev.database,
                    secure=True
                )
                # Verify connection
                self.clickhouse_db.client.ping()
                self.logger.info("ClickHouse connection verified.")
                # Add ClickHouse sink
                ch_sink = ClickHouseSink(self.clickhouse_db, table_name=settings.clickhouse_logging.default_table)
                self.logger.add(ch_sink, level="INFO", format=self._format_log_entry)
            except Exception as e:
                self.logger.error(f"Failed to initialize ClickHouse: {e}")
                self.clickhouse_db = None
        
        # Add Frontend Stream Sink
        frontend_sink = FrontendStreamSink()
        self.logger.add(frontend_sink, level="INFO", format=self._format_log_entry)

    def _format_log_entry(self, record) -> str:
        if "log_entry" in record["extra"]:
            return record["extra"]["log_entry"].json()
        return ""

    def log(self, entry: LogEntry, level: str = "INFO"):
        """Logs a structured LogEntry to all configured destinations."""
        self.logger.bind(log_entry=entry).log(level, entry.event)

    def get_logger(self, name: Optional[str] = None):
        """Returns a Loguru logger instance, optionally named."""
        return self.logger.patch(lambda record: record.update(name=name) if name else None)

class InterceptHandler(logging.Handler):
    """
    Redirects standard logging messages to Loguru.
    """
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# Instantiate the central logger
central_logger = CentralLogger()

def get_central_logger() -> CentralLogger:
    return central_logger
