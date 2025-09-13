"""
E2E Tests for Configuration SSOT Staging Validation - Issue #667

EXPECTED TO FAIL - Staging Environment Configuration Protection

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Production Readiness - Ensure staging mirrors production
- Value Impact: Validates configuration consistency in real deployment environment
- Strategic Impact: Protects $500K+ ARR by ensuring staging environment reliability

PURPOSE: These tests are EXPECTED TO FAIL until Issue #667 is resolved.
They validate configuration consistency on the actual GCP staging environment,
ensuring that configuration manager SSOT violations don't break real deployments.

Test Strategy:
1. Test complete user flow on staging with different config managers
2. Validate service dependencies work consistently in cloud environment
3. Test Golden Path functionality in real staging deployment
4. Ensure configuration changes don't break production deployment pipeline
"""

import pytest
import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from unittest.mock import patch

# Import test framework
from test_framework.ssot.base_test_case import BaseE2ETest


class TestConfigSSotStagingValidation(BaseE2ETest):
    """E2E tests for configuration SSOT validation on GCP staging environment."""

    def setUp(self):
        """Set up staging environment validation tests."""
        super().setUp()

        # Skip if not in staging environment
        if not self._is_staging_environment():
            pytest.skip("These tests only run on GCP staging environment")

        # Initialize configuration managers for staging testing
        self.staging_config_managers = {}
        self._initialize_staging_config_managers()

        # Staging environment configuration expectations
        self.staging_config_expectations = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': None,  # Should exist but not check value
            'DATABASE_URL': None,    # Should exist but not check value
            'REDIS_URL': None,       # Should exist but not check value
            'OPENAI_API_KEY': None,  # Should exist but not check value
            'WEBSOCKET_PORT': '8001'
        }

    def _is_staging_environment(self) -> bool:
        """Check if running in staging environment."""
        # Check for staging environment indicators
        environment = os.getenv('ENVIRONMENT', '').lower()
        cloud_run = os.getenv('K_SERVICE', '')  # Cloud Run indicator
        staging_project = os.getenv('GOOGLE_CLOUD_PROJECT', '') == 'netra-staging'

        return environment == 'staging' or bool(cloud_run) or staging_project

    def _initialize_staging_config_managers(self):
        """Initialize configuration managers for staging validation."""
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

                # Initialize for staging environment
                if config['name'] == 'UnifiedConfigurationManager':
                    try:
                        self.staging_config_managers[config['name']] = manager_class.create_for_user("staging_e2e_user")
                    except (AttributeError, TypeError):
                        self.staging_config_managers[config['name']] = manager_class()
                else:
                    self.staging_config_managers[config['name']] = manager_class()

            except (ImportError, AttributeError, TypeError) as e:
                self.logger.error(f"Failed to initialize {config['name']} in staging: {e}")

    @pytest.mark.staging_only
    def test_staging_auth_config_consistency_e2e_violation(self):
        """
        EXPECTED TO FAIL - Staging auth configuration varies between managers.

        This test validates that authentication configuration is consistent
        across all managers in the real staging environment, ensuring that
        production deployment will work reliably.
        """
        if len(self.staging_config_managers) < 2:
            pytest.skip("Need at least 2 configuration managers for staging validation")

        staging_auth_violations = []

        # Test authentication configuration consistency in staging
        staging_auth_configs = {}

        for manager_name, manager_instance in self.staging_config_managers.items():
            staging_auth_config = {
                'config_accessible': False,
                'jwt_secret_exists': False,
                'oauth_config_exists': False,
                'session_config_exists': False,
                'errors': []
            }

            try:
                if hasattr(manager_instance, 'get_config'):
                    staging_auth_config['config_accessible'] = True

                    if manager_name == 'UnifiedConfigManager':
                        # Test staging config object access
                        config_obj = manager_instance.get_config()
                        staging_auth_config['jwt_secret_exists'] = hasattr(config_obj, 'jwt_secret_key') and \
                                                                   getattr(config_obj, 'jwt_secret_key') is not None
                        staging_auth_config['oauth_config_exists'] = hasattr(config_obj, 'oauth_client_id')
                        staging_auth_config['session_config_exists'] = hasattr(config_obj, 'session_timeout')

                    else:
                        # Test staging environment variable access
                        try:
                            if manager_name == 'ConfigurationManager':
                                jwt_secret = manager_instance.get_config('JWT_SECRET_KEY')
                                oauth_client = manager_instance.get_config('OAUTH_CLIENT_ID')
                                session_timeout = manager_instance.get_config('SESSION_TIMEOUT')
                            else:
                                # UnifiedConfigurationManager
                                env_config = manager_instance.get_environment_config()
                                jwt_secret = env_config.get('JWT_SECRET_KEY')
                                oauth_client = env_config.get('OAUTH_CLIENT_ID')
                                session_timeout = env_config.get('SESSION_TIMEOUT')

                            staging_auth_config['jwt_secret_exists'] = jwt_secret is not None
                            staging_auth_config['oauth_config_exists'] = oauth_client is not None
                            staging_auth_config['session_config_exists'] = session_timeout is not None

                        except Exception as e:
                            staging_auth_config['errors'].append(f"Staging config access error: {str(e)}")

                staging_auth_configs[manager_name] = staging_auth_config

            except Exception as e:
                staging_auth_configs[manager_name] = {'error': f"Staging initialization error: {str(e)}"}

        # Check for staging authentication configuration violations
        # All managers should be able to access configuration
        accessible_managers = [name for name, config in staging_auth_configs.items()
                              if config.get('config_accessible', False)]

        if len(accessible_managers) != len(self.staging_config_managers):
            staging_auth_violations.append(
                f"Staging accessibility inconsistency: {accessible_managers} accessible, "
                f"total managers: {list(self.staging_config_managers.keys())}"
            )

        # All managers should find JWT secrets
        jwt_managers = [name for name, config in staging_auth_configs.items()
                       if config.get('jwt_secret_exists', False)]

        if len(set(jwt_managers)) > 1 and len(jwt_managers) != len(accessible_managers):
            staging_auth_violations.append(
                f"Staging JWT secret inconsistency: {jwt_managers} have secrets, "
                f"but {accessible_managers} are accessible"
            )

        # CRITICAL ASSERTION: Should fail if staging auth configuration is inconsistent
        assert len(staging_auth_violations) == 0, (
            f"STAGING AUTHENTICATION CONFIGURATION VIOLATIONS DETECTED: {staging_auth_violations}. "
            f"Authentication configuration consistency varies between managers in staging environment. "
            f"This indicates that production deployment may have unpredictable behavior "
            f"depending on which configuration manager is used during deployment. "
            f"Staging auth configurations: {staging_auth_configs}. "
            f"This threatens production stability and $500K+ ARR protection."
        )

    @pytest.mark.staging_only
    def test_staging_service_dependencies_config_consistency_violation(self):
        """
        EXPECTED TO FAIL - Service dependency configs cause staging failures.

        This test validates that all service dependencies (database, Redis, LLM)
        are configured consistently across managers in the staging environment.
        """
        if len(self.staging_config_managers) < 2:
            pytest.skip("Need at least 2 configuration managers for staging validation")

        staging_dependency_violations = []

        # Test service dependency configuration in staging
        staging_dependency_configs = {}

        for manager_name, manager_instance in self.staging_config_managers.items():
            dependency_config = {
                'database_config': {},
                'redis_config': {},
                'llm_config': {},
                'errors': []
            }

            try:
                if hasattr(manager_instance, 'get_config'):
                    if manager_name == 'UnifiedConfigManager':
                        # Test staging service dependencies via config object
                        config_obj = manager_instance.get_config()
                        dependency_config['database_config'] = {
                            'url_exists': hasattr(config_obj, 'database_url') and getattr(config_obj, 'database_url') is not None,
                            'pool_size': getattr(config_obj, 'db_pool_size', None)
                        }
                        dependency_config['redis_config'] = {
                            'url_exists': hasattr(config_obj, 'redis_url') and getattr(config_obj, 'redis_url') is not None,
                            'timeout': getattr(config_obj, 'redis_timeout', None)
                        }
                        dependency_config['llm_config'] = {
                            'key_exists': hasattr(config_obj, 'openai_api_key') and getattr(config_obj, 'openai_api_key') is not None,
                            'model': getattr(config_obj, 'default_llm_model', None)
                        }

                    else:
                        # Test staging service dependencies via direct access
                        try:
                            if manager_name == 'ConfigurationManager':
                                db_url = manager_instance.get_config('DATABASE_URL')
                                redis_url = manager_instance.get_config('REDIS_URL')
                                llm_key = manager_instance.get_config('OPENAI_API_KEY')
                            else:
                                # UnifiedConfigurationManager
                                env_config = manager_instance.get_environment_config()
                                db_url = env_config.get('DATABASE_URL')
                                redis_url = env_config.get('REDIS_URL')
                                llm_key = env_config.get('OPENAI_API_KEY')

                            dependency_config['database_config'] = {
                                'url_exists': db_url is not None and len(str(db_url)) > 0,
                                'pool_size': manager_instance.get_config('DB_POOL_SIZE', 10)
                            }
                            dependency_config['redis_config'] = {
                                'url_exists': redis_url is not None and len(str(redis_url)) > 0,
                                'timeout': manager_instance.get_config('REDIS_TIMEOUT', 5)
                            }
                            dependency_config['llm_config'] = {
                                'key_exists': llm_key is not None and len(str(llm_key)) > 0,
                                'model': manager_instance.get_config('DEFAULT_LLM_MODEL', 'gpt-4')
                            }

                        except Exception as e:
                            dependency_config['errors'].append(f"Staging dependency access error: {str(e)}")

                staging_dependency_configs[manager_name] = dependency_config

            except Exception as e:
                staging_dependency_configs[manager_name] = {'error': f"Staging dependency error: {str(e)}"}

        # Check for staging service dependency violations
        # Database URL consistency
        db_managers = [name for name, config in staging_dependency_configs.items()
                      if config.get('database_config', {}).get('url_exists', False)]

        if len(db_managers) > 0 and len(db_managers) != len(self.staging_config_managers):
            staging_dependency_violations.append(
                f"Staging database inconsistency: {db_managers} have database URLs, "
                f"total managers: {list(self.staging_config_managers.keys())}"
            )

        # Redis URL consistency
        redis_managers = [name for name, config in staging_dependency_configs.items()
                         if config.get('redis_config', {}).get('url_exists', False)]

        if len(redis_managers) > 0 and len(redis_managers) != len(self.staging_config_managers):
            staging_dependency_violations.append(
                f"Staging Redis inconsistency: {redis_managers} have Redis URLs, "
                f"total managers: {list(self.staging_config_managers.keys())}"
            )

        # LLM API key consistency
        llm_managers = [name for name, config in staging_dependency_configs.items()
                       if config.get('llm_config', {}).get('key_exists', False)]

        if len(llm_managers) > 0 and len(llm_managers) != len(self.staging_config_managers):
            staging_dependency_violations.append(
                f"Staging LLM inconsistency: {llm_managers} have LLM keys, "
                f"total managers: {list(self.staging_config_managers.keys())}"
            )

        # CRITICAL ASSERTION: Should fail if staging dependencies are inconsistent
        assert len(staging_dependency_violations) == 0, (
            f"STAGING SERVICE DEPENDENCY VIOLATIONS DETECTED: {staging_dependency_violations}. "
            f"Service dependency configuration (database, Redis, LLM) is inconsistent between "
            f"configuration managers in the staging environment. This indicates that production "
            f"services may fail unpredictably depending on configuration manager choice. "
            f"Staging dependency configurations: {staging_dependency_configs}. "
            f"This threatens production service reliability and system stability."
        )

    @pytest.mark.staging_only
    def test_staging_golden_path_complete_flow_config_protection_violation(self):
        """
        EXPECTED TO FAIL - Complete Golden Path flow breaks due to config inconsistencies.

        This test validates the complete Golden Path user flow in the real staging
        environment, ensuring that configuration manager SSOT violations don't
        break the end-to-end user experience in production-like conditions.
        """
        if len(self.staging_config_managers) < 2:
            pytest.skip("Need at least 2 configuration managers for staging Golden Path testing")

        staging_golden_path_violations = []

        # Test complete Golden Path flow in staging with each configuration manager
        for manager_name, manager_instance in self.staging_config_managers.items():
            golden_path_result = {
                'manager': manager_name,
                'flow_steps': {
                    'config_loaded': False,
                    'auth_ready': False,
                    'websocket_ready': False,
                    'llm_ready': False,
                    'complete_flow_possible': False
                },
                'staging_specific': {
                    'cloud_run_compatible': False,
                    'vpc_connector_ready': False,
                    'secrets_accessible': False
                },
                'errors': []
            }

            try:
                # Step 1: Configuration loading in staging
                if hasattr(manager_instance, 'get_config'):
                    if manager_name == 'UnifiedConfigManager':
                        config_obj = manager_instance.get_config()
                        golden_path_result['flow_steps']['config_loaded'] = config_obj is not None
                    else:
                        # Test essential configuration access
                        try:
                            env_value = manager_instance.get_config('ENVIRONMENT')
                            golden_path_result['flow_steps']['config_loaded'] = env_value is not None
                        except Exception:
                            golden_path_result['flow_steps']['config_loaded'] = False

                # Step 2: Authentication readiness in staging
                try:
                    if manager_name == 'UnifiedConfigManager':
                        jwt_secret = getattr(config_obj, 'jwt_secret_key', None)
                    else:
                        jwt_secret = manager_instance.get_config('JWT_SECRET_KEY')

                    golden_path_result['flow_steps']['auth_ready'] = jwt_secret is not None

                except Exception as e:
                    golden_path_result['errors'].append(f"Auth config error: {str(e)}")

                # Step 3: WebSocket readiness in staging
                try:
                    if manager_name == 'UnifiedConfigManager':
                        ws_port = getattr(config_obj, 'websocket_port', None)
                    else:
                        ws_port = manager_instance.get_config('WEBSOCKET_PORT')

                    golden_path_result['flow_steps']['websocket_ready'] = ws_port is not None

                except Exception as e:
                    golden_path_result['errors'].append(f"WebSocket config error: {str(e)}")

                # Step 4: LLM readiness in staging
                try:
                    if manager_name == 'UnifiedConfigManager':
                        llm_key = getattr(config_obj, 'openai_api_key', None)
                    else:
                        llm_key = manager_instance.get_config('OPENAI_API_KEY')

                    golden_path_result['flow_steps']['llm_ready'] = llm_key is not None

                except Exception as e:
                    golden_path_result['errors'].append(f"LLM config error: {str(e)}")

                # Step 5: Complete flow assessment
                golden_path_result['flow_steps']['complete_flow_possible'] = all([
                    golden_path_result['flow_steps']['config_loaded'],
                    golden_path_result['flow_steps']['auth_ready'],
                    golden_path_result['flow_steps']['websocket_ready'],
                    golden_path_result['flow_steps']['llm_ready']
                ])

                # Staging-specific checks
                # Cloud Run compatibility
                k_service = os.getenv('K_SERVICE', '')
                golden_path_result['staging_specific']['cloud_run_compatible'] = bool(k_service)

                # VPC connector readiness (for database/Redis access)
                try:
                    if manager_name == 'UnifiedConfigManager':
                        db_url = getattr(config_obj, 'database_url', None)
                    else:
                        db_url = manager_instance.get_config('DATABASE_URL')

                    golden_path_result['staging_specific']['vpc_connector_ready'] = (
                        db_url is not None and 'private' not in str(db_url).lower()
                    )

                except Exception:
                    golden_path_result['staging_specific']['vpc_connector_ready'] = False

                # Secrets accessibility
                try:
                    secrets_accessible = all([
                        golden_path_result['flow_steps']['auth_ready'],
                        golden_path_result['flow_steps']['llm_ready']
                    ])
                    golden_path_result['staging_specific']['secrets_accessible'] = secrets_accessible

                except Exception:
                    golden_path_result['staging_specific']['secrets_accessible'] = False

            except Exception as e:
                golden_path_result['errors'].append(f"Staging Golden Path error: {str(e)}")

            # Check if this manager breaks the staging Golden Path
            if not golden_path_result['flow_steps']['complete_flow_possible']:
                staging_golden_path_violations.append(golden_path_result)

        # Check for Golden Path consistency across managers in staging
        working_managers = []
        broken_managers = []

        for manager_name in self.staging_config_managers.keys():
            is_working = True
            for violation in staging_golden_path_violations:
                if violation['manager'] == manager_name:
                    is_working = False
                    broken_managers.append(manager_name)
                    break
            if is_working:
                working_managers.append(manager_name)

        # If some managers work in staging while others don't, that's a critical violation
        if working_managers and broken_managers:
            staging_golden_path_violations.append({
                'type': 'staging_golden_path_inconsistency',
                'working_managers': working_managers,
                'broken_managers': broken_managers,
                'message': 'Golden Path success in staging depends on configuration manager choice'
            })

        # CRITICAL ASSERTION: Should fail if staging Golden Path is broken or inconsistent
        assert len(staging_golden_path_violations) == 0, (
            f"STAGING GOLDEN PATH VIOLATIONS DETECTED: {staging_golden_path_violations}. "
            f"The complete Golden Path user flow fails or behaves inconsistently in the "
            f"staging environment depending on which configuration manager is used. "
            f"This indicates that production deployment will have unpredictable behavior "
            f"and threatens the reliability of the $500K+ ARR user experience. "
            f"Staging must provide consistent Golden Path functionality across all "
            f"configuration managers to ensure production deployment safety."
        )