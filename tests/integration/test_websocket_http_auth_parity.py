"""
HTTP vs WebSocket Authentication Parity Test Suite

ISSUE #342: Identifies configuration differences between HTTP and WebSocket auth

This test suite compares HTTP authentication (which works) with WebSocket 
authentication (which has issues) to identify the exact configuration mismatch.

PRIORITY: SECONDARY - These tests should reveal specific configuration differences
"""

import pytest
import json
import asyncio
import unittest
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# SSOT imports from registry  
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    authenticate_websocket_ssot
)
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)

class TestWebSocketHttpAuthParity(SSotAsyncTestCase):
    """
    Test suite to compare HTTP vs WebSocket authentication configurations.
    
    These tests should reveal exact differences causing Issue #342.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.websocket_authenticator = UnifiedWebSocketAuthenticator()
        
    def create_mock_websocket(self, headers: Dict[str, str]) -> Mock:
        """Create mock WebSocket with specific headers."""
        websocket = Mock()
        websocket.headers = headers
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        websocket.client.port = 8000
        websocket.client_state = Mock()
        websocket.client_state.name = "CONNECTED"
        return websocket
    
    def create_mock_http_request(self, headers: Dict[str, str]) -> Mock:
        """Create mock HTTP request with specific headers."""
        request = Mock()
        request.headers = headers
        return request

    async def test_same_jwt_token_both_protocols(self):
        """
        Test that the same JWT token works for both HTTP and WebSocket auth.
        
        This test identifies if the issue is with token format or protocol handling.
        """
        # Standard JWT token
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        # Mock unified auth service to return success
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_get_service:
            mock_auth_service = AsyncMock()
            mock_get_service.return_value = mock_auth_service
            
            # Mock successful authentication result
            mock_auth_result = AuthResult(
                success=True,
                user_id="test-user-123",
                email="test@example.com",
                permissions=["read", "write"]
            )
            
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            mock_user_context = UserExecutionContext(
                user_id="test-user-123",
                thread_id="thread-123",
                run_id="run-123",
                request_id="req-123",
                websocket_client_id="ws-client-123"
            )
            
            mock_auth_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
            mock_auth_service.authenticate_token.return_value = mock_auth_result
            
            # Test 1: HTTP Authentication (via Authorization header)
            http_result = await mock_auth_service.authenticate_token(
                token=jwt_token,
                context=AuthenticationContext.REST_API,
                method=AuthenticationMethod.JWT_TOKEN
            )
            
            # Test 2: WebSocket Authentication (via Authorization header)
            websocket_auth_headers = self.create_mock_websocket({
                "authorization": f"Bearer {jwt_token}"
            })
            
            websocket_result = await authenticate_websocket_ssot(websocket_auth_headers)
            
            # Test 3: WebSocket Authentication (via subprotocol)
            websocket_subprotocol = self.create_mock_websocket({
                "sec-websocket-protocol": f"jwt.{jwt_token}"
            })
            
            websocket_subprotocol_result = await authenticate_websocket_ssot(websocket_subprotocol)
            
            # Compare results
            comparison_results = {
                "http_auth": {
                    "success": http_result.success,
                    "user_id": getattr(http_result, 'user_id', None),
                    "error": getattr(http_result, 'error', None),
                },
                "websocket_auth_header": {
                    "success": websocket_result.success,
                    "user_id": websocket_result.user_context.user_id if websocket_result.user_context else None,
                    "error": websocket_result.error_message,
                },
                "websocket_subprotocol": {
                    "success": websocket_subprotocol_result.success,
                    "user_id": websocket_subprotocol_result.user_context.user_id if websocket_subprotocol_result.user_context else None,
                    "error": websocket_subprotocol_result.error_message,
                }
            }
            
            # Analyze differences
            differences = []
            
            if http_result.success != websocket_result.success:
                differences.append(f"HTTP vs WebSocket header: success mismatch ({http_result.success} vs {websocket_result.success})")
                
            if http_result.success != websocket_subprotocol_result.success:
                differences.append(f"HTTP vs WebSocket subprotocol: success mismatch ({http_result.success} vs {websocket_subprotocol_result.success})")
            
            if websocket_result.success != websocket_subprotocol_result.success:
                differences.append(f"WebSocket header vs subprotocol: success mismatch ({websocket_result.success} vs {websocket_subprotocol_result.success})")
            
            # Log detailed comparison for analysis
            print("\n=== AUTH PARITY COMPARISON ===")
            print(json.dumps(comparison_results, indent=2))
            
            if differences:
                print("\n=== DETECTED DIFFERENCES ===")
                for diff in differences:
                    print(f"- {diff}")
                    
            # At minimum, all should succeed if using the same token
            self.assertTrue(http_result.success, "HTTP authentication should succeed")
            
            # These assertions reveal the Issue #342 bugs
            self.assertTrue(
                websocket_result.success, 
                f"WebSocket header authentication should succeed like HTTP. Error: {websocket_result.error_message}"
            )
            
            self.assertTrue(
                websocket_subprotocol_result.success,
                f"WebSocket subprotocol authentication should succeed. Error: {websocket_subprotocol_result.error_message}"
            )

    async def test_configuration_consistency_check(self):
        """
        Test configuration consistency between HTTP and WebSocket auth systems.
        
        This test checks if both systems use the same configuration values.
        """
        config_comparison = {}
        
        # Check HTTP authentication configuration
        try:
            http_auth_service = get_unified_auth_service()
            config_comparison["http_auth_service_available"] = http_auth_service is not None
            
            # Get HTTP auth configuration details
            if http_auth_service:
                config_comparison["http_auth_service_type"] = type(http_auth_service).__name__
                
        except Exception as e:
            config_comparison["http_auth_service_error"] = str(e)
        
        # Check WebSocket authentication configuration
        try:
            websocket_authenticator = UnifiedWebSocketAuthenticator()
            config_comparison["websocket_authenticator_available"] = websocket_authenticator is not None
            config_comparison["websocket_authenticator_type"] = type(websocket_authenticator).__name__
            
            # Check if WebSocket authenticator uses the same auth service
            websocket_auth_service = getattr(websocket_authenticator, '_auth_service', None)
            config_comparison["websocket_uses_unified_service"] = websocket_auth_service is not None
            
            if websocket_auth_service:
                config_comparison["websocket_auth_service_type"] = type(websocket_auth_service).__name__
                
        except Exception as e:
            config_comparison["websocket_authenticator_error"] = str(e)
        
        # Check environment configuration consistency
        try:
            from shared.isolated_environment import get_env
            env = get_env()
            
            # Check key auth-related env vars
            auth_env_vars = [
                "AUTH_SERVICE_URL",
                "JWT_SECRET",
                "JWT_SECRET_KEY", 
                "SERVICE_SECRET",
                "ENVIRONMENT"
            ]
            
            config_comparison["environment_config"] = {}
            for var in auth_env_vars:
                value = env.get(var)
                config_comparison["environment_config"][var] = {
                    "configured": value is not None,
                    "length": len(value) if value else 0,
                    "starts_with": value[:10] if value and len(value) > 10 else value
                }
                
        except Exception as e:
            config_comparison["environment_config_error"] = str(e)
        
        # Log configuration comparison
        print("\n=== CONFIGURATION CONSISTENCY CHECK ===")
        print(json.dumps(config_comparison, indent=2))
        
        # Check for configuration inconsistencies
        inconsistencies = []
        
        if not config_comparison.get("http_auth_service_available", False):
            inconsistencies.append("HTTP auth service not available")
            
        if not config_comparison.get("websocket_authenticator_available", False):
            inconsistencies.append("WebSocket authenticator not available")
            
        if not config_comparison.get("websocket_uses_unified_service", False):
            inconsistencies.append("WebSocket authenticator not using unified auth service")
        
        # Check if both use the same underlying service type
        http_service_type = config_comparison.get("http_auth_service_type")
        websocket_service_type = config_comparison.get("websocket_auth_service_type")
        
        if http_service_type and websocket_service_type and http_service_type != websocket_service_type:
            inconsistencies.append(f"Service type mismatch: HTTP uses {http_service_type}, WebSocket uses {websocket_service_type}")
        
        # Check critical environment variables
        env_config = config_comparison.get("environment_config", {})
        critical_missing = []
        
        for var in ["JWT_SECRET", "JWT_SECRET_KEY"]:
            if not env_config.get(var, {}).get("configured", False):
                critical_missing.append(var)
        
        if critical_missing:
            inconsistencies.append(f"Critical env vars missing: {critical_missing}")
        
        if inconsistencies:
            print("\n=== CONFIGURATION INCONSISTENCIES ===")
            for issue in inconsistencies:
                print(f"- {issue}")
            
            raise AssertionError(f"Configuration inconsistencies detected: {inconsistencies}")

    async def test_subprotocol_negotiation_comparison(self):
        """
        Test subprotocol negotiation differences that might cause issues.
        
        HTTP doesn't have subprotocol negotiation, but WebSocket does.
        This test checks if the negotiation process causes auth issues.
        """
        # Test different subprotocol formats and their negotiation success
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        from netra_backend.app.websocket_core.unified_jwt_protocol_handler import negotiate_websocket_subprotocol
        
        subprotocol_test_cases = [
            # (client_protocols, description, expected_success)
            ([f"jwt.{jwt_token}"], "JWT with token", True),
            (["jwt"], "JWT protocol only", True),
            (["jwt-auth"], "JWT auth protocol", True),
            ([f"jwt.{jwt_token}", "chat"], "JWT with other protocols", True),
            (["chat", f"jwt.{jwt_token}"], "JWT after other protocols", True),
            (["unsupported"], "Unsupported protocol", False),
            ([], "No protocols", False),
        ]
        
        negotiation_results = []
        
        for client_protocols, description, expected_success in subprotocol_test_cases:
            accepted_protocol = negotiate_websocket_subprotocol(client_protocols)
            
            result = {
                "description": description,
                "client_protocols": client_protocols,
                "accepted_protocol": accepted_protocol,
                "negotiation_success": accepted_protocol is not None,
                "expected_success": expected_success,
                "matches_expectation": (accepted_protocol is not None) == expected_success
            }
            
            negotiation_results.append(result)
            
        # Log negotiation results
        print("\n=== SUBPROTOCOL NEGOTIATION RESULTS ===")
        for result in negotiation_results:
            print(f"- {result['description']}: {result['negotiation_success']} (expected: {result['expected_success']})")
            if not result['matches_expectation']:
                print(f"   FAIL:  MISMATCH: Got {result['negotiation_success']}, expected {result['expected_success']}")
        
        # Check for mismatches
        mismatches = [r for r in negotiation_results if not r['matches_expectation']]
        
        if mismatches:
            mismatch_details = [f"{r['description']}: got {r['negotiation_success']}, expected {r['expected_success']}" for r in mismatches]
            raise AssertionError(f"Subprotocol negotiation mismatches: {mismatch_details}")

    async def test_auth_service_method_parity(self):
        """
        Test that HTTP and WebSocket authentication use equivalent methods.
        
        This checks if the auth service methods are consistent between protocols.
        """
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        # Check available methods on the unified auth service
        auth_service = get_unified_auth_service()
        
        method_comparison = {
            "auth_service_type": type(auth_service).__name__,
            "available_methods": [],
            "http_auth_method": None,
            "websocket_auth_method": None
        }
        
        # Get available methods
        for attr_name in dir(auth_service):
            if not attr_name.startswith('_') and callable(getattr(auth_service, attr_name)):
                method_comparison["available_methods"].append(attr_name)
        
        # Check for HTTP auth method
        if hasattr(auth_service, 'authenticate_token'):
            method_comparison["http_auth_method"] = "authenticate_token"
        elif hasattr(auth_service, 'authenticate'):
            method_comparison["http_auth_method"] = "authenticate"
        elif hasattr(auth_service, 'validate_token'):
            method_comparison["http_auth_method"] = "validate_token"
            
        # Check for WebSocket auth method  
        if hasattr(auth_service, 'authenticate_websocket'):
            method_comparison["websocket_auth_method"] = "authenticate_websocket"
        elif hasattr(auth_service, 'authenticate_ws'):
            method_comparison["websocket_auth_method"] = "authenticate_ws"
        
        # Log method comparison
        print("\n=== AUTH SERVICE METHOD COMPARISON ===")
        print(json.dumps(method_comparison, indent=2))
        
        # Check for method availability issues
        issues = []
        
        if not method_comparison["http_auth_method"]:
            issues.append("No HTTP authentication method found")
            
        if not method_comparison["websocket_auth_method"]:
            issues.append("No WebSocket authentication method found")
        
        if issues:
            raise AssertionError(f"Auth service method issues: {issues}")
        
        # Try to call both methods with the same token to see if they behave the same
        if method_comparison["http_auth_method"] and method_comparison["websocket_auth_method"]:
            # Mock WebSocket for testing
            mock_websocket = self.create_mock_websocket({
                "authorization": f"Bearer {jwt_token}"
            })
            
            try:
                # HTTP method call
                http_method = getattr(auth_service, method_comparison["http_auth_method"])
                
                if asyncio.iscoroutinefunction(http_method):
                    if method_comparison["http_auth_method"] == "authenticate_token":
                        http_result = await http_method(jwt_token, AuthenticationContext.REST_API, AuthenticationMethod.JWT_TOKEN)
                    else:
                        http_result = await http_method(jwt_token)
                else:
                    if method_comparison["http_auth_method"] == "authenticate_token":
                        http_result = http_method(jwt_token, AuthenticationContext.REST_API, AuthenticationMethod.JWT_TOKEN)
                    else:
                        http_result = http_method(jwt_token)
                
                # WebSocket method call
                websocket_method = getattr(auth_service, method_comparison["websocket_auth_method"])
                
                if asyncio.iscoroutinefunction(websocket_method):
                    websocket_result = await websocket_method(mock_websocket)
                else:
                    websocket_result = websocket_method(mock_websocket)
                
                # Compare results structure
                method_results = {
                    "http_result_type": type(http_result).__name__,
                    "websocket_result_type": type(websocket_result).__name__,
                    "http_success": getattr(http_result, 'success', None),
                    "websocket_success": getattr(websocket_result[0] if isinstance(websocket_result, tuple) else websocket_result, 'success', None)
                }
                
                print("\n=== METHOD PARITY TEST RESULTS ===")
                print(json.dumps(method_results, indent=2))
                
                # Check for result type mismatches
                if method_results["http_result_type"] != method_results["websocket_result_type"]:
                    if not (isinstance(websocket_result, tuple) and len(websocket_result) == 2):
                        issues.append(f"Result type mismatch: HTTP returns {method_results['http_result_type']}, WebSocket returns {method_results['websocket_result_type']}")
                
            except Exception as e:
                issues.append(f"Method parity test failed: {e}")
        
        if issues:
            raise AssertionError(f"Method parity issues: {issues}")


if __name__ == '__main__':
    unittest.main()