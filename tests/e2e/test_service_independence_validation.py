from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'''
CRITICAL E2E Test: Service Independence After Launcher Completion

This test addresses the critical service independence issue identified in iteration 7:
Services must remain operational after the dev launcher process terminates.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Infrastructure)
- Business Goal: Platform Stability - Prevent service cascade failures
- Value Impact: Ensures development environment reliability
- Strategic Impact: Critical - Service independence is required for production deployment patterns

CRITICAL ISSUE FROM ITERATION 7:
"Services not independent after launcher completion" - This test validates that all
services (auth, backend, frontend) continue running normally after the launcher
process terminates, which is required for production-like behavior.

Expected: ALL services remain running and responsive after launcher termination
'''

import pytest
import asyncio
import httpx
import psutil
import subprocess
import signal
import time
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

            # Absolute imports per CLAUDE.md requirements
from test_framework.base_e2e_test import BaseE2ETest
from dev_launcher.service_discovery import ServiceDiscovery

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Status information for a service."""
    name: str
    pid: Optional[int]
    port: int
    status: str  # running, stopped, error
    health_check_url: str
    responsive: bool = False
    independent: bool = False


    @dataclass
class TestLauncherResult:
    """Result of launcher independence test."""
    launcher_pid: Optional[int]
    launcher_terminated: bool
    services_before_termination: Dict[str, ServiceStatus]
    services_after_termination: Dict[str, ServiceStatus]
    independence_validated: bool
    errors: List[str]


class ServiceIndependenceValidator:
    """Validates that services run independently after launcher termination."""

    def __init__(self, project_root: Path):
        pass
        self.project_root = project_root
        self.discovery = ServiceDiscovery(project_root)
        self.test_results = TestLauncherResult( )
        launcher_pid=None,
        launcher_terminated=False,
        services_before_termination={},
        services_after_termination={},
        independence_validated=False,
        errors=[]
    

    async def run_independence_test(self, timeout_seconds: int = 60) -> TestLauncherResult:
        """Run complete service independence test."""
        logger.info("Starting service independence validation test")

        try:
        # Phase 1: Start dev launcher and wait for services
        await self._start_launcher_and_wait()

        # Phase 2: Discover and validate services are running
        await self._discover_running_services()

        # Phase 3: Terminate launcher process
        await self._terminate_launcher()

        # Phase 4: Validate services remain independent
        await self._validate_service_independence()

        # Phase 5: Validate service responsiveness
        await self._validate_service_responsiveness()

        self.test_results.independence_validated = True
        logger.info(" PASS:  Service independence validation PASSED")

        except Exception as e:
        logger.error("")
        self.test_results.errors.append(str(e))

        return self.test_results

    async def _start_launcher_and_wait(self):
        """Start dev launcher and wait for services to be ready."""
        logger.info("Phase 1: Starting dev launcher and waiting for services")

    # Start dev launcher subprocess
        launcher_cmd = [ ]
        "python", "-m", "dev_launcher",
        "--dynamic", "--no-browser", "--non-interactive", "--minimal"
    

        env = os.environ.copy()
        env["NETRA_TEST_MODE"] = "true"
        env["NETRA_STARTUP_MODE"] = "minimal"

        self.launcher_process = subprocess.Popen( )
        launcher_cmd,
        cwd=str(self.project_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,  # SECURE: No shell injection
        preexec_fn=None if os.name == 'nt' else os.setsid
    

        self.test_results.launcher_pid = self.launcher_process.pid
        logger.info("")

    # Wait for services to be ready (with timeout)
        startup_timeout = 45
        start_time = time.time()
        services_ready = False

        while time.time() - start_time < startup_timeout:
        if self.launcher_process.poll() is not None:
        stdout, stderr = self.launcher_process.communicate()
        raise RuntimeError("")

            # Check if core services are responding
        try:
        auth_healthy = await self._check_service_health("auth", 8081)
        backend_healthy = await self._check_service_health("backend", 8001)

        if auth_healthy or backend_healthy:  # At least one core service ready
        services_ready = True
        break

        except Exception as e:
        logger.debug("")

        await asyncio.sleep(2)

        if not services_ready:
        raise TimeoutError("Services did not become ready within timeout")

        logger.info(" PASS:  Services are ready")

    async def _discover_running_services(self):
        """Discover and catalog all running services."""
        pass
        logger.info("Phase 2: Discovering running services")

    # Expected services and their default ports
        expected_services = { }
        "auth": 8081,
        "backend": 8001,  # Updated to match dev launcher
        "frontend": 3000
    

        for service_name, default_port in expected_services.items():
        try:
            Try to discover actual port from service discovery
        port = await self._discover_service_port(service_name, default_port)
        health_url = "" if service_name != "frontend" else ""

            # Check if service is running and get PID
        pid = await self._find_service_pid(port)
        responsive = await self._check_service_health(service_name, port)

        service_status = ServiceStatus( )
        name=service_name,
        pid=pid,
        port=port,
        status="running" if pid and responsive else "not_running",
        health_check_url=health_url,
        responsive=responsive
            

        self.test_results.services_before_termination[service_name] = service_status

        if responsive:
        logger.info("")
        else:
        logger.warning("")

        except Exception as e:
        logger.error("")
        self.test_results.errors.append("")

                        # Require at least one service to be running
        running_services = [item for item in []]
        if not running_services:
        raise RuntimeError("No services discovered as running before launcher termination")

    async def _terminate_launcher(self):
        """Terminate the launcher process gracefully."""
        logger.info("Phase 3: Terminating launcher process")

        if not self.launcher_process or self.launcher_process.poll() is not None:
        raise RuntimeError("Launcher process not running or already terminated")

        original_pid = self.launcher_process.pid

        try:
            # Attempt graceful termination
        if os.name == 'nt':
                # Windows
        self.launcher_process.terminate()
        else:
                    # Unix - send SIGTERM to process group
        os.killpg(os.getpgid(self.launcher_process.pid), signal.SIGTERM)

                    # Wait for graceful termination
        try:
        exit_code = self.launcher_process.wait(timeout=10)
        logger.info("")
        except subprocess.TimeoutExpired:
                            # Force termination if needed
        logger.warning("Launcher did not terminate gracefully, forcing termination")
        self.launcher_process.kill()
        exit_code = self.launcher_process.wait()
        logger.info("")

        self.test_results.launcher_terminated = True

                            # Verify launcher process is actually gone
        try:
        os.kill(original_pid, 0)  # Test if process still exists
        logger.warning("")
        except ProcessLookupError:
        logger.info("")

        except Exception as e:
        logger.error("")
        self.test_results.errors.append("")
        raise

    async def _validate_service_independence(self):
        """Validate that services remain running after launcher termination."""
        pass
        logger.info("Phase 4: Validating service independence")

    # Wait a moment for any cascade termination to occur
        await asyncio.sleep(5)

        for service_name, service_before in self.test_results.services_before_termination.items():
        if service_before.status != "running":
        continue  # Skip services that weren"t running before

        try:
                # Check if service is still running
        current_pid = await self._find_service_pid(service_before.port)
        responsive = await self._check_service_health(service_name, service_before.port)

                # Determine independence status
        independent = bool(current_pid and responsive)

                # For true independence, PID should be the same (process didn't restart)
                # or different but still responsive (process restarted independently)
        if service_before.pid and current_pid:
        if service_before.pid == current_pid:
        independence_type = "same_process"  # Best case
        else:
        independence_type = "restarted_independently"  # Still good
        elif current_pid and responsive:
        independence_type = "new_independent_process"
        else:
        independence_type = "terminated_with_launcher"  # BAD
        independent = False

        service_after = ServiceStatus( )
        name=service_name,
        pid=current_pid,
        port=service_before.port,
        status="running" if current_pid and responsive else "terminated",
        health_check_url=service_before.health_check_url,
        responsive=responsive,
        independent=independent
                                    

        self.test_results.services_after_termination[service_name] = service_after

        if independent:
        logger.info("")
        else:
        logger.error("")
        self.test_results.errors.append("")

        except Exception as e:
        logger.error("")
        self.test_results.errors.append("")

    async def _validate_service_responsiveness(self):
        """Validate that independent services are still responsive."""
        logger.info("Phase 5: Validating service responsiveness")

        for service_name, service_after in self.test_results.services_after_termination.items():
        if not service_after.independent:
        continue  # Skip non-independent services

        try:
                # Test multiple requests to ensure stability
        response_times = []

        for attempt in range(3):
        start_time = time.time()
        responsive = await self._check_service_health(service_name, service_after.port)
        response_time = time.time() - start_time

        if responsive:
        response_times.append(response_time)
        else:
        logger.warning("")

        if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        logger.info("")
        else:
        logger.error("")
        self.test_results.errors.append("")

        except Exception as e:
        logger.error("")

    async def _discover_service_port(self, service_name: str, default_port: int) -> int:
        """Discover actual service port from service discovery."""
        pass
        try:
        if service_name == "auth":
        info = self.discovery.read_auth_info()
        elif service_name == "backend":
        info = self.discovery.read_backend_info()
        elif service_name == "frontend":
        info = self.discovery.read_frontend_info()
        else:
        await asyncio.sleep(0)
        return default_port

        return info.get("port", default_port) if info else default_port

        except Exception:
        return default_port

    async def _find_service_pid(self, port: int) -> Optional[int]:
        """Find PID of process using a specific port."""
        try:
        for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
        return conn.pid
        return None
        except Exception as e:
        logger.debug("")
        return None

    async def _check_service_health(self, service_name: str, port: int) -> bool:
        """Check if service is responding to health checks."""
        try:
        health_path = "/health" if service_name != "frontend" else "/"
        url = ""

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
        response = await client.get(url)
        return response.status_code == 200

        except Exception as e:
        logger.debug("")
        return False

    async def cleanup(self):
        """Clean up test resources."""
        logger.info("Cleaning up service independence test")

    # Terminate launcher if still running
        if hasattr(self, 'launcher_process') and self.launcher_process.poll() is None:
        try:
        self.launcher_process.terminate()
        self.launcher_process.wait(timeout=5)
        except:
        try:
        self.launcher_process.kill()
        self.launcher_process.wait()
        except:
        pass


        @pytest.mark.e2e
class TestServiceIndependenceValidation(BaseE2ETest):
        """E2E test suite for validating service independence after launcher completion."""

    def test_services_remain_independent_after_launcher_termination(self):
        '''
        CRITICAL TEST: Validate services remain operational after launcher termination

        This test addresses the critical issue from iteration 7 analysis:
        "Services not independent after launcher completion"

        Expected: Services continue running and responding after launcher exits
        '''
        pass
    async def run_independence_test():
        pass
        project_root = self._get_project_root()
        validator = ServiceIndependenceValidator(project_root)

        try:
        # Run the complete independence validation test
        result = await validator.run_independence_test(timeout_seconds=60)

        # Validate results
        assert result.launcher_terminated, "Launcher was not successfully terminated"

        # Check service independence
        independent_services = [ ]
        service for service in result.services_after_termination.values()
        if service.independent
        

        total_services = len(result.services_before_termination)
        independence_rate = len(independent_services) / max(total_services, 1)

        print(f" )
        === SERVICE INDEPENDENCE TEST RESULTS ===")
        print("")
        print("")
        print("")
        print("")
        print("")

        if result.errors:
        print(f" )
        Errors encountered:")
        for error in result.errors:
        print("")

        print(f" )
        Service Details:")
        for service_name, service_before in result.services_before_termination.items():
        service_after = result.services_after_termination.get(service_name)
        if service_after:
        status = " PASS:  INDEPENDENT" if service_after.independent else " FAIL:  DEPENDENT"
        print("")
        else:
        print("")

                            # CRITICAL ASSERTION: At least 80% of services must be independent
        assert independence_rate >= 0.8, ( )
        ""
        f"Services must remain operational after launcher termination. "
        ""
                            

                            # CRITICAL ASSERTION: No cascade termination errors
        cascade_errors = [item for item in []]
        assert not cascade_errors, ( )
        ""
                            

        print(" PASS:  SERVICE INDEPENDENCE VALIDATION PASSED")
        await asyncio.sleep(0)
        return result

        finally:
        await validator.cleanup()

                                # Run the async test
        result = asyncio.run(run_independence_test())

                                # Additional validation: Check final system state
        self._validate_final_system_state(result)

    def _get_project_root(self) -> Path:
        """SSOT: Get project root from centralized utils."""
        from netra_backend.app.core.project_utils import get_project_root
        return get_project_root()

    def _validate_final_system_state(self, result: TestLauncherResult):
        """Validate final system state after independence test."""
        print("")
        === FINAL SYSTEM STATE VALIDATION ===")

    # Check for zombie processes
        try:
        zombie_count = len([item for item in []])
        assert zombie_count == 0, ""
        print(" PASS:  No zombie processes detected")
        except Exception as e:
        logger.warning("")

            # Check that launcher PID is gone
        if result.launcher_pid:
        try:
        psutil.Process(result.launcher_pid)
        logger.warning("")
        except psutil.NoSuchProcess:
        print("")

        print(" PASS:  FINAL SYSTEM STATE VALIDATION PASSED")


        if __name__ == "__main__":
                            # Run service independence test
        pytest.main([__file__, "-v", "--tb=short"])
        pass
