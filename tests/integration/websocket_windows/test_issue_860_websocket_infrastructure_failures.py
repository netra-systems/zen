"""
Integration Test Suite for Issue #860: WebSocket Infrastructure Failures on Windows

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket infrastructure across all platforms
- Value Impact: Developers on Windows can run integration tests and develop features
- Strategic Impact: Platform reliability and developer experience

This test suite validates WebSocket infrastructure patterns that fail on Windows
with WinError 1225 and related connection issues.

CRITICAL: These tests SHOULD FAIL initially to prove they reproduce infrastructure issues.
"""

import pytest
import asyncio
import platform
import socket
import websockets
import httpx
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env

class Issue860WebSocketInfrastructureFailuresTests(BaseIntegrationTest):
    """Test WebSocket infrastructure failures specific to Windows platform."""

    def setup_method(self):
        """Setup integration test environment."""
        self.env = get_env()
        self.is_windows = platform.system().lower() == 'windows'

        # Test configuration that should fail when services aren't running
        self.test_config = {
            "backend_url": "http://localhost:8000",
            "websocket_url": "ws://localhost:8002/ws",
            "auth_url": "http://localhost:8081",
            "frontend_url": "http://localhost:3000"
        }

        # Service health endpoints to test
        self.health_endpoints = {
            "backend": f"{self.test_config['backend_url']}/health",
            "auth": f"{self.test_config['auth_url']}/health",
            "frontend": f"{self.test_config['frontend_url']}/health"
        }

    @pytest.mark.integration
    async def test_backend_service_unavailable_detection(self):
        """Test detection of unavailable backend service causing WebSocket failures."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Test all health endpoints to confirm services are down
        service_status = {}

        async with httpx.AsyncClient(timeout=2.0) as client:
            for service_name, health_url in self.health_endpoints.items():
                try:
                    response = await client.get(health_url)
                    service_status[service_name] = {
                        "status": "available",
                        "status_code": response.status_code,
                        "response": response.text[:100]
                    }

                except httpx.ConnectError as e:
                    service_status[service_name] = {
                        "status": "connect_error",
                        "error": str(e),
                        "error_type": "ConnectError"
                    }

                except httpx.TimeoutException as e:
                    service_status[service_name] = {
                        "status": "timeout",
                        "error": str(e),
                        "error_type": "TimeoutException"
                    }

                except Exception as e:
                    service_status[service_name] = {
                        "status": "other_error",
                        "error": str(e),
                        "error_type": type(e).__name__
                    }

        print(f"Service status: {service_status}")

        # For Issue #860 reproduction, services should be unavailable
        unavailable_services = [
            name for name, status in service_status.items()
            if status["status"] != "available"
        ]

        assert len(unavailable_services) > 0, \
            f"Expected some services to be unavailable for Issue #860 reproduction, got: {service_status}"

        # Check for Windows-specific connection errors
        windows_connection_errors = [
            name for name, status in service_status.items()
            if "connect_error" in status.get("status", "") and any([
                "WinError 1225" in status.get("error", ""),
                "Connection refused" in status.get("error", ""),
                "[Errno 10061]" in status.get("error", "")
            ])
        ]

        print(f"CHECK Detected {len(windows_connection_errors)} Windows connection errors")
        assert len(windows_connection_errors) > 0, \
            "Expected Windows connection errors for Issue #860 reproduction"

    @pytest.mark.asyncio
    @pytest.mark.integration
    
    async def test_websocket_connection_infrastructure_failure(self):
        """Test WebSocket connection infrastructure failures."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Test the complete WebSocket connection flow that fails in Issue #860
        websocket_connection_attempts = []

        # Test various WebSocket URLs that should fail
        websocket_urls = [
            "ws://localhost:8002/ws",  # Primary WebSocket URL
            "ws://localhost:8000/ws",  # Backend WebSocket URL
            "ws://127.0.0.1:8002/ws",  # Explicit IP address
        ]

        for url in websocket_urls:
            connection_result = await self._attempt_websocket_connection(url)
            websocket_connection_attempts.append(connection_result)

        print(f"WebSocket connection attempts: {websocket_connection_attempts}")

        # All connections should fail for Issue #860 reproduction
        failed_connections = [
            attempt for attempt in websocket_connection_attempts
            if attempt["status"] != "success"
        ]

        assert len(failed_connections) == len(websocket_connection_attempts), \
            f"Expected all WebSocket connections to fail, got successes: {websocket_connection_attempts}"

        # Check for the specific WinError 1225 pattern
        winerror_connections = [
            attempt for attempt in failed_connections
            if any([
                "WinError 1225" in attempt.get("error", ""),
                "Connection refused" in attempt.get("error", ""),
                "ConnectionRefusedError" in attempt.get("error_type", "")
            ])
        ]

        assert len(winerror_connections) > 0, \
            f"Expected WinError 1225 pattern, got: {failed_connections}"

        print(f"CHECK Reproduced {len(winerror_connections)} WinError 1225 WebSocket failures")

    async def _attempt_websocket_connection(self, url):
        """Attempt WebSocket connection and capture detailed error information."""
        try:
            async with asyncio.timeout(3.0):
                async with websockets.connect(url) as websocket:
                    # Test basic WebSocket functionality
                    await websocket.send("test_message")
                    response = await websocket.recv()
                    return {
                        "url": url,
                        "status": "success",
                        "response": response
                    }

        except asyncio.TimeoutError as e:
            return {
                "url": url,
                "status": "timeout",
                "error": str(e),
                "error_type": "TimeoutError"
            }

        except websockets.ConnectionClosed as e:
            return {
                "url": url,
                "status": "connection_closed",
                "error": str(e),
                "error_type": "ConnectionClosed",
                "code": getattr(e, 'code', None),
                "reason": getattr(e, 'reason', None)
            }

        except ConnectionRefusedError as e:
            return {
                "url": url,
                "status": "connection_refused",
                "error": str(e),
                "error_type": "ConnectionRefusedError"
            }

        except OSError as e:
            return {
                "url": url,
                "status": "os_error",
                "error": str(e),
                "error_type": "OSError",
                "errno": getattr(e, 'errno', None)
            }

        except Exception as e:
            return {
                "url": url,
                "status": "unknown_error",
                "error": str(e),
                "error_type": type(e).__name__
            }

    @pytest.mark.integration
    
    def test_service_discovery_infrastructure_failure(self):
        """Test service discovery infrastructure that fails on Windows."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Test the service discovery pattern used by the WebSocket infrastructure
        services_to_discover = {
            "backend": ("localhost", 8000),
            "websocket": ("localhost", 8002),
            "auth": ("localhost", 8081),
            "frontend": ("localhost", 3000),
            "postgresql": ("localhost", 5432),
            "redis": ("localhost", 6379)
        }

        discovery_results = {}

        for service_name, (host, port) in services_to_discover.items():
            try:
                # Test TCP connection to service
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                result = sock.connect_ex((host, port))
                sock.close()

                discovery_results[service_name] = {
                    "host": host,
                    "port": port,
                    "status": "available" if result == 0 else "unavailable",
                    "connect_result": result
                }

            except Exception as e:
                discovery_results[service_name] = {
                    "host": host,
                    "port": port,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                }

        print(f"Service discovery results: {discovery_results}")

        # For Issue #860 reproduction, critical services should be unavailable
        critical_services = ["backend", "websocket", "auth"]
        unavailable_critical_services = [
            name for name in critical_services
            if discovery_results[name]["status"] != "available"
        ]

        assert len(unavailable_critical_services) > 0, \
            f"Expected critical services to be unavailable for Issue #860 reproduction: {discovery_results}"

        # Check for Windows-specific error patterns
        windows_discovery_errors = [
            name for name, result in discovery_results.items()
            if result["status"] == "error" and any([
                "WinError" in result.get("error", ""),
                "[Errno 10061]" in result.get("error", ""),
                "Connection refused" in result.get("error", "")
            ])
        ]

        print(f"CHECK Windows discovery errors: {windows_discovery_errors}")

    @pytest.mark.integration
    
    def test_websocket_factory_integration_failure(self):
        """Test WebSocket factory integration patterns that fail on Windows."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Test importing and initializing WebSocket components
        factory_test_results = {}

        try:
            # Test WebSocket manager import and initialization
            from netra_backend.app.websocket_core.manager import WebSocketManager

            factory_test_results["websocket_manager_import"] = {
                "status": "success",
                "component": "WebSocketManager"
            }

            # Test manager initialization (should fail without running services)
            try:
                manager = WebSocketManager()
                factory_test_results["websocket_manager_init"] = {
                    "status": "unexpected_success",
                    "component": "WebSocketManager"
                }

            except Exception as e:
                factory_test_results["websocket_manager_init"] = {
                    "status": "expected_failure",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "component": "WebSocketManager"
                }

        except ImportError as e:
            factory_test_results["websocket_manager_import"] = {
                "status": "import_error",
                "error": str(e),
                "component": "WebSocketManager"
            }

        try:
            # Test connection manager import and initialization
            from netra_backend.app.websocket_core.connection_manager import ConnectionManager

            factory_test_results["connection_manager_import"] = {
                "status": "success",
                "component": "ConnectionManager"
            }

            # Test connection manager with unavailable service
            try:
                conn_mgr = ConnectionManager(
                    websocket_url="ws://localhost:8002/ws"
                )
                factory_test_results["connection_manager_init"] = {
                    "status": "unexpected_success",
                    "component": "ConnectionManager"
                }

            except Exception as e:
                factory_test_results["connection_manager_init"] = {
                    "status": "expected_failure",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "component": "ConnectionManager"
                }

        except ImportError as e:
            factory_test_results["connection_manager_import"] = {
                "status": "import_error",
                "error": str(e),
                "component": "ConnectionManager"
            }

        print(f"Factory test results: {factory_test_results}")

        # Should have some initialization failures when services unavailable
        initialization_failures = [
            name for name, result in factory_test_results.items()
            if "init" in name and result["status"] == "expected_failure"
        ]

        assert len(initialization_failures) > 0, \
            f"Expected WebSocket factory initialization failures: {factory_test_results}"

        print(f"CHECK WebSocket factory failures: {initialization_failures}")

    @pytest.mark.integration
    
    async def test_full_stack_connection_failure_pattern(self):
        """Test the full stack connection failure pattern seen in Issue #860."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Simulate the complete connection flow that fails in Issue #860
        connection_flow_results = []

        # Step 1: Health check attempts
        health_check_result = await self._test_health_check_failures()
        connection_flow_results.append({
            "step": "health_checks",
            "result": health_check_result
        })

        # Step 2: Service discovery attempts
        discovery_result = self._test_service_discovery_failures()
        connection_flow_results.append({
            "step": "service_discovery",
            "result": discovery_result
        })

        # Step 3: WebSocket connection attempts with retries
        websocket_result = await self._test_websocket_retry_failures()
        connection_flow_results.append({
            "step": "websocket_connections",
            "result": websocket_result
        })

        print(f"Full connection flow results: {connection_flow_results}")

        # Verify each step failed appropriately
        for step_result in connection_flow_results:
            step_name = step_result["step"]
            result = step_result["result"]

            assert result["has_failures"], \
                f"Expected failures in {step_name} step for Issue #860 reproduction"

            # Check for Windows-specific errors
            assert result["windows_errors"] > 0, \
                f"Expected Windows errors in {step_name} step"

        print(f"CHECK Reproduced complete Issue #860 failure pattern across all steps")

    async def _test_health_check_failures(self):
        """Test health check failures."""
        health_failures = 0
        windows_errors = 0

        async with httpx.AsyncClient(timeout=1.0) as client:
            for endpoint_name, url in self.health_endpoints.items():
                try:
                    await client.get(url)
                except Exception as e:
                    health_failures += 1
                    if any([
                        "WinError" in str(e),
                        "Connection refused" in str(e),
                        "[Errno 10061]" in str(e)
                    ]):
                        windows_errors += 1

        return {
            "has_failures": health_failures > 0,
            "total_failures": health_failures,
            "windows_errors": windows_errors
        }

    def _test_service_discovery_failures(self):
        """Test service discovery failures."""
        discovery_failures = 0
        windows_errors = 0

        for service_name, (host, port) in [
            ("backend", ("localhost", 8000)),
            ("websocket", ("localhost", 8002)),
            ("auth", ("localhost", 8081))
        ]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((host, port))
                sock.close()

                if result != 0:
                    discovery_failures += 1
                    # Windows typically returns 10061 for connection refused
                    if result == 10061:
                        windows_errors += 1

            except Exception as e:
                discovery_failures += 1
                if any([
                    "WinError" in str(e),
                    "[Errno 10061]" in str(e)
                ]):
                    windows_errors += 1

        return {
            "has_failures": discovery_failures > 0,
            "total_failures": discovery_failures,
            "windows_errors": windows_errors
        }

    async def _test_websocket_retry_failures(self):
        """Test WebSocket retry failures."""
        retry_failures = 0
        windows_errors = 0

        for url in ["ws://localhost:8002/ws", "ws://localhost:8000/ws"]:
            for attempt in range(3):  # 3 retry attempts
                try:
                    async with asyncio.timeout(1.0):
                        async with websockets.connect(url) as ws:
                            # Should not reach here
                            pass
                except Exception as e:
                    retry_failures += 1
                    if any([
                        "WinError 1225" in str(e),
                        "Connection refused" in str(e),
                        "ConnectionRefusedError" in str(type(e).__name__)
                    ]):
                        windows_errors += 1

        return {
            "has_failures": retry_failures > 0,
            "total_failures": retry_failures,
            "windows_errors": windows_errors
        }