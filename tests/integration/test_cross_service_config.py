"""
Integration test configuration and fixtures for cross-service testing.

Provides shared fixtures, utilities, and configuration for cross-service integration tests.
"""

import pytest
import asyncio
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Generator
import httpx

from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.health_monitor import HealthMonitor
from app.core.middleware_setup import CustomCORSMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient


class CrossServiceTestConfig:
    """Configuration and utilities for cross-service integration testing."""
    
    # Default test ports
    BACKEND_PORT = 8000
    FRONTEND_PORT = 3000
    AUTH_PORT = 8081
    
    # Test service URLs
    BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
    FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"
    AUTH_URL = f"http://localhost:{AUTH_PORT}"
    AUTH_API_URL = f"{AUTH_URL}/auth"
    
    # Test tokens and credentials
    TEST_CROSS_SERVICE_TOKEN = "test-cross-service-token-12345"
    TEST_AUTH_TOKEN = "test-auth-token-67890"
    TEST_JWT_SECRET = "test-jwt-secret-for-integration-testing"
    
    # CORS test origins
    TEST_ORIGINS = [
        BACKEND_URL,
        FRONTEND_URL,
        AUTH_URL,
        AUTH_API_URL,
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8081"
    ]


@pytest.fixture(scope="session")
def cross_service_config():
    """Provide cross-service test configuration."""
    return CrossServiceTestConfig()


