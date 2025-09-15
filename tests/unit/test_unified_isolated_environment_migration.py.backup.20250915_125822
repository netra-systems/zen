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
from shared.isolated_environment import get_env, IsolatedEnvironment, ValidationResult, setenv, getenv, delenv

@pytest.mark.unit
class TestUnifiedIsolatedEnvironment:
    """Test the unified IsolatedEnvironment implementation."""

    @pytest.fixture
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        env = get_env()
        original_env = env.get_all()
        if env.is_isolated():
            env.disable_isolation()
        yield
        env.disable_isolation()
        if env.is_isolated():
            env.clear()
        env.update(original_env, 'test')

    def test_singleton_behavior(self):
        """Test that IsolatedEnvironment maintains singleton behavior."""
        env1 = get_env()
        env2 = get_env()
        env3 = IsolatedEnvironment()
        env4 = IsolatedEnvironment.get_instance()
        assert env1 is env2
        assert env2 is env3
        assert env3 is env4
        instances = []

        def get_instance():
            instances.append(get_env())
        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        unique_instances = set((id(instance) for instance in instances))
        assert len(unique_instances) == 1

    def test_basic_environment_operations(self):
        """Test basic get/set/delete operations."""
        env = get_env()
        env.set('TEST_BASIC', 'original_value', 'test')
        assert env.get('TEST_BASIC') == 'original_value'
        assert env.get('NON_EXISTENT') is None
        assert env.get('NON_EXISTENT', 'default') == 'default'
        assert env.exists('TEST_BASIC') is True
        assert env.exists('NON_EXISTENT') is False
        env.delete('TEST_BASIC')
        assert env.exists('TEST_BASIC') is False

    def test_isolation_mode_functionality(self):
        """Test isolation mode prevents os.environ pollution."""
        env = get_env()
        env.set('TEST_ISOLATION', 'os_value', 'test')
        env.enable_isolation()
        assert env.is_isolated() is True
        env.set('TEST_ISOLATION', 'isolated_value', 'test')
        assert env.get('TEST_ISOLATION') == 'isolated_value'
        assert os.environ['TEST_ISOLATION'] == 'os_value'
        env.set('TEST_NEW_VAR', 'new_value', 'test')
        assert env.get('TEST_NEW_VAR') == 'new_value'
        assert 'TEST_NEW_VAR' not in os.environ
        env.disable_isolation()
        assert env.is_isolated() is False
        assert env.get('TEST_ISOLATION') == 'isolated_value'

    def test_source_tracking(self):
        """Test that all modifications include source tracking."""
        env = get_env()
        env.enable_isolation()
        env.set('TEST_SOURCE', 'value1', 'unit_test')
        assert env.get_variable_source('TEST_SOURCE') == 'unit_test'
        env.set('TEST_SOURCE', 'value2', 'different_source')
        assert env.get_variable_source('TEST_SOURCE') == 'different_source'
        updates = {'VAR1': 'val1', 'VAR2': 'val2'}
        env.update(updates, 'bulk_update')
        assert env.get_variable_source('VAR1') == 'bulk_update'
        assert env.get_variable_source('VAR2') == 'bulk_update'

    def test_value_sanitization(self):
        """Test that values are sanitized while preserving database URLs."""
        env = get_env()
        env.enable_isolation()
        test_value = 'normal_value\x00\x01with_control_chars'
        env.set('TEST_SANITIZE', test_value, 'test')
        sanitized = env.get('TEST_SANITIZE')
        assert '\x00' not in sanitized
        assert '\x01' not in sanitized
        assert 'normal_value' in sanitized
        assert 'with_control_chars' in sanitized
        db_url = 'postgresql://user:p@ss!w0rd@host:5432/db'
        env.set('DATABASE_URL', db_url, 'test')
        retrieved = env.get('DATABASE_URL')
        assert 'p@ss!w0rd' in retrieved

    def test_shell_command_expansion(self):
        """Test shell command expansion functionality (auth_service feature)."""
        env = get_env()
        normal_value = env._expand_shell_commands('normal_value')
        assert normal_value == 'normal_value'
        env.set('EXPAND_TEST', 'expanded_value', 'test')
        test_value = env._expand_shell_commands('prefix_${EXPAND_TEST}_suffix')
        assert test_value == 'prefix_${EXPAND_TEST}_suffix'
        shell_value = env._expand_shell_commands('$(echo test)')
        assert shell_value == '$(echo test)'

    def test_staging_database_validation(self):
        """Test staging database credential validation (auth_service feature)."""
        env = get_env()
        env.enable_isolation()
        env.set('ENVIRONMENT', 'development', 'test')
        result = env.validate_staging_database_credentials()
        assert result['warnings']
        env.set('ENVIRONMENT', 'staging', 'test')
        result = env.validate_staging_database_credentials()
        assert result['valid'] is False
        assert any(('Missing required' in issue for issue in result['issues']))
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
        env.set('CACHE_TEST', 'cached_value', 'test')
        assert env.get('CACHE_TEST') == 'cached_value'
        env.clear_cache()
        assert env.get('CACHE_TEST') == 'cached_value'
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
        result = env.validate_all()
        assert result.is_valid is False
        assert len(result.errors) > 0
        env.set('DATABASE_URL', 'postgresql://user:pass@host:5432/db', 'test')
        env.set('JWT_SECRET_KEY', 'a' * 32, 'test')
        env.set('SECRET_KEY', 'b' * 32, 'test')
        result = env.validate_all()
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_protected_variables(self):
        """Test protected variable functionality."""
        env = get_env()
        env.enable_isolation()
        env.set('PROTECTED_VAR', 'original', 'test')
        env.protect('PROTECTED_VAR')
        assert env.is_protected('PROTECTED_VAR') is True
        result = env.set('PROTECTED_VAR', 'modified', 'test')
        assert result is False
        assert env.get('PROTECTED_VAR') == 'original'
        result = env.set('PROTECTED_VAR', 'forced', 'test', force=True)
        assert result is True
        assert env.get('PROTECTED_VAR') == 'forced'
        env.unprotect_variable('PROTECTED_VAR')
        assert env.is_protected('PROTECTED_VAR') is False
        result = env.set('PROTECTED_VAR', 'unprotected', 'test')
        assert result is True

    def test_subprocess_environment(self):
        """Test subprocess environment management."""
        env = get_env()
        env.enable_isolation()
        env.set('SUBPROCESS_VAR', 'subprocess_value', 'test')
        subprocess_env = env.get_subprocess_env()
        assert 'SUBPROCESS_VAR' in subprocess_env
        assert subprocess_env['SUBPROCESS_VAR'] == 'subprocess_value'
        system_vars = ['PATH']
        for var in system_vars:
            if var in os.environ:
                assert var in subprocess_env
        additional_vars = {'EXTRA_VAR': 'extra_value'}
        subprocess_env = env.get_subprocess_env(additional_vars)
        assert 'EXTRA_VAR' in subprocess_env
        assert subprocess_env['EXTRA_VAR'] == 'extra_value'

    def test_convenience_functions(self):
        """Test convenience functions work with unified implementation."""
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
        test_env_content = '# Test comment\nTEST_FILE_VAR1=value1\nTEST_FILE_VAR2="value with spaces"\nTEST_FILE_VAR3=\'single quoted\'\n'
        test_file = Path('test_env_file.env')
        test_file.write_text(test_env_content)
        try:
            loaded_count, errors = env.load_from_file(test_file)
            assert loaded_count == 3
            assert len(errors) == 0
            assert env.get('TEST_FILE_VAR1') == 'value1'
            assert env.get('TEST_FILE_VAR2') == 'value with spaces'
            assert env.get('TEST_FILE_VAR3') == 'single quoted'
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_change_callbacks(self):
        """Test change callback functionality."""
        env = get_env()
        env.enable_isolation()
        callback_calls = []

        def test_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
        env.add_change_callback(test_callback)
        env.set('CALLBACK_TEST', 'value1', 'test')
        env.set('CALLBACK_TEST', 'value2', 'test')
        env.delete('CALLBACK_TEST')
        assert len(callback_calls) == 3
        assert callback_calls[0] == ('CALLBACK_TEST', None, 'value1')
        assert callback_calls[1] == ('CALLBACK_TEST', 'value1', 'value2')
        assert callback_calls[2] == ('CALLBACK_TEST', 'value2', None)
        env.remove_change_callback(test_callback)
        callback_calls.clear()
        env.set('CALLBACK_TEST2', 'value', 'test')
        assert len(callback_calls) == 0

    def test_environment_detection_methods(self):
        """Test environment detection methods."""
        env = get_env()
        env.enable_isolation()
        env.set('ENVIRONMENT', 'development', 'test')
        assert env.get_environment_name() == 'development'
        assert env.is_development() is True
        assert env.is_staging() is False
        assert env.is_production() is False
        assert env.is_test() is False
        env.set('ENVIRONMENT', 'staging', 'test')
        assert env.get_environment_name() == 'staging'
        assert env.is_staging() is True
        assert env.is_development() is False
        env.set('ENVIRONMENT', 'production', 'test')
        assert env.get_environment_name() == 'production'
        assert env.is_production() is True
        assert env.is_staging() is False
        env.set('ENVIRONMENT', 'test', 'test')
        assert env.get_environment_name() == 'test'
        assert env.is_test() is True
        assert env.is_development() is False

    def test_reset_functionality(self):
        """Test reset and restore functionality."""
        env = get_env()
        env.set('RESET_TEST1', 'original1', 'test')
        env.set('RESET_TEST2', 'original2', 'test')
        env.enable_isolation()
        env.set('RESET_TEST1', 'modified1', 'test')
        env.set('RESET_TEST3', 'new_value', 'test')
        env.reset()
        assert env.is_isolated() is False
        env.enable_isolation()
        env.set('RESET_TEST1', 'modified_again', 'test')
        env.reset_to_original()
        assert env.get('RESET_TEST1') == 'original1'
        assert env.get('RESET_TEST2') == 'original2'

    def test_debug_information(self):
        """Test debug information functionality."""
        env = get_env()
        env.enable_isolation()
        env.set('DEBUG_TEST', 'debug_value', 'test')
        env.protect('DEBUG_TEST')
        debug_info = env.get_debug_info()
        assert 'isolation_enabled' in debug_info
        assert debug_info['isolation_enabled'] is True
        assert 'isolated_vars_count' in debug_info
        assert debug_info['isolated_vars_count'] > 0
        assert 'protected_vars' in debug_info
        assert 'DEBUG_TEST' in debug_info['protected_vars']
        assert 'tracked_sources' in debug_info
        assert 'DEBUG_TEST' in debug_info['tracked_sources']

