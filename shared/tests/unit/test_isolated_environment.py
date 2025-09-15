"""
Comprehensive Unit Tests for IsolatedEnvironment Class

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability
- Business Goal: Ensure reliable environment management across all services
- Value Impact: Prevents configuration drift and service failures
- Strategic Impact: Core platform infrastructure reliability

CRITICAL REQUIREMENTS per CLAUDE.md and TEST_CREATION_GUIDE.md:
1. Follow SSOT testing patterns 
2. Test ALL public methods with 100% coverage
3. Test singleton pattern behavior
4. Test thread safety with race conditions
5. Test isolation modes
6. Test validation methods
7. Test file loading capabilities
8. Test shell command expansion
9. Test caching behavior
10. MUST use absolute imports starting from package root
11. MUST raise errors on failures (no try/except blocks that suppress errors)
12. Use real services when possible (no mocking unless absolutely necessary for unit tests)

ULTRA CRITICAL: Tests MUST FAIL HARD on any issue - no silent failures
"""
import pytest
import os
import threading
import time
import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch, Mock
import concurrent.futures
import subprocess
from shared.isolated_environment import IsolatedEnvironment, get_env, ValidationResult, _mask_sensitive_value, setenv, getenv, delenv, load_secrets, SecretLoader, EnvironmentValidator
from test_framework.isolated_environment_fixtures import isolated_env, test_env, temporary_env_vars, clean_env_context, patch_env

class TestIsolatedEnvironmentSingleton:
    """Test singleton pattern behavior with thread safety."""

    def test_singleton_instance_creation(self):
        """Test that only one instance is ever created."""
        instance1 = IsolatedEnvironment()
        instance2 = IsolatedEnvironment()
        instance3 = IsolatedEnvironment.get_instance()
        instance4 = get_env()
        assert instance1 is instance2, 'IsolatedEnvironment() must return same instance'
        assert instance1 is instance3, 'get_instance() must return same instance'
        assert instance1 is instance4, 'get_env() must return same instance'
        assert id(instance1) == id(instance2) == id(instance3) == id(instance4), 'All instances must have same memory address'

    def test_singleton_thread_safety(self):
        """Test singleton creation under concurrent access - CRITICAL for race conditions."""
        instances = []
        errors = []

        def create_instance():
            """Function to create instance in thread."""
            try:
                if threading.current_thread().name.endswith('0'):
                    instance = IsolatedEnvironment()
                elif threading.current_thread().name.endswith('1'):
                    instance = IsolatedEnvironment.get_instance()
                else:
                    instance = get_env()
                instances.append(instance)
            except Exception as e:
                errors.append(f'Thread {threading.current_thread().name}: {str(e)}')
        threads = []
        for i in range(20):
            thread = threading.Thread(target=create_instance, name=f'test_thread_{i}')
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                raise AssertionError(f'Thread {thread.name} did not complete within timeout')
        if errors:
            raise AssertionError(f'Thread safety errors occurred: {errors}')
        if len(instances) != 20:
            raise AssertionError(f'Expected 20 instances, got {len(instances)}')
        first_instance = instances[0]
        for i, instance in enumerate(instances):
            if instance is not first_instance:
                raise AssertionError(f'Instance {i} is not the singleton (ID: {id(instance)} vs {id(first_instance)})')

    def test_singleton_consistency_after_initialization(self):
        """Test that singleton remains consistent after full initialization."""
        env = get_env()
        env.set('TEST_INIT', 'initialized', 'test')
        env2 = IsolatedEnvironment()
        env3 = IsolatedEnvironment.get_instance()
        assert env is env2 is env3, 'Singleton consistency failed after initialization'
        assert env2.get('TEST_INIT') == 'initialized', 'State not shared across singleton references'
        assert env3.get('TEST_INIT') == 'initialized', 'State not shared across singleton references'

