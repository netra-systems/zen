"""Test to reproduce the circular dependency between logging filter and configuration loading."""

import os
import pytest
import sys
from unittest.mock import patch, MagicMock

# Add the netra_backend to path


def test_logging_filter_circular_dependency():
    """Test that reproduces the circular dependency error seen in staging."""
    
    # Set staging environment to trigger the production-like filter behavior
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Mock the configuration manager to simulate the circular import
    # Mock: Component isolation for testing without external dependencies
    with patch('netra_backend.app.core.configuration.unified_config_manager') as mock_config_manager:
        # Setup a side effect that simulates the circular dependency
        def circular_import_side_effect():
            # This simulates the config manager trying to initialize logging
            # which then tries to load config again
            from netra_backend.app.core.logging_context import ContextFilter
            filter_instance = ContextFilter()
            # This should trigger the circular dependency
            # Mock: Generic component isolation for controlled unit testing
            filter_instance.should_log(MagicMock())
            
        mock_config_manager.get_config.side_effect = circular_import_side_effect
        
        # Now try to use the logging filter which should fail with recursion
        from netra_backend.app.core.logging_context import ContextFilter
        
        filter_instance = ContextFilter()
        # Mock: Generic component isolation for controlled unit testing
        mock_record = MagicMock()
        mock_record.getMessage.return_value = "Test message"
        
        # This should raise RecursionError due to circular dependency
        with pytest.raises(RecursionError):
            filter_instance.should_log(mock_record)


def test_logging_filter_environment_detection_without_config():
    """Test that logging filter should detect environment without loading full config."""
    
    # Set staging environment
    os.environ['ENVIRONMENT'] = 'staging'
    
    from netra_backend.app.core.logging_context import ContextFilter
    
    filter_instance = ContextFilter()
    
    # The filter should be able to determine if it's production without loading config
    # This test will fail until we fix the implementation
    assert filter_instance._is_production() == False  # staging is not production
    
    # Change to production
    os.environ['ENVIRONMENT'] = 'production'
    filter_instance = ContextFilter()
    assert filter_instance._is_production() == True
    
    # Change to development
    os.environ['ENVIRONMENT'] = 'development'
    filter_instance = ContextFilter()
    assert filter_instance._is_production() == False


def test_logging_filter_handles_bootstrap_phase():
    """Test that logging filter works during bootstrap phase before config is available."""
    
    from netra_backend.app.core.logging_context import ContextFilter
    
    # During bootstrap, the filter should work even if config is not available
    filter_instance = ContextFilter()
    # Mock: Generic component isolation for controlled unit testing
    mock_record = MagicMock()
    mock_record.getMessage.return_value = "Bootstrap log message"
    
    # This should not raise any errors during bootstrap
    result = filter_instance.should_log(mock_record)
    assert isinstance(result, bool)  # Should return a boolean decision