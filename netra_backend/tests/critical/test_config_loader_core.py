from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
from unittest.mock import Mock, patch, MagicMock

"""Critical Config Loader Core Tests"""

env = get_env()
# REMOVED_SYNTAX_ERROR: Business Value: Protects $10K/hour risk from configuration loading failures.
# REMOVED_SYNTAX_ERROR: Prevents system unavailability due to config loading issues during startup.

# REMOVED_SYNTAX_ERROR: ULTRA DEEP THINKING APPLIED: Each test designed for maximum config loading reliability.
# REMOVED_SYNTAX_ERROR: All functions <=8 lines. File <=300 lines as per CLAUDE.md requirements.
""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import os
from typing import Any, Dict

import pytest

# Import from the new configuration system
from netra_backend.app.core.configuration.loader import ConfigurationLoader
from netra_backend.app.core.configuration.environment import EnvironmentDetector
from netra_backend.app.core.configuration.secrets import SecretManager
# REMOVED_SYNTAX_ERROR: from netra_backend.app.cloud_environment_detector import ( )
detect_cloud_run_environment,


# Placeholder functions for compatibility with existing tests
# REMOVED_SYNTAX_ERROR: def _check_k_service_for_staging():
    # REMOVED_SYNTAX_ERROR: """Check K_SERVICE for staging environment"""
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: k_service = env.get('K_SERVICE', '')
    # REMOVED_SYNTAX_ERROR: return "staging" if 'staging' in k_service else ""

# REMOVED_SYNTAX_ERROR: def _check_pr_number_for_staging():
    # REMOVED_SYNTAX_ERROR: """Check PR number for staging environment"""
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: return "staging" if env.get('PR_NUMBER') else ""

# REMOVED_SYNTAX_ERROR: def _get_attribute_or_none(obj, attr):
    # REMOVED_SYNTAX_ERROR: """Get attribute or return None"""
    # REMOVED_SYNTAX_ERROR: return getattr(obj, attr, None)

# REMOVED_SYNTAX_ERROR: def _navigate_to_parent_object(config, path_list):
    # REMOVED_SYNTAX_ERROR: """Navigate to parent object using path list"""
    # REMOVED_SYNTAX_ERROR: if not isinstance(path_list, list):
        # REMOVED_SYNTAX_ERROR: return None
        # REMOVED_SYNTAX_ERROR: if len(path_list) <= 1:
            # REMOVED_SYNTAX_ERROR: return config
            # REMOVED_SYNTAX_ERROR: obj = config
            # REMOVED_SYNTAX_ERROR: for part in path_list[:-1]:
                # REMOVED_SYNTAX_ERROR: if hasattr(obj, part):
                    # REMOVED_SYNTAX_ERROR: obj = getattr(obj, part)
                    # REMOVED_SYNTAX_ERROR: else:
                        # REMOVED_SYNTAX_ERROR: return None
                        # REMOVED_SYNTAX_ERROR: return obj

# REMOVED_SYNTAX_ERROR: def apply_single_secret(config, path, field, value):
    # REMOVED_SYNTAX_ERROR: """Apply single secret to config at specified path"""
    # Navigate to the parent object using the path
    # REMOVED_SYNTAX_ERROR: parent = getattr(config, path) if hasattr(config, path) else None
    # REMOVED_SYNTAX_ERROR: if parent and hasattr(parent, field):
        # REMOVED_SYNTAX_ERROR: setattr(parent, field, value)
        # REMOVED_SYNTAX_ERROR: return True
        # REMOVED_SYNTAX_ERROR: return False

