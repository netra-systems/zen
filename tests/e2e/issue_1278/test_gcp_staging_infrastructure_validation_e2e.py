"""
End-to-End Tests for Issue #1278 - GCP Staging Infrastructure Validation

These tests validate the complete Golden Path user flow against live GCP staging
infrastructure, reproducing the exact failures seen in Issue #1278.

Business Value Justification (BVJ):
- Segment: Platform/Production
- Business Goal: Service Reliability/Golden Path Recovery
- Value Impact: Ensure complete user flow works end-to-end in staging
- Strategic Impact: Validate $500K+ ARR infrastructure for production readiness

CRITICAL: These tests are designed to FAIL when GCP staging infrastructure
issues exist, reproducing the complete system failures seen in Issue #1278.
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import json

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestGCPStagingInfrastructureHealth(SSotAsyncTestCase):
    """
    Test GCP staging infrastructure health for Issue #1278.

    These tests should FAIL when infrastructure components are unavailable,
    demonstrating the complete system failures seen in staging.
    """

    def setup_method(self, method):
        """Setup for GCP staging tests."""
        super().setup_method(method)

        # Configure for GCP staging environment
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("TESTING", "false")  # Real environment testing
        self.set_env_var("GCP_PROJECT", "netra-staging")

        # GCP staging infrastructure endpoints
        self.staging_backend_url = "https://staging.netrasystems.ai"
        self.staging_frontend_url = "https://staging.netrasystems.ai"
        self.staging_websocket_url = "wss://api-staging.netrasystems.ai"

        # Database configuration (internal VPC)
        self.set_env_var("POSTGRES_HOST", "10.52.0.3")
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_DB", "netra_staging")
        self.set_env_var("REDIS_HOST", "10.52.0.2")
        self.set_env_var("REDIS_PORT", "6379")

        self.record_metric("test_category", "gcp_staging_infrastructure")
        self.record_metric("test_environment", "staging")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_backend_service_health_endpoint_staging(self):
        """
        Test backend service health endpoint in GCP staging.

        This should FAIL for Issue #1278 - backend service returns 503/500 errors
        due to auth_service import failures and database connectivity issues.
        """
        import httpx

        health_url = f"{self.staging_backend_url}/health"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.time()
                response = await client.get(health_url)
                response_time = time.time() - start_time

                self.record_metric("backend_health_status_code", response.status_code)
                self.record_metric("backend_health_response_time", response_time)

                if response.status_code == 200:
                    # Health check passed - unexpected for Issue #1278
                    try:
                        health_data = response.json()
                        self.record_metric("backend_health_data", health_data)
                        self.record_metric("backend_health_test", "PASSED_UNEXPECTED")
                    except Exception:
                        self.record_metric("backend_health_response", response.text[:500])

                    # This is unexpected - should fail for Issue #1278
                    self.fail(
                        f"Backend health check passed unexpectedly "
                        f"(Issue #1278 should cause 503/500 errors): {response.status_code}"
                    )

                elif response.status_code in [503, 500]:
                    # Expected failure for Issue #1278
                    self.record_metric("backend_health_test", "FAILED_AS_EXPECTED_503_500")
                    self.record_metric("backend_health_error_response", response.text[:1000])

                    # Re-raise to demonstrate Issue #1278
                    raise AssertionError(
                        f"Backend health check failed with status {response.status_code} "
                        f"(Issue #1278 - service startup failure): {response.text[:200]}"
                    )

                else:
                    # Other error code
                    self.record_metric("backend_health_test", f"FAILED_STATUS_{response.status_code}")
                    self.record_metric("backend_health_error_response", response.text[:1000])

                    raise AssertionError(
                        f"Backend health check failed with unexpected status {response.status_code}: "
                        f"{response.text[:200]}"
                    )

        except httpx.TimeoutException as e:
            self.record_metric("backend_health_test", "FAILED_TIMEOUT")
            self.record_metric("backend_health_timeout_error", str(e))

            # Timeout indicates service unavailability (Issue #1278)
            raise AssertionError(
                f"Backend health check timed out (Issue #1278 - service unavailable): {e}"
            )

        except httpx.ConnectError as e:
            self.record_metric("backend_health_test", "FAILED_CONNECTION_ERROR")
            self.record_metric("backend_health_connection_error", str(e))

            # Connection error indicates infrastructure failure (Issue #1278)
            raise AssertionError(
                f"Backend health check connection failed (Issue #1278 - infrastructure failure): {e}"
            )

        except Exception as e:
            self.record_metric("backend_health_test", "FAILED_OTHER_ERROR")
            self.record_metric("backend_health_other_error", str(e))
            raise

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_auth_service_health_endpoint_staging(self):
        """
        Test auth service health endpoint in GCP staging.

        This should FAIL for Issue #1278 - auth service has database connection
        timeouts and startup failures.
        """
        import httpx

        auth_health_url = f"{self.staging_backend_url}/auth/health"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.time()
                response = await client.get(auth_health_url)
                response_time = time.time() - start_time

                self.record_metric("auth_health_status_code", response.status_code)
                self.record_metric("auth_health_response_time", response_time)

                if response.status_code == 200:
                    try:
                        health_data = response.json()
                        self.record_metric("auth_health_data", health_data)
                        self.record_metric("auth_health_test", "PASSED_UNEXPECTED")
                    except Exception:
                        self.record_metric("auth_health_response", response.text[:500])

                    # Check for database connectivity in health response
                    if isinstance(health_data, dict):
                        db_status = health_data.get('database', {}).get('status', 'unknown')
                        self.record_metric("auth_database_status", db_status)

                        if db_status != 'healthy':
                            raise AssertionError(
                                f"Auth service database unhealthy (Issue #1278): {health_data}"
                            )

                elif response.status_code in [503, 500]:
                    # Expected failure for Issue #1278
                    self.record_metric("auth_health_test", "FAILED_AS_EXPECTED_503_500")
                    self.record_metric("auth_health_error_response", response.text[:1000])

                    raise AssertionError(
                        f"Auth service health check failed with status {response.status_code} "
                        f"(Issue #1278 - database timeout/startup failure): {response.text[:200]}"
                    )

                else:
                    self.record_metric("auth_health_test", f"FAILED_STATUS_{response.status_code}")
                    raise AssertionError(
                        f"Auth service health check failed with status {response.status_code}: "
                        f"{response.text[:200]}"
                    )

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            self.record_metric("auth_health_test", "FAILED_NETWORK_ERROR")
            self.record_metric("auth_health_network_error", str(e))

            raise AssertionError(
                f"Auth service health check network failure (Issue #1278): {e}"
            )

        except Exception as e:
            self.record_metric("auth_health_test", "FAILED_OTHER_ERROR")
            self.record_metric("auth_health_other_error", str(e))
            raise

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_connection_staging(self):
        """
        Test WebSocket connection to GCP staging.

        This should FAIL for Issue #1278 - WebSocket connections fail due to
        backend service startup failures and auth_service import errors.
        """
        import websockets
        import json

        try:
            # Attempt WebSocket connection to staging
            websocket_url = f"{self.staging_websocket_url}/ws"

            start_time = time.time()

            try:
                async with websockets.connect(
                    websocket_url,
                    timeout=30,
                    ping_interval=None  # Disable ping for testing
                ) as websocket:
                    connection_time = time.time() - start_time

                    self.record_metric("websocket_connection_success", True)
                    self.record_metric("websocket_connection_time", connection_time)

                    # Try to send a test message
                    test_message = {
                        "type": "ping",
                        "data": {"test": "issue_1278_validation"},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await websocket.send(json.dumps(test_message))

                    # Try to receive a response (with timeout)
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=10.0
                        )

                        self.record_metric("websocket_message_exchange", True)
                        self.record_metric("websocket_response", response[:500])
                        self.record_metric("websocket_test", "PASSED_UNEXPECTED")

                        # This is unexpected for Issue #1278
                        self.fail(
                            f"WebSocket connection and message exchange succeeded unexpectedly "
                            f"(Issue #1278 should cause WebSocket failures)"
                        )

                    except asyncio.TimeoutError:
                        self.record_metric("websocket_message_exchange", False)
                        self.record_metric("websocket_test", "PARTIAL_SUCCESS_NO_RESPONSE")

                        # Connection worked but no response - might indicate backend issues
                        raise AssertionError(
                            "WebSocket connected but no response to messages "
                            "(Issue #1278 - backend processing failure)"
                        )

            except websockets.exceptions.ConnectionClosed as e:
                self.record_metric("websocket_connection_success", False)
                self.record_metric("websocket_connection_error", str(e))
                self.record_metric("websocket_test", "FAILED_AS_EXPECTED_CONNECTION_CLOSED")

                # Expected failure for Issue #1278
                raise AssertionError(
                    f"WebSocket connection closed immediately (Issue #1278 - backend startup failure): {e}"
                )

            except websockets.exceptions.InvalidStatusCode as e:
                self.record_metric("websocket_connection_success", False)
                self.record_metric("websocket_status_code_error", str(e))
                self.record_metric("websocket_test", "FAILED_AS_EXPECTED_INVALID_STATUS")

                # Expected failure for Issue #1278 - likely 503/500 from backend
                raise AssertionError(
                    f"WebSocket invalid status code (Issue #1278 - backend 503/500 error): {e}"
                )

            except (OSError, ConnectionError) as e:
                self.record_metric("websocket_connection_success", False)
                self.record_metric("websocket_network_error", str(e))
                self.record_metric("websocket_test", "FAILED_AS_EXPECTED_NETWORK_ERROR")

                # Expected failure for Issue #1278
                raise AssertionError(
                    f"WebSocket network connection failure (Issue #1278 - infrastructure failure): {e}"
                )

        except asyncio.TimeoutError as e:
            self.record_metric("websocket_connection_success", False)
            self.record_metric("websocket_timeout_error", str(e))
            self.record_metric("websocket_test", "FAILED_AS_EXPECTED_TIMEOUT")

            # Expected failure for Issue #1278
            raise AssertionError(
                f"WebSocket connection timeout (Issue #1278 - service unavailable): {e}"
            )

        except Exception as e:
            self.record_metric("websocket_connection_success", False)
            self.record_metric("websocket_other_error", str(e))
            self.record_metric("websocket_test", "FAILED_OTHER_ERROR")
            raise

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_complete_golden_path_user_flow_staging(self):
        """
        Test complete Golden Path user flow in GCP staging.

        This should FAIL for Issue #1278 - complete user flow fails due to
        service startup failures, auth issues, and infrastructure problems.
        """
        import httpx

        golden_path_steps = []
        current_step = 1

        try:
            # Step 1: Frontend loads
            step_name = f"Step {current_step}: Frontend availability"
            golden_path_steps.append({"step": current_step, "name": step_name, "status": "attempting"})

            async with httpx.AsyncClient(timeout=30.0) as client:
                frontend_response = await client.get(self.staging_frontend_url)

                if frontend_response.status_code == 200:
                    golden_path_steps[-1]["status"] = "success"
                    self.record_metric(f"golden_path_step_{current_step}", "SUCCESS")
                else:
                    golden_path_steps[-1]["status"] = "failed"
                    golden_path_steps[-1]["error"] = f"Status {frontend_response.status_code}"
                    self.record_metric(f"golden_path_step_{current_step}", "FAILED")

            current_step += 1

            # Step 2: Backend API health
            step_name = f"Step {current_step}: Backend API health"
            golden_path_steps.append({"step": current_step, "name": step_name, "status": "attempting"})

            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_response = await client.get(f"{self.staging_backend_url}/health")

                if backend_response.status_code == 200:
                    golden_path_steps[-1]["status"] = "success"
                    self.record_metric(f"golden_path_step_{current_step}", "SUCCESS")
                else:
                    golden_path_steps[-1]["status"] = "failed"
                    golden_path_steps[-1]["error"] = f"Status {backend_response.status_code}"
                    self.record_metric(f"golden_path_step_{current_step}", "FAILED")

            current_step += 1

            # Step 3: Auth service functionality
            step_name = f"Step {current_step}: Auth service functionality"
            golden_path_steps.append({"step": current_step, "name": step_name, "status": "attempting"})

            async with httpx.AsyncClient(timeout=30.0) as client:
                auth_response = await client.get(f"{self.staging_backend_url}/auth/health")

                if auth_response.status_code == 200:
                    golden_path_steps[-1]["status"] = "success"
                    self.record_metric(f"golden_path_step_{current_step}", "SUCCESS")
                else:
                    golden_path_steps[-1]["status"] = "failed"
                    golden_path_steps[-1]["error"] = f"Status {auth_response.status_code}"
                    self.record_metric(f"golden_path_step_{current_step}", "FAILED")

            current_step += 1

            # Step 4: WebSocket connectivity
            step_name = f"Step {current_step}: WebSocket connectivity"
            golden_path_steps.append({"step": current_step, "name": step_name, "status": "attempting"})

            import websockets

            try:
                async with websockets.connect(
                    f"{self.staging_websocket_url}/ws",
                    timeout=15
                ) as websocket:
                    # Send ping message
                    await websocket.send(json.dumps({"type": "ping"}))

                    # Try to get response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        golden_path_steps[-1]["status"] = "success"
                        self.record_metric(f"golden_path_step_{current_step}", "SUCCESS")
                    except asyncio.TimeoutError:
                        golden_path_steps[-1]["status"] = "partial"
                        golden_path_steps[-1]["error"] = "Connected but no response"
                        self.record_metric(f"golden_path_step_{current_step}", "PARTIAL")

            except Exception as e:
                golden_path_steps[-1]["status"] = "failed"
                golden_path_steps[-1]["error"] = str(e)[:200]
                self.record_metric(f"golden_path_step_{current_step}", "FAILED")

            current_step += 1

            # Step 5: Database connectivity (through backend)
            step_name = f"Step {current_step}: Database connectivity"
            golden_path_steps.append({"step": current_step, "name": step_name, "status": "attempting"})

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try database health endpoint if available
                try:
                    db_response = await client.get(f"{self.staging_backend_url}/health/database")

                    if db_response.status_code == 200:
                        golden_path_steps[-1]["status"] = "success"
                        self.record_metric(f"golden_path_step_{current_step}", "SUCCESS")
                    else:
                        golden_path_steps[-1]["status"] = "failed"
                        golden_path_steps[-1]["error"] = f"Status {db_response.status_code}"
                        self.record_metric(f"golden_path_step_{current_step}", "FAILED")

                except Exception as e:
                    golden_path_steps[-1]["status"] = "failed"
                    golden_path_steps[-1]["error"] = str(e)[:200]
                    self.record_metric(f"golden_path_step_{current_step}", "FAILED")

            # Analyze overall Golden Path status
            self.record_metric("golden_path_steps", golden_path_steps)

            successful_steps = sum(1 for step in golden_path_steps if step["status"] == "success")
            failed_steps = sum(1 for step in golden_path_steps if step["status"] == "failed")
            total_steps = len(golden_path_steps)

            self.record_metric("golden_path_successful_steps", successful_steps)
            self.record_metric("golden_path_failed_steps", failed_steps)
            self.record_metric("golden_path_total_steps", total_steps)
            self.record_metric("golden_path_success_rate", successful_steps / total_steps)

            if failed_steps > 0:
                # Expected failure for Issue #1278
                failed_step_details = [
                    f"Step {step['step']}: {step['name']} - {step.get('error', 'Failed')}"
                    for step in golden_path_steps
                    if step["status"] == "failed"
                ]

                self.record_metric("golden_path_test", "FAILED_AS_EXPECTED")
                self.record_metric("golden_path_failure_details", failed_step_details)

                raise AssertionError(
                    f"Golden Path failed at {failed_steps}/{total_steps} steps (Issue #1278): "
                    f"{failed_step_details}"
                )
            else:
                # Unexpected success for Issue #1278
                self.record_metric("golden_path_test", "PASSED_UNEXPECTED")
                self.fail(
                    f"Golden Path succeeded unexpectedly - all {total_steps} steps passed "
                    f"(Issue #1278 should cause infrastructure failures)"
                )

        except Exception as e:
            # Add error information to current step if it exists
            if golden_path_steps and golden_path_steps[-1]["status"] == "attempting":
                golden_path_steps[-1]["status"] = "failed"
                golden_path_steps[-1]["error"] = str(e)[:200]

            self.record_metric("golden_path_steps", golden_path_steps)
            self.record_metric("golden_path_test", "FAILED_EXCEPTION")
            self.record_metric("golden_path_exception", str(e))

            # Re-raise as expected failure for Issue #1278
            raise AssertionError(f"Golden Path failed with exception (Issue #1278): {e}")


class TestGCPContainerStartupValidation(SSotAsyncTestCase):
    """
    Test GCP container startup validation for Issue #1278.

    These tests validate container startup behavior and exit codes that
    are reported in GCP logs for Issue #1278.
    """

    def setup_method(self, method):
        """Setup for container startup tests."""
        super().setup_method(method)

        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("GCP_PROJECT", "netra-staging")

        self.record_metric("test_category", "gcp_container_startup")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_backend_container_startup_logs_validation(self):
        """
        Test backend container startup logs for Issue #1278 indicators.

        This test validates that container startup logs show the specific
        error patterns identified in Issue #1278 analysis.
        """
        import httpx

        # Try to access backend and analyze response for startup indicators
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.staging_backend_url}/health")

                self.record_metric("container_health_status", response.status_code)

                if response.status_code in [503, 500]:
                    # Expected for Issue #1278 - analyze error response
                    error_text = response.text.lower()

                    # Check for specific Issue #1278 error patterns
                    issue_1278_indicators = {
                        "auth_service_import": "auth_service" in error_text and "import" in error_text,
                        "module_not_found": "no module named" in error_text,
                        "container_exit": "exit" in error_text,
                        "startup_failure": any(term in error_text for term in ["startup", "initialization", "failed to start"]),
                        "dependency_error": "dependency" in error_text or "import" in error_text
                    }

                    self.record_metric("issue_1278_indicators", issue_1278_indicators)

                    found_indicators = [key for key, found in issue_1278_indicators.items() if found]
                    self.record_metric("found_issue_1278_indicators", found_indicators)

                    if found_indicators:
                        self.record_metric("container_startup_test", "FAILED_AS_EXPECTED_ISSUE_1278")
                        raise AssertionError(
                            f"Container shows Issue #1278 startup failure indicators: {found_indicators}"
                        )
                    else:
                        self.record_metric("container_startup_test", "FAILED_OTHER_CAUSE")
                        raise AssertionError(
                            f"Container startup failed (status {response.status_code}) but not with Issue #1278 patterns"
                        )

                elif response.status_code == 200:
                    # Unexpected success
                    self.record_metric("container_startup_test", "PASSED_UNEXPECTED")
                    health_data = response.text[:500]
                    self.record_metric("container_health_response", health_data)

                    self.fail(
                        f"Container startup succeeded unexpectedly (Issue #1278 should cause startup failures)"
                    )

                else:
                    # Other error code
                    self.record_metric("container_startup_test", f"FAILED_STATUS_{response.status_code}")
                    raise AssertionError(
                        f"Container responded with unexpected status {response.status_code}"
                    )

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # Network failure indicates container startup issues
            self.record_metric("container_startup_test", "FAILED_AS_EXPECTED_NETWORK")
            self.record_metric("container_network_error", str(e))

            raise AssertionError(
                f"Container startup network failure (Issue #1278 - container not running): {e}"
            )

        except Exception as e:
            self.record_metric("container_startup_test", "FAILED_OTHER_ERROR")
            self.record_metric("container_other_error", str(e))
            raise

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_service_restart_behavior_validation(self):
        """
        Test service restart behavior for Issue #1278.

        This test validates that services are experiencing the restart loop
        behavior described in Issue #1278 analysis (34 restart failures in 1 hour).
        """
        import httpx

        # Test multiple health checks over time to detect restart behavior
        health_check_results = []
        restart_indicators = []

        for attempt in range(5):
            try:
                start_time = time.time()

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{self.staging_backend_url}/health")

                response_time = time.time() - start_time

                result = {
                    "attempt": attempt + 1,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "timestamp": time.time()
                }

                health_check_results.append(result)

                # Check for restart indicators
                if response.status_code in [503, 500]:
                    restart_indicators.append(f"Attempt {attempt + 1}: Status {response.status_code}")

                # Wait between attempts
                if attempt < 4:
                    await asyncio.sleep(2)

            except Exception as e:
                result = {
                    "attempt": attempt + 1,
                    "status_code": None,
                    "response_time": None,
                    "error": str(e),
                    "timestamp": time.time()
                }

                health_check_results.append(result)
                restart_indicators.append(f"Attempt {attempt + 1}: Exception - {str(e)[:100]}")

                # Wait between attempts
                if attempt < 4:
                    await asyncio.sleep(2)

        self.record_metric("health_check_results", health_check_results)
        self.record_metric("restart_indicators", restart_indicators)

        # Analyze restart behavior
        failed_attempts = sum(1 for result in health_check_results
                            if result.get("status_code") in [503, 500, None])
        total_attempts = len(health_check_results)

        self.record_metric("failed_health_checks", failed_attempts)
        self.record_metric("total_health_checks", total_attempts)
        self.record_metric("failure_rate", failed_attempts / total_attempts)

        if failed_attempts > 0:
            # Expected for Issue #1278
            self.record_metric("restart_behavior_test", "FAILED_AS_EXPECTED_RESTART_ISSUES")
            raise AssertionError(
                f"Service restart behavior detected: {failed_attempts}/{total_attempts} failed attempts "
                f"(Issue #1278 - restart loop): {restart_indicators}"
            )
        else:
            # Unexpected stability
            self.record_metric("restart_behavior_test", "PASSED_UNEXPECTED_STABLE")
            self.fail(
                f"Service appears stable across {total_attempts} attempts "
                f"(Issue #1278 should cause restart failures)"
            )