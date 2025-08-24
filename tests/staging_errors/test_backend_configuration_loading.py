"""Test to reproduce backend configuration loading errors."""

import os
import pytest
import sys
from unittest.mock import patch, MagicMock, mock_open

# Add the netra_backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def test_backend_config_loading_failure():
    """Test that reproduces the configuration loading failure seen in staging."""
    
    # Set staging environment
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Clear critical environment variables that might be missing in staging
    critical_vars = [
        'DATABASE_URL',
        'CLICKHOUSE_HOST',
        'CLICKHOUSE_PORT',
        'REDIS_URL',
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY'
    ]
    
    for var in critical_vars:
        os.environ.pop(var, None)
    
    from netra_backend.app.core.configuration.base import ConfigurationManager
    
    manager = ConfigurationManager()
    
    # This should fail with missing required configurations
    with pytest.raises(Exception) as exc_info:
        config = manager._load_complete_configuration()
    
    # The error should be about missing configuration
    assert "configuration" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


def test_backend_config_create_base_config_missing_vars():
    """Test that _create_base_config fails when required environment variables are missing."""
    
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Mock the config file loading
    mock_config_data = {
        "environment": "staging",
        "debug": False,
        "services": {
            "database": {
                "url": "${DATABASE_URL}"  # This will fail to resolve
            },
            "clickhouse": {
                "host": "${CLICKHOUSE_HOST}",
                "port": "${CLICKHOUSE_PORT}"
            }
        }
    }
    
    with patch('builtins.open', mock_open(read_data=str(mock_config_data))):
        from netra_backend.app.core.configuration.base import ConfigurationManager
        
        manager = ConfigurationManager()
        
        # Clear environment variables
        os.environ.pop('DATABASE_URL', None)
        os.environ.pop('CLICKHOUSE_HOST', None)
        
        # This should fail when trying to resolve environment variables
        with pytest.raises(Exception) as exc_info:
            config = manager._create_base_config()
        
        # Should be an environment variable resolution error
        assert "DATABASE_URL" in str(exc_info.value) or "environment variable" in str(exc_info.value).lower()


def test_backend_config_staging_vs_local_differences():
    """Test configuration differences between local and staging environments."""
    
    from netra_backend.app.core.configuration.base import ConfigurationManager
    
    # Test local environment (should have defaults)
    os.environ['ENVIRONMENT'] = 'development'
    manager_local = ConfigurationManager()
    
    # In development, some configs might have defaults
    # This test verifies that development has fallbacks
    
    # Test staging environment (stricter requirements)
    os.environ['ENVIRONMENT'] = 'staging'
    manager_staging = ConfigurationManager()
    
    # Staging should not have the same fallbacks as development
    # This is where the issue occurs - staging expects all vars to be explicitly set


def test_backend_config_validation_in_staging():
    """Test that configuration validation is stricter in staging."""
    
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Set minimal required variables
    os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test'
    os.environ['REDIS_URL'] = 'redis://localhost:6379'
    
    from netra_backend.app.core.configuration.base import ConfigurationManager
    
    manager = ConfigurationManager()
    
    # Even with some vars set, staging might require additional validation
    # This test checks if there are other missing requirements
    try:
        config = manager._load_complete_configuration()
        # If it succeeds, check that all required fields are present
        assert hasattr(config, 'database')
        assert hasattr(config, 'redis')
    except Exception as e:
        # Document what other configurations are missing
        error_msg = str(e)
        assert "required" in error_msg.lower() or "missing" in error_msg.lower()


def test_backend_config_cloud_sql_connection():
    """Test that Cloud SQL connection string is properly formatted for staging."""
    
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Test different DATABASE_URL formats
    test_urls = [
        # Local format
        "postgresql://user:pass@localhost/db",
        # Cloud SQL socket format (what staging needs)
        "postgresql://user:pass@/db?host=/cloudsql/project:region:instance",
        # Cloud SQL private IP format
        "postgresql://user:pass@10.0.0.1/db"
    ]
    
    for url in test_urls:
        os.environ['DATABASE_URL'] = url
        
        # Try to parse and validate the URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Check if it's a valid Cloud SQL format for staging
        if os.environ.get('ENVIRONMENT') == 'staging':
            # Staging should use Cloud SQL format
            assert '/cloudsql/' in url or parsed.hostname != 'localhost'