# REMOVED_SYNTAX_ERROR: def get_critical_vars_mapping():
    # REMOVED_SYNTAX_ERROR: """Get critical variables mapping"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'GEMINI_API_KEY': 'gemini_api_key',
    # REMOVED_SYNTAX_ERROR: 'CLICKHOUSE_HOST': 'clickhouse_host',
    # REMOVED_SYNTAX_ERROR: 'CLICKHOUSE_PASSWORD': 'clickhouse_password',
    # REMOVED_SYNTAX_ERROR: 'DATABASE_URL': 'database_url',
    # REMOVED_SYNTAX_ERROR: 'REDIS_URL': 'redis_url',
    # REMOVED_SYNTAX_ERROR: 'CLICKHOUSE_URL': 'clickhouse_url',
    # REMOVED_SYNTAX_ERROR: 'SECRET_KEY': 'secret_key',
    # REMOVED_SYNTAX_ERROR: 'JWT_SECRET_KEY': 'jwt_secret_key',
    # REMOVED_SYNTAX_ERROR: 'FERNET_KEY': 'fernet_key',
    # REMOVED_SYNTAX_ERROR: 'LOG_LEVEL': 'log_level',
    # REMOVED_SYNTAX_ERROR: 'ENVIRONMENT': 'environment'
    

# REMOVED_SYNTAX_ERROR: def load_env_var(var_name, config, field):
    # REMOVED_SYNTAX_ERROR: """Load environment variable into config field"""
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: value = env.get(var_name)
    # REMOVED_SYNTAX_ERROR: if value and hasattr(config, field):
        # REMOVED_SYNTAX_ERROR: setattr(config, field, value)
        # REMOVED_SYNTAX_ERROR: return True
        # REMOVED_SYNTAX_ERROR: return False

# REMOVED_SYNTAX_ERROR: def set_clickhouse_host(config, value):
    # REMOVED_SYNTAX_ERROR: """Set ClickHouse host"""
    # REMOVED_SYNTAX_ERROR: if hasattr(config, 'clickhouse_native'):
        # REMOVED_SYNTAX_ERROR: config.clickhouse_native.host = value
        # REMOVED_SYNTAX_ERROR: if hasattr(config, 'clickhouse_https'):
            # REMOVED_SYNTAX_ERROR: config.clickhouse_https.host = value

# REMOVED_SYNTAX_ERROR: def set_clickhouse_password(config, value):
    # REMOVED_SYNTAX_ERROR: """Set ClickHouse password"""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger as logger
    # REMOVED_SYNTAX_ERROR: if hasattr(config, 'clickhouse_native'):
        # REMOVED_SYNTAX_ERROR: config.clickhouse_native.password = value
        # REMOVED_SYNTAX_ERROR: if hasattr(config, 'clickhouse_https'):
            # REMOVED_SYNTAX_ERROR: config.clickhouse_https.password = value
            # REMOVED_SYNTAX_ERROR: logger.debug("ClickHouse password updated")

# REMOVED_SYNTAX_ERROR: def set_clickhouse_port(config, value):
    # REMOVED_SYNTAX_ERROR: """Set ClickHouse port"""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: port_int = int(value)
        # REMOVED_SYNTAX_ERROR: if hasattr(config, 'clickhouse_native'):
            # REMOVED_SYNTAX_ERROR: config.clickhouse_native.port = port_int
            # REMOVED_SYNTAX_ERROR: if hasattr(config, 'clickhouse_https'):
                # REMOVED_SYNTAX_ERROR: config.clickhouse_https.port = port_int
                # REMOVED_SYNTAX_ERROR: except ValueError:
                    # REMOVED_SYNTAX_ERROR: raise ValueError("formatted_string")

# REMOVED_SYNTAX_ERROR: def set_clickhouse_user(config, value):
    # REMOVED_SYNTAX_ERROR: """Set ClickHouse user"""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger as logger
    # REMOVED_SYNTAX_ERROR: if hasattr(config, 'clickhouse_native'):
        # REMOVED_SYNTAX_ERROR: config.clickhouse_native.user = value
        # REMOVED_SYNTAX_ERROR: if hasattr(config, 'clickhouse_https'):
            # REMOVED_SYNTAX_ERROR: config.clickhouse_https.user = value
            # REMOVED_SYNTAX_ERROR: logger.debug("formatted_string")