@pytest.mark.unit
class TestBackwardsCompatibility:
    """Test backwards compatibility with legacy interfaces."""

    def test_environment_validator_compatibility(self):
        """Test EnvironmentValidator backwards compatibility."""
        from shared.isolated_environment import EnvironmentValidator
        validator = EnvironmentValidator()
        result = validator.validate_all()
        assert isinstance(result, ValidationResult)
        result = validator.validate_with_fallbacks()
        assert isinstance(result, ValidationResult)
        suggestions = validator.get_fix_suggestions(result)
        assert isinstance(suggestions, list)

    def test_secret_loader_compatibility(self):
        """Test SecretLoader backwards compatibility."""
        from shared.isolated_environment import SecretLoader
        loader = SecretLoader()
        assert loader.load_secrets() is True
        loader.set_secret('TEST_SECRET', 'secret_value')
        assert loader.get_secret('TEST_SECRET') == 'secret_value'
        assert loader.get_secret('NON_EXISTENT_SECRET') is None
        assert loader.get_secret('NON_EXISTENT_SECRET', 'default') == 'default'

    def test_legacy_function_compatibility(self):
        """Test legacy function compatibility."""
        from shared.isolated_environment import load_secrets, get_environment_manager
        assert load_secrets() is True
        env_manager = get_environment_manager()
        assert env_manager is not None
        assert hasattr(env_manager, 'get')
        assert hasattr(env_manager, 'set')

