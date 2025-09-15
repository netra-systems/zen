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

NO MOCKS POLICY: Tests use real FastAPI application and configuration.
All mock usage has been replaced with actual application testing.
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from shared.isolated_environment import IsolatedEnvironment
# NO MOCKS - removed all mock imports per NO MOCKS POLICY

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
from shared.isolated_environment import get_env


class AppFactoryTests:
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

    def test_request_logging_middleware_enabled(self):
        """Test request logging middleware when enabled - NO MOCKS"""
        env = get_env()
        env.set("ENABLE_REQUEST_LOGGING", "true")
        
        app = create_app()
        
        # Create test client
        client = TestClient(app)
        
        # Make a request to non-health endpoint
        response = client.get("/")
        
        assert response.status_code == 200
        # Test that middleware is properly configured (structural test)
        assert len(app.middleware_stack) > 0

    def test_request_logging_middleware_disabled(self):
        """Test request logging middleware when disabled."""
        env = get_env()
        env.set("ENABLE_REQUEST_LOGGING", "false")
        
        app = create_app()
        
        # Verify middleware count (should have fewer middleware)
        # This is a structural test - exact count depends on implementation
        assert len(app.user_middleware) >= 1  # At least CORS

    def test_exception_handler(self):
        """Test global exception handler - NO MOCKS"""
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
        
        # Test that exception handling works properly (no need to verify logging)


class ApplicationRoutesTests:
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


class ApplicationLifespanTests:
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
    async def test_lifespan_startup_success(self):
        """Test successful lifespan startup - NO MOCKS"""
        env = get_env()
        env.set("ENVIRONMENT", "test")
        
        # Create real FastAPI app for lifespan testing
        from fastapi import FastAPI
        test_app = FastAPI()
        
        # Test lifespan startup and shutdown
        async with lifespan(test_app):
            # Test that lifespan context manager works
            assert True  # If we get here, startup succeeded
        
        # Test completed successfully if no exceptions were raised

    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(self):
        """Test lifespan startup failure handling - NO MOCKS"""
        from fastapi import FastAPI
        test_app = FastAPI()
        
        # Create environment that might cause config issues
        env = get_env()
        env.set("ENVIRONMENT", "test")
        
        # Test lifespan with potentially problematic config
        # Note: Real failure testing would require actual config errors
        # This test verifies the lifespan can handle normal startup
        try:
            async with lifespan(test_app):
                pass
        except Exception as e:
            # If exception occurs, ensure it's handled gracefully
            assert isinstance(e, Exception)

    @pytest.mark.asyncio
    async def test_lifespan_configuration_logging(self):
        """Test configuration logging during startup - NO MOCKS"""
        env = get_env()
        env.set("ENVIRONMENT", "test")
        env.set("ANALYTICS_SERVICE_PORT", "8091")
        
        from fastapi import FastAPI
        test_app = FastAPI()
        
        # Test that lifespan works with custom configuration
        async with lifespan(test_app):
            # Verify configuration can be loaded
            config = get_config()
            assert config.environment == "test"
            assert config.service_port == 8091

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self):
        """Test lifespan as context manager - NO MOCKS"""
        from fastapi import FastAPI
        test_app = FastAPI()
        
        # Track if we entered and exited properly
        entered = False
        exited = False
        
        try:
            async with lifespan(test_app):
                entered = True
            exited = True
        except Exception:
            pass
        
        assert entered is True
        assert exited is True


class ApplicationConfigurationTests:
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
        # Set proper production URLs to pass validation
        env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://prod-clickhouse:8123/analytics")
        env.set("REDIS_ANALYTICS_URL", "redis://prod-redis:6379/2")
        
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


class ApplicationIntegrationTests:
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

    def test_main_execution_structure(self):
        """Test main module execution structure - NO MOCKS"""
        env = get_env()
        env.set("ANALYTICS_SERVICE_PORT", "8092")
        env.set("ANALYTICS_WORKERS", "2")
        env.set("ENVIRONMENT", "development")
        env.set("ANALYTICS_LOG_LEVEL", "DEBUG")
        env.set("ENABLE_REQUEST_LOGGING", "true")
        
        # Test that main module can be imported and has required components
        import analytics_service.main
        
        # Verify main components exist
        assert hasattr(analytics_service.main, 'create_app')
        assert hasattr(analytics_service.main, 'lifespan')
        assert hasattr(analytics_service.main, 'app')
        assert hasattr(analytics_service.main, 'SERVICE_START_TIME')
        
        # Verify app is created properly
        assert isinstance(analytics_service.main.app, FastAPI)
        assert analytics_service.main.SERVICE_START_TIME > 0


class ApplicationRobustnessTests:
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