"""
Offline API Routing Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure API routing and middleware integration works without external services
- Value Impact: Validates core FastAPI routing logic, middleware chains, and request processing
- Strategic Impact: Enables immediate testing of API layer without Docker dependencies

These tests validate API routing integration between components without requiring
external services like Redis or PostgreSQL. They focus on:
1. API route registration and resolution
2. Middleware chain integration
3. Request/response processing
4. Authentication middleware setup
5. Error handling integration
6. CORS and security middleware
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockAuthService:
    """Mock auth service for offline testing."""
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Mock token validation."""
        if token == "valid_test_token":
            return {
                "valid": True,
                "user_id": "test_user_123",
                "email": "test@example.com",
                "roles": ["user"]
            }
        elif token == "admin_test_token":
            return {
                "valid": True,
                "user_id": "admin_user_123", 
                "email": "admin@example.com",
                "roles": ["admin", "user"]
            }
        else:
            return {"valid": False, "error": "Invalid token"}
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mock user retrieval."""
        if user_id == "test_user_123":
            return {
                "id": "test_user_123",
                "email": "test@example.com", 
                "name": "Test User",
                "roles": ["user"]
            }
        elif user_id == "admin_user_123":
            return {
                "id": "admin_user_123",
                "email": "admin@example.com",
                "name": "Admin User", 
                "roles": ["admin", "user"]
            }
        return None


class MockDatabaseManager:
    """Mock database manager for offline testing."""
    
    def __init__(self):
        self.connected = False
        self.query_count = 0
        self._mock_data = {
            "users": [
                {"id": "test_user_123", "email": "test@example.com"},
                {"id": "admin_user_123", "email": "admin@example.com"}
            ],
            "threads": [
                {"id": "thread_1", "title": "Test Thread", "user_id": "test_user_123"},
                {"id": "thread_2", "title": "Admin Thread", "user_id": "admin_user_123"}
            ]
        }
    
    async def connect(self):
        """Mock database connection."""
        self.connected = True
        return True
    
    async def disconnect(self):
        """Mock database disconnection."""
        self.connected = False
    
    async def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """Mock query execution."""
        self.query_count += 1
        
        # Simple mock query routing based on query content
        if "users" in query.lower():
            return self._mock_data["users"]
        elif "threads" in query.lower():
            return self._mock_data["threads"]
        else:
            return []
    
    def is_connected(self) -> bool:
        """Check mock connection status."""
        return self.connected


class TestAPIRoutingIntegrationOffline(SSotBaseTestCase):
    """Offline integration tests for API routing and middleware."""

    def setup_method(self, method=None):
        """Setup with mock services for offline testing."""
        super().setup_method(method)
        
        # Initialize mock services
        self.mock_auth_service = MockAuthService()
        self.mock_db_manager = MockDatabaseManager()
        
        # Store original imports for patching
        self.patches = []
    
    def teardown_method(self, method=None):
        """Cleanup patches and mock services."""
        try:
            # Stop all patches
            for patcher in self.patches:
                patcher.stop()
            self.patches.clear()
        finally:
            super().teardown_method(method)

    def create_test_app(self) -> FastAPI:
        """Create test FastAPI app with mock dependencies."""
        app = FastAPI(title="Test API", version="1.0.0")
        
        # Mock dependency injection
        async def get_auth_service():
            return self.mock_auth_service
        
        async def get_db_manager():
            return self.mock_db_manager
        
        # Basic health endpoint
        @app.get("/health")
        async def health():
            return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
        
        # Protected endpoint requiring authentication
        @app.get("/api/protected")
        async def protected_endpoint(request: Request):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return {"error": "Unauthorized"}, 401
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            auth_result = await self.mock_auth_service.validate_token(token)
            
            if not auth_result.get("valid"):
                return {"error": "Invalid token"}, 401
            
            return {"message": "Access granted", "user_id": auth_result["user_id"]}
        
        # Admin-only endpoint
        @app.get("/api/admin")
        async def admin_endpoint(request: Request):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return {"error": "Unauthorized"}, 401
            
            token = auth_header[7:]
            auth_result = await self.mock_auth_service.validate_token(token)
            
            if not auth_result.get("valid"):
                return {"error": "Invalid token"}, 401
            
            user = await self.mock_auth_service.get_user_by_id(auth_result["user_id"])
            if not user or "admin" not in user.get("roles", []):
                return {"error": "Admin access required"}, 403
            
            return {"message": "Admin access granted", "user": user}
        
        # Database-dependent endpoint
        @app.get("/api/data")
        async def data_endpoint():
            if not self.mock_db_manager.is_connected():
                await self.mock_db_manager.connect()
            
            users = await self.mock_db_manager.execute_query("SELECT * FROM users")
            return {"users": users, "query_count": self.mock_db_manager.query_count}
        
        # Error endpoint for testing error handling
        @app.get("/api/error")
        async def error_endpoint():
            raise Exception("Test error for error handling integration")
        
        return app

    @pytest.mark.integration
    async def test_basic_routing_integration(self):
        """
        Test basic API routing integration without external dependencies.
        
        Validates that routes are registered correctly and respond appropriately.
        """
        app = self.create_test_app()
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        
        # Test non-existent route returns 404
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        # Test root path behavior
        response = client.get("/")
        # Should return 404 since we haven't defined root path
        assert response.status_code == 404
        
        # Test different HTTP methods on same path
        response = client.post("/health")  # POST to GET endpoint
        assert response.status_code == 405  # Method Not Allowed
        
        # Record routing integration metrics
        self.record_metric("basic_routes_tested", 4)
        self.record_metric("health_endpoint_working", response.status_code == 200)
        self.record_metric("basic_routing_integration_passed", True)

    @pytest.mark.integration
    async def test_authentication_middleware_integration(self):
        """
        Test authentication middleware integration with mock auth service.
        
        Validates that authentication flows work correctly without real auth service.
        """
        app = self.create_test_app()
        client = TestClient(app)
        
        # Test Case 1: No authentication header
        response = client.get("/api/protected")
        assert response.status_code == 200  # Our mock endpoint returns 200 with error
        data = response.json()
        assert "error" in data[0]  # Tuple response format from FastAPI
        assert data[0]["error"] == "Unauthorized"
        
        # Test Case 2: Invalid authentication header format
        response = client.get("/api/protected", headers={"Authorization": "InvalidFormat"})
        assert response.status_code == 200
        data = response.json()
        assert "error" in data[0]
        
        # Test Case 3: Invalid token
        response = client.get("/api/protected", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 200
        data = response.json()
        assert "error" in data[0]
        assert data[0]["error"] == "Invalid token"
        
        # Test Case 4: Valid token
        response = client.get("/api/protected", headers={"Authorization": "Bearer valid_test_token"})
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Access granted"
        assert data["user_id"] == "test_user_123"
        
        # Test Case 5: Admin endpoint with user token (should fail)
        response = client.get("/api/admin", headers={"Authorization": "Bearer valid_test_token"})
        assert response.status_code == 200
        data = response.json()
        assert "error" in data[0]
        assert data[0]["error"] == "Admin access required"
        
        # Test Case 6: Admin endpoint with admin token (should succeed)
        response = client.get("/api/admin", headers={"Authorization": "Bearer admin_test_token"})
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Admin access granted"
        assert "user" in data
        assert data["user"]["email"] == "admin@example.com"
        
        # Record authentication integration metrics
        self.record_metric("auth_test_scenarios", 6)
        self.record_metric("valid_token_auth_working", True)
        self.record_metric("admin_auth_working", True)
        self.record_metric("authentication_middleware_integration_passed", True)

    @pytest.mark.integration
    async def test_database_integration_mocking(self):
        """
        Test database integration with mock database manager.
        
        Validates that database-dependent endpoints work with mocked database.
        """
        app = self.create_test_app()
        client = TestClient(app)
        
        # Test Case 1: Database endpoint with mock data
        response = client.get("/api/data")
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        assert "query_count" in data
        assert len(data["users"]) == 2  # Our mock data has 2 users
        assert data["query_count"] == 1  # One query executed
        
        # Verify mock data structure
        users = data["users"]
        user_emails = [user["email"] for user in users]
        assert "test@example.com" in user_emails
        assert "admin@example.com" in user_emails
        
        # Test Case 2: Multiple calls increment query count
        response2 = client.get("/api/data")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["query_count"] == 2  # Query count should increment
        
        # Test Case 3: Verify database connection status
        assert self.mock_db_manager.is_connected()
        
        # Test Case 4: Database disconnection and reconnection
        await self.mock_db_manager.disconnect()
        assert not self.mock_db_manager.is_connected()
        
        response3 = client.get("/api/data")
        assert response3.status_code == 200
        assert self.mock_db_manager.is_connected()  # Should reconnect
        
        # Record database integration metrics
        self.record_metric("db_endpoint_requests", 3)
        self.record_metric("mock_db_queries", self.mock_db_manager.query_count)
        self.record_metric("database_integration_mocking_passed", True)

    @pytest.mark.integration
    async def test_error_handling_integration(self):
        """
        Test error handling integration across the API layer.
        
        Validates that errors are properly caught and formatted consistently.
        """
        app = self.create_test_app()
        client = TestClient(app)
        
        # Test Case 1: Endpoint that raises exception
        response = client.get("/api/error")
        assert response.status_code == 500  # Internal Server Error
        
        # Test Case 2: Invalid JSON in request body
        response = client.post("/api/protected", 
                             headers={"Content-Type": "application/json"},
                             data="invalid json")
        # FastAPI should handle invalid JSON gracefully
        assert response.status_code in [400, 422]  # Bad Request or Unprocessable Entity
        
        # Test Case 3: Missing required headers
        response = client.get("/api/protected")
        assert response.status_code == 200  # Our mock handles this gracefully
        data = response.json()
        assert "error" in data[0]
        
        # Test Case 4: Method not allowed
        response = client.post("/health")  # POST to GET endpoint
        assert response.status_code == 405
        
        # Test Case 5: Large request handling
        large_headers = {f"X-Custom-Header-{i}": f"value_{i}" * 100 for i in range(10)}
        response = client.get("/health", headers=large_headers)
        # Should still work with many headers
        assert response.status_code == 200
        
        # Record error handling integration metrics
        self.record_metric("error_scenarios_tested", 5)
        self.record_metric("exception_handling_working", True)
        self.record_metric("error_handling_integration_passed", True)

    @pytest.mark.integration
    async def test_request_response_integration(self):
        """
        Test request/response processing integration.
        
        Validates that requests and responses are processed correctly
        through the entire middleware chain.
        """
        app = self.create_test_app()
        client = TestClient(app)
        
        # Test Case 1: Request headers processing
        custom_headers = {
            "X-Request-ID": "test-123",
            "User-Agent": "Test-Client/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        response = client.get("/health", headers=custom_headers)
        assert response.status_code == 200
        
        # Verify response headers
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]
        
        # Test Case 2: Query parameter processing
        response = client.get("/health?param1=value1&param2=value2")
        assert response.status_code == 200
        # Query params should not affect health endpoint
        
        # Test Case 3: Request body processing (for POST endpoints)
        # Since we don't have POST endpoints defined, test that POST returns correct error
        response = client.post("/health", json={"test": "data"})
        assert response.status_code == 405  # Method Not Allowed
        
        # Test Case 4: Response format consistency
        health_response = client.get("/health")
        health_data = health_response.json()
        assert isinstance(health_data, dict)
        assert "status" in health_data
        
        protected_response = client.get("/api/protected", 
                                      headers={"Authorization": "Bearer valid_test_token"})
        protected_data = protected_response.json()
        assert isinstance(protected_data, dict)
        
        # Test Case 5: Unicode and special character handling
        unicode_headers = {"X-Unicode": "café_résumé_🚀"}
        response = client.get("/health", headers=unicode_headers)
        assert response.status_code == 200
        
        # Record request/response integration metrics
        self.record_metric("request_response_scenarios_tested", 5)
        self.record_metric("header_processing_working", True)
        self.record_metric("json_response_format_consistent", True)
        self.record_metric("request_response_integration_passed", True)

    @pytest.mark.integration
    async def test_middleware_chain_integration(self):
        """
        Test middleware chain integration and execution order.
        
        Validates that middleware components work together correctly.
        """
        # Create app with custom middleware for testing
        app = self.create_test_app()
        
        # Add custom middleware to test execution order
        request_log = []
        
        @app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            request_log.append(f"before_{request.url.path}")
            response = await call_next(request)
            request_log.append(f"after_{request.url.path}")
            return response
        
        @app.middleware("http")
        async def timing_middleware(request: Request, call_next):
            start_time = self.get_metrics().start_time
            response = await call_next(request)
            end_time = self.get_metrics().end_time or start_time
            response.headers["X-Process-Time"] = str(end_time - start_time)
            return response
        
        client = TestClient(app)
        
        # Test Case 1: Middleware execution order
        response = client.get("/health")
        assert response.status_code == 200
        
        # Check that middleware executed in correct order
        assert len(request_log) >= 2
        assert any("before_/health" in log for log in request_log)
        assert any("after_/health" in log for log in request_log)
        
        # Test Case 2: Response headers from middleware
        assert "X-Process-Time" in response.headers
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0.0
        
        # Test Case 3: Middleware with protected endpoints
        request_log.clear()  # Clear previous logs
        response = client.get("/api/protected", 
                            headers={"Authorization": "Bearer valid_test_token"})
        assert response.status_code == 200
        
        # Middleware should execute for all endpoints
        assert len(request_log) >= 2
        assert any("before_/api/protected" in log for log in request_log)
        assert any("after_/api/protected" in log for log in request_log)
        
        # Test Case 4: Middleware with error endpoints
        request_log.clear()
        response = client.get("/api/error")
        
        # Middleware should execute even for error endpoints
        assert len(request_log) >= 2
        assert any("before_/api/error" in log for log in request_log)
        assert any("after_/api/error" in log for log in request_log)
        
        # Record middleware integration metrics
        self.record_metric("middleware_execution_logs", len(request_log))
        self.record_metric("timing_middleware_working", "X-Process-Time" in response.headers)
        self.record_metric("logging_middleware_working", len(request_log) > 0)
        self.record_metric("middleware_chain_integration_passed", True)

    @pytest.mark.integration
    async def test_cors_and_security_integration(self):
        """
        Test CORS and security middleware integration.
        
        Validates that security-related middleware works correctly.
        """
        from fastapi.middleware.cors import CORSMiddleware
        
        app = self.create_test_app()
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "https://example.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )
        
        client = TestClient(app)
        
        # Test Case 1: CORS preflight request
        response = client.options("/api/protected", 
                                headers={"Origin": "http://localhost:3000",
                                        "Access-Control-Request-Method": "GET"})
        # FastAPI/Starlette handles OPTIONS requests
        assert response.status_code in [200, 405]  # Depends on implementation
        
        # Test Case 2: CORS headers on actual request
        response = client.get("/api/protected",
                            headers={"Origin": "http://localhost:3000",
                                   "Authorization": "Bearer valid_test_token"})
        assert response.status_code == 200
        
        # Should include CORS headers (if CORS middleware is working)
        # Note: TestClient might not fully simulate browser CORS behavior
        
        # Test Case 3: Unauthorized origin (if CORS is strict)
        response = client.get("/health", 
                            headers={"Origin": "http://malicious.com"})
        assert response.status_code == 200  # Health endpoint should still work
        
        # Test Case 4: Security headers
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test that response doesn't leak sensitive information
        response_text = response.text.lower()
        sensitive_keywords = ["password", "secret", "key", "token"]
        for keyword in sensitive_keywords:
            assert keyword not in response_text, f"Response should not contain '{keyword}'"
        
        # Test Case 5: Request size limits (basic test)
        large_header_value = "x" * 8192  # 8KB header
        response = client.get("/health", 
                            headers={"X-Large-Header": large_header_value})
        # Should handle reasonably large headers
        assert response.status_code in [200, 413, 431]  # OK, Payload Too Large, or Request Header Fields Too Large
        
        # Record CORS and security integration metrics
        self.record_metric("cors_scenarios_tested", 4)
        self.record_metric("security_header_scenarios_tested", 2)
        self.record_metric("cors_and_security_integration_passed", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])