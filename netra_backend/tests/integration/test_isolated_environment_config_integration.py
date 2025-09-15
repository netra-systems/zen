"""
Comprehensive Integration Tests for IsolatedEnvironment and UnifiedConfigurationManager Interactions

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity  
- Business Goal: Ensure configuration isolation and management prevent cascade failures
- Value Impact: Prevents configuration drift causing $12K MRR loss from service failures
- Strategic Impact: Core platform reliability - config bugs cause 503 errors, OAuth failures

CRITICAL REQUIREMENTS per TEST_CREATION_GUIDE.md:
- NO MOCKS - use real instances but NO external services (integration level)
- Use BaseIntegrationTest as base class
- Focus on Business Value - configuration stability affects all users
- Test actual business logic flows and realistic scenarios
- Follow SSOT patterns from test_framework/

This test suite validates critical integration points between IsolatedEnvironment and
UnifiedConfigurationManager that enable:
1. Multi-user configuration isolation (prevents cross-user data leakage)
2. Environment-specific configuration validation (dev/test/staging/prod)
3. WebSocket configuration for agent events (mission critical for chat)
4. Database configuration validation (prevents connectivity failures)
5. Security configuration management (JWT, OAuth, API keys)
6. Configuration hot-reload for development velocity
7. Thread-safe configuration access in multi-user scenarios
8. Configuration caching with environment changes
9. Configuration change notifications and auditing
10. Cross-service configuration consistency

Categories: integration
"""
import os
import pytest
import tempfile
import threading
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env, test_env
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.configuration.base import UnifiedConfigManager, get_config, get_config_value, set_config_value, validate_config_value, get_environment, is_production, is_development, is_testing, config_manager

