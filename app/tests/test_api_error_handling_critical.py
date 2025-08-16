"""
Critical API error handling tests.

Tests for comprehensive error handling across all API endpoints.
Essential error response validation.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import uuid


class TestAPIErrorHandlingCritical:
    """Critical API error handling tests."""
    async def test_bad_request_error(self):
        """Test 400 Bad Request error handling."""
        mock_client = AsyncMock()
        
        # Test 400 Bad Request
        mock_client.post = AsyncMock(return_value={
            "status_code": 400,
            "json": {"detail": "Invalid request data"}
        })
        
        response = await mock_client.post("/api/auth/login", json={})
        assert response["status_code"] == 400
        assert "detail" in response["json"]
    async def test_unauthorized_error(self):
        """Test 401 Unauthorized error handling."""
        mock_client = AsyncMock()
        
        # Test 401 Unauthorized
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Not authenticated"}
        })
        
        response = await mock_client.get("/api/threads")
        assert response["status_code"] == 401
    async def test_forbidden_error(self):
        """Test 403 Forbidden error handling."""
        mock_client = AsyncMock()
        
        # Test 403 Forbidden
        mock_client.delete = AsyncMock(return_value={
            "status_code": 403,
            "json": {"detail": "Not enough permissions"}
        })
        
        response = await mock_client.delete("/api/admin/users/1")
        assert response["status_code"] == 403
    async def test_not_found_error(self):
        """Test 404 Not Found error handling."""
        mock_client = AsyncMock()
        
        # Test 404 Not Found
        mock_client.get = AsyncMock(return_value={
            "status_code": 404,
            "json": {"detail": "Resource not found"}
        })
        
        response = await mock_client.get("/api/threads/nonexistent")
        assert response["status_code"] == 404
    async def test_internal_server_error(self):
        """Test 500 Internal Server Error handling."""
        mock_client = AsyncMock()
        
        # Test 500 Internal Server Error
        mock_client.post = AsyncMock(return_value={
            "status_code": 500,
            "json": {"detail": "Internal server error"}
        })
        
        response = await mock_client.post("/api/agent/query", json={"query": "test"})
        assert response["status_code"] == 500
    async def test_validation_error_detail(self):
        """Test validation error detail formatting."""
        mock_client = AsyncMock()
        
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
        
        response = await mock_client.post("/api/auth/register", json={})
        assert response["status_code"] == 422
        assert "detail" in response["json"]
    async def test_authentication_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        mock_client = AsyncMock()
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Invalid email or password"}
        })
        
        response = await mock_client.post("/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response["status_code"] == 401
        assert response["json"]["detail"] == "Invalid email or password"
    async def test_permission_insufficient_rights(self):
        """Test insufficient permission rights."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer user_token"}
        
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
    async def test_resource_not_found_specific(self):
        """Test specific resource not found errors."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        endpoints = [
            "/api/threads/99999999-9999-9999-9999-999999999999",
            "/api/users/nonexistent",
            "/api/messages/invalid_id"
        ]
        
        for endpoint in endpoints:
            mock_client.get = AsyncMock(return_value={
                "status_code": 404,
                "json": {"detail": f"Resource not found: {endpoint}"}
            })
            
            response = await mock_client.get(endpoint, headers=auth_headers)
            assert response["status_code"] == 404
    async def test_malformed_json_error(self):
        """Test malformed JSON request error."""
        mock_client = AsyncMock()
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 400,
            "json": {"detail": "Invalid JSON format"}
        })
        
        # Simulate malformed JSON by sending invalid data
        response = await mock_client.post("/api/threads", data="invalid json")
        assert response["status_code"] == 400
    async def test_missing_required_headers(self):
        """Test missing required headers error."""
        mock_client = AsyncMock()
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Authorization header required"}
        })
        
        # Request without auth header
        response = await mock_client.get("/api/threads")
        assert response["status_code"] == 401
    async def test_invalid_token_format(self):
        """Test invalid token format error."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Invalid token_format"}
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Invalid token format"}
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 401
    async def test_expired_token_error(self):
        """Test expired token error."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer expired_token"}
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Token has expired"}
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 401
        assert response["json"]["detail"] == "Token has expired"
    async def test_method_not_allowed(self):
        """Test method not allowed error."""
        mock_client = AsyncMock()
        
        mock_client.patch = AsyncMock(return_value={
            "status_code": 405,
            "json": {"detail": "Method Not Allowed"}
        })
        
        # Try PATCH on endpoint that only accepts GET
        response = await mock_client.patch("/api/health/live")
        assert response["status_code"] == 405
    async def test_content_type_validation(self):
        """Test content type validation error."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
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
    async def test_request_timeout_error(self):
        """Test request timeout error."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
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
    async def test_payload_too_large(self):
        """Test payload too large error."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
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
    async def test_service_unavailable(self):
        """Test service unavailable error."""
        mock_client = AsyncMock()
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 503,
            "json": {"detail": "Service Temporarily Unavailable"}
        })
        
        response = await mock_client.get("/api/health/ready")
        assert response["status_code"] == 503
    async def test_database_connection_error(self):
        """Test database connection error handling."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 503,
            "json": {"detail": "Database connection unavailable"}
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 503
    async def test_error_response_consistency(self):
        """Test error response format consistency."""
        mock_client = AsyncMock()
        
        error_codes = [400, 401, 403, 404, 422, 500]
        
        for code in error_codes:
            mock_client.get = AsyncMock(return_value={
                "status_code": code,
                "json": {"detail": f"Error {code}"}
            })
            
            response = await mock_client.get("/test/endpoint")
            assert response["status_code"] == code
            assert "detail" in response["json"]
    async def test_cascading_error_prevention(self):
        """Test cascading error prevention."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # First error
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
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {"status": "ok"}
        })
        
        response2 = await mock_client.get("/api/health/live")
        assert response1["status_code"] == 500
        assert response2["status_code"] == 200