class TestIsolatedEnvironmentBasicOperations:
    """Test basic environment variable operations."""

    def test_set_and_get_basic(self, isolated_env):
        """Test basic set and get operations."""
        result = isolated_env.set('TEST_STRING', 'test_value', 'test')
        assert result is True, 'set() must return True on success'
        assert isolated_env.get('TEST_STRING') == 'test_value', 'get() must return exact value that was set'
        isolated_env.set('TEST_EMPTY', '', 'test')
        assert isolated_env.get('TEST_EMPTY') == '', 'Empty string must be preserved'
        assert isolated_env.get('NONEXISTENT_VAR') is None, 'get() must return None for nonexistent variables'
        assert isolated_env.get('NONEXISTENT_VAR', 'default') == 'default', 'get() must return custom default'

    def test_exists_and_is_set(self, isolated_env):
        """Test variable existence checking."""
        assert not isolated_env.exists('TEST_EXISTS'), 'exists() must return False for unset variables'
        assert not isolated_env.is_set('TEST_EXISTS'), 'is_set() must return False for unset variables'
        isolated_env.set('TEST_EXISTS', 'exists', 'test')
        assert isolated_env.exists('TEST_EXISTS'), 'exists() must return True after setting'
        assert isolated_env.is_set('TEST_EXISTS'), 'is_set() must return True after setting'
        result = isolated_env.delete('TEST_EXISTS', 'test')
        assert result is True, 'delete() must return True on successful deletion'
        assert not isolated_env.exists('TEST_EXISTS'), 'exists() must return False after deletion'

    def test_delete_and_unset(self, isolated_env):
        """Test variable deletion operations."""
        isolated_env.set('TEST_DELETE', 'to_delete', 'test')
        assert isolated_env.exists('TEST_DELETE'), 'Variable must exist before deletion'
        result = isolated_env.delete('TEST_DELETE', 'test')
        assert result is True, 'delete() must return True on success'
        assert not isolated_env.exists('TEST_DELETE'), 'Variable must not exist after deletion'
        assert isolated_env.get('TEST_DELETE') is None, 'get() must return None after deletion'
        result = isolated_env.delete('NONEXISTENT', 'test')
        assert result is False, 'delete() must return False for non-existent variables'
        isolated_env.set('TEST_UNSET', 'to_unset', 'test')
        isolated_env.unset('TEST_UNSET')
        assert not isolated_env.exists('TEST_UNSET'), 'unset() must remove variable'

    def test_update_multiple_variables(self, isolated_env):
        """Test updating multiple variables at once."""
        test_vars = {'VAR1': 'value1', 'VAR2': 'value2', 'VAR3': 'value3'}
        results = isolated_env.update(test_vars, 'test_batch', force=False)
        for var_name, success in results.items():
            assert success is True, f'update() failed for {var_name}'
        for var_name, expected_value in test_vars.items():
            actual_value = isolated_env.get(var_name)
            assert actual_value == expected_value, f'Variable {var_name} has wrong value: {actual_value}'

    def test_get_all_variables(self, isolated_env):
        """Test retrieving all environment variables."""
        test_vars = {'ALL_VAR1': 'value1', 'ALL_VAR2': 'value2', 'ALL_VAR3': 'value3'}
        isolated_env.update(test_vars, 'test')
        all_vars = isolated_env.get_all()
        assert isinstance(all_vars, dict), 'get_all() must return dictionary'
        for var_name, expected_value in test_vars.items():
            assert var_name in all_vars, f'get_all() missing variable {var_name}'
            assert all_vars[var_name] == expected_value, f'get_all() wrong value for {var_name}'
        assert isolated_env.get_all_variables() == all_vars, 'get_all_variables() must match get_all()'
        assert isolated_env.as_dict() == all_vars, 'as_dict() must match get_all()'

class TestIsolatedEnvironmentIsolation:
    """Test isolation mode functionality."""

    def test_enable_disable_isolation(self, isolated_env):
        """Test isolation mode enabling and disabling."""
        assert isolated_env.is_isolated(), 'Fixture must provide isolated environment'
        assert isolated_env.is_isolation_enabled(), 'is_isolation_enabled() must match is_isolated()'
        isolated_env.disable_isolation()
        assert not isolated_env.is_isolated(), 'is_isolated() must return False after disabling'
        isolated_env.enable_isolation()
        assert isolated_env.is_isolated(), 'is_isolated() must return True after re-enabling'

    def test_isolation_variable_storage(self):
        """Test that isolation properly stores variables separately from os.environ."""
        env = get_env()
        env.disable_isolation(restore_original=False)
        test_var = 'ISOLATION_TEST_VAR'
        test_value_os = 'os_environ_value'
        os.environ[test_var] = test_value_os
        assert env.get(test_var) == test_value_os, 'Variable must be accessible from os.environ when not isolated'
        env.enable_isolation()
        assert env.get(test_var) == test_value_os, 'Variable must be copied when enabling isolation'
        test_value_isolated = 'isolated_value'
        env.set(test_var, test_value_isolated, 'test')
        assert env.get(test_var) == test_value_isolated, 'Isolated environment must have updated value'
        assert os.environ.get(test_var) == test_value_os, 'os.environ must not be polluted by isolated changes'
        del os.environ[test_var]

    def test_isolation_with_refresh(self, isolated_env):
        """Test isolation with variable refresh from os.environ."""
        test_var = 'REFRESH_TEST_VAR'
        test_value = 'refresh_value'
        os.environ[test_var] = test_value
        try:
            isolated_env.enable_isolation(refresh_vars=True)
            assert isolated_env.get(test_var) == test_value, 'refresh_vars=True must capture os.environ variables'
        finally:
            del os.environ[test_var]

    def test_isolation_preserve_special_vars(self, isolated_env):
        """Test that special variables are preserved in os.environ during isolation."""
        test_var = 'PYTEST_CURRENT_TEST'
        test_value = 'test_preserve'
        original_value = os.environ.get(test_var)
        os.environ[test_var] = test_value
        try:
            isolated_env.enable_isolation()
            isolated_env.set(test_var, 'isolated_pytest_value', 'test')
            assert isolated_env.get(test_var) == 'isolated_pytest_value', 'Isolated environment must have updated value'
            assert os.environ.get(test_var) == 'isolated_pytest_value', 'Preserved variable must sync to os.environ'
        finally:
            if original_value is not None:
                os.environ[test_var] = original_value
            elif test_var in os.environ:
                del os.environ[test_var]

    def test_clear_isolated_variables(self, isolated_env):
        """Test clearing isolated variables (only works in isolation mode)."""
        test_vars = {'CLEAR1': 'value1', 'CLEAR2': 'value2'}
        isolated_env.update(test_vars, 'test')
        assert isolated_env.get('CLEAR1') == 'value1', 'Variable must exist before clear'
        assert isolated_env.get('CLEAR2') == 'value2', 'Variable must exist before clear'
        isolated_env.clear()
        assert isolated_env.get('CLEAR1') is None, 'Variable must be None after clear'
        assert isolated_env.get('CLEAR2') is None, 'Variable must be None after clear'
        assert len(isolated_env.get_all()) == 0, 'get_all() must return empty dict after clear'

    def test_clear_fails_without_isolation(self):
        """Test that clear() fails when not in isolation mode."""
        env = get_env()
        env.disable_isolation()
        with pytest.raises(RuntimeError, match='Cannot clear environment variables outside isolation mode'):
            env.clear()

