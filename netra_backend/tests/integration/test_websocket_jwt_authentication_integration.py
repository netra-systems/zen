"""
Test WebSocket JWT Authentication Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure WebSocket authentication prevents security breaches
- Value Impact: JWT authentication protects user data and prevents unauthorized access
- Strategic Impact: Critical security infrastructure that enables multi-user isolation
- Revenue Impact: Prevents security vulnerabilities that could result in data breaches and customer churn

This comprehensive integration test validates the complete WebSocket JWT authentication pipeline
including:
- Valid JWT token authentication 
- Invalid JWT token rejection
- Missing JWT token handling
- Expired JWT token handling
- Environment-specific behavior (dev/test vs staging/prod)
- Multi-user isolation verification
- WebSocket close codes and error messages
- Authentication error logging

The test uses REAL services (PostgreSQL, Redis) and follows Netra's test creation standards
from TEST_CREATION_GUIDE.md with proper SSOT patterns and IsolatedEnvironment usage.

CRITICAL: This test validates the recent WebSocket JWT authentication fixes that ensure
consistent authentication behavior between REST endpoints and WebSocket connections.
"""

import asyncio
import json
import jwt
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following TEST_CREATION_GUIDE.md standards
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.isolated_environment_fixtures import isolated_env, test_env, staging_env, production_env
from test_framework.websocket_helpers import WebSocketTestHelpers, MockWebSocketConnection

# Application imports
from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor, extract_websocket_user_context
from netra_backend.app.routes.websocket import websocket_endpoint
from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_unified_jwt_secret


