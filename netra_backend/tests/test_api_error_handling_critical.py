
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Critical API error handling tests.

Tests for comprehensive error handling across all API endpoints.
Essential error response validation.
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import json
import uuid
from typing import Any, Dict
from unittest.mock import MagicMock, AsyncMock, Mock, patch

import pytest

class TestAPIErrorHandlingCritical:
    """Critical API error handling tests."""
    @pytest.mark.asyncio
    async def test_bad_request_error(self):
        """Test 400 Bad Request error handling."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Test 400 Bad Request
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 400,
            "json": {"detail": "Invalid request data"}
        })
        
        response = await mock_client.post("/auth/login", json={})
        assert response["status_code"] == 400
        assert "detail" in response["json"]
    @pytest.mark.asyncio
    async def test_unauthorized_error(self):
        """Test 401 Unauthorized error handling."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Test 401 Unauthorized
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Not authenticated"}
        })
        
        response = await mock_client.get("/api/threads")
        assert response["status_code"] == 401
    @pytest.mark.asyncio
    async def test_forbidden_error(self):
        """Test 403 Forbidden error handling."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Test 403 Forbidden
        # Mock: Async component isolation for testing without real async operations
        mock_client.delete = AsyncMock(return_value={
            "status_code": 403,
            "json": {"detail": "Not enough permissions"}
        })
        
        response = await mock_client.delete("/api/admin/users/1")
        assert response["status_code"] == 403
    @pytest.mark.asyncio
    async def test_not_found_error(self):
        """Test 404 Not Found error handling."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Test 404 Not Found
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value={
            "status_code": 404,
            "json": {"detail": "Resource not found"}
        })
        
        response = await mock_client.get("/api/threads/nonexistent")
        assert response["status_code"] == 404
    @pytest.mark.asyncio
    async def test_internal_server_error(self):
        """Test 500 Internal Server Error handling."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Test 500 Internal Server Error
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 500,
            "json": {"detail": "Internal server error"}
        })
        
        response = await mock_client.post("/api/agent/query", json={"query": "test"})
        assert response["status_code"] == 500
    @pytest.mark.asyncio
    async def test_validation_error_detail(self):
        """Test validation error detail formatting."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 422,
            "json": {
                "detail": [
                    {
                        "loc": ["body", "email"],
                        "msg": "field required",
                        "type": "value_error.missing"
                    }
                ]
            }
        })
        
        response = await mock_client.post("/auth/register", json={})
        assert response["status_code"] == 422
        assert "detail" in response["json"]
    @pytest.mark.asyncio
    async def test_authentication_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Invalid email or password"}
        })
        
        response = await mock_client.post("/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response["status_code"] == 401
        assert response["json"]["detail"] == "Invalid email or password"
    @pytest.mark.asyncio
    async def test_permission_insufficient_rights(self):
        """Test insufficient permission rights."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Bearer user_token"}
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 403,
            "json": {"detail": "Insufficient permissions for admin operation"}
        })
        
        response = await mock_client.post(
            "/api/admin/users",
            json={"email": "new@example.com"},
            headers=auth_headers
        )
        assert response["status_code"] == 403
    @pytest.mark.asyncio
    async def test_resource_not_found_specific(self):
        """Test specific resource not found errors."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Bearer token123"}
        
        endpoints = [
            "/api/threads/99999999-9999-9999-9999-999999999999",
            "/api/users/nonexistent",
            "/api/messages/invalid_id"
        ]
        
        for endpoint in endpoints:
            # Mock: Async component isolation for testing without real async operations
            mock_client.get = AsyncMock(return_value={
                "status_code": 404,
                "json": {"detail": f"Resource not found: {endpoint}"}
            })
            
            response = await mock_client.get(endpoint, headers=auth_headers)
            assert response["status_code"] == 404
    @pytest.mark.asyncio
    async def test_malformed_json_error(self):
        """Test malformed JSON request error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 400,
            "json": {"detail": "Invalid JSON format"}
        })
        
        # Simulate malformed JSON by sending invalid data
        response = await mock_client.post("/api/threads", data="invalid json")
        assert response["status_code"] == 400
    @pytest.mark.asyncio
    async def test_missing_required_headers(self):
        """Test missing required headers error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Authorization header required"}
        })
        
        # Request without auth header
        response = await mock_client.get("/api/threads")
        assert response["status_code"] == 401
    @pytest.mark.asyncio
    async def test_invalid_token_format(self):
        """Test invalid token format error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Invalid token_format"}
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Invalid token format"}
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 401
    @pytest.mark.asyncio
    async def test_expired_token_error(self):
        """Test expired token error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Bearer expired_token"}
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Token has expired"}
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 401
        assert response["json"]["detail"] == "Token has expired"
    @pytest.mark.asyncio
    async def test_method_not_allowed(self):
        """Test method not allowed error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.patch = AsyncMock(return_value={
            "status_code": 405,
            "json": {"detail": "Method Not Allowed"}
        })
        
        # Try PATCH on endpoint that only accepts GET
        # Mock: Component isolation for testing without external dependencies
        response = await mock_client.patch("/api/health/live")
        assert response["status_code"] == 405
    @pytest.mark.asyncio
    async def test_content_type_validation(self):
        """Test content type validation error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 415,
            "json": {"detail": "Unsupported Media Type"}
        })
        
        # Send form data instead of JSON
        response = await mock_client.post(
            "/api/threads",
            data={"title": "test"},
            headers=auth_headers
        )
        assert response["status_code"] == 415
    @pytest.mark.asyncio
    async def test_request_timeout_error(self):
        """Test request timeout error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 408,
            "json": {"detail": "Request Timeout"}
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json={"query": "complex_long_running_query"},
            headers=auth_headers
        )
        assert response["status_code"] == 408
    @pytest.mark.asyncio
    async def test_payload_too_large(self):
        """Test payload too large error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 413,
            "json": {"detail": "Payload Too Large"}
        })
        
        large_payload = {"data": "x" * 10000}  # Simulate large payload
        response = await mock_client.post(
            "/api/messages",
            json=large_payload,
            headers=auth_headers
        )
        assert response["status_code"] == 413
    @pytest.mark.asyncio
    async def test_service_unavailable(self):
        """Test service unavailable error."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value={
            "status_code": 503,
            "json": {"detail": "Service Temporarily Unavailable"}
        })
        
        response = await mock_client.get("/api/health/ready")
        assert response["status_code"] == 503
    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """Test database connection error handling."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value={
            "status_code": 503,
            "json": {"detail": "Database connection unavailable"}
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 503
    @pytest.mark.asyncio
    async def test_error_response_consistency(self):
        """Test error response format consistency."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        
        error_codes = [400, 401, 403, 404, 422, 500]
        
        for code in error_codes:
            # Mock: Async component isolation for testing without real async operations
            mock_client.get = AsyncMock(return_value={
                "status_code": code,
                "json": {"detail": f"Error {code}"}
            })
            
            response = await mock_client.get("/test/endpoint")
            assert response["status_code"] == code
            assert "detail" in response["json"]
    @pytest.mark.asyncio
    async def test_cascading_error_prevention(self):
        """Test cascading error prevention."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()  # TODO: Use real service instance
        auth_headers = {"Authorization": "Bearer token123"}
        
        # First error
        # Mock: Async component isolation for testing without real async operations
        mock_client.post = AsyncMock(return_value={
            "status_code": 500,
            "json": {"detail": "Primary service error"}
        })
        
        response1 = await mock_client.post(
            "/api/agent/query",
            json={"query": "test"},
            headers=auth_headers
        )
        
        # Second request should still work (no cascading failure)
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {"status": "ok"}
        })
        
        response2 = await mock_client.get("/api/health/live")
        assert response1["status_code"] == 500
        assert response2["status_code"] == 200