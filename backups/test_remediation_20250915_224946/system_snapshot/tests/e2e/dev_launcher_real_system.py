'''
Dev Launcher Real System Integration for Testing
Integrates with the actual dev_launcher module to start real services.

CRITICAL REQUIREMENTS:
- Uses REAL dev_launcher, not mocks or subprocess
- Starts auth service (port 8081), backend (port 8000), frontend (optional)
- Provides proper health checking and service URLs
- Handles cleanup on test completion
- Compatible with existing test infrastructure
- Robust error handling and service management
'''

import asyncio
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

    # Add project root to path for imports

from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager

logger = logging.getLogger(__name__)


class DevLauncherRealSystem:
    """Real system integration using dev_launcher for testing."""

    def __init__(self, skip_frontend: bool = True):
        """Initialize with dev launcher configuration."""
        self.skip_frontend = skip_frontend
        self.launcher: Optional[DevLauncher] = None
        self.config: Optional[LauncherConfig] = None
        self.start_time: Optional[float] = None
        self.service_urls: Dict[str, str] = {}
        self._launcher_task: Optional[asyncio.Task] = None
        self._startup_success: bool = False
        self._startup_errors: List[str] = []
        self._shutdown_event = threading.Event()

    async def start_all_services(self) -> None:
        """Start all services using dev_launcher."""
        self.start_time = time.time()

    # Create launcher config for testing
        self.config = self._create_test_config()

    # Create launcher instance
        self.launcher = DevLauncher(self.config)

        try:
        # Check if we need to start new services or use existing ones
        # Removed problematic line: if await self._check_existing_services():
        logger.info("Using existing healthy services...")
        self._startup_success = True
        else:
        logger.info("Starting new dev_launcher services...")
                # Start launcher in background task
        self._launcher_task = asyncio.create_task(self._run_launcher())

                # Wait for startup to complete
        await self._wait_for_startup_completion()

                # Wait for services to be healthy
        await self._wait_for_health()

                # Set service URLs
        self.service_urls = { )
        "auth_service": "http://localhost:8081",  # Correct auth port
        "backend": "http://localhost:8000",
        "frontend": "http://localhost:3000" if not self.skip_frontend else None
                

        elapsed = time.time() - self.start_time
        logger.info("formatted_string")

        except Exception as e:
        self._startup_errors.append(str(e))
        logger.error("formatted_string")
        raise

    def _create_test_config(self) -> LauncherConfig:
        """Create test configuration."""
        config = LauncherConfig()
        config.backend_port = 8000
        config.frontend_port = 3000 if not self.skip_frontend else None
        config.dynamic_ports = False  # Use fixed ports for testing
        config.no_backend_reload = True  # No hot reload for tests
        config.no_browser = True  # Don"t open browser
        config.verbose = False  # Less output for tests
        config.non_interactive = True  # No prompts
        config.startup_mode = "minimal"  # Fast startup
        config.no_secrets = True  # Don"t load secrets for tests
        config.parallel_startup = True  # Parallel startup for speed
        config.project_root = self._detect_project_root()
        return config

    def _detect_project_root(self) -> Path:
        """Detect project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
        # Check for project root markers - netra_backend and auth_service directories
        if (current / "netra_backend").exists() and (current / "auth_service").exists():
        return current
        current = current.parent
        raise RuntimeError("Could not detect project root directory")

    async def _check_existing_services(self) -> bool:
        """Check if services are already running and healthy."""
        try:
        # Check backend
        backend_response = requests.get("http://localhost:8000/health", timeout=2)
        if backend_response.status_code != 200:
        return False

            # Check auth
        auth_response = requests.get("http://localhost:8081/health", timeout=2)
        if auth_response.status_code != 200:
        return False

                # Check frontend if needed
        if not self.skip_frontend:
        frontend_response = requests.get("http://localhost:3000", timeout=2)
        if frontend_response.status_code not in [200, 404]:
        return False

        return True
        except Exception:
        return False

    async def _run_launcher(self) -> None:
        """Run the launcher."""
        try:
        result = await self.launcher.run()
        self._startup_success = (result == 0)
        if result != 0:
        self._startup_errors.append("formatted_string")
        except Exception as e:
        self._startup_success = False
        self._startup_errors.append("formatted_string")
        logger.error("formatted_string")

    async def _wait_for_startup_completion(self, timeout: int = 60) -> None:
        """Wait for startup to complete or fail."""
        start_time = time.time()

        while (time.time() - start_time) < timeout:
        if self._launcher_task and self._launcher_task.done():
            # Task completed, check result
        if not self._startup_success:
        raise RuntimeError("formatted_string")
        return

                # Check if services are becoming available
                # Removed problematic line: if await self._check_basic_health():
                    # Services responding, consider startup successful
        self._startup_success = True
        return

        await asyncio.sleep(1)

        raise TimeoutError("formatted_string")

    async def _check_basic_health(self) -> bool:
        """Basic health check for core services."""
        try:
        # Just check if ports are responding
        backend_ok = await self._check_port_responding(8000)
        auth_ok = await self._check_port_responding(8081)
        return backend_ok and auth_ok
        except Exception:
        return False

    async def _check_port_responding(self, port: int) -> bool:
        """Check if a port is responding."""
        try:
        response = requests.get("formatted_string", timeout=1)
        return response.status_code == 200
        except Exception:
        return False

    async def _wait_for_health(self, timeout: int = 30) -> None:
        """Wait for all services to be healthy."""
        start = time.time()

        while time.time() - start < timeout:
        try:
            # Check backend health
        backend_response = requests.get("http://localhost:8000/health", timeout=2)
        backend_healthy = backend_response.status_code == 200

            # Check auth health
        auth_response = requests.get("http://localhost:8081/health", timeout=2)
        auth_healthy = auth_response.status_code == 200

            # Check frontend health if needed
        frontend_healthy = True
        if not self.skip_frontend:
        try:
        frontend_response = requests.get("http://localhost:3000", timeout=2)
        frontend_healthy = frontend_response.status_code in [200, 404]
        except Exception:
        frontend_healthy = False

        if backend_healthy and auth_healthy and frontend_healthy:
        logger.info("All required services are healthy")
        return

        except Exception as e:
        logger.debug("formatted_string")

        await asyncio.sleep(1)

        raise TimeoutError("formatted_string")

    async def stop_all_services(self) -> None:
        """Stop all services and cleanup."""
        logger.info("Stopping all services...")

    # Set shutdown event
        self._shutdown_event.set()

    # Cancel launcher task if running
        if self._launcher_task and not self._launcher_task.done():
        self._launcher_task.cancel()
        try:
        await self._launcher_task
        except asyncio.CancelledError:
        pass

                # Graceful shutdown of launcher
        if self.launcher:
        try:
        if hasattr(self.launcher, '_graceful_shutdown'):
        self.launcher._graceful_shutdown()
        elif hasattr(self.launcher, 'stop_services'):
        await self.launcher.stop_services()
        except Exception as e:
        logger.warning("formatted_string")
        finally:
        self.launcher = None

                                        # Force cleanup of test ports
        self._force_cleanup_ports()

    def _force_cleanup_ports(self):
        """Force cleanup of test ports."""
        test_ports = [8000, 8081, 3000]
        for port in test_ports:
        self._force_free_port(port)

    def _force_free_port(self, port: int):
        """Force free a specific port."""
        if sys.platform == "win32":
        try:
        result = subprocess.run( )
        "formatted_string",
        shell=True, capture_output=True, text=True
            
        if result.stdout:
        lines = result.stdout.strip().split(" )
        ")
        for line in lines:
        parts = line.split()
        if len(parts) >= 5:
        pid = parts[-1]
        if pid.isdigit():
        subprocess.run("formatted_string", shell=True)
        logger.debug("formatted_string")
        except Exception as e:
        logger.debug("formatted_string")
        elif sys.platform == "darwin":
        try:
        result = subprocess.run( )
        "formatted_string",
        shell=True, capture_output=True, text=True
                                        
        if result.stdout:
        pids = result.stdout.strip().split(" )
        ")
        for pid in pids:
        if pid.isdigit():
        subprocess.run("formatted_string", shell=True)
        logger.debug("formatted_string")
        except Exception as e:
        logger.debug("formatted_string")

    def get_service_urls(self) -> Dict[str, str]:
        """Get service URLs for testing."""
        return self.service_urls

    def is_healthy(self) -> bool:
        """Check if all services are healthy."""
        try:
        # Check each service
        backend_ok = requests.get("http://localhost:8000/health", timeout=2).status_code == 200
        auth_ok = requests.get("http://localhost:8081/health", timeout=2).status_code == 200

        if self.skip_frontend:
        return backend_ok and auth_ok
        else:
        frontend_ok = requests.get("http://localhost:3000", timeout=2).status_code in [200, 404]
        return backend_ok and auth_ok and frontend_ok

        except Exception:
        return False

    def get_startup_errors(self) -> List[str]:
        """Get any startup errors that occurred."""
        return self._startup_errors.copy()

    def get_startup_time(self) -> Optional[float]:
        """Get startup time in seconds."""
        if self.start_time:
        return time.time() - self.start_time
        return None

    async def __aenter__(self):
        """Context manager entry."""
        await self.start_all_services()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop_all_services()


    def create_dev_launcher_system(skip_frontend: bool = True) -> DevLauncherRealSystem:
        """Factory function to create dev launcher system for tests."""
        return DevLauncherRealSystem(skip_frontend=skip_frontend)


    # Compatibility function for existing tests
    def create_real_services_manager():
        """Create real services manager using dev launcher (compatibility)."""
        return DevLauncherRealSystem(skip_frontend=True)


    # Additional utility functions for tests
    async def wait_for_service_health(service_url: str, timeout: int = 30) -> bool:
        """Wait for a specific service to become healthy."""
        start_time = time.time()

        while (time.time() - start_time) < timeout:
        try:
        response = requests.get("formatted_string", timeout=2)
        if response.status_code == 200:
        return True
        except Exception:
        pass
        await asyncio.sleep(1)

        return False


    def check_port_available(port: int) -> bool:
        """Check if a port is available for use."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
        s.bind(('localhost', port))
        return True
        except OSError:
        return False


    async def verify_service_startup_sequence() -> Dict[str, bool]:
        """Verify the proper service startup sequence."""
        results = {}

    # Check if auth starts first (should be available)
        results['auth_first'] = await wait_for_service_health("http://localhost:8081", 10)

    # Check if backend starts next
        results['backend_second'] = await wait_for_service_health("http://localhost:8000", 15)

    # Check if frontend starts last (if enabled)
        try:
        frontend_response = requests.get("http://localhost:3000", timeout=2)
        results['frontend_last'] = frontend_response.status_code in [200, 404]
        except Exception:
        results['frontend_last'] = False

        return results


            # Test utilities for dev launcher integration
class DevLauncherTestContext:
        """Test context for dev launcher integration tests."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.services: Optional[DevLauncherRealSystem] = None
        self.test_data: Dict[str, Any] = {}

    async def setup_test_environment(self, skip_frontend: bool = True) -> None:
        """Setup test environment with dev launcher."""
        self.start_time = time.time()
        self.services = DevLauncherRealSystem(skip_frontend=skip_frontend)

        try:
        await self.services.start_all_services()
        logger.info("Test environment setup complete")
        except Exception as e:
        logger.error("formatted_string")
        await self.cleanup_test_environment()
        raise

    async def test_cleanup_test_environment(self) -> None:
        """Cleanup test environment."""
        if self.services:
        await self.services.stop_all_services()
        self.services = None

        elapsed = time.time() - (self.start_time or time.time())
        logger.info("formatted_string")

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get URL for a specific service."""
        if self.services:
        return self.services.get_service_urls().get(service_name)
        return None

    def is_environment_healthy(self) -> bool:
        """Check if test environment is healthy."""
        if self.services:
        return self.services.is_healthy()
        return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup_test_environment()
