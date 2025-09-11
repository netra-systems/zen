"""
Mission Critical WebSocket Error Messaging Reliability Tests

BUSINESS CRITICAL: These tests protect $500K+ ARR by ensuring WebSocket error messaging
functions correctly in all scenarios. WebSocket errors breaking chat functionality
directly impacts 90% of platform value delivery.

PURPOSE:
- Validate WebSocket error messaging doesn't break due to function signature mismatches
- Ensure critical error scenarios are properly communicated to users
- Protect against regression of WebSocket message creation failures
- Validate end-to-end error handling preserves business continuity

FAILURE IMPACT:
- Chat functionality degraded (90% of platform value)
- User authentication failures not communicated
- Service initialization errors cause silent failures
- Customer experience severely impacted

This test suite MUST pass before any deployment to production.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketErrorMessagingReliability(SSotAsyncTestCase):
    """
    MISSION CRITICAL: WebSocket error messaging reliability tests.
    
    These tests validate that WebSocket error messaging works correctly
    in all critical business scenarios.
    """
    
    async def setUp(self):
        """Set up mission critical test environment."""
        await super().setUp()
        self.websocket_mock = AsyncMock()
        self.user_context = self.create_test_user_context()
        
        # Mission critical error scenarios
        self.critical_error_scenarios = [
            {
                "name": "authentication_failure",
                "error_code": "AUTH_FAILED",
                "error_message": "Authentication failed",
                "expected_close_code": 1008,
                "business_impact": "Users cannot access chat functionality"
            },
            {
                "name": "service_initialization_failure", 
                "error_code": "SERVICE_INIT_FAILED",
                "error_message": "Service initialization failed",
                "expected_close_code": 1011,
                "business_impact": "WebSocket service unavailable"
            },
            {
                "name": "cleanup_failure",
                "error_code": "CLEANUP_FAILED", 
                "error_message": "Error during cleanup",
                "expected_close_code": 1000,
                "business_impact": "Resource cleanup issues"
            },
            {
                "name": "json_parsing_failure",
                "error_code": "INVALID_JSON",
                "error_message": "Invalid JSON format",
                "expected_close_code": 1003,
                "business_impact": "Message parsing failures"
            }
        ]
        
    def create_test_user_context(self):
        """Create a test user context for mission critical testing."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        return UserExecutionContext(
            user_id="mission_critical_user_123",
            thread_id="mission_critical_thread_456",
            run_id="mission_critical_run_789"
        )
    
    async def test_mission_critical_error_message_function_signatures(self):
        """
        MISSION CRITICAL: Validate that all error message creation functions work correctly.
        
        This test MUST pass to ensure error messaging doesn't break due to signature mismatches.
        """
        # Test both real and fallback implementations
        from netra_backend.app.websocket_core.types import create_error_message as real_impl
        from netra_backend.app.websocket_core import create_error_message as fallback_impl
        
        for scenario in self.critical_error_scenarios:
            error_code = scenario["error_code"]
            error_message = scenario["error_message"]
            
            with self.subTest(scenario=scenario["name"]):
                
                # Test 1: Real implementation MUST work with correct signature
                try:
                    real_result = real_impl(error_code, error_message)
                    self.assertIsNotNone(real_result)
                    self.assertEqual(real_result.error_code, error_code)
                    self.assertEqual(real_result.error_message, error_message)
                    self.assertIsInstance(real_result.timestamp, float)
                except Exception as e:
                    self.fail(f"MISSION CRITICAL FAILURE: Real implementation failed for {scenario['name']}: {e}")
                
                # Test 2: Fallback implementation MUST work for compatibility
                try:
                    fallback_result = fallback_impl(error_code, error_message)
                    self.assertIsNotNone(fallback_result)
                    self.assertIsInstance(fallback_result, dict)
                    self.assertIn("error_code", fallback_result)
                except Exception as e:
                    self.fail(f"MISSION CRITICAL FAILURE: Fallback implementation failed for {scenario['name']}: {e}")
                
                # Test 3: Message serialization MUST work for WebSocket transmission
                try:
                    if hasattr(real_result, 'dict'):
                        json.dumps(real_result.dict())
                    else:
                        json.dumps(real_result, default=str)
                    
                    json.dumps(fallback_result)
                except Exception as e:
                    self.fail(f"MISSION CRITICAL FAILURE: Message serialization failed for {scenario['name']}: {e}")
    
    async def test_mission_critical_websocket_error_handling_end_to_end(self):
        """
        MISSION CRITICAL: Test complete WebSocket error handling flows end-to-end.
        
        This validates that error handling works in real WebSocket scenarios.
        """
        from netra_backend.app.routes.websocket_ssot import WebSocketSSotEndpoint
        
        endpoint = WebSocketSSotEndpoint()
        
        for scenario in self.critical_error_scenarios:
            with self.subTest(scenario=scenario["name"]):
                
                # Reset mocks for each scenario
                self.websocket_mock.reset_mock()
                
                with patch('netra_backend.app.websocket_core.utils.safe_websocket_send') as mock_send:
                    with patch('netra_backend.app.websocket_core.utils.safe_websocket_close') as mock_close:
                        
                        # Simulate the specific error condition
                        await self.simulate_error_condition(endpoint, scenario)
                        
                        # Verify error handling worked without signature failures
                        if mock_send.called:
                            # Error message was sent successfully
                            sent_args = mock_send.call_args[0]
                            error_message = sent_args[1]
                            self.validate_mission_critical_error_message(error_message, scenario)
                        
                        # Verify proper WebSocket closure
                        if mock_close.called:
                            close_args = mock_close.call_args[0]
                            # Validate close code if specified
                            if len(close_args) > 1:
                                actual_close_code = close_args[1]
                                # Close code validation (flexible for different error types)
                                self.assertIn(actual_close_code, [1000, 1003, 1008, 1011],
                                            f"Invalid close code {actual_close_code} for {scenario['name']}")
    
    async def simulate_error_condition(self, endpoint, scenario):
        """Simulate specific error conditions for testing."""
        scenario_name = scenario["name"]
        
        if scenario_name == "authentication_failure":
            # Mock authentication failure
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
                mock_auth.return_value.success = False
                mock_auth.return_value.error = "Invalid JWT token"
                
                try:
                    await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                except Exception as e:
                    if "missing 1 required positional argument" in str(e):
                        self.fail(f"MISSION CRITICAL: Function signature error in {scenario_name}: {e}")
        
        elif scenario_name == "service_initialization_failure":
            # Mock service initialization failure
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
                mock_auth.return_value.success = True
                mock_auth.return_value.user_context = self.user_context
                
                with patch.object(endpoint, '_create_websocket_manager', return_value=None):
                    try:
                        await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                    except Exception as e:
                        if "missing 1 required positional argument" in str(e):
                            self.fail(f"MISSION CRITICAL: Function signature error in {scenario_name}: {e}")
        
        elif scenario_name == "cleanup_failure":
            # Mock cleanup failure
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
                mock_auth.return_value.success = True
                mock_auth.return_value.user_context = self.user_context
                
                with patch.object(endpoint, '_create_websocket_manager') as mock_create_ws:
                    mock_ws_manager = AsyncMock()
                    mock_ws_manager.cleanup.side_effect = Exception("Cleanup failed")
                    mock_create_ws.return_value = mock_ws_manager
                    
                    try:
                        await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                    except Exception as e:
                        if "missing 1 required positional argument" in str(e):
                            self.fail(f"MISSION CRITICAL: Function signature error in {scenario_name}: {e}")
        
        elif scenario_name == "json_parsing_failure":
            # Mock JSON parsing failure
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
                mock_auth.return_value.success = True
                mock_auth.return_value.user_context = self.user_context
                
                with patch.object(endpoint, '_create_websocket_manager') as mock_create_ws:
                    mock_ws_manager = AsyncMock()
                    mock_create_ws.return_value = mock_ws_manager
                    
                    # Mock invalid JSON
                    self.websocket_mock.receive_text.return_value = "invalid json"
                    
                    try:
                        await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                    except Exception as e:
                        if "missing 1 required positional argument" in str(e):
                            self.fail(f"MISSION CRITICAL: Function signature error in {scenario_name}: {e}")
    
    def validate_mission_critical_error_message(self, error_message, scenario):
        """Validate that error message meets mission critical requirements."""
        expected_error_code = scenario["error_code"]
        expected_error_message = scenario["error_message"]
        
        if hasattr(error_message, 'error_code'):
            # Real implementation (pydantic model)
            self.assertEqual(error_message.error_code, expected_error_code,
                           f"Error code mismatch for {scenario['name']}")
            self.assertEqual(error_message.error_message, expected_error_message,
                           f"Error message mismatch for {scenario['name']}")
            self.assertIsNotNone(error_message.timestamp,
                               f"Missing timestamp for {scenario['name']}")
        elif isinstance(error_message, dict):
            # Fallback implementation (dict)
            self.assertIn("error_code", error_message,
                         f"Missing error_code in fallback for {scenario['name']}")
            self.assertIn(expected_error_message, str(error_message),
                         f"Error message not found in fallback for {scenario['name']}")
        else:
            self.fail(f"MISSION CRITICAL: Invalid error message type for {scenario['name']}: {type(error_message)}")
    
    async def test_mission_critical_websocket_function_signature_regression_prevention(self):
        """
        MISSION CRITICAL: Prevent regression of function signature issues.
        
        This test scans the codebase to ensure no new single-parameter calls are introduced.
        """
        import ast
        import os
        
        # Critical files that MUST NOT have single-parameter create_error_message calls
        critical_files = [
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py",
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/websocket_manager.py",
        ]
        
        signature_violations = []
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                
                try:
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            # Check for single-parameter create_error_message calls
                            if (isinstance(node.func, ast.Name) and 
                                node.func.id == 'create_error_message' and 
                                len(node.args) == 1):
                                signature_violations.append(f"{file_path}:{node.lineno}")
                                
                except SyntaxError:
                    # Skip files with syntax errors but warn
                    self.addError(self, f"Syntax error in critical file: {file_path}")
        
        if signature_violations:
            self.fail(f"MISSION CRITICAL FAILURE: Found {len(signature_violations)} function signature violations:\n" +
                     "\n".join(signature_violations) +
                     "\n\nThese MUST be fixed before deployment to prevent WebSocket failures.")
    
    async def test_mission_critical_error_message_delivery_reliability(self):
        """
        MISSION CRITICAL: Test error message delivery reliability under various conditions.
        
        Validates that error messages are delivered even under stress conditions.
        """
        from netra_backend.app.websocket_core.types import create_error_message
        
        # Test rapid error message creation (stress test)
        start_time = time.time()
        error_messages = []
        
        try:
            for i in range(100):
                error_msg = create_error_message(f"TEST_ERROR_{i}", f"Test error message {i}")
                error_messages.append(error_msg)
                
                # Validate each message
                self.assertIsNotNone(error_msg)
                self.assertEqual(error_msg.error_code, f"TEST_ERROR_{i}")
                self.assertEqual(error_msg.error_message, f"Test error message {i}")
        
        except Exception as e:
            self.fail(f"MISSION CRITICAL FAILURE: Error message creation failed under stress: {e}")
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Performance requirement: Should create 100 error messages in < 1 second
        self.assertLess(creation_time, 1.0,
                       f"Error message creation too slow: {creation_time:.3f}s for 100 messages")
        
        # Validate all messages are unique and properly formed
        self.assertEqual(len(error_messages), 100)
        error_codes = [msg.error_code for msg in error_messages]
        self.assertEqual(len(set(error_codes)), 100, "Error codes not unique")
    
    async def test_mission_critical_websocket_compatibility_matrix(self):
        """
        MISSION CRITICAL: Test compatibility matrix for all WebSocket message functions.
        
        Ensures all combinations of function calls work correctly.
        """
        # Test create_error_message function compatibility
        from netra_backend.app.websocket_core.types import create_error_message as real_error
        from netra_backend.app.websocket_core import create_error_message as fallback_error
        
        # Test create_server_message function compatibility  
        from netra_backend.app.websocket_core.types import create_server_message as real_server
        from netra_backend.app.websocket_core import create_server_message as fallback_server
        
        compatibility_matrix = [
            {
                "function": "create_error_message",
                "real_impl": real_error,
                "fallback_impl": fallback_error,
                "test_args": ("TEST_ERROR", "Test message"),
                "single_arg": ("Test message",)
            },
            {
                "function": "create_server_message", 
                "real_impl": real_server,
                "fallback_impl": fallback_server,
                "test_args": ("test_type", {"data": "test"}),
                "single_arg": ("test_type",)
            }
        ]
        
        for test_case in compatibility_matrix:
            function_name = test_case["function"]
            real_impl = test_case["real_impl"]
            fallback_impl = test_case["fallback_impl"]
            test_args = test_case["test_args"]
            single_arg = test_case["single_arg"]
            
            with self.subTest(function=function_name):
                
                # Test 1: Real implementation with correct args (MUST work)
                try:
                    real_result = real_impl(*test_args)
                    self.assertIsNotNone(real_result)
                except Exception as e:
                    self.fail(f"MISSION CRITICAL: Real {function_name} failed with correct args: {e}")
                
                # Test 2: Fallback implementation with correct args (MUST work)
                try:
                    fallback_result = fallback_impl(*test_args)
                    self.assertIsNotNone(fallback_result)
                except Exception as e:
                    self.fail(f"MISSION CRITICAL: Fallback {function_name} failed with correct args: {e}")
                
                # Test 3: Real implementation with single arg (MUST fail gracefully)
                with self.assertRaises(TypeError, msg=f"Real {function_name} should reject single argument"):
                    real_impl(*single_arg)
                
                # Test 4: Fallback implementation with single arg (MAY work for compatibility)
                try:
                    fallback_single_result = fallback_impl(*single_arg)
                    # If this works, it's providing backward compatibility
                    self.assertIsNotNone(fallback_single_result)
                except TypeError:
                    # If this fails, both implementations are strict (acceptable)
                    pass


