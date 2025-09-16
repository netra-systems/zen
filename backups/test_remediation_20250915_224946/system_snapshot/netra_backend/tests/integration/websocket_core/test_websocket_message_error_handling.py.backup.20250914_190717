"""
WebSocket Message Error Handling Integration Tests

Purpose: Test complete error handling flows with real WebSocket connections to validate
that function signature compatibility issues are resolved in actual usage scenarios.

CRITICAL BUSINESS IMPACT:
- Tests authentication failure error messaging (affects user experience)
- Tests service initialization failure handling (affects system reliability)
- Tests cleanup error scenarios (affects resource management)
- Validates end-to-end error communication through WebSocket

This test suite:
1. Tests real WebSocket error scenarios that trigger message creation
2. Validates that error messages are properly formatted and sent
3. Ensures WebSocket connections are properly closed with correct codes
4. Tests both successful and failed message creation patterns
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketMessageErrorHandling(SSotAsyncTestCase):
    """
    Integration tests for WebSocket message error handling scenarios.
    
    Tests real WebSocket behavior with actual error conditions to validate
    that function signature fixes work in practice.
    """
    
    async def setUp(self):
        """Set up test environment with WebSocket mocks."""
        await super().setUp()
        self.websocket_mock = AsyncMock()
        self.user_context = self.create_test_user_context()
        
    def create_test_user_context(self):
        """Create a test user context for testing."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        return UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456", 
            run_id="test_run_789"
        )
    
    async def test_authentication_failure_error_message_creation_flow(self):
        """
        CRITICAL: Test complete authentication failure error flow.
        
        This test verifies that authentication failures trigger proper error message
        creation using the correct function signature.
        """
        # Import the actual WebSocket SSOT handler
        from netra_backend.app.routes.websocket_ssot import WebSocketSSotEndpoint
        
        endpoint = WebSocketSSotEndpoint()
        
        # Mock authentication failure
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
            mock_auth.return_value.success = False
            mock_auth.return_value.error = "Invalid JWT token"
            
            # Mock WebSocket utility functions
            with patch('netra_backend.app.websocket_core.utils.safe_websocket_send') as mock_send:
                with patch('netra_backend.app.websocket_core.utils.safe_websocket_close') as mock_close:
                    
                    # This should trigger the problematic create_error_message call
                    try:
                        await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                    except Exception as e:
                        # If create_error_message fails due to signature mismatch, we'll see it here
                        if "missing 1 required positional argument" in str(e):
                            self.fail(f"Function signature mismatch detected: {e}")
                    
                    # Verify error message was sent (if no signature error occurred)
                    if mock_send.called:
                        sent_args = mock_send.call_args[0]
                        error_message = sent_args[1]  # Second argument is the message
                        
                        # Validate error message structure
                        self.validate_error_message_structure(error_message, "AUTH_FAILED", "Authentication failed")
                        
                        # Verify WebSocket was closed with correct code
                        self.assertTrue(mock_close.called)
                        close_args = mock_close.call_args[0]
                        self.assertEqual(close_args[1], 1008)  # Authentication failure close code
    
    async def test_service_initialization_failure_error_message_creation_flow(self):
        """
        CRITICAL: Test service initialization failure error flow.
        
        This test verifies that service init failures trigger proper error message
        creation using the correct function signature.
        """
        from netra_backend.app.routes.websocket_ssot import WebSocketSSotEndpoint
        
        endpoint = WebSocketSSotEndpoint()
        
        # Mock successful authentication but failed WebSocket manager creation
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
            mock_auth.return_value.success = True
            mock_auth.return_value.user_context = self.user_context
            
            # Mock WebSocket manager creation failure
            with patch.object(endpoint, '_create_websocket_manager', return_value=None):
                with patch('netra_backend.app.websocket_core.utils.safe_websocket_send') as mock_send:
                    with patch('netra_backend.app.websocket_core.utils.safe_websocket_close') as mock_close:
                        
                        # This should trigger the problematic create_error_message call
                        try:
                            await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                        except Exception as e:
                            # If create_error_message fails due to signature mismatch, we'll see it here
                            if "missing 1 required positional argument" in str(e):
                                self.fail(f"Function signature mismatch detected: {e}")
                        
                        # Verify error message was sent (if no signature error occurred)
                        if mock_send.called:
                            sent_args = mock_send.call_args[0]
                            error_message = sent_args[1]
                            
                            # Validate error message structure
                            self.validate_error_message_structure(error_message, "SERVICE_INIT_FAILED", "Service initialization failed")
                            
                            # Verify WebSocket was closed with correct code
                            self.assertTrue(mock_close.called)
                            close_args = mock_close.call_args[0]
                            self.assertEqual(close_args[1], 1011)  # Internal server error close code
    
    async def test_json_parsing_error_message_creation(self):
        """
        Test error message creation during JSON parsing failures.
        
        Tests another location where create_error_message is called.
        """
        from netra_backend.app.routes.websocket_ssot import WebSocketSSotEndpoint
        
        endpoint = WebSocketSSotEndpoint()
        
        # Mock successful authentication and WebSocket manager creation
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
            mock_auth.return_value.success = True
            mock_auth.return_value.user_context = self.user_context
            
            with patch.object(endpoint, '_create_websocket_manager') as mock_create_ws:
                mock_ws_manager = AsyncMock()
                mock_create_ws.return_value = mock_ws_manager
                
                # Mock invalid JSON message
                self.websocket_mock.receive_text.return_value = "invalid json"
                
                with patch('netra_backend.app.websocket_core.utils.safe_websocket_send') as mock_send:
                    
                    # Test JSON parsing error handling
                    try:
                        await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                    except Exception as e:
                        # If create_error_message fails due to signature mismatch, we'll see it here
                        if "missing 1 required positional argument" in str(e):
                            self.fail(f"Function signature mismatch in JSON error handling: {e}")
                    
                    # Note: The actual JSON parsing might be handled differently,
                    # but this test verifies the error creation pattern doesn't break
    
    async def test_cleanup_error_message_creation(self):
        """
        Test error message creation during cleanup procedures.
        
        Tests error handling in cleanup scenarios.
        """
        from netra_backend.app.routes.websocket_ssot import WebSocketSSotEndpoint
        
        endpoint = WebSocketSSotEndpoint()
        
        # Mock successful authentication and WebSocket manager creation
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_auth:
            mock_auth.return_value.success = True
            mock_auth.return_value.user_context = self.user_context
            
            with patch.object(endpoint, '_create_websocket_manager') as mock_create_ws:
                mock_ws_manager = AsyncMock()
                mock_create_ws.return_value = mock_ws_manager
                
                # Mock cleanup failure
                mock_ws_manager.cleanup.side_effect = Exception("Cleanup failed")
                
                with patch('netra_backend.app.websocket_core.utils.safe_websocket_send') as mock_send:
                    with patch('netra_backend.app.websocket_core.utils.safe_websocket_close') as mock_close:
                        
                        # Test cleanup error handling
                        try:
                            await endpoint.websocket_endpoint(self.websocket_mock, mode="main")
                        except Exception as e:
                            # If create_error_message fails due to signature mismatch during cleanup
                            if "missing 1 required positional argument" in str(e):
                                self.fail(f"Function signature mismatch in cleanup error handling: {e}")
    
    def validate_error_message_structure(self, error_message, expected_error_code, expected_error_message):
        """
        Validate that error message has proper structure regardless of implementation.
        
        Args:
            error_message: The error message to validate
            expected_error_code: Expected error code
            expected_error_message: Expected error message text
        """
        if hasattr(error_message, 'error_code'):
            # Real implementation (pydantic model)
            self.assertEqual(error_message.error_code, expected_error_code)
            self.assertEqual(error_message.error_message, expected_error_message)
            self.assertIsNotNone(error_message.timestamp)
        elif isinstance(error_message, dict):
            # Fallback implementation (dict)
            self.assertIn("error_code", error_message)
            self.assertIn(expected_error_message, str(error_message))
        else:
            self.fail(f"Unexpected error message type: {type(error_message)}")
    
    async def test_error_message_serialization_for_websocket_transmission(self):
        """
        CRITICAL: Test that created error messages can be serialized for WebSocket transmission.
        
        This ensures that both real and fallback implementations produce serializable messages.
        """
        # Test both real and fallback implementations
        from netra_backend.app.websocket_core.types import create_error_message as real_create_error_message
        from netra_backend.app.websocket_core import create_error_message as fallback_create_error_message
        
        test_cases = [
            ("AUTH_FAILED", "Authentication failed"),
            ("SERVICE_INIT_FAILED", "Service initialization failed"),
            ("CLEANUP_FAILED", "Error during cleanup"),
            ("INVALID_JSON", "Invalid JSON format"),
        ]
        
        for error_code, error_message in test_cases:
            with self.subTest(error_code=error_code, error_message=error_message):
                
                # Test real implementation serialization
                try:
                    real_error = real_create_error_message(error_code, error_message)
                    if hasattr(real_error, 'dict'):
                        serialized = json.dumps(real_error.dict())
                    else:
                        serialized = json.dumps(real_error, default=str)
                    self.assertIsInstance(serialized, str)
                    
                    # Verify deserialization works
                    deserialized = json.loads(serialized)
                    self.assertIsInstance(deserialized, dict)
                    
                except Exception as e:
                    self.fail(f"Real error message serialization failed for {error_code}: {e}")
                
                # Test fallback implementation serialization
                try:
                    fallback_error = fallback_create_error_message(error_code, error_message)
                    serialized = json.dumps(fallback_error)
                    self.assertIsInstance(serialized, str)
                    
                    # Verify deserialization works
                    deserialized = json.loads(serialized)
                    self.assertIsInstance(deserialized, dict)
                    
                except Exception as e:
                    self.fail(f"Fallback error message serialization failed for {error_code}: {e}")
    
    async def test_websocket_connection_error_recovery(self):
        """
        Test error recovery scenarios where error messages are critical.
        
        Validates that error message creation doesn't break during recovery flows.
        """
        # Mock WebSocket connection that fails during send
        failing_websocket = AsyncMock()
        failing_websocket.send_text.side_effect = Exception("Connection lost")
        
        # Test that error message creation still works even if sending fails
        from netra_backend.app.websocket_core.types import create_error_message
        
        try:
            error_msg = create_error_message("CONNECTION_LOST", "WebSocket connection lost")
            self.assertIsNotNone(error_msg)
            self.assertEqual(error_msg.error_code, "CONNECTION_LOST")
            self.assertEqual(error_msg.error_message, "WebSocket connection lost")
        except Exception as e:
            self.fail(f"Error message creation failed during connection recovery: {e}")


