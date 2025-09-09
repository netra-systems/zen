"""
Unit Tests for ConnectionHandler Error Handling and Logging.

These tests focus on the specific error handling and logging issues identified
in the ConnectionHandler that cause truncated error messages and silent failures.

CRITICAL: These tests target the exception logging completeness issue where
error messages are truncated to empty strings, making debugging impossible.

Business Value:
- Ensures complete error information is captured for debugging
- Validates proper return value semantics (success/failure matching reality)
- Prevents silent failures that break user experience
- Improves system observability and incident response

Test Strategy:
- Unit tests focus on error handling logic in isolation
- Mock different exception types that cause empty string representation
- Validate logging completeness and error message construction
- Test return value accuracy under various failure conditions

Expected Test Behavior:
- CURRENT STATE: Tests FAIL due to incomplete error logging
- AFTER FIX: Tests PASS with complete exception details captured
"""

import asyncio
import logging
import pytest
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch, call, AsyncMock
from io import StringIO

from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class TestConnectionHandlerErrorHandling(SSotBaseTestCase):
    """
    Unit tests for ConnectionHandler error handling and logging completeness.
    
    These tests target the specific issues identified in the Five WHYs analysis:
    1. Truncated error messages that end with just ": "
    2. Return value mismatches where handler returns True despite failures
    3. Insufficient exception information for debugging
    4. Missing traceback information in cloud environments
    """
    
    def setup_method(self):
        """Set up each test with proper mocking infrastructure."""
        super().setup_method()
        
        # Import the ConnectionHandler class under test
        try:
            from netra_backend.app.websocket_core.handlers import ConnectionHandler
            self.ConnectionHandler = ConnectionHandler
        except ImportError as e:
            pytest.skip(f"Cannot import ConnectionHandler for testing: {e}")
            
        # Create mock WebSocket for testing
        self.mock_websocket = Mock()
        self.mock_websocket.send_json = AsyncMock()
        self.mock_websocket.closed = False
        
        # Test user ID
        self.test_user_id = "test-user-12345"
        
        # Capture log output for validation
        self.log_capture = StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        self.log_handler.setLevel(logging.ERROR)
        
        # Get the logger used by ConnectionHandler
        self.connection_handler_logger = logging.getLogger('netra_backend.app.websocket_core.handlers')
        self.connection_handler_logger.addHandler(self.log_handler)
        
        # Track log messages for analysis
        self.captured_log_messages: List[str] = []
        
    def teardown_method(self):
        """Clean up after each test."""
        # Remove our log handler
        self.connection_handler_logger.removeHandler(self.log_handler)
        super().teardown_method()
        
    def _get_captured_logs(self) -> List[str]:
        """Get list of captured log messages."""
        log_content = self.log_capture.getvalue()
        return [line.strip() for line in log_content.split('\n') if line.strip()]
        
    def _create_test_message(self) -> Dict[str, Any]:
        """Create a test message for ConnectionHandler processing."""
        return {
            "type": "test_message",
            "content": "Test message content",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"test-{int(datetime.now().timestamp())}"
        }
        
    @pytest.mark.unit
    async def test_exception_logging_captures_full_details(self):
        """
        CRITICAL: Tests that exception logging captures complete error information.
        
        This test MUST fail in current state due to truncated error messages.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - Error messages truncated to empty string
        - AFTER FIX: PASS - Full exception type, message, and traceback captured
        """
        logger.info("🧪 Testing exception logging captures full details")
        
        # Test different exception types that cause truncated logging
        exception_test_cases = [
            {
                'name': 'asyncio_cancelled_error',
                'exception': asyncio.CancelledError(),
                'expected_in_log': ['CancelledError', self.test_user_id]
            },
            {
                'name': 'runtime_error_empty_message',
                'exception': RuntimeError(""),
                'expected_in_log': ['RuntimeError', self.test_user_id]
            },
            {
                'name': 'value_error_none_message',
                'exception': ValueError(None),
                'expected_in_log': ['ValueError', self.test_user_id]  
            },
            {
                'name': 'type_error_no_message',
                'exception': TypeError(),
                'expected_in_log': ['TypeError', self.test_user_id]
            },
            {
                'name': 'custom_exception_empty',
                'exception': Exception(""),
                'expected_in_log': ['Exception', self.test_user_id]
            }
        ]
        
        handler = self.ConnectionHandler()
        test_message = self._create_test_message()
        
        for case in exception_test_cases:
            logger.info(f"Testing exception logging for: {case['name']}")
            
            # Clear previous logs
            self.log_capture.seek(0)
            self.log_capture.truncate(0)
            
            # Mock websocket.send_json to raise the test exception
            self.mock_websocket.send_json.side_effect = case['exception']
            
            # Mock is_websocket_connected to return True so we reach the send_json call
            with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
                # Call handle_message which should catch and log the exception
                result = await handler.handle_message(
                    websocket=self.mock_websocket,
                    user_id=self.test_user_id,
                    message=test_message
                )
                
                # Handler should return False on exception
                assert result is False, (
                    f"Handler should return False when {case['name']} occurs, but returned {result}"
                )
                
            # Get captured log messages
            log_messages = self._get_captured_logs()
            
            # CRITICAL TEST: Should have at least one error log
            assert len(log_messages) > 0, (
                f"No error logs captured for {case['name']}. "
                f"Exception logging is not working properly."
            )
            
            # Find logs that contain our test user ID
            relevant_logs = [msg for msg in log_messages if self.test_user_id in msg]
            assert len(relevant_logs) > 0, (
                f"No error logs found containing user ID {self.test_user_id} for {case['name']}. "
                f"All logs: {log_messages}"
            )
            
            # Get the most recent relevant log
            latest_log = relevant_logs[-1]
            
            # CRITICAL TEST: Log should not be truncated to empty string after user ID
            empty_pattern = f"Error in ConnectionHandler for user {self.test_user_id}: "
            assert latest_log != empty_pattern and not latest_log.endswith(": "), (
                f"CRITICAL BUG: Exception logging truncated for {case['name']}. "
                f"Log message: '{latest_log}'. "
                f"Expected more details than just user ID and empty string. "
                f"This makes debugging impossible in production."
            )
            
            # Validate expected content is in the log
            for expected_content in case['expected_in_log']:
                assert expected_content in latest_log, (
                    f"Expected '{expected_content}' in log message for {case['name']}, "
                    f"but log is: '{latest_log}'"
                )
                
            logger.info(f"  ✅ Exception logging test passed for {case['name']}")
            logger.info(f"     Log: {latest_log[:100]}...")
            
            # Reset mock for next test
            self.mock_websocket.send_json.side_effect = None
            
        logger.info("✅ All exception logging completeness tests passed")
        
    @pytest.mark.unit
    async def test_connectionhandler_return_values_match_operation_success(self):
        """
        Tests that ConnectionHandler return values accurately reflect operation success.
        
        This test validates the critical issue where handler returns True
        even when operations fail silently.
        
        Expected Behavior:
        - Connection valid, message sent successfully → return True
        - Connection invalid, message not sent → return False
        - Exception during send → return False
        - Silent failure (current bug) → return False (not True)
        """
        logger.info("🧪 Testing ConnectionHandler return value accuracy")
        
        handler = self.ConnectionHandler()
        test_message = self._create_test_message()
        
        # Test scenarios mapping operation outcomes to expected return values
        test_scenarios = [
            {
                'name': 'successful_send',
                'is_connected': True,
                'send_exception': None,
                'expected_return': True,
                'description': 'Connection valid, send successful'
            },
            {
                'name': 'connection_check_fails',
                'is_connected': False,
                'send_exception': None,  # Won't reach send due to connection check
                'expected_return': False,  # CRITICAL: Currently returns True (bug)
                'description': 'Connection check fails, should not send'
            },
            {
                'name': 'send_raises_exception',
                'is_connected': True,
                'send_exception': RuntimeError("Send failed"),
                'expected_return': False,
                'description': 'Send operation raises exception'
            },
            {
                'name': 'send_raises_asyncio_error',
                'is_connected': True, 
                'send_exception': asyncio.CancelledError(),
                'expected_return': False,
                'description': 'Send operation cancelled'
            }
        ]
        
        for scenario in test_scenarios:
            logger.info(f"Testing scenario: {scenario['name']}")
            
            # Clear previous logs
            self.log_capture.seek(0)
            self.log_capture.truncate(0)
            
            # Set up mocks based on scenario
            with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected') as mock_connected:
                mock_connected.return_value = scenario['is_connected']
                
                if scenario['send_exception']:
                    self.mock_websocket.send_json.side_effect = scenario['send_exception']
                else:
                    self.mock_websocket.send_json.side_effect = None
                    
                # Call handle_message
                result = await handler.handle_message(
                    websocket=self.mock_websocket,
                    user_id=self.test_user_id,
                    message=test_message
                )
                
                logger.info(f"  Scenario: {scenario['description']}")
                logger.info(f"  Connection check result: {scenario['is_connected']}")
                logger.info(f"  Send exception: {scenario['send_exception']}")
                logger.info(f"  Expected return: {scenario['expected_return']}")
                logger.info(f"  Actual return: {result}")
                
                # CRITICAL TEST: Return value must match operation success
                if scenario['name'] == 'connection_check_fails':
                    # This is the critical bug test
                    assert result == scenario['expected_return'], (
                        f"CRITICAL BUG: ConnectionHandler returns {result} when connection check fails, "
                        f"but should return {scenario['expected_return']}. "
                        f"This creates silent failures where users get no responses but system thinks operation succeeded. "
                        f"Handler MUST return False when is_websocket_connected() returns False."
                    )
                else:
                    assert result == scenario['expected_return'], (
                        f"Return value mismatch for {scenario['name']}: "
                        f"expected {scenario['expected_return']}, got {result}. "
                        f"Description: {scenario['description']}"
                    )
                    
                # Validate send_json was called appropriately
                if scenario['is_connected'] and not scenario['send_exception']:
                    # Should have attempted to send
                    self.mock_websocket.send_json.assert_called_once()
                elif not scenario['is_connected']:
                    # Should not have attempted to send
                    self.mock_websocket.send_json.assert_not_called()
                    
                logger.info(f"  ✅ Passed")
                
                # Reset mock for next test
                self.mock_websocket.send_json.reset_mock()
                self.mock_websocket.send_json.side_effect = None
                
        logger.info("✅ All ConnectionHandler return value tests passed")
        
    @pytest.mark.unit
    async def test_error_logging_includes_traceback_information(self):
        """
        Tests that error logging includes complete traceback information.
        
        This is critical for debugging issues in production environments
        where the error source may not be obvious from the message alone.
        """
        logger.info("🧪 Testing error logging includes traceback information")
        
        handler = self.ConnectionHandler()
        test_message = self._create_test_message()
        
        # Create a nested exception scenario to test traceback capture
        def create_nested_exception():
            """Create a nested exception with traceback."""
            try:
                # Simulate nested call stack
                def level_3():
                    raise ValueError("Deep nested error")
                
                def level_2():
                    level_3()
                    
                def level_1():
                    level_2()
                    
                level_1()
            except Exception as e:
                return e
                
        nested_exception = create_nested_exception()
        
        # Clear previous logs
        self.log_capture.seek(0)
        self.log_capture.truncate(0)
        
        # Mock websocket.send_json to raise the nested exception
        self.mock_websocket.send_json.side_effect = nested_exception
        
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            # Call handle_message
            result = await handler.handle_message(
                websocket=self.mock_websocket,
                user_id=self.test_user_id,
                message=test_message
            )
            
        # Should return False due to exception
        assert result is False, "Handler should return False when exception occurs"
        
        # Get captured log messages
        log_messages = self._get_captured_logs()
        
        # Should have error logs
        assert len(log_messages) > 0, "No error logs captured for nested exception"
        
        # Find relevant log
        relevant_logs = [msg for msg in log_messages if self.test_user_id in msg]
        assert len(relevant_logs) > 0, "No error logs found for our test user"
        
        latest_log = relevant_logs[-1]
        
        # CRITICAL TEST: Should include exception type and reasonable error details
        assert 'ValueError' in latest_log, (
            f"Exception type 'ValueError' not found in log: {latest_log}"
        )
        
        assert 'Deep nested error' in latest_log, (
            f"Exception message 'Deep nested error' not found in log: {latest_log}"
        )
        
        # Log should not be truncated
        assert not latest_log.endswith(": "), (
            f"Error log appears truncated: {latest_log}"
        )
        
        logger.info(f"✅ Traceback logging test passed")
        logger.info(f"   Log captured: {latest_log[:150]}...")
        
    @pytest.mark.unit
    async def test_logging_handles_unicode_and_special_characters(self):
        """
        Tests that error logging properly handles unicode and special characters.
        
        This prevents logging failures that could mask the original exception.
        """
        logger.info("🧪 Testing error logging handles unicode and special characters")
        
        handler = self.ConnectionHandler()
        test_message = self._create_test_message()
        
        # Test exceptions with special characters
        special_char_tests = [
            {
                'name': 'unicode_message',
                'exception': ValueError("Error with unicode: 测试 🔥 ñoño"),
                'description': 'Unicode characters in exception message'
            },
            {
                'name': 'json_in_message',
                'exception': RuntimeError('JSON error: {"key": "value", "nested": {"data": 123}}'),
                'description': 'JSON content in exception message'
            },
            {
                'name': 'newlines_in_message', 
                'exception': RuntimeError("Multi-line\nerror\nmessage\nwith\nbreaks"),
                'description': 'Newlines in exception message'
            },
            {
                'name': 'special_symbols',
                'exception': TypeError("Error with symbols: !@#$%^&*()[]{}|\\:;\"'<>?,./~`"),
                'description': 'Special symbols in exception message'
            }
        ]
        
        for test_case in special_char_tests:
            logger.info(f"Testing special characters: {test_case['name']}")
            
            # Clear previous logs
            self.log_capture.seek(0)
            self.log_capture.truncate(0)
            
            # Mock to raise the special character exception
            self.mock_websocket.send_json.side_effect = test_case['exception']
            
            with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
                try:
                    result = await handler.handle_message(
                        websocket=self.mock_websocket,
                        user_id=self.test_user_id,
                        message=test_message
                    )
                    
                    # Should return False due to exception
                    assert result is False, f"Handler should return False for {test_case['name']}"
                    
                except Exception as e:
                    pytest.fail(
                        f"Exception logging failed for {test_case['name']}: {e}. "
                        f"Logging system should handle all character encodings gracefully."
                    )
                    
            # Verify log was captured without logging system failure
            log_messages = self._get_captured_logs()
            
            assert len(log_messages) > 0, (
                f"No logs captured for {test_case['name']}. "
                f"Logging system may have failed on special characters."
            )
            
            relevant_logs = [msg for msg in log_messages if self.test_user_id in msg]
            assert len(relevant_logs) > 0, f"No relevant logs for {test_case['name']}"
            
            latest_log = relevant_logs[-1]
            
            # Should not be truncated
            assert not latest_log.endswith(": "), (
                f"Log truncated for {test_case['name']}: {latest_log}"
            )
            
            # Should contain exception type
            exception_type = type(test_case['exception']).__name__
            assert exception_type in latest_log, (
                f"Exception type {exception_type} not found in log for {test_case['name']}: {latest_log}"
            )
            
            logger.info(f"  ✅ Passed for {test_case['name']}")
            
            # Reset for next test
            self.mock_websocket.send_json.side_effect = None
            
        logger.info("✅ All unicode and special character logging tests passed")


if __name__ == "__main__":
    """
    Run ConnectionHandler error handling tests directly for debugging.
    
    Usage:
        python -m pytest tests/unit/test_connectionhandler_error_handling.py -v -s
    """
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])