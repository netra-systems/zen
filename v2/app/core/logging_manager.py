"""Optimized logging system with no circular dependencies and improved performance."""

import logging
import sys
import os
import json
import warnings
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from functools import lru_cache

from loguru import logger
from pydantic import BaseModel, Field

# Suppress warnings early
warnings.filterwarnings("ignore", category=UserWarning, message=".*is not a Python type.*")


class LogLevel:
    """Log level constants."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEntry(BaseModel):
    """Structured log entry model."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str
    message: str
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "backend"
    context: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LoggingConfig(BaseModel):
    """Logging configuration model."""
    level: str = LogLevel.INFO
    enable_file_logging: bool = False
    log_file_path: Optional[str] = None
    enable_clickhouse: bool = False
    enable_structured_logging: bool = True
    max_file_size: str = "100MB"
    backup_count: int = 5
    
    class Config:
        use_enum_values = True


class PerformanceLogHandler:
    """High-performance log handler for structured logging."""
    
    def __init__(self, enable_clickhouse: bool = False):
        self._buffer: List[LogEntry] = []
        self._buffer_size = 100
        self._enable_clickhouse = enable_clickhouse
        self._clickhouse_client = None
        self._last_flush = datetime.utcnow()
        self._flush_interval = 30  # seconds
    
    def add_log(self, entry: LogEntry):
        """Add a log entry to the buffer."""
        self._buffer.append(entry)
        
        # Auto-flush if buffer is full or time interval exceeded
        if (len(self._buffer) >= self._buffer_size or 
            (datetime.utcnow() - self._last_flush).seconds >= self._flush_interval):
            asyncio.create_task(self._flush_buffer())
    
    async def _flush_buffer(self):
        """Flush the buffer to external storage."""
        if not self._buffer:
            return
        
        buffer_copy = self._buffer.copy()
        self._buffer.clear()
        self._last_flush = datetime.utcnow()
        
        # Send to ClickHouse if enabled
        if self._enable_clickhouse and self._clickhouse_client:
            try:
                await self._send_to_clickhouse(buffer_copy)
            except Exception as e:
                # Fallback to console logging
                logger.warning(f"Failed to send logs to ClickHouse: {e}")
    
    async def _send_to_clickhouse(self, entries: List[LogEntry]):
        """Send log entries to ClickHouse."""
        # Implementation would depend on ClickHouse async client
        # For now, just a placeholder
        pass
    
    async def flush(self):
        """Force flush all buffered logs."""
        await self._flush_buffer()