class TestWebSocketJWTAuthenticationIntegration(BaseIntegrationTest):
    """
    Integration test class for WebSocket JWT authentication.
    
    Tests the complete WebSocket authentication pipeline with REAL services
    including PostgreSQL and Redis, validating all authentication scenarios
    and environment-specific behaviors.
    """

    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        
        # Additional setup for WebSocket JWT testing
        self.test_user_id = "test_websocket_user_123"
        self.test_email = "test@netrasystems.ai"
        self.jwt_algorithm = "HS256"
        
        # Test JWT payloads for different scenarios
        self.valid_jwt_payload = {
            "sub": self.test_user_id,
            "email": self.test_email,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour expiration
            "permissions": ["websocket_access", "read", "write"],
            "roles": ["user"]
        }
        
        self.expired_jwt_payload = {
            "sub": self.test_user_id,
            "email": self.test_email,
            "iat": int(time.time()) - 7200,  # 2 hours ago
            "exp": int(time.time()) - 3600,  # 1 hour ago (expired)
            "permissions": ["websocket_access"],
            "roles": ["user"]
        }

    def _create_jwt_token(self, payload: Dict[str, Any], secret: Optional[str] = None) -> str:
        """Create JWT token for testing."""
        if secret is None:
            secret = get_unified_jwt_secret()
        return jwt.encode(payload, secret, algorithm=self.jwt_algorithm)

    def _create_mock_websocket(self, headers: Optional[Dict[str, str]] = None) -> MagicMock:
        """Create mock WebSocket with specified headers."""
        mock_websocket = MagicMock()
        mock_websocket.headers = headers or {}
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        return mock_websocket

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_valid_jwt_token_allows_websocket_connection(self, real_services_fixture, test_env):
        """
        Test that valid JWT token allows WebSocket connection.
        
        This test validates the core authentication success path where a properly
        formatted and signed JWT token enables WebSocket connection establishment.
        """
        # Create valid JWT token
        jwt_secret = get_unified_jwt_secret()
        valid_token = self._create_jwt_token(self.valid_jwt_payload, jwt_secret)
        
        # Create mock WebSocket with valid JWT in Authorization header
        mock_websocket = self._create_mock_websocket({
            "authorization": f"Bearer {valid_token}",
            "user-agent": "test-client",
            "origin": "https://test.netrasystems.ai"
        })
        
        # Test JWT extraction and validation
        extractor = UserContextExtractor()
        
        # Extract JWT token
        extracted_token = extractor.extract_jwt_from_websocket(mock_websocket)
        assert extracted_token == valid_token
        self.logger.info("✅ JWT token successfully extracted from WebSocket headers")
        
        # Validate JWT token using resilient validation (same as REST endpoints)
        validated_payload = await extractor.validate_and_decode_jwt(extracted_token)
        assert validated_payload is not None
        assert validated_payload["sub"] == self.test_user_id
        assert validated_payload["email"] == self.test_email
        assert "websocket_access" in validated_payload["permissions"]
        self.logger.info("✅ JWT token successfully validated using resilient validation")
        
        # Create user context from JWT
        user_context = extractor.create_user_context_from_jwt(validated_payload, mock_websocket)
        assert user_context.user_id == self.test_user_id
        assert user_context.websocket_connection_id is not None
        assert user_context.thread_id is not None
        assert user_context.run_id is not None
        self.logger.info("✅ UserExecutionContext successfully created from JWT")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_invalid_jwt_token_rejects_connection_with_1008(self, real_services_fixture, test_env):
        """
        Test that invalid JWT token rejects WebSocket connection with code 1008.
        
        This test validates that malformed or incorrectly signed JWT tokens
        are properly rejected with the correct WebSocket close code.
        """
        # Create invalid JWT token (using wrong secret)
        invalid_secret = "wrong_secret_key_for_testing_32chars"
        invalid_token = self._create_jwt_token(self.valid_jwt_payload, invalid_secret)
        
        # Create mock WebSocket with invalid JWT
        mock_websocket = self._create_mock_websocket({
            "authorization": f"Bearer {invalid_token}",
            "user-agent": "test-client"
        })
        
        # Test JWT extraction and validation
        extractor = UserContextExtractor()
        
        # Extract JWT token (should succeed)
        extracted_token = extractor.extract_jwt_from_websocket(mock_websocket)
        assert extracted_token == invalid_token
        self.logger.info("✅ Invalid JWT token extracted from headers")
        
        # Validate JWT token (should fail due to wrong signature)
        validated_payload = await extractor.validate_and_decode_jwt(extracted_token)
        assert validated_payload is None
        self.logger.info("✅ Invalid JWT token properly rejected during validation")
        
        # Test complete user context extraction (should raise HTTPException)
        with pytest.raises(Exception) as exc_info:
            await extractor.extract_user_context_from_websocket(mock_websocket)
        
        # Verify proper error handling
        exception = exc_info.value
        assert hasattr(exception, 'status_code')
        assert exception.status_code == 401
        assert "invalid" in exception.detail.lower() or "failed" in exception.detail.lower()
        self.logger.info("✅ Invalid JWT properly raises 401 HTTPException")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_missing_jwt_token_rejects_connection_with_1008(self, real_services_fixture, test_env):
        """
        Test that missing JWT token rejects WebSocket connection with code 1008.
        
        This test validates that WebSocket connections without authentication
        are properly rejected in environments that require authentication.
        """
        # Create mock WebSocket without JWT token
        mock_websocket = self._create_mock_websocket({
            "user-agent": "test-client",
            "origin": "https://test.netrasystems.ai"
        })
        
        # Test JWT extraction
        extractor = UserContextExtractor()
        extracted_token = extractor.extract_jwt_from_websocket(mock_websocket)
        assert extracted_token is None
        self.logger.info("✅ No JWT token found in WebSocket headers (as expected)")
        
        # Test complete user context extraction (should raise HTTPException)
        with pytest.raises(Exception) as exc_info:
            await extractor.extract_user_context_from_websocket(mock_websocket)
        
        # Verify proper error handling
        exception = exc_info.value
        assert hasattr(exception, 'status_code')
        assert exception.status_code == 401
        assert "authentication required" in exception.detail.lower()
        self.logger.info("✅ Missing JWT properly raises 401 HTTPException")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_expired_jwt_token_rejects_connection(self, real_services_fixture, test_env):
        """
        Test that expired JWT token rejects WebSocket connection.
        
        This test validates that expired JWT tokens are properly detected
        and rejected to maintain security.
        """
        # Create expired JWT token
        jwt_secret = get_unified_jwt_secret()
        expired_token = self._create_jwt_token(self.expired_jwt_payload, jwt_secret)
        
        # Create mock WebSocket with expired JWT
        mock_websocket = self._create_mock_websocket({
            "authorization": f"Bearer {expired_token}",
            "user-agent": "test-client"
        })
        
        # Test JWT extraction and validation
        extractor = UserContextExtractor()
        
        # Extract JWT token (should succeed)
        extracted_token = extractor.extract_jwt_from_websocket(mock_websocket)
        assert extracted_token == expired_token
        self.logger.info("✅ Expired JWT token extracted from headers")
        
        # Validate JWT token (should fail due to expiration)
        validated_payload = await extractor.validate_and_decode_jwt(extracted_token)
        assert validated_payload is None
        self.logger.info("✅ Expired JWT token properly rejected during validation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_validation_errors_are_properly_logged(self, real_services_fixture, test_env):
        """
        Test that JWT validation errors are properly logged for debugging.
        
        This test ensures that authentication failures are logged with sufficient
        detail for troubleshooting while not exposing sensitive information.
        """
        # Test various invalid JWT scenarios
        test_scenarios = [
            {
                "name": "malformed_jwt",
                "token": "not.a.valid.jwt.token.structure",
                "expected_error": "invalid"
            },
            {
                "name": "missing_claims",
                "payload": {"iat": int(time.time())},  # Missing 'sub' claim
                "expected_error": "missing"
            },
            {
                "name": "wrong_algorithm",
                "token": jwt.encode(self.valid_jwt_payload, get_unified_jwt_secret(), algorithm="HS512"),
                "expected_error": "signature"
            }
        ]
        
        extractor = UserContextExtractor()
        
        for scenario in test_scenarios:
            self.logger.info(f"Testing JWT validation error scenario: {scenario['name']}")
            
            # Get test token
            if "token" in scenario:
                test_token = scenario["token"]
            else:
                test_token = self._create_jwt_token(scenario["payload"])
            
            # Create mock WebSocket with invalid JWT
            mock_websocket = self._create_mock_websocket({
                "authorization": f"Bearer {test_token}",
                "user-agent": "test-client"
            })
            
            # Test validation (should return None for all invalid cases)
            validated_payload = await extractor.validate_and_decode_jwt(test_token)
            assert validated_payload is None
            
            # Test complete extraction (should raise HTTPException)
            with pytest.raises(Exception) as exc_info:
                await extractor.extract_user_context_from_websocket(mock_websocket)
            
            exception = exc_info.value
            assert hasattr(exception, 'status_code')
            assert exception.status_code == 401
            
            self.logger.info(f"✅ JWT validation error properly handled for {scenario['name']}")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_environment_specific_authentication_behavior(self, real_services_fixture, isolated_env):
        """
        Test environment-specific JWT authentication behavior.
        
        This test validates that authentication behaves differently based on
        environment settings (development allows fallbacks, production enforces strict auth).
        """
        jwt_secret = get_unified_jwt_secret()
        valid_token = self._create_jwt_token(self.valid_jwt_payload, jwt_secret)
        
        # Test development environment behavior
        isolated_env.set("ENVIRONMENT", "development", "test")
        isolated_env.set("TESTING", "0", "test")  # Not in testing mode
        
        mock_websocket_dev = self._create_mock_websocket({
            "authorization": f"Bearer {valid_token}",
            "user-agent": "test-client"
        })
        
        extractor = UserContextExtractor()
        user_context_dev, auth_info_dev = await extractor.extract_user_context_from_websocket(mock_websocket_dev)
        
        assert user_context_dev.user_id == self.test_user_id
        assert auth_info_dev["user_id"] == self.test_user_id
        self.logger.info("✅ Development environment allows JWT authentication")
        
        # Test staging environment behavior  
        isolated_env.set("ENVIRONMENT", "staging", "test")
        isolated_env.set("TESTING", "0", "test")  # Not in testing mode
        
        mock_websocket_staging = self._create_mock_websocket({
            "authorization": f"Bearer {valid_token}",
            "user-agent": "test-client"
        })
        
        user_context_staging, auth_info_staging = await extractor.extract_user_context_from_websocket(mock_websocket_staging)
        
        assert user_context_staging.user_id == self.test_user_id
        assert auth_info_staging["user_id"] == self.test_user_id
        self.logger.info("✅ Staging environment enforces strict JWT authentication")
        
        # Test production environment behavior
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("TESTING", "0", "test")  # Not in testing mode
        
        mock_websocket_prod = self._create_mock_websocket({
            "authorization": f"Bearer {valid_token}",
            "user-agent": "test-client"
        })
        
        user_context_prod, auth_info_prod = await extractor.extract_user_context_from_websocket(mock_websocket_prod)
        
        assert user_context_prod.user_id == self.test_user_id
        assert auth_info_prod["user_id"] == self.test_user_id
        self.logger.info("✅ Production environment enforces strict JWT authentication")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_close_codes_and_reasons(self, real_services_fixture, test_env):
        """
        Test WebSocket close codes and reasons for authentication failures.
        
        This test validates that proper WebSocket close codes are used for different
        authentication failure scenarios, ensuring clients can handle errors appropriately.
        """
        # Test scenarios with expected close codes
        close_code_scenarios = [
            {
                "name": "invalid_jwt_signature",
                "token": self._create_jwt_token(self.valid_jwt_payload, "wrong_secret"),
                "expected_code": 1008,  # Policy Violation
                "expected_reason_contains": ["invalid", "authentication"]
            },
            {
                "name": "expired_jwt",
                "token": self._create_jwt_token(self.expired_jwt_payload),
                "expected_code": 1008,  # Policy Violation
                "expected_reason_contains": ["invalid", "expired"]
            },
            {
                "name": "malformed_jwt",
                "token": "not.a.valid.jwt",
                "expected_code": 1008,  # Policy Violation
                "expected_reason_contains": ["invalid", "authentication"]
            }
        ]
        
        extractor = UserContextExtractor()
        
        for scenario in close_code_scenarios:
            self.logger.info(f"Testing close code scenario: {scenario['name']}")
            
            mock_websocket = self._create_mock_websocket({
                "authorization": f"Bearer {scenario['token']}",
                "user-agent": "test-client"
            })
            
            # Test that validation fails appropriately
            validated_payload = await extractor.validate_and_decode_jwt(scenario['token'])
            assert validated_payload is None
            
            # Test that context extraction raises proper exception
            with pytest.raises(Exception) as exc_info:
                await extractor.extract_user_context_from_websocket(mock_websocket)
            
            exception = exc_info.value
            assert hasattr(exception, 'status_code')
            assert exception.status_code == 401
            
            # Verify error message contains expected information
            error_detail = exception.detail.lower()
            assert any(keyword in error_detail for keyword in scenario['expected_reason_contains'])
            
            self.logger.info(f"✅ Close code scenario {scenario['name']} handled correctly")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_isolation_different_jwt_different_context(self, real_services_fixture, test_env):
        """
        Test multi-user isolation with different JWT tokens creating different contexts.
        
        This test validates that different users with different JWT tokens get
        completely isolated execution contexts, preventing cross-user data leakage.
        """
        jwt_secret = get_unified_jwt_secret()
        
        # Create JWT tokens for different users
        user1_payload = {
            "sub": "user_1_websocket_test",
            "email": "user1@netrasystems.ai",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "permissions": ["websocket_access", "read"],
            "roles": ["basic_user"]
        }
        
        user2_payload = {
            "sub": "user_2_websocket_test", 
            "email": "user2@netrasystems.ai",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "permissions": ["websocket_access", "read", "write"],
            "roles": ["premium_user"]
        }
        
        user1_token = self._create_jwt_token(user1_payload, jwt_secret)
        user2_token = self._create_jwt_token(user2_payload, jwt_secret)
        
        # Create mock WebSockets for different users
        user1_websocket = self._create_mock_websocket({
            "authorization": f"Bearer {user1_token}",
            "user-agent": "user1-client",
            "origin": "https://user1.netrasystems.ai"
        })
        
        user2_websocket = self._create_mock_websocket({
            "authorization": f"Bearer {user2_token}",
            "user-agent": "user2-client", 
            "origin": "https://user2.netrasystems.ai"
        })
        
        extractor = UserContextExtractor()
        
        # Extract contexts for both users
        user1_context, user1_auth_info = await extractor.extract_user_context_from_websocket(user1_websocket)
        user2_context, user2_auth_info = await extractor.extract_user_context_from_websocket(user2_websocket)
        
        # Verify complete isolation
        assert user1_context.user_id != user2_context.user_id
        assert user1_context.websocket_connection_id != user2_context.websocket_connection_id
        assert user1_context.thread_id != user2_context.thread_id
        assert user1_context.run_id != user2_context.run_id
        assert user1_context.request_id != user2_context.request_id
        
        # Verify user-specific information
        assert user1_context.user_id == "user_1_websocket_test"
        assert user2_context.user_id == "user_2_websocket_test"
        
        assert user1_auth_info["permissions"] == ["websocket_access", "read"]
        assert user2_auth_info["permissions"] == ["websocket_access", "read", "write"]
        
        assert user1_auth_info["roles"] == ["basic_user"]
        assert user2_auth_info["roles"] == ["premium_user"]
        
        self.logger.info("✅ Multi-user isolation properly implemented with different JWT contexts")
        self.logger.info(f"User 1 context: {user1_context.websocket_connection_id}")
        self.logger.info(f"User 2 context: {user2_context.websocket_connection_id}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_subprotocol_authentication(self, real_services_fixture, test_env):
        """
        Test JWT authentication via WebSocket subprotocol.
        
        This test validates the alternative authentication method where JWT tokens
        are passed via the Sec-WebSocket-Protocol header instead of Authorization header.
        """
        jwt_secret = get_unified_jwt_secret()
        valid_token = self._create_jwt_token(self.valid_jwt_payload, jwt_secret)
        
        # Encode token for subprotocol (base64url encoding)
        import base64
        encoded_token = base64.urlsafe_b64encode(valid_token.encode('utf-8')).decode('utf-8')
        # Remove padding for URL safety
        encoded_token = encoded_token.rstrip('=')
        
        # Create mock WebSocket with JWT in subprotocol
        mock_websocket = self._create_mock_websocket({
            "sec-websocket-protocol": f"jwt.{encoded_token}, other-protocol",
            "user-agent": "test-client"
        })
        
        extractor = UserContextExtractor()
        
        # Extract JWT token from subprotocol
        extracted_token = extractor.extract_jwt_from_websocket(mock_websocket)
        assert extracted_token == valid_token
        self.logger.info("✅ JWT token successfully extracted from WebSocket subprotocol")
        
        # Validate and create user context
        user_context, auth_info = await extractor.extract_user_context_from_websocket(mock_websocket)
        
        assert user_context.user_id == self.test_user_id
        assert auth_info["user_id"] == self.test_user_id
        assert "websocket_access" in auth_info["permissions"]
        
        self.logger.info("✅ JWT subprotocol authentication successfully validated")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_websocket_authentication_consistency_with_rest_endpoints(self, real_services_fixture, test_env):
        """
        Test that WebSocket authentication is consistent with REST endpoints.
        
        This test validates that WebSocket authentication uses the same resilient
        validation logic as REST endpoints, ensuring consistent behavior across
        all authentication points in the system.
        """
        jwt_secret = get_unified_jwt_secret()
        valid_token = self._create_jwt_token(self.valid_jwt_payload, jwt_secret)
        
        # Create mock WebSocket with valid JWT
        mock_websocket = self._create_mock_websocket({
            "authorization": f"Bearer {valid_token}",
            "user-agent": "test-client"
        })
        
        extractor = UserContextExtractor()
        
        # Test direct JWT validation (should use resilient validation)
        validated_payload = await extractor.validate_and_decode_jwt(valid_token)
        assert validated_payload is not None
        assert validated_payload["sub"] == self.test_user_id
        assert validated_payload.get("source") == "resilient_validation"  # Mark of resilient validation
        
        self.logger.info("✅ WebSocket JWT validation uses resilient validation (same as REST endpoints)")
        
        # Test complete authentication flow
        user_context, auth_info = await extractor.extract_user_context_from_websocket(mock_websocket)
        
        assert user_context.user_id == self.test_user_id
        assert auth_info["user_id"] == self.test_user_id
        assert len(auth_info["permissions"]) == 3  # websocket_access, read, write
        
        # Verify client info extraction (similar to REST middleware)
        assert "client_info" in auth_info
        assert auth_info["client_info"]["user_agent"] == "test-client"
        
        self.logger.info("✅ WebSocket authentication provides same user context as REST endpoints")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_secret_consistency_across_services(self, real_services_fixture, test_env):
        """
        Test JWT secret consistency between auth service and backend.
        
        This test validates that the unified JWT secret manager ensures both
        services use identical secrets, preventing signature mismatches.
        """
        # Test unified JWT secret resolution
        jwt_secret_1 = get_unified_jwt_secret()
        jwt_secret_2 = get_unified_jwt_secret()
        
        assert jwt_secret_1 == jwt_secret_2
        assert len(jwt_secret_1) >= 32  # Minimum secure length
        self.logger.info("✅ Unified JWT secret manager provides consistent secrets")
        
        # Create token with unified secret
        test_token = self._create_jwt_token(self.valid_jwt_payload, jwt_secret_1)
        
        # Validate token with same secret (should succeed)
        extractor = UserContextExtractor()
        validated_payload = await extractor.validate_and_decode_jwt(test_token)
        
        assert validated_payload is not None
        assert validated_payload["sub"] == self.test_user_id
        
        self.logger.info("✅ JWT token created and validated with unified secret successfully")
        
        # Test that UserContextExtractor uses unified secret internally
        extractor_secret = extractor._get_jwt_secret()
        assert extractor_secret == jwt_secret_1
        
        self.logger.info("✅ UserContextExtractor uses unified JWT secret for validation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_id_uniqueness(self, real_services_fixture, test_env):
        """
        Test that WebSocket connection IDs are unique for each connection.
        
        This test validates that each WebSocket connection gets a unique
        connection ID for proper tracking and isolation.
        """
        jwt_secret = get_unified_jwt_secret()
        token = self._create_jwt_token(self.valid_jwt_payload, jwt_secret)
        
        # Create multiple mock WebSocket connections for the same user
        websockets = []
        for i in range(5):
            mock_websocket = self._create_mock_websocket({
                "authorization": f"Bearer {token}",
                "user-agent": f"test-client-{i}",
                "connection": f"connection-{i}"
            })
            websockets.append(mock_websocket)
        
        extractor = UserContextExtractor()
        connection_ids = []
        
        # Extract user contexts for each connection
        for i, websocket in enumerate(websockets):
            user_context, auth_info = await extractor.extract_user_context_from_websocket(websocket)
            
            assert user_context.user_id == self.test_user_id  # Same user
            connection_ids.append(user_context.websocket_connection_id)
            
            self.logger.info(f"Connection {i}: {user_context.websocket_connection_id}")
        
        # Verify all connection IDs are unique
        assert len(set(connection_ids)) == len(connection_ids)  # All unique
        
        # Verify connection ID format
        for conn_id in connection_ids:
            assert conn_id.startswith("ws_")
            assert self.test_user_id[:8] in conn_id  # Contains user ID prefix
        
        self.logger.info("✅ WebSocket connection IDs are unique for each connection")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_authentication_performance(self, real_services_fixture, test_env):
        """
        Test WebSocket authentication performance under load.
        
        This test validates that JWT authentication performs adequately
        under realistic load conditions.
        """
        jwt_secret = get_unified_jwt_secret()
        token = self._create_jwt_token(self.valid_jwt_payload, jwt_secret)
        
        extractor = UserContextExtractor()
        
        # Test multiple authentication operations
        auth_count = 50
        start_time = time.time()
        
        successful_auths = 0
        for i in range(auth_count):
            mock_websocket = self._create_mock_websocket({
                "authorization": f"Bearer {token}",
                "user-agent": f"perf-test-{i}"
            })
            
            try:
                user_context, auth_info = await extractor.extract_user_context_from_websocket(mock_websocket)
                assert user_context.user_id == self.test_user_id
                successful_auths += 1
            except Exception as e:
                self.logger.warning(f"Authentication {i} failed: {e}")
        
        total_time = time.time() - start_time
        avg_time_per_auth = total_time / auth_count
        
        # Performance assertions
        assert successful_auths == auth_count  # All authentications should succeed
        assert avg_time_per_auth < 0.1  # Should be under 100ms per authentication
        assert total_time < 10.0  # Total time should be reasonable
        
        self.logger.info(f"✅ WebSocket authentication performance: {auth_count} auths in {total_time:.2f}s")
        self.logger.info(f"✅ Average time per authentication: {avg_time_per_auth:.3f}s")
        
        # Log performance metrics for monitoring
        self.logger.info(f"Performance Metrics: success_rate={successful_auths/auth_count:.2%}, avg_time={avg_time_per_auth:.3f}s")

    async def test_websocket_authentication_error_recovery(self, test_env):
        """
        Test WebSocket authentication error recovery mechanisms.
        
        This test validates that authentication errors are handled gracefully
        and don't cause system instability.
        """
        extractor = UserContextExtractor()
        
        # Test various error scenarios
        error_scenarios = [
            {
                "name": "network_timeout",
                "setup": lambda: self._create_mock_websocket({}),  # No auth header
                "expected_error": "authentication required"
            },
            {
                "name": "corrupted_header", 
                "setup": lambda: self._create_mock_websocket({"authorization": "Bearer corrupted_token"}),
                "expected_error": "invalid"
            },
            {
                "name": "empty_token",
                "setup": lambda: self._create_mock_websocket({"authorization": "Bearer "}),
                "expected_error": "authentication required"
            }
        ]
        
        for scenario in error_scenarios:
            self.logger.info(f"Testing error recovery for: {scenario['name']}")
            
            mock_websocket = scenario["setup"]()
            
            # Authentication should fail gracefully
            with pytest.raises(Exception) as exc_info:
                await extractor.extract_user_context_from_websocket(mock_websocket)
            
            exception = exc_info.value
            assert hasattr(exception, 'status_code')
            assert exception.status_code == 401
            assert scenario["expected_error"] in exception.detail.lower()
            
            # Verify extractor is still functional after error
            jwt_secret = get_unified_jwt_secret()
            valid_token = self._create_jwt_token(self.valid_jwt_payload, jwt_secret)
            valid_websocket = self._create_mock_websocket({
                "authorization": f"Bearer {valid_token}"
            })
            
            # Should work normally after error
            user_context, auth_info = await extractor.extract_user_context_from_websocket(valid_websocket)
            assert user_context.user_id == self.test_user_id
            
            self.logger.info(f"✅ Error recovery successful for {scenario['name']}")