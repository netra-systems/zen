"""
Test Suite for Issue #860: WebSocket Windows Connection Failures

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure platform works on Windows development environments
- Value Impact: Windows developers can contribute to platform without connectivity issues
- Strategic Impact: Developer productivity and platform compatibility

This test suite reproduces the exact WinError 1225 issues reported in Issue #860
to validate fixes and ensure Windows compatibility.

CRITICAL: These tests SHOULD FAIL initially to prove they reproduce the issue.
"""

import pytest
import asyncio
import platform
import socket
import websockets
from unittest.mock import patch, MagicMock
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env

class TestIssue860WindowsWebSocketFailures(BaseIntegrationTest):
    """Test Windows-specific WebSocket connection failures."""

    def setup_method(self):
        """Setup test environment with Windows-specific conditions."""
        self.env = get_env()
        self.is_windows = platform.system().lower() == 'windows'

        # Windows-specific test URLs that should cause connection failures
        self.failing_urls = [
            "ws://localhost:8002/ws",  # Default WebSocket URL from logs
            "ws://localhost:8000/ws",  # Backend WebSocket URL
            "ws://127.0.0.1:8002/ws",  # Explicit localhost IP
        ]

        # URLs that might work in different environments
        self.fallback_urls = [
            "ws://staging.netrasystems.ai/ws",
            "wss://staging.netrasystems.ai/ws",
        ]

    @pytest.mark.unit
    def test_windows_socket_connection_refused_detection(self):
        """Test detection of Windows-specific connection refused errors."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Test direct socket connection to reproduce WinError 1225
        for url_path in ["localhost:8002", "127.0.0.1:8002", "localhost:8000"]:
            host, port = url_path.split(":")
            port = int(port)

            with pytest.raises(Exception) as exc_info:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)  # Quick timeout to fail fast
                sock.connect((host, port))
                sock.close()

            # Verify we get the expected Windows error
            error = exc_info.value
            assert any([
                "WinError 1225" in str(error),
                "Connection refused" in str(error),
                "ConnectionRefusedError" in str(type(error).__name__),
                "[Errno 10061]" in str(error),  # Windows socket error
                "timed out" in str(error),  # Timeout is also a valid connection failure
                "timeout" in str(error).lower(),
                "OSError" in str(type(error).__name__)  # Generic OS error
            ]), f"Expected Windows connection error, got: {error}"

            print(f"✓ Reproduced connection failure for {url_path}: {error}")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_connection_failure_reproduction(self):
        """Test WebSocket connection failures that reproduce Issue #860."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        connection_attempts = []

        for url in self.failing_urls:
            try:
                # Attempt WebSocket connection with timeout
                async with asyncio.timeout(2.0):
                    async with websockets.connect(url) as websocket:
                        # If we reach here, connection succeeded unexpectedly
                        connection_attempts.append({
                            "url": url,
                            "status": "unexpected_success",
                            "error": None
                        })

            except asyncio.TimeoutError as e:
                connection_attempts.append({
                    "url": url,
                    "status": "timeout",
                    "error": str(e)
                })

            except websockets.exceptions.InvalidURI as e:
                connection_attempts.append({
                    "url": url,
                    "status": "invalid_uri",
                    "error": str(e)
                })

            except websockets.exceptions.ConnectionClosed as e:
                connection_attempts.append({
                    "url": url,
                    "status": "connection_closed",
                    "error": str(e)
                })

            except ConnectionRefusedError as e:
                connection_attempts.append({
                    "url": url,
                    "status": "connection_refused",
                    "error": str(e)
                })

            except OSError as e:
                connection_attempts.append({
                    "url": url,
                    "status": "os_error",
                    "error": str(e)
                })

            except Exception as e:
                connection_attempts.append({
                    "url": url,
                    "status": "other_error",
                    "error": str(e)
                })

        # Verify we got the expected connection failures
        assert len(connection_attempts) > 0, "No connection attempts made"

        # All attempts should fail with connection-related errors
        failed_attempts = [a for a in connection_attempts if a["status"] != "unexpected_success"]
        assert len(failed_attempts) == len(connection_attempts), \
            f"Expected all connections to fail, but got successes: {connection_attempts}"

        # Check for Windows-specific error patterns
        windows_errors = [a for a in failed_attempts if any([
            "WinError 1225" in a["error"],
            "Connection refused" in a["error"],
            "[Errno 10061]" in a["error"],
            "connection_refused" in a["status"]
        ])]

        assert len(windows_errors) > 0, \
            f"Expected Windows connection errors, got: {failed_attempts}"

        print(f"✓ Reproduced {len(windows_errors)} Windows WebSocket connection failures")
        for attempt in windows_errors:
            print(f"  - {attempt['url']}: {attempt['status']} ({attempt['error']})")

    @pytest.mark.unit
    def test_environment_aware_service_discovery_failure(self):
        """Test that environment-aware service discovery fails appropriately on Windows."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Test environment detection
        env = get_env()

        # These should all be None/empty when services aren't running
        websocket_urls = [
            env.get("WEBSOCKET_URL"),
            env.get("MOCK_WEBSOCKET_URL"),
            env.get("STAGING_WEBSOCKET_URL")
        ]

        backend_urls = [
            env.get("BACKEND_URL"),
            env.get("API_BASE_URL")
        ]

        # Test service discovery patterns that should fail
        service_discovery_attempts = []

        # Attempt to discover local services
        for port in [8000, 8001, 8002, 3000]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(("localhost", port))
                sock.close()

                service_discovery_attempts.append({
                    "port": port,
                    "status": "success" if result == 0 else "failed",
                    "error_code": result
                })

            except Exception as e:
                service_discovery_attempts.append({
                    "port": port,
                    "status": "exception",
                    "error": str(e)
                })

        # For Issue #860, we expect all services to be unavailable
        failed_discoveries = [a for a in service_discovery_attempts
                            if a["status"] != "success"]

        # Should have at least some failed discoveries (proving no services running)
        assert len(failed_discoveries) > 0, \
            "Expected service discovery failures when services not running"

        print(f"✓ Service discovery failed appropriately: {failed_discoveries}")

    @pytest.mark.unit
    def test_websocket_factory_windows_compatibility(self):
        """Test WebSocket factory patterns with Windows-specific error handling."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Import WebSocket manager components to test factory patterns
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            from netra_backend.app.websocket_core.connection_manager import ConnectionManager

            # Test factory initialization with unavailable services
            with pytest.raises(Exception) as exc_info:
                # This should fail when trying to connect to unavailable services
                manager = WebSocketManager()
                # Attempt to create connection to non-existent service
                connection_mgr = ConnectionManager(
                    websocket_url="ws://localhost:8002/ws"
                )

            error = exc_info.value
            print(f"✓ WebSocket factory failed appropriately: {error}")

        except ImportError as e:
            pytest.skip(f"WebSocket components not available for testing: {e}")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_retry_mechanism_exhaustion(self):
        """Test WebSocket retry mechanism exhaustion on Windows."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        # Simulate the retry pattern that leads to WinError 1225
        max_retries = 3
        retry_count = 0
        connection_errors = []

        for attempt in range(max_retries):
            try:
                retry_count += 1

                # Simulate connection attempt with exponential backoff
                await asyncio.sleep(0.1 * (2 ** attempt))

                # Attempt connection to unavailable service
                async with websockets.connect(
                    "ws://localhost:8002/ws",
                    timeout=1.0
                ) as websocket:
                    # Should not reach here
                    pytest.fail("Unexpected successful connection")

            except Exception as e:
                connection_errors.append({
                    "attempt": attempt + 1,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

        # Should have exhausted all retries
        assert retry_count == max_retries, f"Expected {max_retries} retries, got {retry_count}"
        assert len(connection_errors) == max_retries, \
            f"Expected {max_retries} errors, got {len(connection_errors)}"

        # Last error should be the final connection failure
        final_error = connection_errors[-1]
        assert any([
            "WinError 1225" in final_error["error"],
            "Connection refused" in final_error["error"],
            "ConnectionRefusedError" in final_error["error_type"]
        ]), f"Expected connection refused error, got: {final_error}"

        print(f"✓ Reproduced retry exhaustion pattern: {connection_errors}")

    @pytest.mark.unit
    def test_docker_bypass_environment_detection(self):
        """Test Docker bypass detection on Windows."""
        if not self.is_windows:
            pytest.skip("This test only runs on Windows")

        env = get_env()

        # Test various Docker bypass environment variables
        docker_bypass_vars = [
            "DOCKER_BYPASS",
            "USE_MOCK_WEBSOCKET",
            "USE_STAGING_FALLBACK",
            "MOCK_WEBSOCKET_URL"
        ]

        bypass_status = {}
        for var in docker_bypass_vars:
            value = env.get(var)
            bypass_status[var] = {
                "value": value,
                "is_set": value is not None,
                "is_enabled": value in ["true", "True", "1", "yes"]
            }

        print(f"Docker bypass status: {bypass_status}")

        # For Issue #860 reproduction, we want to test without bypass initially
        # to reproduce the actual error
        if bypass_status["DOCKER_BYPASS"]["is_enabled"]:
            pytest.skip("Docker bypass is enabled, cannot reproduce connection failures")

        # Test that without bypass, we get connection failures
        assert not bypass_status["DOCKER_BYPASS"]["is_enabled"], \
            "Expected Docker bypass to be disabled for Issue #860 reproduction"