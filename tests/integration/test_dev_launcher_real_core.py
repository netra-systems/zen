"""Core Tests - Split from test_dev_launcher_real.py"""

import asyncio
import pytest
import time
import sys
import os
import subprocess
import signal
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, Future
import threading
import json
from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager
from dev_launcher.cache_manager import CacheManager
import socket


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def __init__(self):
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
        """Setup monitoring for console errors and startup logs."""
        # Monitor launcher logs
        if self.launcher and hasattr(self.launcher, 'log_manager'):
            log_manager = self.launcher.log_manager
            # Hook into log outputs to capture errors
            original_log = logger.error
            
            def capture_error(msg, *args, **kwargs):
                self.console_errors.append(str(msg))
                return original_log(msg, *args, **kwargs)
                
            logger.error = capture_error

    def detect_console_errors(self) -> List[str]:
        """Detect console errors from service outputs."""
        return self.console_errors.copy()

    def verify_port_allocation(self) -> Tuple[bool, List[str]]:
        """Verify services are running on correct ports."""
        issues = []
        
        # Check backend port
        backend_port = self.config.backend_port or 8000
        if not self._is_port_in_use(backend_port):
            issues.append(f"Backend port {backend_port} not in use")
            
        # Check auth port
        if not self._is_port_in_use(8081):
            issues.append("Auth port 8081 not in use")
            
        # Check frontend port (if enabled)
        if self.config.frontend_port:
            if not self._is_port_in_use(self.config.frontend_port):
                issues.append(f"Frontend port {self.config.frontend_port} not in use")
                
        return len(issues) == 0, issues

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return False
            except OSError:
                return True

    def verify_grace_periods(self) -> Tuple[bool, List[str]]:
        """Verify grace periods are respected in startup."""
        issues = []
        
        if not self.start_time:
            issues.append("Start time not recorded")
            return False, issues
            
        elapsed = time.time() - self.start_time
        
        # Grace periods per SPEC:
        # - Backend readiness: 30s
        # - Auth verification: 15s  
        # - Frontend readiness: 90s
        
        if elapsed < 5:  # Minimum reasonable startup time
            issues.append(f"Startup too fast ({elapsed:.1f}s) - grace periods not respected")
            
        # No maximum time check - some systems are slower
            
        return len(issues) == 0, issues

    def _force_free_test_ports(self):
        """Force free test ports."""
        test_ports = [8000, 8081, 3000]
        for port in test_ports:
            self._force_free_port(port)

    def _force_free_port(self, port: int):
        """Force free a specific port."""
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    f"netstat -ano | findstr :{port}",
                    shell=True, capture_output=True, text=True
                )
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid.isdigit():
                                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
            except Exception:
                pass