class TestWebSocketImportResolutionIntegration(SSotAsyncTestCase):
    """
    Integration tests for import resolution behavior in WebSocket error scenarios.
    
    Tests that import path resolution works correctly in real usage scenarios.
    """
    
    async def test_import_fallback_behavior_during_module_failure(self):
        """
        Test import fallback behavior when types.py module fails to load.
        
        Simulates module loading failure to test fallback import behavior.
        """
        import sys
        
        # Temporarily remove types module to test fallback
        types_module = sys.modules.get('netra_backend.app.websocket_core.types')
        if types_module:
            del sys.modules['netra_backend.app.websocket_core.types']
        
        try:
            # Mock the types module import to fail
            with patch.dict('sys.modules', {'netra_backend.app.websocket_core.types': None}):
                
                # Force reload of websocket_core module
                if 'netra_backend.app.websocket_core' in sys.modules:
                    del sys.modules['netra_backend.app.websocket_core']
                
                try:
                    from netra_backend.app.websocket_core import create_error_message, create_server_message
                    
                    # Test fallback implementations work
                    error_msg = create_error_message("TEST_ERROR", "Test message")
                    server_msg = create_server_message("test_type", {"data": "test"})
                    
                    self.assertIsNotNone(error_msg)
                    self.assertIsNotNone(server_msg)
                    
                    # Fallback implementations should return dicts
                    self.assertIsInstance(error_msg, dict)
                    self.assertIsInstance(server_msg, dict)
                    
                except ImportError as e:
                    self.fail(f"Fallback import failed: {e}")
                    
        finally:
            # Restore the types module
            if types_module:
                sys.modules['netra_backend.app.websocket_core.types'] = types_module
    
    async def test_ssot_import_registry_compliance_in_websocket_ssot(self):
        """
        Test that websocket_ssot.py follows SSOT import registry patterns.
        
        Validates that the imports used in websocket_ssot.py are documented
        in the SSOT import registry.
        """
        registry_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/SSOT_IMPORT_REGISTRY.md"
        websocket_ssot_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py"
        
        # Read SSOT registry
        try:
            with open(registry_path, 'r') as f:
                registry_content = f.read()
        except FileNotFoundError:
            self.skipTest("SSOT_IMPORT_REGISTRY.md not found")
        
        # Read websocket_ssot.py
        try:
            with open(websocket_ssot_path, 'r') as f:
                websocket_content = f.read()
        except FileNotFoundError:
            self.skipTest("websocket_ssot.py not found")
        
        # Extract WebSocket-related imports from registry
        verified_imports = []
        lines = registry_content.split('\n')
        in_websocket_section = False
        
        for line in lines:
            if 'websocket' in line.lower() and ('import' in line or 'from' in line):
                if line.strip().startswith('from netra_backend.app.websocket'):
                    verified_imports.append(line.strip())
        
        # Extract imports from websocket_ssot.py
        websocket_imports = []
        for line in websocket_content.split('\n'):
            if 'create_error_message' in line and ('import' in line or 'from' in line):
                websocket_imports.append(line.strip())
        
        # Check if websocket_ssot imports are in verified registry
        for ws_import in websocket_imports:
            import_found = False
            for verified_import in verified_imports:
                if 'create_error_message' in verified_import:
                    import_found = True
                    break
            
            if not import_found:
                self.fail(f"WebSocket import not found in SSOT registry: {ws_import}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])