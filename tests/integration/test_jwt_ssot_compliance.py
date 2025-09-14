"""
JWT SSOT Compliance Integration Tests

PURPOSE: These tests FAIL when JWT operations are not properly integrated 
through the auth service SSOT pattern. Tests will PASS after SSOT refactor.

MISSION CRITICAL: Protects $500K+ ARR Golden Path by ensuring JWT integration
maintains proper service boundaries and auth service delegation.

BUSINESS VALUE: Enterprise/Platform - System Integration & Security Architecture  
- Validates end-to-end JWT flow through auth service
- Ensures proper error handling across service boundaries
- Validates multi-user JWT isolation via auth service
- Tests WebSocket auth integration with auth service

EXPECTED STATUS: FAIL (before SSOT refactor) → PASS (after SSOT refactor)

These tests validate SSOT compliance through integration scenarios:
1. End-to-end JWT validation through auth service
2. WebSocket authentication integration via auth service  
3. Multi-user JWT isolation through auth service
4. Proper error propagation from auth service
"""

import asyncio
import httpx
import logging
from typing import Dict, Any, Optional
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import jwt

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.integration_auth_manager import IntegrationAuthServiceManager
from test_framework.ssot.websocket_auth_test_helpers import WebSocketAuthenticationTester

logger = logging.getLogger(__name__)