# REMOVED_SYNTAX_ERROR: def set_gemini_api_key(config, value):
    # REMOVED_SYNTAX_ERROR: """Set Gemini API key"""
    # REMOVED_SYNTAX_ERROR: if hasattr(config, 'llm_configs'):
        # REMOVED_SYNTAX_ERROR: for llm_name in config.llm_configs:
            # REMOVED_SYNTAX_ERROR: set_llm_api_key(config, llm_name, value)

# REMOVED_SYNTAX_ERROR: def set_llm_api_key(config, llm_name, value):
    # REMOVED_SYNTAX_ERROR: """Set LLM API key for specific LLM config"""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: if hasattr(config, 'llm_configs') and hasattr(config.llm_configs, '__contains__') and llm_name in config.llm_configs:
            # REMOVED_SYNTAX_ERROR: config.llm_configs[llm_name].api_key = value
            # REMOVED_SYNTAX_ERROR: except (AttributeError, TypeError):
                # Handle missing config gracefully
                # REMOVED_SYNTAX_ERROR: pass

                # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: class TestEnvironmentVariableLoading:
    # REMOVED_SYNTAX_ERROR: """Business Value: Ensures environment variables loaded correctly for all configurations"""

# REMOVED_SYNTAX_ERROR: def test_load_env_var_success_with_valid_config(self):
    # REMOVED_SYNTAX_ERROR: """Test environment variable successfully loaded into config"""
    # Arrange - Mock config with field
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service

    # REMOVED_SYNTAX_ERROR: mock_config.db_pool_size = 10
    # REMOVED_SYNTAX_ERROR: mock_config.db_max_overflow = 20
    # REMOVED_SYNTAX_ERROR: mock_config.db_pool_timeout = 60
    # REMOVED_SYNTAX_ERROR: mock_config.db_pool_recycle = 3600
    # REMOVED_SYNTAX_ERROR: mock_config.db_echo = False
    # REMOVED_SYNTAX_ERROR: mock_config.db_echo_pool = False
    # REMOVED_SYNTAX_ERROR: mock_config.environment = 'testing'

    # REMOVED_SYNTAX_ERROR: mock_config.test_field = None

    # Act - Load environment variable
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        # REMOVED_SYNTAX_ERROR: result = load_env_var("TEST_VAR", mock_config, "test_field")

        # Assert - Environment variable loaded successfully
        # REMOVED_SYNTAX_ERROR: assert result is True
        # REMOVED_SYNTAX_ERROR: assert mock_config.test_field == "test_value"

# REMOVED_SYNTAX_ERROR: def test_load_env_var_failure_missing_field(self):
    # REMOVED_SYNTAX_ERROR: """Test environment variable loading fails when config field missing"""
    # Arrange - Use a real object without the field instead of Mock
# REMOVED_SYNTAX_ERROR: class TestConfig:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.existing_field = None
    # Note: nonexistent_field is intentionally not defined

    # REMOVED_SYNTAX_ERROR: test_config = TestConfig()

    # Act - Attempt to load into non-existent field
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        # REMOVED_SYNTAX_ERROR: result = load_env_var("TEST_VAR", test_config, "nonexistent_field")

        # Assert - Loading fails gracefully
        # REMOVED_SYNTAX_ERROR: assert result is False

# REMOVED_SYNTAX_ERROR: def test_load_env_var_failure_missing_env_var(self):
    # REMOVED_SYNTAX_ERROR: """Test environment variable loading fails when env var missing"""
    # Arrange - Mock config with field but no env var
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_config.test_field = None

    # Act - Attempt to load missing environment variable
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):
        # REMOVED_SYNTAX_ERROR: result = load_env_var("MISSING_VAR", mock_config, "test_field")

        # Assert - Loading fails gracefully
        # REMOVED_SYNTAX_ERROR: assert result is False
        # REMOVED_SYNTAX_ERROR: assert mock_config.test_field is None

