"""
Integration tests for health endpoint behavior - Issue #894 deployment synchronization.

Tests the health endpoint behavior to reproduce and validate the staging deployment issue
where f-string errors cause health check failures.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request, Response


class TestHealthEndpointIntegration(SSotAsyncTestCase):
    """Integration test suite for health endpoint - Issue #894."""

    def setup_method(self):
        """Set up test environment for each test."""
        super().setup_method()
        # Import the router after setup to ensure proper initialization
        from netra_backend.app.routes.health import router
        self.health_router = router

    def test_health_endpoint_basic_response_structure(self):
        """Test that health endpoint returns proper response structure without f-string errors."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from netra_backend.app.routes.health import router

        # Create a minimal FastAPI app for testing
        app = FastAPI()
        app.include_router(router, prefix="/health", tags=["health"])

        # Mock app state to avoid startup dependencies
        app.state.startup_complete = True

        with TestClient(app) as client:
            # Mock the health interface to avoid database dependencies
            with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
                mock_health_interface.get_health_status.return_value = {
                    "status": "healthy",
                    "checks": {"postgres": True},
                    "uptime_seconds": 100,
                    "healthy": True
                }

                response = client.get("/health/")

                # Verify response structure
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, dict)
                assert "status" in data

                # Most importantly, verify no f-string corruption in response
                response_text = response.text
                assert "#removed-legacyis not configured" not in response_text, (
                    "Health endpoint response contains corrupted f-string content"
                )

    def test_health_endpoint_database_error_path(self):
        """Test health endpoint behavior when database errors occur - reproduces Issue #894."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from netra_backend.app.routes.health import router

        app = FastAPI()
        app.include_router(router, prefix="/health", tags=["health"])
        app.state.startup_complete = True

        with TestClient(app) as client:
            # Mock health interface to simulate database connection failure
            with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
                # This should trigger the error path that contains the malformed f-string
                mock_health_interface.get_health_status.side_effect = Exception("Database connection failed")

                response = client.get("/health/")

                # The response might be 503 or 200 with error details, but should not contain malformed strings
                response_text = response.text

                # Check for the specific corruption that causes staging issues
                assert "#removed-legacyis not configured" not in response_text, (
                    f"Health endpoint error response contains corrupted string. "
                    f"Response: {response_text}"
                )

                # The response should be valid JSON even in error cases
                try:
                    data = response.json()
                    assert isinstance(data, dict)
                except json.JSONDecodeError:
                    pytest.fail(f"Health endpoint returned invalid JSON: {response_text}")

    async def test_postgres_connection_check_error_message(self):
        """Test the specific function that contains the malformed f-string."""
        from netra_backend.app.routes.health import _check_postgres_connection
        from unittest.mock import AsyncMock, patch

        # Mock database session
        mock_db = AsyncMock()

        # Mock config to have database_url = None (triggers the error path)
        with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
            mock_config_obj = Mock()
            mock_config_obj.database_url = None
            mock_config.return_value = mock_config_obj

            # Mock environment to be production (triggers the error)
            with patch('shared.isolated_environment.get_env') as mock_get_env:
                mock_get_env.return_value.get.return_value = "production"

                # This should raise the ValueError with malformed f-string
                with pytest.raises(ValueError) as exc_info:
                    await _check_postgres_connection(mock_db)

                error_message = str(exc_info.value)

                # Document the exact error that's causing staging issues
                assert error_message == "#removed-legacyis not configured", (
                    f"Expected malformed error message, got: {error_message}"
                )

                # This confirms the issue exists in both local and staging
                print(f"✓ Confirmed malformed f-string error: {error_message}")

    def test_health_endpoint_with_mock_database_url_none(self):
        """Integration test simulating the exact conditions that trigger the f-string error."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from netra_backend.app.routes.health import router

        app = FastAPI()
        app.include_router(router, prefix="/health", tags=["health"])
        app.state.startup_complete = True

        with TestClient(app) as client:
            # Mock all the components to trigger the specific error path
            with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
                mock_config_obj = Mock()
                mock_config_obj.database_url = None  # This triggers the error path
                mock_config.return_value = mock_config_obj

                with patch('shared.isolated_environment.get_env') as mock_get_env:
                    mock_get_env.return_value.get.return_value = "production"

                    with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
                        # This will cause the _check_postgres_connection to fail with the malformed string
                        mock_health_interface.get_health_status.return_value = {
                            "status": "healthy",
                            "checks": {"postgres": True},
                            "uptime_seconds": 100,
                            "healthy": True
                        }

                        # Test the ready endpoint which calls _check_postgres_connection
                        response = client.get("/health/ready")

                        # This might return 503 due to the database error
                        # but we're checking that the error doesn't leak the malformed string
                        response_text = response.text

                        # The malformed string should not appear in the HTTP response
                        assert "#removed-legacyis not configured" not in response_text, (
                            f"Malformed f-string leaked into HTTP response: {response_text}"
                        )

    def test_health_endpoint_startup_health_check(self):
        """Test the startup health endpoint that might expose f-string issues."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from netra_backend.app.routes.health import router

        app = FastAPI()
        app.include_router(router, prefix="/health", tags=["health"])
        app.state.startup_complete = True

        with TestClient(app) as client:
            with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
                mock_health_interface.get_health_status.return_value = {
                    "status": "healthy",
                    "checks": {"postgres": True},
                    "uptime_seconds": 100,
                    "healthy": True
                }

                # Mock database dependency
                with patch('netra_backend.app.routes.health.get_db') as mock_get_db:
                    mock_db = AsyncMock()
                    mock_get_db.return_value.__aenter__.return_value = mock_db

                    response = client.get("/health/startup")

                    # Check response is valid
                    assert response.status_code in [200, 503]  # Either ready or not ready

                    response_text = response.text
                    assert "#removed-legacyis not configured" not in response_text, (
                        f"Startup health endpoint contains corrupted string: {response_text}"
                    )

    def test_health_backend_endpoint_integration(self):
        """Test the /health/backend endpoint that performs comprehensive checks."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from netra_backend.app.routes.health import router

        app = FastAPI()
        app.include_router(router, prefix="/health", tags=["health"])
        app.state.startup_complete = True

        with TestClient(app) as client:
            # Mock various dependencies
            with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
                mock_config_obj = Mock()
                mock_config_obj.environment = "staging"
                mock_config.return_value = mock_config_obj

                with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
                    mock_health_interface.get_health_status.return_value = {
                        "status": "healthy",
                        "checks": {"postgres": True},
                        "uptime_seconds": 100,
                        "healthy": True
                    }

                    response = client.get("/health/backend")

                    # Verify response structure
                    assert response.status_code in [200, 503]
                    data = response.json()
                    assert isinstance(data, dict)
                    assert "service" in data
                    assert "status" in data

                    # Critical check: no corrupted strings in response
                    response_text = response.text
                    assert "#removed-legacyis not configured" not in response_text, (
                        f"Backend health endpoint contains corrupted string: {response_text}"
                    )

    def test_health_error_response_consistency(self):
        """Test that health error responses are consistently formatted without corruption."""
        from netra_backend.app.routes.health import _create_error_response

        # Test the error response builder with various status codes
        test_cases = [
            (503, {"status": "unhealthy", "message": "Service unavailable"}),
            (500, {"status": "error", "message": "Internal server error"}),
            (429, {"status": "throttled", "message": "Rate limited"}),
        ]

        for status_code, response_data in test_cases:
            error_response = _create_error_response(status_code, response_data)

            # Verify the response is properly formatted
            assert error_response.status_code == status_code
            assert error_response.media_type == "application/json"

            # Parse the content to verify it's valid JSON
            content = json.loads(error_response.body.decode())
            assert isinstance(content, dict)
            assert content == response_data

            # Critical: verify no corruption in the response
            content_str = str(content)
            assert "#removed-legacyis not configured" not in content_str, (
                f"Error response contains corrupted string: {content_str}"
            )

    def test_health_endpoint_staging_environment_simulation(self):
        """Simulate the exact staging environment conditions that cause the Issue #894 error."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from netra_backend.app.routes.health import router

        app = FastAPI()
        app.include_router(router, prefix="/health", tags=["health"])

        # Simulate staging environment state
        app.state.startup_complete = True

        with TestClient(app) as client:
            # Set up staging-like environment
            with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
                mock_config_obj = Mock()
                mock_config_obj.environment = "staging"
                mock_config_obj.database_url = None  # This triggers the error path in staging
                mock_config.return_value = mock_config_obj

                with patch('shared.isolated_environment.get_env') as mock_get_env:
                    # Simulate staging environment variables
                    mock_get_env.return_value.get.side_effect = lambda key, default=None: {
                        "ENVIRONMENT": "staging",
                        "CLICKHOUSE_REQUIRED": "false",
                        "REDIS_REQUIRED": "false"
                    }.get(key, default)

                    # Try all health endpoints to see which ones fail
                    endpoints_to_test = [
                        "/health/",
                        "/health/ready",
                        "/health/live",
                        "/health/backend",
                        "/health/startup"
                    ]

                    for endpoint in endpoints_to_test:
                        try:
                            response = client.get(endpoint)
                            response_text = response.text

                            # Log the endpoint results for debugging
                            print(f"Endpoint {endpoint}: status={response.status_code}")

                            # The critical check: no malformed strings should appear in any response
                            assert "#removed-legacyis not configured" not in response_text, (
                                f"Endpoint {endpoint} returned corrupted string: {response_text}"
                            )

                        except Exception as e:
                            # Even if the endpoint fails, the error should not contain corrupted strings
                            error_str = str(e)
                            assert "#removed-legacyis not configured" not in error_str, (
                                f"Endpoint {endpoint} error contains corrupted string: {error_str}"
                            )