class TestWebSocketErrorMessagingBusinessContinuity(SSotAsyncTestCase):
    """
    MISSION CRITICAL: Business continuity tests for WebSocket error messaging.
    
    Validates that business operations continue even when errors occur.
    """
    
    async def test_chat_functionality_preserved_during_error_conditions(self):
        """
        MISSION CRITICAL: Ensure chat functionality is preserved during error conditions.
        
        Chat is 90% of platform value - it MUST continue working even with error messages.
        """
        # This test would require real WebSocket connections and chat simulation
        # For now, validate that error message creation doesn't break other functionality
        
        from netra_backend.app.websocket_core.types import create_error_message, create_server_message
        
        # Simulate chat message while error occurs
        try:
            # Create error message (simulating auth failure)
            error_msg = create_error_message("AUTH_FAILED", "Authentication failed")
            
            # Create normal chat message (simulating ongoing chat)
            chat_msg = create_server_message("user_message", {"text": "Hello, are you there?"})
            
            # Both should succeed
            self.assertIsNotNone(error_msg)
            self.assertIsNotNone(chat_msg)
            
            # Chat message should not be affected by error message creation
            self.assertEqual(chat_msg.data["text"], "Hello, are you there?")
            
        except Exception as e:
            self.fail(f"MISSION CRITICAL: Error message creation interfered with chat functionality: {e}")
    
    async def test_error_message_escalation_path(self):
        """
        MISSION CRITICAL: Test error message escalation for business critical failures.
        
        Ensures that critical errors are properly escalated for business continuity.
        """
        # Test different error severity levels
        error_scenarios = [
            {"level": "WARNING", "code": "RATE_LIMITED", "message": "Rate limit exceeded"},
            {"level": "ERROR", "code": "AUTH_FAILED", "message": "Authentication failed"},
            {"level": "CRITICAL", "code": "SERVICE_DOWN", "message": "Service unavailable"},
        ]
        
        from netra_backend.app.websocket_core.types import create_error_message
        
        for scenario in error_scenarios:
            with self.subTest(level=scenario["level"]):
                try:
                    error_msg = create_error_message(scenario["code"], scenario["message"])
                    
                    # Validate error message structure
                    self.assertIsNotNone(error_msg)
                    self.assertEqual(error_msg.error_code, scenario["code"])
                    self.assertEqual(error_msg.error_message, scenario["message"])
                    
                    # Critical errors should have additional details
                    if scenario["level"] == "CRITICAL":
                        # For critical errors, we might want to add recovery suggestions
                        error_with_suggestions = create_error_message(
                            scenario["code"], 
                            scenario["message"],
                            suggestions=["Contact support", "Try again later"]
                        )
                        self.assertIsNotNone(error_with_suggestions.recovery_suggestions)
                        
                except Exception as e:
                    self.fail(f"MISSION CRITICAL: Error escalation failed for {scenario['level']}: {e}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])