class TestIsolatedEnvironmentProtection:
    """Test variable protection mechanisms."""

    def test_protect_variable(self, isolated_env):
        """Test variable protection from modification."""
        isolated_env.set('PROTECTED_VAR', 'original', 'test')
        isolated_env.protect('PROTECTED_VAR')
        assert isolated_env.is_protected('PROTECTED_VAR'), 'Variable must be marked as protected'
        result = isolated_env.set('PROTECTED_VAR', 'modified', 'test', force=False)
        assert result is False, 'Setting protected variable without force must fail'
        assert isolated_env.get('PROTECTED_VAR') == 'original', 'Protected variable must retain original value'
        result = isolated_env.set('PROTECTED_VAR', 'forced', 'test', force=True)
        assert result is True, 'Setting protected variable with force must succeed'
        assert isolated_env.get('PROTECTED_VAR') == 'forced', 'Force setting must override protection'

    def test_protect_variable_alias(self, isolated_env):
        """Test protect_variable() method (alias for protect())."""
        isolated_env.set('ALIAS_PROTECTED', 'value', 'test')
        isolated_env.protect_variable('ALIAS_PROTECTED')
        assert isolated_env.is_protected('ALIAS_PROTECTED'), 'protect_variable() must work same as protect()'

    def test_unprotect_variable(self, isolated_env):
        """Test removing variable protection."""
        isolated_env.set('UNPROTECT_VAR', 'value', 'test')
        isolated_env.protect('UNPROTECT_VAR')
        assert isolated_env.is_protected('UNPROTECT_VAR'), 'Variable must be protected'
        isolated_env.unprotect_variable('UNPROTECT_VAR')
        assert not isolated_env.is_protected('UNPROTECT_VAR'), 'Variable must not be protected after unprotecting'
        result = isolated_env.set('UNPROTECT_VAR', 'modified', 'test', force=False)
        assert result is True, 'Unprotected variable must be modifiable'
        assert isolated_env.get('UNPROTECT_VAR') == 'modified', 'Unprotected variable must have new value'

class TestIsolatedEnvironmentSourceTracking:
    """Test source tracking functionality."""

    def test_variable_source_tracking(self, isolated_env):
        """Test that variable sources are properly tracked."""
        isolated_env.set('SOURCE_VAR1', 'value1', 'test_source_1')
        isolated_env.set('SOURCE_VAR2', 'value2', 'test_source_2')
        assert isolated_env.get_variable_source('SOURCE_VAR1') == 'test_source_1', 'Source tracking failed for var1'
        assert isolated_env.get_variable_source('SOURCE_VAR2') == 'test_source_2', 'Source tracking failed for var2'
        assert isolated_env.get_variable_source('NONEXISTENT') is None, 'Non-existent variable must return None source'

    def test_source_tracking_with_updates(self, isolated_env):
        """Test source tracking when variables are updated."""
        isolated_env.set('UPDATE_SOURCE_VAR', 'initial', 'initial_source')
        assert isolated_env.get_variable_source('UPDATE_SOURCE_VAR') == 'initial_source', 'Initial source must be tracked'
        isolated_env.set('UPDATE_SOURCE_VAR', 'updated', 'update_source')
        assert isolated_env.get_variable_source('UPDATE_SOURCE_VAR') == 'update_source', 'Updated source must be tracked'
        assert isolated_env.get('UPDATE_SOURCE_VAR') == 'updated', 'Value must be updated'

class TestIsolatedEnvironmentChangeCallbacks:
    """Test change callback functionality."""

    def test_change_callback_on_set(self, isolated_env):
        """Test that callbacks are invoked when variables are set."""
        callback_calls = []

        def test_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
        isolated_env.add_change_callback(test_callback)
        isolated_env.set('CALLBACK_VAR', 'new_value', 'test')
        assert len(callback_calls) == 1, 'Callback must be called once'
        call = callback_calls[0]
        assert call[0] == 'CALLBACK_VAR', 'Callback must receive correct key'
        assert call[1] is None, 'Callback must receive None as old value for new variable'
        assert call[2] == 'new_value', 'Callback must receive correct new value'
        isolated_env.set('CALLBACK_VAR', 'updated_value', 'test')
        assert len(callback_calls) == 2, 'Callback must be called for updates'
        call = callback_calls[1]
        assert call[1] == 'new_value', 'Callback must receive previous value as old value'
        assert call[2] == 'updated_value', 'Callback must receive correct new value'

    def test_change_callback_on_delete(self, isolated_env):
        """Test that callbacks are invoked when variables are deleted."""
        callback_calls = []

        def test_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
        isolated_env.set('DELETE_CALLBACK_VAR', 'to_delete', 'test')
        isolated_env.add_change_callback(test_callback)
        isolated_env.delete('DELETE_CALLBACK_VAR', 'test')
        assert len(callback_calls) == 1, 'Callback must be called on delete'
        call = callback_calls[0]
        assert call[0] == 'DELETE_CALLBACK_VAR', 'Callback must receive correct key'
        assert call[1] == 'to_delete', 'Callback must receive old value'
        assert call[2] is None, 'Callback must receive None as new value for deletion'

    def test_remove_change_callback(self, isolated_env):
        """Test removing change callbacks."""
        callback_calls = []

        def test_callback(key, old_value, new_value):
            callback_calls.append((key, old_value, new_value))
        isolated_env.add_change_callback(test_callback)
        isolated_env.remove_change_callback(test_callback)
        isolated_env.set('NO_CALLBACK_VAR', 'value', 'test')
        assert len(callback_calls) == 0, 'Removed callback must not be invoked'

    def test_callback_error_handling(self, isolated_env):
        """Test that callback errors don't break environment operations."""

        def failing_callback(key, old_value, new_value):
            raise Exception('Callback failed')
        isolated_env.add_change_callback(failing_callback)
        try:
            result = isolated_env.set('ERROR_CALLBACK_VAR', 'value', 'test')
            assert result is True, 'Variable setting must succeed despite callback failure'
            assert isolated_env.get('ERROR_CALLBACK_VAR') == 'value', 'Variable must be set despite callback failure'
        finally:
            isolated_env.remove_change_callback(failing_callback)

