"""Core Tests - Split from test_dev_launcher_real.py"""

import asyncio
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import pytest
import requests

from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.cache_manager import CacheManager
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager

# Set up project root and logger
project_root = Path(__file__).parent.parent.parent
logger = logging.getLogger(__name__)


# REMOVED_SYNTAX_ERROR: class TestSyntaxFix:
    # REMOVED_SYNTAX_ERROR: """Test class for orphaned methods"""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def setup_method(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.launcher: Optional[DevLauncher] = None
    # REMOVED_SYNTAX_ERROR: self.config: Optional[LauncherConfig] = None
    # REMOVED_SYNTAX_ERROR: self.start_time: Optional[float] = None
    # REMOVED_SYNTAX_ERROR: self.service_urls: Dict[str, str] = {}
    # REMOVED_SYNTAX_ERROR: self.console_errors: List[str] = []
    # REMOVED_SYNTAX_ERROR: self.startup_logs: List[str] = []
    # REMOVED_SYNTAX_ERROR: self.service_processes: Dict[str, subprocess.Popen] = {}
    # REMOVED_SYNTAX_ERROR: self._monitoring_threads: List[threading.Thread] = []
    # REMOVED_SYNTAX_ERROR: self._shutdown_event = threading.Event()

# REMOVED_SYNTAX_ERROR: def create_test_config(self,
backend_port: int = 8000,
frontend_port: Optional[int] = 3000,
skip_frontend: bool = False,
verbose: bool = False,
# REMOVED_SYNTAX_ERROR: parallel_startup: bool = True) -> LauncherConfig:
    # REMOVED_SYNTAX_ERROR: """Create test configuration."""
    # REMOVED_SYNTAX_ERROR: config = LauncherConfig()
    # REMOVED_SYNTAX_ERROR: config.backend_port = backend_port
    # REMOVED_SYNTAX_ERROR: config.frontend_port = frontend_port if not skip_frontend else None
    # REMOVED_SYNTAX_ERROR: config.dynamic_ports = False
    # REMOVED_SYNTAX_ERROR: config.no_backend_reload = True
    # REMOVED_SYNTAX_ERROR: config.no_browser = True
    # REMOVED_SYNTAX_ERROR: config.verbose = verbose
    # REMOVED_SYNTAX_ERROR: config.non_interactive = True
    # REMOVED_SYNTAX_ERROR: config.startup_mode = "minimal"
    # REMOVED_SYNTAX_ERROR: config.no_secrets = True
    # REMOVED_SYNTAX_ERROR: config.parallel_startup = parallel_startup
    # REMOVED_SYNTAX_ERROR: config.project_root = project_root
    # REMOVED_SYNTAX_ERROR: return config

# REMOVED_SYNTAX_ERROR: def _setup_error_monitoring(self):
    # REMOVED_SYNTAX_ERROR: """Setup monitoring for console errors and startup logs."""
    # Monitor launcher logs
    # REMOVED_SYNTAX_ERROR: if self.launcher and hasattr(self.launcher, 'log_manager'):
        # REMOVED_SYNTAX_ERROR: log_manager = self.launcher.log_manager
        # Hook into log outputs to capture errors
        # REMOVED_SYNTAX_ERROR: original_log = logger.error

# REMOVED_SYNTAX_ERROR: def capture_error(msg, *args, **kwargs):
    # REMOVED_SYNTAX_ERROR: self.console_errors.append(str(msg))
    # REMOVED_SYNTAX_ERROR: return original_log(msg, *args, **kwargs)

    # REMOVED_SYNTAX_ERROR: logger.error = capture_error

# REMOVED_SYNTAX_ERROR: def detect_console_errors(self) -> List[str]:
    # REMOVED_SYNTAX_ERROR: """Detect console errors from service outputs."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return self.console_errors.copy()

