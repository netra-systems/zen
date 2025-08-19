"""
Log filtering system for clean startup output.

Implements smart log filtering based on startup mode as per spec v2.0.
"""

import os
import re
import logging
from typing import Optional, Set, Dict, Any
from enum import Enum


class StartupMode(Enum):
    """Startup output modes."""
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
    
    # Patterns to always hide in minimal mode
    MINIMAL_HIDE_PATTERNS = [
        r"Session middleware config:",
        r"UnifiedToolRegistry initialized",
        r"Response Generator initialized",
        r"Quality Gate Service initialized",
        r"Multiprocessing configured",
        r"Context impl PostgresqlImpl",
        r"Will assume transactional DDL",
        r"Database environment validation passed",
        r"Loading key manager",
        r"Key manager loaded",
        r"REAL connection established",
        r"REAL connection closed",
        r"Registered telemetry for service",
        r"Security headers middleware initialized",
        r"Application startup\.\.\.",
        r"Waiting for application startup",
        r"Started server process",
        r"Using dev user:",
        r"HTTP Request:",
        r"Request: (GET|POST|OPTIONS)",
        r"connection (open|closed)",
        r"WebSocket.*accepted",
        r"Invalid HTTP request received",
        r"Compiled.*in \d+ms",
        r"Ready in \d+ms",
        r"○ Compiling",
        r"Database environment validation",
        r"Application startup complete",
        r"Uvicorn running on",
    ]
    
    # Patterns to condense in standard mode
    STANDARD_CONDENSE_PATTERNS = [
        (r"Creating ClickHouse table.*: (\w+)", "Table: {1}"),
        (r"Successfully ensured table exists: (\w+)", "✓ {1}"),
        (r"Registered agent: (\w+)", "Agent: {1}"),
        (r"Task Task-\d+ added to background manager", "Background task added"),
    ]
    
    # Critical patterns to always show
    CRITICAL_PATTERNS = [
        r"ERROR",
        r"CRITICAL",
        r"Failed",
        r"error while attempting to bind",
        r"Missing.*credential",
        r"not found",
        r"Connection refused",
        r"timeout",
    ]
    
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
        if self.mode == StartupMode.MINIMAL:
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
        message_lower = message.lower()
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False
    
    def _filter_minimal(self, message: str, level: str) -> bool:
        """Filter for minimal mode - only essentials."""
        # Hide DEBUG and most INFO
        if level in ["DEBUG", "INFO"]:
            # Check if it's a key startup message
            if any(keyword in message for keyword in [
                "Started on port",
                "System Ready",
                "All services ready",
                "Backend ready",
                "Frontend ready",
                "Auth service started",
            ]):
                return True
            return False
            
        # Hide specific patterns
        for pattern in self.MINIMAL_HIDE_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return False
                
        # Show WARNING and ERROR
        return level in ["WARNING", "ERROR", "CRITICAL", "SUCCESS"]
    
    def _filter_standard(self, message: str, level: str) -> bool:
        """Filter for standard mode - balanced output."""
        # Hide DEBUG
        if level == "DEBUG":
            return False
            
        # Hide verbose patterns
        for pattern in self.MINIMAL_HIDE_PATTERNS[:10]:  # Use subset
            if re.search(pattern, message, re.IGNORECASE):
                return False
                
        return True
    
    def _condense_message(self, message: str) -> Optional[str]:
        """Condense repetitive messages in standard mode."""
        for pattern, replacement in self.STANDARD_CONDENSE_PATTERNS:
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
        message = message.strip()
        
        return message
    
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


import time  # Add this import at the top