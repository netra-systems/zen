"""
Integration Tests: Cross-Service Authentication Communication for WebSocket

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical Infrastructure  
- Business Goal: System Stability & Security - Protects $500K+ ARR Golden Path
- Value Impact: Ensures reliable authentication flow across all services for WebSocket connections
- Revenue Impact: Prevents authentication failures that would break user chat experience

CRITICAL PURPOSE: These integration tests validate that UnifiedAuthenticationService 
properly communicates with AuthServiceClient and handles cross-service authentication 
scenarios that are essential for WebSocket connections.

Test Coverage Areas:
1. UnifiedAuthenticationService to AuthServiceClient integration
2. Service-to-service authentication token validation  
3. Auth service circuit breaker behavior during failures
4. Authentication method fallback and retry logic
5. Auth service health check and availability validation
6. Cross-service token exchange and propagation
7. Authentication context switching (REST API vs WebSocket)
"""

import asyncio
import json
import pytest
import time
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
import httpx

from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.fixtures.auth import auth_service_client_fixture
from netra_backend.app.services.unified_authentication_service import (
    UnifiedAuthenticationService,
    AuthenticationContext
)
from netra_backend.app.auth import AuthenticationResult, AuthMethodType
from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceError,
    AuthServiceConnectionError,
    AuthServiceNotAvailableError,
    AuthServiceValidationError
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.environment_constants import Environment


