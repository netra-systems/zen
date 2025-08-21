"""Fixtures Tests - Split from test_cross_service_config.py"""

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
from netra_backend.app.core.middleware_setup import CustomCORSMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient

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

def test_health_monitor(test_service_discovery):
    """Create test health monitor with service discovery integration."""
    monitor = HealthMonitor(check_interval=0.1)  # Fast interval for testing
    monitor.set_service_discovery(test_service_discovery)
    
    # Register test services
    monitor.register_service("backend", lambda: True, grace_period_seconds=1)
    monitor.register_service("frontend", lambda: True, grace_period_seconds=2)  
    monitor.register_service("auth", lambda: True, grace_period_seconds=1)
    
    return monitor

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

def test_client(test_app_with_cors):
    """Create test client for the FastAPI app."""
    return TestClient(test_app_with_cors)

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

def test_helpers():
    """Provide test helper utilities."""
    return CrossServiceTestHelpers()

def performance_test_config():
    """Configuration for performance testing."""
    return {
        'max_requests_per_second': 100,
        'max_response_time_ms': 50,
        'cors_cache_hit_rate_min': 0.8,
        'service_discovery_lookup_time_max_ms': 10
    }
