"""
Dev launcher test fixtures and utilities for startup testing.

Provides fixtures for managing dev launcher lifecycle, capturing logs,
monitoring health checks, and verifying database connections.

Follows 450-line file limit and 25-line function limit constraints.
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import pytest

# Add project root to path

from dev_launcher import DevLauncher, LauncherConfig
from test_framework.test_environment_setup import TestEnvironmentOrchestrator


@dataclass
class DevLauncherState:
    """Captures dev launcher state for testing."""
    launcher: Optional[DevLauncher]
    config: Optional[LauncherConfig]
    process_id: Optional[int]
    allocated_ports: Dict[str, int]
    startup_time: float
    logs: List[str]
    errors: List[str]


class TestEnvironmentManager:
    """Simplified test environment manager for dev launcher tests."""
    
    def __init__(self):
        self.orchestrator: Optional[TestEnvironmentOrchestrator] = None
        self.session_id: Optional[str] = None
        self.test_db_url = "postgresql+asyncpg://netra:netra123@localhost:5432/netra_dev"
        self.test_redis_url = "redis://localhost:6379/1"
        self.test_clickhouse_url = "http://netra:netra123@localhost:8123"
        self._temp_env_vars: Dict[str, str] = {}
    
    async def initialize(self) -> None:
        """Initialize test environment."""
        self.orchestrator = TestEnvironmentOrchestrator()
        await self.orchestrator.initialize()
    
    def setup_test_db(self) -> None:
        """Setup test database environment variables."""
        self._set_temp_env("TEST_DATABASE_URL", self.test_db_url)
        self._set_temp_env("DATABASE_URL", self.test_db_url)
    
    def setup_test_redis(self) -> None:
        """Setup test Redis environment variables."""
        self._set_temp_env("TEST_REDIS_URL", self.test_redis_url)
        self._set_temp_env("REDIS_URL", self.test_redis_url)
    
    def setup_test_clickhouse(self) -> None:
        """Setup test ClickHouse environment variables."""
        self._set_temp_env("TEST_CLICKHOUSE_URL", self.test_clickhouse_url)
        self._set_temp_env("CLICKHOUSE_URL", self.test_clickhouse_url)
    
    def setup_test_secrets(self) -> None:
        """Setup test secrets environment variables."""
        self._set_temp_env("TESTING", "true")
        self._set_temp_env("SECRET_KEY", "test-secret-key")
        self._set_temp_env("JWT_SECRET_KEY", "test-jwt-secret")
    
    def _set_temp_env(self, key: str, value: str) -> None:
        """Set temporary environment variable."""
        if key not in self._temp_env_vars:
            self._temp_env_vars[key] = os.getenv(key, "")
        os.environ[key] = value
    
    def cleanup(self) -> None:
        """Cleanup test environment."""
        # Restore original environment variables
        for key, original_value in self._temp_env_vars.items():
            if original_value:
                os.environ[key] = original_value
            else:
                os.environ.pop(key, None)
        self._temp_env_vars.clear()


class LogCapture:
    """Captures logs during dev launcher testing."""
    
    def __init__(self):
        self.captured_logs: List[str] = []
        self.log_handler: Optional[logging.Handler] = None
        self.original_level: Optional[int] = None
    
    def start_capture(self) -> None:
        """Start capturing logs."""
        self.log_handler = LogCaptureHandler(self.captured_logs)
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        self.original_level = root_logger.level
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(self.log_handler)
    
    def stop_capture(self) -> None:
        """Stop capturing logs."""
        if self.log_handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self.log_handler)
            if self.original_level is not None:
                root_logger.setLevel(self.original_level)
    
    def get_logs(self) -> List[str]:
        """Get captured logs."""
        return self.captured_logs.copy()
    
    def clear_logs(self) -> None:
        """Clear captured logs."""
        self.captured_logs.clear()


class LogCaptureHandler(logging.Handler):
    """Custom log handler for capturing logs."""
    
    def __init__(self, log_list: List[str]):
        super().__init__()
        self.log_list = log_list
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record to captured list."""
        try:
            message = self.format(record)
            self.log_list.append(message)
        except Exception:
            pass


