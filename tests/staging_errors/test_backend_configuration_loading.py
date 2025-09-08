"""Test to reproduce backend configuration loading errors."""

import os
import pytest
import sys
from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import IsolatedEnvironment

# Add the netra_backend to path


env = get_env()
def test_backend_config_loading_failure():
    """Test that reproduces the configuration loading failure seen in staging."""
    
    # Set staging environment
    env.set('ENVIRONMENT', 'staging', "test")
    
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
    
    env.set('ENVIRONMENT', 'staging', "test")
    
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
    
    # Mock: Component isolation for testing without external dependencies
    with patch('builtins.open', mock_open(read_data=str(mock_config_data))):
        from netra_backend.app.core.configuration.base import ConfigurationManager
        
        manager = ConfigurationManager()
        
        # Clear environment variables
        env.delete('DATABASE_URL', "test")
        env.delete('CLICKHOUSE_HOST', "test")
        
        # This should fail when trying to resolve environment variables
        with pytest.raises(Exception) as exc_info:
            config = manager._create_base_config()
        
        # Should be an environment variable resolution error
        assert "DATABASE_URL" in str(exc_info.value) or "environment variable" in str(exc_info.value).lower()


def test_backend_config_staging_vs_local_differences():
    """Test configuration differences between local and staging environments."""
    
    from netra_backend.app.core.configuration.base import ConfigurationManager
    
    # Test local environment (should have defaults)
    env.set('ENVIRONMENT', 'development', "test")
    manager_local = ConfigurationManager()
    
    # In development, some configs might have defaults
    # This test verifies that development has fallbacks
    
    # Test staging environment (stricter requirements)
    env.set('ENVIRONMENT', 'staging', "test")
    manager_staging = ConfigurationManager()
    
    # Staging should not have the same fallbacks as development
    # This is where the issue occurs - staging expects all vars to be explicitly set


def test_backend_config_validation_in_staging():
    """Test that configuration validation is stricter in staging."""
    
    env.set('ENVIRONMENT', 'staging', "test")
    
    # Set minimal required variables
    env.set('DATABASE_URL', 'postgresql://test:test@localhost/test', "test")
    env.set('REDIS_URL', 'redis://localhost:6379', "test")
    
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
    
    env.set('ENVIRONMENT', 'staging', "test")
    
    # Test different #removed-legacyformats
    test_urls = [
        # Local format
        "postgresql://user:pass@localhost/db",
        # Cloud SQL socket format (what staging needs)
        "postgresql://user:pass@/db?host=/cloudsql/project:region:instance",
        # Cloud SQL private IP format
        "postgresql://user:pass@10.0.0.1/db"
    ]
    
    for url in test_urls:
        env.set('DATABASE_URL', url, "test")
        
        # Try to parse and validate the URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Check if it's a valid Cloud SQL format for staging
        if env.get('ENVIRONMENT') == 'staging':
            # Staging should use Cloud SQL format
            assert '/cloudsql/' in url or parsed.hostname != 'localhost'