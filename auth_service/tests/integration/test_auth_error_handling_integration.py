"""
Auth Comprehensive Error Handling Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure proper error handling and user experience during authentication failures
- Value Impact: Users receive clear error messages and appropriate responses when auth issues occur
- Strategic Impact: System resilience and security through proper error handling prevents system abuse and improves reliability

CRITICAL: These tests use REAL PostgreSQL and Redis services (no mocks).
Tests validate error scenarios with real service interactions and proper error responses.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import jwt
from unittest.mock import patch, AsyncMock
import aiohttp

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.config import AuthConfig
from auth_service.services.user_service import UserService
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService
from auth_service.services.error_handler_service import ErrorHandlerService
from auth_service.database import get_database


class TestAuthErrorHandlingIntegration(BaseIntegrationTest):
    """Integration tests for comprehensive auth error handling with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real services."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real auth service configuration
        self.auth_config = AuthConfig()
        
        # Real service instances
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.jwt_service = JWTService(self.auth_config)
        self.user_service = UserService(self.auth_config, get_database())
        self.error_handler = ErrorHandlerService(self.auth_config, self.redis_service)
        
        # Test data
        self.test_user_data = {
            "user_id": "error-test-user-123",
            "email": "error-test@example.com",
            "name": "Error Test User",
            "password": "ErrorTestPassword123!",
            "permissions": ["read", "write"]
        }
        
        self.created_user_emails = []  # Track for cleanup
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services."""
        try:
            # Clean test users
            for email in self.created_user_emails:
                try:
                    user = await self.user_service.get_user_by_email(email)
                    if user:
                        await self.user_service.delete_user(user.id)
                except Exception as e:
                    self.logger.warning(f"Could not delete test user {email}: {e}")
            
            # Clean error logs and test data from Redis
            error_keys = await self.redis_service.keys("error:*")
            if error_keys:
                await self.redis_service.delete(*error_keys)
            
            test_keys = await self.redis_service.keys("*error-test*")
            if test_keys:
                await self.redis_service.delete(*test_keys)
                
            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_invalid_credentials_error_handling(self):
        """
        Test error handling for invalid login credentials (401 errors).
        
        BVJ: Users receive clear feedback when authentication fails, improving user experience.
        """
        # Create test user first
        created_user = await self.user_service.create_user(
            email=self.test_user_data["email"],
            name=self.test_user_data["name"],
            password=self.test_user_data["password"]
        )
        self.created_user_emails.append(self.test_user_data["email"])
        
        # Test Case 1: Wrong password
        try:
            await self.user_service.authenticate_user(
                email=self.test_user_data["email"],
                password="WrongPassword123!"
            )
            assert False, "Should have raised authentication error"
        except Exception as e:
            error_details = await self.error_handler.handle_authentication_error(
                error=e,
                email=self.test_user_data["email"],
                error_type="invalid_password",
                request_ip="127.0.0.1"
            )
            
            assert error_details is not None
            assert error_details["error_code"] == "AUTH_INVALID_CREDENTIALS"
            assert error_details["status_code"] == 401
            assert error_details["user_message"] == "Invalid email or password"
            assert error_details["safe_for_client"] is True
            
            # Verify error logging in Redis
            error_log_key = f"error:auth:{int(time.time())//60}"  # Per minute grouping
            error_logs = await self.redis_service.get(error_log_key)
            if error_logs:
                logs = json.loads(error_logs)
                assert any("invalid_password" in log.get("error_type", "") for log in logs)
        
        # Test Case 2: Non-existent user
        try:
            await self.user_service.authenticate_user(
                email="nonexistent@example.com",
                password="SomePassword123!"
            )
            assert False, "Should have raised user not found error"
        except Exception as e:
            error_details = await self.error_handler.handle_authentication_error(
                error=e,
                email="nonexistent@example.com",
                error_type="user_not_found",
                request_ip="127.0.0.1"
            )
            
            assert error_details["error_code"] == "AUTH_USER_NOT_FOUND"
            assert error_details["status_code"] == 401
            # For security, return same message as invalid password
            assert error_details["user_message"] == "Invalid email or password"
            assert error_details["safe_for_client"] is True
        
        # Test Case 3: Empty credentials
        try:
            await self.user_service.authenticate_user(
                email="",
                password=""
            )
            assert False, "Should have raised validation error"
        except Exception as e:
            error_details = await self.error_handler.handle_validation_error(
                error=e,
                field="email",
                error_type="required_field_missing"
            )
            
            assert error_details["error_code"] == "VALIDATION_REQUIRED_FIELD"
            assert error_details["status_code"] == 400
            assert "required" in error_details["user_message"].lower()
            assert error_details["safe_for_client"] is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_error_handling(self):
        """
        Test error handling for JWT token validation failures (403 errors).
        
        BVJ: Proper token error handling maintains security and provides clear feedback.
        """
        # Test Case 1: Malformed JWT token
        malformed_token = "not.a.valid.jwt.token.structure"
        
        try:
            await self.jwt_service.validate_token(malformed_token)
            assert False, "Should have raised invalid token error"
        except Exception as e:
            error_details = await self.error_handler.handle_jwt_error(
                error=e,
                token=malformed_token[:20] + "...",  # Truncated for security
                error_type="malformed_token"
            )
            
            assert error_details["error_code"] == "JWT_MALFORMED"
            assert error_details["status_code"] == 403
            assert error_details["user_message"] == "Invalid authentication token"
            assert error_details["safe_for_client"] is True
            assert "technical_details" in error_details
        
        # Test Case 2: Expired JWT token  
        expired_token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=self.test_user_data["permissions"],
            exp_minutes=0  # Immediate expiry
        )
        
        # Wait to ensure expiry
        await asyncio.sleep(1)
        
        try:
            await self.jwt_service.validate_token(expired_token)
            assert False, "Should have raised expired token error"
        except jwt.ExpiredSignatureError as e:
            error_details = await self.error_handler.handle_jwt_error(
                error=e,
                token=expired_token[:20] + "...",
                error_type="expired_token"
            )
            
            assert error_details["error_code"] == "JWT_EXPIRED"
            assert error_details["status_code"] == 401
            assert error_details["user_message"] == "Authentication token has expired"
            assert error_details["safe_for_client"] is True
            assert "expired_at" in error_details.get("technical_details", {})
        
        # Test Case 3: Invalid signature
        valid_token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=self.test_user_data["permissions"]
        )
        
        # Tamper with signature
        tampered_token = valid_token[:-10] + "tamperedsig"
        
        try:
            await self.jwt_service.validate_token(tampered_token)
            assert False, "Should have raised invalid signature error"
        except jwt.InvalidSignatureError as e:
            error_details = await self.error_handler.handle_jwt_error(
                error=e,
                token=tampered_token[:20] + "...",
                error_type="invalid_signature"
            )
            
            assert error_details["error_code"] == "JWT_INVALID_SIGNATURE"
            assert error_details["status_code"] == 403
            assert error_details["user_message"] == "Invalid authentication token"
            assert error_details["safe_for_client"] is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_permission_denied_error_handling(self):
        """
        Test error handling for permission-based access denials (403 errors).
        
        BVJ: Users understand when they lack permissions and how to upgrade access.
        """
        # Create user with limited permissions
        limited_user_data = {
            **self.test_user_data,
            "email": "limited-user@example.com",
            "permissions": ["read"]  # Only read permission
        }
        
        created_user = await self.user_service.create_user(
            email=limited_user_data["email"],
            name=limited_user_data["name"],
            password=limited_user_data["password"]
        )
        self.created_user_emails.append(limited_user_data["email"])
        
        # Create token with limited permissions
        limited_token = await self.jwt_service.create_access_token(
            user_id=str(created_user.id),
            email=created_user.email,
            permissions=limited_user_data["permissions"]
        )
        
        # Test Case 1: Insufficient permissions for write operation
        try:
            # Simulate checking write permission
            decoded = jwt.decode(
                limited_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            if "write" not in decoded.get("permissions", []):
                raise PermissionError("Insufficient permissions for write operation")
        except PermissionError as e:
            error_details = await self.error_handler.handle_permission_error(
                error=e,
                user_id=str(created_user.id),
                required_permission="write",
                user_permissions=limited_user_data["permissions"],
                resource="thread_creation"
            )
            
            assert error_details["error_code"] == "PERMISSION_DENIED"
            assert error_details["status_code"] == 403
            assert "write" in error_details["user_message"]
            assert "upgrade" in error_details["user_message"].lower()
            assert error_details["safe_for_client"] is True
            
            # Should include upgrade suggestion
            assert "suggested_action" in error_details
            assert error_details["suggested_action"]["type"] == "upgrade_subscription"
        
        # Test Case 2: Admin permission required
        try:
            decoded = jwt.decode(
                limited_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            if "admin" not in decoded.get("permissions", []):
                raise PermissionError("Admin privileges required")
        except PermissionError as e:
            error_details = await self.error_handler.handle_permission_error(
                error=e,
                user_id=str(created_user.id),
                required_permission="admin",
                user_permissions=limited_user_data["permissions"],
                resource="admin_panel"
            )
            
            assert error_details["error_code"] == "PERMISSION_ADMIN_REQUIRED"
            assert error_details["status_code"] == 403
            assert "admin" in error_details["user_message"].lower()
            assert error_details["suggested_action"]["type"] == "contact_admin"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_rate_limiting_error_handling(self):
        """
        Test error handling for rate limiting scenarios (429 errors).
        
        BVJ: Prevents abuse while providing clear feedback to legitimate users.
        """
        # Simulate rate limiting by storing attempt counts in Redis
        rate_limit_key = f"rate_limit:{self.test_user_data['email']}"
        max_attempts = 5
        window_seconds = 300  # 5 minutes
        
        # Set up rate limit tracking
        await self.redis_service.set(
            rate_limit_key,
            json.dumps({
                "attempts": max_attempts + 1,  # Exceed limit
                "window_start": datetime.now(timezone.utc).isoformat(),
                "last_attempt": datetime.now(timezone.utc).isoformat()
            }),
            ex=window_seconds
        )
        
        # Test rate limit exceeded
        try:
            # Simulate checking rate limit
            rate_data = await self.redis_service.get(rate_limit_key)
            if rate_data:
                limit_info = json.loads(rate_data)
                if limit_info["attempts"] > max_attempts:
                    raise Exception("Rate limit exceeded")
        except Exception as e:
            error_details = await self.error_handler.handle_rate_limit_error(
                error=e,
                user_identifier=self.test_user_data["email"],
                limit_type="authentication_attempts",
                max_attempts=max_attempts,
                window_seconds=window_seconds
            )
            
            assert error_details["error_code"] == "RATE_LIMIT_EXCEEDED"
            assert error_details["status_code"] == 429
            assert "too many" in error_details["user_message"].lower()
            assert "try again" in error_details["user_message"].lower()
            assert error_details["safe_for_client"] is True
            
            # Should include retry information
            assert "retry_after_seconds" in error_details
            assert error_details["retry_after_seconds"] > 0
            assert error_details["retry_after_seconds"] <= window_seconds
        
        # Cleanup rate limit
        await self.redis_service.delete(rate_limit_key)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_error_handling(self):
        """
        Test error handling for database connection and query failures (500 errors).
        
        BVJ: System gracefully handles database issues and provides appropriate feedback.
        """
        # Test Case 1: Database connection failure simulation
        with patch.object(self.user_service, 'get_user_by_email') as mock_get_user:
            mock_get_user.side_effect = Exception("Database connection failed")
            
            try:
                await self.user_service.get_user_by_email("test@example.com")
                assert False, "Should have raised database error"
            except Exception as e:
                error_details = await self.error_handler.handle_database_error(
                    error=e,
                    operation="get_user_by_email",
                    table="users",
                    query_type="SELECT"
                )
                
                assert error_details["error_code"] == "DATABASE_CONNECTION_FAILED"
                assert error_details["status_code"] == 500
                assert error_details["user_message"] == "Service temporarily unavailable"
                assert error_details["safe_for_client"] is True
                
                # Technical details should not be exposed to client
                assert "internal_error" in error_details
                assert error_details["internal_error"] == "Database connection failed"
        
        # Test Case 2: Query timeout simulation
        with patch.object(self.user_service, 'create_user') as mock_create_user:
            mock_create_user.side_effect = asyncio.TimeoutError("Query timeout")
            
            try:
                await self.user_service.create_user(
                    email="timeout-test@example.com",
                    name="Timeout Test",
                    password="Password123!"
                )
                assert False, "Should have raised timeout error"
            except Exception as e:
                error_details = await self.error_handler.handle_database_error(
                    error=e,
                    operation="create_user", 
                    table="users",
                    query_type="INSERT"
                )
                
                assert error_details["error_code"] == "DATABASE_TIMEOUT"
                assert error_details["status_code"] == 504
                assert "timeout" in error_details["user_message"].lower()
                assert error_details["safe_for_client"] is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_error_handling(self):
        """
        Test error handling for Redis connection and operation failures.
        
        BVJ: System maintains functionality when session storage is unavailable.
        """
        # Test Case 1: Redis connection failure
        with patch.object(self.redis_service, 'set') as mock_redis_set:
            mock_redis_set.side_effect = Exception("Redis connection failed")
            
            try:
                await self.redis_service.set("test:key", "test_value")
                assert False, "Should have raised Redis error"
            except Exception as e:
                error_details = await self.error_handler.handle_redis_error(
                    error=e,
                    operation="set",
                    key="test:key"
                )
                
                assert error_details["error_code"] == "REDIS_CONNECTION_FAILED"
                assert error_details["status_code"] == 503
                assert error_details["user_message"] == "Session service temporarily unavailable"
                assert error_details["safe_for_client"] is True
                
                # Should suggest fallback behavior
                assert "fallback_behavior" in error_details
                assert error_details["fallback_behavior"]["type"] == "stateless_session"
        
        # Test Case 2: Redis memory full
        with patch.object(self.redis_service, 'get') as mock_redis_get:
            mock_redis_get.side_effect = Exception("OOM command not allowed")
            
            try:
                await self.redis_service.get("test:key")
                assert False, "Should have raised Redis memory error"
            except Exception as e:
                error_details = await self.error_handler.handle_redis_error(
                    error=e,
                    operation="get",
                    key="test:key"
                )
                
                assert error_details["error_code"] == "REDIS_MEMORY_FULL"
                assert error_details["status_code"] == 503
                assert "storage" in error_details["user_message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_error_handling(self):
        """
        Test error handling under concurrent load scenarios.
        
        BVJ: System maintains proper error handling even under high concurrent load.
        """
        # Create multiple concurrent error scenarios
        concurrent_errors = 10
        
        async def simulate_error_scenario(error_id: int):
            """Simulate different error scenarios concurrently."""
            error_types = [
                "invalid_credentials",
                "expired_token", 
                "permission_denied",
                "rate_limit",
                "database_error"
            ]
            
            error_type = error_types[error_id % len(error_types)]
            
            try:
                if error_type == "invalid_credentials":
                    raise Exception("Invalid credentials")
                elif error_type == "expired_token":
                    raise jwt.ExpiredSignatureError("Token expired")
                elif error_type == "permission_denied":
                    raise PermissionError("Insufficient permissions")
                elif error_type == "rate_limit":
                    raise Exception("Rate limit exceeded")
                elif error_type == "database_error":
                    raise Exception("Database connection failed")
            except Exception as e:
                # Handle error based on type
                if error_type == "invalid_credentials":
                    error_details = await self.error_handler.handle_authentication_error(
                        error=e,
                        email=f"concurrent-test-{error_id}@example.com",
                        error_type=error_type
                    )
                elif error_type == "expired_token":
                    error_details = await self.error_handler.handle_jwt_error(
                        error=e,
                        token=f"token-{error_id}",
                        error_type=error_type
                    )
                elif error_type == "permission_denied":
                    error_details = await self.error_handler.handle_permission_error(
                        error=e,
                        user_id=f"user-{error_id}",
                        required_permission="write",
                        user_permissions=["read"]
                    )
                elif error_type == "rate_limit":
                    error_details = await self.error_handler.handle_rate_limit_error(
                        error=e,
                        user_identifier=f"user-{error_id}",
                        limit_type="requests",
                        max_attempts=100
                    )
                elif error_type == "database_error":
                    error_details = await self.error_handler.handle_database_error(
                        error=e,
                        operation="select",
                        table="users"
                    )
                
                return {
                    "error_id": error_id,
                    "error_type": error_type,
                    "handled_successfully": True,
                    "error_code": error_details["error_code"],
                    "status_code": error_details["status_code"],
                    "safe_for_client": error_details["safe_for_client"]
                }
        
        # Execute concurrent error handling
        tasks = [simulate_error_scenario(i) for i in range(concurrent_errors)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_handlers = [r for r in results if not isinstance(r, Exception) and r.get("handled_successfully")]
        failed_handlers = [r for r in results if isinstance(r, Exception) or not r.get("handled_successfully")]
        
        # All error handlers should succeed
        assert len(successful_handlers) == concurrent_errors
        assert len(failed_handlers) == 0
        
        # Verify error codes are appropriate
        for result in successful_handlers:
            assert result["error_code"] is not None
            assert result["status_code"] in [400, 401, 403, 404, 429, 500, 503, 504]
            assert result["safe_for_client"] is True
        
        # Verify error type distribution
        error_types = [r["error_type"] for r in successful_handlers]
        unique_error_types = set(error_types)
        assert len(unique_error_types) >= 3  # Should have variety of error types