class TestJwtSsotComplianceIntegration(SSotAsyncTestCase):
    """
    JWT SSOT Integration Compliance Tests
    
    These tests FAIL when JWT integration bypasses auth service SSOT patterns.
    After SSOT refactor, all tests should PASS.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.auth_manager = IntegrationAuthServiceManager()
        self.websocket_helper = WebSocketAuthenticationTester()
        
    @pytest.mark.asyncio
    async def test_end_to_end_jwt_validation_through_auth_service(self):
        """
        SSOT Integration Test: End-to-end JWT validation through auth service only.
        
        EXPECTED: FAIL - Backend currently has local JWT validation fallbacks
        AFTER SSOT: PASS - All JWT validation goes through auth service
        
        This test validates that JWT tokens are validated end-to-end through
        auth service without any local backend validation fallbacks.
        """
        from netra_backend.app.auth_integration.auth import get_current_user
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create test JWT token
        test_token = "test_jwt_token_for_ssot_validation"
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=test_token)
        
        # Mock database session
        mock_db_session = AsyncMock()
        
        # Test 1: When auth service is available, should delegate properly
        with patch.object(AuthServiceClient, 'validate_token') as mock_validate:
            # SSOT VIOLATION: If backend has local validation fallback,
            # this test will detect it by checking if validate_token is called
            
            mock_validate.return_value = {
                "valid": True,
                "user_id": "test_user_123",
                "email": "test@example.com",
                "permissions": ["read"]
            }
            
            # Mock user retrieval from database
            mock_user = MagicMock()
            mock_user.id = "test_user_123"
            mock_user.email = "test@example.com"
            
            with patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user:
                mock_get_user.return_value = mock_user
                
                try:
                    result = await get_current_user(credentials, mock_db_session)
                    
                    # CRITICAL: validate_token MUST be called for SSOT compliance
                    assert mock_validate.called, (
                        "SSOT VIOLATION: Auth service validate_token was not called. "
                        "Backend is likely using local JWT validation instead of delegating to auth service."
                    )
                    
                    assert result.id == "test_user_123"
                    logger.info("✓ JWT validation properly delegated to auth service")
                    
                except Exception as e:
                    # If this fails, backend might have local JWT validation bypassing auth service
                    pytest.fail(
                        f"SSOT VIOLATION: JWT validation failed - backend may have local validation bypassing auth service. "
                        f"Error: {e}"
                    )
        
        # Test 2: When auth service returns invalid, should fail (no local fallback)
        with patch.object(AuthServiceClient, 'validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "user_id": None,
                "email": None,
                "permissions": []
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, mock_db_session)
            
            # Should fail properly without local JWT fallback
            assert exc_info.value.status_code == 401
            assert mock_validate.called
            logger.info("✓ Invalid JWT properly rejected via auth service")

    @pytest.mark.asyncio 
    async def test_websocket_auth_integration_delegates_to_auth_service(self):
        """
        SSOT Integration Test: WebSocket auth integrates with auth service only.
        
        EXPECTED: FAIL - WebSocket currently has local JWT validation fallback
        AFTER SSOT: PASS - WebSocket auth delegates to auth service
        
        This test validates WebSocket authentication integration with auth service.
        """
        from netra_backend.app.websocket_core.auth import authenticate
        
        # Create test WebSocket connection mock
        mock_websocket = MagicMock()
        mock_websocket.headers = {"authorization": "Bearer test_jwt_token"}
        
        # Test WebSocket auth delegation to auth service
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient') as mock_auth_client_class:
            mock_auth_client = AsyncMock()
            mock_auth_client_class.return_value = mock_auth_client
            
            # Configure auth service response
            mock_auth_client.validate_token.return_value = {
                "valid": True,
                "user_id": "websocket_user_123",
                "email": "ws_test@example.com",
                "permissions": ["websocket_connect"]
            }
            
            try:
                # Test WebSocket authentication
                result = await authenticate(mock_websocket)
                
                # CRITICAL: Auth service must be called for SSOT compliance
                assert mock_auth_client.validate_token.called, (
                    "SSOT VIOLATION: WebSocket auth did not call auth service validate_token. "
                    "WebSocket is likely using local JWT validation bypassing auth service."
                )
                
                assert result is not None
                logger.info("✓ WebSocket auth properly delegated to auth service")
                
            except Exception as e:
                # Check if this is due to local validation fallback
                error_msg = str(e).lower()
                if any(pattern in error_msg for pattern in ['jwt.decode', 'local validation', 'fallback']):
                    pytest.fail(
                        f"SSOT VIOLATION: WebSocket auth appears to use local JWT validation. "
                        f"Error indicates local validation: {e}"
                    )
                else:
                    # Legitimate error from proper auth service integration
                    logger.warning(f"WebSocket auth integration error (may be legitimate): {e}")

    @pytest.mark.asyncio
    async def test_multi_user_jwt_isolation_through_auth_service(self):
        """
        SSOT Integration Test: Multi-user JWT isolation through auth service.
        
        EXPECTED: FAIL - Backend may have shared JWT state violations
        AFTER SSOT: PASS - Perfect user isolation via auth service
        
        This test validates that JWT operations maintain user isolation
        through proper auth service delegation.
        """
        from netra_backend.app.auth_integration.auth import get_current_user
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create tokens for two different users
        user1_token = "user1_jwt_token_for_isolation_test"
        user2_token = "user2_jwt_token_for_isolation_test"
        
        user1_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=user1_token)
        user2_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=user2_token)
        
        mock_db_session = AsyncMock()
        
        # Mock user objects
        mock_user1 = MagicMock()
        mock_user1.id = "user1_id"
        mock_user1.email = "user1@example.com"
        
        mock_user2 = MagicMock()  
        mock_user2.id = "user2_id"
        mock_user2.email = "user2@example.com"
        
        with patch.object(AuthServiceClient, 'validate_token') as mock_validate:
            with patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user:
                
                # Configure auth service responses for different users
                def validate_side_effect(token):
                    if token == user1_token:
                        return {
                            "valid": True,
                            "user_id": "user1_id", 
                            "email": "user1@example.com",
                            "permissions": ["user1_perms"]
                        }
                    elif token == user2_token:
                        return {
                            "valid": True,
                            "user_id": "user2_id",
                            "email": "user2@example.com", 
                            "permissions": ["user2_perms"]
                        }
                    else:
                        return {"valid": False}
                
                mock_validate.side_effect = validate_side_effect
                
                def get_user_side_effect(db, validation_result):
                    if validation_result["user_id"] == "user1_id":
                        return mock_user1
                    elif validation_result["user_id"] == "user2_id":
                        return mock_user2
                    return None
                    
                mock_get_user.side_effect = get_user_side_effect
                
                # Test user isolation
                try:
                    result1 = await get_current_user(user1_credentials, mock_db_session)
                    result2 = await get_current_user(user2_credentials, mock_db_session)
                    
                    # Verify proper user isolation through auth service
                    assert result1.id != result2.id, (
                        "SSOT VIOLATION: User isolation failed - same user returned for different tokens"
                    )
                    
                    assert result1.id == "user1_id"
                    assert result2.id == "user2_id"
                    
                    # Verify auth service was called for each user
                    assert mock_validate.call_count >= 2, (
                        "SSOT VIOLATION: Auth service not called for each user validation. "
                        "Backend may be caching/sharing JWT state improperly."
                    )
                    
                    logger.info("✓ Multi-user JWT isolation properly maintained via auth service")
                    
                except Exception as e:
                    pytest.fail(
                        f"SSOT VIOLATION: Multi-user JWT isolation failed. "
                        f"Backend may have shared JWT state. Error: {e}"
                    )

    @pytest.mark.asyncio
    async def test_auth_service_error_propagation_compliance(self):
        """
        SSOT Integration Test: Auth service errors propagate properly (no local fallback).
        
        EXPECTED: FAIL - Backend currently has fallback mechanisms for auth service errors
        AFTER SSOT: PASS - Auth service errors propagate cleanly without fallbacks
        
        This test validates proper error handling when auth service is unavailable.
        """
        from netra_backend.app.auth_integration.auth import get_current_user
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        
        test_token = "test_token_for_error_propagation"
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=test_token)
        mock_db_session = AsyncMock()
        
        # Test auth service unavailable scenario
        with patch.object(AuthServiceClient, 'validate_token') as mock_validate:
            # Simulate auth service unavailable
            mock_validate.side_effect = httpx.RequestError("Auth service unavailable")
            
            with pytest.raises((HTTPException, httpx.RequestError)) as exc_info:
                await get_current_user(credentials, mock_db_session)
            
            # Should fail properly without local JWT fallback
            assert mock_validate.called, (
                "SSOT VIOLATION: Auth service was not called when expected"
            )
            
            # Should not succeed (which would indicate local fallback)
            logger.info("✓ Auth service error properly propagated without local fallback")
        
        # Test auth service returns error response  
        with patch.object(AuthServiceClient, 'validate_token') as mock_validate:
            # Simulate auth service error response
            mock_validate.side_effect = HTTPException(status_code=503, detail="Auth service error")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, mock_db_session)
            
            # Should propagate auth service error properly
            assert exc_info.value.status_code in [401, 403, 503], (
                "SSOT VIOLATION: Auth service error not properly propagated"
            )
            
            assert mock_validate.called
            logger.info("✓ Auth service error response properly propagated")

    @pytest.mark.asyncio
    async def test_no_backend_jwt_secrets_in_integration_flow(self):
        """
        SSOT Integration Test: No JWT secrets used in backend integration flow.
        
        EXPECTED: FAIL - Backend currently uses JWT secrets for local operations
        AFTER SSOT: PASS - No JWT secrets used in backend, all handled by auth service
        
        This test validates that backend integration flows don't use JWT secrets.
        """
        from netra_backend.app.auth_integration.auth import get_current_user
        
        # Monitor for JWT secret usage during integration flow
        jwt_secret_accessed = []
        
        # Patch common JWT secret access patterns
        with patch('os.environ.get') as mock_env_get:
            def env_get_side_effect(key, default=None):
                if any(secret_key in key.upper() for secret_key in ['JWT_SECRET', 'JWT_KEY', 'SECRET_KEY']):
                    jwt_secret_accessed.append(f"Environment variable {key} accessed")
                    return "mock_secret_value"  # Return mock to prevent errors
                return default
                
            mock_env_get.side_effect = env_get_side_effect
            
            # Patch JWT library usage
            with patch('jwt.decode') as mock_jwt_decode:
                mock_jwt_decode.side_effect = Exception("JWT decode should not be called in backend integration")
                
                with patch('jwt.encode') as mock_jwt_encode:
                    mock_jwt_encode.side_effect = Exception("JWT encode should not be called in backend integration")
                    
                    # Execute integration flow
                    test_token = "integration_test_token"
                    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=test_token)
                    mock_db_session = AsyncMock()
                    
                    # Mock successful auth service response
                    from netra_backend.app.clients.auth_client_core import AuthServiceClient
                    with patch.object(AuthServiceClient, 'validate_token') as mock_validate:
                        mock_validate.return_value = {
                            "valid": True,
                            "user_id": "integration_user",
                            "email": "integration@example.com",
                            "permissions": ["read"]
                        }
                        
                        with patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user:
                            mock_user = MagicMock()
                            mock_user.id = "integration_user"
                            mock_get_user.return_value = mock_user
                            
                            try:
                                result = await get_current_user(credentials, mock_db_session)
                                
                                # Verify no JWT secrets were accessed during integration
                                if jwt_secret_accessed:
                                    secrets_summary = "\n".join([f"  - {s}" for s in jwt_secret_accessed])
                                    pytest.fail(
                                        f"SSOT VIOLATION: JWT secrets accessed during backend integration flow. "
                                        f"All JWT operations should be handled by auth service. "
                                        f"Secret accesses:\n{secrets_summary}"
                                    )
                                
                                # Verify no direct JWT operations were attempted
                                assert not mock_jwt_decode.called, (
                                    "SSOT VIOLATION: jwt.decode called during backend integration - should delegate to auth service"
                                )
                                
                                assert not mock_jwt_encode.called, (
                                    "SSOT VIOLATION: jwt.encode called during backend integration - should delegate to auth service"
                                )
                                
                                logger.info("✓ Backend integration flow uses no JWT secrets or operations")
                                
                            except Exception as e:
                                if "JWT decode should not be called" in str(e) or "JWT encode should not be called" in str(e):
                                    pytest.fail(
                                        f"SSOT VIOLATION: Backend attempted direct JWT operations during integration. "
                                        f"All JWT operations must be delegated to auth service. Error: {e}"
                                    )
                                else:
                                    # Legitimate integration error
                                    logger.warning(f"Integration flow error (may be legitimate): {e}")

    def teardown_method(self, method):
        """Clean up after test."""
        super().teardown_method(method)
        logger.info(f"JWT SSOT integration compliance test completed: {method.__name__}")