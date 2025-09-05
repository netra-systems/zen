"""
Stub implementation for LogStreamer to fix broken imports.
Functionality moved to log_buffer.py and log_filter.py.
"""

import asyncio
import sys
from typing import Optional, Any, Dict
from pathlib import Path
from dev_launcher.log_buffer import LogBuffer
from dev_launcher.log_filter import LogFilter


class LogManager:
    """Stub for backward compatibility - use LogBuffer and LogFilter directly."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.buffer = LogBuffer()
        self.filter = LogFilter()
        self.running = False
    
    async def start(self) -> None:
        """Start log streaming."""
        self.running = True
    
    async def stop(self) -> None:
        """Stop log streaming."""
        self.running = False
    
    def write(self, message: str) -> None:
        """Write log message."""
        if self.running:
            print(message, file=sys.stderr)


class LogStreamer:
    """Stub for backward compatibility."""
    
    def __init__(self, name: str = "default", log_file: Optional[Path] = None):
        self.name = name
        self.log_file = log_file
        self.running = False
    
    async def start(self) -> None:
        """Start streaming."""
        self.running = True
    
    async def stop(self) -> None:
        """Stop streaming."""
        self.running = False
    
    def write(self, message: str) -> None:
        """Write message."""
        if self.running:
            print(f"[{self.name}] {message}")


def setup_logging(config: Optional[Dict[str, Any]] = None) -> LogManager:
    """Setup logging - returns LogManager instance."""
    return LogManager(config)