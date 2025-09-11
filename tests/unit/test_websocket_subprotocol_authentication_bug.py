"""
WebSocket Subprotocol Authentication Bug Reproduction Test Suite

ISSUE #342: Configuration mismatch causing "No subprotocols supported" error

This test suite reproduces the exact conditions described in Issue #342:
- Frontend sends JWT tokens via WebSocket subprotocol headers  
- Backend expects different subprotocol format
- Configuration mismatch causes authentication failures

PRIORITY: PRIMARY - This test should FAIL initially to demonstrate the bug
"""

import pytest
import json
import asyncio
import unittest
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# SSOT imports from registry
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_jwt_protocol_handler import (
    negotiate_websocket_subprotocol,
    extract_jwt_from_subprotocol,
    UnifiedJWTProtocolHandler
)
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    authenticate_websocket_ssot
)

class TestWebSocketSubprotocolAuthenticationBug(SSotAsyncTestCase):
    """
    Test suite to reproduce WebSocket subprotocol authentication bug.
    
    These tests should initially FAIL to demonstrate Issue #342.
    After remediation, they should pass.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.authenticator = UnifiedWebSocketAuthenticator()

    def create_mock_websocket(
        self, 
        subprotocol_header: Optional[str] = None,
        authorization_header: Optional[str] = None,
        **kwargs
    ) -> Mock:
        """Create mock WebSocket with specific headers."""
        websocket = Mock()
        headers = {}
        
        if subprotocol_header:
            headers["sec-websocket-protocol"] = subprotocol_header
            
        if authorization_header:
            headers["authorization"] = authorization_header
            
        websocket.headers = headers
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        websocket.client.port = 8000
        websocket.client_state = Mock()
        websocket.client_state.name = "CONNECTED"  # Mock enum value
        
        # Add any additional mock attributes
        for key, value in kwargs.items():
            setattr(websocket, key, value)
            
        return websocket

    def test_reproduce_no_subprotocols_supported_error(self):
        """
        PRIMARY TEST: Reproduce "No subprotocols supported" error.
        
        This test should FAIL initially to demonstrate Issue #342.
        
        The bug occurs when:
        1. Frontend sends JWT via "sec-websocket-protocol: jwt.TOKEN" 
        2. Backend doesn't properly handle this format
        3. Subprotocol negotiation fails with "No subprotocols supported"
        """
        # Simulate frontend behavior - sending JWT token via subprotocol
        frontend_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        # Frontend format: "jwt." + base64url_encoded(token)
        import base64
        encoded_token = base64.urlsafe_b64encode(frontend_jwt_token.encode()).decode().rstrip('=')
        frontend_subprotocol = f"jwt.{encoded_token}"
        
        # Test 1: Frontend sends subprotocol with JWT
        client_protocols = [frontend_subprotocol, "chat", "protocol1"]
        
        # THIS SHOULD FAIL - demonstrating the bug
        accepted_protocol = negotiate_websocket_subprotocol(client_protocols)
        
        # BUG ASSERTION: This will fail because backend doesn't support frontend format
        self.assertIsNotNone(
            accepted_protocol, 
            "BUG REPRODUCTION FAILED: Expected subprotocol negotiation to succeed with frontend JWT format"
        )
        
        # Test 2: Try to extract JWT from subprotocol header
        mock_websocket = self.create_mock_websocket(
            subprotocol_header=",".join(client_protocols)
        )
        
        extracted_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket)
        
        # BUG ASSERTION: This will fail because JWT extraction doesn't handle frontend format
        self.assertIsNotNone(
            extracted_token,
            "BUG REPRODUCTION FAILED: Expected JWT extraction from frontend subprotocol format to succeed"
        )
        
        self.assertEqual(
            extracted_token,
            frontend_jwt_token,
            "BUG REPRODUCTION FAILED: Extracted token should match original frontend JWT"
        )

    def test_correct_subprotocol_format_works(self):
        """
        CONTROL TEST: Verify that correct subprotocol format works.
        
        This test should PASS to show what currently works.
        """
        # Test with authorization header (this should work)
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        mock_websocket = self.create_mock_websocket(
            authorization_header=f"Bearer {jwt_token}"
        )
        
        extracted_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket)
        
        self.assertIsNotNone(extracted_token, "Authorization header JWT extraction should work")
        self.assertEqual(extracted_token, jwt_token, "Extracted token should match original")

    def test_subprotocol_format_variations(self):
        """
        Test various subprotocol format variations that might cause issues.
        
        This test explores the configuration mismatch by testing different formats.
        """
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        # Test different format variations
        test_cases = [
            # Format, Description
            (f"jwt.{jwt_token}", "Direct JWT format"),
            (f"jwt-auth.{jwt_token}", "JWT auth format (Issue #342 fix)"),
            (f"bearer.{jwt_token}", "Bearer format (Issue #342 fix)"),
        ]
        
        failed_formats = []
        
        for subprotocol_format, description in test_cases:
            mock_websocket = self.create_mock_websocket(
                subprotocol_header=subprotocol_format
            )
            
            try:
                extracted_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket)
                if extracted_token != jwt_token:
                    failed_formats.append((subprotocol_format, description, f"Token mismatch: got {extracted_token}"))
            except Exception as e:
                failed_formats.append((subprotocol_format, description, f"Exception: {e}"))
        
        if failed_formats:
            failure_details = "\n".join([f"  - {desc} ({fmt}): {error}" for fmt, desc, error in failed_formats])
            raise AssertionError(f"Configuration mismatch detected in {len(failed_formats)}/{len(test_cases)} formats:\n{failure_details}")

    def test_multiple_subprotocols_with_jwt(self):
        """
        Test handling of multiple subprotocols where one contains JWT.
        
        This simulates real client behavior where multiple protocols are requested.
        """
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        # Frontend sends multiple protocols
        import base64
        encoded_token = base64.urlsafe_b64encode(jwt_token.encode()).decode().rstrip('=')
        
        subprotocol_header = f"chat, jwt.{encoded_token}, protocol1"
        
        mock_websocket = self.create_mock_websocket(
            subprotocol_header=subprotocol_header
        )
        
        # Test subprotocol negotiation
        client_protocols = [p.strip() for p in subprotocol_header.split(",")]
        accepted_protocol = negotiate_websocket_subprotocol(client_protocols)
        
        self.assertIsNotNone(
            accepted_protocol,
            "Should accept at least one subprotocol when JWT is present"
        )
        
        # Test JWT extraction
        extracted_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket)
        
        self.assertIsNotNone(
            extracted_token,
            "Should extract JWT from multiple subprotocols"
        )

    async def test_authentication_with_subprotocol_jwt(self):
        """
        Test complete authentication flow using subprotocol JWT.
        
        This tests the end-to-end flow that's failing in Issue #342.
        """
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        # Frontend format
        import base64
        encoded_token = base64.urlsafe_b64encode(jwt_token.encode()).decode().rstrip('=')
        subprotocol_header = f"jwt.{encoded_token}"
        
        mock_websocket = self.create_mock_websocket(
            subprotocol_header=subprotocol_header
        )
        
        # Mock the authentication service to return success for this test token
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth_service:
            mock_auth = AsyncMock()
            mock_auth.authenticate_websocket = AsyncMock()
            
            # Mock successful auth response
            from netra_backend.app.services.unified_authentication_service import AuthResult
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            auth_result = AuthResult(
                success=True,
                user_id="1234567890",  # Use the same user ID from the JWT token
                email="test@example.com",
                permissions=["read", "write"]
            )
            
            user_context = UserExecutionContext(
                user_id="1234567890",  # Use the same user ID from the JWT token
                thread_id="thread-123",
                run_id="run-123",
                request_id="req-123",
                websocket_client_id="ws-client-123"
            )
            
            mock_auth.authenticate_websocket.return_value = (auth_result, user_context)
            mock_auth_service.return_value = mock_auth
            
            # Test authentication
            result = await authenticate_websocket_ssot(mock_websocket)
            
            # This should succeed if subprotocol handling is fixed
            self.assertTrue(
                result.success,
                f"Authentication should succeed with subprotocol JWT. Error: {result.error_message}"
            )
            
            self.assertIsNotNone(result.user_context, "User context should be created")
            self.assertEqual(result.user_context.user_id, "1234567890")

    def test_subprotocol_error_cases(self):
        """
        Test various error cases in subprotocol handling.
        
        These tests help identify specific configuration issues.
        """
        error_cases = [
            # (subprotocol_value, expected_behavior, description)
            ("", "no_token", "Empty subprotocol"),
            ("invalid-format", "no_token", "Invalid format without jwt prefix"),
            ("jwt.", "no_token", "JWT prefix but no token"),  # Issue #342 fix: return None instead of error to prevent 1011
            ("jwt.invalid", "no_token", "JWT prefix but invalid token"),  # Issue #342 fix: return None instead of error to prevent 1011
            ("jwt.a", "no_token", "JWT prefix but token too short"),  # Issue #342 fix: return None instead of error to prevent 1011
        ]
        
        for subprotocol_value, expected_behavior, description in error_cases:
            mock_websocket = self.create_mock_websocket(
                subprotocol_header=subprotocol_value
            )
            
            if expected_behavior == "no_token":
                extracted_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket)
                self.assertIsNone(
                    extracted_token,
                    f"Should not extract token for {description}: {subprotocol_value}"
                )
            elif expected_behavior == "error":
                try:
                    extract_jwt_from_subprotocol(subprotocol_value)
                    raise AssertionError(f"Should raise error for {description}: {subprotocol_value}")
                except ValueError:
                    # This is expected
                    pass
                except AssertionError:
                    # Re-raise assertion errors
                    raise
                except Exception as e:
                    raise AssertionError(f"Unexpected exception type for {description}: {subprotocol_value} - {e}")

    def test_configuration_mismatch_detection(self):
        """
        Test to detect specific configuration mismatches.
        
        This test helps identify exactly what configuration is causing issues.
        """
        # Test if the issue is with base64url encoding/decoding
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        # Test raw JWT in subprotocol (backend expectation?)
        mock_websocket_raw = self.create_mock_websocket(
            subprotocol_header=f"jwt.{jwt_token}"
        )
        
        # Test base64url encoded JWT in subprotocol (frontend behavior?)
        import base64
        encoded_token = base64.urlsafe_b64encode(jwt_token.encode()).decode().rstrip('=')
        mock_websocket_encoded = self.create_mock_websocket(
            subprotocol_header=f"jwt.{encoded_token}"
        )
        
        # Check which format works
        raw_result = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket_raw)
        encoded_result = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket_encoded)
        
        config_mismatch_details = []
        
        if raw_result != jwt_token:
            config_mismatch_details.append(f"Raw format failed: expected {jwt_token}, got {raw_result}")
            
        if encoded_result != jwt_token:
            config_mismatch_details.append(f"Encoded format failed: expected {jwt_token}, got {encoded_result}")
        
        if config_mismatch_details:
            raise AssertionError(f"Configuration mismatch detected:\n" + "\n".join(config_mismatch_details))


if __name__ == '__main__':
    unittest.main()