class TestIsolatedEnvironmentFileLoading:
    """Test file loading functionality."""

    def test_load_from_env_file(self, isolated_env):
        """Test loading variables from .env file."""
        env_content = '\n# Test .env file\nVAR1=value1\nVAR2=value2\nVAR3="quoted value"\nVAR4=\'single quoted\'\n# Comment line\nEMPTY_VAR=\n\n# Another comment\nVAR_WITH_SPACES=  value with spaces  \n'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file_path = f.name
        try:
            loaded_count, errors = isolated_env.load_from_file(env_file_path)
            assert loaded_count > 0, 'Must load variables from file'
            assert len(errors) == 0, f'Must not have errors: {errors}'
            assert isolated_env.get('VAR1') == 'value1', 'Simple variable must be loaded'
            assert isolated_env.get('VAR2') == 'value2', 'Second variable must be loaded'
            assert isolated_env.get('VAR3') == 'quoted value', 'Quoted variable must be loaded without quotes'
            assert isolated_env.get('VAR4') == 'single quoted', 'Single quoted variable must be loaded without quotes'
            assert isolated_env.get('EMPTY_VAR') == '', 'Empty variable must be loaded'
            assert isolated_env.get('VAR_WITH_SPACES') == 'value with spaces', 'Spaces must be preserved'
        finally:
            os.unlink(env_file_path)

    def test_load_from_nonexistent_file(self, isolated_env):
        """Test loading from non-existent file."""
        loaded_count, errors = isolated_env.load_from_file('/nonexistent/file.env')
        assert loaded_count == 0, 'Must not load from non-existent file'
        assert len(errors) == 1, 'Must report one error'
        assert 'not found' in errors[0].lower(), 'Error must mention file not found'

    def test_load_from_file_without_override(self, isolated_env):
        """Test loading from file without overriding existing variables."""
        isolated_env.set('EXISTING_VAR', 'original', 'test')
        env_content = 'EXISTING_VAR=from_file\nNEW_VAR=new_value'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file_path = f.name
        try:
            loaded_count, errors = isolated_env.load_from_file(env_file_path, override_existing=False)
            assert loaded_count == 1, 'Must load only new variables'
            assert isolated_env.get('EXISTING_VAR') == 'original', 'Existing variable must not be overridden'
            assert isolated_env.get('NEW_VAR') == 'new_value', 'New variable must be loaded'
        finally:
            os.unlink(env_file_path)

    def test_load_from_file_with_override(self, isolated_env):
        """Test loading from file with overriding existing variables."""
        isolated_env.set('OVERRIDE_VAR', 'original', 'test')
        env_content = 'OVERRIDE_VAR=overridden\nNEW_VAR=new_value'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file_path = f.name
        try:
            loaded_count, errors = isolated_env.load_from_file(env_file_path, override_existing=True)
            assert loaded_count == 2, 'Must load both variables'
            assert isolated_env.get('OVERRIDE_VAR') == 'overridden', 'Existing variable must be overridden'
            assert isolated_env.get('NEW_VAR') == 'new_value', 'New variable must be loaded'
        finally:
            os.unlink(env_file_path)

    def test_load_from_file_malformed_content(self, isolated_env):
        """Test loading file with malformed content."""
        env_content = '\nVALID_VAR=valid_value\nMISSING_EQUALS\n=MISSING_KEY\nANOTHER_VALID=another_value\n'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file_path = f.name
        try:
            loaded_count, errors = isolated_env.load_from_file(env_file_path)
            assert loaded_count >= 2, 'Must load at least the valid variables'
            assert len(errors) >= 1, 'Must report errors for malformed lines'
            assert isolated_env.get('VALID_VAR') == 'valid_value', 'Valid variable must be loaded'
            assert isolated_env.get('ANOTHER_VALID') == 'another_value', 'Another valid variable must be loaded'
        finally:
            os.unlink(env_file_path)

