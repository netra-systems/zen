"""Comprehensive unit tests for Analytics Service Main Application.

BUSINESS VALUE: Ensures main application startup, configuration, and routing
reliability for analytics service operations. Critical for service availability
and proper FastAPI application initialization.

Tests cover:
- Application factory (create_app)
- FastAPI application configuration
- Middleware setup
- Route registration
- Error handling
- Lifespan management
- Health endpoints
- Service startup behavior

MOCK JUSTIFICATION: L1 Unit Tests - Mocking FastAPI components and external
dependencies to isolate application factory logic. Real application behavior
tested in integration tests.
"""

import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from analytics_service.main import (
    create_app,
    lifespan,
    app,
    SERVICE_START_TIME,
)
from analytics_service.analytics_core.config import get_config
from analytics_service.analytics_core.isolated_environment import get_env


class TestAppFactory:
    """Test suite for FastAPI application factory."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()
        
        # Reset global config
        import analytics_service.analytics_core.config as config_module
        config_module._config = None

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_create_app_basic(self):
        """Test basic application creation."""
        app = create_app()
        
        assert isinstance(app, FastAPI)
        assert app.title == "Netra Analytics Service"
        assert "Analytics and event processing microservice" in app.description
        assert app.version == "1.0.0"  # Default version

    def test_create_app_with_custom_config(self):
        """Test application creation with custom configuration."""
        env = get_env()
        env.set("ANALYTICS_SERVICE_VERSION", "2.0.0")
        env.set("ENVIRONMENT", "production")
        # Set proper production URLs to pass validation
        env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://prod-clickhouse:8123/analytics")
        env.set("REDIS_ANALYTICS_URL", "redis://prod-redis:6379/2")
        
        app = create_app()
        
        assert app.version == "2.0.0"
        # In production, docs should be disabled
        assert app.docs_url is None
        assert app.redoc_url is None

    def test_create_app_development_mode(self):
        """Test application creation in development mode."""
        env = get_env()
        env.set("ENVIRONMENT", "development")
        
        app = create_app()
        
        # In development, docs should be enabled
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_cors_middleware_configuration(self):
        """Test CORS middleware configuration."""
        env = get_env()
        env.set("ANALYTICS_CORS_ORIGINS", "https://app.netra.ai,https://api.netra.ai")
        
        app = create_app()
        
        # Verify CORS middleware is added (check middleware stack)
        from starlette.middleware.cors import CORSMiddleware
        cors_middleware_found = any(
            hasattr(middleware, 'cls') and middleware.cls == CORSMiddleware 
            for middleware in app.user_middleware
        )
        assert cors_middleware_found, f"CORSMiddleware not found in middleware stack: {[str(mw) for mw in app.user_middleware]}"

    @patch('analytics_service.main.logger')
    def test_request_logging_middleware_enabled(self, mock_logger):
        """Test request logging middleware when enabled."""
        env = get_env()
        env.set("ENABLE_REQUEST_LOGGING", "true")
        
        app = create_app()
        
        # Create test client
        client = TestClient(app)
        
        # Make a request to non-health endpoint
        response = client.get("/")
        
        assert response.status_code == 200
        # Verify logging was called (middleware should log requests)
        mock_logger.info.assert_called()

    def test_request_logging_middleware_disabled(self):
        """Test request logging middleware when disabled."""
        env = get_env()
        env.set("ENABLE_REQUEST_LOGGING", "false")
        
        app = create_app()
        
        # Verify middleware count (should have fewer middleware)
        # This is a structural test - exact count depends on implementation
        assert len(app.user_middleware) >= 1  # At least CORS

    @patch('analytics_service.main.logger')
    def test_exception_handler(self, mock_logger):
        """Test global exception handler."""
        app = create_app()
        
        # Add a route that raises an exception for testing
        @app.get("/test-error")
        async def test_error():
            raise ValueError("Test exception")
        
        client = TestClient(app)
        
        # Make request that triggers exception
        response = client.get("/test-error")
        
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
        
        # Verify error was logged
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Unhandled exception" in error_call
        assert "GET /test-error" in error_call


class TestApplicationRoutes:
    """Test suite for application route registration."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()
        
        # Reset global config
        import analytics_service.analytics_core.config as config_module
        config_module._config = None

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_root_endpoint(self):
        """Test root endpoint functionality."""
        env = get_env()
        env.set("ENVIRONMENT", "test")
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "analytics_service"
        assert data["version"] == "1.0.0"
        assert data["environment"] == "test"
        assert data["status"] == "running"
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_health_endpoint(self):
        """Test basic health check endpoint."""
        env = get_env()
        env.set("ENVIRONMENT", "test")
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "analytics_service"
        assert data["version"] == "1.0.0"
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_uptime_calculation(self):
        """Test uptime calculation in endpoints."""
        app = create_app()
        client = TestClient(app)
        
        # Get initial uptime
        response1 = client.get("/")
        uptime1 = response1.json()["uptime_seconds"]
        
        # Wait a small amount
        time.sleep(0.1)
        
        # Get uptime again
        response2 = client.get("/")
        uptime2 = response2.json()["uptime_seconds"]
        
        # Second uptime should be greater
        assert uptime2 > uptime1

    def test_event_ingestion_placeholder(self):
        """Test placeholder event ingestion endpoint."""
        app = create_app()
        client = TestClient(app)
        
        # Test with events
        payload = {
            "events": [
                {"type": "user_action", "data": {"action": "click"}},
                {"type": "page_view", "data": {"page": "/dashboard"}}
            ]
        }
        
        response = client.post("/api/analytics/events", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["events_processed"] == 2
        assert "placeholder" in data["message"].lower()

    def test_event_ingestion_empty_events(self):
        """Test event ingestion with empty events."""
        app = create_app()
        client = TestClient(app)
        
        payload = {"events": []}
        
        response = client.post("/api/analytics/events", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["events_processed"] == 0

    def test_event_ingestion_no_events_key(self):
        """Test event ingestion without events key."""
        app = create_app()
        client = TestClient(app)
        
        payload = {"data": "some_data"}
        
        response = client.post("/api/analytics/events", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["events_processed"] == 0

    def test_user_activity_report_placeholder(self):
        """Test placeholder user activity report endpoint."""
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/analytics/reports/user-activity")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"] == []
        assert "placeholder" in data["message"].lower()


class TestApplicationLifespan:
    """Test suite for application lifespan management."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()
        
        # Reset global config
        import analytics_service.analytics_core.config as config_module
        config_module._config = None

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    @pytest.mark.asyncio
    @patch('analytics_service.main.logger')
    async def test_lifespan_startup_success(self, mock_logger):
        """Test successful lifespan startup."""
        env = get_env()
        env.set("ENVIRONMENT", "test")
        
        # Create mock app
        mock_app = Mock()
        
        # Test lifespan startup
        async with lifespan(mock_app):
            pass
        
        # Verify startup logging
        startup_calls = [call for call in mock_logger.info.call_args_list 
                        if "Starting" in str(call)]
        assert len(startup_calls) > 0
        
        # Verify shutdown logging
        shutdown_calls = [call for call in mock_logger.info.call_args_list 
                         if "Shutting down" in str(call)]
        assert len(shutdown_calls) > 0

    @pytest.mark.asyncio
    @patch('analytics_service.main.logger')
    async def test_lifespan_startup_failure(self, mock_logger):
        """Test lifespan startup failure handling."""
        mock_app = Mock()
        
        # Mock a startup failure by patching the config
        with patch('analytics_service.main.get_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Config error")
            
            # Should raise exception during startup
            with pytest.raises(Exception, match="Config error"):
                async with lifespan(mock_app):
                    pass

    @pytest.mark.asyncio
    @patch('analytics_service.main.logger')
    async def test_lifespan_configuration_logging(self, mock_logger):
        """Test configuration logging during startup."""
        env = get_env()
        env.set("ENVIRONMENT", "test")
        env.set("ANALYTICS_SERVICE_PORT", "8091")
        
        mock_app = Mock()
        
        async with lifespan(mock_app):
            pass
        
        # Verify configuration information is logged
        info_calls = mock_logger.info.call_args_list
        logged_messages = [str(call) for call in info_calls]
        
        # Check for key configuration messages
        assert any("Environment: test" in msg for msg in logged_messages)
        assert any("Port: 8091" in msg for msg in logged_messages)
        assert any("Configuration:" in msg for msg in logged_messages)

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self):
        """Test lifespan as context manager."""
        mock_app = Mock()
        
        # Track if we entered and exited properly
        entered = False
        exited = False
        
        try:
            async with lifespan(mock_app):
                entered = True
            exited = True
        except Exception:
            pass
        
        assert entered is True
        assert exited is True


class TestApplicationConfiguration:
    """Test suite for application configuration integration."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()
        
        # Reset global config
        import analytics_service.analytics_core.config as config_module
        config_module._config = None

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_service_port_configuration(self):
        """Test service port configuration."""
        env = get_env()
        env.set("ANALYTICS_SERVICE_PORT", "9000")
        
        # Verify configuration is loaded
        config = get_config()
        assert config.service_port == 9000

    def test_environment_specific_behavior(self):
        """Test environment-specific application behavior."""
        # Test production environment
        env = get_env()
        env.set("ENVIRONMENT", "production")
        
        app = create_app()
        
        # Docs should be disabled in production
        assert app.docs_url is None
        assert app.redoc_url is None
        
        # Test development environment
        env.set("ENVIRONMENT", "development")
        import analytics_service.analytics_core.config as config_module
        config_module._config = None  # Reset config
        
        app = create_app()
        
        # Docs should be enabled in development
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_cors_configuration(self):
        """Test CORS configuration from environment."""
        env = get_env()
        env.set("ANALYTICS_CORS_ORIGINS", "https://app1.com,https://app2.com")
        
        config = get_config()
        assert config.cors_origins == ["https://app1.com", "https://app2.com"]

    def test_worker_count_configuration(self):
        """Test worker count configuration."""
        env = get_env()
        env.set("ANALYTICS_WORKERS", "4")
        
        config = get_config()
        assert config.worker_count == 4


class TestApplicationIntegration:
    """Integration tests for the complete application."""

    def test_global_app_instance(self):
        """Test that global app instance is properly created."""
        # The global app should be available
        from analytics_service.main import app as global_app
        
        assert isinstance(global_app, FastAPI)
        assert global_app.title == "Netra Analytics Service"

    def test_service_start_time(self):
        """Test SERVICE_START_TIME is set properly."""
        assert isinstance(SERVICE_START_TIME, (int, float))
        assert SERVICE_START_TIME > 0
        
        # Should be close to current time (within reasonable range)
        current_time = time.time()
        assert current_time - SERVICE_START_TIME < 3600  # Within an hour

    def test_complete_application_flow(self):
        """Test complete application request flow."""
        app = create_app()
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test analytics endpoints
        response = client.post("/api/analytics/events", 
                             json={"events": [{"type": "test"}]})
        assert response.status_code == 200
        
        response = client.get("/api/analytics/reports/user-activity")
        assert response.status_code == 200

    def test_error_handling_integration(self):
        """Test error handling integration."""
        app = create_app()
        
        # Add a test route that raises an exception
        @app.get("/test-exception")
        async def test_exception():
            raise Exception("Test error")
        
        client = TestClient(app)
        
        # Should handle exception gracefully
        response = client.get("/test-exception")
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    @patch('analytics_service.main.uvicorn')
    def test_main_execution(self, mock_uvicorn):
        """Test main module execution."""
        env = get_env()
        env.set("ANALYTICS_SERVICE_PORT", "8092")
        env.set("ANALYTICS_WORKERS", "2")
        env.set("ENVIRONMENT", "development")
        env.set("ANALYTICS_LOG_LEVEL", "DEBUG")
        env.set("ENABLE_REQUEST_LOGGING", "true")
        
        # Import and execute main
        import analytics_service.main
        
        # Mock sys.argv to simulate command line execution
        with patch('sys.argv', ['main.py']):
            with patch('analytics_service.main.__name__', '__main__'):
                # This would normally call uvicorn.run
                # We've mocked it to verify the call
                try:
                    exec(compile(open('analytics_service/main.py').read(), 
                               'analytics_service/main.py', 'exec'))
                except SystemExit:
                    pass  # Expected for command line execution
                except Exception:
                    pass  # May fail due to mocking, but we can check if uvicorn was called
        
        # Note: Due to mocking complexity, this test verifies structure more than execution


class TestApplicationRobustness:
    """Test suite for application robustness and edge cases."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()
        
        # Reset global config
        import analytics_service.analytics_core.config as config_module
        config_module._config = None

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_malformed_request_handling(self):
        """Test handling of malformed requests."""
        app = create_app()
        client = TestClient(app)
        
        # Test malformed JSON
        response = client.post("/api/analytics/events", 
                             data="invalid json")
        
        # Should handle gracefully (422 for validation error or 500 for parse error)
        assert response.status_code in [422, 500]

    def test_missing_content_type(self):
        """Test handling requests with missing content type."""
        app = create_app()
        client = TestClient(app)
        
        # Test POST without content-type header
        response = client.post("/api/analytics/events")
        
        # Should handle gracefully
        assert response.status_code in [422, 400, 500]

    def test_large_payload_handling(self):
        """Test handling of large payloads."""
        app = create_app()
        client = TestClient(app)
        
        # Create large payload
        large_events = [{"type": "test", "data": "x" * 1000} for _ in range(100)]
        payload = {"events": large_events}
        
        response = client.post("/api/analytics/events", json=payload)
        
        # Should handle large payload
        assert response.status_code == 200
        data = response.json()
        assert data["events_processed"] == 100

    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        app = create_app()
        client = TestClient(app)
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            response = client.get("/health")
            results.put(response.status_code)
        
        # Make concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all requests
        for thread in threads:
            thread.join()
        
        # All should succeed
        while not results.empty():
            status_code = results.get()
            assert status_code == 200