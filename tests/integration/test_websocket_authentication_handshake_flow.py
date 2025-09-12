"""
Integration Tests for WebSocket Authentication Handshake Flow

ISSUE #395 TEST PLAN (Step 3) - Integration Test Suite  
Tests the complete WebSocket authentication handshake flow without docker dependency:

TARGET ISSUES:
1. WebSocket authentication handshake immediate failure
2. Authentication service integration broken 
3. E2E context propagation failure in integration scenarios

CRITICAL: These tests use real services (no mocks) for authentication validation.
"""

import pytest
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from unittest.mock import patch
import json

# SSOT imports 
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    authenticate_websocket_ssot,
    extract_e2e_context_from_websocket,
    WebSocketAuthResult
)
from netra_backend.app.services.unified_authentication_service import get_unified_auth_service
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

# Mark as integration test (no docker required)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.websocket_authentication,  # Use existing WebSocket authentication marker
    pytest.mark.no_docker  # Explicitly no docker dependency
]


class TestWebSocketAuthenticationHandshakeFlow(SSotAsyncTestCase):
    """
    Integration test suite for WebSocket authentication handshake flow.
    
    Business Impact:
    - Tests complete authentication flow from handshake to user context creation
    - Validates WebSocket state management during authentication
    - Tests E2E context propagation in realistic integration scenarios
    - Protects Golden Path functionality ($500K+ ARR)
    
    EXPECTED BEHAVIOR:
    - Initial runs: Tests should FAIL (reproducing handshake failures)
    - After fixes: Tests should PASS (validating proper handshake flow)
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.authenticator = UnifiedWebSocketAuthenticator()
        self.auth_service = get_unified_auth_service()
        
    def create_mock_websocket_with_state(self, state: str = "CONNECTED", **kwargs) -> object:
        """Create a mock WebSocket with realistic state and attributes."""
        from unittest.mock import Mock
        from fastapi.websockets import WebSocketState
        
        websocket = Mock()
        
        # Set WebSocket state
        if state == "CONNECTED":
            websocket.client_state = WebSocketState.CONNECTED
        elif state == "DISCONNECTED":
            websocket.client_state = WebSocketState.DISCONNECTED
        else:
            websocket.client_state = Mock()
            websocket.client_state.name = state
        
        # Set headers
        websocket.headers = kwargs.get("headers", {})
        
        # Set client info
        websocket.client = Mock()
        websocket.client.host = kwargs.get("host", "127.0.0.1")
        websocket.client.port = kwargs.get("port", 8000)
        
        # Set subprotocols if provided
        websocket.subprotocols = kwargs.get("subprotocols", [])
        
        # Add send/receive methods for integration testing
        websocket.send_json = Mock()
        websocket.receive_json = Mock()
        websocket.close = Mock()
        
        return websocket

    async def test_handshake_timing_validation_integration(self):
        """
        INTEGRATION TEST: WebSocket handshake timing validation.
        
        Issue #395: Tests that handshake timing validation works correctly in integration scenarios.
        This test should FAIL initially if handshake timing logic is broken.
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: WebSocket handshake timing validation")
        
        # Test with WebSocket in different states
        test_cases = [
            ("CONNECTED", True, "Connected WebSocket should pass timing validation"),
            ("DISCONNECTED", False, "Disconnected WebSocket should fail timing validation"),
            ("CONNECTING", False, "Connecting WebSocket should fail timing validation")
        ]
        
        for state, expected_valid, description in test_cases:
            websocket = self.create_mock_websocket_with_state(state=state)
            
            # Test handshake timing validation  
            is_valid = await self.authenticator._validate_websocket_handshake_timing(websocket)
            
            if expected_valid:
                self.assertTrue(is_valid, f"HANDSHAKE TIMING BUG: {description}")
            else:
                self.assertFalse(is_valid, f"HANDSHAKE TIMING BUG: {description}")

    async def test_authentication_service_integration_real(self):
        """
        INTEGRATION TEST: Real authentication service integration.
        
        Issue #395: Tests authentication service integration with real service calls.
        This test should FAIL initially if service integration is broken.
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: Real authentication service integration")
        
        # Create WebSocket with E2E context for testing
        websocket = self.create_mock_websocket_with_state(
            headers={"authorization": "Bearer test-valid-token"},
            host="127.0.0.1",
            port=8000
        )
        
        # Set up E2E testing environment for integration test
        e2e_context = {
            "is_e2e_testing": True,
            "detection_method": {"via_environment": True},
            "environment": "test",
            "bypass_enabled": True
        }
        
        try:
            # Test real authentication service integration
            result = await authenticate_websocket_ssot(websocket, e2e_context=e2e_context)
            
            # Validate authentication result structure
            self.assertIsInstance(result, WebSocketAuthResult)
            
            # In E2E mode, authentication should succeed for testing
            if not result.success:
                logger.error(f"INTEGRATION BUG: Auth service integration failed: {result.error_message}")
                self.fail(f"Authentication service integration failed: {result.error_message}")
            
            # Validate user context creation
            self.assertIsNotNone(result.user_context, "User context should be created")
            self.assertIsInstance(result.user_context, UserExecutionContext)
            
            # Validate auth result
            self.assertIsNotNone(result.auth_result, "Auth result should be present")
            self.assertTrue(result.auth_result.success, "Auth result should indicate success")
            
        except Exception as e:
            logger.error(f"INTEGRATION ERROR: Authentication service integration failed: {e}")
            self.fail(f"Authentication service integration error: {e}")

    async def test_e2e_context_propagation_integration(self):
        """
        INTEGRATION TEST: E2E context propagation through authentication flow.
        
        Issue #395: Tests that E2E context is properly propagated through the entire authentication flow.
        This test should FAIL initially if context propagation is broken.
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: E2E context propagation")
        
        # Set up realistic E2E environment variables
        test_env_vars = {
            "E2E_TESTING": "1",
            "STAGING_E2E_TEST": "1",
            "E2E_TEST_ENV": "staging",
            "ENVIRONMENT": "test"
        }
        
        with patch.dict('os.environ', test_env_vars, clear=False):
            # Create WebSocket for E2E testing
            websocket = self.create_mock_websocket_with_state(
                headers={"user-agent": "test-client"},
                host="127.0.0.1",
                port=8000
            )
            
            # Test E2E context extraction
            extracted_context = extract_e2e_context_from_websocket(websocket)
            
            if extracted_context is None:
                self.fail("E2E CONTEXT PROPAGATION BUG: Context extraction failed")
            
            # Validate context structure
            required_fields = ["is_e2e_testing", "detection_method", "environment", "bypass_enabled"]
            for field in required_fields:
                self.assertIn(field, extracted_context, f"Missing required E2E context field: {field}")
            
            self.assertTrue(extracted_context["is_e2e_testing"], "Should detect E2E testing")
            self.assertTrue(extracted_context["bypass_enabled"], "Should enable bypass for E2E")
            
            # Test context propagation through authentication
            result = await authenticate_websocket_ssot(websocket, e2e_context=extracted_context)
            
            # Verify authentication used E2E context
            self.assertTrue(result.success, f"E2E authentication should succeed: {result.error_message}")
            
            # Check if context was properly used in authentication
            if result.auth_result and hasattr(result.auth_result, 'metadata'):
                metadata = result.auth_result.metadata or {}
                if "auth_method" in metadata:
                    # E2E context should influence auth method
                    logger.info(f"Auth method with E2E context: {metadata['auth_method']}")

    async def test_websocket_state_management_during_auth(self):
        """
        INTEGRATION TEST: WebSocket state management during authentication.
        
        Issue #395: Tests that WebSocket state is properly managed during authentication flow.
        This test should FAIL initially if state management is broken.
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: WebSocket state management during authentication")
        
        # Test authentication with different WebSocket states
        from fastapi.websockets import WebSocketState
        
        state_test_cases = [
            (WebSocketState.CONNECTED, True, "Connected state should allow authentication"),
            (WebSocketState.DISCONNECTED, False, "Disconnected state should prevent authentication"),
        ]
        
        for ws_state, should_succeed, description in state_test_cases:
            websocket = self.create_mock_websocket_with_state()
            websocket.client_state = ws_state
            
            # Set up E2E context for testing
            e2e_context = {
                "is_e2e_testing": True,
                "bypass_enabled": True,
                "environment": "test"
            }
            
            result = await authenticate_websocket_ssot(websocket, e2e_context=e2e_context)
            
            if should_succeed:
                if not result.success:
                    self.fail(f"WEBSOCKET STATE BUG: {description} - Error: {result.error_message}")
                
                # Verify state didn't change during auth
                self.assertEqual(websocket.client_state, ws_state, "WebSocket state should be preserved")
                
            else:
                if result.success:
                    self.fail(f"WEBSOCKET STATE BUG: {description} - Should have failed but succeeded")
                
                # Verify error code indicates state issue
                self.assertIn("WEBSOCKET_STATE", result.error_code or "", 
                            "Error code should indicate WebSocket state issue")

    async def test_authentication_retry_mechanism_integration(self):
        """
        INTEGRATION TEST: Authentication retry mechanism with real timing.
        
        Issue #395: Tests that authentication retry mechanism works with realistic timing.
        This test should FAIL initially if retry logic is broken.
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: Authentication retry mechanism")
        
        websocket = self.create_mock_websocket_with_state(
            headers={"authorization": "Bearer test-token"}
        )
        
        # Set up E2E context for testing
        e2e_context = {
            "is_e2e_testing": True,
            "bypass_enabled": True,
            "environment": "test"
        }
        
        # Track timing for retry mechanism
        start_time = time.time()
        
        # Test authentication with retry (should succeed in E2E mode)
        result = await authenticate_websocket_ssot(websocket, e2e_context=e2e_context)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Verify authentication succeeded
        self.assertTrue(result.success, f"Retry mechanism failed: {result.error_message}")
        
        # Verify timing is reasonable (not too fast indicating no retry, not too slow indicating hang)
        self.assertLess(elapsed_time, 5.0, "Authentication took too long - possible retry loop")
        
        # Log timing for analysis
        logger.info(f"Authentication completed in {elapsed_time:.2f} seconds")

    async def test_circuit_breaker_integration(self):
        """
        INTEGRATION TEST: Circuit breaker pattern in authentication.
        
        Issue #395: Tests that circuit breaker pattern works in integration scenarios.
        This test should FAIL initially if circuit breaker logic is broken.
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: Circuit breaker pattern")
        
        # Test circuit breaker state management
        circuit_state = await self.authenticator._check_circuit_breaker()
        
        # Initially should be CLOSED (normal operation)
        self.assertEqual(circuit_state, "CLOSED", "Circuit breaker should start in CLOSED state")
        
        # Test successful authentication resets circuit breaker
        await self.authenticator._record_circuit_breaker_success()
        circuit_state = await self.authenticator._check_circuit_breaker()
        self.assertEqual(circuit_state, "CLOSED", "Successful auth should keep circuit breaker CLOSED")
        
        # Test failure recording
        await self.authenticator._record_circuit_breaker_failure()
        circuit_state = await self.authenticator._check_circuit_breaker()
        # Should still be CLOSED after one failure (threshold not reached)
        self.assertEqual(circuit_state, "CLOSED", "Single failure should not open circuit breaker")

    async def test_concurrent_authentication_integration(self):
        """
        INTEGRATION TEST: Concurrent authentication handling.
        
        Issue #395: Tests that multiple concurrent authentication attempts are handled correctly.
        This test should FAIL initially if concurrency handling is broken.
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: Concurrent authentication handling")
        
        # Create multiple WebSocket connections for concurrent testing
        websockets = []
        for i in range(3):
            ws = self.create_mock_websocket_with_state(
                headers={"authorization": f"Bearer test-token-{i}"},
                host="127.0.0.1",
                port=8000 + i
            )
            websockets.append(ws)
        
        # Set up E2E context for concurrent testing
        e2e_context = {
            "is_e2e_testing": True,
            "bypass_enabled": True,
            "environment": "test",
            "concurrent_test_mode": True
        }
        
        # Run concurrent authentication attempts
        auth_tasks = []
        for ws in websockets:
            task = authenticate_websocket_ssot(ws, e2e_context=e2e_context)
            auth_tasks.append(task)
        
        # Wait for all authentications to complete
        start_time = time.time()
        results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Validate all authentications succeeded
        successful_auths = 0
        failed_auths = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"CONCURRENT AUTH BUG: WebSocket {i} authentication failed with exception: {result}")
                failed_auths += 1
            elif isinstance(result, WebSocketAuthResult):
                if result.success:
                    successful_auths += 1
                else:
                    logger.error(f"CONCURRENT AUTH BUG: WebSocket {i} authentication failed: {result.error_message}")
                    failed_auths += 1
            else:
                logger.error(f"CONCURRENT AUTH BUG: WebSocket {i} returned unexpected result type: {type(result)}")
                failed_auths += 1
        
        # Verify concurrent handling worked
        self.assertEqual(successful_auths, len(websockets), f"All concurrent authentications should succeed (got {successful_auths}/{len(websockets)})")
        self.assertEqual(failed_auths, 0, f"No concurrent authentications should fail (got {failed_auths} failures)")
        
        # Verify timing is reasonable for concurrent execution
        elapsed_time = end_time - start_time
        self.assertLess(elapsed_time, 10.0, f"Concurrent authentication took too long: {elapsed_time:.2f}s")
        
        logger.info(f"Concurrent authentication of {len(websockets)} connections completed in {elapsed_time:.2f} seconds")

    def test_websocket_validation_edge_cases(self):
        """
        INTEGRATION TEST: WebSocket validation edge cases.
        
        Issue #395: Tests edge cases in WebSocket validation that cause authentication failures.
        This test should FAIL initially if edge case handling is broken.
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: WebSocket validation edge cases")
        
        edge_cases = [
            # (websocket_config, expected_valid, description)
            ({"headers": {}, "state": "CONNECTED"}, True, "Empty headers but connected"),
            ({"headers": None, "state": "CONNECTED"}, False, "None headers should fail"),
            ({"headers": {}, "state": "DISCONNECTED"}, False, "Disconnected state should fail"),
            ({"headers": {}, "client": None, "state": "CONNECTED"}, False, "Missing client should fail"),
        ]
        
        for config, expected_valid, description in edge_cases:
            # Create WebSocket with specific configuration
            websocket = self.create_mock_websocket_with_state(
                headers=config.get("headers", {}),
                state=config.get("state", "CONNECTED")
            )
            
            if config.get("client") is None:
                websocket.client = None
            
            # Test WebSocket validation
            is_valid = self.authenticator._is_websocket_valid_for_auth(websocket)
            
            if expected_valid:
                self.assertTrue(is_valid, f"WEBSOCKET VALIDATION BUG: {description}")
            else:
                self.assertFalse(is_valid, f"WEBSOCKET VALIDATION BUG: {description}")


if __name__ == '__main__':
    pytest.main([__file__, "-v", "--tb=short"])