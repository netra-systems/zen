"""Utilities_2 Tests - Split from test_dev_launcher_errors.py"""

import asyncio
import pytest
import time
import sys
import os
import subprocess
import signal
import requests
import logging
import re
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Pattern
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import tempfile
from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager
from dev_launcher.cache_manager import CacheManager
import socket


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def emit(self, record):
        """Handle log record."""
        if record.levelno >= logging.ERROR:
            message = self.format(record)
            self.error_detector._check_line_for_errors(message, 'launcher', 'log')

    def __init__(self):
        self.launcher: Optional[DevLauncher] = None
        self.config: Optional[LauncherConfig] = None
        self.error_detector = ErrorDetector()
        self.start_time: Optional[float] = None

    def create_test_config(self, **kwargs) -> LauncherConfig:
        """Create test configuration."""
        config = LauncherConfig()
        config.backend_port = kwargs.get('backend_port', 8000)
        config.frontend_port = kwargs.get('frontend_port', 3000) if not kwargs.get('skip_frontend', True) else None
        config.dynamic_ports = False
        config.no_backend_reload = True
        config.no_browser = True
        config.verbose = kwargs.get('verbose', True)  # Enable verbose for error detection
        config.non_interactive = True
        config.startup_mode = kwargs.get('startup_mode', 'minimal')
        config.no_secrets = kwargs.get('no_secrets', True)
        config.parallel_startup = kwargs.get('parallel_startup', True)
        config.project_root = project_root
        return config

        def monitor_launcher():
            # Hook into Python logging
            log_handler = ErrorLogHandler(self)
            root_logger = logging.getLogger()
            root_logger.addHandler(log_handler)
            
            # Monitor until shutdown
            while not self._shutdown_event.is_set():
                time.sleep(0.1)
                
            root_logger.removeHandler(log_handler)

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
