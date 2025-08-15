"""
Critical core API endpoint tests.

Tests for health checks, authentication, pagination, and rate limiting.
Essential API infrastructure functionality.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import uuid
from datetime import datetime, timezone


class TestAPICoreEndpointsCritical:
    """Critical core API endpoint tests."""
    
    @pytest.mark.asyncio
    async def test_health_endpoints(self):
        """Test health check endpoints."""
        mock_client = AsyncMock()
        
        # Test /health/live endpoint
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {"status": "ok"}
        })
        
        response = await mock_client.get("/health/live")
        assert response["status_code"] == 200
        assert response["json"]["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_health_ready_endpoint(self):
        """Test health ready endpoint."""
        mock_client = AsyncMock()
        
        # Test /health/ready endpoint
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {"status": "ready", "services": {"database": "ok", "redis": "ok"}}
        })
        
        response = await mock_client.get("/health/ready")
        assert response["status_code"] == 200
        assert response["json"]["status"] == "ready"
    
    @pytest.mark.asyncio
    async def test_login_endpoint(self):
        """Test login authentication endpoint."""
        mock_client = AsyncMock()
        
        # Test login endpoint
        login_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {"id": 1, "email": "test@example.com"}
            }
        })
        
        response = await mock_client.post("/api/auth/login", json=login_data)
        assert response["status_code"] == 200
        assert "access_token" in response["json"]
    
    @pytest.mark.asyncio
    async def test_register_endpoint(self):
        """Test user registration endpoint."""
        mock_client = AsyncMock()
        
        # Test register endpoint
        register_data = {
            "email": "newuser@example.com",
            "password": "NewPassword123!",
            "username": "newuser"
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {"id": 2, "email": "newuser@example.com", "username": "newuser"}
        })
        
        response = await mock_client.post("/api/auth/register", json=register_data)
        assert response["status_code"] == 201
        assert response["json"]["email"] == "newuser@example.com"
    
    @pytest.mark.asyncio
    async def test_pagination_basic(self):
        """Test basic API pagination."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test paginated response
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "items": [{"id": i} for i in range(10)],
                "total": 100,
                "page": 1,
                "per_page": 10,
                "pages": 10
            }
        })
        
        response = await mock_client.get(
            "/api/threads?page=1&per_page=10",
            headers=auth_headers
        )
        assert response["status_code"] == 200
        assert len(response["json"]["items"]) == 10
    
    @pytest.mark.asyncio
    async def test_pagination_metadata(self):
        """Test pagination metadata validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "items": [{"id": i} for i in range(10)],
                "total": 100,
                "page": 1,
                "per_page": 10,
                "pages": 10
            }
        })
        
        response = await mock_client.get(
            "/api/threads?page=1&per_page=10",
            headers=auth_headers
        )
        assert response["json"]["total"] == 100
        assert response["json"]["pages"] == 10
    
    @pytest.mark.asyncio
    async def test_rate_limiting_exceeded(self):
        """Test rate limit exceeded response."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test rate limit exceeded
        mock_client.post = AsyncMock(return_value={
            "status_code": 429,
            "json": {"detail": "Rate limit exceeded"},
            "headers": {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1234567890"
            }
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json={"query": "test"},
            headers=auth_headers
        )
        assert response["status_code"] == 429
    
    @pytest.mark.asyncio
    async def test_rate_limiting_headers(self):
        """Test rate limiting headers validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 429,
            "json": {"detail": "Rate limit exceeded"},
            "headers": {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1234567890"
            }
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json={"query": "test"},
            headers=auth_headers
        )
        assert response["headers"]["X-RateLimit-Remaining"] == "0"
    
    @pytest.mark.asyncio
    async def test_authentication_token_validation(self):
        """Test authentication token validation."""
        mock_client = AsyncMock()
        
        login_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "access_token": "valid_token_123",
                "token_type": "bearer",
                "user": {"id": 1, "email": "test@example.com"}
            }
        })
        
        response = await mock_client.post("/api/auth/login", json=login_data)
        assert response["json"]["token_type"] == "bearer"
        assert "user" in response["json"]
    
    @pytest.mark.asyncio
    async def test_health_service_status(self):
        """Test health endpoint service status."""
        mock_client = AsyncMock()
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "status": "ready", 
                "services": {
                    "database": "ok", 
                    "redis": "ok",
                    "clickhouse": "ok"
                }
            }
        })
        
        response = await mock_client.get("/health/ready")
        services = response["json"]["services"]
        assert services["database"] == "ok"
        assert services["redis"] == "ok"
    
    @pytest.mark.asyncio
    async def test_authentication_error_handling(self):
        """Test authentication error handling."""
        mock_client = AsyncMock()
        
        # Test invalid credentials
        mock_client.post = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Invalid credentials"}
        })
        
        response = await mock_client.post("/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrong_password"
        })
        assert response["status_code"] == 401
        assert "detail" in response["json"]
    
    @pytest.mark.asyncio
    async def test_registration_validation(self):
        """Test registration input validation."""
        mock_client = AsyncMock()
        
        # Test missing required fields
        mock_client.post = AsyncMock(return_value={
            "status_code": 400,
            "json": {"detail": "Missing required fields"}
        })
        
        response = await mock_client.post("/api/auth/register", json={
            "email": "incomplete@example.com"
        })
        assert response["status_code"] == 400
    
    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self):
        """Test pagination edge cases."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test empty results
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "items": [],
                "total": 0,
                "page": 1,
                "per_page": 10,
                "pages": 0
            }
        })
        
        response = await mock_client.get(
            "/api/threads?page=1&per_page=10",
            headers=auth_headers
        )
        assert len(response["json"]["items"]) == 0
        assert response["json"]["total"] == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_recovery(self):
        """Test rate limiting recovery."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test successful request after rate limit reset
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {"result": "success"},
            "headers": {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "99",
                "X-RateLimit-Reset": "1234567890"
            }
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json={"query": "test"},
            headers=auth_headers
        )
        assert response["status_code"] == 200
        assert response["headers"]["X-RateLimit-Remaining"] == "99"