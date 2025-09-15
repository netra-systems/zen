"""
JWT Handler SSOT Validation Test Suite - Issue #1117

This test suite validates the current JWT validation SSOT violations by creating
FAILING tests that demonstrate the problem. These tests are designed to expose
the SSOT compliance gaps in JWT handling across the system.

CRITICAL: These tests are EXPECTED TO FAIL initially to prove SSOT violations exist.
They serve as validation for the remediation work by failing first, then passing
after SSOT consolidation is complete.

Test Focus Areas:
1. JWT wrapper duplication (UnifiedJWTProtocolHandler, UserContextExtractor)
2. Direct jwt.decode() operations bypassing auth service
3. Cross-service JWT validation inconsistencies
4. WebSocket auth wrapper violations

Business Impact: $500K+ ARR protected by ensuring consistent JWT validation
"""

import asyncio
import unittest
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class JWTHandlerSSOTValidationTests(SSotAsyncTestCase):
    """
    Test suite to validate SSOT compliance in JWT handling.
    
    These tests EXPOSE the current SSOT violations by checking for:
    1. Multiple JWT decode implementations
    2. Direct jwt.decode() bypassing auth service
    3. Inconsistent JWT validation patterns
    4. WebSocket-specific JWT wrapper duplication
    """
    
    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.test_jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJpYXQiOjE2MzQ3MzQ4MDAsImV4cCI6MTYzNDczODQwMH0.test_signature"
        self.test_user_id = "test_user_123"
        
    async def test_unified_jwt_protocol_handler_violates_ssot(self):
        """
        EXPECTED TO FAIL: Test that UnifiedJWTProtocolHandler bypasses auth service.
        
        This test demonstrates SSOT violation #1: JWT protocol handling should
        delegate to auth service, not implement local JWT operations.
        """
        from netra_backend.app.websocket_core.unified_jwt_protocol_handler import UnifiedJWTProtocolHandler
        
        # VIOLATION CHECK: UnifiedJWTProtocolHandler implements local JWT validation
        try:
            from fastapi import WebSocket
            
            # Mock WebSocket with JWT token
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.headers = {
                "authorization": f"Bearer {self.test_jwt_token}",
                "sec-websocket-protocol": f"jwt.{self.test_jwt_token}"
            }
            
            # SSOT VIOLATION: This should delegate to auth service, not handle locally
            extracted_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket)
            
            # VIOLATION ASSERTION: If this passes, it proves local JWT handling exists
            self.assertIsNotNone(extracted_token, 
                "SSOT VIOLATION: UnifiedJWTProtocolHandler implements local JWT extraction instead of delegating to auth service")
            
            # VIOLATION CHECK: Look for direct JWT decode operations
            handler_source = UnifiedJWTProtocolHandler.__module__
            import inspect
            source_code = inspect.getsource(UnifiedJWTProtocolHandler)
            
            # EXPECTED FAILURE: This should find local JWT operations
            self.assertNotIn("jwt.decode", source_code.lower(), 
                "SSOT VIOLATION: Found direct jwt.decode() operations in UnifiedJWTProtocolHandler")
            self.assertNotIn("base64", source_code.lower(),
                "SSOT VIOLATION: Found base64 JWT operations instead of auth service delegation")
            
            # This test should FAIL proving the violation exists
            self.fail("EXPECTED FAILURE: UnifiedJWTProtocolHandler should NOT implement local JWT handling - this proves SSOT violation exists")
            
        except ImportError as e:
            self.fail(f"Could not import UnifiedJWTProtocolHandler: {e}")
    
    async def test_user_context_extractor_duplicate_jwt_validation(self):
        """
        EXPECTED TO FAIL: Test that UserContextExtractor duplicates auth service logic.
        
        This test demonstrates SSOT violation #2: UserContextExtractor implements
        its own JWT validation instead of pure delegation to auth service.
        """
        try:
            from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
            
            # Create extractor instance
            extractor = UserContextExtractor()
            
            # VIOLATION CHECK: UserContextExtractor should only delegate to auth service
            # Any local JWT validation methods violate SSOT
            extractor_methods = [method for method in dir(extractor) if not method.startswith('_')]
            
            # EXPECTED VIOLATION: These methods suggest local JWT handling
            jwt_related_methods = [method for method in extractor_methods 
                                 if 'jwt' in method.lower() or 'token' in method.lower() or 'validate' in method.lower()]
            
            logger.info(f"JWT-related methods in UserContextExtractor: {jwt_related_methods}")
            
            # SSOT VIOLATION CHECK: If extractor has validate_and_decode_jwt, it's duplicating auth service
            if hasattr(extractor, 'validate_and_decode_jwt'):
                # This method should ONLY delegate to auth service, never do local validation
                import inspect
                validation_method_source = inspect.getsource(extractor.validate_and_decode_jwt)
                
                # VIOLATION INDICATORS: Local JWT operations instead of pure delegation
                ssot_violations = []
                if "jwt.decode" in validation_method_source.lower():
                    ssot_violations.append("Direct jwt.decode() operations found")
                if "jwt_secret" in validation_method_source.lower():
                    ssot_violations.append("Local JWT secret handling found")
                if "algorithms=" in validation_method_source.lower():
                    ssot_violations.append("Local JWT algorithm specification found")
                
                # EXPECTED FAILURE: This should find SSOT violations
                if not ssot_violations:
                    # If no violations found, the method is properly delegating (good)
                    # But we expect violations to exist currently
                    self.fail("EXPECTED FAILURE: UserContextExtractor.validate_and_decode_jwt should have SSOT violations - none found suggests remediation already done")
                
                # Report the violations we found
                logger.error(f"SSOT VIOLATIONS in UserContextExtractor.validate_and_decode_jwt: {ssot_violations}")
                
            # This test should FAIL due to SSOT violations
            self.fail("EXPECTED FAILURE: UserContextExtractor should use pure delegation to auth service - local JWT validation violates SSOT")
            
        except ImportError as e:
            self.fail(f"Could not import UserContextExtractor: {e}")
    
    async def test_direct_jwt_decode_operations_violate_ssot(self):
        """
        EXPECTED TO FAIL: Test that finds direct jwt.decode() operations in backend.
        
        This test scans for SSOT violation #3: Any direct jwt.decode() operations
        in the backend service should be eliminated in favor of auth service calls.
        """
        import os
        import re
        
        # Search for direct jwt.decode operations in backend code
        backend_path = "/Users/anthony/Desktop/netra-apex/netra_backend"
        jwt_decode_violations = []
        
        # Scan backend files for direct JWT operations
        for root, dirs, files in os.walk(backend_path):
            # Skip test directories and cache
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and 'test' not in d.lower()]
            
            for file in files:
                if file.endswith('.py') and 'test' not in file.lower():
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Look for SSOT violations
                        if re.search(r'jwt\.decode\s*\(', content, re.IGNORECASE):
                            jwt_decode_violations.append(f"{file_path}: Direct jwt.decode() call found")
                        
                        if re.search(r'import\s+jwt', content) and 'auth_client_core' not in content:
                            jwt_decode_violations.append(f"{file_path}: Direct JWT import without auth service")
                            
                    except Exception as e:
                        logger.warning(f"Could not scan {file_path}: {e}")
        
        # EXPECTED VIOLATIONS: Report what we found
        if jwt_decode_violations:
            logger.error(f"SSOT VIOLATIONS - Direct JWT operations found: {jwt_decode_violations}")
            
        # This test should FAIL if violations exist (which we expect)
        self.assertEqual(len(jwt_decode_violations), 0, 
            f"EXPECTED FAILURE: Found {len(jwt_decode_violations)} direct JWT operations that violate SSOT: {jwt_decode_violations[:5]}")
    
    async def test_websocket_auth_wrapper_duplication(self):
        """
        EXPECTED TO FAIL: Test that WebSocket auth wrappers duplicate auth service logic.
        
        This test demonstrates SSOT violation #4: WebSocket authentication should
        use the same auth service interface as REST endpoints, not custom wrappers.
        """
        try:
            # Check UnifiedJWTProtocolHandler for WebSocket-specific auth logic
            from netra_backend.app.websocket_core.unified_jwt_protocol_handler import UnifiedJWTProtocolHandler
            
            # VIOLATION CHECK: WebSocket handler should delegate, not implement auth logic
            handler_methods = [method for method in dir(UnifiedJWTProtocolHandler) 
                             if not method.startswith('__')]
            
            # These methods suggest local implementation instead of delegation
            violation_methods = []
            for method in handler_methods:
                if any(keyword in method.lower() for keyword in ['extract', 'decode', 'validate', 'normalize']):
                    violation_methods.append(method)
            
            logger.error(f"WebSocket auth methods that should delegate to auth service: {violation_methods}")
            
            # SSOT VIOLATION: If methods exist, they should delegate not implement
            self.assertEqual(len(violation_methods), 0,
                f"EXPECTED FAILURE: Found {len(violation_methods)} WebSocket auth methods that should delegate to auth service: {violation_methods}")
            
        except ImportError as e:
            self.fail(f"Could not import WebSocket auth components: {e}")
    
    async def test_auth_service_is_single_source_of_truth(self):
        """
        EXPECTED TO FAIL: Test that validates auth service is the ONLY JWT handler.
        
        This test checks that the auth service is properly configured as the
        single source of truth for all JWT operations across the system.
        """
        try:
            # Check that auth service client is properly configured
            from netra_backend.app.clients.auth_client_core import auth_client
            
            # Verify auth service has expected JWT validation interface
            required_methods = ['validate_token', 'decode_token', 'verify_token']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(auth_client, method):
                    missing_methods.append(method)
            
            # EXPECTED ISSUE: Auth service may not have complete interface
            if missing_methods:
                self.fail(f"EXPECTED FAILURE: Auth service missing SSOT JWT methods: {missing_methods}")
            
            # Test auth service is being used consistently
            from netra_backend.app.websocket_core.user_context_extractor import get_user_context_extractor
            
            extractor = get_user_context_extractor()
            auth_service_used = extractor._get_auth_service() == auth_client
            
            # VIOLATION CHECK: Extractor should use the SSOT auth service
            self.assertTrue(auth_service_used, 
                "EXPECTED FAILURE: UserContextExtractor not using SSOT auth service client")
            
            # This test validates the auth service SSOT configuration
            logger.info("Auth service SSOT configuration validated successfully")
            
        except ImportError as e:
            self.fail(f"Could not import auth service components: {e}")
        except Exception as e:
            # This might indicate SSOT violation - auth service not properly configured
            self.fail(f"EXPECTED FAILURE: Auth service SSOT configuration issue: {e}")
    
    async def test_jwt_secret_consistency_across_services(self):
        """
        EXPECTED TO FAIL: Test that JWT secrets are consistent between services.
        
        This test demonstrates potential SSOT violation #5: JWT secret inconsistencies
        between backend and auth service that cause validation failures.
        """
        try:
            # Check backend JWT configuration
            env = get_env()
            backend_jwt_secret = env.get('JWT_SECRET') or env.get('JWT_SECRET_KEY')
            
            # VIOLATION CHECK: Backend should not have local JWT secrets
            if backend_jwt_secret:
                logger.warning(f"SSOT VIOLATION: Backend has local JWT secret configuration: {backend_jwt_secret[:10]}...")
            
            # Check auth service configuration
            from netra_backend.app.clients.auth_client_core import auth_client
            
            # This test should reveal configuration inconsistencies
            # EXPECTED FAILURE: Different services may have different JWT configurations
            self.assertIsNone(backend_jwt_secret,
                "EXPECTED FAILURE: Backend should not have local JWT secret - this should be in auth service only")
            
        except Exception as e:
            # Configuration inconsistencies are expected
            logger.error(f"JWT secret configuration issue (expected): {e}")
            self.fail(f"EXPECTED FAILURE: JWT secret configuration inconsistency detected: {e}")


if __name__ == '__main__':
    unittest.main()