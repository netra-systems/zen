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
        try:
            from netra_backend.app.websocket_core.handlers import ConnectionHandler
            self.ConnectionHandler = ConnectionHandler
        except ImportError as e:
            pytest.skip(f'Cannot import ConnectionHandler for testing: {e}')
        self.mock_websocket = Mock()
        self.mock_websocket.send_json = AsyncMock()
        self.mock_websocket.closed = False
        self.test_user_id = 'test-user-12345'
        self.log_capture = StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        self.log_handler.setLevel(logging.ERROR)
        self.connection_handler_logger = logging.getLogger('netra_backend.app.websocket_core.handlers')
        self.connection_handler_logger.addHandler(self.log_handler)
        self.captured_log_messages: List[str] = []

    def teardown_method(self):
        """Clean up after each test."""
        self.connection_handler_logger.removeHandler(self.log_handler)
        super().teardown_method()

    def _get_captured_logs(self) -> List[str]:
        """Get list of captured log messages."""
        log_content = self.log_capture.getvalue()
        return [line.strip() for line in log_content.split('\n') if line.strip()]

    def _create_test_message(self) -> Dict[str, Any]:
        """Create a test message for ConnectionHandler processing."""
        return {'type': 'test_message', 'content': 'Test message content', 'timestamp': datetime.now(timezone.utc).isoformat(), 'request_id': f'test-{int(datetime.now().timestamp())}'}

    @pytest.mark.unit
    async def test_exception_logging_captures_full_details(self):
        """
        CRITICAL: Tests that exception logging captures complete error information.
        
        This test MUST fail in current state due to truncated error messages.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - Error messages truncated to empty string
        - AFTER FIX: PASS - Full exception type, message, and traceback captured
        """
        logger.info('[U+1F9EA] Testing exception logging captures full details')
        exception_test_cases = [{'name': 'asyncio_cancelled_error', 'exception': asyncio.CancelledError(), 'expected_in_log': ['CancelledError', self.test_user_id]}, {'name': 'runtime_error_empty_message', 'exception': RuntimeError(''), 'expected_in_log': ['RuntimeError', self.test_user_id]}, {'name': 'value_error_none_message', 'exception': ValueError(None), 'expected_in_log': ['ValueError', self.test_user_id]}, {'name': 'type_error_no_message', 'exception': TypeError(), 'expected_in_log': ['TypeError', self.test_user_id]}, {'name': 'custom_exception_empty', 'exception': Exception(''), 'expected_in_log': ['Exception', self.test_user_id]}]
        handler = self.ConnectionHandler()
        test_message = self._create_test_message()
        for case in exception_test_cases:
            logger.info(f"Testing exception logging for: {case['name']}")
            self.log_capture.seek(0)
            self.log_capture.truncate(0)
            self.mock_websocket.send_json.side_effect = case['exception']
            with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
                result = await handler.handle_message(websocket=self.mock_websocket, user_id=self.test_user_id, message=test_message)
                assert result is False, f"Handler should return False when {case['name']} occurs, but returned {result}"
            log_messages = self._get_captured_logs()
            assert len(log_messages) > 0, f"No error logs captured for {case['name']}. Exception logging is not working properly."
            relevant_logs = [msg for msg in log_messages if self.test_user_id in msg]
            assert len(relevant_logs) > 0, f"No error logs found containing user ID {self.test_user_id} for {case['name']}. All logs: {log_messages}"
            latest_log = relevant_logs[-1]
            empty_pattern = f'Error in ConnectionHandler for user {self.test_user_id}: '
            assert latest_log != empty_pattern and (not latest_log.endswith(': ')), f"CRITICAL BUG: Exception logging truncated for {case['name']}. Log message: '{latest_log}'. Expected more details than just user ID and empty string. This makes debugging impossible in production."
            for expected_content in case['expected_in_log']:
                assert expected_content in latest_log, f"Expected '{expected_content}' in log message for {case['name']}, but log is: '{latest_log}'"
            logger.info(f"   PASS:  Exception logging test passed for {case['name']}")
            logger.info(f'     Log: {latest_log[:100]}...')
            self.mock_websocket.send_json.side_effect = None
        logger.info(' PASS:  All exception logging completeness tests passed')

    @pytest.mark.unit
    async def test_connectionhandler_return_values_match_operation_success(self):
        """
        Tests that ConnectionHandler return values accurately reflect operation success.
        
        This test validates the critical issue where handler returns True
        even when operations fail silently.
        
        Expected Behavior:
        - Connection valid, message sent successfully  ->  return True
        - Connection invalid, message not sent  ->  return False
        - Exception during send  ->  return False
        - Silent failure (current bug)  ->  return False (not True)
        """
        logger.info('[U+1F9EA] Testing ConnectionHandler return value accuracy')
        handler = self.ConnectionHandler()
        test_message = self._create_test_message()
        test_scenarios = [{'name': 'successful_send', 'is_connected': True, 'send_exception': None, 'expected_return': True, 'description': 'Connection valid, send successful'}, {'name': 'connection_check_fails', 'is_connected': False, 'send_exception': None, 'expected_return': False, 'description': 'Connection check fails, should not send'}, {'name': 'send_raises_exception', 'is_connected': True, 'send_exception': RuntimeError('Send failed'), 'expected_return': False, 'description': 'Send operation raises exception'}, {'name': 'send_raises_asyncio_error', 'is_connected': True, 'send_exception': asyncio.CancelledError(), 'expected_return': False, 'description': 'Send operation cancelled'}]
        for scenario in test_scenarios:
            logger.info(f"Testing scenario: {scenario['name']}")
            self.log_capture.seek(0)
            self.log_capture.truncate(0)
            with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected') as mock_connected:
                mock_connected.return_value = scenario['is_connected']
                if scenario['send_exception']:
                    self.mock_websocket.send_json.side_effect = scenario['send_exception']
                else:
                    self.mock_websocket.send_json.side_effect = None
                result = await handler.handle_message(websocket=self.mock_websocket, user_id=self.test_user_id, message=test_message)
                logger.info(f"  Scenario: {scenario['description']}")
                logger.info(f"  Connection check result: {scenario['is_connected']}")
                logger.info(f"  Send exception: {scenario['send_exception']}")
                logger.info(f"  Expected return: {scenario['expected_return']}")
                logger.info(f'  Actual return: {result}')
                if scenario['name'] == 'connection_check_fails':
                    assert result == scenario['expected_return'], f"CRITICAL BUG: ConnectionHandler returns {result} when connection check fails, but should return {scenario['expected_return']}. This creates silent failures where users get no responses but system thinks operation succeeded. Handler MUST return False when is_websocket_connected() returns False."
                else:
                    assert result == scenario['expected_return'], f"Return value mismatch for {scenario['name']}: expected {scenario['expected_return']}, got {result}. Description: {scenario['description']}"
                if scenario['is_connected'] and (not scenario['send_exception']):
                    self.mock_websocket.send_json.assert_called_once()
                elif not scenario['is_connected']:
                    self.mock_websocket.send_json.assert_not_called()
                logger.info(f'   PASS:  Passed')
                self.mock_websocket.send_json.reset_mock()
                self.mock_websocket.send_json.side_effect = None
        logger.info(' PASS:  All ConnectionHandler return value tests passed')

    @pytest.mark.unit
    async def test_error_logging_includes_traceback_information(self):
        """
        Tests that error logging includes complete traceback information.
        
        This is critical for debugging issues in production environments
        where the error source may not be obvious from the message alone.
        """
        logger.info('[U+1F9EA] Testing error logging includes traceback information')
        handler = self.ConnectionHandler()
        test_message = self._create_test_message()

        def create_nested_exception():
            """Create a nested exception with traceback."""
            try:

                def level_3():
                    raise ValueError('Deep nested error')

                def level_2():
                    level_3()

                def level_1():
                    level_2()
                level_1()
            except Exception as e:
                return e
        nested_exception = create_nested_exception()
        self.log_capture.seek(0)
        self.log_capture.truncate(0)
        self.mock_websocket.send_json.side_effect = nested_exception
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            result = await handler.handle_message(websocket=self.mock_websocket, user_id=self.test_user_id, message=test_message)
        assert result is False, 'Handler should return False when exception occurs'
        log_messages = self._get_captured_logs()
        assert len(log_messages) > 0, 'No error logs captured for nested exception'
        relevant_logs = [msg for msg in log_messages if self.test_user_id in msg]
        assert len(relevant_logs) > 0, 'No error logs found for our test user'
        latest_log = relevant_logs[-1]
        assert 'ValueError' in latest_log, f"Exception type 'ValueError' not found in log: {latest_log}"
        assert 'Deep nested error' in latest_log, f"Exception message 'Deep nested error' not found in log: {latest_log}"
        assert not latest_log.endswith(': '), f'Error log appears truncated: {latest_log}'
        logger.info(f' PASS:  Traceback logging test passed')
        logger.info(f'   Log captured: {latest_log[:150]}...')

    @pytest.mark.unit
    async def test_logging_handles_unicode_and_special_characters(self):
        """
        Tests that error logging properly handles unicode and special characters.
        
        This prevents logging failures that could mask the original exception.
        """
        logger.info('[U+1F9EA] Testing error logging handles unicode and special characters')
        handler = self.ConnectionHandler()
        test_message = self._create_test_message()
        special_char_tests = [{'name': 'unicode_message', 'exception': ValueError('Error with unicode: [U+6D4B][U+8BD5]  FIRE:  [U+00F1]o[U+00F1]o'), 'description': 'Unicode characters in exception message'}, {'name': 'json_in_message', 'exception': RuntimeError('JSON error: {"key": "value", "nested": {"data": 123}}'), 'description': 'JSON content in exception message'}, {'name': 'newlines_in_message', 'exception': RuntimeError('Multi-line\nerror\nmessage\nwith\nbreaks'), 'description': 'Newlines in exception message'}, {'name': 'special_symbols', 'exception': TypeError('Error with symbols: !@#$%^&*()[]{}|\\:;"\'<>?,./~`'), 'description': 'Special symbols in exception message'}]
        for test_case in special_char_tests:
            logger.info(f"Testing special characters: {test_case['name']}")
            self.log_capture.seek(0)
            self.log_capture.truncate(0)
            self.mock_websocket.send_json.side_effect = test_case['exception']
            with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
                try:
                    result = await handler.handle_message(websocket=self.mock_websocket, user_id=self.test_user_id, message=test_message)
                    assert result is False, f"Handler should return False for {test_case['name']}"
                except Exception as e:
                    pytest.fail(f"Exception logging failed for {test_case['name']}: {e}. Logging system should handle all character encodings gracefully.")
            log_messages = self._get_captured_logs()
            assert len(log_messages) > 0, f"No logs captured for {test_case['name']}. Logging system may have failed on special characters."
            relevant_logs = [msg for msg in log_messages if self.test_user_id in msg]
            assert len(relevant_logs) > 0, f"No relevant logs for {test_case['name']}"
            latest_log = relevant_logs[-1]
            assert not latest_log.endswith(': '), f"Log truncated for {test_case['name']}: {latest_log}"
            exception_type = type(test_case['exception']).__name__
            assert exception_type in latest_log, f"Exception type {exception_type} not found in log for {test_case['name']}: {latest_log}"
            logger.info(f"   PASS:  Passed for {test_case['name']}")
            self.mock_websocket.send_json.side_effect = None
        logger.info(' PASS:  All unicode and special character logging tests passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')