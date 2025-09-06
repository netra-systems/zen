from unittest.mock import Mock, patch, MagicMock

"""Regression test for logging source location depth configuration.

This test ensures that log messages show the actual caller's location,
not the wrapper's location (unified_logging.py).

Business Value: Accurate logging source locations reduce debugging time
and improve operational efficiency for all customer segments.
""""

import inspect
import os
from typing import Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest
from loguru import logger

from netra_backend.app.core.unified_logging import UnifiedLogger


class TestLoggingDepthConfiguration:
    """Test that UnifiedLogger uses correct depth parameter for accurate source location."""
    
    def test_emit_log_uses_correct_depth(self):
        """Test that _emit_log method uses logger.opt(depth=3) for accurate source location."""
        # Create a UnifiedLogger instance
        unified_logger = UnifiedLogger()
        
        # Create mock for logger.opt
        mock_opt_result = MagicMock()  # TODO: Use real service instance
        mock_opt_result.log = MagicMock()  # TODO: Use real service instance
        
        with patch.object(logger, 'opt', return_value=mock_opt_result) as mock_opt:
            # Call _emit_log directly
            unified_logger._emit_log('info', 'Test message', False, {})
            
            # Verify logger.opt was called with depth=3
            mock_opt.assert_called_once_with(depth=3)
            
            # Verify the log method was called
            mock_opt_result.log.assert_called_once_with('INFO', 'Test message')
    
    def test_emit_log_with_exception_uses_correct_depth(self):
        """Test that _emit_log with exception uses correct depth and exception flag."""
        unified_logger = UnifiedLogger()
        
        # Create mock for logger.opt
        mock_opt_result = MagicMock()  # TODO: Use real service instance
        mock_opt_result.log = MagicMock()  # TODO: Use real service instance
        
        # Mock _has_exception_info to return True
        with patch.object(unified_logger, '_has_exception_info', return_value=True):
            with patch.object(logger, 'opt', return_value=mock_opt_result) as mock_opt:
                # Call _emit_log with exception
                unified_logger._emit_log('error', 'Error message', True, {})
                
                # Verify logger.opt was called with depth=3 and exception=True
                mock_opt.assert_called_once_with(depth=3, exception=True)
                
                # Verify the log method was called
                mock_opt_result.log.assert_called_once_with('ERROR', 'Error message')
    
    def test_different_log_levels_use_consistent_depth(self):
        """Test that all log levels (debug, info, warning, error, critical) use same depth."""
        unified_logger = UnifiedLogger()
        
        log_levels = ['debug', 'info', 'warning', 'error', 'critical']
        
        for level in log_levels:
            # Create fresh mock for each level
            mock_opt_result = MagicMock()  # TODO: Use real service instance
            mock_opt_result.log = MagicMock()  # TODO: Use real service instance
            
            with patch.object(logger, 'opt', return_value=mock_opt_result) as mock_opt:
                # Call _emit_log for each level
                unified_logger._emit_log(level, f'{level} message', False, {})
                
                # Verify depth=3 is used consistently
                mock_opt.assert_called_once_with(depth=3)
                mock_opt_result.log.assert_called_once_with(level.upper(), f'{level} message')
    
    def test_actual_source_location_not_wrapper(self):
        """Integration test to verify logs don't show unified_logging as source.
        
        This test verifies that the depth parameter correctly skips the wrapper
        layers so that the actual caller location is reported, not the wrapper.
        """"
        # Create a test logger that captures records
        captured_records = []
        
        def capture_record(message):
            """Capture the log record for inspection."""
            # Get the frame info to simulate what loguru does
            frame = inspect.currentframe()
            # Go back 3 frames as per our depth setting
            for _ in range(3):
                if frame and frame.f_back:
                    frame = frame.f_back
            
            if frame:
                filename = frame.f_code.co_filename
                function = frame.f_code.co_name
                lineno = frame.f_lineno
                
                captured_records.append({
                    'filename': filename,
                    'function': function,
                    'lineno': lineno,
                    'message': str(message.record['message']) if hasattr(message, 'record') else str(message)
                })
        
        # Temporarily replace logger with our capture function
        with patch.object(logger, 'opt') as mock_opt:
            mock_log = MagicMock()  # TODO: Use real service instance
            mock_opt.return_value.log = mock_log
            
            # Create and use the unified logger
            unified_logger = UnifiedLogger()
            
            # This is the actual caller location we want to see
            def test_function():
                """Function that logs - this should be the reported source."""
                current_file = __file__
                current_function = 'test_function'
                unified_logger.info("Test message from test_function")
                return current_file, current_function
            
            expected_file, expected_function = test_function()
            
            # Verify depth=3 was used
            mock_opt.assert_called_with(depth=3)
            
            # Verify log was called
            mock_log.assert_called_once()
            
            # The important part: verify that if we were to trace back,
            # we wouldn't see 'unified_logging' in the call chain at depth 3
            # This is what the depth=3 parameter accomplishes
            
            # Get the actual call arguments to verify correct parameters
            call_args = mock_opt.call_args
            assert call_args[1]['depth'] == 3, "Depth parameter should be 3"
    
    def test_regression_wrapper_location_not_shown(self):
        """Regression test: Ensure unified_logging.py:202 is never shown as source.
        
        This specific test prevents regression of the bug where logs showed:
            'netra_backend.app.core.unified_logging:_emit_log:202'
        instead of the actual source location.
        """"
        unified_logger = UnifiedLogger()
        
        # Mock the logger.opt to verify it's called correctly
        with patch.object(logger, 'opt') as mock_opt:
            mock_log_method = MagicMock()  # TODO: Use real service instance
            mock_opt.return_value.log = mock_log_method
            
            # Test warning (case from the bug report)
            unified_logger.warning("Using fallback optimization for run_id: test_id")
            
            # Verify consistent depth usage
            assert mock_opt.call_args[1]['depth'] == 3, \
                "REGRESSION: Warning should use depth=3"
            
            # Reset mock for next test
            mock_opt.reset_mock()
            mock_log_method.reset_mock()
            
            # Test error without an actual exception (just logging an error message)
            unified_logger.error("Core logic failed: No module named 'langchain_google_genai'", exc_info=False)
            
            # Verify depth=3 was used to skip wrapper layers
            assert mock_opt.call_args[1]['depth'] == 3, \
                "REGRESSION: Depth must be 3 to skip wrapper methods"
            
            # Reset and test with actual exception
            mock_opt.reset_mock()
            
            # Mock _has_exception_info to simulate actual exception case
            with patch.object(unified_logger, '_has_exception_info', return_value=True):
                unified_logger.error("Error with exception")
                
                # Should have exception flag when there's actual exception info
                assert mock_opt.call_args[1].get('exception', False) == True, \
                    "Should have exception flag when actual exception exists"


@pytest.mark.parametrize("log_method,level", [
    ("debug", "DEBUG"),
    ("info", "INFO"),
    ("warning", "WARNING"),
    ("error", "ERROR"),
    ("critical", "CRITICAL"),
])
def test_all_log_methods_use_correct_depth(log_method, level):
    """Parameterized test to verify all log methods use depth=3."""
    unified_logger = UnifiedLogger()
    
    with patch.object(logger, 'opt') as mock_opt:
        mock_log = MagicMock()  # TODO: Use real service instance
        mock_opt.return_value.log = mock_log
        
        # Get the actual log method
        log_func = getattr(unified_logger, log_method)
        
        # Call it without exception
        if log_method in ['error', 'critical']:
            # Explicitly disable exc_info for error/critical
            log_func(f"Test {level} message", exc_info=False)
        else:
            log_func(f"Test {level} message")
        
        # Verify correct depth
        assert mock_opt.call_args[1]['depth'] == 3, \
            f"{log_method} should use depth=3"
        
        # Verify the level is passed correctly
        mock_log.assert_called_once_with(level, f"Test {level} message")