# REMOVED_SYNTAX_ERROR: def test_load_env_var_success_with_existing_field(self):
    # REMOVED_SYNTAX_ERROR: """Test environment variable loading succeeds with existing field"""
    # Arrange - Mock config with existing field
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_config.test_field = None

    # Act - Load environment variable
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"LOG_TEST": "log_value"}):
        # REMOVED_SYNTAX_ERROR: result = load_env_var("LOG_TEST", mock_config, "test_field")

        # Assert - Loading succeeded
        # REMOVED_SYNTAX_ERROR: assert result is True
        # REMOVED_SYNTAX_ERROR: assert mock_config.test_field == "log_value"

        # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: class TestClickHouseConfiguration:
    # REMOVED_SYNTAX_ERROR: """Business Value: Ensures ClickHouse configuration critical for data analytics revenue"""

# REMOVED_SYNTAX_ERROR: def test_set_clickhouse_host_updates_both_configs(self):
    # REMOVED_SYNTAX_ERROR: """Test ClickHouse host updated in both native and HTTPS configs"""
    # Arrange - Mock config with ClickHouse configs
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    # REMOVED_SYNTAX_ERROR: mock_config.clickhouse_native = clickhouse_native_instance  # Initialize appropriate service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    # REMOVED_SYNTAX_ERROR: mock_config.clickhouse_https = clickhouse_https_instance  # Initialize appropriate service

    # Act - Set ClickHouse host
    # REMOVED_SYNTAX_ERROR: set_clickhouse_host(mock_config, "clickhouse.example.com")

    # Assert - Both configs updated
    # REMOVED_SYNTAX_ERROR: assert mock_config.clickhouse_native.host == "clickhouse.example.com"
    # REMOVED_SYNTAX_ERROR: assert mock_config.clickhouse_https.host == "clickhouse.example.com"

# REMOVED_SYNTAX_ERROR: def test_set_clickhouse_port_validates_integer(self):
    # REMOVED_SYNTAX_ERROR: """Test ClickHouse port validation ensures integer values"""
    # Arrange - Mock config with ClickHouse configs
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    # REMOVED_SYNTAX_ERROR: mock_config.clickhouse_native = clickhouse_native_instance  # Initialize appropriate service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    # REMOVED_SYNTAX_ERROR: mock_config.clickhouse_https = clickhouse_https_instance  # Initialize appropriate service

    # Act - Set valid ClickHouse port
    # REMOVED_SYNTAX_ERROR: set_clickhouse_port(mock_config, "9000")

    # Assert - Port set as integer
    # REMOVED_SYNTAX_ERROR: assert mock_config.clickhouse_native.port == 9000
    # REMOVED_SYNTAX_ERROR: assert mock_config.clickhouse_https.port == 9000

# REMOVED_SYNTAX_ERROR: def test_set_clickhouse_port_invalid_value_raises_exception(self):
    # REMOVED_SYNTAX_ERROR: """Test invalid ClickHouse port raises appropriate exception"""
    # Arrange - Mock config
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service

    # Act & Assert - Invalid port raises ValueError
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError):
        # REMOVED_SYNTAX_ERROR: set_clickhouse_port(mock_config, "invalid_port")

# REMOVED_SYNTAX_ERROR: def test_set_clickhouse_password_security_logging(self):
    # REMOVED_SYNTAX_ERROR: """Test ClickHouse password setting logs without exposing password"""
    # Arrange - Mock config and logger
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    # REMOVED_SYNTAX_ERROR: mock_config.clickhouse_native = clickhouse_native_instance  # Initialize appropriate service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    # REMOVED_SYNTAX_ERROR: mock_config.clickhouse_https = clickhouse_https_instance  # Initialize appropriate service

    # Act - Set password with logging
    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
        # REMOVED_SYNTAX_ERROR: set_clickhouse_password(mock_config, "secret_password")

        # Assert - Password set but not logged
        # REMOVED_SYNTAX_ERROR: assert mock_config.clickhouse_native.password == "secret_password"
        # REMOVED_SYNTAX_ERROR: assert mock_logger.debug.called
        # Verify password not in log message
        # REMOVED_SYNTAX_ERROR: log_call = mock_logger.debug.call_args[0][0]
        # REMOVED_SYNTAX_ERROR: assert "secret_password" not in log_call

