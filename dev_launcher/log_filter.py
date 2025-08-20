"""
Log filtering system for clean startup output.

Consolidated log filtering based on startup mode as per spec v2.0.
"""

import os
import re
import time
from typing import Dict, Any, Optional, Set
from enum import Enum

try:
    from .filter_patterns import (
        NOISE_PATTERNS, CRITICAL_PATTERNS, KEY_STARTUP_MESSAGES,
        CRITICAL_STARTUP_FAILURES, COMMON_NOISE_PATTERNS,
        STANDARD_CONDENSE_PATTERNS
    )
except ImportError:
    from filter_patterns import (
        NOISE_PATTERNS, CRITICAL_PATTERNS, KEY_STARTUP_MESSAGES,
        CRITICAL_STARTUP_FAILURES, COMMON_NOISE_PATTERNS,
        STANDARD_CONDENSE_PATTERNS
    )


class StartupMode(Enum):
    """Startup output modes."""
    SILENT = "silent"
    MINIMAL = "minimal"
    STANDARD = "standard"
    VERBOSE = "verbose"


class LogLevel(Enum):
    """Log levels with priority."""
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogFilter:
    """
    Smart log filtering system for clean startup output.
    
    Filters logs based on startup mode and importance.
    """
    
    def __init__(self, mode: StartupMode = StartupMode.MINIMAL):
        """Initialize log filter with specified mode."""
        self.mode = mode
        self.seen_messages: Set[str] = set()
        self.condensed_groups: Dict[str, int] = {}
        
    def should_show(self, message: str, level: str = "INFO") -> bool:
        """Determine if a log message should be shown."""
        # Always show critical messages
        if self._is_critical(message):
            return True
            
        # Mode-specific filtering
        if self.mode == StartupMode.SILENT:
            return self._filter_silent(message, level)
        elif self.mode == StartupMode.MINIMAL:
            return self._filter_minimal(message, level)
        elif self.mode == StartupMode.STANDARD:
            return self._filter_standard(message, level)
        else:  # VERBOSE
            return True
    
    def format_message(self, message: str, level: str = "INFO") -> Optional[str]:
        """Format message based on mode."""
        if not self.should_show(message, level):
            return None
            
        # Apply condensing in standard mode
        if self.mode == StartupMode.STANDARD:
            condensed = self._condense_message(message)
            if condensed:
                return condensed
                
        # Apply minimal formatting
        if self.mode == StartupMode.MINIMAL:
            return self._minimal_format(message)
            
        return message
    
    def _is_critical(self, message: str) -> bool:
        """Check if message is critical and should always be shown."""
        for pattern in CRITICAL_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False
    
    def _filter_silent(self, message: str, level: str) -> bool:
        """Filter for silent mode - errors and critical only."""
        # Only show errors and critical messages
        if level in ["ERROR", "CRITICAL"]:
            return True
        
        # Show critical startup failures
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in CRITICAL_STARTUP_FAILURES)
    
    def _filter_minimal(self, message: str, level: str) -> bool:
        """Filter for minimal mode - only essentials."""
        # Show errors, warnings, and success
        if level in ["ERROR", "CRITICAL", "WARNING", "SUCCESS"]:
            return True
            
        # Hide all noise patterns
        for pattern in NOISE_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return False
        
        # Show key startup messages only
        if level in ["DEBUG", "INFO"]:
            message_lower = message.lower()
            return any(keyword in message_lower for keyword in KEY_STARTUP_MESSAGES)
            
        return False
    
    def _filter_standard(self, message: str, level: str) -> bool:
        """Filter for standard mode - balanced output."""
        # Hide DEBUG
        if level == "DEBUG":
            return False
            
        # Hide common noise patterns
        for pattern in COMMON_NOISE_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return False
                
        return True
    
    def _condense_message(self, message: str) -> Optional[str]:
        """Condense repetitive messages in standard mode."""
        for pattern, replacement in STANDARD_CONDENSE_PATTERNS:
            match = re.search(pattern, message)
            if match:
                condensed = replacement.format(*match.groups())
                
                # Track condensed groups
                group_key = pattern.split("(")[0]
                if group_key not in self.condensed_groups:
                    self.condensed_groups[group_key] = 0
                self.condensed_groups[group_key] += 1
                
                # Show count for repeated items
                if self.condensed_groups[group_key] > 1:
                    condensed += f" ({self.condensed_groups[group_key]})"
                    
                return condensed
                
        return None
    
    def _minimal_format(self, message: str) -> str:
        """Apply minimal formatting to message."""
        # Remove timestamps if present
        message = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\.]?\d* - ', '', message)
        message = re.sub(r'^\d{2}:\d{2}:\d{2} \| \w+ \| ', '', message)
        
        # Shorten long module paths
        message = re.sub(r'app\.\w+\.\w+\.\w+:', '', message)
        message = re.sub(r'app\.\w+\.\w+:', '', message)
        
        # Clean up whitespace
        return message.strip()
    
    def update_mode(self, mode: StartupMode) -> None:
        """Update filter mode dynamically."""
        self.mode = mode
        # Clear seen messages when mode changes
        self.seen_messages.clear()
        self.condensed_groups.clear()
    
    def get_filter_stats(self) -> dict:
        """Get filtering statistics."""
        return {
            "mode": self.mode.value,
            "messages_seen": len(self.seen_messages),
            "condensed_groups": len(self.condensed_groups),
            "total_condensed": sum(self.condensed_groups.values())
        }
    
    @classmethod
    def from_env(cls) -> 'LogFilter':
        """Create log filter from environment variable."""
        mode_str = os.environ.get("NETRA_STARTUP_MODE", "minimal").lower()
        try:
            mode = StartupMode(mode_str)
        except ValueError:
            mode = StartupMode.MINIMAL
        return cls(mode)


