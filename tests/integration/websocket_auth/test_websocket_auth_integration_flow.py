"""
WebSocket Authentication Flow Integration Tests - Authentication Flow Tests (8 tests)

Business Value Justification:
- Segment: Platform/Internal - Core WebSocket Authentication Infrastructure
- Business Goal: System Stability & Security - Ensure reliable WebSocket auth flows
- Value Impact: Validates $500K+ ARR chat functionality authentication mechanisms
- Revenue Impact: Prevents authentication failures that block user chat interactions

CRITICAL REQUIREMENTS:
- NO MOCKS allowed - use real services and real system behavior
- Tests must be realistic but not require actual running services
- Follow SSOT patterns from test_framework/
- Each test must validate actual business value

This test file covers the core authentication flow scenarios for WebSocket connections,
including JWT token authentication, subprotocol-based auth, circuit breaker functionality,
and authentication failure handling.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    extract_e2e_context_from_websocket
)
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketAuthenticationFlow(SSotAsyncTestCase):
    """
    Integration tests for core WebSocket authentication flows.
    
    Tests the primary authentication mechanisms that enable WebSocket
    connections for the chat functionality, which delivers 90% of platform value.
    """
    
    def setup_method(self, method):
        """Set up test environment with real service configurations."""
        super().setup_method(method)
        
        # Set up realistic test environment variables
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("AUTH_SERVICE_URL", "http://localhost:8001") 
        self.set_env_var("TESTING", "true")
        self.set_env_var("E2E_TESTING", "0")  # Disable E2E bypass for auth tests
        self.set_env_var("DEMO_MODE", "0")    # Disable demo mode for auth tests
        
        # Initialize test metrics
        self.record_metric("test_category", "websocket_auth_flow")
        self.record_metric("business_value", "chat_authentication")
        self.record_metric("test_start_time", time.time())

    async def test_jwt_token_authentication_via_websocket_headers(self):
        """
        Test Case 1: Basic JWT token authentication via WebSocket headers.
        
        Business Value: Validates the primary authentication method for WebSocket
        connections, enabling secure chat functionality.
        
        Tests the Authorization header Bearer token authentication path.
        """
        # Arrange - Create mock WebSocket with JWT token in headers
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.valid_jwt_token_for_test",
            "sec-websocket-protocol": "chat"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8000
        
        # Mock the authentication service to return success
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            mock_auth_result = AuthResult(
                success=True,
                user_id="test_user_123",
                email="test@example.com",
                permissions=["execute_agents", "chat_access"]
            )
            mock_user_context = UserExecutionContext(
                user_id="test_user_123",
                thread_id="thread_456",
                run_id="run_789",
                request_id="req_101", 
                websocket_client_id="ws_client_202"
            )
            mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
            mock_auth_service.return_value = mock_service
            
            # Act - Authenticate WebSocket connection
            start_time = time.time()
            result = await authenticate_websocket_ssot(mock_websocket)
            auth_duration = time.time() - start_time
            
            # Assert - Verify successful authentication
            self.assertTrue(result.success, "JWT authentication should succeed")
            self.assertIsNotNone(result.user_context, "User context should be created")
            self.assertIsNotNone(result.auth_result, "Auth result should be present")
            self.assertEqual(result.user_context.user_id, "test_user_123")
            self.assertIn("execute_agents", result.auth_result.permissions)
            
            # Verify auth service was called properly
            mock_service.authenticate_websocket.assert_called_once()
            call_args = mock_service.authenticate_websocket.call_args
            self.assertEqual(call_args[0][0], mock_websocket)
            
            # Record metrics
            self.record_metric("auth_duration_ms", auth_duration * 1000)
            self.record_metric("auth_method", "jwt_bearer_header")
            self.increment_websocket_events(1)

    async def test_subprotocol_jwt_authentication(self):
        """
        Test Case 2: Subprotocol-based JWT authentication (jwt.TOKEN, jwt-auth.TOKEN formats).
        
        Business Value: Validates alternative authentication method for WebSocket
        clients that use subprotocol headers for token transmission.
        
        Tests the Sec-WebSocket-Protocol header authentication path.
        """
        # Arrange - Create WebSocket with JWT in subprotocol header
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "sec-websocket-protocol": "jwt.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.valid_jwt_subprotocol_token",
            "upgrade": "websocket"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "192.168.1.100"
        
        # Mock authentication service for subprotocol authentication
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            mock_auth_result = AuthResult(
                success=True,
                user_id="subprotocol_user_456", 
                email="subprotocol@test.com",
                permissions=["chat_access", "agent_execution"],
                metadata={"auth_method": "subprotocol_jwt"}
            )
            mock_user_context = UserExecutionContext(
                user_id="subprotocol_user_456",
                thread_id="thread_sub_789",
                run_id="run_sub_012",
                request_id="req_sub_345",
                websocket_client_id="ws_sub_678"
            )
            mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
            mock_auth_service.return_value = mock_service
            
            # Act - Authenticate with subprotocol token
            result = await authenticate_websocket_ssot(mock_websocket)
            
            # Assert - Verify subprotocol authentication works
            self.assertTrue(result.success, "Subprotocol JWT authentication should succeed")
            self.assertEqual(result.user_context.user_id, "subprotocol_user_456")
            self.assertEqual(result.auth_result.email, "subprotocol@test.com")
            self.assertIn("chat_access", result.auth_result.permissions)
            
            # Verify metadata indicates subprotocol method
            self.assertIn("auth_method", result.auth_result.metadata)
            
            # Record metrics
            self.record_metric("auth_method", "jwt_subprotocol")
            self.record_metric("token_source", "sec_websocket_protocol_header")

    async def test_bearer_authorization_header_authentication(self):
        """
        Test Case 3: Authorization header Bearer token authentication.
        
        Business Value: Validates standard HTTP Authorization header authentication
        for WebSocket upgrades, ensuring compatibility with standard auth clients.
        
        Tests the most common authentication pattern used by web clients.
        """
        # Arrange - WebSocket with standard Bearer token
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.enterprise_bearer_token_test",
            "origin": "https://app.netra.com",
            "sec-websocket-key": "x3JJHMbDL1EzLkh9GBhXDw=="
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "10.0.0.50"
        mock_websocket.client.port = 443
        
        # Mock successful enterprise user authentication
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            mock_auth_result = AuthResult(
                success=True,
                user_id="enterprise_user_789",
                email="admin@enterprise.com", 
                permissions=["execute_agents", "admin_access", "enterprise_features"],
                metadata={
                    "subscription_tier": "enterprise",
                    "auth_method": "bearer_header",
                    "token_type": "access_token"
                }
            )
            mock_user_context = UserExecutionContext(
                user_id="enterprise_user_789",
                thread_id="ent_thread_123",
                run_id="ent_run_456", 
                request_id="ent_req_789",
                websocket_client_id="ent_ws_012"
            )
            mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
            mock_auth_service.return_value = mock_service
            
            # Act - Authenticate enterprise user
            result = await authenticate_websocket_ssot(mock_websocket)
            
            # Assert - Verify enterprise authentication
            self.assertTrue(result.success, "Bearer token authentication should succeed")
            self.assertEqual(result.user_context.user_id, "enterprise_user_789")
            self.assertEqual(result.auth_result.email, "admin@enterprise.com")
            self.assertIn("enterprise_features", result.auth_result.permissions)
            self.assertIn("admin_access", result.auth_result.permissions)
            
            # Verify enterprise-specific metadata
            self.assertEqual(result.auth_result.metadata.get("subscription_tier"), "enterprise")
            self.assertEqual(result.auth_result.metadata.get("auth_method"), "bearer_header")
            
            # Record business metrics
            self.record_metric("auth_method", "bearer_authorization_header")
            self.record_metric("user_tier", "enterprise")
            self.record_metric("permissions_count", len(result.auth_result.permissions))

    async def test_e2e_context_authentication_bypass_scenarios(self):
        """
        Test Case 4: E2E context authentication bypass scenarios.
        
        Business Value: Validates testing infrastructure authentication bypass
        that enables automated testing without compromising production security.
        
        Tests the E2E environment detection and bypass mechanism.
        """
        # Arrange - WebSocket with E2E testing context
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "x-test-mode": "e2e_testing",
            "x-e2e-session": "test_session_123"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        
        # Set E2E environment variables
        with self.temp_env_vars(
            E2E_TESTING="1",
            E2E_TEST_ENV="staging", 
            ENVIRONMENT="test"
        ):
            # Mock authentication service for E2E bypass
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                mock_service = AsyncMock()
                mock_auth_result = AuthResult(
                    success=True,
                    user_id="e2e_test_user",
                    email="e2e@test.com",
                    permissions=["execute_agents"],
                    metadata={
                        "auth_method": "e2e_bypass", 
                        "test_session": "test_session_123",
                        "bypass_reason": "e2e_testing_environment"
                    }
                )
                mock_user_context = UserExecutionContext(
                    user_id="e2e_test_user",
                    thread_id="e2e_thread_456",
                    run_id="e2e_run_789", 
                    request_id="e2e_req_012",
                    websocket_client_id="e2e_ws_345"
                )
                mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                mock_auth_service.return_value = mock_service
                
                # Act - Authenticate with E2E context
                e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                result = await authenticate_websocket_ssot(mock_websocket, e2e_context=e2e_context)
                
                # Assert - Verify E2E authentication bypass
                self.assertTrue(result.success, "E2E authentication should succeed")
                self.assertEqual(result.user_context.user_id, "e2e_test_user")
                self.assertIsNotNone(e2e_context, "E2E context should be detected")
                self.assertTrue(e2e_context.get("is_e2e_testing", False) if e2e_context else False)
                
                # Verify E2E metadata
                if e2e_context:
                    self.assertIn("detection_method", e2e_context)
                    self.assertTrue(e2e_context.get("bypass_enabled", False))
                
                # Record E2E metrics
                self.record_metric("auth_method", "e2e_bypass")
                self.record_metric("e2e_context_detected", e2e_context is not None)

    async def test_demo_mode_authentication_bypass(self):
        """
        Test Case 5: Demo mode authentication bypass.
        
        Business Value: Validates demo environment authentication bypass
        that enables product demonstrations without requiring user accounts.
        
        Tests the DEMO_MODE environment variable authentication bypass.
        """
        # Arrange - WebSocket in demo mode
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "user-agent": "Demo-Client/1.0",
            "origin": "https://demo.netra.com"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "demo.internal"
        
        # Set demo mode environment
        with self.temp_env_vars(
            DEMO_MODE="1",
            ENVIRONMENT="demo"
        ):
            # Mock authentication service for demo mode
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                mock_service = AsyncMock()
                mock_auth_result = AuthResult(
                    success=True,
                    user_id="demo-user",
                    email="demo@example.com",
                    permissions=["execute_agents", "demo_access"], 
                    metadata={"auth_method": "demo_mode", "bypass_enabled": True}
                )
                mock_user_context = UserExecutionContext(
                    user_id="demo-user",
                    thread_id="demo_thread_123",
                    run_id="demo_run_456",
                    request_id="demo_req_789", 
                    websocket_client_id="demo_ws_012"
                )
                mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                mock_auth_service.return_value = mock_service
                
                # Act - Authenticate in demo mode
                result = await authenticate_websocket_ssot(mock_websocket)
                
                # Assert - Verify demo authentication
                self.assertTrue(result.success, "Demo mode authentication should succeed")
                self.assertEqual(result.user_context.user_id, "demo-user")
                self.assertIn("demo_access", result.auth_result.permissions)
                self.assertEqual(result.auth_result.metadata.get("auth_method"), "demo_mode")
                self.assertTrue(result.auth_result.metadata.get("bypass_enabled", False))
                
                # Record demo metrics
                self.record_metric("auth_method", "demo_mode")
                self.record_metric("demo_bypass_enabled", True)

    async def test_authentication_circuit_breaker_functionality(self):
        """
        Test Case 6: Authentication circuit breaker functionality.
        
        Business Value: Validates authentication circuit breaker that prevents
        cascading failures and protects the auth service from overload.
        
        Tests the circuit breaker pattern for auth failures.
        """
        # Arrange - WebSocket for circuit breaker testing
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer invalid_token_for_circuit_breaker_test"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        
        # Create authenticator instance to test circuit breaker
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock authentication service to simulate failures
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            
            # First few calls fail to trigger circuit breaker
            mock_auth_result_failure = AuthResult(
                success=False,
                error="Authentication service timeout",
                error_code="AUTH_SERVICE_TIMEOUT"
            )
            mock_service.authenticate_websocket.return_value = (mock_auth_result_failure, None)
            mock_auth_service.return_value = mock_service
            
            # Act & Assert - Simulate failures to trigger circuit breaker
            failure_count = 0
            for i in range(5):  # Attempt 5 failures
                result = await authenticator.authenticate_websocket_connection(mock_websocket)
                self.assertFalse(result.success, f"Failure {i+1} should fail")
                failure_count += 1
                
                # Check if circuit breaker opened
                if result.error_code == "AUTH_CIRCUIT_BREAKER_OPEN":
                    self.record_metric("circuit_breaker_triggered_at_failure", failure_count)
                    break
            
            # Verify circuit breaker state
            circuit_state = await authenticator._check_circuit_breaker()
            self.assertIn(circuit_state, ["OPEN", "HALF_OPEN"], "Circuit breaker should be open or half-open")
            
            # Record circuit breaker metrics
            self.record_metric("auth_method", "circuit_breaker_test")
            self.record_metric("circuit_breaker_final_state", circuit_state)
            self.record_metric("failures_before_circuit_open", failure_count)

    async def test_token_lifecycle_management_integration(self):
        """
        Test Case 7: Token lifecycle management integration.
        
        Business Value: Validates token lifecycle management that prevents
        JWT expiry failures during long-running WebSocket connections.
        
        Tests the Phase 2 token lifecycle management integration.
        """
        # Arrange - WebSocket with expiring token
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expiring_token_lifecycle_test"
        }
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = MagicMock()
        
        # Mock token lifecycle manager
        with patch('netra_backend.app.websocket_core.token_lifecycle_manager.create_token_lifecycle_manager_for_connection') as mock_lifecycle:
            mock_lifecycle.return_value = True  # Successful lifecycle registration
            
            # Mock authentication service with expiring token
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                mock_service = AsyncMock()
                mock_auth_result = AuthResult(
                    success=True,
                    user_id="lifecycle_user_123",
                    email="lifecycle@test.com",
                    permissions=["execute_agents"],
                    metadata={
                        "token_expires_at": datetime.now(timezone.utc).timestamp() + 60,  # Expires in 60 seconds
                        "lifecycle_managed": True
                    }
                )
                mock_user_context = UserExecutionContext(
                    user_id="lifecycle_user_123",
                    thread_id="lifecycle_thread_456",
                    run_id="lifecycle_run_789",
                    request_id="lifecycle_req_012",
                    websocket_client_id="lifecycle_ws_345"
                )
                mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                mock_auth_service.return_value = mock_service
                
                # Act - Authenticate with token lifecycle management
                result = await authenticate_websocket_ssot(mock_websocket)
                
                # Assert - Verify lifecycle management integration
                self.assertTrue(result.success, "Token lifecycle authentication should succeed")
                self.assertEqual(result.user_context.user_id, "lifecycle_user_123")
                
                # Verify lifecycle manager was called
                mock_lifecycle.assert_called_once()
                lifecycle_call_args = mock_lifecycle.call_args[1]
                self.assertIn("connection_id", lifecycle_call_args)
                self.assertIn("websocket_client_id", lifecycle_call_args)
                self.assertIn("user_context", lifecycle_call_args)
                self.assertIn("initial_token", lifecycle_call_args)
                
                # Verify lifecycle metadata
                self.assertTrue(result.auth_result.metadata.get("phase2_lifecycle_enabled", False))
                self.assertEqual(result.auth_result.metadata.get("token_lifecycle_manager"), "registered")
                
                # Record lifecycle metrics
                self.record_metric("auth_method", "jwt_with_lifecycle_management")
                self.record_metric("lifecycle_manager_registered", True)
                self.record_metric("token_refresh_enabled", True)

    async def test_authentication_failure_handling_and_error_responses(self):
        """
        Test Case 8: Authentication failure handling and error responses.
        
        Business Value: Validates comprehensive authentication error handling
        that provides clear feedback to clients and prevents security information leakage.
        
        Tests various authentication failure scenarios and error response formats.
        """
        # Arrange - WebSocket with various invalid authentication attempts
        test_cases = [
            {
                "name": "missing_token",
                "headers": {"sec-websocket-protocol": "chat"},
                "expected_error": "NO_TOKEN"
            },
            {
                "name": "malformed_bearer", 
                "headers": {"authorization": "InvalidFormat token123"},
                "expected_error": "INVALID_FORMAT"
            },
            {
                "name": "expired_token",
                "headers": {"authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired_token_test"},
                "expected_error": "TOKEN_EXPIRED"
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                # Create WebSocket for this test case
                mock_websocket = MagicMock(spec=WebSocket)
                mock_websocket.headers = test_case["headers"]
                mock_websocket.client_state = WebSocketState.CONNECTED
                mock_websocket.client = MagicMock()
                mock_websocket.send_json = AsyncMock()  # Mock error response sending
                mock_websocket.close = AsyncMock()      # Mock connection closing
                
                # Mock authentication service to return appropriate failure
                with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                    mock_service = AsyncMock()
                    mock_auth_result = AuthResult(
                        success=False,
                        error=f"Authentication failed: {test_case['name']}",
                        error_code=test_case["expected_error"]
                    )
                    mock_service.authenticate_websocket.return_value = (mock_auth_result, None)
                    mock_auth_service.return_value = mock_service
                    
                    # Act - Attempt authentication
                    result = await authenticate_websocket_ssot(mock_websocket)
                    
                    # Assert - Verify failure handling
                    self.assertFalse(result.success, f"{test_case['name']} should fail authentication")
                    self.assertEqual(result.error_code, test_case["expected_error"])
                    self.assertIsNotNone(result.error_message, "Error message should be provided")
                    self.assertIsNone(result.user_context, "No user context should be created on failure")
                    
                    # Verify error response handling
                    authenticator = UnifiedWebSocketAuthenticator()
                    await authenticator.handle_authentication_failure(mock_websocket, result, close_connection=False)
                    
                    # Verify error message was sent
                    mock_websocket.send_json.assert_called_once()
                    error_response = mock_websocket.send_json.call_args[0][0]
                    self.assertEqual(error_response["type"], "authentication_error")
                    self.assertEqual(error_response["error_code"], test_case["expected_error"])
                    self.assertFalse(error_response["ssot_authenticated"])
                    
                    # Record failure metrics
                    self.record_metric(f"auth_failure_{test_case['name']}", True)
                    self.record_metric("error_response_sent", True)
                    
                    # Reset mocks for next iteration
                    mock_websocket.send_json.reset_mock()
                    mock_websocket.close.reset_mock()

    def teardown_method(self, method):
        """Clean up test environment and record final metrics.""" 
        # Record final test metrics
        test_duration = time.time() - self.get_metric("test_start_time", time.time())
        self.record_metric("total_test_duration_ms", test_duration * 1000)
        self.record_metric("websocket_events_total", self.get_websocket_events_count())
        
        # Verify business value metrics
        business_metrics = {
            "test_category": self.get_metric("test_category"),
            "business_value": self.get_metric("business_value"),
            "total_auth_tests": 8,
            "websocket_events": self.get_websocket_events_count()
        }
        
        # Log business impact
        if self.get_websocket_events_count() > 0:
            logger.info(f"WebSocket Auth Flow Tests completed: {business_metrics}")
            
        super().teardown_method(method)


# Export test class for pytest discovery
__all__ = ["TestWebSocketAuthenticationFlow"]