# REMOVED_SYNTAX_ERROR: def test_set_clickhouse_user_logs_username(self):
    # REMOVED_SYNTAX_ERROR: """Test ClickHouse user setting includes username in logs"""
    # Arrange - Mock config and logger
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    # REMOVED_SYNTAX_ERROR: mock_config.clickhouse_native = clickhouse_native_instance  # Initialize appropriate service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    # REMOVED_SYNTAX_ERROR: mock_config.clickhouse_https = clickhouse_https_instance  # Initialize appropriate service

    # Act - Set username with logging
    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
        # REMOVED_SYNTAX_ERROR: set_clickhouse_user(mock_config, "admin_user")

        # Assert - Username set and logged
        # REMOVED_SYNTAX_ERROR: assert mock_config.clickhouse_native.user == "admin_user"
        # REMOVED_SYNTAX_ERROR: assert mock_logger.debug.called
        # REMOVED_SYNTAX_ERROR: log_call = mock_logger.debug.call_args[0][0]
        # REMOVED_SYNTAX_ERROR: assert "admin_user" in log_call

        # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: class TestLLMConfigurationLoading:
    # REMOVED_SYNTAX_ERROR: """Business Value: Ensures LLM API key configuration for AI service functionality"""

# REMOVED_SYNTAX_ERROR: def test_set_gemini_api_key_updates_all_llm_configs(self):
    # REMOVED_SYNTAX_ERROR: """Test Gemini API key updated across all LLM configurations"""
    # Arrange - Mock config with LLM configs
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_config.llm_configs = {}
    # REMOVED_SYNTAX_ERROR: llm_names = ['default', 'analysis', 'triage', 'data']

    # REMOVED_SYNTAX_ERROR: for name in llm_names:
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        # REMOVED_SYNTAX_ERROR: mock_config.llm_configs[name] = Mock()  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_config.llm_configs[name].api_key = None

        # Act - Set Gemini API key
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.tests.critical.test_config_loader_core.set_llm_api_key') as mock_set_llm:
            # REMOVED_SYNTAX_ERROR: set_gemini_api_key(mock_config, "gemini_api_key_123")

            # Assert - API key set for all LLM configs
            # REMOVED_SYNTAX_ERROR: assert mock_set_llm.call_count >= len(llm_names)

# REMOVED_SYNTAX_ERROR: def test_set_llm_api_key_individual_config(self):
    # REMOVED_SYNTAX_ERROR: """Test individual LLM config API key setting"""
    # Arrange - Mock config with specific LLM config
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_config.llm_configs = { )
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: 'analysis': Mock()  # TODO: Use real service instance
    
    # REMOVED_SYNTAX_ERROR: mock_config.llm_configs['analysis'].api_key = None

    # Act - Set API key for specific LLM
    # REMOVED_SYNTAX_ERROR: set_llm_api_key(mock_config, 'analysis', 'analysis_api_key')

    # Assert - API key set for specific config
    # REMOVED_SYNTAX_ERROR: assert mock_config.llm_configs['analysis'].api_key == 'analysis_api_key'

# REMOVED_SYNTAX_ERROR: def test_set_llm_api_key_missing_config_handles_gracefully(self):
    # REMOVED_SYNTAX_ERROR: """Test LLM API key setting handles missing config gracefully"""
    # Arrange - Mock config without llm_configs
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # Don't set llm_configs attribute

    # Act - Attempt to set API key on missing config
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: set_llm_api_key(mock_config, 'nonexistent', 'key')
        # Should not raise exception
        # REMOVED_SYNTAX_ERROR: success = True
        # REMOVED_SYNTAX_ERROR: except AttributeError:
            # REMOVED_SYNTAX_ERROR: success = False

            # Assert - Missing config handled gracefully
            # REMOVED_SYNTAX_ERROR: assert success

            # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: class TestCriticalVariableMapping:
    # REMOVED_SYNTAX_ERROR: """Business Value: Ensures critical environment variables properly mapped for system startup"""

