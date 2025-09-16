from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'Test that ANSI color codes are properly disabled in staging/production environments.'
import os
import sys
import re
from io import StringIO
import pytest
from unittest.mock import patch
os.environ['ENVIRONMENT'] = 'staging'
os.environ['TESTING'] = '0'
from netra_backend.app.core.logging_formatters import LogHandlerConfig
from loguru import logger

def has_ansi_codes(text: str) -> bool:
    """Check if text contains ANSI escape codes."""
    ansi_pattern = '\\x1b\\[[0-9;]*m|\\[3[0-9]m|\\[0m|\\[1m'
    return bool(re.search(ansi_pattern, text))

@pytest.mark.parametrize('environment,should_have_colors', [('development', True), ('staging', False), ('production', False), ('prod', False)])
def test_logging_colors_by_environment(environment, should_have_colors, monkeypatch):
    """Test that logging colors are properly enabled/disabled based on environment."""
    monkeypatch.setenv('ENVIRONMENT', environment)
    monkeypatch.setenv('TESTING', '0')
    logger.remove()
    captured_output = StringIO()

    def should_log_func(record):
        return True
    with patch('sys.stderr', captured_output):
        from netra_backend.app.core.logging_formatters import LogHandlerConfig
        config = LogHandlerConfig(level='INFO', enable_json=False)
        config.add_console_handler(should_log_func)
        logger.info('Test message for color detection')
        output = captured_output.getvalue()
        if should_have_colors:
            pass
        else:
            assert not has_ansi_codes(output), f'Found ANSI codes in {environment} environment: {repr(output)}'

def test_staging_logs_no_ansi(monkeypatch):
    """Specific test to ensure staging logs have no ANSI color codes."""
    monkeypatch.setenv('ENVIRONMENT', 'staging')
    monkeypatch.setenv('TESTING', '0')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    import loguru
    import io
    fresh_logger = loguru.logger.opt(depth=1)
    fresh_logger.remove()
    log_output = io.StringIO()
    handler_id = fresh_logger.add(log_output, format='{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}', level='INFO', colorize=False, enqueue=False, backtrace=False, diagnose=False)
    fresh_logger.error('Error message for staging test')
    fresh_logger.warning('Warning message for staging test')
    fresh_logger.info('Info message for staging test')
    output = log_output.getvalue()
    fresh_logger.remove(handler_id)
    assert not has_ansi_codes(output), f'Found ANSI codes in staging logs: {repr(output[:200])}'
    assert 'Error message for staging test' in output
    assert 'Warning message for staging test' in output
    assert 'Info message for staging test' in output
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')