class HealthMonitor:
    """Monitors service health during testing."""
    
    def __init__(self):
        self.health_checks: List[Dict[str, Any]] = []
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, services: Dict[str, int], interval: float = 5.0) -> None:
        """Start monitoring service health."""
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(
            self._monitor_loop(services, interval)
        )
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring service health."""
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, services: Dict[str, int], interval: float) -> None:
        """Main monitoring loop."""
        async with aiohttp.ClientSession() as session:
            while self.monitoring_active:
                timestamp = time.time()
                for service, port in services.items():
                    health_result = await self._check_service_health(
                        session, service, port
                    )
                    health_result["timestamp"] = timestamp
                    self.health_checks.append(health_result)
                
                await asyncio.sleep(interval)
    
    async def _check_service_health(self, session: aiohttp.ClientSession, 
                                   service: str, port: int) -> Dict[str, Any]:
        """Check health of individual service."""
        url = f"http://localhost:{port}/health"
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return {
                    "service": service,
                    "port": port,
                    "status_code": response.status,
                    "healthy": response.status == 200,
                    "error": None
                }
        except Exception as e:
            return {
                "service": service,
                "port": port,
                "status_code": 0,
                "healthy": False,
                "error": str(e)
            }
    
    def get_health_history(self) -> List[Dict[str, Any]]:
        """Get health check history."""
        return self.health_checks.copy()


class ProcessMonitor:
    """Monitors processes during dev launcher testing."""
    
    def __init__(self):
        self.process_snapshots: List[Dict[str, Any]] = []
    
    def capture_process_snapshot(self) -> Dict[str, Any]:
        """Capture current process snapshot."""
        snapshot = {
            "timestamp": time.time(),
            "processes": self._get_running_processes()
        }
        self.process_snapshots.append(snapshot)
        return snapshot
    
    def _get_running_processes(self) -> List[Dict[str, Any]]:
        """Get list of running processes."""
        try:
            if os.name == "nt":  # Windows
                cmd = ["tasklist", "/FO", "CSV"]
            else:  # Unix-like
                cmd = ["ps", "aux"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return self._parse_process_output(result.stdout, os.name == "nt")
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []
    
    def _parse_process_output(self, output: str, is_windows: bool) -> List[Dict[str, Any]]:
        """Parse process output into structured data."""
        processes = []
        lines = output.strip().split('\n')
        
        if is_windows and len(lines) > 1:
            # Skip header line for Windows
            for line in lines[1:]:
                if 'uvicorn' in line or 'next' in line or 'node' in line:
                    parts = line.split('","')
                    if len(parts) >= 2:
                        processes.append({
                            "name": parts[0].strip('"'),
                            "pid": parts[1].strip('"'),
                            "platform": "windows"
                        })
        else:
            # Unix-like systems
            for line in lines[1:]:  # Skip header
                if 'uvicorn' in line or 'next' in line or 'node' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        processes.append({
                            "name": parts[-1],
                            "pid": parts[1],
                            "platform": "unix"
                        })
        
        return processes
    
    def verify_clean_shutdown(self) -> bool:
        """Verify no dev launcher processes remain."""
        current_processes = self._get_running_processes()
        return len(current_processes) == 0


@pytest.fixture
async def test_environment():
    """Pytest fixture for test environment setup."""
    env_manager = TestEnvironmentManager()
    await env_manager.initialize()
    yield env_manager
    env_manager.cleanup()


@pytest.fixture
async def log_capture():
    """Pytest fixture for log capture."""
    capture = LogCapture()
    capture.start_capture()
    yield capture
    capture.stop_capture()


@pytest.fixture
async def health_monitor():
    """Pytest fixture for health monitoring."""
    monitor = HealthMonitor()
    yield monitor
    await monitor.stop_monitoring()


@pytest.fixture
async def process_monitor():
    """Pytest fixture for process monitoring."""
    monitor = ProcessMonitor()
    yield monitor