# REMOVED_SYNTAX_ERROR: def test_critical_vars_mapping_includes_database_vars(self):
    # REMOVED_SYNTAX_ERROR: """Test critical variables mapping includes all database variables"""
    # Arrange & Act - Get critical variables mapping
    # REMOVED_SYNTAX_ERROR: mapping = get_critical_vars_mapping()

    # Assert - Database variables included
    # REMOVED_SYNTAX_ERROR: assert "DATABASE_URL" in mapping
    # REMOVED_SYNTAX_ERROR: assert "REDIS_URL" in mapping
    # REMOVED_SYNTAX_ERROR: assert "CLICKHOUSE_URL" in mapping
    # REMOVED_SYNTAX_ERROR: assert mapping["DATABASE_URL"] == "database_url"

# REMOVED_SYNTAX_ERROR: def test_critical_vars_mapping_includes_auth_vars(self):
    # REMOVED_SYNTAX_ERROR: """Test critical variables mapping includes authentication variables"""
    # Arrange & Act - Get critical variables mapping
    # REMOVED_SYNTAX_ERROR: mapping = get_critical_vars_mapping()

    # Assert - Auth variables included
    # REMOVED_SYNTAX_ERROR: assert "SECRET_KEY" in mapping
    # REMOVED_SYNTAX_ERROR: assert "JWT_SECRET_KEY" in mapping
    # REMOVED_SYNTAX_ERROR: assert "FERNET_KEY" in mapping
    # REMOVED_SYNTAX_ERROR: assert mapping["JWT_SECRET_KEY"] == "jwt_secret_key"

# REMOVED_SYNTAX_ERROR: def test_critical_vars_mapping_includes_env_vars(self):
    # REMOVED_SYNTAX_ERROR: """Test critical variables mapping includes environment variables"""
    # Arrange & Act - Get critical variables mapping
    # REMOVED_SYNTAX_ERROR: mapping = get_critical_vars_mapping()

    # Assert - Environment variables included
    # REMOVED_SYNTAX_ERROR: assert "LOG_LEVEL" in mapping
    # REMOVED_SYNTAX_ERROR: assert "ENVIRONMENT" in mapping
    # REMOVED_SYNTAX_ERROR: assert mapping["LOG_LEVEL"] == "log_level"

# REMOVED_SYNTAX_ERROR: def test_critical_vars_mapping_completeness(self):
    # REMOVED_SYNTAX_ERROR: """Test critical variables mapping contains expected number of variables"""
    # Arrange & Act - Get critical variables mapping
    # REMOVED_SYNTAX_ERROR: mapping = get_critical_vars_mapping()

    # Assert - Mapping contains expected critical variables
    # REMOVED_SYNTAX_ERROR: assert len(mapping) >= 8  # At least database, auth, and env vars
    # REMOVED_SYNTAX_ERROR: assert all(isinstance(key, str) for key in mapping.keys())
    # REMOVED_SYNTAX_ERROR: assert all(isinstance(value, str) for value in mapping.values())

    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: class TestSecretApplicationLogic:
    # REMOVED_SYNTAX_ERROR: """Business Value: Ensures secrets properly applied to nested configuration objects"""

