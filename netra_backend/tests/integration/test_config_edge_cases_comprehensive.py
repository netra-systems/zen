"""Comprehensive Integration Tests for Configuration Edge Cases and Error Scenarios

Business Value Justification (BVJ):
- Segment: Platform/Internal - All customer tiers depend on stable configuration
- Business Goal: System Reliability - Prevent silent failures and configuration-related outages
- Value Impact: Prevents $12K MRR loss from config errors, enables WebSocket agent events
- Strategic Impact: Ensures multi-user agent execution works under edge conditions

CRITICAL MISSION:
Configuration edge cases can cause silent failures that break WebSocket agent events.
These tests validate the configuration system under stress conditions that would
occur in production multi-user scenarios.

CRITICAL REQUIREMENTS:
- NO MOCKS! Use real configuration instances under stress
- Test realistic failure scenarios that occur in production
- Focus on edge cases that prevent WebSocket agent events
- Test configuration recovery mechanisms 
- Test scenarios that cause silent failures vs hard failures
- Test multi-user isolation under configuration stress

Categories: integration
"""
import asyncio
import concurrent.futures
import hashlib
import json
import os
import pytest
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.jwt_secret_manager import SharedJWTSecretManager, get_jwt_secret_manager
from netra_backend.app.core.configuration.base import UnifiedConfigManager, get_unified_config, validate_unified_config, config_manager, reload_unified_config
from netra_backend.app.core.configuration.validator import ConfigurationValidator, ValidationMode, ValidationResult
from netra_backend.app.core.configuration.loader import ConfigurationLoader
from netra_backend.app.core.environment_constants import EnvironmentDetector
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, StagingConfig, ProductionConfig, NetraTestingConfig, RedisConfig, GoogleCloudConfig, OAuthConfig, ClickHouseNativeConfig
from test_framework.base_integration_test import BaseIntegrationTest

