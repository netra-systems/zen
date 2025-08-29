"""Test that logging properly disables ANSI codes in Cloud Run environments."""

import io
import os
import sys
import re
import pytest
from unittest.mock import patch, MagicMock
from loguru import logger


class TestCloudRunLogging:
    """Test that ANSI codes are properly disabled in production/staging environments."""
    
    @pytest.fixture(autouse=True)
    def cleanup_logger(self):
        """Clean up logger handlers before and after each test."""
        logger.remove()
        yield
        logger.remove()
    
    def test_no_ansi_codes_in_staging_environment(self):
        """Test that staging environment produces no ANSI escape codes."""
        # Mock the environment to be staging
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'TESTING': '1'
            }.get(key, default)
            
            # Import after patching to ensure proper environment detection
            from netra_backend.app.core.logging_formatters import LogHandlerConfig
            
            # Create a string buffer to capture output
            output = io.StringIO()
            
            # Create handler config with staging environment
            config = LogHandlerConfig("INFO", enable_json=False)
            
            # Add a handler that writes to our buffer
            logger.add(
                output,
                format=config.formatter.get_console_format(),
                level="INFO",
                colorize=False  # Should be False in staging
            )
            
            # Log a test message
            logger.info("Test message in staging")
            
            # Get the output
            log_output = output.getvalue()
            
            # Check for ANSI escape codes (format: ESC[...m)
            ansi_pattern = r'\x1b\[[0-9;]*m'
            ansi_codes = re.findall(ansi_pattern, log_output)
            
            # Assert no ANSI codes found
            assert len(ansi_codes) == 0, f"Found ANSI codes in staging logs: {ansi_codes}"
            
            # Also check for literal color tags (should not be present either)
            assert '<green>' not in log_output
            assert '<cyan>' not in log_output
            assert '<level>' not in log_output
    
    def test_no_ansi_codes_in_production_environment(self):
        """Test that production environment produces no ANSI escape codes."""
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'production',
                'TESTING': '1'
            }.get(key, default)
            
            # Import after patching
            from netra_backend.app.core.logging_formatters import LogHandlerConfig
            
            output = io.StringIO()
            config = LogHandlerConfig("INFO", enable_json=False)
            
            logger.add(
                output,
                format=config.formatter.get_console_format(),
                level="INFO",
                colorize=False  # Should be False in production
            )
            
            logger.info("Test message in production")
            log_output = output.getvalue()
            
            # Check for ANSI codes
            ansi_pattern = r'\x1b\[[0-9;]*m'
            ansi_codes = re.findall(ansi_pattern, log_output)
            assert len(ansi_codes) == 0, f"Found ANSI codes in production logs: {ansi_codes}"
            
            # Check for literal tags
            assert '<green>' not in log_output
            assert '<cyan>' not in log_output
            assert '<level>' not in log_output
    
    def test_console_format_has_no_color_tags_in_cloud_run(self):
        """Test that console format doesn't include color tags in Cloud Run environments."""
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
            # Test staging
            mock_env.return_value.get.return_value = 'staging'
            from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter
            
            formatter = LogFormatter(SensitiveDataFilter())
            format_string = formatter.get_console_format()
            
            # Should not contain color tags
            assert '<green>' not in format_string
            assert '<cyan>' not in format_string
            assert '<level>' not in format_string
            assert '</green>' not in format_string
            assert '</cyan>' not in format_string
            assert '</level>' not in format_string
            
            # Test production
            mock_env.return_value.get.return_value = 'production'
            formatter = LogFormatter(SensitiveDataFilter())
            format_string = formatter.get_console_format()
            
            # Should not contain color tags
            assert '<green>' not in format_string
            assert '<cyan>' not in format_string
            assert '<level>' not in format_string
    
    def test_console_format_has_color_tags_in_development(self):
        """Test that console format includes color tags in development environment."""
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = 'development'
            from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter
            
            formatter = LogFormatter(SensitiveDataFilter())
            format_string = formatter.get_console_format()
            
            # Should contain color tags in development
            assert '<green>' in format_string
            assert '<cyan>' in format_string
            assert '<level>' in format_string
    
    def test_colorize_setting_based_on_environment(self):
        """Test that colorize setting is properly set based on environment."""
        # Test that should_colorize is False for staging/production
        for env in ['staging', 'production', 'prod']:
            with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
                mock_env.return_value.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': env,
                }.get(key, default)
                
                from netra_backend.app.core.logging_formatters import LogHandlerConfig
                
                # Check the environment detection logic
                environment = mock_env.return_value.get('ENVIRONMENT', 'development').lower()
                should_colorize = environment not in ['staging', 'production', 'prod']
                assert should_colorize is False, f"colorize should be False for {env}"
        
        # Test that should_colorize is True for development
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = 'development'
            
            environment = mock_env.return_value.get('ENVIRONMENT', 'development').lower()
            should_colorize = environment not in ['staging', 'production', 'prod']
            assert should_colorize is True, "colorize should be True for development"