@pytest.mark.unit
class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_file_loading_errors(self):
        """Test file loading error handling."""
        env = get_env()
        env.enable_isolation()
        loaded_count, errors = env.load_from_file(Path('non_existent_file.env'))
        assert loaded_count == 0
        assert len(errors) > 0
        assert 'File not found' in errors[0]
        malformed_content = 'INVALID_LINE_WITHOUT_EQUALS\n'
        test_file = Path('malformed.env')
        test_file.write_text(malformed_content)
        try:
            loaded_count, errors = env.load_from_file(test_file)
            assert loaded_count == 0
            assert len(errors) > 0
            assert 'Invalid format' in errors[0]
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_callback_error_handling(self):
        """Test that callback errors don't break environment operations."""
        env = get_env()
        env.enable_isolation()

        def failing_callback(key, old_value, new_value):
            raise Exception('Callback error')
        env.add_change_callback(failing_callback)
        result = env.set('ERROR_TEST', 'value', 'test')
        assert result is True
        assert env.get('ERROR_TEST') == 'value'

    def test_sanitization_edge_cases(self):
        """Test value sanitization edge cases."""
        env = get_env()
        env.enable_isolation()
        env.set('NONE_TEST', None, 'test')
        assert env.get('NONE_TEST') == 'None'
        env.set('EMPTY_TEST', '', 'test')
        assert env.get('EMPTY_TEST') == ''
        env.set('INT_TEST', 123, 'test')
        assert env.get('INT_TEST') == '123'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')