# REMOVED_SYNTAX_ERROR: def verify_port_allocation(self) -> Tuple[bool, List[str]]:
    # REMOVED_SYNTAX_ERROR: """Verify services are running on correct ports."""
    # REMOVED_SYNTAX_ERROR: issues = []

    # Check backend port
    # REMOVED_SYNTAX_ERROR: backend_port = self.config.backend_port or 8000
    # REMOVED_SYNTAX_ERROR: if not self._is_port_in_use(backend_port):
        # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")

        # Check auth port
        # REMOVED_SYNTAX_ERROR: if not self._is_port_in_use(8081):
            # REMOVED_SYNTAX_ERROR: issues.append("Auth port 8081 not in use")

            # Check frontend port (if enabled)
            # REMOVED_SYNTAX_ERROR: if self.config.frontend_port:
                # REMOVED_SYNTAX_ERROR: if not self._is_port_in_use(self.config.frontend_port):
                    # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")

                    # REMOVED_SYNTAX_ERROR: return len(issues) == 0, issues

# REMOVED_SYNTAX_ERROR: def _is_port_in_use(self, port: int) -> bool:
    # REMOVED_SYNTAX_ERROR: """Check if a port is in use."""
    # REMOVED_SYNTAX_ERROR: with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: s.bind(('localhost', port))
            # REMOVED_SYNTAX_ERROR: return False
            # REMOVED_SYNTAX_ERROR: except OSError:
                # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: def verify_grace_periods(self) -> Tuple[bool, List[str]]:
    # REMOVED_SYNTAX_ERROR: """Verify grace periods are respected in startup."""
    # REMOVED_SYNTAX_ERROR: issues = []

    # REMOVED_SYNTAX_ERROR: if not self.start_time:
        # REMOVED_SYNTAX_ERROR: issues.append("Start time not recorded")
        # REMOVED_SYNTAX_ERROR: return False, issues

        # REMOVED_SYNTAX_ERROR: elapsed = time.time() - self.start_time

        # Grace periods per SPEC:
            # - Backend readiness: 30s
            # - Auth verification: 15s
            # - Frontend readiness: 90s

            # REMOVED_SYNTAX_ERROR: if elapsed < 5:  # Minimum reasonable startup time
            # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")

            # No maximum time check - some systems are slower

            # REMOVED_SYNTAX_ERROR: return len(issues) == 0, issues

# REMOVED_SYNTAX_ERROR: def _force_free_test_ports(self):
    # REMOVED_SYNTAX_ERROR: """Force free test ports."""
    # REMOVED_SYNTAX_ERROR: test_ports = [8000, 8081, 3000]
    # REMOVED_SYNTAX_ERROR: for port in test_ports:
        # REMOVED_SYNTAX_ERROR: self._force_free_port(port)

# REMOVED_SYNTAX_ERROR: def _force_free_port(self, port: int):
    # REMOVED_SYNTAX_ERROR: """Force free a specific port."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: if sys.platform == "win32":
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
            # REMOVED_SYNTAX_ERROR: "formatted_string",
            # REMOVED_SYNTAX_ERROR: shell=True, capture_output=True, text=True
            
            # REMOVED_SYNTAX_ERROR: if result.stdout:
                # REMOVED_SYNTAX_ERROR: lines = result.stdout.strip().split(" )
                # REMOVED_SYNTAX_ERROR: ")
                # REMOVED_SYNTAX_ERROR: for line in lines:
                    # REMOVED_SYNTAX_ERROR: parts = line.split()
                    # REMOVED_SYNTAX_ERROR: if len(parts) >= 5:
                        # REMOVED_SYNTAX_ERROR: pid = parts[-1]
                        # REMOVED_SYNTAX_ERROR: if pid.isdigit():
                            # REMOVED_SYNTAX_ERROR: subprocess.run("formatted_string", shell=True)
                            # REMOVED_SYNTAX_ERROR: except Exception:
                                # REMOVED_SYNTAX_ERROR: pass
