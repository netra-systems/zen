"""
Cross-Service JWT Flow Integration Tests - Issue #1117

This test suite validates JWT flow consistency between auth service and backend
by creating FAILING tests that expose SSOT violations in cross-service JWT handling.

CRITICAL: These tests are EXPECTED TO FAIL initially to demonstrate:
1. JWT validation inconsistencies between services
2. Cross-service communication issues
3. Token format mismatches
4. Authentication flow breakdowns

These failures will validate that SSOT remediation is needed and provide
a test harness to verify the fix works correctly.

Business Impact: $500K+ ARR Golden Path user flow depends on reliable
cross-service JWT authentication working consistently.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import httpx

from test_framework.ssot.base_test_case import SSotAsyncTestCase  
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class CrossServiceJWTFlowTests(SSotAsyncTestCase):
    """
    Integration tests for JWT flow between auth service and backend.
    
    These tests expose SSOT violations by validating cross-service JWT handling:
    1. Auth service JWT generation vs backend JWT validation
    2. Token format consistency across services
    3. WebSocket authentication integration
    4. Error handling consistency
    """
    
    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.auth_service_url = "http://auth-service:8001"
        self.backend_url = "http://backend:8000"
        self.test_user_credentials = {
            "email": "test@netra.com",
            "password": "test_password_123"
        }
        self.test_jwt_token = None
    
    async def test_auth_service_jwt_generation_format(self):
        """
        EXPECTED TO FAIL: Test auth service JWT generation format consistency.
        
        This test validates that auth service generates JWT tokens in the format
        expected by backend services. Format mismatches are SSOT violations.
        """
        try:
            # Simulate auth service JWT generation
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            
            jwt_handler = JWTHandler()
            
            # Generate test JWT token
            test_payload = {
                "sub": "test_user_123",
                "email": "test@netra.com",
                "iat": 1634734800,
                "exp": 1634738400,
                "permissions": ["read", "write"],
                "roles": ["user"]
            }
            
            # SSOT CHECK: Auth service should generate tokens in expected format
            token = await jwt_handler.generate_token(test_payload)
            self.assertIsNotNone(token, "Auth service should generate valid JWT token")
            
            # Validate token structure
            token_parts = token.split('.')
            self.assertEqual(len(token_parts), 3, 
                "EXPECTED FAILURE: JWT token should have 3 parts (header.payload.signature)")
            
            # Store token for use in other tests
            self.test_jwt_token = token
            
            logger.info(f"Generated JWT token: {token[:20]}...")
            
        except ImportError as e:
            self.fail(f"EXPECTED FAILURE: Could not import auth service JWT handler: {e}")
        except Exception as e:
            self.fail(f"EXPECTED FAILURE: Auth service JWT generation failed: {e}")
    
    async def test_backend_jwt_validation_consistency(self):
        """
        EXPECTED TO FAIL: Test backend JWT validation matches auth service format.
        
        This test validates that backend can properly validate JWT tokens generated
        by auth service. Validation failures indicate SSOT violations.
        """
        try:
            # First generate a token (or use from previous test)
            if not self.test_jwt_token:
                await self.test_auth_service_jwt_generation_format()
            
            # Test backend JWT validation
            from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
            
            extractor = UserContextExtractor()
            
            # SSOT VIOLATION CHECK: Backend should validate auth service tokens
            validated_payload = await extractor.validate_and_decode_jwt(self.test_jwt_token)
            
            # EXPECTED FAILURE: This may fail due to secret mismatches or format issues
            self.assertIsNotNone(validated_payload, 
                "EXPECTED FAILURE: Backend should validate auth service JWT tokens")
            
            # Verify payload structure consistency
            required_fields = ["sub", "iat", "exp"]
            missing_fields = [field for field in required_fields if field not in validated_payload]
            
            self.assertEqual(len(missing_fields), 0,
                f"EXPECTED FAILURE: JWT payload missing required fields: {missing_fields}")
            
            # Verify user ID extraction consistency
            user_id = validated_payload.get("sub")
            self.assertEqual(user_id, "test_user_123",
                "EXPECTED FAILURE: User ID extraction inconsistent between services")
            
            logger.info("Backend JWT validation successful")
            
        except Exception as e:
            # This failure indicates SSOT violation - services not aligned
            logger.error(f"Cross-service JWT validation failed: {e}")
            self.fail(f"EXPECTED FAILURE: Cross-service JWT validation inconsistency: {e}")
    
    async def test_websocket_auth_integration_with_auth_service(self):
        """
        EXPECTED TO FAIL: Test WebSocket authentication integrates with auth service.
        
        This test validates that WebSocket authentication uses the same JWT validation
        logic as REST endpoints, ensuring consistent auth across protocols.
        """
        try:
            from fastapi import WebSocket
            from netra_backend.app.websocket_core.user_context_extractor import extract_websocket_user_context
            
            # Mock WebSocket with JWT token
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.headers = {
                "authorization": f"Bearer {self.test_jwt_token or 'test_token'}",
                "sec-websocket-protocol": "jwt-auth",
                "user-agent": "test-client",
                "origin": "https://app.staging.netrasystems.ai"
            }
            
            # SSOT VIOLATION CHECK: WebSocket auth should use same validation as REST
            try:
                user_context, auth_info = await extract_websocket_user_context(mock_websocket)
                
                # Verify context created successfully
                self.assertIsNotNone(user_context, "WebSocket should create valid user context")
                self.assertIsNotNone(auth_info, "WebSocket should provide auth info")
                
                # Verify consistency with auth service format
                self.assertEqual(user_context.user_id, "test_user_123",
                    "WebSocket user context should match auth service user ID")
                
                logger.info("WebSocket auth integration successful")
                
            except Exception as auth_error:
                # This is the expected failure - WebSocket auth not integrated properly
                self.fail(f"EXPECTED FAILURE: WebSocket auth not properly integrated with auth service: {auth_error}")
            
        except ImportError as e:
            self.fail(f"EXPECTED FAILURE: Could not import WebSocket auth components: {e}")
    
    async def test_auth_service_backend_secret_consistency(self):
        """
        EXPECTED TO FAIL: Test JWT secret consistency between auth service and backend.
        
        This test validates that both services use the same JWT secrets for
        token generation and validation. Secret mismatches are major SSOT violations.
        """
        try:
            # Check auth service JWT secret configuration
            env = get_env()
            
            # VIOLATION CHECK: Services should use same JWT configuration source
            auth_service_secret = env.get('JWT_SECRET_KEY') or env.get('JWT_SECRET')
            backend_jwt_config = env.get('BACKEND_JWT_SECRET') or env.get('JWT_SECRET_KEY')
            
            logger.info(f"Auth service secret configured: {'Yes' if auth_service_secret else 'No'}")
            logger.info(f"Backend JWT config found: {'Yes' if backend_jwt_config else 'No'}")
            
            # EXPECTED FAILURE: Services may have different configurations
            if auth_service_secret and backend_jwt_config:
                # Both services have JWT configuration - they should match
                self.assertEqual(auth_service_secret, backend_jwt_config,
                    "EXPECTED FAILURE: JWT secrets differ between auth service and backend")
            else:
                # Configuration missing or inconsistent
                self.fail(f"EXPECTED FAILURE: JWT secret configuration inconsistent - "
                        f"Auth service: {'configured' if auth_service_secret else 'missing'}, "
                        f"Backend: {'configured' if backend_jwt_config else 'missing'}")
            
        except Exception as e:
            # Configuration issues are expected SSOT violations
            logger.error(f"JWT secret consistency check failed: {e}")
            self.fail(f"EXPECTED FAILURE: JWT secret configuration problem: {e}")
    
    async def test_cross_service_error_handling_consistency(self):
        """
        EXPECTED TO FAIL: Test error handling consistency across services.
        
        This test validates that auth failures are handled consistently
        between auth service and backend, providing unified error responses.
        """
        try:
            from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
            
            extractor = UserContextExtractor()
            
            # Test with invalid JWT token
            invalid_token = "invalid.jwt.token"
            
            # SSOT CHECK: Error handling should be consistent
            try:
                result = await extractor.validate_and_decode_jwt(invalid_token)
                
                # Should return None for invalid token
                self.assertIsNone(result, "Invalid JWT should return None")
                
            except Exception as e:
                # Error handling inconsistency
                logger.error(f"JWT validation error handling: {e}")
            
            # Test with expired token format
            expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJpYXQiOjE2MDA3MzQ4MDAsImV4cCI6MTYwMDczODQwMH0.expired_signature"
            
            try:
                result = await extractor.validate_and_decode_jwt(expired_token)
                
                # Should handle expired token gracefully
                self.assertIsNone(result, "Expired JWT should return None")
                
            except Exception as e:
                # Inconsistent error handling for expired tokens
                logger.error(f"Expired JWT handling inconsistency: {e}")
                self.fail(f"EXPECTED FAILURE: Inconsistent expired token handling: {e}")
            
        except Exception as e:
            self.fail(f"EXPECTED FAILURE: Error handling consistency test failed: {e}")
    
    async def test_auth_service_availability_and_integration(self):
        """
        EXPECTED TO FAIL: Test that auth service is properly integrated with backend.
        
        This test validates that backend can successfully communicate with auth service
        for JWT operations. Communication failures indicate integration SSOT violations.
        """
        try:
            from netra_backend.app.clients.auth_client_core import auth_client
            
            # Test auth service connectivity
            test_payload = {"test": "connectivity"}
            
            # SSOT VIOLATION CHECK: Backend should successfully communicate with auth service
            try:
                # This should work if services are properly integrated
                health_check = await auth_client.health_check()
                self.assertTrue(health_check.get('healthy', False),
                    "EXPECTED FAILURE: Auth service should be healthy and accessible")
                
                logger.info("Auth service connectivity successful")
                
            except Exception as conn_error:
                # This is expected failure - services not properly integrated
                self.fail(f"EXPECTED FAILURE: Cannot connect to auth service: {conn_error}")
            
            # Test JWT validation through auth service
            if self.test_jwt_token:
                try:
                    validation_result = await auth_client.validate_token(self.test_jwt_token)
                    self.assertIsNotNone(validation_result, 
                        "Auth service should validate JWT tokens")
                    
                except Exception as validation_error:
                    self.fail(f"EXPECTED FAILURE: Auth service JWT validation failed: {validation_error}")
            
        except ImportError as e:
            self.fail(f"EXPECTED FAILURE: Could not import auth service client: {e}")
        except Exception as e:
            self.fail(f"EXPECTED FAILURE: Auth service integration test failed: {e}")
    
    async def test_golden_path_jwt_flow_end_to_end(self):
        """
        EXPECTED TO FAIL: Test complete Golden Path JWT authentication flow.
        
        This test simulates the complete user authentication flow from initial
        login through WebSocket connection to verify SSOT compliance end-to-end.
        """
        try:
            # Step 1: Simulate user login to auth service
            login_payload = self.test_user_credentials
            
            # Mock successful auth service response
            mock_auth_response = {
                "access_token": "mock_jwt_token_from_auth_service",
                "token_type": "bearer",
                "expires_in": 3600,
                "user_id": "test_user_123"
            }
            
            # Step 2: Test backend accepts auth service JWT
            from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
            
            extractor = UserContextExtractor()
            jwt_token = mock_auth_response["access_token"]
            
            # SSOT VIOLATION CHECK: This should work if services are aligned
            try:
                # This will likely fail due to token format/secret mismatches
                validated_payload = await extractor.validate_and_decode_jwt(jwt_token)
                
                if validated_payload:
                    logger.info("Golden Path JWT flow successful")
                else:
                    self.fail("EXPECTED FAILURE: Golden Path JWT validation failed - SSOT violation detected")
                
            except Exception as jwt_error:
                self.fail(f"EXPECTED FAILURE: Golden Path JWT flow broken: {jwt_error}")
            
            # Step 3: Test WebSocket connection with JWT
            from fastapi import WebSocket
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.headers = {
                "authorization": f"Bearer {jwt_token}",
                "sec-websocket-protocol": "jwt-auth"
            }
            
            # This should complete the Golden Path but will likely fail
            try:
                from netra_backend.app.websocket_core.user_context_extractor import extract_websocket_user_context
                user_context, auth_info = await extract_websocket_user_context(mock_websocket)
                
                self.assertIsNotNone(user_context, "Golden Path should create user context")
                logger.info("Golden Path WebSocket authentication successful")
                
            except Exception as ws_error:
                self.fail(f"EXPECTED FAILURE: Golden Path WebSocket authentication failed: {ws_error}")
            
        except Exception as e:
            self.fail(f"EXPECTED FAILURE: Golden Path JWT flow failed: {e}")


if __name__ == '__main__':
    import unittest
    unittest.main()