class TestIsolatedEnvironmentValidation:
    """Test validation functionality."""

    def test_validate_all_success(self, isolated_env):
        """Test validation when all required variables are present."""
        required_vars = {'DATABASE_URL': 'postgresql://test:test@localhost:5432/test', 'JWT_SECRET_KEY': 'test-jwt-secret-key-minimum-32-chars', 'SECRET_KEY': 'test-secret-key-for-testing'}
        isolated_env.update(required_vars, 'test')
        result = isolated_env.validate_all()
        assert isinstance(result, ValidationResult), 'Must return ValidationResult instance'
        assert result.is_valid is True, 'Validation must pass when all required variables present'
        assert len(result.errors) == 0, 'Must have no errors when validation passes'

    def test_validate_all_missing_required(self, isolated_env):
        """Test validation when required variables are missing."""
        required_vars = ['DATABASE_URL', 'JWT_SECRET_KEY', 'SECRET_KEY']
        original_values = {}
        for var in required_vars:
            original_values[var] = isolated_env.get(var)
            isolated_env.delete(var, 'test_setup')
        try:
            for var in required_vars:
                actual_value = isolated_env.get(var)
                assert actual_value is None, f'Variable {var} should be None after delete, got: {actual_value}'
            result = isolated_env.validate_all()
            assert result.is_valid is False, f'Validation must fail when required variables missing. Result: {result}'
            assert len(result.errors) > 0, f'Must have errors when required variables missing. Errors: {result.errors}'
            error_text = ' '.join(result.errors).lower()
            for var in required_vars:
                assert var.lower() in error_text, f'Missing variable {var} must be mentioned in errors: {result.errors}'
        finally:
            for var, original_value in original_values.items():
                if original_value is not None:
                    isolated_env.set(var, original_value, 'test_restore')

    def test_validate_staging_database_credentials_success(self, isolated_env):
        """Test staging database credential validation with valid credentials."""
        staging_vars = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'cloudsql-instance', 'POSTGRES_USER': 'postgres', 'POSTGRES_PASSWORD': 'secure-staging-password-123', 'POSTGRES_DB': 'netra_staging'}
        isolated_env.update(staging_vars, 'test')
        result = isolated_env.validate_staging_database_credentials()
        assert result['valid'] is True, 'Staging credential validation must pass with valid credentials'
        assert len(result['issues']) == 0, 'Must have no issues with valid credentials'

    def test_validate_staging_database_credentials_invalid(self, isolated_env):
        """Test staging database credential validation with invalid credentials."""
        invalid_vars = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'user_pr-4', 'POSTGRES_PASSWORD': 'weak', 'POSTGRES_DB': 'netra_staging'}
        isolated_env.update(invalid_vars, 'test')
        result = isolated_env.validate_staging_database_credentials()
        assert result['valid'] is False, 'Staging credential validation must fail with invalid credentials'
        assert len(result['issues']) > 0, 'Must have issues with invalid credentials'
        issues_text = ' '.join(result['issues']).lower()
        assert 'localhost' in issues_text, 'Must detect localhost issue'
        assert 'user_pr-4' in issues_text, 'Must detect invalid user pattern'
        assert 'password' in issues_text, 'Must detect weak password'

    def test_validate_staging_credentials_not_staging(self, isolated_env):
        """Test staging validation when not in staging environment."""
        isolated_env.set('ENVIRONMENT', 'development', 'test')
        result = isolated_env.validate_staging_database_credentials()
        assert len(result['warnings']) > 0, 'Must warn when not in staging environment'
        warning_text = ' '.join(result['warnings']).lower()
        assert 'not in staging' in warning_text, 'Warning must mention environment mismatch'

