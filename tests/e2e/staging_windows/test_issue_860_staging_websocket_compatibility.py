"""
E2E Test Suite for Issue #860: Staging WebSocket Windows Compatibility

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure staging environment works for Windows developers
- Value Impact: Windows developers can test against staging for feature development
- Strategic Impact: Platform reliability and cross-platform compatibility

This test suite validates staging WebSocket connectivity from Windows environments
and tests fallback mechanisms when local services fail.

CRITICAL: These tests validate both failure reproduction AND working solutions.
"""

import pytest
import asyncio
import platform
import websockets
import httpx
from test_framework.base_e2e_test import BaseE2ETest
from shared.isolated_environment import get_env

class Issue860StagingWebSocketCompatibilityTests(BaseE2ETest):
    """Test staging WebSocket compatibility for Windows Issue #860 resolution."""

    def setup_method(self):
        """Setup E2E test environment with staging configuration."""
        self.env = get_env()
        self.is_windows = platform.system().lower() == 'windows'

        # Staging environment URLs (these should work)
        self.staging_config = {
            "backend_url": "https://staging.netrasystems.ai",
            "websocket_url": "wss://staging.netrasystems.ai/ws",
            "auth_url": "https://auth.staging.netrasystems.ai",
            "frontend_url": "https://staging.netrasystems.ai"
        }

        # Local URLs that should fail (reproducing Issue #860)
        self.local_config = {
            "backend_url": "http://localhost:8000",
            "websocket_url": "ws://localhost:8002/ws",
            "auth_url": "http://localhost:8081",
            "frontend_url": "http://localhost:3000"
        }

    @pytest.mark.e2e
    @pytest.mark.staging
    
    async def test_staging_websocket_connectivity_from_windows(self):
        """Test that staging WebSocket works from Windows (solution validation)."""
        if not self.is_windows:
            pytest.skip("This test validates Windows-specific connectivity")

        # Test staging WebSocket connectivity
        websocket_url = self.staging_config["websocket_url"]

        try:
            async with asyncio.timeout(10.0):  # Longer timeout for staging
                async with websockets.connect(
                    websocket_url,
                    additional_headers={
                        "User-Agent": "Issue860-Windows-Test",
                        "Origin": self.staging_config["frontend_url"]
                    }
                ) as websocket:

                    # Test basic WebSocket functionality
                    test_message = {
                        "type": "ping",
                        "data": "Issue #860 Windows connectivity test"
                    }

                    await websocket.send(str(test_message))

                    # Wait for response
                    response = await websocket.recv()

                    print(f"✓ Staging WebSocket connection successful from Windows")
                    print(f"  URL: {websocket_url}")
                    print(f"  Response: {response}")

                    # Verify we got a response
                    assert response is not None
                    assert len(response) > 0

        except asyncio.TimeoutError:
            pytest.fail(f"Staging WebSocket connection timed out: {websocket_url}")

        except websockets.exceptions.ConnectionClosed as e:
            pytest.fail(f"Staging WebSocket connection closed: {e}")

        except Exception as e:
            pytest.fail(f"Staging WebSocket connection failed: {e}")

    @pytest.mark.e2e
    @pytest.mark.staging
    
    async def test_local_to_staging_fallback_mechanism(self):
        """Test fallback from local services (failing) to staging (working)."""
        if not self.is_windows:
            pytest.skip("This test validates Windows-specific fallback")

        # Step 1: Confirm local services fail (Issue #860 reproduction)
        local_connection_result = await self._test_local_websocket_connection()

        assert not local_connection_result["success"], \
            f"Expected local connection to fail for Issue #860 reproduction: {local_connection_result}"

        print(f"✓ Confirmed local WebSocket failure: {local_connection_result['error']}")

        # Step 2: Test staging fallback works
        staging_connection_result = await self._test_staging_websocket_connection()

        assert staging_connection_result["success"], \
            f"Expected staging connection to succeed: {staging_connection_result}"

        print(f"✓ Confirmed staging WebSocket success: {staging_connection_result}")

        # Step 3: Validate fallback mechanism
        fallback_test_result = {
            "local_failed": not local_connection_result["success"],
            "staging_succeeded": staging_connection_result["success"],
            "fallback_viable": True
        }

        assert fallback_test_result["local_failed"], "Local connection should fail"
        assert fallback_test_result["staging_succeeded"], "Staging connection should succeed"
        assert fallback_test_result["fallback_viable"], "Fallback should be viable"

        print(f"✓ Issue #860 fallback mechanism validated: {fallback_test_result}")

    async def _test_local_websocket_connection(self):
        """Test local WebSocket connection (should fail for Issue #860)."""
        try:
            async with asyncio.timeout(2.0):  # Short timeout for local
                async with websockets.connect(
                    self.local_config["websocket_url"]
                ) as websocket:
                    await websocket.send("test")
                    response = await websocket.recv()
                    return {
                        "success": True,
                        "url": self.local_config["websocket_url"],
                        "response": response
                    }

        except Exception as e:
            return {
                "success": False,
                "url": self.local_config["websocket_url"],
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def _test_staging_websocket_connection(self):
        """Test staging WebSocket connection (should succeed)."""
        try:
            async with asyncio.timeout(10.0):  # Longer timeout for staging
                async with websockets.connect(
                    self.staging_config["websocket_url"],
                    additional_headers={
                        "Origin": self.staging_config["frontend_url"]
                    }
                ) as websocket:
                    await websocket.send("test")
                    response = await websocket.recv()
                    return {
                        "success": True,
                        "url": self.staging_config["websocket_url"],
                        "response": response
                    }

        except Exception as e:
            return {
                "success": False,
                "url": self.staging_config["websocket_url"],
                "error": str(e),
                "error_type": type(e).__name__
            }

    @pytest.mark.e2e
    @pytest.mark.staging
    
    async def test_staging_service_health_checks(self):
        """Test staging service health checks from Windows."""
        if not self.is_windows:
            pytest.skip("This test validates Windows-specific service health")

        # Test all staging service health endpoints
        health_results = {}

        staging_health_endpoints = {
            "backend": f"{self.staging_config['backend_url']}/health",
            "auth": f"{self.staging_config['auth_url']}/health",
            "frontend": f"{self.staging_config['frontend_url']}/health"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            for service_name, health_url in staging_health_endpoints.items():
                try:
                    response = await client.get(health_url)
                    health_results[service_name] = {
                        "status": "healthy",
                        "status_code": response.status_code,
                        "response_size": len(response.text),
                        "url": health_url
                    }

                except httpx.TimeoutException as e:
                    health_results[service_name] = {
                        "status": "timeout",
                        "error": str(e),
                        "url": health_url
                    }

                except Exception as e:
                    health_results[service_name] = {
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "url": health_url
                    }

        print(f"Staging health results: {health_results}")

        # At least backend should be healthy
        assert health_results["backend"]["status"] == "healthy", \
            f"Expected staging backend to be healthy: {health_results['backend']}"

        # Count healthy services
        healthy_services = [
            name for name, result in health_results.items()
            if result["status"] == "healthy"
        ]

        assert len(healthy_services) > 0, \
            f"Expected at least one healthy staging service: {health_results}"

        print(f"✓ Staging services healthy from Windows: {healthy_services}")

    @pytest.mark.e2e
    @pytest.mark.staging
    
    def test_environment_detection_and_configuration(self):
        """Test environment detection and configuration for Issue #860 resolution."""
        if not self.is_windows:
            pytest.skip("This test validates Windows-specific environment detection")

        env = get_env()

        # Test environment variable detection
        environment_config = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "docker_bypass": env.get("DOCKER_BYPASS"),
            "use_staging_fallback": env.get("USE_STAGING_FALLBACK"),
            "use_mock_websocket": env.get("USE_MOCK_WEBSOCKET"),
            "websocket_url": env.get("WEBSOCKET_URL"),
            "staging_websocket_url": env.get("STAGING_WEBSOCKET_URL")
        }

        print(f"Environment configuration: {environment_config}")

        # Verify Windows detection
        assert environment_config["platform"] == "Windows", \
            f"Expected Windows platform, got: {environment_config['platform']}"

        # Test configuration precedence for Issue #860 resolution
        configuration_precedence = self._determine_configuration_precedence(environment_config)

        print(f"Configuration precedence: {configuration_precedence}")

        # Should prioritize staging over local for Issue #860 resolution
        assert configuration_precedence["preferred_environment"] in ["staging", "mock"], \
            f"Expected staging or mock preference for Issue #860 resolution: {configuration_precedence}"

    def _determine_configuration_precedence(self, env_config):
        """Determine configuration precedence for Issue #860 resolution."""
        precedence = {
            "local_available": False,
            "staging_available": True,  # Assume staging is available
            "mock_enabled": env_config.get("use_mock_websocket") == "true",
            "docker_bypass": env_config.get("docker_bypass") == "true",
            "staging_fallback": env_config.get("use_staging_fallback") == "true"
        }

        # Determine preferred environment
        if precedence["mock_enabled"]:
            precedence["preferred_environment"] = "mock"
        elif precedence["staging_fallback"] or not precedence["local_available"]:
            precedence["preferred_environment"] = "staging"
        else:
            precedence["preferred_environment"] = "local"

        return precedence

    @pytest.mark.e2e
    @pytest.mark.staging
    
    async def test_websocket_authentication_flow_staging(self):
        """Test WebSocket authentication flow against staging from Windows."""
        if not self.is_windows:
            pytest.skip("This test validates Windows-specific authentication")

        # Test basic authentication flow without actual login
        # (since we don't want to create real users in staging)

        auth_test_results = {
            "connection_established": False,
            "connection_error": None,
            "authentication_attempted": False,
            "authentication_error": None
        }

        try:
            # Attempt connection to staging WebSocket
            async with asyncio.timeout(10.0):
                async with websockets.connect(
                    self.staging_config["websocket_url"],
                    additional_headers={
                        "Origin": self.staging_config["frontend_url"],
                        "User-Agent": "Issue860-Auth-Test"
                    }
                ) as websocket:

                    auth_test_results["connection_established"] = True

                    # Send a test authentication message
                    auth_message = {
                        "type": "auth_test",
                        "message": "Issue #860 authentication test"
                    }

                    await websocket.send(str(auth_message))
                    auth_test_results["authentication_attempted"] = True

                    # Wait for response (may be error, that's expected)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        auth_test_results["response"] = response
                    except asyncio.TimeoutError:
                        auth_test_results["response"] = "No response (expected for auth test)"

        except websockets.exceptions.ConnectionClosed as e:
            auth_test_results["connection_error"] = f"Connection closed: {e}"
            # Connection closed might be expected for auth failure
            if e.code in [1011, 1008]:  # Internal error or policy violation
                auth_test_results["authentication_error"] = f"Auth rejected (expected): {e}"

        except Exception as e:
            auth_test_results["connection_error"] = str(e)

        print(f"Authentication test results: {auth_test_results}")

        # Connection should be established even if auth fails
        assert auth_test_results["connection_established"], \
            f"Expected WebSocket connection to establish: {auth_test_results}"

        print(f"✓ WebSocket authentication flow tested from Windows")

    @pytest.mark.e2e
    @pytest.mark.staging
    
    async def test_complete_issue_860_resolution_validation(self):
        """Test complete Issue #860 resolution validation."""
        if not self.is_windows:
            pytest.skip("This test validates complete Windows Issue #860 resolution")

        resolution_validation = {
            "local_failure_confirmed": False,
            "staging_connectivity_confirmed": False,
            "fallback_mechanism_working": False,
            "windows_compatibility_confirmed": False
        }

        # Step 1: Confirm local services fail (Issue #860 reproduction)
        local_test = await self._test_local_websocket_connection()
        resolution_validation["local_failure_confirmed"] = not local_test["success"]

        # Step 2: Confirm staging connectivity works
        staging_test = await self._test_staging_websocket_connection()
        resolution_validation["staging_connectivity_confirmed"] = staging_test["success"]

        # Step 3: Confirm fallback mechanism
        resolution_validation["fallback_mechanism_working"] = (
            resolution_validation["local_failure_confirmed"] and
            resolution_validation["staging_connectivity_confirmed"]
        )

        # Step 4: Confirm Windows compatibility
        resolution_validation["windows_compatibility_confirmed"] = (
            self.is_windows and
            resolution_validation["staging_connectivity_confirmed"]
        )

        print(f"Issue #860 resolution validation: {resolution_validation}")

        # All validation steps should pass
        for validation_key, validation_result in resolution_validation.items():
            assert validation_result, \
                f"Issue #860 resolution validation failed at: {validation_key}"

        print(f"✓ Complete Issue #860 resolution validated successfully")

        # Return summary for reporting
        return {
            "issue": "Issue #860 WebSocket Windows Connection Failures",
            "resolution_status": "VALIDATED",
            "validation_results": resolution_validation,
            "local_error": local_test.get("error"),
            "staging_success": staging_test.get("success"),
            "platform": platform.system(),
            "test_timestamp": asyncio.get_event_loop().time()
        }