"""Core_1 Tests - Split from test_dev_launcher_errors.py"""

import asyncio
import json
import logging
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty, Queue
from typing import Dict, List, Optional, Pattern, Tuple
from shared.isolated_environment import IsolatedEnvironment

import pytest
import requests

from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.cache_manager import CacheManager
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager

# ErrorDetector module does not exist, creating mock
class ErrorDetector:
    """Mock ErrorDetector for tests since the real module doesn't exist."""
    def _check_line_for_errors(self, message: str, component: str, log_type: str):
        """Mock method for error checking."""
        pass


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def setup_method(self):
        """Setup method called before each test method"""
        self.detected_errors: List[Dict] = []
        self.log_monitors: Dict[str, threading.Thread] = {}
        self.output_queues: Dict[str, Queue] = {}
        self.patterns = None  # ErrorPatterns class doesn't exist
        self._monitoring = False
        self._shutdown_event = threading.Event()

    def start_monitoring(self, launcher: DevLauncher):
        """Start monitoring launcher and service outputs."""
        self._monitoring = True
        self._shutdown_event.clear()
        
        # Monitor launcher logs
        self._start_launcher_monitoring(launcher)
        
        # Monitor service processes
        if hasattr(launcher, 'process_manager'):
            self._start_service_monitoring(launcher.process_manager)

    def _start_launcher_monitoring(self, launcher: DevLauncher):
        """Monitor launcher logs and console output."""
        def monitor_launcher():
            # Hook into Python logging
            log_handler = ErrorLogHandler(self)
            root_logger = logging.getLogger()
            root_logger.addHandler(log_handler)
            
            # Monitor until shutdown
            while not self._shutdown_event.is_set():
                time.sleep(0.1)
                
            root_logger.removeHandler(log_handler)
            
        thread = threading.Thread(target=monitor_launcher, daemon=True)
        thread.start()
        self.log_monitors['launcher'] = thread

    def _start_service_monitoring(self, process_manager: ProcessManager):
        """Monitor service process outputs."""
        for service_name, process in process_manager.processes.items():
            if process and hasattr(process, 'stdout') and hasattr(process, 'stderr'):
                self._start_process_monitoring(service_name, process)

    def _start_process_monitoring(self, service_name: str, process: subprocess.Popen):
        """Monitor individual process output."""
        def monitor_process():
            while not self._shutdown_event.is_set() and process.poll() is None:
                try:
                    # Monitor stdout
                    if process.stdout:
                        line = process.stdout.readline()
                        if line:
                            self._check_line_for_errors(line.decode('utf-8', errors='ignore'), service_name, 'stdout')
                            
                    # Monitor stderr
                    if process.stderr:
                        line = process.stderr.readline()
                        if line:
                            self._check_line_for_errors(line.decode('utf-8', errors='ignore'), service_name, 'stderr')
                            
                except Exception as e:
                    logger.debug(f"Process monitoring error for {service_name}: {e}")
                    
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
        thread = threading.Thread(target=monitor_process, daemon=True)
        thread.start()
        self.log_monitors[service_name] = thread

    def _check_line_for_errors(self, line: str, source: str, stream: str):
        """Check a log line against error patterns."""
        line = line.strip()
        if not line:
            return
            
        # Check against all error patterns
        error_type = self._classify_error(line)
        if error_type:
            error_info = {
                'timestamp': time.time(),
                'source': source,
                'stream': stream,
                'error_type': error_type,
                'message': line,
                'severity': self._determine_severity(error_type, line)
            }
            self.detected_errors.append(error_info)
            logger.warning(f"Error detected in {source}({stream}): {error_type} - {line[:100]}")

    def _classify_error(self, line: str) -> Optional[str]:
        """Classify error type based on patterns."""
        # Check Python exceptions
        for pattern in self.patterns.PYTHON_EXCEPTIONS:
            if pattern.search(line):
                return 'python_exception'
                
        # Check database errors
        for pattern in self.patterns.DATABASE_ERRORS:
            if pattern.search(line):
                return 'database_error'
                
        # Check JavaScript errors
        for pattern in self.patterns.JAVASCRIPT_ERRORS:
            if pattern.search(line):
                return 'javascript_error'
                
        # Check startup errors
        for pattern in self.patterns.STARTUP_ERRORS:
            if pattern.search(line):
                return 'startup_error'
                
        # Check auth errors
        for pattern in self.patterns.AUTH_ERRORS:
            if pattern.search(line):
                return 'auth_error'
                
        # Check network errors
        for pattern in self.patterns.NETWORK_ERRORS:
            if pattern.search(line):
                return 'network_error'
                
        return None

    def _determine_severity(self, error_type: str, line: str) -> str:
        """Determine error severity."""
        if any(keyword in line.lower() for keyword in ['critical', 'fatal', 'emergency']):
            return 'critical'
        elif any(keyword in line.lower() for keyword in ['error', 'exception', 'failed']):
            return 'error'
        elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
            return 'warning'
        else:
            return 'info'

    def stop_monitoring(self):
        """Stop all monitoring."""
        self._monitoring = False
        self._shutdown_event.set()
        
        # Wait for threads to finish
        for thread in self.log_monitors.values():
            if thread.is_alive():
                thread.join(timeout=5)
                
        self.log_monitors.clear()

    def get_errors_by_type(self, error_type: str) -> List[Dict]:
        """Get errors filtered by type."""
        return [error for error in self.detected_errors if error['error_type'] == error_type]

    def get_critical_errors(self) -> List[Dict]:
        """Get critical errors."""
        return [error for error in self.detected_errors if error['severity'] == 'critical']

    def has_startup_failures(self) -> bool:
        """Check if any startup failures were detected."""
        startup_errors = self.get_errors_by_type('startup_error')
        return len(startup_errors) > 0

    def has_database_failures(self) -> bool:
        """Check if database failures were detected."""
        db_errors = self.get_errors_by_type('database_error')
        return len(db_errors) > 0

    def get_error_summary(self) -> Dict:
        """Get summary of all detected errors."""
        summary = {
            'total_errors': len(self.detected_errors),
            'by_type': {},
            'by_severity': {},
            'by_source': {}
        }
        
        for error in self.detected_errors:
            # Count by type
            error_type = error['error_type']
            summary['by_type'][error_type] = summary['by_type'].get(error_type, 0) + 1
            
            # Count by severity
            severity = error['severity']
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            
            # Count by source
            source = error['source']
            summary['by_source'][source] = summary['by_source'].get(source, 0) + 1
            
        return summary

    def __init__(self):
        self.launcher: Optional[DevLauncher] = None
        self.config: Optional[LauncherConfig] = None
        self.error_detector = ErrorDetector()
        self.start_time: Optional[float] = None