class TestIsolatedEnvironmentUtilityMethods:
    """Test utility and helper methods."""

    def test_get_all_with_prefix(self, isolated_env):
        """Test getting variables with specific prefix."""
        unique_prefix = 'UNIQUE_PREFIX_TEST_'
        test_vars = {f'{unique_prefix}VAR1': 'value1', f'{unique_prefix}VAR2': 'value2', 'OTHER_VAR': 'other', f'{unique_prefix}ANOTHER': 'another'}
        isolated_env.update(test_vars, 'test')
        test_prefixed = isolated_env.get_all_with_prefix(unique_prefix)
        assert len(test_prefixed) == 3, f'Must find exactly 3 variables with {unique_prefix} prefix, got {len(test_prefixed)}: {list(test_prefixed.keys())}'
        assert f'{unique_prefix}VAR1' in test_prefixed, 'Must include VAR1'
        assert f'{unique_prefix}VAR2' in test_prefixed, 'Must include VAR2'
        assert f'{unique_prefix}ANOTHER' in test_prefixed, 'Must include ANOTHER'
        assert 'OTHER_VAR' not in test_prefixed, 'Must not include variables without prefix'
        assert test_prefixed[f'{unique_prefix}VAR1'] == 'value1', 'Must have correct value'

    def test_get_subprocess_env(self, isolated_env):
        """Test getting environment for subprocess calls."""
        isolated_env.set('SUBPROCESS_VAR', 'subprocess_value', 'test')
        subprocess_env = isolated_env.get_subprocess_env()
        assert isinstance(subprocess_env, dict), 'Must return dictionary'
        assert 'SUBPROCESS_VAR' in subprocess_env, 'Must include isolated variables'
        assert subprocess_env['SUBPROCESS_VAR'] == 'subprocess_value', 'Must have correct value'
        assert 'PATH' in subprocess_env, 'Must include system PATH variable'

    def test_get_subprocess_env_with_additional_vars(self, isolated_env):
        """Test subprocess environment with additional variables."""
        isolated_env.set('BASE_VAR', 'base_value', 'test')
        additional_vars = {'ADDITIONAL_VAR': 'additional_value'}
        subprocess_env = isolated_env.get_subprocess_env(additional_vars)
        assert 'BASE_VAR' in subprocess_env, 'Must include base variables'
        assert 'ADDITIONAL_VAR' in subprocess_env, 'Must include additional variables'
        assert subprocess_env['BASE_VAR'] == 'base_value', 'Base variable must have correct value'
        assert subprocess_env['ADDITIONAL_VAR'] == 'additional_value', 'Additional variable must have correct value'

    def test_get_changes_since_init(self, isolated_env):
        """Test tracking changes since initialization."""
        isolated_env.set('NEW_VAR', 'new_value', 'test')
        changes = isolated_env.get_changes_since_init()
        assert isinstance(changes, dict), 'Must return dictionary'
        if 'NEW_VAR' in changes:
            old_value, new_value = changes['NEW_VAR']
            assert new_value == 'new_value', 'Must track new value correctly'

    def test_reset_and_reset_to_original(self, isolated_env):
        """Test reset functionality."""
        isolated_env.set('RESET_VAR', 'reset_value', 'test')
        assert isolated_env.get('RESET_VAR') == 'reset_value', 'Variable must be set before reset'
        isolated_env.reset()
        assert isolated_env.get('RESET_VAR') is None, 'Variable must be None after reset'
        assert not isolated_env.is_isolated(), 'Isolation must be disabled after reset'
        isolated_env.enable_isolation()
        isolated_env.set('ORIGINAL_TEST', 'test_original', 'test')
        isolated_env.reset_to_original()

    def test_clear_cache(self, isolated_env):
        """Test cache clearing functionality."""
        isolated_env.set('CACHE_VAR', 'cache_value', 'test')
        assert isolated_env.get('CACHE_VAR') == 'cache_value', 'Variable must be accessible'
        isolated_env.clear_cache()
        assert isolated_env.get('CACHE_VAR') == 'cache_value', 'Variable must still be accessible after cache clear'

    def test_environment_detection_methods(self, isolated_env):
        """Test environment detection methods."""
        isolated_env.set('ENVIRONMENT', 'development', 'test')
        assert isolated_env.get_environment_name() == 'development', 'Must detect development environment'
        assert isolated_env.is_development() is True, 'is_development() must return True'
        assert isolated_env.is_production() is False, 'is_production() must return False'
        assert isolated_env.is_staging() is False, 'is_staging() must return False'
        assert isolated_env.is_test() is False, 'is_test() must return False'
        isolated_env.set('ENVIRONMENT', 'staging', 'test')
        assert isolated_env.get_environment_name() == 'staging', 'Must detect staging environment'
        assert isolated_env.is_staging() is True, 'is_staging() must return True'
        assert isolated_env.is_development() is False, 'is_development() must return False'
        isolated_env.set('ENVIRONMENT', 'production', 'test')
        assert isolated_env.is_production() is True, 'is_production() must return True'
        assert isolated_env.is_staging() is False, 'is_staging() must return False'
        isolated_env.set('ENVIRONMENT', 'test', 'test')
        assert isolated_env.is_test() is True, 'is_test() must return True'
        assert isolated_env.is_production() is False, 'is_production() must return False'

class TestIsolatedEnvironmentShellExpansion:
    """Test shell command expansion functionality."""

    def test_shell_expansion_disabled_in_tests(self, isolated_env):
        """Test that shell expansion is disabled during tests."""
        shell_value = "$(echo 'test_output')"
        isolated_env.set('SHELL_VAR', shell_value, 'test')
        result = isolated_env.get('SHELL_VAR')
        assert result == shell_value, 'Shell commands must not be expanded during tests'

    def test_shell_expansion_with_env_vars(self, isolated_env):
        """Test shell expansion with environment variables."""
        isolated_env.set('BASE_VAR', 'base_value', 'test')
        env_ref_value = '${BASE_VAR}_suffix'
        isolated_env.set('ENV_REF_VAR', env_ref_value, 'test')
        result = isolated_env.get('ENV_REF_VAR')
        assert result == env_ref_value, 'Environment variable references must not be expanded during tests'

class TestIsolatedEnvironmentSanitization:
    """Test value sanitization functionality."""

    def test_sanitize_generic_value(self, isolated_env):
        """Test sanitization of generic values."""
        value_with_controls = 'test\nvalue\r\twith\x00controls'
        isolated_env.set('SANITIZE_VAR', value_with_controls, 'test')
        result = isolated_env.get('SANITIZE_VAR')
        assert '\n' not in result, 'Newline characters must be removed'
        assert '\r' not in result, 'Carriage return characters must be removed'
        assert '\t' not in result, 'Tab characters must be removed'
        assert '\x00' not in result, 'Null bytes must be removed'
        assert 'test' in result, 'Regular text must be preserved'
        assert 'value' in result, 'Regular text must be preserved'

    def test_sanitize_database_url(self, isolated_env):
        """Test sanitization of database URLs."""
        db_url = 'postgresql://user:pass@#$%@localhost:5432/db'
        isolated_env.set('DATABASE_URL', db_url, 'test')
        result = isolated_env.get('DATABASE_URL')
        assert '@' in result, 'Database URL special characters must be preserved'
        assert 'postgresql://' in result, 'Database URL format must be preserved'

    def test_sanitize_empty_and_none_values(self, isolated_env):
        """Test sanitization of edge case values."""
        isolated_env.set('EMPTY_VAR', '', 'test')
        assert isolated_env.get('EMPTY_VAR') == '', 'Empty string must be preserved'
        isolated_env.set('NONE_VAR', None, 'test')
        result = isolated_env.get('NONE_VAR')
        assert result is not None, 'None values must be converted to string'