class OptimizedLoggingManager:
    """Optimized logging manager with performance improvements and no circular dependencies."""
    
    def __init__(self, config: Optional[LoggingConfig] = None):
        self._config = config or LoggingConfig()
        self._loggers: Dict[str, Any] = {}
        self._performance_handler = PerformanceLogHandler(
            enable_clickhouse=self._config.enable_clickhouse
        )
        self._initialized = False
        
        # Initialize logging system
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up the logging system."""
        if self._initialized:
            return
        
        # Remove default loguru handlers
        logger.remove()
        
        # Add console handler with optimized formatting
        self._add_console_handler()
        
        # Add file handler if enabled
        if self._config.enable_file_logging:
            self._add_file_handler()
        
        # Set up standard library logging interception
        self._setup_stdlib_interception()
        
        self._initialized = True
    
    def _add_console_handler(self):
        """Add optimized console handler."""
        def format_record(record):
            """Custom formatter for better performance."""
            level_colors = {
                "DEBUG": "dim white",
                "INFO": "cyan", 
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold red"
            }
            
            color = level_colors.get(record["level"].name, "white")
            
            # Base format
            format_str = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                f"<{color}>{{level: <8}}</{color}> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                f"<{color}>{{message}}</{color}>"
            )
            
            # Add structured data if present
            if "structured_data" in record["extra"]:
                format_str += "\n<dim>{extra[structured_data]}</dim>"
            
            return format_str + "\n"
        
        logger.add(
            sys.stdout,
            level=self._config.level,
            format=format_record,
            colorize=True,
            filter=self._console_filter
        )
    
    def _console_filter(self, record):
        """Filter function for console output."""
        # Format structured data if present
        if "log_entry" in record["extra"]:
            try:
                structured_data = json.dumps(
                    record["extra"]["log_entry"].dict(),
                    indent=2,
                    default=str
                )
                record["extra"]["structured_data"] = structured_data
                # Remove original to prevent recursion
                del record["extra"]["log_entry"]
            except Exception as e:
                record["extra"]["structured_data"] = f"Could not serialize log entry: {e}"
        
        return True
    
    def _add_file_handler(self):
        """Add file handler for persistent logging."""
        if not self._config.log_file_path:
            # Create default log file path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            self._config.log_file_path = str(log_dir / "netra.log")
        
        logger.add(
            self._config.log_file_path,
            level=self._config.level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=self._config.max_file_size,
            retention=f"{self._config.backup_count} files",
            compression="gz",
            enqueue=True  # Thread-safe
        )
    
    def _setup_stdlib_interception(self):
        """Set up interception of standard library logging."""
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                # Get corresponding Loguru level
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno
                
                # Find caller frame
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1
                
                logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )
        
        # Replace standard logging with interceptor
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        
        # Reduce noise from common libraries
        self._configure_library_loggers()
    
    def _configure_library_loggers(self):
        """Configure logging levels for common libraries."""
        library_configs = {
            "sqlalchemy.engine": logging.WARNING,
            "sqlalchemy.pool": logging.WARNING,
            "urllib3": logging.WARNING,
            "httpx": logging.WARNING,
            "fastapi": logging.INFO,
            "uvicorn.access": logging.WARNING,
        }
        
        for lib_name, level in library_configs.items():
            logging.getLogger(lib_name).setLevel(level)
    
    @lru_cache(maxsize=128)
    def get_logger(self, name: str = None) -> Any:
        """Get a logger instance (cached for performance)."""
        if name is None:
            name = "netra"
        
        if name not in self._loggers:
            # Create context-bound logger
            self._loggers[name] = logger.bind(logger_name=name)
        
        return self._loggers[name]
    
    def log_structured(
        self,
        level: str,
        message: str,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        logger_name: str = "netra"
    ):
        """Log structured data with performance optimization."""
        entry = LogEntry(
            level=level.upper(),
            message=message,
            trace_id=trace_id,
            request_id=request_id,
            user_id=user_id,
            context=context or {}
        )
        
        # Add to performance buffer
        self._performance_handler.add_log(entry)
        
        # Log immediately to console/file
        logger_instance = self.get_logger(logger_name)
        logger_instance.bind(log_entry=entry).log(level.upper(), message)
    
    async def flush_all(self):
        """Flush all buffered logs."""
        await self._performance_handler.flush()
    
    async def shutdown(self):
        """Shutdown the logging system gracefully."""
        await self.flush_all()
        
        # Complete any pending log operations
        logger.stop()


class LoggingFactory:
    """Factory for creating logging instances."""
    
    _instance: Optional[OptimizedLoggingManager] = None
    _config: Optional[LoggingConfig] = None
    
    @classmethod
    def configure(cls, config: LoggingConfig):
        """Configure the logging system."""
        cls._config = config
        cls._instance = None  # Force recreation with new config
    
    @classmethod
    def get_manager(cls) -> OptimizedLoggingManager:
        """Get the logging manager instance (singleton)."""
        if cls._instance is None:
            cls._instance = OptimizedLoggingManager(cls._config)
        return cls._instance
    
    @classmethod
    def get_logger(cls, name: str = None) -> Any:
        """Get a logger instance."""
        return cls.get_manager().get_logger(name)


# Convenience functions for backward compatibility
def get_logger(name: str = None) -> Any:
    """Get a logger instance."""
    return LoggingFactory.get_logger(name)


def configure_logging(
    level: str = LogLevel.INFO,
    enable_file_logging: bool = False,
    enable_clickhouse: bool = False,
    log_file_path: Optional[str] = None
):
    """Configure the logging system with common options."""
    config = LoggingConfig(
        level=level,
        enable_file_logging=enable_file_logging,
        enable_clickhouse=enable_clickhouse,
        log_file_path=log_file_path
    )
    LoggingFactory.configure(config)


def log_structured(
    level: str,
    message: str,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    logger_name: str = "netra"
):
    """Log structured data."""
    LoggingFactory.get_manager().log_structured(
        level, message, trace_id, request_id, user_id, context, logger_name
    )


async def shutdown_logging():
    """Shutdown the logging system."""
    if LoggingFactory._instance:
        await LoggingFactory._instance.shutdown()