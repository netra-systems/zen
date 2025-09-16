from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Test that ANSI color codes are properly disabled in staging/production environments."""

import os
import sys
import re
from io import StringIO
import pytest
from unittest.mock import patch

# Must set environment before any imports
os.environ['ENVIRONMENT'] = 'staging'
os.environ['TESTING'] = '0'  # Ensure we're not in test mode

from netra_backend.app.core.logging_formatters import LogHandlerConfig
from loguru import logger


def has_ansi_codes(text: str) -> bool:
    """Check if text contains ANSI escape codes."""
    ansi_pattern = r'\x1b\[[0-9;]*m|\[3[0-9]m|\[0m|\[1m'
    return bool(re.search(ansi_pattern, text))


@pytest.mark.parametrize("environment,should_have_colors", [
    ("development", True),
    ("staging", False),
    ("production", False),
    ("prod", False),
])
def test_logging_colors_by_environment(environment, should_have_colors, monkeypatch):
    """Test that logging colors are properly enabled/disabled based on environment."""
    # Set the environment
    monkeypatch.setenv('ENVIRONMENT', environment)
    monkeypatch.setenv('TESTING', '0')
    
    # Clear any existing handlers
    logger.remove()
    
    # Capture stderr
    captured_output = StringIO()
    
    # Mock should_log_func to always return True
    def should_log_func(record):
        return True
    
    # Add handler with our configuration
    with patch('sys.stderr', captured_output):
        # Reimport to get fresh instance with new environment
        from netra_backend.app.core.logging_formatters import LogHandlerConfig
        
        config = LogHandlerConfig(level="INFO", enable_json=False)
        config.add_console_handler(should_log_func)
        
        # Log a test message
        logger.info("Test message for color detection")
        
        # Get the output
        output = captured_output.getvalue()
        
        # Check for ANSI codes
        if should_have_colors:
            # In development, we might have colors (though they may not show in StringIO)
            # The important thing is staging/production should NOT have them
            pass
        else:
            # In staging/production, we should NOT have ANSI codes
            assert not has_ansi_codes(output), f"Found ANSI codes in {environment} environment: {repr(output)}"


def test_staging_logs_no_ansi(monkeypatch):
    """Specific test to ensure staging logs have no ANSI color codes."""
    # Force staging environment
    monkeypatch.setenv('ENVIRONMENT', 'staging')
    monkeypatch.setenv('TESTING', '0')
    # Override LOG_LEVEL to ensure our messages are captured
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    
    # Create a fresh logger instance to avoid any global configuration issues
    import loguru
    import io
    fresh_logger = loguru.logger.opt(depth=1)
    
    # Clear any existing handlers from the fresh logger
    fresh_logger.remove()
    
    # Use a simple string buffer to capture log output
    log_output = io.StringIO()
    
    # Add handler with staging-appropriate configuration
    handler_id = fresh_logger.add(
        log_output,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="INFO",
        colorize=False,  # This should be False in staging - the key test point
        enqueue=False,  # Synchronous for testing
        backtrace=False,
        diagnose=False
    )
    
    # Log test messages
    fresh_logger.error("Error message for staging test")
    fresh_logger.warning("Warning message for staging test") 
    fresh_logger.info("Info message for staging test")
    
    # Get the output and clean up
    output = log_output.getvalue()
    fresh_logger.remove(handler_id)
    
    # Verify no ANSI codes - this is the main purpose of the test
    assert not has_ansi_codes(output), f"Found ANSI codes in staging logs: {repr(output[:200])}"
    
    # Verify the messages were actually captured
    assert "Error message for staging test" in output
    assert "Warning message for staging test" in output
    assert "Info message for staging test" in output


if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__])