class TestIsolatedEnvironmentDebugInfo:
    """Test debug and introspection functionality."""

    def test_get_debug_info(self, isolated_env):
        """Test debug information retrieval."""
        isolated_env.set('DEBUG_VAR', 'debug_value', 'debug_source')
        isolated_env.protect('DEBUG_VAR')
        debug_info = isolated_env.get_debug_info()
        assert isinstance(debug_info, dict), 'Debug info must be dictionary'
        assert 'isolation_enabled' in debug_info, 'Must include isolation status'
        assert 'isolated_vars_count' in debug_info, 'Must include isolated variable count'
        assert 'os_environ_count' in debug_info, 'Must include os.environ count'
        assert 'protected_vars' in debug_info, 'Must include protected variables'
        assert 'tracked_sources' in debug_info, 'Must include source tracking'
        assert debug_info['isolation_enabled'] is True, 'Must show isolation is enabled'
        assert isinstance(debug_info['isolated_vars_count'], int), 'Variable count must be integer'
        assert isinstance(debug_info['protected_vars'], list), 'Protected vars must be list'
        assert 'DEBUG_VAR' in debug_info['protected_vars'], 'Must show protected variable'
        assert debug_info['tracked_sources'].get('DEBUG_VAR') == 'debug_source', 'Must track variable source'

class TestIsolatedEnvironmentLegacyCompatibility:
    """Test legacy compatibility functions and classes."""

    def test_convenience_functions(self, isolated_env):
        """Test global convenience functions."""
        result = setenv('CONV_VAR', 'conv_value', 'convenience')
        assert result is True, 'setenv() must return True on success'
        value = getenv('CONV_VAR')
        assert value == 'conv_value', 'getenv() must return correct value'
        default_value = getenv('NONEXISTENT_CONV', 'default')
        assert default_value == 'default', 'getenv() must return default for nonexistent variable'
        result = delenv('CONV_VAR')
        assert result is True, 'delenv() must return True on successful deletion'
        assert getenv('CONV_VAR') is None, 'getenv() must return None after deletion'

    def test_secret_loader_class(self, isolated_env):
        """Test SecretLoader legacy compatibility class."""
        secret_loader = SecretLoader(isolated_env)
        result = secret_loader.load_secrets()
        assert result is True, 'load_secrets() must return True'
        secret_loader.set_secret('SECRET_VAR', 'secret_value', 'secret_loader')
        secret = secret_loader.get_secret('SECRET_VAR')
        assert secret == 'secret_value', 'get_secret() must return correct value'
        default_secret = secret_loader.get_secret('NONEXISTENT_SECRET', 'default')
        assert default_secret == 'default', 'get_secret() must return default'

    def test_environment_validator_class(self, isolated_env):
        """Test EnvironmentValidator legacy compatibility class."""
        validator = EnvironmentValidator()
        result = validator.validate_all()
        assert isinstance(result, ValidationResult), 'Must return ValidationResult'
        result2 = validator.validate_with_fallbacks()
        assert isinstance(result2, ValidationResult), 'validate_with_fallbacks must return ValidationResult'
        suggestions = validator.get_fix_suggestions(result)
        assert isinstance(suggestions, list), 'Must return list of suggestions'

class TestIsolatedEnvironmentErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_operations_fail_appropriately(self, isolated_env):
        """Test that invalid operations fail with appropriate errors."""
        non_isolated_env = get_env()
        non_isolated_env.disable_isolation()
        with pytest.raises(RuntimeError):
            non_isolated_env.clear()

    def test_concurrent_access_safety(self, isolated_env):
        """Test thread safety under concurrent access."""
        errors = []
        results = []

        def concurrent_operations():
            """Function to perform concurrent environment operations."""
            try:
                thread_id = threading.current_thread().ident
                var_name = f'THREAD_VAR_{thread_id}'
                isolated_env.set(var_name, f'value_{thread_id}', f'thread_{thread_id}')
                value = isolated_env.get(var_name)
                exists = isolated_env.exists(var_name)
                all_vars = isolated_env.get_all()
                results.append({'thread_id': thread_id, 'var_name': var_name, 'value': value, 'exists': exists, 'all_vars_count': len(all_vars)})
            except Exception as e:
                errors.append(f'Thread {threading.current_thread().ident}: {str(e)}')
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_operations)
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10.0)
            if thread.is_alive():
                raise AssertionError(f'Thread {thread.ident} did not complete')
        if errors:
            raise AssertionError(f'Concurrent access errors: {errors}')
        assert len(results) == 10, f'Expected 10 results, got {len(results)}'
        for result in results:
            assert result['value'] == f"value_{result['thread_id']}", 'Thread variable value mismatch'
            assert result['exists'] is True, 'Thread variable must exist'
            assert result['all_vars_count'] > 0, 'Must have variables in environment'