@pytest.mark.integration
@pytest.mark.asyncio
class TestUnifiedAuthServiceClientIntegration(BaseIntegrationTest):
    """Integration tests for UnifiedAuthenticationService with AuthServiceClient communication."""
    
    async def setup_method(self):
        """Setup test environment with real service instances."""
        await super().setup_method()
        
        # Create real service instances for integration testing
        self.auth_client = AuthServiceClient()
        self.unified_auth_service = UnifiedAuthenticationService()
        
        # Test user context
        self.test_user_id = "test-user-123"
        self.test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZXhwIjoyMTQ3NDgzNjQ3fQ.test"
        
    async def teardown_method(self):
        """Cleanup test resources."""
        if hasattr(self, 'auth_client') and self.auth_client:
            await self.auth_client.cleanup()
        await super().teardown_method()

    async def test_unified_auth_service_client_token_validation_success(self):
        """
        BVJ: Ensures token validation works end-to-end between services
        Critical for maintaining user sessions across WebSocket connections
        """
        # Mock successful auth service response
        with patch.object(self.auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": self.test_user_id,
                "permissions": ["websocket_access"]
            }
            
            # Create authentication context
            auth_context = AuthenticationContext(
                token=self.test_token,
                user_id=self.test_user_id,
                method=AuthMethodType.JWT_BEARER,
                source="websocket_handshake"
            )
            
            # Test unified service integration
            result = await self.unified_auth_service.authenticate_user(auth_context)
            
            # Validate integration success
            assert result.success is True
            assert result.user_id == self.test_user_id
            assert result.authentication_method == AuthMethodType.JWT_BEARER
            assert "websocket_access" in result.permissions
            
            # Verify auth client was called properly
            mock_validate.assert_called_once_with(self.test_token)

    async def test_unified_auth_service_client_communication_failure_handling(self):
        """
        BVJ: Tests service resilience when auth service is unreachable
        Prevents complete system failure when auth service has issues
        """
        # Simulate auth service connection failure
        with patch.object(self.auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = AuthServiceConnectionError("Auth service unreachable")
            
            auth_context = AuthenticationContext(
                token=self.test_token,
                user_id=self.test_user_id,
                method=AuthMethodType.JWT_BEARER,
                source="websocket_handshake"
            )
            
            # Test failure handling
            result = await self.unified_auth_service.authenticate_user(auth_context)
            
            # Should handle failure gracefully
            assert result.success is False
            assert result.error_code == "AUTH_SERVICE_UNAVAILABLE"
            assert "Auth service unreachable" in result.error_message
            
            # Verify fallback mechanisms triggered
            assert result.fallback_attempted is True

    async def test_service_to_service_authentication_token_validation(self):
        """
        BVJ: Validates service-to-service authentication for backend-to-auth communication
        Essential for WebSocket service calling auth service for user validation
        """
        # Test service-to-service authentication
        with patch.object(self.auth_client, 'authenticate_service') as mock_auth_service:
            mock_auth_service.return_value = {
                "service_token": "service-auth-token-123",
                "expires_in": 3600,
                "service_id": "netra-backend"
            }
            
            # Authenticate service-to-service
            service_auth_result = await self.unified_auth_service.authenticate_service(
                service_id="netra-backend",
                service_secret="backend-service-secret"
            )
            
            assert service_auth_result["service_token"] is not None
            assert service_auth_result["service_id"] == "netra-backend"
            assert service_auth_result["expires_in"] > 0
            
            mock_auth_service.assert_called_once_with(
                service_id="netra-backend",
                service_secret="backend-service-secret"
            )

    async def test_auth_service_circuit_breaker_integration(self):
        """
        BVJ: Tests circuit breaker behavior during auth service failures
        Prevents cascading failures in WebSocket authentication
        """
        failure_count = 0
        
        async def mock_failing_validation(token):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise AuthServiceConnectionError(f"Failure {failure_count}")
            return {"valid": True, "user_id": self.test_user_id}
            
        with patch.object(self.auth_client, 'validate_token', side_effect=mock_failing_validation):
            
            # Test circuit breaker activation
            for i in range(5):
                auth_context = AuthenticationContext(
                    token=f"token-{i}",
                    user_id=self.test_user_id,
                    method=AuthMethodType.JWT_BEARER,
                    source="websocket_handshake"
                )
                
                result = await self.unified_auth_service.authenticate_user(auth_context)
                
                if i < 3:
                    # Should fail initially
                    assert result.success is False
                    assert result.error_code == "AUTH_SERVICE_UNAVAILABLE"
                else:
                    # Circuit breaker should allow recovery
                    assert result.success is True
                    
                # Small delay for circuit breaker timing
                await asyncio.sleep(0.1)

    async def test_authentication_method_fallback_and_retry_logic(self):
        """
        BVJ: Tests fallback authentication methods when primary method fails
        Ensures WebSocket connections can still authenticate through backup methods
        """
        # Setup primary method failure, secondary method success
        jwt_fail_count = 0
        
        async def mock_jwt_validation(token):
            nonlocal jwt_fail_count
            jwt_fail_count += 1
            if jwt_fail_count <= 2:
                raise AuthServiceValidationError("JWT validation failed")
            return {"valid": True, "user_id": self.test_user_id}
        
        with patch.object(self.auth_client, 'validate_token', side_effect=mock_jwt_validation):
            with patch.object(self.auth_client, 'validate_session') as mock_session:
                mock_session.return_value = {
                    "valid": True,
                    "user_id": self.test_user_id,
                    "session_id": "session-123"
                }
                
                auth_context = AuthenticationContext(
                    token=self.test_token,
                    user_id=self.test_user_id,
                    method=AuthMethodType.JWT_BEARER,
                    source="websocket_handshake",
                    fallback_session_id="session-123"
                )
                
                # Test fallback mechanism
                result = await self.unified_auth_service.authenticate_user(auth_context)
                
                # Should succeed through fallback
                assert result.success is True
                assert result.authentication_method == AuthMethodType.SESSION_BASED
                assert result.fallback_attempted is True

    async def test_auth_service_health_check_and_availability_validation(self):
        """
        BVJ: Tests health check integration with auth service
        Prevents WebSocket authentication attempts when auth service is down
        """
        with patch.object(self.auth_client, 'health_check') as mock_health:
            # Test healthy auth service
            mock_health.return_value = {
                "status": "healthy",
                "response_time_ms": 45,
                "database_connected": True
            }
            
            health_result = await self.unified_auth_service.check_auth_service_availability()
            
            assert health_result["available"] is True
            assert health_result["response_time_ms"] < 1000
            assert health_result["database_connected"] is True
            
            # Test unhealthy auth service
            mock_health.return_value = {
                "status": "unhealthy",
                "response_time_ms": 5000,
                "database_connected": False
            }
            
            health_result = await self.unified_auth_service.check_auth_service_availability()
            
            assert health_result["available"] is False
            assert health_result["database_connected"] is False

    async def test_cross_service_token_exchange_and_propagation(self):
        """
        BVJ: Tests token exchange between services for WebSocket authentication
        Ensures tokens remain valid across service boundaries
        """
        # Mock token exchange scenario
        with patch.object(self.auth_client, 'exchange_token') as mock_exchange:
            mock_exchange.return_value = {
                "new_token": "exchanged-token-456",
                "expires_in": 1800,
                "scope": ["websocket_access", "chat_access"]
            }
            
            # Test token exchange
            exchange_result = await self.unified_auth_service.exchange_token(
                original_token=self.test_token,
                target_service="websocket-service",
                requested_scopes=["websocket_access", "chat_access"]
            )
            
            assert exchange_result["new_token"] is not None
            assert exchange_result["new_token"] != self.test_token
            assert "websocket_access" in exchange_result["scope"]
            assert "chat_access" in exchange_result["scope"]
            
            mock_exchange.assert_called_once_with(
                original_token=self.test_token,
                target_service="websocket-service",
                requested_scopes=["websocket_access", "chat_access"]
            )


@pytest.mark.integration  
@pytest.mark.asyncio
class TestAuthenticationContextSwitching(BaseIntegrationTest):
    """Test authentication context switching between REST API and WebSocket."""
    
    async def setup_method(self):
        await super().setup_method()
        self.unified_auth_service = UnifiedAuthenticationService()
        self.test_token = "test-token-context-switch"
        
    async def test_authentication_context_switching_rest_to_websocket(self):
        """
        BVJ: Tests seamless authentication transition from REST API to WebSocket
        Critical for maintaining user sessions when upgrading to WebSocket
        """
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock REST API authentication
            mock_client.validate_token.return_value = {
                "valid": True,
                "user_id": "user-123",
                "context": "rest_api",
                "permissions": ["api_access"]
            }
            
            # Test REST authentication
            rest_context = AuthenticationContext(
                token=self.test_token,
                user_id="user-123",
                method=AuthMethodType.JWT_BEARER,
                source="rest_api"
            )
            
            rest_result = await self.unified_auth_service.authenticate_user(rest_context)
            assert rest_result.success is True
            assert rest_result.source == "rest_api"
            
            # Mock WebSocket context switch
            mock_client.validate_token.return_value = {
                "valid": True,
                "user_id": "user-123", 
                "context": "websocket",
                "permissions": ["api_access", "websocket_access"]
            }
            
            # Test WebSocket authentication with same token
            ws_context = AuthenticationContext(
                token=self.test_token,
                user_id="user-123",
                method=AuthMethodType.JWT_BEARER,
                source="websocket_handshake"
            )
            
            ws_result = await self.unified_auth_service.authenticate_user(ws_context)
            assert ws_result.success is True
            assert ws_result.source == "websocket_handshake"
            assert "websocket_access" in ws_result.permissions
            
            # Verify context switching maintained user identity
            assert rest_result.user_id == ws_result.user_id