"""Utilities Tests - Split from test_dev_launcher_real.py"""

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


class TestSyntaxFix:
    """Test class for orphaned methods"""
    pass

    def setup_method(self):
        pass
        self.launcher: Optional[DevLauncher] = None
        self.config: Optional[LauncherConfig] = None
        self.start_time: Optional[float] = None
        self.service_urls: Dict[str, str] = {}
        self.console_errors: List[str] = []
        self.startup_logs: List[str] = []
        self.service_processes: Dict[str, subprocess.Popen] = {}
        self._monitoring_threads: List[threading.Thread] = []
        self._shutdown_event = threading.Event()

        def create_test_config(self,
backend_port: int = 8000,
frontend_port: Optional[int] = 3000,
skip_frontend: bool = False,
verbose: bool = False,
parallel_startup: bool = True) -> LauncherConfig:
"""Create test configuration."""
config = LauncherConfig()
config.backend_port = backend_port
config.frontend_port = frontend_port if not skip_frontend else None
config.dynamic_ports = False
config.no_backend_reload = True
config.no_browser = True
config.verbose = verbose
config.non_interactive = True
config.startup_mode = "minimal"
config.no_secrets = True
config.parallel_startup = parallel_startup
config.project_root = project_root
return config

def _setup_error_monitoring(self):
    pass
"""Setup monitoring for console errors and startup logs."""
    # Monitor launcher logs
if self.launcher and hasattr(self.launcher, 'log_manager'):
    pass
log_manager = self.launcher.log_manager
        # Hook into log outputs to capture errors
original_log = logger.error

def capture_error(msg, *args, **kwargs):
    pass
self.console_errors.append(str(msg))
return original_log(msg, *args, **kwargs)

logger.error = capture_error

def detect_console_errors(self) -> List[str]:
    pass
"""Detect console errors from service outputs."""
pass
return self.console_errors.copy()

def verify_port_allocation(self) -> Tuple[bool, List[str]]:
    pass
"""Verify services are running on correct ports."""
issues = []

    # Check backend port
backend_port = self.config.backend_port or 8000
if not self._is_port_in_use(backend_port):
    pass
issues.append("")

        # Check auth port
if not self._is_port_in_use(8081):
    pass
issues.append("Auth port 8081 not in use")

            # Check frontend port (if enabled)
if self.config.frontend_port:
    pass
if not self._is_port_in_use(self.config.frontend_port):
    pass
issues.append("")

return len(issues) == 0, issues

def _is_port_in_use(self, port: int) -> bool:
    pass
"""Check if a port is in use."""
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
try:
    pass
s.bind(('localhost', port))
return False
except OSError:
    pass
return True

def verify_grace_periods(self) -> Tuple[bool, List[str]]:
    pass
"""Verify grace periods are respected in startup."""
issues = []

if not self.start_time:
    pass
issues.append("Start time not recorded")
return False, issues

elapsed = time.time() - self.start_time

        # Grace periods per SPEC:
            # - Backend readiness: 30s
            # - Auth verification: 15s
            # - Frontend readiness: 90s

if elapsed < 5:  # Minimum reasonable startup time
issues.append("")

            # No maximum time check - some systems are slower

return len(issues) == 0, issues

def _force_free_test_ports(self):
    pass
"""Force free test ports."""
test_ports = [8000, 8081, 3000]
for port in test_ports:
self._force_free_port(port)

def _force_free_port(self, port: int):
    pass
"""Force free a specific port."""
pass
if sys.platform == "win32":
    pass
try:
    pass
result = subprocess.run( )
"",
shell=True, capture_output=True, text=True
            
if result.stdout:
    pass
lines = result.stdout.strip().split(" )"
")"
for line in lines:
parts = line.split()
if len(parts) >= 5:
    pass
pid = parts[-1]
if pid.isdigit():
    pass
subprocess.run("", shell=True)
except Exception:
    pass
pass