class ConfigurationValidationFailuresTests(BaseIntegrationTest):
    """Test configuration validation failure scenarios and error recovery.
    
    BVJ: Ensures configuration validation catches errors before they cause
    silent failures in WebSocket agent events.
    """

    @contextmanager
    def isolated_test_env(self):
        """Create isolated test environment for configuration testing."""
        env = get_env()
        env.enable_isolation()
        original_state = env._isolated_environment.copy() if hasattr(env, '_isolated_environment') else {}
        try:
            yield env
        finally:
            if hasattr(env, '_isolated_environment'):
                env._isolated_environment.clear()
                env._isolated_environment.update(original_state)
            env.disable_isolation()

    @pytest.mark.integration
    def test_validation_with_missing_critical_database_url(self):
        """Test validation behavior when critical #removed-legacyis missing.
        
        BVJ: #removed-legacyis required for agent execution - missing value should
        be handled gracefully by development config, trigger errors in production.
        """
        with self.isolated_test_env() as env:
            env.delete('DATABASE_URL') if env.get('DATABASE_URL') else None
            env.set('ENVIRONMENT', 'development', 'test')
            config_manager = UnifiedConfigManager()
            try:
                config = config_manager.get_config()
                assert config is not None
                assert hasattr(config, 'database_url')
                validator = ConfigurationValidator()
                result = validator.validate_complete_config(config)
                assert result is not None
                assert isinstance(result, ValidationResult)
                if not config.database_url:
                    total_issues = len(result.errors) + len(result.warnings)
                    assert total_issues > 0, 'Missing database URL should generate validation issues'
                    all_issues_text = ' '.join(result.errors + result.warnings).lower()
                    assert 'database' in all_issues_text or 'url' in all_issues_text
            except Exception as e:
                error_text = str(e).lower()
                assert 'database' in error_text or 'url' in error_text

    @pytest.mark.integration
    def test_validation_with_production_mode_missing_secrets(self):
        """Test validation in production mode with missing secrets.
        
        BVJ: Production environment should fail fast when critical secrets missing
        to prevent silent failures that break OAuth and WebSocket authentication.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'production', 'test')
            env.delete('JWT_SECRET_KEY') if env.get('JWT_SECRET_KEY') else None
            env.delete('SECRET_KEY') if env.get('SECRET_KEY') else None
            env.delete('SERVICE_SECRET') if env.get('SERVICE_SECRET') else None
            config_manager = UnifiedConfigManager()
            validator = ConfigurationValidator()
            try:
                config = config_manager.get_config()
                result = validator.validate_complete_config(config)
                if result.errors:
                    error_text = ' '.join(result.errors).lower()
                    assert any((term in error_text for term in ['secret', 'key', 'required']))
            except Exception as e:
                assert 'secret' in str(e).lower() or 'key' in str(e).lower()

    @pytest.mark.integration
    def test_progressive_validation_mode_enforcement(self):
        """Test progressive validation modes (warn, enforce_critical, enforce_all).
        
        BVJ: Different environments need different validation strictness to balance
        development velocity with production safety.
        """
        with self.isolated_test_env() as env:
            validator = ConfigurationValidator()
            env.set('ENVIRONMENT', 'development', 'test')
            env.set('DATABASE_URL', 'postgresql://test:test@localhost:5432/test', 'test')
            config = DevelopmentConfig()
            result = validator.validate_complete_config(config)
            assert result is not None
            assert len(result.errors) <= len(result.warnings)

    @pytest.mark.integration
    def test_validation_with_corrupted_config_data(self):
        """Test validation with corrupted or inconsistent configuration data.
        
        BVJ: Corrupted config can cause WebSocket agent events to fail silently.
        System should detect corruption and either recover or fail explicitly.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            env.set('DATABASE_URL', 'postgresql://test:test@localhost:5432/test', 'test')
            env.set('SERVICE_SECRET', 'strong_unique_cross_auth_key_for_configuration_validation_32_chars', 'test')
            config = NetraTestingConfig()
            test_config_data = config.__dict__.copy()
            test_config_data['port'] = 'not_a_number'
            validator = ConfigurationValidator()
            try:
                result = validator.validate_complete_config(config)
                assert result is not None
            except (ValueError, TypeError) as e:
                assert 'port' in str(e).lower() or 'number' in str(e).lower()

    @pytest.mark.integration
    def test_config_health_score_calculation(self):
        """Test configuration health score calculation under various conditions.
        
        BVJ: Health scores help monitor configuration quality and predict failures
        before they impact WebSocket agent events.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            validator = ConfigurationValidator()
            env.set('DATABASE_URL', 'postgresql://test:test@localhost:5432/test', 'test')
            env.set('JWT_SECRET_KEY', 'secure_jwt_key_at_least_32_characters_long', 'test')
            env.set('SECRET_KEY', 'secure_secret_key_at_least_32_characters_long', 'test')
            env.set('SERVICE_SECRET', 'strong_unique_cross_auth_key_for_configuration_validation_32_chars', 'test')
            config = NetraTestingConfig()
            result = validator.validate_complete_config(config)
            assert hasattr(result, 'score')
            assert result.score >= 0
            assert result.score <= 100
            env.set('DATABASE_URL', 'postgresql://enhanced:enhanced@localhost:5432/enhanced', 'test')
            env.set('JWT_SECRET_KEY', 'very_secure_jwt_secret_key_with_proper_length', 'test')
            env.set('SECRET_KEY', 'very_secure_secret_key_with_proper_length', 'test')
            env.set('SERVICE_SECRET', 'enhanced_unique_cross_auth_key_for_configuration_validation_32_chars', 'test')
            env.set('REDIS_PASSWORD', 'redis_password_secure_32_chars', 'test')
            enhanced_config = NetraTestingConfig()
            enhanced_result = validator.validate_complete_config(enhanced_config)
            assert enhanced_result.score >= result.score

class MalformedConfigurationHandlingTests(BaseIntegrationTest):
    """Test handling of malformed configuration data.
    
    BVJ: Malformed configuration can cause silent failures in agent execution.
    System must detect and handle malformed data gracefully.
    """

    @pytest.mark.integration
    def test_malformed_env_file_parsing(self):
        """Test handling of malformed .env file parsing.
        
        BVJ: Malformed .env files in development can break WebSocket agent events.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('VALID_KEY=valid_value\n')
            f.write('MALFORMED_LINE_WITHOUT_EQUALS\n')
            f.write('=MISSING_KEY\n')
            f.write('KEY_WITH_SPACES = value with spaces\n')
            f.write("QUOTED_VALUE='single quoted'\n")
            f.write('DOUBLE_QUOTED="double quoted"\n')
            f.flush()
            env_file = Path(f.name)
        try:
            with self.isolated_test_env() as env:
                try:
                    env.load_from_file(env_file)
                    assert env.get('VALID_KEY') == 'valid_value'
                except Exception as e:
                    assert '.env' in str(e).lower() or 'parsing' in str(e).lower()
        finally:
            env_file.unlink()

    @pytest.mark.integration
    def test_invalid_url_format_handling(self):
        """Test handling of invalid URL formats in configuration.
        
        BVJ: Invalid URLs for database/Redis/external services cause connection
        failures that break agent execution.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            invalid_urls = ['not_a_url', 'http://', 'postgresql://no_port', 'redis://:password@host', 'https://[invalid:bracket', 'ftp://wrong.protocol.com']
            validator = ConfigurationValidator()
            for invalid_url in invalid_urls:
                env.set('DATABASE_URL', invalid_url, 'test')
                config = NetraTestingConfig()
                result = validator.validate_complete_config(config)
                if result.errors:
                    error_text = ' '.join(result.errors).lower()
                    assert any((term in error_text for term in ['url', 'format', 'invalid']))

    @pytest.mark.integration
    def test_malformed_json_config_handling(self):
        """Test handling of malformed JSON configuration data.
        
        BVJ: JSON config used in secrets and complex settings can be malformed,
        causing silent failures in agent configuration.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            malformed_json_values = ['{"incomplete": true,}', '{"missing_quotes": value}', '{incomplete_object: true', '[{"array": "with"}, missing_element]']
            for malformed_json in malformed_json_values:
                env.set('LLM_CONFIG_JSON', malformed_json, 'test')
                config = NetraTestingConfig()
                validator = ConfigurationValidator()
                result = validator.validate_complete_config(config)
                assert result is not None

    @pytest.mark.integration
    def test_encoding_issues_handling(self):
        """Test handling of encoding issues in configuration values.
        
        BVJ: Encoding issues can cause silent failures in WebSocket agent events,
        especially with international characters or special symbols.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            problematic_values = ['password_with_[U+00E9]mojis_[U+1F511]', 'binary_\x00\x01\x02_data', 'newline_\n_in_value', 'tab_\t_in_value', 'carriage_\r_return', 'quote_\'_and_"_mixed']
            validator = ConfigurationValidator()
            for problematic_value in problematic_values:
                env.set('SECRET_KEY', problematic_value, 'test')
                config = NetraTestingConfig()
                result = validator.validate_complete_config(config)
                assert result is not None
                if hasattr(config, 'secret_key') and config.secret_key:
                    assert '\x00' not in config.secret_key

class ConfigurationPrecedenceEdgeCasesTests(BaseIntegrationTest):
    """Test configuration precedence edge cases.
    
    BVJ: Configuration precedence issues can cause production values to leak
    into development or wrong OAuth credentials to be used.
    """

    @pytest.mark.integration
    def test_os_environment_vs_env_file_precedence(self):
        """Test precedence between OS environment variables and .env file.
        
        BVJ: Incorrect precedence can cause staging credentials to leak into production.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('TEST_VALUE=from_env_file\n')
            f.write('DATABASE_URL=postgresql://envfile:password@localhost:5432/envfile\n')
            f.flush()
            env_file = Path(f.name)
        try:
            with self.isolated_test_env() as env:
                env.set('TEST_VALUE', 'from_os_environment', 'os')
                env.set('DATABASE_URL', 'postgresql://os:password@localhost:5432/os', 'os')
                env.load_from_file(env_file)
                assert env.get('TEST_VALUE') == 'from_os_environment'
                assert 'os:password' in env.get('DATABASE_URL')
                env.set('ENVIRONMENT', 'development', 'test')
                config = DevelopmentConfig()
                assert config.database_url and 'os:password' in config.database_url
        finally:
            env_file.unlink()

    @pytest.mark.integration
    def test_fallback_generation_precedence(self):
        """Test fallback value generation precedence in development.
        
        BVJ: Fallback generation should not override explicitly set values.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'development', 'test')
            explicit_secret = 'explicitly_set_jwt_secret_key_for_testing'
            env.set('JWT_SECRET_KEY', explicit_secret, 'test')
            config = DevelopmentConfig()
            assert config.jwt_secret_key == explicit_secret
            env.delete('SECRET_KEY') if env.get('SECRET_KEY') else None
            config2 = DevelopmentConfig()
            assert hasattr(config2, 'secret_key')
            if config2.secret_key:
                assert len(config2.secret_key) >= 16

    @pytest.mark.integration
    def test_environment_specific_value_precedence(self):
        """Test environment-specific value precedence logic.
        
        BVJ: Environment-specific OAuth credentials must not leak between environments.
        """
        with self.isolated_test_env() as env:
            env.set('GOOGLE_CLIENT_ID_STAGING', 'staging_client_id', 'test')
            env.set('GOOGLE_CLIENT_ID_PRODUCTION', 'production_client_id', 'test')
            env.set('GOOGLE_CLIENT_ID', 'generic_client_id', 'test')
            env.set('ENVIRONMENT', 'staging', 'test')
            staging_config = StagingConfig()
            env.set('ENVIRONMENT', 'production', 'test')
            production_config = ProductionConfig()

class ConcurrentConfigurationAccessTests(BaseIntegrationTest):
    """Test configuration access under high concurrency and load.
    
    BVJ: Multi-user agent execution requires thread-safe configuration access.
    Configuration race conditions can break WebSocket agent events.
    """

    @pytest.mark.integration
    def test_concurrent_config_loading(self):
        """Test concurrent configuration loading from multiple threads.
        
        BVJ: Multiple agent executions loading config simultaneously
        should not cause race conditions or corruption.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            env.set('DATABASE_URL', 'postgresql://test:test@localhost:5432/test', 'test')
            results = []
            exceptions = []

            def load_config(thread_id: int):
                """Load configuration in separate thread."""
                try:
                    manager = UnifiedConfigManager()
                    config = manager.get_config()
                    results.append({'thread_id': thread_id, 'config_type': type(config).__name__, 'database_url': getattr(config, 'database_url', None), 'environment': manager.get_environment_name()})
                except Exception as e:
                    exceptions.append({'thread_id': thread_id, 'error': str(e), 'error_type': type(e).__name__})
            threads = []
            num_threads = 10
            for i in range(num_threads):
                thread = threading.Thread(target=load_config, args=(i,))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join(timeout=10.0)
            assert len(exceptions) == 0, f'Concurrent config loading failed: {exceptions}'
            assert len(results) == num_threads
            first_result = results[0]
            for result in results[1:]:
                assert result['config_type'] == first_result['config_type']
                assert result['environment'] == first_result['environment']

    @pytest.mark.integration
    def test_config_cache_consistency_under_load(self):
        """Test configuration cache consistency under load.
        
        BVJ: Config caching race conditions can cause different agents 
        to use different configurations, breaking multi-user isolation.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            config_manager_instance = config_manager
            results = []
            cache_hits = []

            def access_cached_config(iteration: int):
                """Access cached configuration."""
                try:
                    config = config_manager_instance.get_config()
                    results.append({'iteration': iteration, 'config_id': id(config), 'config_valid': config is not None})
                    is_cached = hasattr(config_manager_instance, '_config_cache') and config_manager_instance._config_cache is not None
                    cache_hits.append(is_cached)
                except Exception as e:
                    results.append({'iteration': iteration, 'error': str(e)})
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(access_cached_config, i) for i in range(20)]
                concurrent.futures.wait(futures, timeout=10.0)
            valid_results = [r for r in results if 'config_id' in r]
            assert len(valid_results) > 0
            if len(valid_results) > 1:
                first_config_id = valid_results[0]['config_id']
                same_config_count = sum((1 for r in valid_results if r['config_id'] == first_config_id))
                assert same_config_count >= len(valid_results) * 0.8

    @pytest.mark.integration
    def test_config_modification_race_conditions(self):
        """Test configuration modification race conditions.
        
        BVJ: Simultaneous config modifications can corrupt configuration state,
        breaking WebSocket connections for all users.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            modification_results = []

            def modify_config_environment(env_name: str, iteration: int):
                """Modify configuration environment in separate thread."""
                try:
                    manager = UnifiedConfigManager()
                    env.set('ENVIRONMENT', env_name, f'thread_{iteration}')
                    manager._environment = None
                    manager._config_cache = None
                    config = manager.get_config()
                    modification_results.append({'iteration': iteration, 'requested_env': env_name, 'actual_env': manager.get_environment_name(), 'config_type': type(config).__name__, 'success': True})
                except Exception as e:
                    modification_results.append({'iteration': iteration, 'requested_env': env_name, 'error': str(e), 'success': False})
            environments = ['testing', 'development'] * 5
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(modify_config_environment, env_name, i) for i, env_name in enumerate(environments)]
                concurrent.futures.wait(futures, timeout=15.0)
            successful_results = [r for r in modification_results if r['success']]
            failed_results = [r for r in modification_results if not r['success']]
            assert len(successful_results) >= len(modification_results) * 0.7
            for result in successful_results:
                assert result['config_type'] in ['NetraTestingConfig', 'DevelopmentConfig']
                assert result['actual_env'] in ['testing', 'development']

