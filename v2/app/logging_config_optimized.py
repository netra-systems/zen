"""Optimized logging configuration that replaces the original circular-dependency-prone system."""

import os
import logging
from typing import Optional

# Import the optimized logging system
from app.core.logging_manager import (
    LoggingFactory,
    LoggingConfig,
    LogLevel,
    configure_logging,
    get_logger,
    log_structured,
    shutdown_logging
)


class CentralLogger:
    """Backward-compatible central logger using the optimized system."""
    
    def __init__(self):
        # Get configuration from environment or use defaults
        log_level = os.environ.get("LOG_LEVEL", LogLevel.INFO).upper()
        enable_file_logging = os.environ.get("ENABLE_FILE_LOGGING", "false").lower() == "true"
        enable_clickhouse = os.environ.get("ENABLE_CLICKHOUSE_LOGGING", "false").lower() == "true"
        log_file_path = os.environ.get("LOG_FILE_PATH")
        
        # Configure the optimized logging system
        configure_logging(
            level=log_level,
            enable_file_logging=enable_file_logging,
            enable_clickhouse=enable_clickhouse,
            log_file_path=log_file_path
        )
        
        self._manager = LoggingFactory.get_manager()
        self.logger = get_logger("central")
    
    def get_logger(self, name: Optional[str] = None):
        """Get a logger instance."""
        return get_logger(name)
    
    def log(self, level: str, message: str, **kwargs):
        """Log a message with optional structured data."""
        log_structured(level, message, **kwargs)
    
    async def shutdown(self):
        """Shutdown the logging system."""
        await shutdown_logging()


# Global logger instance for backward compatibility
central_logger = CentralLogger()


def get_central_logger() -> CentralLogger:
    """Get the central logger instance."""
    return central_logger