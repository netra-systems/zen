"""
E2E Tests for Issue #1278 - Golden Path Validation (Non-Docker)

These tests validate the Golden Path user flow WITHOUT Docker, directly testing
staging infrastructure to reproduce Issue #1278 503 error patterns.

Business Value Justification (BVJ):
- Segment: Platform/Production
- Business Goal: Service Reliability/Golden Path Recovery
- Value Impact: Ensure complete user flow works end-to-end without Docker dependency
- Strategic Impact: Validate $500K+ ARR Golden Path infrastructure readiness

CRITICAL: These tests are designed to FAIL when GCP staging infrastructure
issues exist, reproducing the complete system failures seen in Issue #1278
without requiring Docker orchestration.
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import httpx
import websockets

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestIssue1278GoldenPathValidationNonDocker(SSotAsyncTestCase):
    """
    Test Golden Path validation for Issue #1278 without Docker.

    These tests validate the complete user journey against staging infrastructure
    to reproduce Issue #1278 failures without Docker dependencies.
    """

    def setup_method(self, method):
        """Setup for Golden Path validation tests."""
        super().setup_method(method)

        # Configure for staging environment
        self.set_env_var("ENVIRONMENT", "staging", source="test")
        self.set_env_var("TESTING", "false", source="test")  # Real environment testing
        self.set_env_var("GCP_PROJECT", "netra-staging", source="test")

        # Staging infrastructure endpoints
        self.staging_backend_url = "https://staging.netrasystems.ai"
        self.staging_frontend_url = "https://staging.netrasystems.ai"
        self.staging_websocket_url = "wss://api.staging.netrasystems.ai"

        self.record_metric("test_category", "issue_1278_golden_path_non_docker")
        self.record_metric("test_environment", "staging_direct")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_golden_path_step_1_frontend_accessibility(self):
        """
        Test Golden Path Step 1: Frontend accessibility without Docker.

        This should PASS for Issue #1278 - Frontend is Node.js and typically
        works even when Python services fail due to database issues.
        """
        step_start = time.time()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.staging_frontend_url)
                response_time = time.time() - step_start

                self.record_metric("frontend_status_code", response.status_code)
                self.record_metric("frontend_response_time", response_time)

                if response.status_code == 200:
                    self.record_metric("frontend_accessibility_test", "PASSED_AS_EXPECTED")
                    self.record_metric("frontend_content_length", len(response.text))

                    # Check for basic HTML structure
                    response_text = response.text.lower()
                    html_indicators = {
                        "html_tag": "<html" in response_text,
                        "head_tag": "<head" in response_text,
                        "body_tag": "<body" in response_text,
                        "react_app": "react" in response_text or "app" in response_text
                    }

                    self.record_metric("html_indicators", html_indicators)

                    # Frontend should be accessible (Node.js not affected by database issues)
                    assert response.status_code == 200, (
                        f"Frontend should be accessible (Node.js), but got status {response.status_code}"
                    )

                else:
                    self.record_metric("frontend_accessibility_test", "FAILED_UNEXPECTED")
                    self.record_metric("frontend_error_response", response.text[:500])

                    raise AssertionError(
                        f"Frontend accessibility failed unexpectedly "
                        f"(Node.js should work even with backend database issues): "
                        f"Status {response.status_code}"
                    )

        except httpx.TimeoutException as e:
            response_time = time.time() - step_start
            self.record_metric("frontend_accessibility_test", "FAILED_TIMEOUT")
            self.record_metric("frontend_response_time", response_time)
            self.record_metric("frontend_timeout_error", str(e))

            raise AssertionError(
                f"Frontend accessibility timeout (unexpected for Node.js): {e}"
            )

        except Exception as e:
            response_time = time.time() - step_start
            self.record_metric("frontend_accessibility_test", "FAILED_OTHER_ERROR")
            self.record_metric("frontend_response_time", response_time)
            self.record_metric("frontend_other_error", str(e))

            raise AssertionError(f"Frontend accessibility test failed: {e}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_golden_path_step_2_backend_health_check(self):
        """
        Test Golden Path Step 2: Backend health check without Docker.

        This should FAIL for Issue #1278 - Backend service returns 503 errors
        due to SMD Phase 3 database timeout and startup failures.
        """
        step_start = time.time()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.staging_backend_url}/health")
                response_time = time.time() - step_start

                self.record_metric("backend_health_status_code", response.status_code)
                self.record_metric("backend_health_response_time", response_time)

                if response.status_code == 200:
                    # Unexpected success for Issue #1278
                    self.record_metric("backend_health_test", "PASSED_UNEXPECTED")
                    self.record_metric("backend_health_response", response.text[:500])

                    try:
                        health_data = response.json()
                        self.record_metric("backend_health_data", health_data)
                    except Exception:
                        pass

                    raise AssertionError(
                        f"Backend health check passed unexpectedly "
                        f"(Issue #1278 should cause 503 Service Unavailable): "
                        f"Status {response.status_code}, Time {response_time:.2f}s"
                    )

                elif response.status_code == 503:
                    # Expected failure for Issue #1278
                    self.record_metric("backend_health_test", "FAILED_AS_EXPECTED_503")
                    self.record_metric("backend_health_error_response", response.text[:1000])

                    # Analyze error response for Issue #1278 patterns
                    error_text = response.text.lower()
                    issue_1278_patterns = {
                        "service_unavailable": "service unavailable" in error_text,
                        "startup_failure": "startup" in error_text and "fail" in error_text,
                        "database_timeout": "database" in error_text and "timeout" in error_text,
                        "smd_phase_failure": "smd" in error_text or "phase" in error_text,
                        "container_exit": "exit" in error_text
                    }

                    found_patterns = [key for key, found in issue_1278_patterns.items() if found]
                    self.record_metric("backend_issue_1278_patterns", found_patterns)

                    raise AssertionError(
                        f"Backend health check failed with 503 Service Unavailable "
                        f"(Issue #1278 - SMD Phase 3 database timeout): "
                        f"Time {response_time:.2f}s, Patterns: {found_patterns}, "
                        f"Error: {response.text[:200]}"
                    )

                elif response.status_code == 500:
                    # Also expected for Issue #1278
                    self.record_metric("backend_health_test", "FAILED_AS_EXPECTED_500")
                    self.record_metric("backend_health_error_response", response.text[:1000])

                    raise AssertionError(
                        f"Backend health check failed with 500 Internal Server Error "
                        f"(Issue #1278 - startup failure): "
                        f"Time {response_time:.2f}s, Error: {response.text[:200]}"
                    )

                else:
                    # Other error status
                    self.record_metric("backend_health_test", f"FAILED_STATUS_{response.status_code}")
                    self.record_metric("backend_health_error_response", response.text[:1000])

                    raise AssertionError(
                        f"Backend health check failed with unexpected status {response.status_code}: "
                        f"Time {response_time:.2f}s, Error: {response.text[:200]}"
                    )

        except httpx.TimeoutException as e:
            response_time = time.time() - step_start
            self.record_metric("backend_health_test", "FAILED_AS_EXPECTED_TIMEOUT")
            self.record_metric("backend_health_response_time", response_time)
            self.record_metric("backend_health_timeout_error", str(e))

            # Expected failure for Issue #1278
            raise AssertionError(
                f"Backend health check timeout (Issue #1278 - service unavailable): "
                f"Time {response_time:.2f}s, Error: {e}"
            )

        except httpx.ConnectError as e:
            response_time = time.time() - step_start
            self.record_metric("backend_health_test", "FAILED_AS_EXPECTED_CONNECTION")
            self.record_metric("backend_health_response_time", response_time)
            self.record_metric("backend_health_connection_error", str(e))

            # Expected failure for Issue #1278
            raise AssertionError(
                f"Backend health check connection failed (Issue #1278 - service not running): "
                f"Time {response_time:.2f}s, Error: {e}"
            )

        except Exception as e:
            response_time = time.time() - step_start
            self.record_metric("backend_health_test", "FAILED_OTHER_ERROR")
            self.record_metric("backend_health_response_time", response_time)
            self.record_metric("backend_health_other_error", str(e))

            raise AssertionError(f"Backend health check test failed: {e}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_golden_path_step_3_auth_service_validation(self):
        """
        Test Golden Path Step 3: Auth service validation without Docker.

        This should FAIL for Issue #1278 - Auth service has same database
        dependency issues as backend service.
        """
        step_start = time.time()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.staging_backend_url}/auth/health")
                response_time = time.time() - step_start

                self.record_metric("auth_health_status_code", response.status_code)
                self.record_metric("auth_health_response_time", response_time)

                if response.status_code == 200:
                    # Unexpected success for Issue #1278
                    self.record_metric("auth_health_test", "PASSED_UNEXPECTED")

                    try:
                        health_data = response.json()
                        self.record_metric("auth_health_data", health_data)

                        # Check database status in auth health response
                        if isinstance(health_data, dict):
                            db_status = health_data.get('database', {}).get('status')
                            self.record_metric("auth_database_status", db_status)

                            if db_status and db_status != 'healthy':
                                raise AssertionError(
                                    f"Auth service database unhealthy "
                                    f"(Issue #1278 - database connectivity): {health_data}"
                                )

                    except Exception:
                        self.record_metric("auth_health_response", response.text[:500])

                    raise AssertionError(
                        f"Auth service health check passed unexpectedly "
                        f"(Issue #1278 should cause database timeout failures): "
                        f"Status {response.status_code}, Time {response_time:.2f}s"
                    )

                elif response.status_code in [503, 500]:
                    # Expected failure for Issue #1278
                    self.record_metric("auth_health_test", f"FAILED_AS_EXPECTED_{response.status_code}")
                    self.record_metric("auth_health_error_response", response.text[:1000])

                    # Analyze error response for auth-specific Issue #1278 patterns
                    error_text = response.text.lower()
                    auth_issue_patterns = {
                        "database_connection": "database" in error_text and "connection" in error_text,
                        "auth_service_import": "auth_service" in error_text and "import" in error_text,
                        "module_not_found": "no module named" in error_text,
                        "startup_failure": "startup" in error_text and "fail" in error_text
                    }

                    found_patterns = [key for key, found in auth_issue_patterns.items() if found]
                    self.record_metric("auth_issue_1278_patterns", found_patterns)

                    raise AssertionError(
                        f"Auth service health check failed with status {response.status_code} "
                        f"(Issue #1278 - database timeout/import failure): "
                        f"Time {response_time:.2f}s, Patterns: {found_patterns}, "
                        f"Error: {response.text[:200]}"
                    )

                else:
                    # Other error status
                    self.record_metric("auth_health_test", f"FAILED_STATUS_{response.status_code}")
                    self.record_metric("auth_health_error_response", response.text[:1000])

                    raise AssertionError(
                        f"Auth service health check failed with unexpected status {response.status_code}: "
                        f"Time {response_time:.2f}s, Error: {response.text[:200]}"
                    )

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            response_time = time.time() - step_start
            self.record_metric("auth_health_test", "FAILED_AS_EXPECTED_NETWORK")
            self.record_metric("auth_health_response_time", response_time)
            self.record_metric("auth_health_network_error", str(e))

            # Expected failure for Issue #1278
            raise AssertionError(
                f"Auth service health check network failure (Issue #1278): "
                f"Time {response_time:.2f}s, Error: {e}"
            )

        except Exception as e:
            response_time = time.time() - step_start
            self.record_metric("auth_health_test", "FAILED_OTHER_ERROR")
            self.record_metric("auth_health_response_time", response_time)
            self.record_metric("auth_health_other_error", str(e))

            raise AssertionError(f"Auth service health check test failed: {e}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_golden_path_step_4_websocket_connectivity(self):
        """
        Test Golden Path Step 4: WebSocket connectivity without Docker.

        This should FAIL for Issue #1278 - WebSocket connections fail because
        backend services are not running due to database startup failures.
        """
        step_start = time.time()

        try:
            websocket_url = f"{self.staging_websocket_url}/ws"

            try:
                async with websockets.connect(
                    websocket_url,
                    timeout=30,
                    ping_interval=None  # Disable ping for testing
                ) as websocket:
                    connection_time = time.time() - step_start

                    self.record_metric("websocket_connection_success", True)
                    self.record_metric("websocket_connection_time", connection_time)

                    # Try to send a test message
                    test_message = {
                        "type": "ping",
                        "data": {"test": "issue_1278_golden_path_validation"},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await websocket.send(json.dumps(test_message))

                    # Try to receive a response
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=10.0
                        )

                        self.record_metric("websocket_message_exchange", True)
                        self.record_metric("websocket_response", response[:500])
                        self.record_metric("websocket_test", "PASSED_UNEXPECTED")

                        # Unexpected success for Issue #1278
                        raise AssertionError(
                            f"WebSocket connection and message exchange succeeded unexpectedly "
                            f"(Issue #1278 should cause WebSocket failures due to backend unavailability): "
                            f"Connection time {connection_time:.2f}s"
                        )

                    except asyncio.TimeoutError:
                        self.record_metric("websocket_message_exchange", False)
                        self.record_metric("websocket_test", "PARTIAL_CONNECTION_NO_RESPONSE")

                        # Connection worked but no response - backend processing failure
                        raise AssertionError(
                            f"WebSocket connected but no response to messages "
                            f"(Issue #1278 - backend processing unavailable): "
                            f"Connection time {connection_time:.2f}s"
                        )

            except websockets.ConnectionClosed as e:
                connection_time = time.time() - step_start
                self.record_metric("websocket_connection_success", False)
                self.record_metric("websocket_connection_time", connection_time)
                self.record_metric("websocket_connection_error", str(e))
                self.record_metric("websocket_test", "FAILED_AS_EXPECTED_CONNECTION_CLOSED")

                # Expected failure for Issue #1278
                raise AssertionError(
                    f"WebSocket connection closed immediately "
                    f"(Issue #1278 - backend startup failure): "
                    f"Time {connection_time:.2f}s, Error: {e}"
                )

            except websockets.InvalidStatusCode as e:
                connection_time = time.time() - step_start
                self.record_metric("websocket_connection_success", False)
                self.record_metric("websocket_connection_time", connection_time)
                self.record_metric("websocket_status_code_error", str(e))
                self.record_metric("websocket_test", "FAILED_AS_EXPECTED_INVALID_STATUS")

                # Expected failure for Issue #1278 - likely 503/500 from backend
                raise AssertionError(
                    f"WebSocket invalid status code "
                    f"(Issue #1278 - backend 503/500 error): "
                    f"Time {connection_time:.2f}s, Error: {e}"
                )

            except (OSError, ConnectionError) as e:
                connection_time = time.time() - step_start
                self.record_metric("websocket_connection_success", False)
                self.record_metric("websocket_connection_time", connection_time)
                self.record_metric("websocket_network_error", str(e))
                self.record_metric("websocket_test", "FAILED_AS_EXPECTED_NETWORK_ERROR")

                # Expected failure for Issue #1278
                raise AssertionError(
                    f"WebSocket network connection failure "
                    f"(Issue #1278 - infrastructure/backend unavailability): "
                    f"Time {connection_time:.2f}s, Error: {e}"
                )

        except asyncio.TimeoutError as e:
            connection_time = time.time() - step_start
            self.record_metric("websocket_connection_success", False)
            self.record_metric("websocket_connection_time", connection_time)
            self.record_metric("websocket_timeout_error", str(e))
            self.record_metric("websocket_test", "FAILED_AS_EXPECTED_TIMEOUT")

            # Expected failure for Issue #1278
            raise AssertionError(
                f"WebSocket connection timeout "
                f"(Issue #1278 - service unavailable): "
                f"Time {connection_time:.2f}s, Error: {e}"
            )

        except Exception as e:
            connection_time = time.time() - step_start
            self.record_metric("websocket_connection_success", False)
            self.record_metric("websocket_connection_time", connection_time)
            self.record_metric("websocket_other_error", str(e))
            self.record_metric("websocket_test", "FAILED_OTHER_ERROR")

            raise AssertionError(f"WebSocket connectivity test failed: {e}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_golden_path_complete_flow_summary(self):
        """
        Test complete Golden Path flow summary for Issue #1278.

        This test runs all Golden Path steps in sequence to provide a complete
        picture of the Issue #1278 impact on the user journey.
        """
        golden_path_steps = []
        start_time = time.time()

        # Step 1: Frontend
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                frontend_response = await client.get(self.staging_frontend_url)

            golden_path_steps.append({
                "step": 1,
                "name": "Frontend Accessibility",
                "status": "success" if frontend_response.status_code == 200 else "failed",
                "status_code": frontend_response.status_code,
                "expected": "success"  # Frontend should work (Node.js)
            })

        except Exception as e:
            golden_path_steps.append({
                "step": 1,
                "name": "Frontend Accessibility",
                "status": "failed",
                "error": str(e)[:100],
                "expected": "success"
            })

        # Step 2: Backend Health
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                backend_response = await client.get(f"{self.staging_backend_url}/health")

            golden_path_steps.append({
                "step": 2,
                "name": "Backend Health",
                "status": "success" if backend_response.status_code == 200 else "failed",
                "status_code": backend_response.status_code,
                "expected": "failed"  # Should fail for Issue #1278
            })

        except Exception as e:
            golden_path_steps.append({
                "step": 2,
                "name": "Backend Health",
                "status": "failed",
                "error": str(e)[:100],
                "expected": "failed"
            })

        # Step 3: Auth Service
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                auth_response = await client.get(f"{self.staging_backend_url}/auth/health")

            golden_path_steps.append({
                "step": 3,
                "name": "Auth Service",
                "status": "success" if auth_response.status_code == 200 else "failed",
                "status_code": auth_response.status_code,
                "expected": "failed"  # Should fail for Issue #1278
            })

        except Exception as e:
            golden_path_steps.append({
                "step": 3,
                "name": "Auth Service",
                "status": "failed",
                "error": str(e)[:100],
                "expected": "failed"
            })

        # Step 4: WebSocket
        try:
            async with websockets.connect(
                f"{self.staging_websocket_url}/ws",
                timeout=10
            ) as websocket:
                await websocket.send(json.dumps({"type": "ping"}))
                await asyncio.wait_for(websocket.recv(), timeout=5.0)

            golden_path_steps.append({
                "step": 4,
                "name": "WebSocket Connectivity",
                "status": "success",
                "expected": "failed"  # Should fail for Issue #1278
            })

        except Exception as e:
            golden_path_steps.append({
                "step": 4,
                "name": "WebSocket Connectivity",
                "status": "failed",
                "error": str(e)[:100],
                "expected": "failed"
            })

        total_time = time.time() - start_time

        # Analyze results
        total_steps = len(golden_path_steps)
        successful_steps = sum(1 for step in golden_path_steps if step["status"] == "success")
        failed_steps = sum(1 for step in golden_path_steps if step["status"] == "failed")

        # Check alignment with expectations
        expected_results = []
        unexpected_results = []

        for step in golden_path_steps:
            if step["status"] == step["expected"]:
                expected_results.append(step)
            else:
                unexpected_results.append(step)

        self.record_metric("golden_path_steps", golden_path_steps)
        self.record_metric("golden_path_total_steps", total_steps)
        self.record_metric("golden_path_successful_steps", successful_steps)
        self.record_metric("golden_path_failed_steps", failed_steps)
        self.record_metric("golden_path_expected_results", len(expected_results))
        self.record_metric("golden_path_unexpected_results", len(unexpected_results))
        self.record_metric("golden_path_total_time", total_time)

        # Validate Issue #1278 pattern
        if len(unexpected_results) > 0:
            # Some results don't match Issue #1278 expectations
            unexpected_details = [
                f"Step {step['step']}: {step['name']} - "
                f"Expected {step['expected']}, got {step['status']}"
                for step in unexpected_results
            ]

            self.record_metric("golden_path_test", "PARTIAL_ISSUE_1278_PATTERN")

            raise AssertionError(
                f"Golden Path partially matches Issue #1278 pattern: "
                f"{len(expected_results)}/{total_steps} steps as expected, "
                f"Unexpected: {unexpected_details}"
            )

        else:
            # All results match Issue #1278 expectations
            self.record_metric("golden_path_test", "COMPLETE_ISSUE_1278_PATTERN")

            # This indicates Issue #1278 is fully reproducing
            raise AssertionError(
                f"Golden Path completely matches Issue #1278 failure pattern: "
                f"Frontend accessible (Node.js working), "
                f"Backend/Auth/WebSocket failed (Python services with database dependencies)"
            )