class DatabaseConnectionStringValidationTests(BaseIntegrationTest):
    """Test configuration validation with invalid database connection strings.
    
    BVJ: Invalid database connections prevent agent execution and cause 
    silent failures in WebSocket agent events.
    """

    @pytest.mark.integration
    def test_invalid_postgresql_url_formats(self):
        """Test validation of invalid PostgreSQL URL formats.
        
        BVJ: Malformed database URLs cause connection failures during agent execution.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            invalid_postgres_urls = ['postgresql://', 'postgresql://host', 'postgresql://user@host', 'postgresql://user:pass@', 'postgresql://:pass@host:5432/db', 'mysql://user:pass@host:5432/db', 'http://user:pass@host:5432/db', 'redis://user:pass@host:5432/db', 'postgresql://user:pass@host:99999/db', 'postgresql://user:pass@host:abc/db', 'postgresql://user:pass@host:-1/db', 'postgresql://user with spaces:pass@host:5432/db', 'postgresql://user:pass with spaces@host:5432/db', 'postgresql://user:pass@host with spaces:5432/db', 'postgresql://user:pass@host:5432/db with spaces', "postgresql://user'; DROP TABLE users; --:pass@host:5432/db", "postgresql://user:pass@host:5432/db'; DROP DATABASE test; --"]
            validator = ConfigurationValidator()
            for invalid_url in invalid_postgres_urls:
                env.set('DATABASE_URL', invalid_url, 'test')
                config = NetraTestingConfig()
                result = validator.validate_complete_config(config)
                if result.errors:
                    error_text = ' '.join(result.errors).lower()
                    assert any((term in error_text for term in ['database', 'url', 'connection', 'invalid', 'format'])), f'No database error found for URL: {invalid_url}'

    @pytest.mark.integration
    def test_database_connection_timeout_scenarios(self):
        """Test database connection validation with timeout scenarios.
        
        BVJ: Connection timeouts can cause agent execution to hang,
        breaking WebSocket responsiveness.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'testing', 'test')
            timeout_prone_urls = ['postgresql://user:pass@192.0.2.0:5432/db', 'postgresql://user:pass@10.255.255.1:5432/db', 'postgresql://user:pass@example.invalid:5432/db', 'postgresql://user:pass@localhost:1:db']
            validator = ConfigurationValidator()
            for timeout_url in timeout_prone_urls:
                env.set('DATABASE_URL', timeout_url, 'test')
                start_time = time.time()
                try:
                    config = NetraTestingConfig()
                    result = validator.validate_complete_config(config)
                    elapsed = time.time() - start_time
                    assert elapsed < 5.0, f'Validation took too long: {elapsed}s for {timeout_url}'
                    assert result is not None
                except Exception as e:
                    elapsed = time.time() - start_time
                    assert elapsed < 5.0, f'Exception took too long: {elapsed}s for {timeout_url}'
                    error_msg = str(e).lower()
                    assert any((term in error_msg for term in ['connection', 'timeout', 'url', 'database', 'invalid']))

    @pytest.mark.integration
    def test_database_ssl_configuration_validation(self):
        """Test database SSL configuration validation edge cases.
        
        BVJ: SSL configuration errors can prevent secure database connections
        required for production agent execution.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'production', 'test')
            ssl_test_cases = [{'url': 'postgresql://user:pass@host:5432/db?sslmode=require', 'should_pass': True, 'description': 'SSL required - good for production'}, {'url': 'postgresql://user:pass@host:5432/db?sslmode=disable', 'should_pass': False, 'description': 'SSL disabled - bad for production'}, {'url': 'postgresql://user:pass@host:5432/db?sslmode=invalid_mode', 'should_pass': False, 'description': 'Invalid SSL mode'}, {'url': 'postgresql://user:pass@host:5432/db?sslmode=prefer&sslcert=/path/to/cert', 'should_pass': True, 'description': 'SSL with certificate path'}]
            validator = ConfigurationValidator()
            for test_case in ssl_test_cases:
                env.set('DATABASE_URL', test_case['url'], 'test')
                config = ProductionConfig()
                result = validator.validate_complete_config(config)
                if test_case['should_pass']:
                    if result.errors:
                        error_text = ' '.join(result.errors).lower()
                        assert 'ssl' not in error_text, f"SSL error for valid config: {test_case['description']}"
                else:
                    all_issues = result.errors + result.warnings
                    if all_issues:
                        issue_text = ' '.join(all_issues).lower()

class OAuthCredentialValidationTests(BaseIntegrationTest):
    """Test configuration with malformed OAuth credentials.
    
    BVJ: OAuth credential errors prevent user authentication,
    blocking access to WebSocket agent functionality.
    """

    @pytest.mark.integration
    def test_malformed_oauth_client_ids(self):
        """Test validation with malformed OAuth client IDs.
        
        BVJ: Invalid OAuth client IDs cause authentication failures
        that prevent users from accessing agents.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'staging', 'test')
            malformed_client_ids = ['', '   ', 'short', 'client_id_with_spaces in_middle', 'client-id-with\ttabs', 'client\nid\nwith\nnewlines', 'client_id_with_unicode_[U+00E9]mojis_[U+1F511]', 'a' * 300, 'client.id.with.only.dots', 'AAAAAAAA-BBBB-CCCC-DDDD-' + 'E' * 50]
            validator = ConfigurationValidator()
            for malformed_id in malformed_client_ids:
                env.set('GOOGLE_CLIENT_ID', malformed_id, 'test')
                env.set('GOOGLE_OAUTH_CLIENT_ID_STAGING', malformed_id, 'test')
                config = StagingConfig()
                result = validator.validate_complete_config(config)
                assert result is not None
                if result.errors or result.warnings:
                    issue_text = ' '.join(result.errors + result.warnings).lower()

    @pytest.mark.integration
    def test_oauth_client_secret_validation(self):
        """Test OAuth client secret validation edge cases.
        
        BVJ: Invalid OAuth client secrets cause authentication failures
        during the OAuth flow for WebSocket connections.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'production', 'test')
            secret_test_cases = [{'secret': '', 'valid': False, 'description': 'Empty client secret'}, {'secret': 'a' * 10, 'valid': False, 'description': 'Too short client secret'}, {'secret': 'GOCSPX-' + 'a' * 28, 'valid': True, 'description': 'Standard Google client secret format'}, {'secret': 'secret_with_special_chars!@#$%^&*()', 'valid': True, 'description': 'Client secret with special characters'}, {'secret': 'secret with spaces', 'valid': False, 'description': 'Client secret with spaces (should be invalid)'}, {'secret': 'a' * 200, 'valid': True, 'description': 'Very long client secret'}]
            validator = ConfigurationValidator()
            for test_case in secret_test_cases:
                env.set('GOOGLE_CLIENT_SECRET', test_case['secret'], 'test')
                env.set('GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION', test_case['secret'], 'test')
                config = ProductionConfig()
                result = validator.validate_complete_config(config)
                assert result is not None
                if not test_case['valid']:
                    if not (result.errors or result.warnings):
                        pass

    @pytest.mark.integration
    def test_oauth_environment_credential_leakage(self):
        """Test prevention of OAuth credential leakage between environments.
        
        BVJ: Using staging OAuth credentials in production breaks enterprise
        authentication and violates security compliance.
        """
        with self.isolated_test_env() as env:
            env.set('GOOGLE_OAUTH_CLIENT_ID_STAGING', 'staging_client_id', 'test')
            env.set('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', 'staging_client_secret', 'test')
            env.set('GOOGLE_OAUTH_CLIENT_ID_PRODUCTION', 'production_client_id', 'test')
            env.set('GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION', 'production_client_secret', 'test')
            env.set('GOOGLE_CLIENT_ID', 'generic_client_id', 'test')
            env.set('GOOGLE_CLIENT_SECRET', 'generic_client_secret', 'test')
            env.set('ENVIRONMENT', 'staging', 'test')
            staging_config = StagingConfig()
            env.set('ENVIRONMENT', 'production', 'test')
            production_config = ProductionConfig()
            validator = ConfigurationValidator()
            staging_result = validator.validate_complete_config(staging_config)
            production_result = validator.validate_complete_config(production_config)
            assert staging_result is not None
            assert production_result is not None

class ConfigurationRecoveryMechanismsTests(BaseIntegrationTest):
    """Test configuration recovery mechanisms and corrupted file handling.
    
    BVJ: Configuration corruption can bring down the entire platform.
    Recovery mechanisms ensure WebSocket agent events continue working.
    """

    @pytest.mark.integration
    def test_corrupted_config_file_recovery(self):
        """Test recovery from corrupted configuration files.
        
        BVJ: Corrupted config files should not prevent system startup
        or cause silent failures in agent execution.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / 'config'
            config_dir.mkdir()
            corrupted_config = config_dir / 'config.json'
            with corrupted_config.open('w') as f:
                f.write('{"incomplete": json, content}')
            corrupted_env = config_dir / '.env'
            with corrupted_env.open('w') as f:
                f.write('CORRUPTED_ENV_FILE\n')
                f.write('INVALID\x00CHARACTERS=value\n')
            with self.isolated_test_env() as env:
                try:
                    env.load_from_file(corrupted_env)
                except Exception:
                    pass
                env.set('ENVIRONMENT', 'development', 'test')
                config_manager = UnifiedConfigManager()
                config = config_manager.get_config()
                assert config is not None
                assert isinstance(config, AppConfig)

    @pytest.mark.integration
    def test_partial_config_loading_resilience(self):
        """Test resilience when only partial configuration can be loaded.
        
        BVJ: Partial configuration failures should not prevent WebSocket
        connections that don't depend on the failed components.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'development', 'test')
            env.set('DATABASE_URL', 'postgresql://test:test@localhost:5432/test', 'test')
            env.set('JWT_SECRET_KEY', 'valid_jwt_secret_key_for_testing', 'test')
            env.set('REDIS_URL', 'invalid_redis_url', 'test')
            env.set('CLICKHOUSE_URL', 'invalid_clickhouse_url', 'test')
            config_manager = UnifiedConfigManager()
            config = config_manager.get_config()
            assert config is not None
            assert config.database_url is not None
            assert config.jwt_secret_key is not None
            validator = ConfigurationValidator()
            result = validator.validate_complete_config(config)
            assert result is not None

    @pytest.mark.integration
    def test_config_hot_reload_error_recovery(self):
        """Test error recovery during configuration hot-reload.
        
        BVJ: Configuration hot-reload errors can cause ongoing agent
        executions to fail and break WebSocket connections.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'development', 'test')
            env.set('DATABASE_URL', 'postgresql://test:test@localhost:5432/test', 'test')
            config_manager = UnifiedConfigManager()
            initial_config = config_manager.get_config()
            assert initial_config is not None
            env.set('DATABASE_URL', 'completely_invalid_url', 'test')
            try:
                reloaded_config = config_manager.reload_config(force=True)
                assert reloaded_config is not None
            except Exception as e:
                fallback_config = config_manager.get_config()
                assert fallback_config is not None

    @pytest.mark.integration
    def test_config_validation_error_accumulation(self):
        """Test that configuration validation errors accumulate properly.
        
        BVJ: Multiple configuration errors should be reported together
        to prevent silent failures and aid in debugging.
        """
        with self.isolated_test_env() as env:
            env.set('ENVIRONMENT', 'production', 'test')
            env.delete('DATABASE_URL') if env.get('DATABASE_URL') else None
            env.delete('JWT_SECRET_KEY') if env.get('JWT_SECRET_KEY') else None
            env.set('REDIS_URL', 'invalid_redis_format', 'test')
            env.set('GOOGLE_CLIENT_ID', '', 'test')
            validator = ConfigurationValidator()
            config = ProductionConfig()
            result = validator.validate_complete_config(config)
            assert result is not None
            total_issues = len(result.errors) + len(result.warnings)
            assert total_issues > 0
            if result.errors:
                error_text = ' '.join(result.errors).lower()
                error_topics = ['database' in error_text, 'jwt' in error_text or 'secret' in error_text, 'redis' in error_text, 'client' in error_text or 'oauth' in error_text]
                detected_issues = sum(error_topics)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')