@pytest.fixture
def temp_project_root():
    """Create temporary project root directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        
        # Create basic project structure
        (project_root / "app").mkdir()
        (project_root / "dev_launcher").mkdir()
        (project_root / "frontend").mkdir()
        (project_root / "auth_service").mkdir()
        (project_root / "tests").mkdir()
        
        yield project_root


@pytest.fixture
def test_service_discovery(temp_project_root, cross_service_config):
    """Create fully configured test service discovery."""
    discovery = ServiceDiscovery(temp_project_root)
    
    # Register backend service
    discovery.write_backend_info(cross_service_config.BACKEND_PORT)
    
    # Register frontend service  
    discovery.write_frontend_info(cross_service_config.FRONTEND_PORT)
    
    # Register auth service with full configuration
    auth_info = {
        'port': cross_service_config.AUTH_PORT,
        'url': cross_service_config.AUTH_URL,
        'api_url': cross_service_config.AUTH_API_URL,
        'timestamp': '2025-08-20T10:00:00Z',
        'status': 'healthy',
        'endpoints': [
            '/auth/config',
            '/auth/login',
            '/auth/callback',
            '/auth/token',
            '/auth/logout',
            '/auth/status',
            '/health'
        ]
    }
    discovery.write_auth_info(auth_info)
    
    # Set cross-service auth token
    discovery.set_cross_service_auth_token(cross_service_config.TEST_CROSS_SERVICE_TOKEN)
    
    # Register all services with CORS metadata
    discovery.register_service_for_cors('backend', {
        'port': cross_service_config.BACKEND_PORT,
        'url': cross_service_config.BACKEND_URL
    })
    discovery.register_service_for_cors('frontend', {
        'port': cross_service_config.FRONTEND_PORT, 
        'url': cross_service_config.FRONTEND_URL
    })
    discovery.register_service_for_cors('auth', auth_info)
    
    return discovery


@pytest.fixture
def test_health_monitor(test_service_discovery):
    """Create test health monitor with service discovery integration."""
    monitor = HealthMonitor(check_interval=0.1)  # Fast interval for testing
    monitor.set_service_discovery(test_service_discovery)
    
    # Register test services
    monitor.register_service("backend", lambda: True, grace_period_seconds=1)
    monitor.register_service("frontend", lambda: True, grace_period_seconds=2)  
    monitor.register_service("auth", lambda: True, grace_period_seconds=1)
    
    return monitor


@pytest.fixture
def test_fastapi_app():
    """Create test FastAPI application."""
    app = FastAPI(title="Cross-Service Test App")
    
    @app.get("/")
    async def root():
        return {"message": "Cross-service test app", "status": "ok"}
    
    @app.get("/api/test")
    async def api_test():
        return {"endpoint": "api_test", "service": "backend"}
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": "2025-08-20T10:00:00Z"}
    
    @app.get("/health/ready")
    async def readiness_check():
        return {"status": "ready", "services": ["database", "cache", "auth"]}
    
    @app.options("/api/test")
    async def api_test_options():
        return {"method": "OPTIONS", "allowed": True}
    
    return app


@pytest.fixture  
def test_app_with_cors(test_fastapi_app, test_service_discovery):
    """Create test app with enhanced CORS middleware."""
    # Add enhanced CORS middleware
    cors_middleware = CustomCORSMiddleware(
        test_fastapi_app,
        service_discovery=test_service_discovery,
        enable_metrics=True
    )
    
    test_fastapi_app.add_middleware(
        type(cors_middleware),
        service_discovery=test_service_discovery,
        enable_metrics=True
    )
    
    return test_fastapi_app


@pytest.fixture
def test_client(test_app_with_cors):
    """Create test client for the FastAPI app."""
    return TestClient(test_app_with_cors)


@pytest.fixture
def mock_environment_variables(cross_service_config):
    """Mock environment variables for cross-service testing."""
    test_env = {
        'ENVIRONMENT': 'development',
        'CORS_ORIGINS': '*',
        'BACKEND_PORT': str(cross_service_config.BACKEND_PORT),
        'FRONTEND_PORT': str(cross_service_config.FRONTEND_PORT),
        'AUTH_PORT': str(cross_service_config.AUTH_PORT),
        'CROSS_SERVICE_AUTH_TOKEN': cross_service_config.TEST_CROSS_SERVICE_TOKEN,
        'JWT_SECRET_KEY': cross_service_config.TEST_JWT_SECRET,
        'DATABASE_URL': 'sqlite:///test.db',
        'LOG_LEVEL': 'DEBUG'
    }
    
    with patch.dict(os.environ, test_env, clear=False):
        yield test_env


@pytest.fixture
def mock_httpx_responses():
    """Create mock HTTP responses for different services."""
    
    class MockResponses:
        def __init__(self):
            self.backend_health = Mock()
            self.backend_health.status_code = 200
            self.backend_health.json.return_value = {"status": "healthy", "service": "backend"}
            
            self.frontend_health = Mock()
            self.frontend_health.status_code = 200
            self.frontend_health.json.return_value = {"status": "healthy", "service": "frontend"}
            
            self.auth_health = Mock()
            self.auth_health.status_code = 200
            self.auth_health.json.return_value = {"status": "healthy", "service": "auth"}
            
            self.auth_config = Mock()
            self.auth_config.status_code = 200
            self.auth_config.json.return_value = {
                "client_id": "test-client-id",
                "auth_url": "http://localhost:8081/auth/login",
                "token_url": "http://localhost:8081/auth/token"
            }
            
            self.token_validation = Mock()
            self.token_validation.status_code = 200
            self.token_validation.json.return_value = {
                "valid": True,
                "user_id": "test-user-123",
                "email": "test@example.com", 
                "permissions": ["read", "write"]
            }
    
    return MockResponses()


@pytest.fixture
async def async_mock_http_client(mock_httpx_responses):
    """Create async mock HTTP client with predefined responses."""
    
    class AsyncMockHttpClient:
        def __init__(self, responses):
            self.responses = responses
            self._closed = False
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self._closed = True
        
        async def get(self, url, **kwargs):
            if '/health' in url:
                if 'localhost:8000' in url:
                    return self.responses.backend_health
                elif 'localhost:3000' in url:
                    return self.responses.frontend_health  
                elif 'localhost:8081' in url:
                    return self.responses.auth_health
            elif '/auth/config' in url:
                return self.responses.auth_config
            
            # Default response
            default_response = Mock()
            default_response.status_code = 404
            default_response.json.return_value = {"error": "Not found"}
            return default_response
        
        async def post(self, url, **kwargs):
            if '/auth/validate' in url or '/validate' in url:
                return self.responses.token_validation
            
            # Default response
            default_response = Mock()
            default_response.status_code = 400
            default_response.json.return_value = {"error": "Bad request"}
            return default_response
        
        def close(self):
            self._closed = True
    
    return AsyncMockHttpClient(mock_httpx_responses)


class CrossServiceTestHelpers:
    """Helper utilities for cross-service testing."""
    
    @staticmethod
    def create_test_request_with_origin(origin: str, method: str = "GET") -> Mock:
        """Create mock request with specified origin."""
        request = Mock()
        request.method = method
        request.headers = {"origin": origin}
        request.url = Mock()
        request.url.path = "/api/test"
        return request
    
    @staticmethod
    def create_cross_service_headers(service_id: str = "netra-test", auth_token: str = None) -> Dict[str, str]:
        """Create headers for cross-service requests."""
        headers = {
            "X-Service-ID": service_id,
            "Content-Type": "application/json",
            "User-Agent": "Netra-Cross-Service-Client/1.0"
        }
        
        if auth_token:
            headers["X-Cross-Service-Auth"] = auth_token
            
        return headers
    
    @staticmethod
    def assert_cors_headers_present(response, expected_origin: str = None):
        """Assert that required CORS headers are present."""
        headers = response.headers
        
        assert "Access-Control-Allow-Origin" in headers
        if expected_origin:
            assert headers["Access-Control-Allow-Origin"] == expected_origin
        
        assert "Access-Control-Allow-Credentials" in headers
        assert headers["Access-Control-Allow-Credentials"] == "true"
        
        assert "Access-Control-Allow-Methods" in headers
        assert "GET" in headers["Access-Control-Allow-Methods"]
        assert "POST" in headers["Access-Control-Allow-Methods"]
        assert "OPTIONS" in headers["Access-Control-Allow-Methods"]
    
    @staticmethod
    def assert_cross_service_headers_present(response):
        """Assert that cross-service specific headers are present."""
        headers = response.headers
        
        # Check for cross-service specific headers in Allow-Headers
        allow_headers = headers.get("Access-Control-Allow-Headers", "")
        assert "X-Service-ID" in allow_headers
        assert "X-Cross-Service-Auth" in allow_headers
        
        # Check for service identification headers
        if "X-Service-ID" in headers:
            assert headers["X-Service-ID"] == "netra-backend"


@pytest.fixture
def test_helpers():
    """Provide test helper utilities."""
    return CrossServiceTestHelpers()


# Performance testing fixtures
@pytest.fixture
def performance_test_config():
    """Configuration for performance testing."""
    return {
        'max_requests_per_second': 100,
        'max_response_time_ms': 50,
        'cors_cache_hit_rate_min': 0.8,
        'service_discovery_lookup_time_max_ms': 10
    }


# Integration test markers
pytest_integration = pytest.mark.integration
pytest_cross_service = pytest.mark.cross_service
pytest_cors = pytest.mark.cors
pytest_service_discovery = pytest.mark.service_discovery
pytest_health_monitoring = pytest.mark.health_monitoring
pytest_performance = pytest.mark.performance


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "cross_service: mark test as cross-service test")  
    config.addinivalue_line("markers", "cors: mark test as CORS-related test")
    config.addinivalue_line("markers", "service_discovery: mark test as service discovery test")
    config.addinivalue_line("markers", "health_monitoring: mark test as health monitoring test")
    config.addinivalue_line("markers", "performance: mark test as performance test")


if __name__ == "__main__":
    # Run configuration tests
    pytest.main([__file__, "-v"])