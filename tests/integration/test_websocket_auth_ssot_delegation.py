"""
WebSocket Authentication SSOT Delegation Integration Tests

MISSION CRITICAL: Integration tests that validate SSOT JWT validation delegation
in real WebSocket connection scenarios WITHOUT Docker dependencies.

SSOT INTEGRATION REQUIREMENTS:
1. WebSocket connections MUST use ONLY JWTHandler.validate_token() for JWT validation
2. NO integration-level fallback authentication paths
3. Real WebSocket connection behavior with SSOT delegation
4. Integration between WebSocket bridge and auth service

These tests are designed to FAIL initially, proving integration-level SSOT violations exist.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional
from fastapi import WebSocket
from fastapi.testclient import TestClient

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketAuthSSOTIntegration(SSotBaseTestCase):
    """
    Integration tests that validate SSOT delegation in WebSocket authentication flows.
    These tests should FAIL initially to prove integration-level violations exist.
    """

    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        self.valid_jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMH0.test_signature"
        self.expired_jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjE2MDAwMDAwMDAsImlhdCI6MTYwMDAwMDAwMH0.expired_signature"

    def test_integration_ssot_websocket_connection_delegates_to_jwt_handler(self):
        """
        TEST DESIGNED TO FAIL: Integration test for WebSocket connection SSOT delegation.
        
        This test should FAIL initially because:
        1. WebSocket connection may use multiple JWT validation layers
        2. Integration flow may bypass JWTHandler.validate_token()
        3. Connection establishment may use non-SSOT authentication paths
        
        Expected: FAILURE - Integration uses multiple JWT validation paths
        After Fix: PASS - Single SSOT JWTHandler delegation throughout
        """
        from netra_backend.app.websocket_core.user_context_extractor import extract_websocket_user_context
        
        # Create mock WebSocket connection
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_jwt_token}"}
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Mock SSOT JWTHandler to track delegation
        with patch('auth_service.auth_core.core.jwt_handler.JWTHandler') as mock_jwt_handler_class:
            mock_jwt_handler = Mock()
            mock_jwt_handler.validate_token.return_value = {
                'sub': 'test_user',
                'email': 'test@example.com',
                'exp': 9999999999,
                'iat': 1600000000,
                'permissions': ['execute_agents']
            }
            mock_jwt_handler_class.return_value = mock_jwt_handler
            
            # Mock intermediate auth services to detect non-SSOT usage
            auth_service_calls = []
            
            with patch('netra_backend.app.websocket_core.user_context_extractor.get_unified_auth') as mock_unified_auth:
                def track_unified_auth_call():
                    auth_service_calls.append('UnifiedAuthInterface')
                    mock_auth = Mock()
                    mock_auth.validate_token.return_value = {
                        'user_id': 'test_user',
                        'sub': 'test_user',
                        'email': 'test@example.com'
                    }
                    return mock_auth
                    
                mock_unified_auth.side_effect = track_unified_auth_call
                
                with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
                    async def track_auth_client_call(*args, **kwargs):
                        auth_service_calls.append('auth_client_core')
                        return {
                            'valid': True,
                            'payload': {'sub': 'test_user', 'email': 'test@example.com'},
                            'user_id': 'test_user',
                            'email': 'test@example.com'
                        }
                    
                    mock_auth_client.validate_token = track_auth_client_call
                    
                    # Execute integration flow
                    try:
                        user_context, auth_info = asyncio.run(
                            extract_websocket_user_context(mock_websocket)
                        )
                        integration_success = True
                    except Exception as e:
                        integration_success = False
                        self.logger.error(f"Integration flow failed: {e}")
                    
                    # INTEGRATION SSOT VIOLATIONS - These should FAIL initially
                    integration_violations = []
                    
                    # Violation 1: Check if intermediate auth services were used instead of direct JWTHandler
                    if 'UnifiedAuthInterface' in auth_service_calls:
                        integration_violations.append("integration uses UnifiedAuthInterface instead of direct JWTHandler")
                    
                    if 'auth_client_core' in auth_service_calls:
                        integration_violations.append("integration uses auth_client_core fallback path")
                    
                    # Violation 2: Check if JWTHandler was NOT called directly in integration
                    if not mock_jwt_handler.validate_token.called:
                        integration_violations.append("integration bypasses JWTHandler.validate_token() completely")
                    
                    # Violation 3: Check for multiple auth service usage (indicates non-SSOT)
                    if len(auth_service_calls) > 0:
                        integration_violations.append(f"integration uses multiple auth services: {auth_service_calls}")
                    
                    # ASSERTION: This should FAIL initially due to integration SSOT violations
                    self.assertEqual(
                        len(integration_violations), 0,
                        f"INTEGRATION SSOT VIOLATIONS: {integration_violations}. "
                        f"WebSocket integration must delegate ONLY to JWTHandler.validate_token()"
                    )

    def test_integration_ssot_websocket_auth_error_handling_consistency(self):
        """
        TEST DESIGNED TO FAIL: Integration test for consistent SSOT error handling.
        
        This test should FAIL initially because:
        1. Error handling may use different JWT validation paths
        2. Auth error scenarios may bypass SSOT validation
        3. Fallback error handling may create dual paths
        
        Expected: FAILURE - Inconsistent error handling with multiple JWT paths
        After Fix: PASS - Consistent SSOT error handling throughout
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        # Create mock WebSocket with expired token
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.expired_jwt_token}"}
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        
        # Track which JWT validation methods are used for error handling
        jwt_validation_calls = []
        
        # Mock SSOT JWTHandler to return validation error
        with patch('auth_service.auth_core.core.jwt_handler.JWTHandler') as mock_jwt_handler_class:
            def track_jwt_handler_call(*args, **kwargs):
                jwt_validation_calls.append('JWTHandler.validate_token')
                return None  # Simulate validation failure
                
            mock_jwt_handler = Mock()
            mock_jwt_handler.validate_token.side_effect = track_jwt_handler_call
            mock_jwt_handler_class.return_value = mock_jwt_handler
            
            # Mock intermediate services to detect fallback usage during error handling
            with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth_service:
                def track_auth_service_call():
                    jwt_validation_calls.append('UnifiedAuthService')
                    mock_service = Mock()
                    # Simulate auth service error
                    mock_result = Mock()
                    mock_result.success = False
                    mock_result.error = "Token validation failed"
                    mock_result.error_code = "VALIDATION_FAILED"
                    mock_service.authenticate_websocket = AsyncMock(return_value=(mock_result, None))
                    return mock_service
                    
                mock_auth_service.side_effect = track_auth_service_call
                
                # Execute integration error handling
                try:
                    result = asyncio.run(authenticate_websocket_ssot(mock_websocket))
                    error_handled = True
                except Exception as e:
                    error_handled = False
                    self.logger.error(f"Error handling integration failed: {e}")
                
                # ERROR HANDLING SSOT VIOLATIONS - These should FAIL initially
                error_handling_violations = []
                
                # Violation 1: Check if multiple JWT validation methods used during error handling
                unique_jwt_calls = set(jwt_validation_calls)
                if len(unique_jwt_calls) > 1:
                    error_handling_violations.append(f"error handling uses multiple JWT validation methods: {list(unique_jwt_calls)}")
                
                # Violation 2: Check if SSOT JWTHandler was bypassed during error handling
                if 'JWTHandler.validate_token' not in jwt_validation_calls:
                    error_handling_violations.append("error handling bypasses SSOT JWTHandler.validate_token()")
                
                # Violation 3: Check if intermediate services were used instead of SSOT
                if 'UnifiedAuthService' in jwt_validation_calls:
                    error_handling_violations.append("error handling uses UnifiedAuthService instead of direct JWTHandler")
                
                # ASSERTION: This should FAIL initially due to inconsistent error handling
                self.assertEqual(
                    len(error_handling_violations), 0,
                    f"ERROR HANDLING SSOT VIOLATIONS: {error_handling_violations}. "
                    f"Error handling must use consistent SSOT JWT validation"
                )

    def test_integration_ssot_websocket_auth_flow_end_to_end_delegation(self):
        """
        TEST DESIGNED TO FAIL: End-to-end integration test for SSOT delegation.
        
        This test should FAIL initially because:
        1. Full auth flow may use multiple JWT validation services
        2. E2E flow may have bypass mechanisms that violate SSOT
        3. Context creation may use non-SSOT JWT processing
        
        Expected: FAILURE - E2E flow uses multiple JWT validation paths
        After Fix: PASS - E2E flow uses only SSOT JWTHandler delegation
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator
        
        # Create WebSocket authenticator
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Create mock WebSocket
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_jwt_token}"}
        mock_websocket.client_state = Mock()  # Mock WebSocket state
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        
        # Track JWT validation calls throughout the entire flow
        end_to_end_jwt_calls = []
        
        # Mock SSOT JWTHandler
        with patch('auth_service.auth_core.core.jwt_handler.JWTHandler') as mock_jwt_handler_class:
            def track_end_to_end_jwt_call(*args, **kwargs):
                end_to_end_jwt_calls.append('JWTHandler')
                return {
                    'sub': 'test_user',
                    'email': 'test@example.com',
                    'exp': 9999999999,
                    'permissions': ['execute_agents']
                }
                
            mock_jwt_handler = Mock()
            mock_jwt_handler.validate_token.side_effect = track_end_to_end_jwt_call
            mock_jwt_handler_class.return_value = mock_jwt_handler
            
            # Mock all possible JWT validation services to detect usage
            with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth_service:
                def track_unified_auth_service():
                    end_to_end_jwt_calls.append('UnifiedAuthService')
                    mock_service = Mock()
                    mock_result = Mock()
                    mock_result.success = True
                    mock_result.user_id = 'test_user'
                    mock_result.email = 'test@example.com'
                    mock_result.permissions = ['execute_agents']
                    
                    from netra_backend.app.services.user_execution_context import UserExecutionContext
                    mock_context = Mock(spec=UserExecutionContext)
                    mock_context.user_id = 'test_user'
                    mock_context.websocket_client_id = 'ws_test_123'
                    
                    mock_service.authenticate_websocket = AsyncMock(return_value=(mock_result, mock_context))
                    return mock_service
                
                mock_auth_service.side_effect = track_unified_auth_service
                
                with patch('netra_backend.app.websocket_core.auth_remediation.authenticate_websocket_with_remediation') as mock_remediation:
                    def track_remediation_auth(*args, **kwargs):
                        end_to_end_jwt_calls.append('RemedationAuth')
                        return (True, Mock(), None)
                    
                    mock_remediation.side_effect = track_remediation_auth
                    
                    # Execute full end-to-end authentication flow
                    try:
                        result = asyncio.run(
                            authenticator.authenticate_websocket_connection(mock_websocket)
                        )
                        e2e_success = True
                    except Exception as e:
                        e2e_success = False
                        self.logger.error(f"E2E authentication flow failed: {e}")
                    
                    # END-TO-END SSOT VIOLATIONS - These should FAIL initially
                    e2e_violations = []
                    
                    # Violation 1: Check for multiple JWT validation services in E2E flow
                    unique_services = set(end_to_end_jwt_calls)
                    if len(unique_services) > 1:
                        e2e_violations.append(f"E2E flow uses multiple JWT services: {list(unique_services)}")
                    
                    # Violation 2: Check if SSOT JWTHandler was NOT used
                    if 'JWTHandler' not in end_to_end_jwt_calls:
                        e2e_violations.append("E2E flow bypasses SSOT JWTHandler completely")
                    
                    # Violation 3: Check if intermediate services were used instead of SSOT
                    non_ssot_services = [s for s in end_to_end_jwt_calls if s != 'JWTHandler']
                    if non_ssot_services:
                        e2e_violations.append(f"E2E flow uses non-SSOT services: {non_ssot_services}")
                    
                    # Violation 4: Check if remediation auth was used (indicates dual paths)
                    if 'RemedationAuth' in end_to_end_jwt_calls:
                        e2e_violations.append("E2E flow uses remediation auth instead of SSOT")
                    
                    # ASSERTION: This should FAIL initially due to E2E SSOT violations
                    self.assertEqual(
                        len(e2e_violations), 0,
                        f"END-TO-END SSOT VIOLATIONS: {e2e_violations}. "
                        f"Complete E2E flow must use ONLY JWTHandler.validate_token()"
                    )

    def test_integration_ssot_websocket_context_creation_uses_ssot_validation(self):
        """
        TEST DESIGNED TO FAIL: Integration test for SSOT validation in context creation.
        
        This test should FAIL initially because:
        1. UserExecutionContext creation may use non-SSOT JWT processing
        2. Context creation may have embedded JWT validation logic
        3. Context metadata may be populated via non-SSOT JWT decoding
        
        Expected: FAILURE - Context creation uses non-SSOT JWT processing
        After Fix: PASS - Context creation relies only on SSOT validation results
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        extractor = UserContextExtractor()
        
        # Mock WebSocket
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_jwt_token}"}
        
        # Track JWT processing during context creation
        context_creation_jwt_calls = []
        
        # Mock JWT library to detect direct usage during context creation
        with patch('jwt.decode') as mock_jwt_decode:
            def track_direct_jwt_decode(*args, **kwargs):
                context_creation_jwt_calls.append('direct_jwt_decode')
                return {
                    'sub': 'test_user',
                    'email': 'test@example.com',
                    'exp': 9999999999,
                    'iat': 1600000000
                }
                
            mock_jwt_decode.side_effect = track_direct_jwt_decode
            
            # Mock SSOT JWTHandler
            with patch('auth_service.auth_core.core.jwt_handler.JWTHandler') as mock_jwt_handler_class:
                def track_ssot_jwt_call(*args, **kwargs):
                    context_creation_jwt_calls.append('JWTHandler_validate_token')
                    return {
                        'sub': 'test_user',
                        'email': 'test@example.com',
                        'exp': 9999999999,
                        'iat': 1600000000,
                        'permissions': ['execute_agents']
                    }
                
                mock_jwt_handler = Mock()
                mock_jwt_handler.validate_token.side_effect = track_ssot_jwt_call
                mock_jwt_handler_class.return_value = mock_jwt_handler
                
                # Mock UnifiedAuthInterface to track usage
                with patch('netra_backend.app.websocket_core.user_context_extractor.get_unified_auth') as mock_unified_auth:
                    def track_unified_auth():
                        context_creation_jwt_calls.append('UnifiedAuthInterface')
                        mock_auth = Mock()
                        mock_auth.validate_token.return_value = {
                            'user_id': 'test_user',
                            'sub': 'test_user',
                            'email': 'test@example.com'
                        }
                        return mock_auth
                    
                    mock_unified_auth.side_effect = track_unified_auth
                    
                    # Execute context creation integration
                    try:
                        user_context, auth_info = asyncio.run(
                            extractor.extract_user_context_from_websocket(mock_websocket)
                        )
                        context_creation_success = True
                    except Exception as e:
                        context_creation_success = False
                        self.logger.error(f"Context creation integration failed: {e}")
                    
                    # CONTEXT CREATION SSOT VIOLATIONS - These should FAIL initially  
                    context_violations = []
                    
                    # Violation 1: Check for direct jwt.decode usage during context creation
                    if 'direct_jwt_decode' in context_creation_jwt_calls:
                        context_violations.append("context creation uses direct jwt.decode() bypassing SSOT")
                    
                    # Violation 2: Check if SSOT JWTHandler was NOT used for context creation
                    if 'JWTHandler_validate_token' not in context_creation_jwt_calls:
                        context_violations.append("context creation bypasses SSOT JWTHandler.validate_token()")
                    
                    # Violation 3: Check for intermediate service usage during context creation
                    if 'UnifiedAuthInterface' in context_creation_jwt_calls:
                        context_violations.append("context creation uses UnifiedAuthInterface instead of direct SSOT")
                    
                    # Violation 4: Check for multiple JWT processing methods during context creation
                    jwt_methods = set(context_creation_jwt_calls)
                    if len(jwt_methods) > 1:
                        context_violations.append(f"context creation uses multiple JWT methods: {list(jwt_methods)}")
                    
                    # ASSERTION: This should FAIL initially due to context creation SSOT violations
                    self.assertEqual(
                        len(context_violations), 0,
                        f"CONTEXT CREATION SSOT VIOLATIONS: {context_violations}. "
                        f"UserExecutionContext creation must rely only on SSOT validation results"
                    )

    def tearDown(self):
        """Clean up integration test environment."""
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])