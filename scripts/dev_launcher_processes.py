#!/usr/bin/env python3
"""
Process management utilities for dev launcher.
Provides real-time log streaming and enhanced process monitoring.
"""

import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from scripts.dev_launcher_config import setup_environment_variables, setup_frontend_environment


class LogStreamer(threading.Thread):
    """Streams process output in real-time with colored output."""
    
    def __init__(self, process: subprocess.Popen, name: str, 
                 color_code: Optional[str] = None) -> None:
        super().__init__(daemon=True)
        self.process = process
        self.name = name
        self.color_code = color_code or ""
        self.reset_code = "\033[0m" if color_code else ""
        self.running = True
        self.lines_buffer: List[str] = []
        
    def run(self) -> None:
        """Stream output from process."""
        try:
            for line in iter(self.process.stdout.readline, b''):
                if not self.running:
                    break
                if line:
                    self._process_line(line)
        except Exception as e:
            print(f"[{self.name}] Stream error: {e}")
    
    def _process_line(self, line: bytes) -> None:
        """Process a single line of output."""
        decoded_line = line.decode('utf-8', errors='replace').rstrip()
        # Add to buffer for error detection
        self.lines_buffer.append(decoded_line)
        if len(self.lines_buffer) > 100:
            self.lines_buffer.pop(0)
        
        # Print with color and prefix
        print(f"{self.color_code}[{self.name}] {decoded_line}{self.reset_code}")
    
    def stop(self) -> None:
        """Stop streaming."""
        self.running = False
    
    def get_recent_errors(self, lines: int = 20) -> List[str]:
        """Get recent error lines from buffer."""
        error_lines = []
        for line in self.lines_buffer[-lines:]:
            if self._is_error_line(line):
                error_lines.append(line)
        return error_lines
    
    def _is_error_line(self, line: str) -> bool:
        """Check if line contains error indicators."""
        lower_line = line.lower()
        error_keywords = ['error', 'exception', 'traceback', 'failed']
        return any(keyword in lower_line for keyword in error_keywords)


class ProcessMonitor:
    """Enhanced process monitor with real-time logging and better crash detection."""
    
    def __init__(self, name: str, start_func: Callable, restart_delay: int = 5, 
                 max_restarts: int = 3, color_code: Optional[str] = None) -> None:
        self.name = name
        self.start_func = start_func
        self.restart_delay = restart_delay
        self.max_restarts = max_restarts
        self.restart_count = 0
        self.process: Optional[subprocess.Popen] = None
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_restart_time: Optional[datetime] = None
        self.crash_log: List[Dict[str, Any]] = []
        self.log_streamer: Optional[LogStreamer] = None
        self.color_code = color_code
        
    def start(self) -> bool:
        """Start the process and begin monitoring."""
        self.process, self.log_streamer = self.start_func()
        if self.process:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            return True
        return False
    
    def stop(self) -> None:
        """Stop monitoring and terminate the process."""
        self.monitoring = False
        if self.log_streamer:
            self.log_streamer.stop()
        if self.process and self.process.poll() is None:
            self._terminate_process()
    
    def _terminate_process(self) -> None:
        """Terminate the process based on platform."""
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                capture_output=True
            )
        else:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
    
    def _monitor_loop(self) -> None:
        """Enhanced monitoring with better crash detection."""
        consecutive_failures = 0
        
        while self.monitoring:
            if self.process and self.process.poll() is not None:
                if self._handle_process_crash(consecutive_failures):
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
            
            time.sleep(2)  # Check every 2 seconds
    
    def _handle_process_crash(self, consecutive_failures: int) -> bool:
        """Handle process crash and attempt restart."""
        exit_code = self.process.returncode
        crash_time = datetime.now()
        
        # Get recent error messages
        recent_errors = []
        if self.log_streamer:
            recent_errors = self.log_streamer.get_recent_errors()
        
        self._log_crash(crash_time, exit_code, recent_errors)
        
        # Check if we should restart
        if self.restart_count < self.max_restarts:
            return self._attempt_restart(crash_time, consecutive_failures)
        else:
            print(f"❌ {self.name} exceeded maximum restart attempts ({self.max_restarts})")
            self.monitoring = False
            return False
    
    def _log_crash(self, crash_time: datetime, exit_code: int, 
                   recent_errors: List[str]) -> None:
        """Log crash information."""
        self.crash_log.append({
            'time': crash_time,
            'exit_code': exit_code,
            'restart_count': self.restart_count,
            'errors': recent_errors
        })
        
        print(f"\n[WARNING] {self.name} process stopped with exit code {exit_code}")
        if recent_errors:
            print(f"   Recent errors:")
            for error in recent_errors[:5]:
                print(f"     {error}")
    
    def _attempt_restart(self, crash_time: datetime, consecutive_failures: int) -> bool:
        """Attempt to restart the process."""
        # Check for rapid restarts (more than 3 in 1 minute)
        recent_crashes = [c for c in self.crash_log 
                         if (crash_time - c['time']).total_seconds() < 60]
        if len(recent_crashes) >= 3:
            print(f"❌ {self.name} is crashing rapidly. Stopping auto-restart.")
            self.monitoring = False
            return False
        
        print(f"[RESTART] Attempting to restart {self.name} (attempt {self.restart_count + 1}/{self.max_restarts})")
        time.sleep(self.restart_delay)
        
        return self._perform_restart(crash_time, consecutive_failures)
    
    def _perform_restart(self, crash_time: datetime, consecutive_failures: int) -> bool:
        """Perform the actual restart."""
        # Stop old streamer
        if self.log_streamer:
            self.log_streamer.stop()
        
        self.process, self.log_streamer = self.start_func()
        if self.process:
            self.restart_count += 1
            self.last_restart_time = crash_time
            print(f"[OK] {self.name} restarted successfully")
            return True
        else:
            print(f"❌ Failed to restart {self.name} (failure {consecutive_failures + 1})")
            if consecutive_failures >= 1:
                print(f"❌ Multiple restart failures. Stopping {self.name} monitoring.")
                self.monitoring = False
            return False


def create_backend_process(cmd: List[str], env: dict) -> subprocess.Popen:
    """Create backend process with platform-specific settings."""
    if sys.platform == "win32":
        return subprocess.Popen(
            cmd,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
    else:
        return subprocess.Popen(
            cmd,
            env=env,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )


def create_frontend_process(cmd: List[str], cwd: str, env: dict) -> subprocess.Popen:
    """Create frontend process with platform-specific settings."""
    if sys.platform == "win32":
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
    else:
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )


def cleanup_process(process: Optional[subprocess.Popen], 
                   streamer: Optional[LogStreamer]) -> None:
    """Clean up a process and its streamer."""
    if streamer:
        streamer.stop()
    
    if process and process.poll() is None:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True
            )
        else:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass