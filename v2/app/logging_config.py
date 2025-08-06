
import logging
import sys
import os
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from logging import Handler

# ClickHouse
from app.db.clickhouse_base import ClickHouseDatabase
from app.config import settings

class LogEntry(BaseModel):
    """Pydantic model for a single log entry."""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
    source: str = "backend"
    user_id: Optional[str] = None

class ClickHouseHandler(Handler):
    """A logging handler that writes logs to ClickHouse."""

    def __init__(self, clickhouse_db: ClickHouseDatabase, table_name: str = "logs"):
        super().__init__()
        self.db = clickhouse_db
        self.table_name = table_name

    def emit(self, record):
        try:
            log_entry = self.format(record)
            if isinstance(log_entry, LogEntry):
                self.db.insert_log(log_entry)
        except Exception as e:
            # Handle exceptions during logging, e.g., DB connection errors
            print(f"Failed to log to ClickHouse: {e}", file=sys.stderr)

    def format(self, record) -> Optional[LogEntry]:
        if hasattr(record, 'extra') and 'log_entry' in record.extra:
            return record.extra['log_entry']
        return None

class FrontendStreamHandler(Handler):
    """A logging handler that streams logs to the frontend."""
    
    def emit(self, record):
        # This is a placeholder for the actual implementation
        # that will send logs to the frontend, e.g., via WebSockets.
        try:
            log_entry = self.format(record)
            if isinstance(log_entry, LogEntry):
                # In a real application, this would publish the message to a queue
                # or directly to a WebSocket manager.
                print(f"FRONTEND_LOG: {log_entry.json()}")
        except Exception as e:
            print(f"Failed to stream log to frontend: {e}", file=sys.stderr)

    def format(self, record) -> Optional[LogEntry]:
        if hasattr(record, 'extra') and 'log_entry' in record.extra:
            return record.extra['log_entry']
        return None

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

        # Basic console logger for development and debugging
        self.logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )

        # Intercept standard logging
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]

    def _initialize_services(self):
        """Initializes external logging services like Langfuse and ClickHouse."""
        # ClickHouse
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
            # Add ClickHouse handler
            ch_handler = ClickHouseHandler(self.clickhouse_db, table_name="logs")
            self.logger.add(ch_handler, level="INFO", format=lambda record: record)
        except Exception as e:
            self.logger.error(f"Failed to initialize ClickHouse: {e}")
            self.clickhouse_db = None
        
        # Add Frontend Stream Handler
        frontend_handler = FrontendStreamHandler()
        self.logger.add(frontend_handler, level="INFO", format=lambda record: record)

    def log(self, entry: LogEntry):
        """Logs a structured LogEntry to all configured destinations."""
        self.logger.bind(log_entry=entry).info(entry.event)

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

# Example Usage:
if __name__ == "__main__":
    # This demonstrates how to use the central logger from anywhere in the application.
    
    # Get the logger instance
    log_manager = get_central_logger()

    # Log a simple event
    log_manager.log(LogEntry(
        event="application_startup",
        data={"message": "Application is starting up."},
        user_id="system"
    ))

    log_manager.logger.info("This is a standard info message through Loguru.")
