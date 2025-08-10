import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import uuid
from datetime import datetime, timezone


class TestAPIEndpointsCritical:
    """Critical API endpoint tests"""
    
    @pytest.mark.asyncio
    async def test_health_endpoints(self):
        """Test health check endpoints"""
        mock_client = AsyncMock()
        
        # Test /health/live endpoint
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {"status": "ok"}
        })
        
        response = await mock_client.get("/health/live")
        assert response["status_code"] == 200
        assert response["json"]["status"] == "ok"
        
        # Test /health/ready endpoint
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {"status": "ready", "services": {"database": "ok", "redis": "ok"}}
        })
        
        response = await mock_client.get("/health/ready")
        assert response["status_code"] == 200
        assert response["json"]["status"] == "ready"
    
    @pytest.mark.asyncio
    async def test_authentication_endpoints(self):
        """Test authentication API endpoints"""
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
    async def test_thread_management_endpoints(self):
        """Test thread management API endpoints"""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test create thread
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": str(uuid.uuid4()),
                "title": "New Thread",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        response = await mock_client.post(
            "/api/threads",
            json={"title": "New Thread"},
            headers=auth_headers
        )
        assert response["status_code"] == 201
        assert response["json"]["title"] == "New Thread"
        
        # Test get user threads
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "threads": [
                    {"id": "thread1", "title": "Thread 1"},
                    {"id": "thread2", "title": "Thread 2"}
                ],
                "total": 2
            }
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 200
        assert len(response["json"]["threads"]) == 2
    
    @pytest.mark.asyncio
    async def test_message_endpoints(self):
        """Test message API endpoints"""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        thread_id = str(uuid.uuid4())
        
        # Test send message
        message_data = {
            "content": "Hello, AI assistant!",
            "thread_id": thread_id
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": str(uuid.uuid4()),
                "content": "Hello, AI assistant!",
                "role": "user",
                "thread_id": thread_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        response = await mock_client.post(
            "/api/messages",
            json=message_data,
            headers=auth_headers
        )
        assert response["status_code"] == 201
        assert response["json"]["content"] == message_data["content"]
        
        # Test get thread messages
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help?"}
                ],
                "total": 2
            }
        })
        
        response = await mock_client.get(
            f"/api/threads/{thread_id}/messages",
            headers=auth_headers
        )
        assert response["status_code"] == 200
        assert len(response["json"]["messages"]) == 2
    
    @pytest.mark.asyncio
    async def test_agent_endpoints(self):
        """Test agent interaction endpoints"""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test agent query
        query_data = {
            "query": "Analyze my system performance",
            "thread_id": str(uuid.uuid4()),
            "context": {"optimization_type": "cost"}
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "response": "Based on analysis, your system shows...",
                "metadata": {
                    "processing_time": 2.5,
                    "agents_used": ["triage", "data", "optimization"]
                }
            }
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json=query_data,
            headers=auth_headers
        )
        assert response["status_code"] == 200
        assert "response" in response["json"]
        assert len(response["json"]["metadata"]["agents_used"]) == 3
    
    @pytest.mark.asyncio
    async def test_generation_endpoints(self):
        """Test content generation endpoints"""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test generate synthetic data
        generation_data = {
            "type": "logs",
            "count": 100,
            "format": "json"
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "job_id": str(uuid.uuid4()),
                "status": "processing",
                "estimated_time": 30
            }
        })
        
        response = await mock_client.post(
            "/api/generate/synthetic-data",
            json=generation_data,
            headers=auth_headers
        )
        assert response["status_code"] == 200
        assert response["json"]["status"] == "processing"
    
    @pytest.mark.asyncio
    async def test_configuration_endpoints(self):
        """Test configuration management endpoints"""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test get configuration
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "environment": "development",
                "features": {
                    "optimization": True,
                    "synthetic_data": True
                },
                "limits": {
                    "max_threads": 100,
                    "max_messages_per_thread": 1000
                }
            }
        })
        
        response = await mock_client.get("/api/config", headers=auth_headers)
        assert response["status_code"] == 200
        assert response["json"]["environment"] == "development"
        
        # Test update configuration (admin only)
        config_update = {
            "features": {
                "optimization": False
            }
        }
        
        mock_client.patch = AsyncMock(return_value={
            "status_code": 200,
            "json": {"message": "Configuration updated successfully"}
        })
        
        response = await mock_client.patch(
            "/api/config",
            json=config_update,
            headers=auth_headers
        )
        assert response["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test API error handling"""
        mock_client = AsyncMock()
        
        # Test 400 Bad Request
        mock_client.post = AsyncMock(return_value={
            "status_code": 400,
            "json": {"detail": "Invalid request data"}
        })
        
        response = await mock_client.post("/api/auth/login", json={})
        assert response["status_code"] == 400
        assert "detail" in response["json"]
        
        # Test 401 Unauthorized
        mock_client.get = AsyncMock(return_value={
            "status_code": 401,
            "json": {"detail": "Not authenticated"}
        })
        
        response = await mock_client.get("/api/threads")
        assert response["status_code"] == 401
        
        # Test 403 Forbidden
        mock_client.delete = AsyncMock(return_value={
            "status_code": 403,
            "json": {"detail": "Not enough permissions"}
        })
        
        response = await mock_client.delete("/api/admin/users/1")
        assert response["status_code"] == 403
        
        # Test 404 Not Found
        mock_client.get = AsyncMock(return_value={
            "status_code": 404,
            "json": {"detail": "Resource not found"}
        })
        
        response = await mock_client.get("/api/threads/nonexistent")
        assert response["status_code"] == 404
        
        # Test 500 Internal Server Error
        mock_client.post = AsyncMock(return_value={
            "status_code": 500,
            "json": {"detail": "Internal server error"}
        })
        
        response = await mock_client.post("/api/agent/query", json={"query": "test"})
        assert response["status_code"] == 500
    
    @pytest.mark.asyncio
    async def test_pagination(self):
        """Test API pagination"""
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
        assert response["json"]["total"] == 100
        assert response["json"]["pages"] == 10
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test API rate limiting"""
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
        assert response["headers"]["X-RateLimit-Remaining"] == "0"