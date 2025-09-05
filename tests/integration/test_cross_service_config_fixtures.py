from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Fixtures Tests - Split from test_cross_service_config.py"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.service_discovery import ServiceDiscovery
from fastapi.middleware.cors import CORSMiddleware
from shared.cors_config_builder import get_fastapi_cors_config
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


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
    """Create test app with unified CORS configuration."""
    # Add CORS middleware using unified configuration
    cors_config = get_fastapi_cors_config("development")  # Use development config for testing
    test_fastapi_app.add_middleware(CORSMiddleware, **cors_config)
    
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
        'DATABASE_URL': 'DATABASE_URL_PLACEHOLDER',
        'LOG_LEVEL': 'DEBUG'
    }
    
    with patch.dict(os.environ, test_env, clear=False):
        yield test_env

def mock_httpx_responses():
    """Create mock HTTP responses for different services."""
    
    class MockResponses:
        def __init__(self):
            # Mock: Generic component isolation for controlled unit testing
            self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
            self.backend_health.status_code = 200
            self.backend_health.json.return_value = {"status": "healthy", "service": "backend"}
            
            # Mock: Generic component isolation for controlled unit testing
            self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
            self.frontend_health.status_code = 200
            self.frontend_health.json.return_value = {"status": "healthy", "service": "frontend"}
            
            # Mock: Generic component isolation for controlled unit testing
            self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
            self.auth_health.status_code = 200
            self.auth_health.json.return_value = {"status": "healthy", "service": "auth"}
            
            # Mock: Generic component isolation for controlled unit testing
            self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
            self.auth_config.status_code = 200
            self.auth_config.json.return_value = {
                "client_id": "test-client-id",
                "auth_url": "http://localhost:8081/auth/login",
                "token_url": "http://localhost:8081/auth/token"
            }
            
            # Mock: Generic component isolation for controlled unit testing
            self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
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


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()
