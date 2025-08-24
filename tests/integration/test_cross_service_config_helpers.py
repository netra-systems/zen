"""Utilities Tests - Split from test_cross_service_config.py"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.service_discovery import ServiceDiscovery
from netra_backend.app.core.middleware_setup import CustomCORSMiddleware


def cross_service_config():
    """Provide cross-service test configuration."""
    return CrossServiceTestConfig()

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "cross_service: mark test as cross-service test")  
    config.addinivalue_line("markers", "cors: mark test as CORS-related test")
    config.addinivalue_line("markers", "service_discovery: mark test as service discovery test")
    config.addinivalue_line("markers", "health_monitoring: mark test as health monitoring test")
    config.addinivalue_line("markers", "performance: mark test as performance test")

    def create_test_request_with_origin(origin: str, method: str = "GET") -> Mock:
        """Create mock request with specified origin."""
        # Mock: Generic component isolation for controlled unit testing
        request = Mock()
        request.method = method
        request.headers = {"origin": origin}
        # Mock: Generic component isolation for controlled unit testing
        request.url = Mock()
        request.url.path = "/api/test"
        return request

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

        def __init__(self):
            # Mock: Generic component isolation for controlled unit testing
            self.backend_health = Mock()
            self.backend_health.status_code = 200
            self.backend_health.json.return_value = {"status": "healthy", "service": "backend"}
            
            # Mock: Generic component isolation for controlled unit testing
            self.frontend_health = Mock()
            self.frontend_health.status_code = 200
            self.frontend_health.json.return_value = {"status": "healthy", "service": "frontend"}
            
            # Mock: Generic component isolation for controlled unit testing
            self.auth_health = Mock()
            self.auth_health.status_code = 200
            self.auth_health.json.return_value = {"status": "healthy", "service": "auth"}
            
            # Mock: Generic component isolation for controlled unit testing
            self.auth_config = Mock()
            self.auth_config.status_code = 200
            self.auth_config.json.return_value = {
                "client_id": "test-client-id",
                "auth_url": "http://localhost:8081/auth/login",
                "token_url": "http://localhost:8081/auth/token"
            }
            
            # Mock: Generic component isolation for controlled unit testing
            self.token_validation = Mock()
            self.token_validation.status_code = 200
            self.token_validation.json.return_value = {
                "valid": True,
                "user_id": "test-user-123",
                "email": "test@example.com", 
                "permissions": ["read", "write"]
            }

        def __init__(self, responses):
            self.responses = responses
            self._closed = False

        def close(self):
            self._closed = True
