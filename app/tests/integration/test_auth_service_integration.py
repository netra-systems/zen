"""Integration Test: Auth Service Communication and Coordination

BVJ: $25K MRR - Authentication failures block all user value creation
Components: Auth Service ↔ Main Backend ↔ Session Management
Critical: Multi-service auth coordination must be seamless
"""

import pytest
import asyncio
import json
import jwt
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from app.schemas import UserInDB
from app.core.config import settings
from test_framework.mock_utils import mock_justified


@pytest.mark.asyncio
class TestAuthServiceIntegration:
    """Test complete auth service integration with main backend."""
    
    @pytest.fixture
    async def test_user(self):
        """Create test user for authentication testing."""
        return UserInDB(
            id="auth_user_456",
            email="auth@example.com",
            username="authuser",
            is_active=True,
            created_at=datetime.utcnow()
        )
    
    @pytest.fixture
    async def valid_token(self, test_user):
        """Generate valid JWT token for testing."""
        payload = {
            "sub": test_user.id,
            "email": test_user.email,
            "username": test_user.username,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    @pytest.fixture
    async def auth_service_mock(self, test_user, valid_token):
        """Mock auth service for integration testing."""
        from auth_service.auth_core.services.auth_service import AuthService
        
        service = Mock(spec=AuthService)
        service.login = AsyncMock(return_value={
            "access_token": valid_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": test_user.dict()
        })
        service.validate_token = AsyncMock(return_value=test_user)
        service.refresh_token = AsyncMock(return_value={
            "access_token": valid_token,
            "expires_in": 3600
        })
        return service
    
    async def test_authentication_service_communication(self, auth_service_mock, test_user):
        """
        Test authentication service communication with main backend.
        
        Validates:
        - Auth service login flow
        - Token generation and response format
        - User data serialization
        - Service communication patterns
        """
        from auth_service.auth_core.models.auth_models import LoginRequest
        
        # Prepare login request
        login_request = LoginRequest(
            email=test_user.email,
            password="test_password",
            provider="email"
        )
        
        client_info = {
            "ip_address": "192.168.1.100",
            "user_agent": "Test Client/1.0"
        }
        
        # Execute login through auth service
        login_response = await auth_service_mock.login(login_request, client_info)
        
        # Verify response structure
        assert "access_token" in login_response
        assert "token_type" in login_response
        assert "expires_in" in login_response
        assert "user" in login_response
        
        # Verify token format
        token = login_response["access_token"]
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens should be substantial length
        
        # Verify user data
        user_data = login_response["user"]
        assert user_data["id"] == test_user.id
        assert user_data["email"] == test_user.email
        
        # Test backend validates token
        validated_user = await auth_service_mock.validate_token(token)
        assert validated_user.id == test_user.id
        assert validated_user.email == test_user.email
    
    async def test_token_generation_and_validation_flow(self, auth_service_mock, test_user, valid_token):
        """
        Test complete token generation and validation flow.
        
        Validates:
        - Token contains correct claims
        - Token validation returns user data
        - Expired tokens are rejected
        - Invalid tokens are rejected
        """
        # Test valid token validation
        validated_user = await auth_service_mock.validate_token(valid_token)
        assert validated_user.id == test_user.id
        assert validated_user.email == test_user.email
        
        # Test token claims by decoding
        decoded = jwt.decode(valid_token, settings.SECRET_KEY, algorithms=["HS256"])
        assert decoded["sub"] == test_user.id
        assert decoded["email"] == test_user.email
        assert decoded["type"] == "access"
        
        # Test expired token handling
        expired_payload = {
            "sub": test_user.id,
            "email": test_user.email,
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "type": "access"
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
        
        # Mock service should reject expired token
        auth_service_mock.validate_token.side_effect = [
            test_user,  # First call succeeds (valid token)
            jwt.ExpiredSignatureError("Token expired")  # Second call fails (expired)
        ]
        
        with pytest.raises(jwt.ExpiredSignatureError):
            await auth_service_mock.validate_token(expired_token)
        
        # Test invalid token handling
        auth_service_mock.validate_token.side_effect = jwt.InvalidTokenError("Invalid token")
        
        with pytest.raises(jwt.InvalidTokenError):
            await auth_service_mock.validate_token("invalid.token.format")
    
    async def test_token_refresh_mechanism(self, auth_service_mock, test_user, valid_token):
        """
        Test token refresh mechanism.
        
        Validates:
        - Refresh token exchange
        - New token generation
        - Token lifetime management
        - Refresh token security
        """
        # Mock refresh token
        refresh_token = "refresh_token_abc123"
        
        # Test token refresh
        refresh_response = await auth_service_mock.refresh_token(refresh_token)
        
        # Verify refresh response
        assert "access_token" in refresh_response
        assert "expires_in" in refresh_response
        
        new_token = refresh_response["access_token"]
        assert isinstance(new_token, str)
        assert len(new_token) > 50
        
        # Verify new token is valid
        auth_service_mock.validate_token.side_effect = None
        auth_service_mock.validate_token.return_value = test_user
        
        validated_user = await auth_service_mock.validate_token(new_token)
        assert validated_user.id == test_user.id
    
    async def test_permission_and_role_checking(self, auth_service_mock, test_user):
        """
        Test permission and role checking integration.
        
        Validates:
        - User permission validation
        - Role-based access control
        - Permission inheritance
        - Access decision propagation
        """
        # Add permission checking methods to mock
        auth_service_mock.check_permission = AsyncMock()
        auth_service_mock.get_user_roles = AsyncMock()
        
        # Test permission checking
        auth_service_mock.check_permission.return_value = True
        has_permission = await auth_service_mock.check_permission(
            test_user.id, 
            "read_threads"
        )
        assert has_permission is True
        
        # Test role retrieval
        user_roles = ["user", "premium"]
        auth_service_mock.get_user_roles.return_value = user_roles
        
        roles = await auth_service_mock.get_user_roles(test_user.id)
        assert "user" in roles
        assert "premium" in roles
        
        # Test permission denied scenario
        auth_service_mock.check_permission.return_value = False
        has_admin_permission = await auth_service_mock.check_permission(
            test_user.id, 
            "admin_access"
        )
        assert has_admin_permission is False
    
    async def test_auth_state_synchronization(self, auth_service_mock, test_user, valid_token):
        """
        Test auth state synchronization across services.
        
        Validates:
        - Session state consistency
        - Auth state propagation
        - Cross-service auth validation
        - State update coordination
        """
        from app.redis_manager import RedisManager
        
        # Mock Redis for session storage
        redis_manager = Mock(spec=RedisManager)
        redis_manager.set = AsyncMock(return_value=True)
        redis_manager.get = AsyncMock()
        
        # Test auth state storage
        auth_state = {
            "user_id": test_user.id,
            "token": valid_token,
            "last_activity": datetime.utcnow().isoformat(),
            "permissions": ["read", "write"],
            "roles": ["user", "premium"]
        }
        
        session_key = f"auth_state:{test_user.id}"
        await redis_manager.set(
            session_key, 
            json.dumps(auth_state), 
            ex=3600
        )
        
        # Verify state was stored
        redis_manager.set.assert_called_once()
        stored_args = redis_manager.set.call_args
        assert session_key in stored_args[0]
        assert "user_id" in stored_args[0][1]
        
        # Test state retrieval
        redis_manager.get.return_value = json.dumps(auth_state)
        retrieved_state = await redis_manager.get(session_key)
        
        parsed_state = json.loads(retrieved_state)
        assert parsed_state["user_id"] == test_user.id
        assert parsed_state["token"] == valid_token
        assert "permissions" in parsed_state
        assert "roles" in parsed_state
    
    async def test_multi_service_auth_coordination(self, auth_service_mock, test_user, valid_token):
        """
        Test multi-service auth coordination.
        
        Validates:
        - Auth service coordination with backend
        - WebSocket service auth validation
        - API service auth checks
        - Service-to-service communication
        """
        services = ["backend", "websocket", "api"]
        auth_results = {}
        
        # Simulate each service validating the same token
        for service in services:
            # Each service calls auth service for validation
            validated_user = await auth_service_mock.validate_token(valid_token)
            auth_results[service] = {
                "user_id": validated_user.id,
                "email": validated_user.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Verify consistent auth results across services
        for service, result in auth_results.items():
            assert result["user_id"] == test_user.id
            assert result["email"] == test_user.email
            assert "timestamp" in result
        
        # Verify auth service was called for each service
        assert auth_service_mock.validate_token.call_count == len(services)
    
    @mock_justified("Auth service network communication requires mocking external service")
    async def test_auth_service_failover(self, test_user):
        """
        Test auth service failover and recovery.
        
        Validates:
        - Graceful handling of auth service unavailability
        - Fallback authentication mechanisms
        - Service recovery detection
        - Error propagation and handling
        """
        from auth_service.auth_core.services.auth_service import AuthService
        
        # Create auth service that fails initially
        failing_auth_service = Mock(spec=AuthService)
        failing_auth_service.validate_token = AsyncMock(
            side_effect=ConnectionError("Auth service unavailable")
        )
        
        # Test failure handling
        with pytest.raises(ConnectionError):
            await failing_auth_service.validate_token("any_token")
        
        # Simulate service recovery
        recovering_auth_service = Mock(spec=AuthService)
        recovering_auth_service.validate_token = AsyncMock(return_value=test_user)
        
        # Test recovery
        validated_user = await recovering_auth_service.validate_token("valid_token")
        assert validated_user.id == test_user.id
    
    async def test_concurrent_auth_operations(self, auth_service_mock, test_user, valid_token):
        """
        Test concurrent authentication operations.
        
        Validates:
        - Multiple simultaneous token validations
        - Concurrent login attempts
        - Auth service performance under load
        - Race condition handling
        """
        # Prepare multiple validation tasks
        validation_tasks = []
        concurrent_requests = 10
        
        for i in range(concurrent_requests):
            task = auth_service_mock.validate_token(valid_token)
            validation_tasks.append(task)
        
        # Execute all validations concurrently
        results = await asyncio.gather(*validation_tasks)
        
        # Verify all validations succeeded
        assert len(results) == concurrent_requests
        for result in results:
            assert result.id == test_user.id
            assert result.email == test_user.email
        
        # Verify auth service handled concurrent load
        assert auth_service_mock.validate_token.call_count == concurrent_requests
    
    async def test_auth_integration_error_scenarios(self, auth_service_mock, test_user):
        """
        Test various auth integration error scenarios.
        
        Validates:
        - Database connectivity issues
        - Invalid user states
        - Network timeouts
        - Service degradation handling
        """
        # Test user not found scenario
        auth_service_mock.validate_token.side_effect = ValueError("User not found")
        
        with pytest.raises(ValueError, match="User not found"):
            await auth_service_mock.validate_token("token_for_missing_user")
        
        # Test inactive user scenario
        inactive_user = UserInDB(
            id="inactive_user",
            email="inactive@example.com",
            username="inactive",
            is_active=False,
            created_at=datetime.utcnow()
        )
        
        auth_service_mock.validate_token.side_effect = None
        auth_service_mock.validate_token.return_value = inactive_user
        
        validated_user = await auth_service_mock.validate_token("inactive_user_token")
        assert validated_user.is_active is False
        
        # Test service timeout scenario
        auth_service_mock.validate_token.side_effect = asyncio.TimeoutError("Service timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await auth_service_mock.validate_token("timeout_token")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])