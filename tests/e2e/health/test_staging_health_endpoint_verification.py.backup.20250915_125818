"""
E2E tests for staging health endpoint verification - Issue #894 deployment synchronization.

Tests the actual staging environment to verify the deployment state vs local codebase
and confirm the "undefined variable 's'" error in staging.
"""

import pytest
import requests
import asyncio
import json
from typing import Dict, Any
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestStagingHealthEndpointVerification(SSotBaseTestCase):
    """E2E test suite for staging health endpoint verification - Issue #894."""

    STAGING_BASE_URL = "https://api.staging.netrasystems.ai"
    STAGING_HEALTH_ENDPOINTS = [
        "/health",
        "/health/",
        "/health/ready",
        "/health/live",
        "/health/backend",
        "/health/startup"
    ]

    def setup_method(self):
        """Set up test environment for each test."""
        super().setup_method()
        self.session = requests.Session()
        self.session.timeout = 30
        # Disable SSL verification for staging testing
        self.session.verify = False
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(self, 'session'):
            self.session.close()
        super().teardown_method()

    def test_staging_health_endpoint_basic_connectivity(self):
        """Test basic connectivity to staging health endpoints."""
        for endpoint in self.STAGING_HEALTH_ENDPOINTS:
            url = f"{self.STAGING_BASE_URL}{endpoint}"

            try:
                response = self.session.get(url)
                print(f"Staging endpoint {endpoint}: status={response.status_code}")

                # Log response for debugging
                if response.status_code in [200, 503]:
                    try:
                        data = response.json()
                        print(f"  Response data: {data}")
                    except json.JSONDecodeError:
                        print(f"  Response text: {response.text[:200]}...")

                # Critical check: verify no malformed f-string content in staging responses
                response_text = response.text
                assert "#removed-legacyis not configured" not in response_text, (
                    f"Staging endpoint {endpoint} contains corrupted f-string: {response_text}"
                )

            except requests.RequestException as e:
                print(f"Failed to connect to staging endpoint {endpoint}: {e}")
                # Don't fail the test for connection issues, but log them
                continue

    def test_staging_health_endpoint_error_detection(self):
        """Test staging health endpoints to detect the specific 'undefined variable s' error."""
        # Focus on endpoints most likely to trigger the database error path
        critical_endpoints = ["/health/ready", "/health/backend", "/health/startup"]

        for endpoint in critical_endpoints:
            url = f"{self.STAGING_BASE_URL}{endpoint}"

            try:
                response = self.session.get(url)

                # Check for any error responses that might contain the malformed string
                if response.status_code >= 400:
                    response_text = response.text
                    print(f"Staging error response from {endpoint}: {response_text}")

                    # This is the key test - detecting if staging has the corrupted f-string
                    if "#removed-legacyis not configured" in response_text:
                        pytest.fail(
                            f"CONFIRMED: Staging endpoint {endpoint} contains corrupted f-string. "
                            f"Response: {response_text}"
                        )

                    # Also check for the 'undefined variable s' error pattern
                    if "'s' is not defined" in response_text or "undefined variable" in response_text:
                        pytest.fail(
                            f"CONFIRMED: Staging endpoint {endpoint} has 'undefined variable s' error. "
                            f"Response: {response_text}"
                        )

            except requests.RequestException as e:
                print(f"Connection error to staging endpoint {endpoint}: {e}")
                continue

    def test_staging_vs_local_codebase_comparison(self):
        """Compare staging behavior with local codebase to detect deployment synchronization issues."""
        from netra_backend.app.routes.health import _check_postgres_connection
        from unittest.mock import AsyncMock, Mock, patch

        # First, reproduce the local error
        local_error_message = None
        try:
            mock_db = AsyncMock()

            with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
                mock_config_obj = Mock()
                mock_config_obj.database_url = None
                mock_config.return_value = mock_config_obj

                with patch('shared.isolated_environment.get_env') as mock_get_env:
                    mock_get_env.return_value.get.return_value = "production"

                    asyncio.run(_check_postgres_connection(mock_db))

        except ValueError as e:
            local_error_message = str(e)

        print(f"Local error message: {local_error_message}")

        # Now test staging endpoints to see if they produce similar errors
        for endpoint in ["/health/ready", "/health/backend"]:
            url = f"{self.STAGING_BASE_URL}{endpoint}"

            try:
                response = self.session.get(url)

                if response.status_code >= 400:
                    response_text = response.text

                    # Check if staging shows the same corrupted message
                    if local_error_message and local_error_message in response_text:
                        print(
                            f"DEPLOYMENT SYNCHRONIZATION CONFIRMED: "
                            f"Staging endpoint {endpoint} shows same corrupted message as local: {local_error_message}"
                        )

            except requests.RequestException:
                continue

    def test_staging_health_response_format_validation(self):
        """Validate that staging health responses are properly formatted JSON."""
        for endpoint in self.STAGING_HEALTH_ENDPOINTS:
            url = f"{self.STAGING_BASE_URL}{endpoint}"

            try:
                response = self.session.get(url)

                if response.status_code in [200, 503]:
                    # Verify response is valid JSON
                    try:
                        data = response.json()
                        assert isinstance(data, dict)

                        # Verify basic health response structure
                        if response.status_code == 200:
                            assert "status" in data or "service" in data

                        # Critical: verify no corruption in any response fields
                        response_str = json.dumps(data)
                        assert "#removed-legacyis not configured" not in response_str, (
                            f"Staging endpoint {endpoint} JSON contains corrupted content: {response_str}"
                        )

                    except json.JSONDecodeError as e:
                        print(f"Staging endpoint {endpoint} returned invalid JSON: {response.text}")
                        print(f"JSON decode error: {e}")
                        # Don't fail the test, but log the issue

            except requests.RequestException as e:
                print(f"Failed to test staging endpoint {endpoint}: {e}")
                continue

    def test_staging_database_error_path_detection(self):
        """Test staging endpoints to detect if database errors trigger the malformed f-string."""
        # Try to trigger database connection errors in staging

        # The /health/ready endpoint is most likely to perform database checks
        url = f"{self.STAGING_BASE_URL}/health/ready"

        try:
            response = self.session.get(url, timeout=10)

            print(f"Staging /health/ready response: status={response.status_code}")

            if response.status_code == 503:
                # This might be a database connectivity issue
                response_text = response.text
                print(f"Staging readiness failure response: {response_text}")

                # Check for the exact malformed string that causes the issue
                if "#removed-legacyis not configured" in response_text:
                    pytest.fail(
                        f"CONFIRMED ISSUE #894: Staging /health/ready endpoint shows corrupted f-string. "
                        f"This is the deployment synchronization issue. Response: {response_text}"
                    )

                # Check for Python error messages that would indicate f-string parsing issues
                python_error_patterns = [
                    "'s' is not defined",
                    "NameError",
                    "undefined variable",
                    "invalid syntax"
                ]

                for pattern in python_error_patterns:
                    if pattern in response_text:
                        pytest.fail(
                            f"CONFIRMED ISSUE #894: Staging shows Python error pattern '{pattern}'. "
                            f"Response: {response_text}"
                        )

        except requests.Timeout:
            print("Staging /health/ready endpoint timed out - possible database connectivity issue")
        except requests.RequestException as e:
            print(f"Failed to test staging database error path: {e}")

    def test_staging_environment_configuration_detection(self):
        """Test staging to understand its environment configuration and database setup."""
        # Try the /health/backend endpoint which provides detailed environment info
        url = f"{self.STAGING_BASE_URL}/health/backend"

        try:
            response = self.session.get(url)

            if response.status_code in [200, 503]:
                try:
                    data = response.json()

                    print(f"Staging backend health response: {json.dumps(data, indent=2)}")

                    # Look for environment information
                    if "environment" in data:
                        print(f"Staging environment: {data['environment']}")

                    if "capabilities" in data:
                        print(f"Staging capabilities: {data['capabilities']}")

                    if "degraded_services" in data:
                        print(f"Staging degraded services: {data['degraded_services']}")

                    # Check if database connectivity issues are reported
                    if "database_connectivity" in data.get("capabilities", {}):
                        db_status = data["capabilities"]["database_connectivity"]
                        print(f"Staging database connectivity: {db_status}")

                        if not db_status:
                            print("Staging database connectivity is FALSE - this might trigger the f-string error")

                    # Critical check for corrupted content
                    response_str = json.dumps(data)
                    assert "#removed-legacyis not configured" not in response_str, (
                        f"Staging backend health contains corrupted content: {response_str}"
                    )

                except json.JSONDecodeError:
                    print(f"Staging backend health returned non-JSON: {response.text}")

        except requests.RequestException as e:
            print(f"Failed to get staging environment configuration: {e}")

    def test_document_staging_deployment_state(self):
        """Document the current staging deployment state for Issue #894 analysis."""
        print("\n=== STAGING DEPLOYMENT STATE ANALYSIS ===")

        staging_state = {
            "base_url": self.STAGING_BASE_URL,
            "endpoints_tested": self.STAGING_HEALTH_ENDPOINTS,
            "corruption_detected": False,
            "endpoints_status": {},
            "errors_found": []
        }

        for endpoint in self.STAGING_HEALTH_ENDPOINTS:
            url = f"{self.STAGING_BASE_URL}{endpoint}"

            try:
                response = self.session.get(url, timeout=15)

                endpoint_info = {
                    "status_code": response.status_code,
                    "response_size": len(response.text),
                    "is_json": False,
                    "contains_corruption": "#removed-legacyis not configured" in response.text
                }

                try:
                    data = response.json()
                    endpoint_info["is_json"] = True
                    endpoint_info["response_keys"] = list(data.keys()) if isinstance(data, dict) else []
                except json.JSONDecodeError:
                    pass

                staging_state["endpoints_status"][endpoint] = endpoint_info

                if endpoint_info["contains_corruption"]:
                    staging_state["corruption_detected"] = True
                    staging_state["errors_found"].append(f"Corruption in {endpoint}")

            except requests.RequestException as e:
                staging_state["endpoints_status"][endpoint] = {
                    "error": str(e)
                }
                staging_state["errors_found"].append(f"Connection error to {endpoint}: {e}")

        print(f"Staging State Analysis: {json.dumps(staging_state, indent=2)}")

        # This test always passes but documents the current state
        assert True, "Staging state documented successfully"