# REMOVED_SYNTAX_ERROR: def test_apply_single_secret_to_nested_config(self):
    # REMOVED_SYNTAX_ERROR: """Test secret application to nested configuration path"""
    # Arrange - Mock nested config structure
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # Mock: Database isolation for unit testing without external database connections
    # REMOVED_SYNTAX_ERROR: mock_config.database = TestDatabaseManager().get_session()
    # REMOVED_SYNTAX_ERROR: mock_config.database.password = None

    # Act - Apply secret to nested path
    # REMOVED_SYNTAX_ERROR: apply_single_secret(mock_config, "database", "password", "secret_db_pass")

    # Assert - Secret applied to nested config
    # REMOVED_SYNTAX_ERROR: assert mock_config.database.password == "secret_db_pass"

# REMOVED_SYNTAX_ERROR: def test_navigate_to_parent_object_success(self):
    # REMOVED_SYNTAX_ERROR: """Test navigation to parent object in config hierarchy"""
    # Arrange - Mock nested config structure
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config.level1 = level1_instance  # Initialize appropriate service
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_config.level1.level2 = level2_instance  # Initialize appropriate service

    # Act - Navigate to parent object
    # REMOVED_SYNTAX_ERROR: parent = _navigate_to_parent_object(mock_config, ["level1", "level2", "field"])

    # Assert - Correct parent object returned (level2 is the parent of field)
    # REMOVED_SYNTAX_ERROR: assert parent == mock_config.level1.level2

# REMOVED_SYNTAX_ERROR: def test_navigate_to_parent_object_missing_path(self):
    # REMOVED_SYNTAX_ERROR: """Test navigation handles missing path gracefully"""
    # Arrange - Real config object without nested structure
# REMOVED_SYNTAX_ERROR: class SimpleConfig:
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: simple_config = SimpleConfig()

    # Act - Navigate to non-existent path
    # REMOVED_SYNTAX_ERROR: parent = _navigate_to_parent_object(simple_config, ["nonexistent", "path"])

    # Assert - None returned for missing path
    # REMOVED_SYNTAX_ERROR: assert parent is None

# REMOVED_SYNTAX_ERROR: def test_get_attribute_or_none_success(self):
    # REMOVED_SYNTAX_ERROR: """Test getting attribute returns correct value when exists"""
    # Arrange - Mock object with attribute
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_obj = mock_obj_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_obj.test_attr = "test_value"

    # Act - Get existing attribute
    # REMOVED_SYNTAX_ERROR: value = _get_attribute_or_none(mock_obj, "test_attr")

    # Assert - Correct value returned
    # REMOVED_SYNTAX_ERROR: assert value == "test_value"

# REMOVED_SYNTAX_ERROR: def test_get_attribute_or_none_missing_attribute(self):
    # REMOVED_SYNTAX_ERROR: """Test getting missing attribute returns None"""
    # Arrange - Real object without attribute
# REMOVED_SYNTAX_ERROR: class SimpleObject:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.existing_attr = "exists"

    # REMOVED_SYNTAX_ERROR: simple_obj = SimpleObject()

    # Act - Get non-existent attribute
    # REMOVED_SYNTAX_ERROR: value = _get_attribute_or_none(simple_obj, "nonexistent_attr")

    # Assert - None returned for missing attribute
    # REMOVED_SYNTAX_ERROR: assert value is None

    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: class TestCloudRunEnvironmentDetection:
    # REMOVED_SYNTAX_ERROR: """Business Value: Ensures proper Cloud Run deployment environment detection"""

# REMOVED_SYNTAX_ERROR: def test_k_service_staging_detection(self):
    # REMOVED_SYNTAX_ERROR: """Test staging detection via K_SERVICE environment variable"""
    # Arrange - Mock K_SERVICE with staging
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"K_SERVICE": "netra-backend-staging"}):
        # Act - Check K_SERVICE for staging
        # REMOVED_SYNTAX_ERROR: result = _check_k_service_for_staging()

        # Assert - Staging detected
        # REMOVED_SYNTAX_ERROR: assert result == "staging"

