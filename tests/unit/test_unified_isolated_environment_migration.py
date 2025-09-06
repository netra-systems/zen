"""
Comprehensive test suite for the unified IsolatedEnvironment migration.

This test ensures that the SSOT IsolatedEnvironment implementation works correctly
across all services and maintains all functionality from the original implementations.

Business Value: Platform/Internal - System Stability
Prevents configuration drift and ensures reliable environment management.
"""
import os
import pytest
import threading
import time
from pathlib import Path

from shared.isolated_environment import (
    get_env,
    IsolatedEnvironment,
    ValidationResult,
    setenv,
    getenv,
    delenv
)


class TestUnifiedIsolatedEnvironment:
    """Test the unified IsolatedEnvironment implementation."""

    @pytest.fixture
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Get fresh environment instance for each test
        env = get_env()

        # Store original environment
        original_env = env.get_all()

        # Ensure we start in a clean state
        if env.is_isolated():
            env.disable_isolation()

        yield

        # Cleanup: restore original environment
        env.disable_isolation()

        # Only clear if isolation is enabled
        if env.is_isolated():
            env.clear()

        env.update(original_env, "test")

    def test_singleton_behavior(self):
        """Test that IsolatedEnvironment maintains singleton behavior."""
        env1 = get_env()
        env2 = get_env()
        env3 = IsolatedEnvironment()
        env4 = IsolatedEnvironment.get_instance()

        # All should be the same instance
        assert env1 is env2
        assert env2 is env3
        assert env3 is env4

        # Test thread safety of singleton
        instances = []

        def get_instance():
            instances.append(get_env())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be identical
        unique_instances = set(id(instance) for instance in instances)
        assert len(unique_instances) == 1

    def test_basic_environment_operations(self):
        """Test basic get/set/delete operations."""
        env = get_env()

        # Test basic get/set
        env.set('TEST_BASIC', 'original_value', "test")
        assert env.get('TEST_BASIC') == 'original_value'
        assert env.get('NON_EXISTENT') is None
        assert env.get('NON_EXISTENT', 'default') == 'default'

        # Test exists
        assert env.exists('TEST_BASIC') is True
        assert env.exists('NON_EXISTENT') is False

        # Test delete
        env.delete('TEST_BASIC')
        assert env.exists('TEST_BASIC') is False

    def test_isolation_mode_functionality(self):
        """Test isolation mode prevents os.environ pollution."""
        env = get_env()

        # Set initial value in os.environ
        env.set('TEST_ISOLATION', 'os_value', "test")

        # Enable isolation
        env.enable_isolation()
        assert env.is_isolated() is True

        # Modify value in isolated mode
        env.set('TEST_ISOLATION', 'isolated_value', 'test')

        # Check values
        assert env.get('TEST_ISOLATION') == 'isolated_value'
        assert os.environ['TEST_ISOLATION'] == 'os_value'  # Should not be polluted

        # Test new variable in isolation
        env.set('TEST_NEW_VAR', 'new_value', 'test')
        assert env.get('TEST_NEW_VAR') == 'new_value'
        assert 'TEST_NEW_VAR' not in os.environ

        # Disable isolation - should sync to os.environ
        env.disable_isolation()
        assert env.is_isolated() is False
        assert env.get('TEST_ISOLATION') == 'isolated_value'  # Should be synced

    def test_source_tracking(self):
        """Test that all modifications include source tracking."""
        env = get_env()
        env.enable_isolation()

        # Set with specific source
        env.set('TEST_SOURCE', 'value1', 'unit_test')
        assert env.get_variable_source('TEST_SOURCE') == 'unit_test'

        # Update with different source
        env.set('TEST_SOURCE', 'value2', 'different_source')
        assert env.get_variable_source('TEST_SOURCE') == 'different_source'

        # Test bulk update
        updates = {'VAR1': 'val1', 'VAR2': 'val2'}
        env.update(updates, 'bulk_update')
        assert env.get_variable_source('VAR1') == 'bulk_update'
        assert env.get_variable_source('VAR2') == 'bulk_update'

    def test_value_sanitization(self):
        """Test that values are sanitized while preserving database URLs."""
        env = get_env()
        env.enable_isolation()

        # Test generic value sanitization (control character removal)
        test_value = "normal_value\x00\x01with_control_chars"
        env.set('TEST_SANITIZE', test_value, 'test')
        sanitized = env.get('TEST_SANITIZE')
        assert '\x00' not in sanitized
        assert '\x01' not in sanitized
        assert 'normal_value' in sanitized
        assert 'with_control_chars' in sanitized

        # Test database URL preservation
        db_url = "postgresql://user:p@ss!w0rd@host:5432/db"
        env.set('DATABASE_URL', db_url, 'test')
        retrieved = env.get('DATABASE_URL')
        assert 'p@ss!w0rd' in retrieved  # Password special chars preserved

    def test_shell_command_expansion(self):
        """Test shell command expansion functionality (auth_service feature)."""
        env = get_env()

        # Test normal value (no expansion)
        normal_value = env._expand_shell_commands("normal_value")
        assert normal_value == "normal_value"

        # Test with ${VARIABLE} expansion (should be skipped during pytest)
        env.set('EXPAND_TEST', 'expanded_value', "test")
        test_value = env._expand_shell_commands("prefix_${EXPAND_TEST}_suffix")
        # During pytest, shell expansion is skipped for safety
        assert test_value == "prefix_${EXPAND_TEST}_suffix"

        # Test during pytest (should skip expansion)
        # This test itself is running in pytest context, so expansion should be skipped
        shell_value = env._expand_shell_commands("$(echo test)")
        assert shell_value == "$(echo test)"  # Should not be expanded in test context

    def test_staging_database_validation(self):
        """Test staging database credential validation (auth_service feature)."""
        env = get_env()
        env.enable_isolation()

        # Test non-staging environment
        env.set('ENVIRONMENT', 'development', 'test')
        result = env.validate_staging_database_credentials()
        assert result['warnings']  # Should warn about not being in staging

        # Test staging environment with missing variables
        env.set('ENVIRONMENT', 'staging', 'test')
        result = env.validate_staging_database_credentials()
        assert result['valid'] is False
        assert any('Missing required' in issue for issue in result['issues'])

        # Test staging environment with valid variables
        env.set('POSTGRES_HOST', 'staging-db.example.com', 'test')
        env.set('POSTGRES_USER', 'postgres', 'test')
        env.set('POSTGRES_PASSWORD', 'secure_staging_password_123', 'test')
        env.set('POSTGRES_DB', 'netra_staging', 'test')

        result = env.validate_staging_database_credentials()
        assert result['valid'] is True

    def test_caching_functionality(self):
        """Test environment caching functionality (analytics_service feature)."""
        env = get_env()
        env.enable_isolation()

        # Set a value and verify it's accessible
        env.set('CACHE_TEST', 'cached_value', 'test')
        assert env.get('CACHE_TEST') == 'cached_value'

        # Clear cache and verify functionality still works
        env.clear_cache()
        assert env.get('CACHE_TEST') == 'cached_value'  # Should still work from isolated_vars

        # Test get_all_with_prefix functionality
        env.set('PREFIX_VAR1', 'value1', 'test')
        env.set('PREFIX_VAR2', 'value2', 'test')
        env.set('OTHER_VAR', 'other', 'test')

        prefixed_vars = env.get_all_with_prefix('PREFIX_')
        assert len(prefixed_vars) == 2
        assert 'PREFIX_VAR1' in prefixed_vars
        assert 'PREFIX_VAR2' in prefixed_vars
        assert 'OTHER_VAR' not in prefixed_vars

    def test_comprehensive_validation(self):
        """Test comprehensive validation functionality (dev_launcher feature)."""
        env = get_env()
        env.enable_isolation()

        # Test with missing required variables
        result = env.validate_all()
        assert result.is_valid is False
        assert len(result.errors) > 0

        # Test with required variables present
        env.set('DATABASE_URL', 'postgresql://user:pass@host:5432/db', 'test')
        env.set('JWT_SECRET_KEY', 'a' * 32, 'test')  # 32 chars for security
        env.set('SECRET_KEY', 'b' * 32, 'test')

        result = env.validate_all()
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_protected_variables(self):
        """Test protected variable functionality."""
        env = get_env()
        env.enable_isolation()

        # Set a variable and protect it
        env.set('PROTECTED_VAR', 'original', 'test')
        env.protect('PROTECTED_VAR')

        assert env.is_protected('PROTECTED_VAR') is True

        # Try to modify protected variable (should fail)
        result = env.set('PROTECTED_VAR', 'modified', 'test')
        assert result is False
        assert env.get('PROTECTED_VAR') == 'original'  # Should remain unchanged

        # Force modification should work
        result = env.set('PROTECTED_VAR', 'forced', 'test', force=True)
        assert result is True
        assert env.get('PROTECTED_VAR') == 'forced'

        # Unprotect and modify
        env.unprotect_variable('PROTECTED_VAR')
        assert env.is_protected('PROTECTED_VAR') is False
        result = env.set('PROTECTED_VAR', 'unprotected', 'test')
        assert result is True

    def test_subprocess_environment(self):
        """Test subprocess environment management."""
        env = get_env()
        env.enable_isolation()

        # Set some test variables
        env.set('SUBPROCESS_VAR', 'subprocess_value', 'test')

        # Get subprocess environment
        subprocess_env = env.get_subprocess_env()

        # Should contain our variable
        assert 'SUBPROCESS_VAR' in subprocess_env
        assert subprocess_env['SUBPROCESS_VAR'] == 'subprocess_value'

        # Should contain system variables
        system_vars = ['PATH']
        for var in system_vars:
            if var in os.environ:
                assert var in subprocess_env

        # Test with additional vars
        additional_vars = {'EXTRA_VAR': 'extra_value'}
        subprocess_env = env.get_subprocess_env(additional_vars)
        assert 'EXTRA_VAR' in subprocess_env
        assert subprocess_env['EXTRA_VAR'] == 'extra_value'

    def test_convenience_functions(self):
        """Test convenience functions work with unified implementation."""
        # Test setenv/getenv/delenv functions
        result = setenv('CONVENIENCE_TEST', 'convenience_value', 'test')
        assert result is True

        value = getenv('CONVENIENCE_TEST')
        assert value == 'convenience_value'

        result = delenv('CONVENIENCE_TEST')
        assert result is True

        value = getenv('CONVENIENCE_TEST')
        assert value is None

    def test_file_loading(self):
        """Test loading environment variables from files."""
        env = get_env()
        env.enable_isolation()

        # Create a temporary .env file
        test_env_content = '''# Test comment
TEST_FILE_VAR1=value1
TEST_FILE_VAR2="value with spaces"
TEST_FILE_VAR3='single quoted'
'''

        test_file = Path("test_env_file.env")
        test_file.write_text(test_env_content)

        try:
            # Load from file
            loaded_count, errors = env.load_from_file(test_file)

            assert loaded_count == 3
            assert len(errors) == 0

            assert env.get('TEST_FILE_VAR1') == 'value1'
            assert env.get('TEST_FILE_VAR2') == 'value with spaces'
            assert env.get('TEST_FILE_VAR3') == 'single quoted'

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

    def test_change_callbacks(self):
        """Test change callback functionality."""
        env = get_env()
        env.enable_isolation()

        callback_calls = []

        def test_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))

        # Add callback
        env.add_change_callback(test_callback)

        # Make changes
        env.set('CALLBACK_TEST', 'value1', 'test')
        env.set('CALLBACK_TEST', 'value2', 'test')
        env.delete('CALLBACK_TEST')

        # Verify callbacks were called
        assert len(callback_calls) == 3
        assert callback_calls[0] == ('CALLBACK_TEST', None, 'value1')
        assert callback_calls[1] == ('CALLBACK_TEST', 'value1', 'value2')
        assert callback_calls[2] == ('CALLBACK_TEST', 'value2', None)

        # Remove callback
        env.remove_change_callback(test_callback)

        # Make another change - should not trigger callback
        callback_calls.clear()
        env.set('CALLBACK_TEST2', 'value', 'test')
        assert len(callback_calls) == 0

    def test_environment_detection_methods(self):
        """Test environment detection methods."""
        env = get_env()
        env.enable_isolation()

        # Test development environment
        env.set('ENVIRONMENT', 'development', 'test')
        assert env.get_environment_name() == 'development'
        assert env.is_development() is True
        assert env.is_staging() is False
        assert env.is_production() is False
        assert env.is_test() is False

        # Test staging environment
        env.set('ENVIRONMENT', 'staging', 'test')
        assert env.get_environment_name() == 'staging'
        assert env.is_staging() is True
        assert env.is_development() is False

        # Test production environment
        env.set('ENVIRONMENT', 'production', 'test')
        assert env.get_environment_name() == 'production'
        assert env.is_production() is True
        assert env.is_staging() is False

        # Test test environment
        env.set('ENVIRONMENT', 'test', 'test')
        assert env.get_environment_name() == 'test'
        assert env.is_test() is True
        assert env.is_development() is False

    def test_reset_functionality(self):
        """Test reset and restore functionality."""
        env = get_env()

        # Set some initial values in os.environ
        env.set('RESET_TEST1', 'original1', "test")
        env.set('RESET_TEST2', 'original2', "test")

        # Enable isolation and modify values
        env.enable_isolation()
        env.set('RESET_TEST1', 'modified1', 'test')
        env.set('RESET_TEST3', 'new_value', 'test')

        # Test basic reset
        env.reset()
        assert env.is_isolated() is False

        # Test reset to original
        env.enable_isolation()
        env.set('RESET_TEST1', 'modified_again', 'test')

        env.reset_to_original()
        # Should restore to original state
        assert env.get('RESET_TEST1') == 'original1'
        assert env.get('RESET_TEST2') == 'original2'

    def test_debug_information(self):
        """Test debug information functionality."""
        env = get_env()
        env.enable_isolation()

        # Add some state
        env.set('DEBUG_TEST', 'debug_value', 'test')
        env.protect('DEBUG_TEST')

        debug_info = env.get_debug_info()

        # Verify expected debug information
        assert 'isolation_enabled' in debug_info
        assert debug_info['isolation_enabled'] is True
        assert 'isolated_vars_count' in debug_info
        assert debug_info['isolated_vars_count'] > 0
        assert 'protected_vars' in debug_info
        assert 'DEBUG_TEST' in debug_info['protected_vars']
        assert 'tracked_sources' in debug_info
        assert 'DEBUG_TEST' in debug_info['tracked_sources']


