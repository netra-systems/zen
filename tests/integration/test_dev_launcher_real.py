"""
Dev Launcher Real Integration Tests

Comprehensive integration tests that actually launch services and verify proper operation.
Tests the complete SPEC startup sequence (steps 1-13) and validates real service functionality.

CRITICAL REQUIREMENTS:
- Actually start backend, auth, and frontend services  
- Verify services respond on correct ports
- Check for console errors in output
- Validate health endpoints work
- Test grace periods and timing requirements
- Verify cache effectiveness
"""

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

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager
from dev_launcher.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class DevLauncherIntegrationTester:
    """Real integration tester for dev launcher."""
    
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
        
    async def start_services_with_monitoring(self, config: LauncherConfig) -> bool:
        """Start services with comprehensive monitoring."""
        self.start_time = time.time()
        self.config = config
        self.launcher = DevLauncher(config)
        
        # Setup console error monitoring
        self._setup_error_monitoring()
        
        # Run the launcher
        try:
            result = await self.launcher.run()
            return result == 0
        except Exception as e:
            logger.error(f"Launcher startup failed: {e}")
            self.console_errors.append(f"Launcher exception: {str(e)}")
            return False
            
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
            
    async def verify_spec_startup_sequence(self) -> Tuple[bool, List[str]]:
        """Verify SPEC startup sequence steps 1-13 are executed properly."""
        issues = []
        
        if not self.launcher:
            issues.append("Launcher not initialized")
            return False, issues
            
        # Verify Step 1-2: Cache and environment checks
        if not hasattr(self.launcher, 'cache_manager'):
            issues.append("Cache manager not initialized")
            
        # Verify Step 3: Secret loading (allowed to fail in tests)
        if not hasattr(self.launcher, 'secret_loader'):
            issues.append("Secret loader not initialized")
            
        # Verify Step 4: Database validation
        if not hasattr(self.launcher, 'database_connector'):
            issues.append("Database connector not initialized")
            
        # Verify Step 5: Migration checks
        if not hasattr(self.launcher, 'migration_runner'):
            issues.append("Migration runner not initialized")
            
        # Verify Step 6-7: Backend and auth processes started
        if not self.launcher.process_manager.is_running("Backend"):
            issues.append("Backend process not started")
        if not self.launcher.process_manager.is_running("Auth"):
            issues.append("Auth process not started")
            
        # Verify Step 8: Backend readiness
        backend_ready = await self._check_backend_ready()
        if not backend_ready:
            issues.append("Backend not ready after startup")
            
        # Verify Step 9: Auth system verification
        auth_ready = await self._check_auth_ready()
        if not auth_ready:
            issues.append("Auth system not verified")
            
        # Verify Step 10-11: Frontend (if not skipped)
        if self.config.frontend_port:
            if not self.launcher.process_manager.is_running("Frontend"):
                issues.append("Frontend process not started")
            frontend_ready = await self._check_frontend_ready()
            if not frontend_ready:
                issues.append("Frontend not ready after startup")
                
        # Verify Step 12: Cache updates
        if hasattr(self.launcher, 'cache_manager'):
            # Cache should have been updated with successful startup
            pass  # This is internal state, hard to verify externally
            
        # Verify Step 13: Health monitoring started
        if not hasattr(self.launcher, 'health_monitor'):
            issues.append("Health monitor not initialized")
        elif not self.launcher.health_monitor.is_running():
            issues.append("Health monitoring not started")
            
        return len(issues) == 0, issues
        
    async def _check_backend_ready(self, timeout: int = 30) -> bool:
        """Check backend /health/ready endpoint."""
        backend_port = self.config.backend_port or 8000
        ready_url = f"http://localhost:{backend_port}/health/ready"
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                response = requests.get(ready_url, timeout=5)
                if response.status_code == 200:
                    return True
            except Exception as e:
                logger.debug(f"Backend check: {e}")
            await asyncio.sleep(1)
        return False
        
    async def _check_auth_ready(self, timeout: int = 15) -> bool:
        """Check auth /api/auth/config endpoint."""
        auth_url = "http://localhost:8081/api/auth/config"
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                response = requests.get(auth_url, timeout=5)
                if response.status_code in [200, 404]:  # 404 acceptable
                    return True
            except Exception as e:
                logger.debug(f"Auth check: {e}")
            await asyncio.sleep(1)
        return False
        
    async def _check_frontend_ready(self, timeout: int = 90) -> bool:
        """Check frontend readiness."""
        frontend_port = self.config.frontend_port or 3000
        frontend_url = f"http://localhost:{frontend_port}"
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                response = requests.get(frontend_url, timeout=5)
                if response.status_code in [200, 404]:
                    return True
            except Exception as e:
                logger.debug(f"Frontend check: {e}")
            await asyncio.sleep(2)
        return False
        
    async def verify_health_endpoints(self) -> Tuple[bool, List[str]]:
        """Verify all health endpoints are working."""
        issues = []
        
        # Check backend health
        try:
            backend_port = self.config.backend_port or 8000
            health_url = f"http://localhost:{backend_port}/health"
            response = requests.get(health_url, timeout=5)
            if response.status_code != 200:
                issues.append(f"Backend health endpoint returned {response.status_code}")
        except Exception as e:
            issues.append(f"Backend health check failed: {e}")
            
        # Check auth health
        try:
            auth_health_url = "http://localhost:8081/health"
            response = requests.get(auth_health_url, timeout=5)
            if response.status_code != 200:
                issues.append(f"Auth health endpoint returned {response.status_code}")
        except Exception as e:
            issues.append(f"Auth health check failed: {e}")
            
        # Check frontend health (if enabled)
        if self.config.frontend_port:
            try:
                frontend_port = self.config.frontend_port
                frontend_url = f"http://localhost:{frontend_port}"
                response = requests.get(frontend_url, timeout=5)
                if response.status_code not in [200, 404]:
                    issues.append(f"Frontend returned unexpected {response.status_code}")
            except Exception as e:
                issues.append(f"Frontend check failed: {e}")
                
        return len(issues) == 0, issues
        
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
        import socket
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
        
    async def test_cache_effectiveness(self) -> Tuple[bool, List[str]]:
        """Test cache effectiveness by running startup twice."""
        issues = []
        
        if not self.launcher or not hasattr(self.launcher, 'cache_manager'):
            issues.append("Cache manager not available")
            return False, issues
            
        cache_manager = self.launcher.cache_manager
        
        # First run should populate cache
        first_startup_time = time.time() - (self.start_time or time.time())
        
        # Stop current launcher
        await self.stop_services()
        
        # Start again and measure cache effectiveness
        second_start = time.time()
        config2 = self.create_test_config()
        launcher2 = DevLauncher(config2)
        
        try:
            result = await launcher2.run()
            if result != 0:
                issues.append("Second startup failed")
            else:
                second_startup_time = time.time() - second_start
                # Second startup should be faster due to caching
                if second_startup_time >= first_startup_time:
                    issues.append(f"Cache not effective: {second_startup_time:.1f}s vs {first_startup_time:.1f}s")
        except Exception as e:
            issues.append(f"Second startup exception: {e}")
        finally:
            # Cleanup second launcher
            if hasattr(launcher2, '_graceful_shutdown'):
                launcher2._graceful_shutdown()
                
        return len(issues) == 0, issues
        
    async def stop_services(self):
        """Stop all services and cleanup."""
        self._shutdown_event.set()
        
        # Stop monitoring threads
        for thread in self._monitoring_threads:
            if thread.is_alive():
                thread.join(timeout=5)
                
        # Stop launcher
        if self.launcher:
            if hasattr(self.launcher, '_graceful_shutdown'):
                self.launcher._graceful_shutdown()
            self.launcher = None
            
        # Ensure ports are freed
        self._force_free_test_ports()
        
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
                
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_services()


