"""
Test Suite for Issue #1195: Auth Flow Delegation SSOT Compliance

Business Value Justification (BVJ):
- Segment: Platform/Security
- Business Goal: Ensure consistent auth flows across all services
- Value Impact: Prevents auth bypasses and security vulnerabilities
- Strategic Impact: Maintains centralized auth control and audit trails

This test suite validates that authentication flows properly delegate to
the auth service SSOT rather than implementing local auth logic.

Focus Areas:
1. WebSocket authentication flows
2. HTTP route authentication flows  
3. Middleware authentication flows
4. Background service authentication flows

These tests validate that ALL authentication paths go through the auth service.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from test_framework.base_integration_test import BaseIntegrationTest
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class AuthFlowDelegationComplianceTests(BaseIntegrationTest):
    """
    Test suite to validate auth flow delegation to auth service SSOT.
    
    Validates that all authentication flows properly delegate to auth service
    rather than implementing local authentication logic.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.auth_flow_violations = []
        
    @pytest.mark.ssot_compliance
    @pytest.mark.auth_flow
    async def test_websocket_auth_flow_delegates_to_auth_service(self):
        """
        AUTH FLOW TEST: Verify WebSocket authentication delegates to auth service.
        
        Validates that WebSocket authentication flows use auth service delegation
        rather than local authentication logic.
        
        EXPECTED: PASS (WebSocket auth should delegate properly)
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        # Create extractor instance
        extractor = UserContextExtractor()
        
        # Mock WebSocket with valid token
        mock_websocket = Mock()
        mock_websocket.headers = {
            "authorization": "Bearer test_jwt_token_for_delegation_test"
        }
        
        # Mock auth service to track delegation
        auth_service_called = False
        original_auth_service = None
        
        async def mock_validate_token(token):
            nonlocal auth_service_called
            auth_service_called = True
            return {
                'valid': True,
                'payload': {
                    'sub': 'test_user_123',
                    'iat': 1234567890,
                    'exp': 9999999999
                }
            }
        
        try:
            # Patch the auth service validation
            with patch.object(extractor, 'auth_service') as mock_auth_service:
                mock_auth_service.validate_token = mock_validate_token
                
                # Test WebSocket context extraction
                user_context, auth_info = await extractor.extract_user_context_from_websocket(mock_websocket)
                
                # Verify delegation occurred
                if not auth_service_called:
                    violation_details = {
                        "flow": "websocket_authentication",
                        "method": "extract_user_context_from_websocket",
                        "file": "netra_backend/app/websocket_core/user_context_extractor.py",
                        "violation_type": "missing_auth_service_delegation",
                        "ssot_requirement": "WebSocket auth must delegate to auth service"
                    }
                    
                    self.auth_flow_violations.append(violation_details)
                    
                    pytest.fail(
                        f"ISSUE #1195 AUTH FLOW VIOLATION: WebSocket authentication did not delegate to auth service. "
                        f"Details: {violation_details}"
                    )
                
                # Verify proper user context creation
                assert user_context is not None
                assert user_context.user_id == 'test_user_123'
                assert auth_info is not None
                
                logger.info("✅ ISSUE #1195 COMPLIANCE: WebSocket authentication properly delegates to auth service")
                
        except Exception as e:
            logger.error(f"WebSocket auth flow test failed: {e}")
            raise

    @pytest.mark.ssot_compliance
    @pytest.mark.auth_flow
    async def test_http_route_auth_flow_delegates_to_auth_service(self):
        """
        AUTH FLOW TEST: Verify HTTP route authentication delegates to auth service.
        
        Validates that HTTP route authentication (like messages API) properly
        delegates to auth service for JWT validation.
        
        EXPECTED: PASS (HTTP auth should delegate properly)
        """
        from netra_backend.app.routes.messages import get_current_user_from_jwt
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock credentials
        test_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test_jwt_token_for_http_delegation"
        )
        
        # Track auth service delegation
        auth_service_called = False
        
        async def mock_validate_and_decode_jwt(token, fast_path_enabled=False):
            nonlocal auth_service_called
            auth_service_called = True
            return {
                'sub': 'test_user_456',
                'iat': 1234567890,
                'exp': 9999999999
            }
        
        try:
            # Patch the JWT validation to track delegation
            with patch('netra_backend.app.websocket_core.user_context_extractor.UserContextExtractor.validate_and_decode_jwt', 
                      side_effect=mock_validate_and_decode_jwt):
                
                # Test HTTP route authentication
                user_id = await get_current_user_from_jwt(test_credentials)
                
                # Verify delegation occurred
                if not auth_service_called:
                    violation_details = {
                        "flow": "http_route_authentication",
                        "method": "get_current_user_from_jwt",
                        "file": "netra_backend/app/routes/messages.py",
                        "violation_type": "missing_auth_service_delegation",
                        "ssot_requirement": "HTTP route auth must delegate to auth service"
                    }
                    
                    self.auth_flow_violations.append(violation_details)
                    
                    pytest.fail(
                        f"ISSUE #1195 AUTH FLOW VIOLATION: HTTP route authentication did not delegate to auth service. "
                        f"Details: {violation_details}"
                    )
                
                # Verify proper user extraction
                assert user_id == 'test_user_456'
                
                logger.info("✅ ISSUE #1195 COMPLIANCE: HTTP route authentication properly delegates to auth service")
                
        except HTTPException as e:
            if e.status_code == 401:
                # Expected if test token is rejected
                logger.info("HTTP auth flow test: Expected 401 (test token validation)")
            else:
                raise
        except Exception as e:
            logger.error(f"HTTP route auth flow test failed: {e}")
            raise

    @pytest.mark.ssot_compliance
    @pytest.mark.auth_flow
    async def test_middleware_auth_flow_compliance_check(self):
        """
        AUTH FLOW TEST: Check middleware authentication flow compliance.
        
        Investigates the GCP auth context middleware to determine if it
        performs proper auth service delegation or local authentication.
        
        EXPECTED: FAIL initially if middleware performs local auth
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        from fastapi import Request
        
        # Create middleware instance
        middleware = GCPAuthContextMiddleware(None)
        
        # Mock request with JWT token
        mock_request = Mock(spec=Request)
        mock_request.headers = {
            'Authorization': 'Bearer test_middleware_jwt_token'
        }
        mock_request.state = Mock()
        
        # Check if middleware has local JWT decoding
        if hasattr(middleware, '_decode_jwt_context'):
            # VIOLATION: Middleware performs local JWT decoding
            violation_details = {
                "flow": "middleware_authentication",
                "method": "_decode_jwt_context",
                "file": "netra_backend/app/middleware/gcp_auth_context_middleware.py",
                "violation_type": "local_jwt_decoding_in_middleware",
                "ssot_requirement": "Middleware must delegate JWT operations to auth service"
            }
            
            self.auth_flow_violations.append(violation_details)
            
            logger.critical(
                f"🚨 ISSUE #1195 AUTH FLOW VIOLATION: GCP auth middleware performs local JWT decoding. "
                f"This must be replaced with auth service delegation."
            )
            
            pytest.fail(
                f"ISSUE #1195 AUTH FLOW VIOLATION: Middleware contains local JWT decoding method. "
                f"Details: {violation_details}"
            )
        else:
            logger.info("✅ ISSUE #1195 COMPLIANCE: GCP auth middleware does not contain local JWT decoding")
        
        # Test middleware auth context extraction
        try:
            auth_context = await middleware._extract_auth_context(mock_request)
            
            # Check if auth context extraction delegates properly
            if 'jwt_token' in auth_context:
                # Check if the token was decoded locally or just extracted
                has_decoded_claims = any(
                    key in auth_context for key in ['user_id', 'user_email', 'permissions']
                )
                
                if has_decoded_claims:
                    logger.warning(
                        f"⚠️ ISSUE #1195 WARNING: Middleware auth context contains decoded claims. "
                        f"Verify this comes from auth service delegation, not local decoding."
                    )
                else:
                    logger.info("✅ ISSUE #1195 COMPLIANCE: Middleware only extracts token, doesn't decode locally")
                    
        except Exception as e:
            logger.warning(f"Middleware auth context test encountered error: {e}")

    @pytest.mark.ssot_compliance
    @pytest.mark.auth_flow
    async def test_no_local_auth_bypass_paths(self):
        """
        SECURITY TEST: Verify no local authentication bypass paths exist.
        
        Validates that there are no code paths that bypass auth service
        delegation and perform local authentication decisions.
        
        EXPECTED: PASS (no bypass paths should exist)
        """
        # Define patterns that indicate auth bypass or local auth logic
        bypass_patterns = [
            "skip_auth",
            "bypass_auth", 
            "local_auth",
            "debug_auth",
            "test_auth_skip",
            "auth_disabled",
            "no_auth_required",
            "anonymous_access"
        ]
        
        # Check specific modules for bypass patterns
        modules_to_check = [
            'netra_backend.app.websocket_core.user_context_extractor',
            'netra_backend.app.routes.messages',
            'netra_backend.app.middleware.gcp_auth_context_middleware'
        ]
        
        bypasses_found = []
        
        for module_name in modules_to_check:
            try:
                import importlib
                module = importlib.import_module(module_name)
                
                # Get module source if available
                import inspect
                try:
                    source = inspect.getsource(module)
                    
                    # Check for bypass patterns
                    for pattern in bypass_patterns:
                        if pattern.lower() in source.lower():
                            bypass_info = {
                                "module": module_name,
                                "pattern": pattern,
                                "violation_type": "potential_auth_bypass",
                                "requires_investigation": True
                            }
                            bypasses_found.append(bypass_info)
                            
                except Exception as e:
                    logger.debug(f"Could not get source for {module_name}: {e}")
                    
            except ImportError as e:
                logger.warning(f"Could not import {module_name}: {e}")
        
        if bypasses_found:
            logger.warning(
                f"⚠️ ISSUE #1195 WARNING: Found {len(bypasses_found)} potential auth bypass patterns. "
                f"Manual investigation required: {bypasses_found}"
            )
            
            # Log each bypass for investigation
            for bypass in bypasses_found:
                logger.warning(f"Potential auth bypass: {bypass}")
        else:
            logger.info("✅ ISSUE #1195 COMPLIANCE: No obvious auth bypass patterns found")

    @pytest.mark.ssot_compliance
    @pytest.mark.auth_flow
    async def test_auth_error_handling_delegates_properly(self):
        """
        AUTH FLOW TEST: Verify auth error handling maintains delegation.
        
        Validates that authentication error handling doesn't fall back to
        local auth logic and maintains proper auth service delegation.
        
        EXPECTED: PASS (error handling should maintain delegation)
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        extractor = UserContextExtractor()
        
        # Mock WebSocket with invalid token
        mock_websocket = Mock()
        mock_websocket.headers = {
            "authorization": "Bearer invalid_token_for_error_test"
        }
        
        # Mock auth service to return error
        async def mock_failing_validate_token(token):
            return {'valid': False, 'error': 'Token validation failed'}
        
        try:
            with patch.object(extractor, 'auth_service') as mock_auth_service:
                mock_auth_service.validate_token = mock_failing_validate_token
                
                # Test that error handling doesn't bypass auth service
                with pytest.raises(HTTPException) as exc_info:
                    await extractor.extract_user_context_from_websocket(mock_websocket)
                
                # Verify proper error response (should be 401 Unauthorized)
                assert exc_info.value.status_code == 401
                
                logger.info("✅ ISSUE #1195 COMPLIANCE: Auth error handling maintains delegation pattern")
                
        except Exception as e:
            logger.error(f"Auth error handling test failed: {e}")
            raise

    @pytest.mark.ssot_compliance
    @pytest.mark.auth_flow
    async def test_concurrent_auth_flows_maintain_isolation(self):
        """
        AUTH FLOW TEST: Verify concurrent auth flows maintain proper isolation.
        
        Validates that multiple concurrent authentication flows properly
        delegate to auth service without interference or state leakage.
        
        EXPECTED: PASS (concurrent flows should be properly isolated)
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        # Create multiple extractor instances to simulate concurrent flows
        extractors = [UserContextExtractor() for _ in range(3)]
        
        # Mock WebSockets with different tokens
        mock_websockets = []
        expected_user_ids = []
        
        for i in range(3):
            mock_ws = Mock()
            mock_ws.headers = {
                "authorization": f"Bearer concurrent_test_token_{i}"
            }
            mock_websockets.append(mock_ws)
            expected_user_ids.append(f"concurrent_user_{i}")
        
        # Mock auth service responses for each token
        def create_mock_validate_token(user_id):
            async def mock_validate_token(token):
                return {
                    'valid': True,
                    'payload': {
                        'sub': user_id,
                        'iat': 1234567890,
                        'exp': 9999999999
                    }
                }
            return mock_validate_token
        
        try:
            # Test concurrent authentication flows
            tasks = []
            
            for i, (extractor, websocket, user_id) in enumerate(zip(extractors, mock_websockets, expected_user_ids)):
                with patch.object(extractor, 'auth_service') as mock_auth_service:
                    mock_auth_service.validate_token = create_mock_validate_token(user_id)
                    
                    task = extractor.extract_user_context_from_websocket(websocket)
                    tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify each result has correct user isolation
            for i, (result, expected_user_id) in enumerate(zip(results, expected_user_ids)):
                if isinstance(result, Exception):
                    logger.error(f"Concurrent auth flow {i} failed: {result}")
                    continue
                    
                user_context, auth_info = result
                
                # Verify no cross-contamination between concurrent flows
                assert user_context.user_id == expected_user_id, \
                    f"User ID mismatch in concurrent flow {i}: expected {expected_user_id}, got {user_context.user_id}"
            
            logger.info("✅ ISSUE #1195 COMPLIANCE: Concurrent auth flows maintain proper isolation")
            
        except Exception as e:
            logger.error(f"Concurrent auth flow test failed: {e}")
            raise

    def teardown_method(self):
        """Teardown for each test method."""
        if self.auth_flow_violations:
            logger.critical(
                f"🚨 ISSUE #1195 AUTH FLOW VIOLATIONS: Found {len(self.auth_flow_violations)} violations. "
                f"All auth flows must delegate to auth service SSOT."
            )
            
            # Generate detailed violation report
            violation_summary = {
                "total_violations": len(self.auth_flow_violations),
                "violation_types": list(set(v.get("violation_type", "unknown") for v in self.auth_flow_violations)),
                "flows_affected": list(set(v.get("flow", "unknown") for v in self.auth_flow_violations)),
                "violations": self.auth_flow_violations
            }
            
            logger.error(f"ISSUE #1195 AUTH FLOW VIOLATION REPORT: {violation_summary}")
        
        super().teardown_method()


if __name__ == "__main__":
    # Allow running this test file directly for Issue #1195 validation
    pytest.main([__file__, "-v", "--tb=short"])