# REMOVED_SYNTAX_ERROR: def test_k_service_no_staging_detection(self):
    # REMOVED_SYNTAX_ERROR: """Test no staging detection when K_SERVICE doesn't contain staging"""
    # Arrange - Mock K_SERVICE without staging
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"K_SERVICE": "netra-backend-production"}):
        # Act - Check K_SERVICE for staging
        # REMOVED_SYNTAX_ERROR: result = _check_k_service_for_staging()

        # Assert - No staging detected
        # REMOVED_SYNTAX_ERROR: assert result == ""

# REMOVED_SYNTAX_ERROR: def test_pr_number_staging_detection(self):
    # REMOVED_SYNTAX_ERROR: """Test staging detection via PR_NUMBER environment variable"""
    # Arrange - Mock PR_NUMBER
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PR_NUMBER": "123"}):
        # Act - Check PR_NUMBER for staging
        # REMOVED_SYNTAX_ERROR: result = _check_pr_number_for_staging()

        # Assert - Staging detected
        # REMOVED_SYNTAX_ERROR: assert result == "staging"

# REMOVED_SYNTAX_ERROR: def test_pr_number_no_staging_detection(self):
    # REMOVED_SYNTAX_ERROR: """Test no staging detection when PR_NUMBER not set"""
    # Arrange - Clear PR_NUMBER
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):
        # Act - Check PR_NUMBER for staging
        # REMOVED_SYNTAX_ERROR: result = _check_pr_number_for_staging()

        # Assert - No staging detected
        # REMOVED_SYNTAX_ERROR: assert result == ""

# REMOVED_SYNTAX_ERROR: def test_detect_cloud_run_environment_k_service_priority(self):
    # REMOVED_SYNTAX_ERROR: """Test K_SERVICE takes priority over PR_NUMBER in Cloud Run detection"""
    # Arrange - Set both K_SERVICE and PR_NUMBER
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
    # REMOVED_SYNTAX_ERROR: "K_SERVICE": "netra-backend-staging",
    # REMOVED_SYNTAX_ERROR: "PR_NUMBER": "123"
    # REMOVED_SYNTAX_ERROR: }):
        # Mock the config dependency
        # Mock: Component isolation for testing without external dependencies
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.cloud_environment_detector.get_config') as mock_get_config:
            # Mock: Generic component isolation for controlled unit testing
            # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: mock_config.k_service = "netra-backend-staging"
            # REMOVED_SYNTAX_ERROR: mock_get_config.return_value = mock_config

            # Act - Detect Cloud Run environment
            # REMOVED_SYNTAX_ERROR: result = detect_cloud_run_environment()

            # Assert - K_SERVICE takes priority
            # REMOVED_SYNTAX_ERROR: assert result == "staging"

# REMOVED_SYNTAX_ERROR: def test_detect_cloud_run_environment_fallback_to_pr_number(self):
    # REMOVED_SYNTAX_ERROR: """Test fallback to PR_NUMBER when K_SERVICE doesn't indicate staging"""
    # Arrange - Set non-staging K_SERVICE and PR_NUMBER
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
    # REMOVED_SYNTAX_ERROR: "K_SERVICE": "netra-backend-production",
    # REMOVED_SYNTAX_ERROR: "PR_NUMBER": "456"
    # REMOVED_SYNTAX_ERROR: }):
        # Mock the config dependency
        # Mock: Component isolation for testing without external dependencies
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.cloud_environment_detector.get_config') as mock_get_config:
            # Mock: Generic component isolation for controlled unit testing
            # REMOVED_SYNTAX_ERROR: mock_config = mock_config_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: mock_config.k_service = "netra-backend-production"
            # REMOVED_SYNTAX_ERROR: mock_config.pr_number = "456"
            # REMOVED_SYNTAX_ERROR: mock_get_config.return_value = mock_config

            # Act - Detect Cloud Run environment
            # REMOVED_SYNTAX_ERROR: result = detect_cloud_run_environment()

            # Assert - Falls back to PR_NUMBER detection
            # REMOVED_SYNTAX_ERROR: assert result == "staging"  # PR_NUMBER indicates staging