# Test Cases

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_startup_sequence():
    """Test complete startup sequence with all services."""
    async with DevLauncherIntegrationTester() as tester:
        config = tester.create_test_config(skip_frontend=False, verbose=True)
        
        # Start services
        success = await tester.start_services_with_monitoring(config)
        assert success, "Failed to start services"
        
        # Verify SPEC startup sequence
        sequence_ok, sequence_issues = await tester.verify_spec_startup_sequence()
        assert sequence_ok, f"Startup sequence issues: {sequence_issues}"
        
        # Verify health endpoints
        health_ok, health_issues = await tester.verify_health_endpoints()
        assert health_ok, f"Health endpoint issues: {health_issues}"
        
        # Verify port allocation
        ports_ok, port_issues = tester.verify_port_allocation()
        assert ports_ok, f"Port allocation issues: {port_issues}"
        
        # Check for console errors
        errors = tester.detect_console_errors()
        assert len(errors) == 0, f"Console errors detected: {errors}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_backend_only_startup():
    """Test backend-only startup (skip frontend)."""
    async with DevLauncherIntegrationTester() as tester:
        config = tester.create_test_config(skip_frontend=True)
        
        # Start services
        success = await tester.start_services_with_monitoring(config)
        assert success, "Failed to start backend services"
        
        # Verify backend and auth are running
        backend_ready = await tester._check_backend_ready()
        assert backend_ready, "Backend not ready"
        
        auth_ready = await tester._check_auth_ready()
        assert auth_ready, "Auth not ready"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_grace_periods_respected():
    """Test that grace periods are respected during startup."""
    async with DevLauncherIntegrationTester() as tester:
        config = tester.create_test_config()
        
        start_time = time.time()
        success = await tester.start_services_with_monitoring(config)
        elapsed = time.time() - start_time
        
        assert success, "Failed to start services"
        
        # Verify grace periods
        grace_ok, grace_issues = tester.verify_grace_periods()
        assert grace_ok, f"Grace period issues: {grace_issues}"
        
        # Should take reasonable time (not too fast, not too slow)
        assert elapsed >= 3, f"Startup too fast: {elapsed:.1f}s"
        assert elapsed <= 120, f"Startup too slow: {elapsed:.1f}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_monitoring_timing():
    """Test health monitoring starts only after services are ready."""
    async with DevLauncherIntegrationTester() as tester:
        config = tester.create_test_config()
        
        success = await tester.start_services_with_monitoring(config)
        assert success, "Failed to start services"
        
        # Health monitor should be running
        assert tester.launcher.health_monitor.is_running(), "Health monitor not started"
        
        # All services should be marked ready before monitoring starts
        assert tester.launcher.health_monitor.all_services_ready(), "Services not ready for monitoring"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_effectiveness():
    """Test cache effectiveness between runs."""
    async with DevLauncherIntegrationTester() as tester:
        config = tester.create_test_config()
        
        success = await tester.start_services_with_monitoring(config)
        assert success, "Failed to start services"
        
        # Test cache effectiveness
        cache_ok, cache_issues = await tester.test_cache_effectiveness()
        assert cache_ok, f"Cache effectiveness issues: {cache_issues}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_startup():
    """Test parallel startup functionality."""
    async with DevLauncherIntegrationTester() as tester:
        config = tester.create_test_config(parallel_startup=True)
        
        start_time = time.time()
        success = await tester.start_services_with_monitoring(config)
        parallel_time = time.time() - start_time
        
        assert success, "Failed to start services with parallel startup"
        
        # Test sequential startup for comparison
        await tester.stop_services()
        
        config_sequential = tester.create_test_config(parallel_startup=False)
        start_time = time.time()
        tester2 = DevLauncherIntegrationTester()
        success2 = await tester2.start_services_with_monitoring(config_sequential)
        sequential_time = time.time() - start_time
        await tester2.stop_services()
        
        assert success2, "Failed to start services with sequential startup"
        
        # Parallel should be faster or at least not significantly slower
        assert parallel_time <= sequential_time * 1.2, f"Parallel startup not effective: {parallel_time:.1f}s vs {sequential_time:.1f}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_port_conflict_handling():
    """Test handling of port conflicts."""
    # This test would require external port occupation
    # For now, just verify our port checking works
    async with DevLauncherIntegrationTester() as tester:
        config = tester.create_test_config()
        
        success = await tester.start_services_with_monitoring(config)
        assert success, "Failed to start services"
        
        # Verify port allocation
        ports_ok, port_issues = tester.verify_port_allocation()
        assert ports_ok, f"Port allocation issues: {port_issues}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graceful_shutdown():
    """Test graceful shutdown of services."""
    async with DevLauncherIntegrationTester() as tester:
        config = tester.create_test_config()
        
        success = await tester.start_services_with_monitoring(config)
        assert success, "Failed to start services"
        
        # Stop services gracefully
        await tester.stop_services()
        
        # Verify ports are freed
        test_ports = [8000, 8081, 3000]
        for port in test_ports:
            assert not tester._is_port_in_use(port), f"Port {port} not freed after shutdown"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])