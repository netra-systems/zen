"""
Integration test for environment loading regression prevention.

This test verifies that the dev launcher properly prevents environment variable
conflicts using the EnvironmentManager.
"""
import os
import pytest
from shared.isolated_environment import IsolatedEnvironment
from dev_launcher.config import LauncherConfig
from shared.isolated_environment import get_env, get_environment_manager
from dev_launcher.launcher import DevLauncher
env = get_env()

def reset_global_manager():
    """Reset the global environment manager for testing."""
    from shared.isolated_environment import _global_env
    _global_env.reset_to_original()
    _global_env._protected_vars.clear()
    _global_env._variable_sources.clear()

class EnvironmentLoadingRegressionTests:
    """Test that environment loading prevents conflicts and race conditions."""

    def setup_method(self):
        """Setup for each test."""
        reset_global_manager()
        self.original_env = env.get_all()

    def teardown_method(self):
        """Cleanup after each test."""
        env.clear()
        env.update(self.original_env, 'test')
        reset_global_manager()

    def test_no_auth_service_port_duplicate_setting(self):
        """Test that AUTH_SERVICE_PORT is not set multiple times by different components."""
        env.set('ENVIRONMENT', 'development', 'test')
        manager = get_environment_manager()
        result1 = manager.set('AUTH_SERVICE_PORT', '8081', source='auth_starter')
        assert result1 is True
        result2 = manager.set('AUTH_SERVICE_PORT', '8081', source='service_startup')
        assert result2 is True
        manager.protect_variable('AUTH_SERVICE_PORT')
        result3 = manager.set('AUTH_SERVICE_PORT', '8082', source='service_startup')
        assert result3 is False
        assert manager.get('AUTH_SERVICE_PORT') == '8081'
        assert manager.get_variable_source('AUTH_SERVICE_PORT') == 'auth_starter'

    def test_temporary_secrets_loading_flag_cleanup(self):
        """Test that NETRA_SECRETS_LOADING flag is properly cleaned up."""
        env.set('ENVIRONMENT', 'development', 'test')
        manager = get_environment_manager()
        manager.set('NETRA_SECRETS_LOADING', 'true', source='launcher_early_load')
        assert manager.get('NETRA_SECRETS_LOADING') == 'true'
        manager.set('DATABASE_URL', 'postgresql://test', source='secret_loader')
        manager.set('JWT_SECRET_KEY', 'test_secret_minimum_20_characters_long', source='secret_loader')
        manager.delete('NETRA_SECRETS_LOADING', source='launcher_cleanup')
        assert manager.get('NETRA_SECRETS_LOADING') is None
        assert manager.get('DATABASE_URL') == 'postgresql://test'
        assert manager.get('JWT_SECRET_KEY') == 'test_secret_minimum_20_characters_long'

    def test_isolation_mode_prevents_os_environ_pollution_in_development(self):
        """Test that development mode uses isolation to prevent os.environ pollution."""
        env.set('ENVIRONMENT', 'development', 'test')
        manager = get_environment_manager()
        manager.enable_isolation()
        assert manager.is_isolation_enabled() is True
        test_vars = {'TEST_VAR_1': 'value1', 'TEST_VAR_2': 'value2', 'DEVELOPMENT_FLAG': 'true'}
        for key, value in test_vars.items():
            manager.set(key, value, source='test_component')
        for key, expected_value in test_vars.items():
            assert manager.get(key) == expected_value
            assert key not in os.environ

    def test_production_mode_sets_os_environ(self):
        """Test that production mode sets variables in os.environ."""
        env.set('ENVIRONMENT', 'production', 'test')
        reset_global_manager()
        manager = get_environment_manager()
        manager.disable_isolation()
        assert manager.is_isolation_enabled() is False
        test_vars = {'PROD_VAR_1': 'prod_value1', 'PROD_VAR_2': 'prod_value2'}
        for key, value in test_vars.items():
            manager.set(key, value, source='prod_component')
        for key, expected_value in test_vars.items():
            assert manager.get(key) == expected_value
            assert env.get(key) == expected_value

    def test_secret_loader_isolation_behavior(self):
        """Test that secret loading respects isolation mode."""
        env.set('ENVIRONMENT', 'development', 'test')
        manager = get_environment_manager()
        manager.enable_isolation()
        assert manager.is_isolation_enabled() is True
        secrets = {'DATABASE_URL': 'postgresql://localhost/test', 'JWT_SECRET_KEY': 'test_jwt_secret', 'API_KEY': 'test_api_key'}
        for key, value in secrets.items():
            manager.set(key, value, source='secret_loader')
        for key, expected_value in secrets.items():
            assert manager.get(key) == expected_value
            assert key not in os.environ

    def test_environment_manager_singleton_behavior_in_launcher(self):
        """Test that all components get the same EnvironmentManager instance."""
        env.set('ENVIRONMENT', 'development', 'test')
        secret_loader_manager = get_environment_manager()
        auth_starter_manager = get_environment_manager()
        service_startup_manager = get_environment_manager()
        launcher_manager = get_environment_manager()
        assert secret_loader_manager is auth_starter_manager
        assert auth_starter_manager is service_startup_manager
        assert service_startup_manager is launcher_manager
        secret_loader_manager.enable_isolation()
        assert all((manager.is_isolation_enabled() for manager in [secret_loader_manager, auth_starter_manager, service_startup_manager, launcher_manager]))

    def test_component_environment_variable_precedence(self):
        """Test proper precedence handling between different components."""
        env.set('ENVIRONMENT', 'development', 'test')
        manager = get_environment_manager()
        defaults_result = manager.bulk_set_environment({'BACKEND_PORT': '8000', 'LOG_LEVEL': 'INFO', 'CORS_ORIGINS': '*'}, source='launcher_defaults')
        assert all(defaults_result.values())
        secret_result = manager.set('BACKEND_PORT', '8001', source='secret_loader', force=True)
        assert secret_result is True
        assert manager.get('BACKEND_PORT') == '8001'
        auth_results = manager.bulk_set_environment({'AUTH_SERVICE_PORT': '8081', 'AUTH_SERVICE_URL': 'http://localhost:8081'}, source='auth_starter')
        assert all(auth_results.values())
        manager.protect_variable('BACKEND_PORT')
        conflict_result = manager.set('BACKEND_PORT', '8002', source='random_component')
        assert conflict_result is False
        assert manager.get('BACKEND_PORT') == '8001'

    def test_no_race_conditions_with_temporary_flags(self):
        """Test that temporary flags don't cause race conditions."""
        env.set('ENVIRONMENT', 'development', 'test')
        manager = get_environment_manager()
        manager.set('NETRA_SECRETS_LOADING', 'true', source='launcher')
        assert manager.get('NETRA_SECRETS_LOADING') is not None
        assert manager.get('NETRA_SECRETS_LOADING') == 'true'
        loader_results = manager.bulk_set_environment({'DATABASE_URL': 'postgresql://localhost/netra_dev', 'JWT_SECRET_KEY': 'super_secret_key', 'REDIS_URL': 'redis://localhost:6379'}, source='secret_loader')
        assert all(loader_results.values())
        assert manager.get('NETRA_SECRETS_LOADING') == 'true'
        manager.delete('NETRA_SECRETS_LOADING', source='launcher_cleanup')
        assert manager.get('NETRA_SECRETS_LOADING') is None
        assert manager.get('DATABASE_URL') == 'postgresql://localhost/netra_dev'
        assert manager.get('JWT_SECRET_KEY') == 'super_secret_key'
        assert manager.get('REDIS_URL') == 'redis://localhost:6379'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')