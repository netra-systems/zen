"""
Stub implementation for LogStreamer to fix broken imports.
Functionality moved to log_buffer.py and log_filter.py.
"""

import asyncio
import subprocess
import sys
from typing import Optional, Any, Dict
from pathlib import Path
from dev_launcher.log_buffer import LogBuffer
from dev_launcher.log_filter import LogFilter


class Colors:
    """Terminal colors for log output."""
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    WHITE = '\033[97m'


class LogManager:
    """Stub for backward compatibility - use LogBuffer and LogFilter directly."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.buffer = LogBuffer()
        self.filter = LogFilter()
        self.running = False
        self.streamers = {}
    
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
    
    def add_streamer(self, name: str, process: subprocess.Popen, color: str = None) -> 'LogStreamer':
        """
        Add a log streamer for a process.
        
        Args:
            name: Name of the streamer (e.g., "BACKEND", "AUTH") 
            process: The subprocess to stream logs from
            color: Terminal color for output (optional)
            
        Returns:
            LogStreamer instance
        """
        streamer = LogStreamer(name, process=process, color=color)
        self.streamers[name] = streamer
        return streamer


class LogStreamer:
    """Stub for backward compatibility."""
    
    def __init__(self, name: str = "default", log_file: Optional[Path] = None, 
                 process: Optional[subprocess.Popen] = None, color: Optional[str] = None):
        self.name = name
        self.log_file = log_file
        self.process = process
        self.color = color or Colors.WHITE
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
            colored_message = f"{self.color}[{self.name}]{Colors.ENDC} {message}"
            print(colored_message)


def setup_logging(config: Optional[Dict[str, Any]] = None) -> LogManager:
    """Setup logging - returns LogManager instance."""
    return LogManager(config)