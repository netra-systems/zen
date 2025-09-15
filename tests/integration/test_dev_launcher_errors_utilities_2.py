"""Utilities_2 Tests - Split from test_dev_launcher_errors.py"""

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


@pytest.mark.integration
class TestSyntaxFix:
    """Test class for orphaned methods"""

    def emit(self, record):
        """Handle log record."""
        if record.levelno >= logging.ERROR:
            message = self.format(record)
            self.error_detector._check_line_for_errors(message, 'launcher', 'log')

    def setup_method(self):
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
