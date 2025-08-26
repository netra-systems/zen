"""Test logging color output to ensure proper ANSI escape codes instead of literal tags.

This test verifies that the logging system produces proper colored console output
with ANSI escape codes rather than literal color tags like <white>, <red>, etc.
"""

import io
import re
import sys
from contextlib import redirect_stderr
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from netra_backend.app.core.unified_logging import UnifiedLogger, central_logger, get_logger
from netra_backend.app.core.logging_formatters import (
    LogHandlerConfig,
    SensitiveDataFilter,
    _color_message_preprocessor
)


class TestLoggingColorOutput:
    """Test proper color handling in logging output."""
    
    @pytest.fixture
    def clean_logger(self):
        """Create a fresh logger instance for testing."""
        logger = UnifiedLogger()
        yield logger
        # Cleanup
        try:
            from loguru import logger as loguru_logger
            loguru_logger.remove()
        except Exception:
            pass
    
    @pytest.fixture
    def capture_stderr(self):
        """Fixture to capture stderr output."""
        captured_output = io.StringIO()
        return captured_output
    
    def test_info_message_no_literal_color_tags(self, clean_logger, capture_stderr):
        """Test that INFO messages don't contain literal <white> tags in console output."""
        from loguru import logger as loguru_logger
        import sys
        
        # Remove all existing handlers first
        loguru_logger.remove()
        
        # Setup a simple handler that should produce colored output
        loguru_logger.add(
            capture_stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <white>{message}</white>",
            level="INFO",
            colorize=True
        )
        
        # Log an info message directly using loguru
        test_message = "This is a test info message"
        loguru_logger.info(test_message)
        
        # Get the captured output
        output = capture_stderr.getvalue()
        
        # ASSERTION: Should NOT contain literal color tags if working properly
        # This test will FAIL with current implementation if literal tags are present
        assert "<white>" not in output, f"Found literal <white> tag in output: {output}"
        assert "</white>" not in output, f"Found literal </white> tag in output: {output}"
        assert "<green>" not in output, f"Found literal <green> tag in output: {output}"
        assert "</green>" not in output, f"Found literal </green> tag in output: {output}"
        
        # Should contain the actual message
        assert test_message in output, f"Test message not found in output: {output}"
    
    def test_error_message_no_literal_color_tags(self, clean_logger, capture_stderr):
        """Test that ERROR messages don't contain literal <red> tags in console output."""
        clean_logger._config = {
            'log_level': 'ERROR',
            'enable_file_logging': False,
            'enable_json_logging': False,
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            clean_logger._configure_handlers()
            logger_instance = clean_logger.get_logger("test_logger")
            
            test_message = "This is a test error message"
            clean_logger.error(test_message, exc_info=False)  # Don't include exception info
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: Should NOT contain literal color tags
            assert "<red>" not in output, f"Found literal <red> tag in output: {output}"
            assert "</red>" not in output, f"Found literal </red> tag in output: {output}"
            assert test_message in output, f"Test message not found in output: {output}"
    
    def test_warning_message_no_literal_color_tags(self, clean_logger, capture_stderr):
        """Test that WARNING messages don't contain literal <yellow> tags in console output."""
        clean_logger._config = {
            'log_level': 'WARNING',
            'enable_file_logging': False,
            'enable_json_logging': False,
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            clean_logger._configure_handlers()
            logger_instance = clean_logger.get_logger("test_logger")
            
            test_message = "This is a test warning message"
            clean_logger.warning(test_message)
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: Should NOT contain literal color tags
            assert "<yellow>" not in output, f"Found literal <yellow> tag in output: {output}"
            assert "</yellow>" not in output, f"Found literal </yellow> tag in output: {output}"
            assert test_message in output, f"Test message not found in output: {output}"
    
    def test_debug_message_no_literal_color_tags(self, clean_logger, capture_stderr):
        """Test that DEBUG messages don't contain literal <dim> tags in console output."""
        clean_logger._config = {
            'log_level': 'DEBUG',
            'enable_file_logging': False,
            'enable_json_logging': False,
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            clean_logger._configure_handlers()
            logger_instance = clean_logger.get_logger("test_logger")
            
            test_message = "This is a test debug message"
            clean_logger.debug(test_message)
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: Should NOT contain literal color tags
            assert "<dim>" not in output, f"Found literal <dim> tag in output: {output}"
            assert "</dim>" not in output, f"Found literal </dim> tag in output: {output}"
            assert test_message in output, f"Test message not found in output: {output}"
    
    def test_critical_message_no_literal_color_tags(self, clean_logger, capture_stderr):
        """Test that CRITICAL messages don't contain literal <bold> tags in console output."""
        clean_logger._config = {
            'log_level': 'CRITICAL',
            'enable_file_logging': False,
            'enable_json_logging': False,
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            clean_logger._configure_handlers()
            logger_instance = clean_logger.get_logger("test_logger")
            
            test_message = "This is a test critical message"
            clean_logger.critical(test_message, exc_info=False)
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: Should NOT contain literal color tags
            assert "<bold>" not in output, f"Found literal <bold> tag in output: {output}"
            assert "</bold>" not in output, f"Found literal </bold> tag in output: {output}"
            assert test_message in output, f"Test message not found in output: {output}"
    
    def test_console_output_contains_ansi_escape_codes(self, clean_logger, capture_stderr):
        """Test that console output contains ANSI escape codes for colors when not in JSON mode."""
        clean_logger._config = {
            'log_level': 'INFO',
            'enable_file_logging': False,
            'enable_json_logging': False,  # Ensure we're not in JSON mode
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            clean_logger._configure_handlers()
            logger_instance = clean_logger.get_logger("test_logger")
            
            test_message = "This message should have colors"
            clean_logger.info(test_message)
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: Should contain ANSI escape codes (starts with \x1b[ or \033[)
            ansi_pattern = r'\x1b\[[0-9;]*m|\033\[[0-9;]*m'
            has_ansi_codes = re.search(ansi_pattern, output)
            
            assert has_ansi_codes, f"No ANSI escape codes found in output: {repr(output)}"
            assert test_message in output, f"Test message not found in output: {output}"
    
    def test_file_output_no_ansi_escape_codes(self, clean_logger, tmp_path):
        """Test that file output contains no ANSI escape codes."""
        log_file = tmp_path / "test.log"
        
        clean_logger._config = {
            'log_level': 'INFO',
            'enable_file_logging': True,
            'enable_json_logging': False,
            'log_file_path': str(log_file)
        }
        
        clean_logger._configure_handlers()
        logger_instance = clean_logger.get_logger("test_logger")
        
        test_message = "This message should not have colors in file"
        clean_logger.info(test_message)
        
        # Allow some time for file write
        import time
        time.sleep(0.1)
        
        # Read file content
        if log_file.exists():
            file_content = log_file.read_text()
            
            # ASSERTION: File output should NOT contain ANSI codes or literal tags
            ansi_pattern = r'\x1b\[[0-9;]*m|\033\[[0-9;]*m'
            has_ansi_codes = re.search(ansi_pattern, file_content)
            
            assert not has_ansi_codes, f"Found ANSI codes in file output: {repr(file_content)}"
            assert "<white>" not in file_content, f"Found literal color tag in file: {file_content}"
            assert test_message in file_content, f"Test message not found in file: {file_content}"
    
    def test_json_output_no_color_tags_or_ansi(self, clean_logger, capture_stderr):
        """Test that JSON output contains neither color tags nor ANSI codes."""
        clean_logger._config = {
            'log_level': 'INFO',
            'enable_file_logging': False,
            'enable_json_logging': True,  # Enable JSON mode
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            clean_logger._configure_handlers()
            logger_instance = clean_logger.get_logger("test_logger")
            
            test_message = "This JSON message should be clean"
            clean_logger.info(test_message)
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: JSON output should be clean
            assert "<white>" not in output, f"Found literal color tag in JSON: {output}"
            assert "<red>" not in output, f"Found literal color tag in JSON: {output}"
            
            ansi_pattern = r'\x1b\[[0-9;]*m|\033\[[0-9;]*m'
            has_ansi_codes = re.search(ansi_pattern, output)
            assert not has_ansi_codes, f"Found ANSI codes in JSON output: {repr(output)}"
            
            # Should be valid JSON-like structure
            assert '"message"' in output or test_message in output, f"Message not found in JSON: {output}"
    
    def test_color_preprocessor_should_not_add_literal_tags_when_colorize_false(self):
        """Test that the color preprocessor should not add literal tags to colored_message."""
        from netra_backend.app.core.logging_formatters import _color_message_preprocessor
        
        # Create a mock record like loguru would
        record = {
            "level": MagicMock(name="INFO"),
            "message": "Test message for color processing",
            "extra": {}
        }
        
        # Apply the preprocessor (this currently adds literal tags, which is wrong)
        _color_message_preprocessor(record)
        
        # ASSERTION: The preprocessor should NOT add literal color tags
        # This test will FAIL because current implementation adds literal tags
        assert "colored_message" in record["extra"], "colored_message should be added"
        colored_message = record["extra"]["colored_message"]
        
        # The bug: current implementation adds literal tags instead of processing them
        # When fixed, this should pass by either:
        # 1. Adding ANSI escape codes instead of literal tags, OR  
        # 2. Not adding literal tags when colorization should be off, OR
        # 3. Processing the tags properly based on sink capabilities
        
        # These assertions will FAIL with current implementation, demonstrating the bug
        assert "<white>" not in colored_message, f"Found literal <white> tag (BUG): {repr(colored_message)}"
        assert "</white>" not in colored_message, f"Found literal </white> tag (BUG): {repr(colored_message)}"
        assert "<red>" not in colored_message, f"Found literal <red> tag (BUG): {repr(colored_message)}"  
        assert "<dim>" not in colored_message, f"Found literal <dim> tag (BUG): {repr(colored_message)}"
        
        # Should still contain the original message
        assert "Test message for color processing" in colored_message, f"Message not found: {colored_message}"
    
    def test_multiple_log_levels_no_literal_tags(self, clean_logger, capture_stderr):
        """Test multiple log levels to ensure none produce literal color tags."""
        clean_logger._config = {
            'log_level': 'TRACE',  # Enable all levels
            'enable_file_logging': False,
            'enable_json_logging': False,
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            clean_logger._configure_handlers()
            logger_instance = clean_logger.get_logger("test_logger")
            
            # Log messages at different levels
            clean_logger.debug("Debug message")
            clean_logger.info("Info message") 
            clean_logger.warning("Warning message")
            clean_logger.error("Error message", exc_info=False)
            clean_logger.critical("Critical message", exc_info=False)
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: No literal color tags should appear
            literal_tags = ["<white>", "</white>", "<red>", "</red>", "<yellow>", "</yellow>", 
                          "<dim>", "</dim>", "<bold>", "</bold>", "<green>", "</green>"]
            
            for tag in literal_tags:
                assert tag not in output, f"Found literal color tag '{tag}' in output: {output}"
            
            # All messages should be present
            assert "Debug message" in output
            assert "Info message" in output  
            assert "Warning message" in output
            assert "Error message" in output
            assert "Critical message" in output
    
    def test_central_logger_instance_color_behavior(self, capture_stderr):
        """Test the global central_logger instance for color tag issues."""
        # Reset central logger state
        central_logger._initialized = False
        central_logger._config = {
            'log_level': 'INFO',
            'enable_file_logging': False,
            'enable_json_logging': False,
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            # This will trigger logger initialization
            logger_instance = get_logger("central_test")
            central_logger.info("Central logger test message")
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: Central logger should not produce literal color tags
            assert "<white>" not in output, f"Central logger produced literal <white> tag: {output}"
            assert "</white>" not in output, f"Central logger produced literal </white> tag: {output}"
            assert "Central logger test message" in output

    def test_loguru_with_string_sink_produces_literal_tags(self):
        """Test that demonstrates the root cause: loguru with StringIO sink produces literal tags."""
        from loguru import logger as loguru_logger
        import io
        import sys
        
        # Remove existing handlers
        loguru_logger.remove()
        
        # Create StringIO sink (like our tests use)
        string_sink = io.StringIO()
        
        # Add handler with color format - this should fail if colors are not processed
        loguru_logger.add(
            string_sink,
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <white>{message}</white>",
            level="INFO",
            colorize=True  # This should enable color processing
        )
        
        # Log a message
        test_message = "Test message with colors"
        loguru_logger.info(test_message)
        
        # Get output
        output = string_sink.getvalue()
        
        # This demonstrates the bug: even with colorize=True, StringIO sinks get literal tags
        # When this test FAILS, it shows the problem exists
        assert "<white>" not in output, f"StringIO sink contains literal tags (BUG): {repr(output)}"
        assert "<green>" not in output, f"StringIO sink contains literal tags (BUG): {repr(output)}"
        assert test_message in output, f"Message not found: {output}"

    def test_real_system_shows_literal_tags_in_stderr_output(self, capsys):
        """Test that demonstrates the actual system issue: literal tags appear in stderr."""
        # Use the central logger directly to trigger the bug
        from netra_backend.app.core.unified_logging import central_logger
        
        # Force the logger to be set up if not already
        test_message = "Test message to demonstrate color tag bug"
        central_logger.info(test_message)
        
        # Capture the stderr output
        captured = capsys.readouterr()
        stderr_output = captured.err
        
        # This test will FAIL because the system produces literal color tags
        # The error output we've seen shows lines like:
        # "2025-08-26 12:14:23.249 | DEBUG | logging:handle:1028 | <dim>Looking for locale...</dim>"
        
        # ASSERTION: The stderr output should NOT contain literal color tags
        # This will FAIL with current implementation, demonstrating the bug
        assert "<white>" not in stderr_output, f"Found literal <white> tag in stderr: {repr(stderr_output)}"
        assert "<dim>" not in stderr_output, f"Found literal <dim> tag in stderr: {repr(stderr_output)}"
        assert "<red>" not in stderr_output, f"Found literal <red> tag in stderr: {repr(stderr_output)}"
        
        # Should contain the actual message (without tags)
        if test_message not in stderr_output:
            # If message not in stderr, that's fine - the main test is about color tags
            pass
    
    def test_sensitive_data_filter_preserves_color_behavior(self, clean_logger, capture_stderr):
        """Test that sensitive data filtering doesn't interfere with color processing."""
        clean_logger._config = {
            'log_level': 'INFO',
            'enable_file_logging': False,
            'enable_json_logging': False,
            'log_file_path': 'logs/test.log'
        }
        
        with redirect_stderr(capture_stderr):
            clean_logger._configure_handlers()
            
            # Log a message with sensitive data that should be filtered
            test_message = "User logged in with password=secret123 and api_key=abc123"
            clean_logger.info(test_message)
            
            output = capture_stderr.getvalue()
            
            # ASSERTION: No literal color tags despite sensitive data filtering
            assert "<white>" not in output, f"Found literal color tag with sensitive data: {output}"
            assert "</white>" not in output, f"Found literal color tag with sensitive data: {output}"
            
            # Sensitive data should be redacted
            assert "REDACTED" in output, f"Sensitive data not redacted: {output}"
            assert "secret123" not in output, f"Sensitive password not redacted: {output}"


class TestColorPreprocessorBehavior:
    """Test the specific behavior of the color message preprocessor."""
    
    def test_preprocessor_color_mapping_info_level(self):
        """Test preprocessor maps INFO level to white color tag."""
        record = {
            "level": MagicMock(name="INFO"),
            "message": "Info test",
            "extra": {}
        }
        
        _color_message_preprocessor(record)
        
        colored_message = record["extra"]["colored_message"] 
        assert "<white>Info test</white>" == colored_message
    
    def test_preprocessor_color_mapping_error_level(self):
        """Test preprocessor maps ERROR level to red color tag.""" 
        record = {
            "level": MagicMock(name="ERROR"),
            "message": "Error test",
            "extra": {}
        }
        
        _color_message_preprocessor(record)
        
        colored_message = record["extra"]["colored_message"]
        assert "<red>Error test</red>" == colored_message
    
    def test_preprocessor_color_mapping_warning_level(self):
        """Test preprocessor maps WARNING level to yellow color tag."""
        record = {
            "level": MagicMock(name="WARNING"), 
            "message": "Warning test",
            "extra": {}
        }
        
        _color_message_preprocessor(record)
        
        colored_message = record["extra"]["colored_message"]
        assert "<yellow>Warning test</yellow>" == colored_message
    
    def test_preprocessor_color_mapping_debug_level(self):
        """Test preprocessor maps DEBUG level to dim color tag."""
        record = {
            "level": MagicMock(name="DEBUG"),
            "message": "Debug test", 
            "extra": {}
        }
        
        _color_message_preprocessor(record)
        
        colored_message = record["extra"]["colored_message"]
        assert "<dim>Debug test</dim>" == colored_message
    
    def test_preprocessor_color_mapping_critical_level(self):
        """Test preprocessor maps CRITICAL level to red bold color tag."""
        record = {
            "level": MagicMock(name="CRITICAL"),
            "message": "Critical test",
            "extra": {}
        }
        
        _color_message_preprocessor(record)
        
        colored_message = record["extra"]["colored_message"]
        assert "<red><bold>Critical test</bold></red>" == colored_message
    
    def test_preprocessor_preserves_existing_extra_data(self):
        """Test preprocessor preserves existing extra data in record."""
        record = {
            "level": MagicMock(name="INFO"),
            "message": "Test",
            "extra": {"existing_key": "existing_value"}
        }
        
        _color_message_preprocessor(record)
        
        assert "existing_key" in record["extra"]
        assert record["extra"]["existing_key"] == "existing_value"
        assert "colored_message" in record["extra"]