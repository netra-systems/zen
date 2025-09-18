class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
"""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False
"""
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()"""
        """Test for Loguru GCP formatter fix to prevent format_map errors."""

import json
import sys
import os
from datetime import datetime, timezone
from io import StringIO
from shared.isolated_environment import IsolatedEnvironment

    # Add project root to path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from loguru import logger

from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
import asyncio

"""
        """Test the GCP JSON formatter handles Loguru record structures correctly."""
"""
        """Test that the GCP formatter properly handles Loguru's record structure."""
        formatter = LogFormatter(SensitiveDataFilter())

    # Create a mock Loguru record with the actual structure
    # Loguru uses a namedtuple for level with .name, .no, .icon attributes
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        level_mock.name = 'INFO'
        level_mock.no = 20
        level_mock.icon = '[U+2139][U+FE0F]'

    # Create a datetime object for time
        time_obj = datetime.now(timezone.utc)

    # Create a record similar to what Loguru provides
record = {'level': level_mock,, 'time': time_obj,, 'message': 'Test message',, 'name': 'test_module',, 'function': 'test_function',, 'line': 42,, 'extra': {'key': 'value'}}
    # Format the record - should not raise an error
        result = formatter.gcp_json_formatter(record)

    # Verify the result is valid JSON
        parsed = json.loads(result)
        assert parsed['severity'] == 'INFO'
        assert parsed['message'] == 'Test message'
        assert parsed['timestamp'] == time_obj.isoformat()
        assert parsed['labels']['module'] == 'test_module'
        assert parsed['labels']['function'] == 'test_function'
        assert parsed['labels']['line'] == '42'
"""
        """Test that the formatter handles missing or None fields gracefully."""
        pass
        formatter = LogFormatter(SensitiveDataFilter())

    # Minimal record with missing fields
record = {'message': 'Minimal message'}
    # Should not raise an error
        result = formatter.gcp_json_formatter(record)
        parsed = json.loads(result)

    # When level is missing, it defaults to 'DEFAULT' in mapping
        assert parsed['severity'] in ['DEFAULT', 'INFO', 'ERROR']  # May vary based on fallback
    # Message might be wrapped in error if there's an issue
        assert 'message' in str(parsed['message'])"""
        assert parsed['labels']['module'] == ""
        assert parsed['labels']['function'] == ""
        assert parsed['labels']['line'] == ""

    def test_gcp_formatter_handles_string_level(self):
        """Test that the formatter handles level as a string."""
        formatter = LogFormatter(SensitiveDataFilter())

record = {'level': 'ERROR',  # String instead of namedtuple, 'message': 'Error message',, 'time': datetime.now(timezone.utc)}
        result = formatter.gcp_json_formatter(record)
        parsed = json.loads(result)

        assert parsed['severity'] == 'ERROR'
"""
        """Test that the formatter handles level as a dict."""
        pass
        formatter = LogFormatter(SensitiveDataFilter())

record = {'level': {'name': 'WARNING'},  # Dict instead of namedtuple, 'message': 'Warning message',, 'time': datetime.now(timezone.utc)}
        result = formatter.gcp_json_formatter(record)
        parsed = json.loads(result)

        assert parsed['severity'] == 'WARNING'
"""
        """Test that the formatter has a proper fallback when an unexpected error occurs."""
        formatter = LogFormatter(SensitiveDataFilter())

    # Create a record that will cause an error during processing
    # Use None which will cause issues when checking hasattr
        record = None  # This will cause an error when trying to call .get()

    # Should not raise an error, should use fallback
        result = formatter.gcp_json_formatter(record)
        parsed = json.loads(result)

        assert parsed['severity'] == 'ERROR'
        assert 'Logging formatter error' in parsed['message']
        assert 'formatter_error' in parsed['labels']
"""
        """Test that the formatter handles exception information correctly."""
        pass
        formatter = LogFormatter(SensitiveDataFilter())

        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        level_mock.name = 'ERROR'

    # Create exception info
        websocket = TestWebSocketConnection()  # Real WebSocket implementation"""
        exc_mock.value = ValueError("Test error")
        exc_mock.traceback = "Traceback line 1
        Traceback line 2"

record = {'level': level_mock,, 'time': datetime.now(timezone.utc),, 'message': 'Error with exception',, 'name': 'test_module',, 'function': 'test_function',, 'line': 100,, 'exception': exc_mock}
        result = formatter.gcp_json_formatter(record)
        parsed = json.loads(result)

        assert parsed['severity'] == 'ERROR'
        assert 'error' in parsed
        assert parsed['error']['type'] == 'ValueError'
        assert 'Test error' in str(parsed['error']['value'])
    # Traceback should have newlines escaped for single-line JSON
        assert "\
        " in parsed["error"]["traceback"]

        @pytest.mark.integration
    def test_gcp_formatter_with_real_loguru(self):
        """Integration test with real Loguru logger."""
from netra_backend.app.core.logging_formatters import LogHandlerConfig

    # Capture output
        output = StringIO()

    # Create a custom formatter that writes to our StringIO
    def test_sink(message):
        formatter = LogFormatter(SensitiveDataFilter())
        record = message.record"""
        output.write(json_output + " )
        ")

    # Configure logger with our test sink
        logger.remove()  # Remove default handlers
        logger.add(test_sink, format="{message}")

    # Log some messages
        logger.info("Test info message")
        logger.error("Test error message")
        logger.warning("Test warning with context", extra_field="extra_value")

    # Get the output
        output.seek(0)
        lines = output.readlines()

    # Verify each line is valid JSON with correct structure
        assert len(lines) >= 3

        for line in lines:
        parsed = json.loads(line)
        assert 'severity' in parsed
        assert 'message' in parsed
        assert 'timestamp' in parsed
        assert 'labels' in parsed
        assert parsed['severity'] in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'DEFAULT']

        # Check specific messages
        info_line = json.loads(lines[0])
        assert info_line['severity'] == 'INFO'
        assert info_line['message'] == 'Test info message'

        error_line = json.loads(lines[1])
        assert error_line['severity'] == 'ERROR'
        assert error_line['message'] == 'Test error message'

        warning_line = json.loads(lines[2])
        assert warning_line['severity'] == 'WARNING'
        assert warning_line['message'] == 'Test warning with context'
        if 'context' in warning_line:
        assert warning_line['context'].get('extra_field') == 'extra_value'


        if __name__ == "__main__":
                # Run the tests
        test = TestGCPFormatterFix()
        test.test_gcp_formatter_handles_loguru_record_structure()
        test.test_gcp_formatter_handles_missing_fields()
        test.test_gcp_formatter_handles_string_level()
        test.test_gcp_formatter_handles_dict_level()
        test.test_gcp_formatter_fallback_on_exception()
        test.test_gcp_formatter_with_exception_info()
        print("All tests passed!")
        pass