class TestBackwardsCompatibility:
    """Test backwards compatibility with legacy interfaces."""

    def test_environment_validator_compatibility(self):
        """Test EnvironmentValidator backwards compatibility."""
        from shared.isolated_environment import EnvironmentValidator

        validator = EnvironmentValidator()

        # Test basic validation
        result = validator.validate_all()
        assert isinstance(result, ValidationResult)

        # Test with fallbacks
        result = validator.validate_with_fallbacks()
        assert isinstance(result, ValidationResult)

        # Test suggestions
        suggestions = validator.get_fix_suggestions(result)
        assert isinstance(suggestions, list)

    def test_secret_loader_compatibility(self):
        """Test SecretLoader backwards compatibility."""
        from shared.isolated_environment import SecretLoader

        loader = SecretLoader()

        # Test basic functionality
        assert loader.load_secrets() is True

        # Test get/set secret
        loader.set_secret('TEST_SECRET', 'secret_value')
        assert loader.get_secret('TEST_SECRET') == 'secret_value'
        assert loader.get_secret('NON_EXISTENT_SECRET') is None
        assert loader.get_secret('NON_EXISTENT_SECRET', 'default') == 'default'

    def test_legacy_function_compatibility(self):
        """Test legacy function compatibility."""
        from shared.isolated_environment import load_secrets, get_environment_manager

        # Test load_secrets function
        assert load_secrets() is True

        # Test get_environment_manager function
        env_manager = get_environment_manager()
        assert env_manager is not None
        # Should work like IsolatedEnvironment
        assert hasattr(env_manager, 'get')
        assert hasattr(env_manager, 'set')


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_file_loading_errors(self):
        """Test file loading error handling."""
        env = get_env()
        env.enable_isolation()

        # Test non-existent file
        loaded_count, errors = env.load_from_file(Path("non_existent_file.env"))
        assert loaded_count == 0
        assert len(errors) > 0
        assert "File not found" in errors[0]

        # Test malformed file
        malformed_content = "INVALID_LINE_WITHOUT_EQUALS\n"
        test_file = Path("malformed.env")
        test_file.write_text(malformed_content)

        try:
            loaded_count, errors = env.load_from_file(test_file)
            assert loaded_count == 0
            assert len(errors) > 0
            assert "Invalid format" in errors[0]
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_callback_error_handling(self):
        """Test that callback errors don't break environment operations."""
        env = get_env()
        env.enable_isolation()

        def failing_callback(key, old_value, new_value):
            raise Exception("Callback error")

        env.add_change_callback(failing_callback)

        # Should not raise exception despite callback error
        result = env.set('ERROR_TEST', 'value', 'test')
        assert result is True
        assert env.get('ERROR_TEST') == 'value'

    def test_sanitization_edge_cases(self):
        """Test value sanitization edge cases."""
        env = get_env()
        env.enable_isolation()

        # Test None value
        env.set('NONE_TEST', None, 'test')
        assert env.get('NONE_TEST') == 'None'  # Converted to string

        # Test empty string
        env.set('EMPTY_TEST', '', 'test')
        assert env.get('EMPTY_TEST') == ''

        # Test non-string value
        env.set('INT_TEST', 123, 'test')
        assert env.get('INT_TEST') == '123'  # Converted to string


if __name__ == "__main__":
    pytest.main([__file__, "-v"])