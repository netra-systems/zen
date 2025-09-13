"""
Integration Tests for Configuration System Consistency - Issue #667

EXPECTED TO FAIL - Demonstrates System-Wide SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Protect $500K+ ARR Golden Path
- Value Impact: Proves configuration inconsistencies break authentication and core services
- Strategic Impact: Validates need for unified configuration across entire system

PURPOSE: These tests are EXPECTED TO FAIL until Issue #667 is resolved.
They demonstrate how configuration manager SSOT violations cause system-wide
failures that break the Golden Path user authentication and chat functionality.

Test Strategy:
1. Test authentication configuration consistency across all managers
2. Validate database configuration consistency for data persistence
3. Test environment-specific configuration consistency
4. Demonstrate service startup configuration conflicts
"""

import pytest
import asyncio
import os
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import patch, MagicMock

# Import test framework
from test_framework.ssot.base_test_case import BaseIntegrationTest


class TestConfigSystemConsistencyIntegration(BaseIntegrationTest):
    """Integration tests for system-wide configuration consistency violations."""

    def setUp(self):
        """Set up integration test environment."""
        super().setUp()

        # Initialize configuration managers for testing
        self.config_managers = {}
        self._initialize_config_managers()

        # Set up test environment variables
        self.test_env_vars = {
            'JWT_SECRET_KEY': 'test-secret-key-12345',
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db',
            'REDIS_URL': 'redis://localhost:6379/1',
            'ENVIRONMENT': 'testing'
        }

    def _initialize_config_managers(self):
        """Initialize all available configuration managers."""
        manager_configs = [
            {
                'name': 'UnifiedConfigManager',
                'module': 'netra_backend.app.core.configuration.base',
                'class_name': 'UnifiedConfigManager'
            },
            {
                'name': 'UnifiedConfigurationManager',
                'module': 'netra_backend.app.core.managers.unified_configuration_manager',
                'class_name': 'UnifiedConfigurationManager'
            },
            {
                'name': 'ConfigurationManager',
                'module': 'netra_backend.app.services.configuration_service',
                'class_name': 'ConfigurationManager'
            }
        ]

        for config in manager_configs:
            try:
                module = __import__(config['module'], fromlist=[config['class_name']])
                manager_class = getattr(module, config['class_name'])

                # Initialize manager with appropriate method
                if config['name'] == 'UnifiedConfigurationManager':
                    try:
                        # Try factory pattern first
                        self.config_managers[config['name']] = manager_class.create_for_user("integration_test_user")
                    except (AttributeError, TypeError):
                        # Fallback to direct instantiation
                        self.config_managers[config['name']] = manager_class()
                else:
                    self.config_managers[config['name']] = manager_class()

            except (ImportError, AttributeError, TypeError) as e:
                self.logger.warning(f"Failed to initialize {config['name']}: {e}")

    def test_auth_configuration_consistency_across_managers_violation(self):
        """
        EXPECTED TO FAIL - Auth configuration differs between managers.

        Authentication configuration must be identical across all managers
        to ensure consistent login behavior. Differences break Golden Path.
        """
        if len(self.config_managers) < 2:
            pytest.skip("Need at least 2 configuration managers for consistency testing")

        # Set up test environment with authentication configuration
        with patch.dict(os.environ, self.test_env_vars):
            auth_configs = {}

            for manager_name, manager_instance in self.config_managers.items():
                auth_config = {}

                try:
                    # Extract authentication-related configuration
                    if hasattr(manager_instance, 'get_config'):
                        if manager_name == 'UnifiedConfigManager':
                            # Get configuration object and extract auth settings
                            config_obj = manager_instance.get_config()
                            auth_config = {
                                'jwt_secret_key': getattr(config_obj, 'jwt_secret_key', None),
                                'oauth_client_id': getattr(config_obj, 'oauth_client_id', None),
                                'auth_token_expiry': getattr(config_obj, 'auth_token_expiry', None),
                                'session_timeout': getattr(config_obj, 'session_timeout', None)
                            }
                        elif manager_name == 'ConfigurationManager':
                            # Get individual configuration values
                            auth_config = {
                                'jwt_secret_key': manager_instance.get_config('JWT_SECRET_KEY'),
                                'oauth_client_id': manager_instance.get_config('OAUTH_CLIENT_ID'),
                                'auth_token_expiry': manager_instance.get_config('AUTH_TOKEN_EXPIRY'),
                                'session_timeout': manager_instance.get_config('SESSION_TIMEOUT')
                            }
                        else:
                            # UnifiedConfigurationManager - try various methods
                            try:
                                env_config = manager_instance.get_environment_config()
                                auth_config = {
                                    'jwt_secret_key': env_config.get('JWT_SECRET_KEY'),
                                    'oauth_client_id': env_config.get('OAUTH_CLIENT_ID'),
                                    'auth_token_expiry': env_config.get('AUTH_TOKEN_EXPIRY'),
                                    'session_timeout': env_config.get('SESSION_TIMEOUT')
                                }
                            except Exception:
                                # Fallback to direct config access
                                auth_config = {
                                    'jwt_secret_key': manager_instance.get_config('JWT_SECRET_KEY'),
                                    'oauth_client_id': manager_instance.get_config('OAUTH_CLIENT_ID'),
                                    'auth_token_expiry': manager_instance.get_config('AUTH_TOKEN_EXPIRY'),
                                    'session_timeout': manager_instance.get_config('SESSION_TIMEOUT')
                                }

                    auth_configs[manager_name] = auth_config

                except Exception as e:
                    auth_configs[manager_name] = {'error': str(e)}

            # Check for authentication configuration inconsistencies
            auth_consistency_violations = []

            # Compare JWT secret key across managers
            jwt_secrets = {name: config.get('jwt_secret_key')
                          for name, config in auth_configs.items()
                          if 'error' not in config}

            unique_jwt_secrets = set(str(secret) for secret in jwt_secrets.values() if secret is not None)
            if len(unique_jwt_secrets) > 1:
                auth_consistency_violations.append(
                    f"JWT secret key inconsistency: {jwt_secrets}"
                )

            # Compare OAuth client ID across managers
            oauth_clients = {name: config.get('oauth_client_id')
                           for name, config in auth_configs.items()
                           if 'error' not in config}

            unique_oauth_clients = set(str(client) for client in oauth_clients.values() if client is not None)
            if len(unique_oauth_clients) > 1:
                auth_consistency_violations.append(
                    f"OAuth client ID inconsistency: {oauth_clients}"
                )

            # CRITICAL ASSERTION: Should fail if auth configuration is inconsistent
            assert len(auth_consistency_violations) == 0, (
                f"AUTHENTICATION CONFIGURATION VIOLATIONS DETECTED: {auth_consistency_violations}. "
                f"Authentication configuration differs between configuration managers, "
                f"causing inconsistent login behavior that breaks the Golden Path user flow. "
                f"Full auth configurations: {auth_configs}. "
                f"This affects $500K+ ARR by preventing users from logging in and accessing AI chat."
            )

    def test_database_configuration_consistency_violation(self):
        """
        EXPECTED TO FAIL - Database connection settings vary between managers.

        Database configuration must be identical across all managers to ensure
        consistent data persistence and prevent connection failures.
        """
        if len(self.config_managers) < 2:
            pytest.skip("Need at least 2 configuration managers for consistency testing")

        with patch.dict(os.environ, self.test_env_vars):
            database_configs = {}

            for manager_name, manager_instance in self.config_managers.items():
                db_config = {}

                try:
                    if hasattr(manager_instance, 'get_config'):
                        if manager_name == 'UnifiedConfigManager':
                            config_obj = manager_instance.get_config()
                            db_config = {
                                'database_url': getattr(config_obj, 'database_url', None),
                                'db_pool_size': getattr(config_obj, 'db_pool_size', None),
                                'db_timeout': getattr(config_obj, 'db_timeout', None)
                            }
                        elif manager_name == 'ConfigurationManager':
                            db_config = {
                                'database_url': manager_instance.get_config('DATABASE_URL'),
                                'db_pool_size': manager_instance.get_config('DB_POOL_SIZE'),
                                'db_timeout': manager_instance.get_config('DB_TIMEOUT')
                            }
                        else:
                            # UnifiedConfigurationManager
                            try:
                                env_config = manager_instance.get_environment_config()
                                db_config = {
                                    'database_url': env_config.get('DATABASE_URL'),
                                    'db_pool_size': env_config.get('DB_POOL_SIZE'),
                                    'db_timeout': env_config.get('DB_TIMEOUT')
                                }
                            except Exception:
                                db_config = {
                                    'database_url': manager_instance.get_config('DATABASE_URL'),
                                    'db_pool_size': manager_instance.get_config('DB_POOL_SIZE'),
                                    'db_timeout': manager_instance.get_config('DB_TIMEOUT')
                                }

                    database_configs[manager_name] = db_config

                except Exception as e:
                    database_configs[manager_name] = {'error': str(e)}

            # Check for database configuration inconsistencies
            db_consistency_violations = []

            # Compare database URLs
            db_urls = {name: config.get('database_url')
                      for name, config in database_configs.items()
                      if 'error' not in config}

            unique_db_urls = set(str(url) for url in db_urls.values() if url is not None)
            if len(unique_db_urls) > 1:
                db_consistency_violations.append(
                    f"Database URL inconsistency: {db_urls}"
                )

            # Compare pool sizes
            pool_sizes = {name: config.get('db_pool_size')
                         for name, config in database_configs.items()
                         if 'error' not in config}

            unique_pool_sizes = set(str(size) for size in pool_sizes.values() if size is not None)
            if len(unique_pool_sizes) > 1:
                db_consistency_violations.append(
                    f"Database pool size inconsistency: {pool_sizes}"
                )

            # CRITICAL ASSERTION: Should fail if database configuration is inconsistent
            assert len(db_consistency_violations) == 0, (
                f"DATABASE CONFIGURATION VIOLATIONS DETECTED: {db_consistency_violations}. "
                f"Database configuration differs between configuration managers, "
                f"causing inconsistent data persistence and potential connection failures. "
                f"Full database configurations: {database_configs}. "
                f"This affects system reliability and data consistency."
            )

    def test_environment_specific_config_consistency_violation(self):
        """
        EXPECTED TO FAIL - Test/staging/prod configs differ between managers.

        Environment-specific configurations must be consistent across managers
        to ensure proper behavior in different deployment environments.
        """
        if len(self.config_managers) < 2:
            pytest.skip("Need at least 2 configuration managers for consistency testing")

        environment_consistency_violations = []

        # Test different environment configurations
        test_environments = ['testing', 'development', 'staging', 'production']

        for environment in test_environments:
            env_vars = {**self.test_env_vars, 'ENVIRONMENT': environment}

            with patch.dict(os.environ, env_vars, clear=True):
                env_configs = {}

                for manager_name, manager_instance in self.config_managers.items():
                    try:
                        if hasattr(manager_instance, 'get_config'):
                            if manager_name == 'UnifiedConfigManager':
                                config_obj = manager_instance.get_config()
                                env_config = {
                                    'environment': getattr(config_obj, 'environment', None),
                                    'debug': getattr(config_obj, 'debug', None),
                                    'log_level': getattr(config_obj, 'log_level', None)
                                }
                            elif manager_name == 'ConfigurationManager':
                                env_config = {
                                    'environment': manager_instance.get_config('ENVIRONMENT'),
                                    'debug': manager_instance.get_config('DEBUG'),
                                    'log_level': manager_instance.get_config('LOG_LEVEL')
                                }
                            else:
                                # UnifiedConfigurationManager
                                try:
                                    full_config = manager_instance.get_environment_config()
                                    env_config = {
                                        'environment': full_config.get('ENVIRONMENT'),
                                        'debug': full_config.get('DEBUG'),
                                        'log_level': full_config.get('LOG_LEVEL')
                                    }
                                except Exception:
                                    env_config = {
                                        'environment': manager_instance.get_config('ENVIRONMENT'),
                                        'debug': manager_instance.get_config('DEBUG'),
                                        'log_level': manager_instance.get_config('LOG_LEVEL')
                                    }

                            env_configs[manager_name] = env_config

                    except Exception as e:
                        env_configs[manager_name] = {'error': str(e)}

                # Check for environment configuration inconsistencies
                env_values = {name: config.get('environment')
                             for name, config in env_configs.items()
                             if 'error' not in config}

                unique_env_values = set(str(val) for val in env_values.values() if val is not None)
                if len(unique_env_values) > 1:
                    environment_consistency_violations.append(
                        f"Environment {environment}: inconsistent values {env_values}"
                    )

        # CRITICAL ASSERTION: Should fail if environment configurations are inconsistent
        assert len(environment_consistency_violations) == 0, (
            f"ENVIRONMENT CONFIGURATION VIOLATIONS DETECTED: {environment_consistency_violations}. "
            f"Environment-specific configurations differ between managers, "
            f"causing inconsistent behavior across development, staging, and production environments. "
            f"This affects deployment reliability and environment parity."
        )

    def test_service_startup_configuration_conflicts_violation(self):
        """
        EXPECTED TO FAIL - Service startup fails due to config manager conflicts.

        Service startup configurations must be consistent to ensure all
        services can initialize properly with any configuration manager.
        """
        if len(self.config_managers) < 2:
            pytest.skip("Need at least 2 configuration managers for consistency testing")

        startup_conflicts = []

        with patch.dict(os.environ, self.test_env_vars):
            # Simulate service startup with different configuration managers
            for manager_name, manager_instance in self.config_managers.items():
                startup_result = {
                    'manager': manager_name,
                    'success': False,
                    'config_loaded': False,
                    'validation_passed': False,
                    'error': None
                }

                try:
                    # Test configuration loading
                    if hasattr(manager_instance, 'get_config'):
                        if manager_name == 'UnifiedConfigManager':
                            config = manager_instance.get_config()
                            startup_result['config_loaded'] = config is not None
                        else:
                            # Test essential configuration keys
                            essential_keys = ['ENVIRONMENT', 'JWT_SECRET_KEY', 'DATABASE_URL']
                            config_values = {}

                            for key in essential_keys:
                                try:
                                    value = manager_instance.get_config(key)
                                    config_values[key] = value
                                except Exception:
                                    config_values[key] = None

                            startup_result['config_loaded'] = all(
                                value is not None for value in config_values.values()
                            )

                    # Test configuration validation
                    if hasattr(manager_instance, 'validate_config'):
                        startup_result['validation_passed'] = manager_instance.validate_config()
                    else:
                        # Assume validation passes if no validation method
                        startup_result['validation_passed'] = True

                    startup_result['success'] = (
                        startup_result['config_loaded'] and
                        startup_result['validation_passed']
                    )

                except Exception as e:
                    startup_result['error'] = str(e)

                # Check for startup conflicts
                if not startup_result['success']:
                    startup_conflicts.append(startup_result)

        # Check for inconsistent startup behavior
        startup_success_rates = {}
        for manager_name in self.config_managers.keys():
            success_rate = 1.0  # Assume success if no conflicts found
            for conflict in startup_conflicts:
                if conflict['manager'] == manager_name:
                    success_rate = 0.0
                    break
            startup_success_rates[manager_name] = success_rate

        # If some managers succeed while others fail, that's a consistency violation
        unique_success_rates = set(startup_success_rates.values())
        if len(unique_success_rates) > 1:
            startup_conflicts.append({
                'type': 'consistency_violation',
                'success_rates': startup_success_rates,
                'message': 'Different managers have different startup success rates'
            })

        # CRITICAL ASSERTION: Should fail if service startup conflicts exist
        assert len(startup_conflicts) == 0, (
            f"SERVICE STARTUP CONFLICTS DETECTED: {startup_conflicts}. "
            f"Service startup configurations conflict between managers, "
            f"causing some services to fail initialization depending on which "
            f"configuration manager is used. This creates unpredictable system behavior "
            f"and affects service reliability during deployment and scaling."
        )