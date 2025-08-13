"""
Real-time log streaming and monitoring for development processes.
"""

import threading
import subprocess
from typing import Optional, List
from collections import deque
import logging

logger = logging.getLogger(__name__)


class LogStreamer(threading.Thread):
    """
    Streams process output in real-time with colored output and error detection.
    
    This class provides real-time streaming of subprocess output with
    buffering for error detection and optional color coding.
    """
    
    def __init__(self, 
                 process: subprocess.Popen, 
                 name: str, 
                 color_code: Optional[str] = None,
                 buffer_size: int = 100):
        """
        Initialize the log streamer.
        
        Args:
            process: The subprocess to stream output from
            name: Name to prefix log lines with
            color_code: ANSI color code for output
            buffer_size: Number of recent lines to keep in buffer
        """
        super().__init__(daemon=True)
        self.process = process
        self.name = name
        self.color_code = color_code or ""
        self.reset_code = "\033[0m" if color_code else ""
        self.running = True
        self.lines_buffer = deque(maxlen=buffer_size)
        self.error_keywords = ['error', 'exception', 'traceback', 'failed', 'fatal', 'critical']
        self.warning_keywords = ['warning', 'warn', 'deprecated']
        self.success_keywords = ['success', 'started', 'running', 'listening', 'ready']
        
    def run(self):
        """Stream output from process."""
        try:
            for line in iter(self.process.stdout.readline, b''):
                if not self.running:
                    break
                    
                if line:
                    decoded_line = self._decode_line(line)
                    if decoded_line:
                        # Add to buffer for error detection
                        self.lines_buffer.append(decoded_line)
                        
                        # Print with color and prefix
                        self._print_line(decoded_line)
                        
        except Exception as e:
            logger.error(f"[{self.name}] Stream error: {e}")
    
    def _decode_line(self, line: bytes) -> Optional[str]:
        """Decode a line of output safely."""
        try:
            return line.decode('utf-8', errors='replace').rstrip()
        except Exception as e:
            logger.error(f"Failed to decode line: {e}")
            return None
    
    def _get_line_emoji(self, line: str) -> str:
        """Get emoji indicator for line type."""
        lower_line = line.lower()
        if any(kw in lower_line for kw in self.error_keywords):
            return "❌ "
        elif any(kw in lower_line for kw in self.warning_keywords):
            return "⚠️  "
        elif any(kw in lower_line for kw in self.success_keywords):
            return "✅ "
        return ""
    
    def _format_content(self, line: str) -> str:
        """Apply syntax highlighting to line content."""
        return self._apply_syntax_colors(line)
    
    def _print_line(self, line: str):
        """Print a line with appropriate formatting."""
        emoji = self._get_line_emoji(line)
        formatted_line = f"{self.color_code}[{self.name}]{self.reset_code} {emoji}{self._format_content(line)}"
        print(formatted_line)
    
    def stop(self):
        """Stop streaming."""
        self.running = False
    
    def get_recent_errors(self, lines: int = 20) -> List[str]:
        """
        Get recent error lines from buffer.
        
        Args:
            lines: Maximum number of recent lines to check
        
        Returns:
            List of error lines found
        """
        error_lines = []
        recent = list(self.lines_buffer)[-lines:] if len(self.lines_buffer) > lines else list(self.lines_buffer)
        
        for line in recent:
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in self.error_keywords):
                error_lines.append(line)
        
        return error_lines
    
    def get_recent_lines(self, count: int = 10) -> List[str]:
        """
        Get recent lines from the buffer.
        
        Args:
            count: Number of lines to retrieve
        
        Returns:
            List of recent lines
        """
        return list(self.lines_buffer)[-count:] if len(self.lines_buffer) > count else list(self.lines_buffer)
    
    def has_errors(self) -> bool:
        """Check if any errors have been detected in recent output."""
        return len(self.get_recent_errors()) > 0
    
    def _apply_syntax_colors(self, text: str) -> str:
        """Apply professional syntax highlighting."""
        # Keywords
        keywords = ['import', 'from', 'class', 'def', 'return', 'if', 'else', 
                   'try', 'except', 'finally', 'with', 'as', 'for', 'while']
        # Numbers
        import re
        result = text
        
        # Highlight strings (green)
        result = re.sub(r'(["\'])([^"\']*)(["\'])', 
                       r'\033[32m\1\2\3\033[0m', result)
        
        # Highlight numbers (cyan)
        result = re.sub(r'\b(\d+)\b', r'\033[36m\1\033[0m', result)
        
        # Highlight keywords (blue)
        for kw in keywords:
            result = re.sub(rf'\b({kw})\b', r'\033[34m\1\033[0m', result)
        
        # Highlight paths (yellow)
        result = re.sub(r'([/\\][\w/\\.-]+)', r'\033[33m\1\033[0m', result)
        
        return result