class StartupProgressTracker:
    """
    Track and display startup progress in clean format.
    """
    
    def __init__(self, mode: StartupMode = StartupMode.MINIMAL):
        """Initialize progress tracker."""
        self.mode = mode
        self.services: Dict[str, Dict[str, Any]] = {}
        self.start_time = None
        
    def start(self):
        """Mark startup beginning."""
        self.start_time = time.time()
        if self.mode == StartupMode.MINIMAL:
            print("⚡ Starting Netra Apex Development Environment...")
        
    def service_starting(self, name: str):
        """Mark service as starting."""
        self.services[name] = {
            "status": "starting",
            "start_time": time.time(),
            "port": None
        }
        
    def service_started(self, name: str, port: int):
        """Mark service as started."""
        if name in self.services:
            duration = time.time() - self.services[name]["start_time"]
            self.services[name].update({
                "status": "started",
                "port": port,
                "duration": duration
            })
            
            if self.mode == StartupMode.MINIMAL:
                # Single line progress
                print(f"✅ {name:<15} [Port: {port:<5}] {duration:.1f}s")
            
    def service_failed(self, name: str, error: str):
        """Mark service as failed."""
        if name in self.services:
            self.services[name]["status"] = "failed"
            self.services[name]["error"] = error
            
            if self.mode == StartupMode.MINIMAL:
                print(f"❌ {name:<15} Failed: {error}")
    
    def complete(self):
        """Show completion summary."""
        if not self.start_time:
            return
            
        total_time = time.time() - self.start_time
        
        if self.mode == StartupMode.MINIMAL:
            print(f"\n🚀 System Ready ({total_time:.1f}s)")
            
            # Show service URLs
            for name, info in self.services.items():
                if info["status"] == "started" and info.get("port"):
                    url = f"http://localhost:{info['port']}"
                    print(f"   {name:<10} {url}")


# Additional filter presets for different scenarios
class FilterPresets:
    """Predefined filter configurations."""
    
    @staticmethod
    def get_development_filter() -> LogFilter:
        """Get filter optimized for development."""
        return LogFilter(StartupMode.MINIMAL)
    
    @staticmethod
    def get_ci_filter() -> LogFilter:
        """Get filter optimized for CI/CD."""
        return LogFilter(StartupMode.STANDARD)
    
    @staticmethod
    def get_production_filter() -> LogFilter:
        """Get filter optimized for production."""
        return LogFilter(StartupMode.SILENT)
    
    @staticmethod
    def get_debug_filter() -> LogFilter:
        """Get filter for debugging sessions."""
        return LogFilter(StartupMode.VERBOSE)


# Export main classes for backward compatibility
__all__ = [
    'LogFilter', 
    'StartupMode', 
    'LogLevel', 
    'StartupProgressTracker',
    'FilterPresets'
]