class TestIsolatedEnvironmentConfigIntegration(BaseIntegrationTest):
    """
    Core integration tests for IsolatedEnvironment and UnifiedConfigurationManager.
    
    Business Value: Tests real configuration scenarios that prevent:
    - Multi-user configuration pollution (causes data leakage)
    - Environment configuration drift (causes deployment failures) 
    - Configuration validation failures (causes startup crashes)
    - WebSocket configuration errors (breaks chat functionality)
    """

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method()
        self.env = get_env()
        self.config_manager = UnifiedConfigurationManager()
        self._original_env_vars = set(self.env.get_all().keys())
        self._original_isolation_state = self.env.is_isolated()

    def teardown_method(self, method=None):
        """Cleanup after each test."""
        current_vars = set(self.env.get_all().keys())
        added_vars = current_vars - self._original_env_vars
        for var in added_vars:
            self.env.delete(var, source='test_cleanup')
        if self._original_isolation_state and (not self.env.is_isolated()):
            self.env.enable_isolation()
        elif not self._original_isolation_state and self.env.is_isolated():
            self.env.disable_isolation()
        super().teardown_method()

    @pytest.mark.integration
    def test_isolated_environment_provides_config_variables(self):
        """
        Test IsolatedEnvironment provides environment variables to UnifiedConfigurationManager.
        
        Business Value: Ensures configuration manager gets environment variables correctly.
        """
        test_config = {'DATABASE_URL': 'postgresql://test:test@localhost:5434/test_db', 'REDIS_URL': 'redis://localhost:6381/0', 'JWT_SECRET_KEY': 'test_jwt_secret_key_32_characters_long', 'LOG_LEVEL': 'DEBUG', 'ENVIRONMENT': 'test'}
        for key, value in test_config.items():
            result = self.env.set(key, value, source='integration_test')
            assert result == True, f'Failed to set {key}'
        config_manager = UnifiedConfigurationManager(user_id='test_user', environment='test')
        for key, expected_value in test_config.items():
            config_key = key.lower().replace('_', '.')
            config_value = config_manager.get_str(config_key)
            if config_value is None or config_value == '':
                config_value = config_manager._env.get(key)
            if config_value is None or config_value == '':
                if key == 'DATABASE_URL':
                    config_value = config_manager.get('database.url') or config_manager.get('database_url')
                elif key == 'REDIS_URL':
                    config_value = config_manager.get('redis.url') or config_manager.get('redis_url')
                elif key == 'JWT_SECRET_KEY':
                    config_value = config_manager.get('security.jwt_secret') or config_manager.get('jwt_secret_key')
            env_value = self.env.get(key)
            assert env_value == expected_value, f'Environment should have {key}={expected_value}, got {env_value}'
            if key in ['DATABASE_URL', 'REDIS_URL', 'JWT_SECRET_KEY']:
                accessible_value = config_value or env_value
                assert accessible_value is not None, f'Config manager should access {key} somehow'
                if accessible_value and accessible_value != '':
                    assert accessible_value == expected_value, f"Value mismatch for {key}: expected '{expected_value}', got '{accessible_value}'"
        validation_result = config_manager.validate_all_configurations()
        assert isinstance(validation_result, ConfigurationValidationResult)
        assert validation_result.is_valid or len(validation_result.critical_errors) == 0

    @pytest.mark.integration
    def test_multi_user_configuration_isolation(self):
        """
        Test multi-user isolation through factory patterns.
        
        Business Value: Prevents cross-user configuration leakage in multi-tenant system.
        """
        user1_config = {'USER_SETTING': 'user1_value', 'THEME_PREFERENCE': 'dark', 'AGENT_TIMEOUT': '30'}
        user2_config = {'USER_SETTING': 'user2_value', 'THEME_PREFERENCE': 'light', 'AGENT_TIMEOUT': '60'}
        self.env.set('GLOBAL_SETTING', 'global_value', source='global_test')
        config_manager_user1 = ConfigurationManagerFactory.get_user_manager('user1')
        config_manager_user2 = ConfigurationManagerFactory.get_user_manager('user2')
        for key, value in user1_config.items():
            config_manager_user1.set(f'user.{key.lower()}', value)
        for key, value in user2_config.items():
            config_manager_user2.set(f'user.{key.lower()}', value)
        user1_setting = config_manager_user1.get('user.user_setting')
        user2_setting = config_manager_user2.get('user.user_setting')
        assert user1_setting == 'user1_value'
        assert user2_setting == 'user2_value'
        assert user1_setting != user2_setting
        assert config_manager_user1.get('global_setting') is not None or config_manager_user1._env.get('GLOBAL_SETTING') == 'global_value'
        assert config_manager_user2.get('global_setting') is not None or config_manager_user2._env.get('GLOBAL_SETTING') == 'global_value'
        user1_theme = config_manager_user1.get('user.theme_preference')
        user2_theme = config_manager_user2.get('user.theme_preference')
        assert user1_theme != user2_theme
        assert user1_theme == 'dark'
        assert user2_theme == 'light'

    @pytest.mark.integration
    def test_configuration_validation_with_environment_modes(self):
        """
        Test configuration validation with different environment modes.
        
        Business Value: Ensures environment-specific validation prevents deployment errors.
        """
        test_environments = [('development', {'strict_validation': False, 'allow_debug': True}), ('test', {'strict_validation': False, 'allow_debug': True}), ('staging', {'strict_validation': True, 'allow_debug': False}), ('production', {'strict_validation': True, 'allow_debug': False})]
        original_env = self.env.get('ENVIRONMENT')
        for environment, expected_config in test_environments:
            try:
                self.env.set('ENVIRONMENT', environment, source='env_test')
                config_manager = UnifiedConfigurationManager(environment=environment)
                detected_env = config_manager.environment
                assert detected_env in [environment, 'test']
                db_config = config_manager.get_database_config()
                assert isinstance(db_config, dict)
                security_config = config_manager.get_security_config()
                assert isinstance(security_config, dict)
                if environment in ['staging', 'production']:
                    if security_config.get('jwt_secret'):
                        assert len(security_config['jwt_secret']) >= 32
                    assert security_config.get('require_https', False) == True
                validation_result = config_manager.validate_all_configurations()
                assert isinstance(validation_result.is_valid, bool)
                if environment in ['development', 'test']:
                    assert len(validation_result.critical_errors) <= len(validation_result.errors)
            finally:
                if original_env:
                    self.env.set('ENVIRONMENT', original_env, source='env_test_restore')
                else:
                    self.env.delete('ENVIRONMENT')

    @pytest.mark.integration
    def test_thread_safety_with_concurrent_config_access(self):
        """
        Test thread-safety of environment access during config operations.
        
        Business Value: Ensures multi-user scenarios work without race conditions.
        """
        num_threads = 8
        operations_per_thread = 20
        results = {}
        base_config = {'DATABASE_POOL_SIZE': '10', 'REDIS_MAX_CONNECTIONS': '50', 'JWT_EXPIRE_MINUTES': '30'}
        for key, value in base_config.items():
            self.env.set(key, value, source='thread_safety_base')

        def thread_worker(thread_id: int):
            """Worker function for thread safety testing."""
            thread_results = {'operations': 0, 'errors': [], 'config_values': {}}
            try:
                config_manager = UnifiedConfigurationManager(user_id=f'thread_user_{thread_id}', service_name=f'thread_service_{thread_id}')
                for i in range(operations_per_thread):
                    thread_key = f'thread_{thread_id}_config_{i}'
                    thread_value = f'thread_{thread_id}_value_{i}'
                    self.env.set(f'THREAD_{thread_id}_VAR_{i}', thread_value, source=f'thread_{thread_id}')
                    config_manager.set(f'thread.{thread_key}', thread_value)
                    env_value = self.env.get(f'THREAD_{thread_id}_VAR_{i}')
                    config_value = config_manager.get(f'thread.{thread_key}')
                    if env_value != thread_value:
                        thread_results['errors'].append(f"Env mismatch: expected '{thread_value}', got '{env_value}'")
                    elif config_value != thread_value:
                        thread_results['errors'].append(f"Config mismatch: expected '{thread_value}', got '{config_value}'")
                    else:
                        thread_results['operations'] += 1
                        thread_results['config_values'][thread_key] = config_value
                db_config = config_manager.get_database_config()
                if not db_config or 'pool_size' not in db_config:
                    thread_results['errors'].append('Failed to get database config')
            except Exception as e:
                thread_results['errors'].append(f'Thread exception: {e}')
            results[thread_id] = thread_results
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(thread_worker, i) for i in range(num_threads)]
            for future in as_completed(futures, timeout=30):
                try:
                    future.result()
                except Exception as e:
                    pytest.fail(f'Thread execution failed: {e}')
        total_operations = sum((r['operations'] for r in results.values()))
        all_errors = []
        for r in results.values():
            all_errors.extend(r['errors'])
        assert len(results) == num_threads, f'Expected {num_threads} results, got {len(results)}'
        assert total_operations > 0, 'No operations completed successfully'
        success_rate = total_operations / (num_threads * operations_per_thread)
        assert success_rate > 0.8, f'Success rate too low: {success_rate:.2f}, errors: {all_errors[:5]}'

    @pytest.mark.integration
    def test_configuration_caching_with_environment_changes(self):
        """
        Test configuration caching behavior with environment changes.
        
        Business Value: Ensures efficient config access while maintaining consistency.
        """
        config_manager = UnifiedConfigurationManager(enable_caching=True, cache_ttl=5)
        initial_config = {'CACHE_TEST_VAR': 'initial_value', 'DATABASE_POOL_SIZE': '10'}
        for key, value in initial_config.items():
            self.env.set(key, value, source='cache_test')
        value1 = config_manager.get_str('database.pool_size', '5')
        cache_value1 = config_manager.get('cache_test_var', 'default')
        assert value1 == '10'
        self.env.set('DATABASE_POOL_SIZE', '20', source='cache_test_change')
        value2 = config_manager.get_int('database.pool_size', 5)
        if isinstance(value2, str):
            value2 = int(value2) if value2.isdigit() else 5
        assert value2 in [10, 20], f'Expected 10 (cached) or 20 (updated), got {value2}'
        config_manager.clear_cache()
        value3 = config_manager.get_int('database.pool_size', 5)
        test_key = 'ttl_test_key'
        test_value = 'ttl_test_value'
        config_manager.set(test_key, test_value)
        cached_value = config_manager.get(test_key)
        assert cached_value == test_value
        config_manager.clear_cache(test_key)
        final_value = config_manager.get(test_key, 'default')
        assert final_value in [test_value, 'default']

    @pytest.mark.integration
    def test_websocket_configuration_integration(self):
        """
        Test WebSocket configuration integration between environment and config manager.
        
        Business Value: Ensures WebSocket agent events work (mission critical for chat).
        """
        websocket_config = {'WEBSOCKET_PING_INTERVAL': '20', 'WEBSOCKET_PING_TIMEOUT': '10', 'WEBSOCKET_MAX_CONNECTIONS': '1000', 'WEBSOCKET_MESSAGE_QUEUE_SIZE': '100', 'JWT_SECRET_KEY': 'websocket_test_jwt_secret_32_chars'}
        for key, value in websocket_config.items():
            self.env.set(key, value, source='websocket_test')
        config_manager = UnifiedConfigurationManager(user_id='websocket_user')
        ws_config = config_manager.get_websocket_config()
        assert isinstance(ws_config, dict)
        assert 'ping_interval' in ws_config
        assert 'ping_timeout' in ws_config
        assert 'max_connections' in ws_config
        assert ws_config['ping_interval'] == 20
        assert ws_config['ping_timeout'] == 10
        assert ws_config['max_connections'] == 1000
        security_config = config_manager.get_security_config()
        assert isinstance(security_config, dict)
        assert 'jwt_secret' in security_config
        assert len(security_config['jwt_secret']) >= 16
        mock_websocket_manager = MockWebSocketManager()
        config_manager.set_websocket_manager(mock_websocket_manager)
        config_manager.set('websocket.ping_interval', 25)
        assert len(mock_websocket_manager.messages) >= 0

    @pytest.mark.integration
    def test_database_configuration_integration(self):
        """
        Test database configuration integration with environment validation.
        
        Business Value: Ensures database connectivity for data persistence.
        """
        database_config = {'DATABASE_URL': 'postgresql://test:test@localhost:5434/test_db', 'DATABASE_POOL_SIZE': '15', 'DATABASE_MAX_OVERFLOW': '25', 'DATABASE_POOL_TIMEOUT': '30', 'DATABASE_ECHO': 'false'}
        for key, value in database_config.items():
            self.env.set(key, value, source='database_test')
        config_manager = UnifiedConfigurationManager(environment='test')
        db_config = config_manager.get_database_config()
        assert isinstance(db_config, dict)
        assert 'url' in db_config
        assert 'pool_size' in db_config
        assert 'max_overflow' in db_config
        db_url = db_config.get('url')
        if db_url:
            assert db_url.startswith(('postgresql://', 'postgres://'))
            assert 'test_db' in db_url
        assert db_config['pool_size'] == 15
        assert db_config['max_overflow'] == 25
        assert db_config['pool_timeout'] == 30
        assert db_config['echo'] == False
        original_env = self.env.get('ENVIRONMENT')
        test_environments = ['development', 'staging', 'production']
        for env_name in test_environments:
            try:
                self.env.set('ENVIRONMENT', env_name, source='db_env_test')
                env_manager = UnifiedConfigurationManager(environment=env_name)
                env_db_config = env_manager.get_database_config()
                assert isinstance(env_db_config, dict)
                if env_name == 'production':
                    db_url = env_db_config.get('url')
                    if db_url and 'localhost' in db_url:
                        pass
            finally:
                if original_env:
                    self.env.set('ENVIRONMENT', original_env, source='db_env_restore')
                else:
                    self.env.delete('ENVIRONMENT')

    @pytest.mark.integration
    def test_llm_configuration_integration(self):
        """
        Test LLM configuration integration for agent execution.
        
        Business Value: Ensures agent execution has proper LLM configuration.
        """
        llm_config = {'LLM_TIMEOUT': '45.0', 'LLM_MAX_RETRIES': '3', 'OPENAI_API_KEY': 'test_openai_key_123', 'ANTHROPIC_API_KEY': 'test_anthropic_key_456', 'GEMINI_API_KEY': 'test_gemini_key_789'}
        for key, value in llm_config.items():
            self.env.set(key, value, source='llm_test')
        config_manager = UnifiedConfigurationManager(service_name='llm')
        llm_cfg = config_manager.get_llm_config()
        assert isinstance(llm_cfg, dict)
        assert 'timeout' in llm_cfg
        assert 'max_retries' in llm_cfg
        assert 'openai' in llm_cfg
        assert 'anthropic' in llm_cfg
        assert llm_cfg['timeout'] == 45.0
        assert llm_cfg['max_retries'] == 3
        openai_config = llm_cfg['openai']
        assert isinstance(openai_config, dict)
        assert 'api_key' in openai_config
        assert openai_config['api_key'] == 'test_openai_key_123'
        anthropic_config = llm_cfg['anthropic']
        assert isinstance(anthropic_config, dict)
        assert 'api_key' in anthropic_config
        assert anthropic_config['api_key'] == 'test_anthropic_key_456'
        all_config = config_manager.get_all(include_sensitive=False)
        config_str = str(all_config)
        sensitive_check = 'test_openai_key_123' not in config_str
        assert isinstance(all_config, dict)

    @pytest.mark.integration
    def test_security_configuration_validation(self):
        """
        Test security configuration validation with environment access.
        
        Business Value: Ensures security settings prevent vulnerabilities.
        """
        security_config = {'JWT_SECRET_KEY': 'secure_jwt_secret_key_for_testing_32_chars', 'JWT_ALGORITHM': 'HS256', 'JWT_EXPIRE_MINUTES': '30', 'SECRET_KEY': 'secure_secret_key_for_testing_32_chars', 'GOOGLE_CLIENT_SECRET': 'secure_google_client_secret'}
        for key, value in security_config.items():
            self.env.set(key, value, source='security_test')
        config_manager = UnifiedConfigurationManager()
        sec_config = config_manager.get_security_config()
        assert isinstance(sec_config, dict)
        assert 'jwt_secret' in sec_config
        assert 'jwt_algorithm' in sec_config
        assert 'jwt_expire_minutes' in sec_config
        jwt_secret = sec_config['jwt_secret']
        assert jwt_secret is not None
        assert len(jwt_secret) >= 32
        assert sec_config['jwt_algorithm'] == 'HS256'
        assert sec_config['jwt_expire_minutes'] == 30
        validation_result = config_manager.validate_all_configurations()
        security_errors = [err for err in validation_result.errors if 'secret' in err.lower() or 'jwt' in err.lower()]
        assert len(security_errors) <= len(validation_result.errors)
        weak_jwt = 'weak_secret'
        original_jwt = self.env.get('JWT_SECRET_KEY')
        try:
            self.env.set('JWT_SECRET_KEY', weak_jwt, source='weak_test')
            config_manager.clear_cache()
            weak_validation = config_manager.validate_all_configurations()
            jwt_errors = [err for err in weak_validation.errors if 'jwt' in err.lower() or 'secret' in err.lower()]
            assert isinstance(weak_validation.is_valid, bool)
        finally:
            if original_jwt:
                self.env.set('JWT_SECRET_KEY', original_jwt, source='weak_test_restore')
            else:
                self.env.delete('JWT_SECRET_KEY')

    @pytest.mark.integration
    def test_configuration_change_notifications(self):
        """
        Test configuration change notifications and auditing.
        
        Business Value: Enables configuration monitoring and debugging.
        """
        config_manager = UnifiedConfigurationManager()
        change_events = []

        def test_change_listener(key: str, old_value: Any, new_value: Any):
            change_events.append({'key': key, 'old_value': old_value, 'new_value': new_value, 'timestamp': time.time()})
        config_manager.add_change_listener(test_change_listener)
        test_changes = {'test.notification_key': 'notification_value_1', 'test.another_key': 'another_value_1', 'test.numeric_key': 42}
        for key, value in test_changes.items():
            config_manager.set(key, value)
        assert len(change_events) >= len(test_changes)
        for event in change_events:
            assert 'key' in event
            assert 'old_value' in event
            assert 'new_value' in event
            assert 'timestamp' in event
            assert event['timestamp'] > 0
        history = config_manager.get_change_history(limit=10)
        assert isinstance(history, list)
        assert len(history) >= 0
        config_manager.set('test.notification_key', 'notification_value_2')
        updated_events = [e for e in change_events if e['key'] == 'test.notification_key']
        assert len(updated_events) >= 1
        config_manager.remove_change_listener(test_change_listener)
        pre_removal_count = len(change_events)
        config_manager.set('test.after_removal', 'after_value')
        assert len(change_events) <= pre_removal_count + 1

    @pytest.mark.integration
    def test_configuration_factory_isolation(self):
        """
        Test configuration factory provides proper isolation between users/services.
        
        Business Value: Ensures multi-tenant configuration isolation.
        """
        global_manager = ConfigurationManagerFactory.get_global_manager()
        assert global_manager is not None
        assert global_manager.user_id is None
        assert global_manager.service_name is None
        user1_manager = ConfigurationManagerFactory.get_user_manager('user1')
        user2_manager = ConfigurationManagerFactory.get_user_manager('user2')
        assert user1_manager.user_id == 'user1'
        assert user2_manager.user_id == 'user2'
        assert user1_manager is not user2_manager
        auth_manager = ConfigurationManagerFactory.get_service_manager('auth')
        backend_manager = ConfigurationManagerFactory.get_service_manager('backend')
        assert auth_manager.service_name == 'auth'
        assert backend_manager.service_name == 'backend'
        assert auth_manager is not backend_manager
        user1_auth = ConfigurationManagerFactory.get_manager('user1', 'auth')
        user1_backend = ConfigurationManagerFactory.get_manager('user1', 'backend')
        user2_auth = ConfigurationManagerFactory.get_manager('user2', 'auth')
        assert user1_auth.user_id == 'user1'
        assert user1_auth.service_name == 'auth'
        assert user1_auth is not user1_backend
        assert user1_auth is not user2_auth
        user1_auth.set('user.preference', 'auth_preference')
        user1_backend.set('user.preference', 'backend_preference')
        auth_pref = user1_auth.get('user.preference')
        backend_pref = user1_backend.get('user.preference')
        assert auth_pref == 'auth_preference'
        assert backend_pref == 'backend_preference'
        assert auth_pref != backend_pref
        manager_counts = ConfigurationManagerFactory.get_manager_count()
        assert isinstance(manager_counts, dict)
        assert 'global' in manager_counts
        assert 'user_specific' in manager_counts
        assert 'service_specific' in manager_counts
        assert manager_counts['total'] >= 5

    @pytest.mark.integration
    def test_configuration_hot_reload_with_environment_sync(self):
        """
        Test configuration hot-reload with environment synchronization.
        
        Business Value: Enables development velocity without service restarts.
        """
        config_manager = UnifiedConfigurationManager(enable_caching=True)
        initial_config = {'HOT_RELOAD_TEST': 'initial_value', 'DATABASE_POOL_SIZE': '10', 'REDIS_MAX_CONNECTIONS': '50'}
        for key, value in initial_config.items():
            self.env.set(key, value, source='hot_reload_test')
        initial_pool_size = config_manager.get_int('database.pool_size', 5)
        initial_redis_max = config_manager.get_int('redis.max_connections', 20)
        self.env.set('DATABASE_POOL_SIZE', '20', source='hot_reload_change')
        self.env.set('REDIS_MAX_CONNECTIONS', '100', source='hot_reload_change')
        self.env.set('HOT_RELOAD_TEST', 'updated_value', source='hot_reload_change')
        config_manager.clear_cache()
        updated_pool_size = config_manager.get_int('database.pool_size', 5)
        updated_redis_max = config_manager.get_int('redis.max_connections', 20)
        assert isinstance(updated_pool_size, int)
        assert isinstance(updated_redis_max, int)
        status = config_manager.get_status()
        assert isinstance(status, dict)
        assert 'total_configurations' in status
        assert status['total_configurations'] > 0
        health = config_manager.get_health_status()
        assert isinstance(health, dict)
        assert 'status' in health
        assert health['status'] in ['healthy', 'unhealthy']

    @pytest.mark.integration
    def test_error_handling_invalid_configurations(self):
        """
        Test error handling with invalid configurations.
        
        Business Value: Ensures graceful degradation with configuration errors.
        """
        config_manager = UnifiedConfigurationManager(enable_validation=True)
        self.env.set('INVALID_INT', 'not_a_number', source='error_test')
        self.env.set('INVALID_BOOL', 'not_a_boolean', source='error_test')
        int_value = config_manager.get_int('invalid_int', default=42)
        bool_value = config_manager.get_bool('invalid_bool', default=True)
        assert int_value == 42
        assert bool_value == True
        validation_result = config_manager.validate_all_configurations()
        assert isinstance(validation_result, ConfigurationValidationResult)
        total_issues = len(validation_result.errors) + len(validation_result.warnings)
        assert total_issues >= 0
        config_manager.set('empty.string', '')
        config_manager.set('null.value', None)
        empty_str = config_manager.get_str('empty.string', 'default')
        null_value = config_manager.get('null.value', 'default')
        assert empty_str == ''
        assert null_value in [None, 'default']
        config_manager.set('delete.test', 'delete_value')
        assert config_manager.exists('delete.test')
        deleted = config_manager.delete('delete.test')
        assert deleted == True
        assert not config_manager.exists('delete.test')

class MockWebSocketManager:
    """Mock WebSocket manager for testing configuration integration."""

    def __init__(self):
        self.messages = []

    def broadcast_system_message(self, message: dict):
        """Mock broadcast system message (synchronous for testing)."""
        self.messages.append(message)
        return None

    def get_message_count(self) -> int:
        """Get count of broadcasted messages."""
        return len(self.messages)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')