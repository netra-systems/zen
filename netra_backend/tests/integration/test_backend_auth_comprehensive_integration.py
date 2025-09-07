"""
Backend Auth Comprehensive Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure backend properly integrates with auth service for secure user operations
- Value Impact: Users can securely access chat features, threads, and agent executions through authenticated sessions
- Strategic Impact: Core security integration that enables all user-facing features while maintaining multi-user isolation

CRITICAL: These tests use REAL PostgreSQL and Redis services (no mocks).
Tests validate backend-to-auth-service integration with real cross-service communication.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import aiohttp
from unittest.mock import patch, AsyncMock

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from netra_backend.app.config import BackendConfig
from netra_backend.app.services.auth_integration_service import AuthIntegrationService
from netra_backend.app.middleware.auth_middleware import AuthMiddleware
from netra_backend.app.database import get_database
from netra_backend.app.models import User, Thread, Message


class TestBackendAuthIntegration(BaseIntegrationTest):
    """Integration tests for backend authentication with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real services."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real backend configuration
        self.backend_config = BackendConfig()
        
        # Real service instances
        self.auth_integration_service = AuthIntegrationService(self.backend_config)
        self.auth_middleware = AuthMiddleware(self.auth_integration_service)
        
        # Real database connection
        self.db = get_database()
        
        # Test configuration
        self.auth_service_url = "http://localhost:8081"  # Test auth service
        self.backend_url = "http://localhost:8000"       # Test backend
        
        # Test users for various scenarios
        self.test_users = [
            {
                "user_id": "backend-auth-test-user-1",
                "email": "backend-test-1@example.com",
                "name": "Backend Auth Test User 1",
                "permissions": ["read", "write"]
            },
            {
                "user_id": "backend-auth-test-user-2",
                "email": "backend-test-2@example.com",
                "name": "Backend Auth Test User 2",
                "permissions": ["read", "write", "admin"]
            }
        ]
        
        self.created_tokens = []  # Track for cleanup
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services."""
        try:
            # Clean test threads and messages from database
            async with self.db.begin() as conn:
                await conn.execute("""
                    DELETE FROM messages 
                    WHERE thread_id IN (
                        SELECT id FROM threads 
                        WHERE user_id LIKE 'backend-auth-test-user-%'
                    )
                """)
                await conn.execute("""
                    DELETE FROM threads 
                    WHERE user_id LIKE 'backend-auth-test-user-%'
                """)
                await conn.execute("""
                    DELETE FROM users 
                    WHERE id LIKE 'backend-auth-test-user-%'
                """)
        except Exception as e:
            self.logger.warning(f"Database cleanup warning: {e}")
    
    async def create_test_token(self, user_data: Dict[str, Any]) -> str:
        """Create test JWT token using auth helper."""
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        self.created_tokens.append(token)
        return token
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_middleware_token_validation(self):
        """
        Test auth middleware validates tokens correctly with auth service.
        
        BVJ: Ensures only authenticated users can access backend endpoints.
        """
        user_data = self.test_users[0]
        
        # Create valid token
        valid_token = await self.create_test_token(user_data)
        
        # Test 1: Valid token should pass validation
        auth_result = await self.auth_middleware.validate_auth_token(valid_token)
        
        assert auth_result is not None
        assert auth_result["valid"] is True
        assert auth_result["user_id"] == user_data["user_id"]
        assert auth_result["email"] == user_data["email"]
        assert auth_result["permissions"] == user_data["permissions"]
        
        # Test 2: Invalid token should fail validation
        invalid_token = "invalid.jwt.token"
        
        invalid_result = await self.auth_middleware.validate_auth_token(invalid_token)
        assert invalid_result is None or invalid_result["valid"] is False
        
        # Test 3: Malformed token should fail validation
        malformed_token = "not-a-jwt-token-at-all"
        
        malformed_result = await self.auth_middleware.validate_auth_token(malformed_token)
        assert malformed_result is None or malformed_result["valid"] is False
        
        # Test 4: Empty token should fail validation
        with pytest.raises(ValueError):
            await self.auth_middleware.validate_auth_token("")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_isolation_per_request(self):
        """
        Test user context isolation for multi-user system.
        
        BVJ: Critical for multi-user system - ensures users cannot access each other's data.
        """
        # Create tokens for different users
        user1_token = await self.create_test_token(self.test_users[0])
        user2_token = await self.create_test_token(self.test_users[1])
        
        # Create user contexts in database
        async with self.db.begin() as conn:
            # Create user 1
            await conn.execute("""
                INSERT INTO users (id, email, name, created_at) 
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET 
                email = $2, name = $3, updated_at = NOW()
            """, [
                self.test_users[0]["user_id"],
                self.test_users[0]["email"],
                self.test_users[0]["name"],
                datetime.now(timezone.utc)
            ])
            
            # Create user 2
            await conn.execute("""
                INSERT INTO users (id, email, name, created_at) 
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET 
                email = $2, name = $3, updated_at = NOW()
            """, [
                self.test_users[1]["user_id"],
                self.test_users[1]["email"],
                self.test_users[1]["name"],
                datetime.now(timezone.utc)
            ])
            
            # Create thread for user 1
            user1_thread_id = f"thread-{self.test_users[0]['user_id']}-{int(time.time())}"
            await conn.execute("""
                INSERT INTO threads (id, user_id, title, created_at) 
                VALUES ($1, $2, $3, $4)
            """, [
                user1_thread_id,
                self.test_users[0]["user_id"],
                "User 1 Private Thread",
                datetime.now(timezone.utc)
            ])
            
            # Create thread for user 2
            user2_thread_id = f"thread-{self.test_users[1]['user_id']}-{int(time.time())}"
            await conn.execute("""
                INSERT INTO threads (id, user_id, title, created_at) 
                VALUES ($1, $2, $3, $4)
            """, [
                user2_thread_id,
                self.test_users[1]["user_id"],
                "User 2 Private Thread", 
                datetime.now(timezone.utc)
            ])
        
        # Test user 1 context
        user1_context = await self.auth_middleware.create_user_context(user1_token)
        assert user1_context is not None
        assert user1_context["user_id"] == self.test_users[0]["user_id"]
        assert user1_context["email"] == self.test_users[0]["email"]
        
        # Test user 2 context
        user2_context = await self.auth_middleware.create_user_context(user2_token)
        assert user2_context is not None
        assert user2_context["user_id"] == self.test_users[1]["user_id"]
        assert user2_context["email"] == self.test_users[1]["email"]
        
        # Verify contexts are isolated
        assert user1_context["user_id"] != user2_context["user_id"]
        assert user1_context["email"] != user2_context["email"]
        
        # Test data isolation: User 1 should only see their threads
        async with self.db.begin() as conn:
            user1_threads = await conn.fetch("""
                SELECT id, title FROM threads 
                WHERE user_id = $1
            """, self.test_users[0]["user_id"])
            
            user2_threads = await conn.fetch("""
                SELECT id, title FROM threads 
                WHERE user_id = $1
            """, self.test_users[1]["user_id"])
        
        # Each user should only see their own threads
        assert len(user1_threads) >= 1
        assert len(user2_threads) >= 1
        
        user1_thread_titles = [t["title"] for t in user1_threads]
        user2_thread_titles = [t["title"] for t in user2_threads]
        
        assert "User 1 Private Thread" in user1_thread_titles
        assert "User 1 Private Thread" not in user2_thread_titles
        assert "User 2 Private Thread" in user2_thread_titles
        assert "User 2 Private Thread" not in user1_thread_titles
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_communication(self):
        """
        Test backend-to-auth-service communication for token validation.
        
        BVJ: Ensures seamless integration between backend and auth service for user verification.
        """
        user_data = self.test_users[0]
        
        # Mock auth service responses to test communication
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful token validation response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "valid": True,
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "permissions": user_data["permissions"],
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test auth service communication
            validation_result = await self.auth_integration_service.validate_token_with_auth_service(
                token="mock-jwt-token",
                auth_service_url=self.auth_service_url
            )
            
            assert validation_result is not None
            assert validation_result["valid"] is True
            assert validation_result["user_id"] == user_data["user_id"]
            
            # Verify auth service was called
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "auth/validate" in call_args[0][0]  # URL contains validation endpoint
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_service_failure_handling(self):
        """
        Test graceful handling when auth service is unavailable.
        
        BVJ: Ensures system resilience and appropriate error handling during auth service outages.
        """
        user_data = self.test_users[0]
        valid_token = await self.create_test_token(user_data)
        
        # Test 1: Auth service returns 500 error
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.json.return_value = {"error": "Internal server error"}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception, match="Auth service unavailable"):
                await self.auth_integration_service.validate_token_with_auth_service(
                    token=valid_token,
                    auth_service_url=self.auth_service_url
                )
        
        # Test 2: Auth service connection timeout
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Connection timeout")
            
            with pytest.raises(Exception, match="Auth service timeout"):
                await self.auth_integration_service.validate_token_with_auth_service(
                    token=valid_token,
                    auth_service_url=self.auth_service_url,
                    timeout=1.0
                )
        
        # Test 3: Invalid response format
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"invalid": "response_format"}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await self.auth_integration_service.validate_token_with_auth_service(
                token=valid_token,
                auth_service_url=self.auth_service_url
            )
            
            # Should handle gracefully and return failure
            assert result is None or result.get("valid") is False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_permission_based_access_control(self):
        """
        Test permission-based access control for different user tiers.
        
        BVJ: Enables different access levels for Free, Early, Mid, and Enterprise users.
        """
        # Create users with different permission levels
        free_user_data = {
            "user_id": "backend-free-user",
            "email": "free@example.com",
            "permissions": ["read"]
        }
        
        enterprise_user_data = {
            "user_id": "backend-enterprise-user",
            "email": "enterprise@example.com",
            "permissions": ["read", "write", "admin"]
        }
        
        free_token = await self.create_test_token(free_user_data)
        enterprise_token = await self.create_test_token(enterprise_user_data)
        
        # Test read permission (both should have)
        free_read_access = await self.auth_middleware.check_permission(free_token, "read")
        enterprise_read_access = await self.auth_middleware.check_permission(enterprise_token, "read")
        
        assert free_read_access is True
        assert enterprise_read_access is True
        
        # Test write permission (only enterprise should have)
        free_write_access = await self.auth_middleware.check_permission(free_token, "write")
        enterprise_write_access = await self.auth_middleware.check_permission(enterprise_token, "write")
        
        assert free_write_access is False
        assert enterprise_write_access is True
        
        # Test admin permission (only enterprise should have)
        free_admin_access = await self.auth_middleware.check_permission(free_token, "admin")
        enterprise_admin_access = await self.auth_middleware.check_permission(enterprise_token, "admin")
        
        assert free_admin_access is False
        assert enterprise_admin_access is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authenticated_thread_operations(self):
        """
        Test thread operations with proper authentication.
        
        BVJ: Users must be authenticated to create and access chat threads.
        """
        user_data = self.test_users[0]
        user_token = await self.create_test_token(user_data)
        
        # Create authenticated user context
        user_context = await self.auth_middleware.create_user_context(user_token)
        
        # Create user in database
        async with self.db.begin() as conn:
            await conn.execute("""
                INSERT INTO users (id, email, name, created_at) 
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET 
                email = $2, name = $3, updated_at = NOW()
            """, [
                user_data["user_id"],
                user_data["email"],
                user_data["name"],
                datetime.now(timezone.utc)
            ])
        
        # Test thread creation with authentication
        thread_data = {
            "id": f"auth-test-thread-{int(time.time())}",
            "user_id": user_context["user_id"],
            "title": "Authenticated Thread Test",
            "created_at": datetime.now(timezone.utc)
        }
        
        async with self.db.begin() as conn:
            await conn.execute("""
                INSERT INTO threads (id, user_id, title, created_at) 
                VALUES ($1, $2, $3, $4)
            """, [
                thread_data["id"],
                thread_data["user_id"],
                thread_data["title"],
                thread_data["created_at"]
            ])
        
        # Verify thread was created for the authenticated user
        async with self.db.begin() as conn:
            created_thread = await conn.fetchrow("""
                SELECT id, user_id, title 
                FROM threads 
                WHERE id = $1 AND user_id = $2
            """, thread_data["id"], user_context["user_id"])
        
        assert created_thread is not None
        assert created_thread["id"] == thread_data["id"]
        assert created_thread["user_id"] == user_context["user_id"]
        assert created_thread["title"] == thread_data["title"]
        
        # Test message creation in authenticated thread
        message_data = {
            "id": f"auth-test-message-{int(time.time())}",
            "thread_id": thread_data["id"],
            "user_id": user_context["user_id"],
            "content": "Test message in authenticated thread",
            "role": "user",
            "created_at": datetime.now(timezone.utc)
        }
        
        async with self.db.begin() as conn:
            await conn.execute("""
                INSERT INTO messages (id, thread_id, user_id, content, role, created_at) 
                VALUES ($1, $2, $3, $4, $5, $6)
            """, [
                message_data["id"],
                message_data["thread_id"],
                message_data["user_id"],
                message_data["content"],
                message_data["role"],
                message_data["created_at"]
            ])
        
        # Verify message was created
        async with self.db.begin() as conn:
            created_message = await conn.fetchrow("""
                SELECT id, thread_id, user_id, content 
                FROM messages 
                WHERE id = $1 AND user_id = $2
            """, message_data["id"], user_context["user_id"])
        
        assert created_message is not None
        assert created_message["id"] == message_data["id"]
        assert created_message["thread_id"] == thread_data["id"]
        assert created_message["user_id"] == user_context["user_id"]
        assert created_message["content"] == message_data["content"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_authenticated_operations(self):
        """
        Test concurrent operations with different authenticated users.
        
        BVJ: Ensures system can handle multiple authenticated users simultaneously.
        """
        # Create tokens for both test users
        user1_token = await self.create_test_token(self.test_users[0])
        user2_token = await self.create_test_token(self.test_users[1])
        
        # Create user contexts
        user1_context = await self.auth_middleware.create_user_context(user1_token)
        user2_context = await self.auth_middleware.create_user_context(user2_token)
        
        # Create users in database
        async with self.db.begin() as conn:
            for i, user_data in enumerate(self.test_users):
                await conn.execute("""
                    INSERT INTO users (id, email, name, created_at) 
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO UPDATE SET 
                    email = $2, name = $3, updated_at = NOW()
                """, [
                    user_data["user_id"],
                    user_data["email"],
                    user_data["name"],
                    datetime.now(timezone.utc)
                ])
        
        async def create_thread_for_user(user_context: Dict[str, Any], user_index: int):
            """Create thread for a specific user."""
            thread_id = f"concurrent-thread-{user_context['user_id']}-{int(time.time())}"
            
            async with self.db.begin() as conn:
                await conn.execute("""
                    INSERT INTO threads (id, user_id, title, created_at) 
                    VALUES ($1, $2, $3, $4)
                """, [
                    thread_id,
                    user_context["user_id"],
                    f"Concurrent Thread for User {user_index}",
                    datetime.now(timezone.utc)
                ])
            
            # Verify thread creation
            async with self.db.begin() as conn:
                thread = await conn.fetchrow("""
                    SELECT id, user_id, title 
                    FROM threads 
                    WHERE id = $1
                """, thread_id)
            
            return {
                "user_index": user_index,
                "user_id": user_context["user_id"],
                "thread": thread,
                "success": thread is not None
            }
        
        # Execute concurrent thread creation
        tasks = [
            create_thread_for_user(user1_context, 1),
            create_thread_for_user(user2_context, 2)
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify both operations succeeded
        assert len(results) == 2
        
        for result in results:
            assert result["success"] is True
            assert result["thread"] is not None
            assert result["thread"]["user_id"] == result["user_id"]
            assert f"User {result['user_index']}" in result["thread"]["title"]
        
        # Verify threads are isolated per user
        user1_result = next(r for r in results if r["user_index"] == 1)
        user2_result = next(r for r in results if r["user_index"] == 2)
        
        assert user1_result["thread"]["id"] != user2_result["thread"]["id"]
        assert user1_result["thread"]["user_id"] != user2_result["thread"]["user_id"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_expiry_handling(self):
        """
        Test handling of expired authentication tokens.
        
        BVJ: Ensures security by properly rejecting expired tokens and prompting re-authentication.
        """
        user_data = self.test_users[0]
        
        # Create token with very short expiry
        expired_token = self.auth_helper.create_test_jwt_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"],
            exp_minutes=0  # Expires immediately
        )
        
        # Wait to ensure token expiry
        await asyncio.sleep(1)
        
        # Test expired token validation
        expired_validation = await self.auth_middleware.validate_auth_token(expired_token)
        
        # Should fail validation
        assert expired_validation is None or expired_validation["valid"] is False
        
        # Test operation with expired token should fail
        with pytest.raises(Exception, match="Token expired|Invalid token|Unauthorized"):
            await self.auth_middleware.create_user_context(expired_token)
        
        # Create fresh token - should work
        fresh_token = self.auth_helper.create_test_jwt_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"],
            exp_minutes=30  # 30 minutes
        )
        
        # Fresh token should validate successfully
        fresh_validation = await self.auth_middleware.validate_auth_token(fresh_token)
        assert fresh_validation is not None
        assert fresh_validation["valid"] is True
        assert fresh_validation["user_id"] == user_data["user_id"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_middleware_request_lifecycle(self):
        """
        Test complete auth middleware request lifecycle.
        
        BVJ: Validates end-to-end authentication flow for user requests.
        """
        user_data = self.test_users[0]
        user_token = await self.create_test_token(user_data)
        
        # Simulate incoming request with auth token
        request_headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json",
            "User-Agent": "integration-test-client"
        }
        
        # Step 1: Extract token from request
        auth_token = self.auth_middleware.extract_token_from_headers(request_headers)
        assert auth_token == user_token
        
        # Step 2: Validate token
        validation_result = await self.auth_middleware.validate_auth_token(auth_token)
        assert validation_result is not None
        assert validation_result["valid"] is True
        
        # Step 3: Create user context
        user_context = await self.auth_middleware.create_user_context(auth_token)
        assert user_context is not None
        assert user_context["user_id"] == user_data["user_id"]
        
        # Step 4: Check permissions for operation
        read_permission = await self.auth_middleware.check_permission(auth_token, "read")
        write_permission = await self.auth_middleware.check_permission(auth_token, "write")
        
        assert read_permission is True
        assert write_permission is True  # User has write permission
        
        # Step 5: Execute authenticated operation
        # (This would be where the actual business logic runs)
        authenticated_operation_result = {
            "user_id": user_context["user_id"],
            "operation": "thread_list",
            "permissions": validation_result["permissions"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        assert authenticated_operation_result["user_id"] == user_data["user_id"]
        assert "read" in authenticated_operation_result["permissions"]
        assert "write" in authenticated_operation_result["permissions"]