class LogManager:
    """
    Manages multiple log streamers and provides centralized logging functionality.
    """
    
    def __init__(self):
        """Initialize the log manager."""
        self.streamers: dict[str, LogStreamer] = {}
        self.log_files: dict[str, object] = {}
        
    def add_streamer(self, 
                     name: str, 
                     process: subprocess.Popen,
                     color_code: Optional[str] = None) -> LogStreamer:
        """
        Add a new log streamer.
        
        Args:
            name: Name for the streamer
            process: Process to stream from
            color_code: Optional ANSI color code
        
        Returns:
            The created LogStreamer instance
        """
        streamer = LogStreamer(process, name, color_code)
        streamer.start()
        self.streamers[name] = streamer
        return streamer
    
    def stop_streamer(self, name: str):
        """Stop a specific streamer."""
        if name in self.streamers:
            self.streamers[name].stop()
            del self.streamers[name]
    
    def stop_all(self):
        """Stop all active streamers."""
        for name in list(self.streamers.keys()):
            self.stop_streamer(name)
    
    def get_errors(self, name: str, lines: int = 20) -> List[str]:
        """
        Get recent errors from a specific streamer.
        
        Args:
            name: Name of the streamer
            lines: Number of recent lines to check
        
        Returns:
            List of error lines
        """
        if name in self.streamers:
            return self.streamers[name].get_recent_errors(lines)
        return []
    
    def get_all_errors(self) -> dict[str, List[str]]:
        """
        Get recent errors from all streamers.
        
        Returns:
            Dictionary mapping streamer names to error lists
        """
        errors = {}
        for name, streamer in self.streamers.items():
            streamer_errors = streamer.get_recent_errors()
            if streamer_errors:
                errors[name] = streamer_errors
        return errors


# ANSI color codes for different services
class Colors:
    """ANSI color codes for terminal output."""
    # Service name colors (distinct)
    BACKEND = "\033[96m"   # Bright Cyan
    FRONTEND = "\033[95m"  # Bright Magenta
    
    # Standard syntax colors
    CYAN = "\033[36m"      # Numbers
    MAGENTA = "\033[35m"   # Special
    YELLOW = "\033[33m"    # Paths, warnings
    GREEN = "\033[32m"     # Strings, success
    RED = "\033[31m"       # Errors
    BLUE = "\033[34m"      # Keywords
    WHITE = "\033[37m"     # Default text
    GRAY = "\033[90m"      # Comments, timestamps
    
    # Formatting
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    @staticmethod
    def get_service_color(service_name: str) -> str:
        """Get appropriate color for a service."""
        service_colors = {
            "backend": Colors.BACKEND + Colors.BOLD,
            "frontend": Colors.FRONTEND + Colors.BOLD,
            "database": Colors.YELLOW,
            "redis": Colors.GREEN,
            "clickhouse": Colors.BLUE,
            "postgres": Colors.CYAN,
            "secret": Colors.GRAY,
            "health": Colors.GREEN,
        }
        
        service_lower = service_name.lower()
        for key, color in service_colors.items():
            if key in service_lower:
                return color
        
        return Colors.WHITE  # Default white


def setup_logging(verbose: bool = False):
    """
    Configure logging for the application.
    
    Args:
        verbose: Whether to enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    # Custom formatter with colors
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': Colors.GRAY,
            'INFO': Colors.WHITE,
            'WARNING': Colors.YELLOW,
            'ERROR': Colors.RED,
            'CRITICAL': Colors.RED + Colors.BOLD,
        }
        
        def format(self, record):
            color = self.COLORS.get(record.levelname, Colors.WHITE)
            record.levelname = f"{color}{record.levelname}{Colors.RESET}"
            record.asctime = f"{Colors.GRAY}{self.formatTime(record)}{Colors.RESET}"
            return super().format(record)
    
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    logging.basicConfig(
        level=level,
        handlers=[handler]
    )
    
    # Suppress noisy loggers
    if not verbose:
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('google').setLevel(logging.WARNING)