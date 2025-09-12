"""
WebSocket Bridge SSOT Consolidation Validation Tests

MISSION CRITICAL: Validate that WebSocket bridge components delegate ALL JWT validation
to the SSOT auth_service/auth_core/core/jwt_handler.py:JWTHandler.validate_token()

SSOT DELEGATION REQUIREMENTS:
1. NO direct jwt.decode() calls in WebSocket bridge code
2. ALL JWT validation delegates to JWTHandler.validate_token()
3. NO local JWT secret access or configuration
4. NO fallback validation methods

These tests are designed to FAIL initially, proving SSOT violations exist.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, call
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketBridgeSSOTDelegation(SSotBaseTestCase):
    """
    Tests that validate proper SSOT delegation in WebSocket bridge components.
    These tests should FAIL initially to prove delegation violations exist.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.valid_jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMH0.test_signature"
        self.invalid_jwt_token = "invalid.jwt.token"

    def test_ssot_delegation_user_context_extractor_calls_jwt_handler(self):
        """
        TEST DESIGNED TO FAIL: Verify UserContextExtractor delegates to JWTHandler.validate_token().
        
        This test should FAIL initially because UserContextExtractor may:
        1. Use conditional auth service access (dual paths)
        2. Have fallback validation methods
        3. Not directly call JWTHandler.validate_token()
        
        Expected: FAILURE - Delegation not properly configured
        After Fix: PASS - Direct delegation to SSOT JWTHandler
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        extractor = UserContextExtractor()
        mock_websocket = Mock()
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_jwt_token}"}
        
        # Mock the SSOT JWTHandler to verify it's called
        with patch('auth_service.auth_core.core.jwt_handler.JWTHandler') as mock_jwt_handler_class:
            mock_jwt_handler = Mock()
            mock_jwt_handler.validate_token.return_value = {
                'sub': 'test_user',
                'email': 'test@example.com', 
                'exp': 9999999999
            }
            mock_jwt_handler_class.return_value = mock_jwt_handler
            
            # Also mock UnifiedAuthInterface to track if it's used instead of direct JWTHandler
            with patch('netra_backend.app.websocket_core.user_context_extractor.get_unified_auth') as mock_get_unified_auth:
                mock_unified_auth = Mock()
                mock_unified_auth.validate_token.return_value = {
                    'user_id': 'test_user',
                    'sub': 'test_user', 
                    'email': 'test@example.com'
                }
                mock_get_unified_auth.return_value = mock_unified_auth
                
                # Execute validation
                try:
                    result = asyncio.run(extractor.validate_and_decode_jwt(self.valid_jwt_token))
                except Exception as e:
                    self.fail(f"Validation failed with exception: {e}")
                
                # SSOT DELEGATION CHECKS - These should FAIL initially
                delegation_violations = []
                
                # Violation 1: Check if UnifiedAuthInterface was used instead of direct JWTHandler
                if mock_get_unified_auth.called or mock_unified_auth.validate_token.called:
                    delegation_violations.append("uses UnifiedAuthInterface instead of direct JWTHandler delegation")
                
                # Violation 2: Check if JWTHandler.validate_token was NOT called directly
                if not mock_jwt_handler.validate_token.called:
                    delegation_violations.append("does not call JWTHandler.validate_token() directly")
                
                # ASSERTION: This should FAIL initially due to improper delegation
                self.assertEqual(
                    len(delegation_violations), 0,
                    f"SSOT DELEGATION VIOLATIONS in UserContextExtractor: {delegation_violations}. "
                    f"Must call JWTHandler.validate_token() directly, not through intermediary services"
                )

    def test_ssot_delegation_no_fallback_validation_paths(self):
        """
        TEST DESIGNED TO FAIL: Ensure no fallback validation paths exist.
        
        This test should FAIL initially because the code may have:
        1. Try/except blocks with fallback validation
        2. Conditional imports leading to dual paths
        3. Auth client fallback when UnifiedAuth fails
        
        Expected: FAILURE - Fallback paths detected
        After Fix: PASS - Single delegation path only
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        extractor = UserContextExtractor()
        
        # Mock UnifiedAuthInterface to return None (force fallback)
        with patch('netra_backend.app.websocket_core.user_context_extractor.get_unified_auth', return_value=None):
            # Mock auth_client_core as fallback 
            with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
                mock_auth_client.validate_token = AsyncMock(return_value={
                    'valid': True,
                    'payload': {'sub': 'test_user', 'email': 'test@example.com'},
                    'user_id': 'test_user',
                    'email': 'test@example.com'
                })
                
                # Execute validation - this should expose fallback path usage
                try:
                    result = asyncio.run(extractor.validate_and_decode_jwt(self.valid_jwt_token))
                except Exception as e:
                    result = None
                
                # SSOT VIOLATION CHECKS - These should FAIL initially
                fallback_violations = []
                
                # Violation 1: Check if auth_client fallback was used
                if mock_auth_client.validate_token.called:
                    fallback_violations.append("auth_client_core fallback validation path activated")
                
                # Violation 2: Check if result was produced via fallback (indicates dual path)
                if result is not None:
                    source = result.get('source') if isinstance(result, dict) else None
                    if source == 'auth_service_fallback':
                        fallback_violations.append("result produced via auth_service_fallback path")
                
                # ASSERTION: This should FAIL initially due to fallback paths
                self.assertEqual(
                    len(fallback_violations), 0,
                    f"FALLBACK PATH VIOLATIONS detected: {fallback_violations}. "
                    f"SSOT architecture requires single delegation path with no fallbacks"
                )

    def test_ssot_delegation_websocket_auth_uses_single_path(self):
        """
        TEST DESIGNED TO FAIL: Verify UnifiedWebSocketAuth uses single SSOT path.
        
        This test should FAIL initially because UnifiedWebSocketAuth may:
        1. Use remediation authentication as primary path
        2. Have legacy SSOT authentication as fallback
        3. Use demo mode or E2E bypasses that create multiple paths
        
        Expected: FAILURE - Multiple authentication paths detected
        After Fix: PASS - Single SSOT delegation path only
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        mock_websocket = Mock()
        mock_websocket.headers = {"sec-websocket-protocol": f"jwt.{self.valid_jwt_token}"}
        
        # Mock remediation authentication to track if it's used
        with patch('netra_backend.app.websocket_core.auth_remediation.authenticate_websocket_with_remediation') as mock_remediation:
            mock_remediation.return_value = (True, Mock(), None)
            
            # Mock SSOT authenticator to track if it's used
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_websocket_authenticator') as mock_get_authenticator:
                mock_authenticator = Mock()
                mock_auth_result = Mock()
                mock_auth_result.success = True
                mock_authenticator.authenticate_websocket_connection.return_value = mock_auth_result
                mock_get_authenticator.return_value = mock_authenticator
                
                # Execute authentication
                try:
                    result = asyncio.run(authenticate_websocket_ssot(mock_websocket))
                except Exception as e:
                    result = None
                
                # SSOT PATH VIOLATIONS - These should FAIL initially
                multiple_path_violations = []
                
                # Violation 1: Check if remediation path was used
                if mock_remediation.called:
                    multiple_path_violations.append("remediation authentication path used instead of SSOT")
                
                # Violation 2: Check if SSOT authenticator was used as fallback (indicates dual paths)
                if mock_get_authenticator.called:
                    multiple_path_violations.append("SSOT authenticator used as fallback indicates multiple paths")
                
                # ASSERTION: This should FAIL initially due to multiple paths
                self.assertEqual(
                    len(multiple_path_violations), 0,
                    f"MULTIPLE PATH VIOLATIONS in WebSocket auth: {multiple_path_violations}. "
                    f"Must use single SSOT delegation path only"
                )

    def test_ssot_delegation_no_direct_jwt_secret_access(self):
        """
        TEST DESIGNED TO FAIL: Ensure WebSocket code doesn't access JWT secrets directly.
        
        This test should FAIL initially because WebSocket code may:
        1. Import JWT secrets from environment
        2. Access JWT configuration directly
        3. Perform local JWT operations instead of delegating
        
        Expected: FAILURE - Direct JWT secret access detected
        After Fix: PASS - All JWT operations delegated to SSOT
        """
        import os
        import inspect
        from pathlib import Path
        
        # Files to check for direct JWT secret access
        websocket_files = [
            "netra_backend/app/websocket_core/user_context_extractor.py",
            "netra_backend/app/websocket_core/unified_websocket_auth.py"
        ]
        
        jwt_secret_violations = []
        
        for file_path in websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for JWT secret access patterns
                secret_access_patterns = [
                    "JWT_SECRET",
                    "AuthConfig.get_jwt_secret",
                    "os.environ.get('JWT_SECRET')",
                    "get_env().get('JWT_SECRET')",
                    "jwt_secret",
                    "self.secret"
                ]
                
                for pattern in secret_access_patterns:
                    if pattern in content:
                        # Find the line number for better reporting
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if pattern in line and not line.strip().startswith('#'):
                                jwt_secret_violations.append(f"{file_path}:{i} - {pattern}")
                                
            except Exception as e:
                self.logger.warning(f"Could not check {file_path}: {e}")
        
        # ASSERTION: This should FAIL initially due to direct secret access
        self.assertEqual(
            len(jwt_secret_violations), 0,
            f"DIRECT JWT SECRET ACCESS VIOLATIONS: {jwt_secret_violations}. "
            f"WebSocket components must delegate ALL JWT operations to SSOT JWTHandler"
        )

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])