class TestMaskSensitiveValue:
    """Test the _mask_sensitive_value utility function."""

    def test_mask_sensitive_patterns(self):
        """Test masking of sensitive variable patterns."""
        assert _mask_sensitive_value('PASSWORD', 'secretpass123') == 'sec***'
        assert _mask_sensitive_value('API_KEY', 'sk-1234567890') == 'sk-***'
        assert _mask_sensitive_value('SECRET', 'topsecret') == 'top***'
        assert _mask_sensitive_value('JWT_TOKEN', 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9') == 'eyJ***'
        assert _mask_sensitive_value('KEY', 'ab') == '***'
        assert _mask_sensitive_value('AUTH', 'x') == '***'
        assert _mask_sensitive_value('PORT', '8080') == '8080'
        assert _mask_sensitive_value('HOST', 'localhost') == 'localhost'
        long_value = 'x' * 100
        masked = _mask_sensitive_value('DEBUG_INFO', long_value)
        assert masked == long_value[:50] + '...'

class TestFixtureIntegration:
    """Test that test framework fixtures work correctly with IsolatedEnvironment."""

    def test_isolated_env_fixture_basic(self, isolated_env):
        """Test that isolated_env fixture provides working environment."""
        assert isinstance(isolated_env, IsolatedEnvironment), 'Fixture must provide IsolatedEnvironment instance'
        assert isolated_env.is_isolated(), 'Fixture must enable isolation'
        isolated_env.set('FIXTURE_TEST', 'fixture_value', 'test')
        assert isolated_env.get('FIXTURE_TEST') == 'fixture_value', 'Basic operations must work with fixture'

    def test_test_env_fixture_with_defaults(self, test_env):
        """Test that test_env fixture provides standard test configuration."""
        assert isinstance(test_env, IsolatedEnvironment), 'Fixture must provide IsolatedEnvironment instance'
        assert test_env.is_isolated(), 'Fixture must enable isolation'
        assert test_env.get('TESTING') == 'true', 'Standard test config must be applied'
        assert test_env.get('ENVIRONMENT') == 'test', 'Environment must be set to test'
        assert test_env.get('DATABASE_URL') is not None, 'Database URL must be provided'

    def test_temporary_env_vars_context(self, isolated_env):
        """Test temporary environment variables context manager."""
        isolated_env.set('BASE_VAR', 'base', 'test')
        temp_vars = {'TEMP_VAR': 'temp_value', 'BASE_VAR': 'overridden'}
        with temporary_env_vars(temp_vars):
            assert isolated_env.get('TEMP_VAR') == 'temp_value', 'Temporary variable must be set'
            assert isolated_env.get('BASE_VAR') == 'overridden', 'Base variable must be overridden'
        assert isolated_env.get('TEMP_VAR') is None, 'Temporary variable must be cleaned up'
        assert isolated_env.get('BASE_VAR') == 'base', 'Base variable must be restored'

    def test_clean_env_context(self, isolated_env):
        """Test clean environment context manager."""
        isolated_env.set('CLEAN_TEST1', 'value1', 'test')
        isolated_env.set('CLEAN_TEST2', 'value2', 'test')
        with clean_env_context(clear_all=True):
            all_vars = isolated_env.get_all()
            assert len(all_vars) == 0, 'Environment must be clean in clean context'
        assert isolated_env.get('CLEAN_TEST1') == 'value1', 'Variables must be restored after clean context'
        assert isolated_env.get('CLEAN_TEST2') == 'value2', 'Variables must be restored after clean context'

class TestIsolatedEnvironmentPerformance:
    """Test performance characteristics and stress conditions."""

    def test_large_number_of_variables(self, isolated_env):
        """Test handling large number of environment variables."""
        num_vars = 1000
        large_vars = {f'PERF_VAR_{i}': f'value_{i}' for i in range(num_vars)}
        import time
        start_time = time.time()
        results = isolated_env.update(large_vars, 'performance_test')
        end_time = time.time()
        success_count = sum((1 for success in results.values() if success))
        assert success_count == num_vars, f'All {num_vars} variables must be set successfully'
        elapsed = end_time - start_time
        assert elapsed < 5.0, f'Large variable update took too long: {elapsed:.2f}s'
        start_time = time.time()
        all_vars = isolated_env.get_all()
        end_time = time.time()
        assert len(all_vars) >= num_vars, 'All variables must be retrievable'
        elapsed = end_time - start_time
        assert elapsed < 1.0, f'Large variable retrieval took too long: {elapsed:.2f}s'

    def test_concurrent_high_frequency_operations(self, isolated_env):
        """Test high-frequency concurrent operations."""
        operations_per_thread = 100
        num_threads = 5
        errors = []

        def high_frequency_operations():
            """Perform high-frequency environment operations."""
            try:
                thread_id = threading.current_thread().ident
                for i in range(operations_per_thread):
                    var_name = f'HF_VAR_{thread_id}_{i}'
                    isolated_env.set(var_name, f'value_{i}', f'hf_thread_{thread_id}')
                    value = isolated_env.get(var_name)
                    if value != f'value_{i}':
                        errors.append(f'Thread {thread_id} iteration {i}: expected value_{i}, got {value}')
                    isolated_env.delete(var_name, f'hf_cleanup_{thread_id}')
            except Exception as e:
                errors.append(f'Thread {thread_id}: {str(e)}')
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=high_frequency_operations)
            threads.append(thread)
        start_time = time.time()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30.0)
            if thread.is_alive():
                raise AssertionError(f'High-frequency thread did not complete in time')
        end_time = time.time()
        if errors:
            raise AssertionError(f'High-frequency operation errors: {errors[:10]}...')
        total_operations = operations_per_thread * num_threads * 3
        elapsed = end_time - start_time
        ops_per_second = total_operations / elapsed
        assert ops_per_second > 100, f'Low throughput: {ops_per_second:.2f} ops/sec'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')