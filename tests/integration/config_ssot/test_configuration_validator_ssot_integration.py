"""
PHASE 2: SSOT Integration Tests
Tests that validate consolidated SSOT behavior and FAIL before consolidation, PASS after.

These tests validate the proper integration of the unified ConfigurationValidator SSOT
and will FAIL before SSOT consolidation (showing the need) and PASS after consolidation.

CRITICAL: These tests demonstrate the desired end-state where all services use
the single CentralConfigurationValidator from shared/configuration/central_config_validator.py

Business Impact: Ensures consistent OAuth validation prevents $500K+ ARR authentication failures
"""

import asyncio
import logging
import unittest
import tempfile
import os
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# SSOT Target - This should be the ONLY validator after consolidation
from shared.configuration.central_config_validator import CentralConfigurationValidator

logger = logging.getLogger(__name__)


class TestConfigurationValidatorSSOTIntegration(SSotAsyncTestCase, unittest.TestCase):
    """
    SSOT Integration Tests
    
    These tests validate consolidated SSOT behavior.
    They should FAIL initially (showing SSOT not implemented) and PASS after consolidation.
    """

    def setUp(self):
        """Set up test environment with comprehensive configuration."""
        super().setUp()
        
        # Comprehensive test environment for SSOT validation
        self.ssot_test_env = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': 'ssot_test_jwt_secret_key_minimum_length_requirement',
            'SERVICE_SECRET': 'ssot_test_service_secret_for_validation',
            'TESTING': 'false',
            'OAUTH_CLIENT_ID': 'ssot_oauth_client_id_test',
            'OAUTH_CLIENT_SECRET': 'ssot_oauth_client_secret_minimum_length',
            'DATABASE_URL': 'postgresql://ssot_user:ssot_pass@localhost:5432/ssot_test_db',
            'REDIS_URL': 'redis://localhost:6379/1',
            'WEBSOCKET_ORIGIN_ALLOWED': 'https://staging.netra.com,https://test.netra.com',
            'LOG_LEVEL': 'INFO',
            'DEBUG': 'false'
        }
        
        # Mock environment for SSOT testing
        self.env_patcher = patch.dict('os.environ', self.ssot_test_env)
        self.env_patcher.start()

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()
        if hasattr(self, 'env_patcher'):
            self.env_patcher.stop()

    def test_unified_oauth_validation_all_services(self):
        """
        Test unified OAuth validation across all services using SSOT CentralConfigurationValidator.
        
        This test FAILS initially (no unified validation) and PASSES after SSOT consolidation.
        Validates that all services use the same OAuth validation logic.
        """
        # Test OAuth configurations that should be validated consistently
        oauth_test_cases = [
            {
                'name': 'minimal_valid',
                'config': {
                    'OAUTH_CLIENT_ID': 'test_client_id',
                    'OAUTH_CLIENT_SECRET': 'test_client_secret_valid_length'
                },
                'should_pass': True
            },
            {
                'name': 'missing_client_id',
                'config': {
                    'OAUTH_CLIENT_SECRET': 'test_client_secret_valid_length'
                },
                'should_pass': False
            },
            {
                'name': 'short_secret',
                'config': {
                    'OAUTH_CLIENT_ID': 'test_client_id',
                    'OAUTH_CLIENT_SECRET': 'short'
                },
                'should_pass': False
            }
        ]
        
        # Test that SSOT CentralConfigurationValidator handles all cases consistently
        ssot_validator = CentralConfigurationValidator()
        
        for test_case in oauth_test_cases:
            with self.subTest(test_case=test_case['name']):
                with patch.dict('os.environ', test_case['config'], clear=True):
                    try:
                        # This should be the ONLY OAuth validation after SSOT consolidation
                        validation_result = ssot_validator.validate_oauth_configuration()
                        oauth_valid = True
                        validation_error = None
                    except Exception as e:
                        oauth_valid = False
                        validation_error = str(e)
                    
                    # Log validation results for debugging
                    logger.info(f"SSOT OAuth validation {test_case['name']}: "
                              f"valid={oauth_valid}, expected={test_case['should_pass']}")
                    
                    # Validate expected behavior
                    if test_case['should_pass']:
                        self.assertTrue(
                            oauth_valid,
                            f"SSOT OAuth validation should pass for {test_case['name']}: {validation_error}"
                        )
                    else:
                        self.assertFalse(
                            oauth_valid,
                            f"SSOT OAuth validation should fail for {test_case['name']}"
                        )
        
        # This assertion will FAIL before SSOT consolidation (no unified validation exists)
        # and PASS after consolidation (unified SSOT validation working)
        self.assertTrue(
            hasattr(ssot_validator, 'validate_oauth_configuration'),
            "SSOT CentralConfigurationValidator must have unified OAuth validation after consolidation"
        )

    def test_environment_detection_ssot_consistency(self):
        """
        Test environment detection SSOT consistency across all use cases.
        
        This test FAILS initially (multiple detection methods) and PASSES after SSOT consolidation.
        Validates single source of truth for environment detection.
        """
        test_environments = ['development', 'test', 'staging', 'production']
        
        ssot_validator = CentralConfigurationValidator()
        
        environment_consistency_results = {}
        
        for env in test_environments:
            with patch.dict('os.environ', {'ENVIRONMENT': env}):
                try:
                    # SSOT environment detection
                    detected_env = ssot_validator.get_current_environment()
                    
                    # Validate environment normalization consistency
                    if env == 'test':
                        expected_normalized = 'test'
                    elif env == 'development':
                        expected_normalized = 'development'
                    elif env == 'staging':
                        expected_normalized = 'staging'
                    elif env == 'production':
                        expected_normalized = 'production'
                    else:
                        expected_normalized = env
                    
                    environment_consistency_results[env] = {
                        'detected': detected_env,
                        'expected': expected_normalized,
                        'consistent': detected_env == expected_normalized
                    }
                    
                except Exception as e:
                    environment_consistency_results[env] = {
                        'detected': None,
                        'expected': env,
                        'consistent': False,
                        'error': str(e)
                    }
        
        # Validate all environments detected consistently
        all_consistent = all(
            result.get('consistent', False) 
            for result in environment_consistency_results.values()
        )
        
        # Log results for debugging
        for env, result in environment_consistency_results.items():
            logger.info(f"SSOT Environment detection {env}: {result}")
        
        # This assertion FAILS before SSOT consolidation (inconsistent detection)
        # and PASSES after consolidation (consistent SSOT detection)
        self.assertTrue(
            all_consistent,
            f"SSOT environment detection must be consistent: {environment_consistency_results}"
        )
        
        # Validate SSOT method exists
        self.assertTrue(
            hasattr(ssot_validator, 'get_current_environment'),
            "SSOT CentralConfigurationValidator must have unified environment detection"
        )

    def test_jwt_secret_validation_unified_behavior(self):
        """
        Test JWT secret validation unified behavior through SSOT.
        
        This test FAILS initially (inconsistent JWT validation) and PASSES after SSOT consolidation.
        Validates consistent JWT security requirements across all services.
        """
        jwt_test_scenarios = [
            {
                'name': 'valid_length',
                'jwt_secret': 'valid_jwt_secret_key_with_sufficient_length_for_security',
                'should_pass': True
            },
            {
                'name': 'minimum_length',
                'jwt_secret': 'minimum_length_jwt_key',  # Exactly minimum
                'should_pass': True
            },
            {
                'name': 'too_short',
                'jwt_secret': 'short',
                'should_pass': False
            },
            {
                'name': 'empty',
                'jwt_secret': '',
                'should_pass': False
            }
        ]
        
        ssot_validator = CentralConfigurationValidator()
        jwt_validation_results = {}
        
        for scenario in jwt_test_scenarios:
            with patch.dict('os.environ', {'JWT_SECRET_KEY': scenario['jwt_secret']}, clear=True):
                try:
                    # SSOT JWT validation
                    jwt_valid = ssot_validator.validate_jwt_configuration()
                    validation_passed = True
                    validation_error = None
                except Exception as e:
                    validation_passed = False
                    validation_error = str(e)
                
                jwt_validation_results[scenario['name']] = {
                    'passed': validation_passed,
                    'expected': scenario['should_pass'],
                    'error': validation_error
                }
        
        # Validate all JWT scenarios behave as expected
        all_jwt_consistent = True
        for scenario_name, result in jwt_validation_results.items():
            if result['passed'] != result['expected']:
                all_jwt_consistent = False
                logger.warning(f"JWT validation inconsistency in {scenario_name}: {result}")
        
        # This assertion FAILS before SSOT consolidation (inconsistent JWT validation)
        # and PASSES after consolidation (consistent SSOT JWT validation)
        self.assertTrue(
            all_jwt_consistent,
            f"SSOT JWT validation must be consistent across scenarios: {jwt_validation_results}"
        )
        
        # Validate SSOT JWT validation method exists
        self.assertTrue(
            hasattr(ssot_validator, 'validate_jwt_configuration'),
            "SSOT CentralConfigurationValidator must have unified JWT validation"
        )

    def test_database_config_ssot_delegation(self):
        """
        Test database configuration SSOT delegation across all database scenarios.
        
        This test FAILS initially (multiple DB validation patterns) and PASSES after SSOT consolidation.
        Validates single source of truth for database configuration validation.
        """
        database_scenarios = [
            {
                'name': 'full_url_only',
                'config': {
                    'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'
                },
                'should_pass': True
            },
            {
                'name': 'component_based',
                'config': {
                    'DB_HOST': 'localhost',
                    'DB_PORT': '5432',
                    'DB_NAME': 'testdb',
                    'DB_USER': 'user',
                    'DB_PASSWORD': 'pass'
                },
                'should_pass': True
            },
            {
                'name': 'both_url_and_components',
                'config': {
                    'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb',
                    'DB_HOST': 'localhost',
                    'DB_PORT': '5432'
                },
                'should_pass': True
            },
            {
                'name': 'missing_all',
                'config': {},
                'should_pass': False
            }
        ]
        
        ssot_validator = CentralConfigurationValidator()
        db_validation_results = {}
        
        for scenario in database_scenarios:
            with patch.dict('os.environ', scenario['config'], clear=True):
                try:
                    # SSOT database validation
                    db_valid = ssot_validator.validate_database_configuration()
                    validation_passed = True
                    validation_error = None
                except Exception as e:
                    validation_passed = False
                    validation_error = str(e)
                
                db_validation_results[scenario['name']] = {
                    'passed': validation_passed,
                    'expected': scenario['should_pass'],
                    'error': validation_error
                }
        
        # Validate database scenarios behave consistently
        all_db_consistent = True
        for scenario_name, result in db_validation_results.items():
            if result['passed'] != result['expected']:
                all_db_consistent = False
                logger.warning(f"Database validation inconsistency in {scenario_name}: {result}")
        
        # This assertion FAILS before SSOT consolidation (inconsistent DB validation)
        # and PASSES after consolidation (consistent SSOT DB validation)
        self.assertTrue(
            all_db_consistent,
            f"SSOT database validation must be consistent: {db_validation_results}"
        )
        
        # Validate SSOT database validation method exists
        self.assertTrue(
            hasattr(ssot_validator, 'validate_database_configuration'),
            "SSOT CentralConfigurationValidator must have unified database validation"
        )

    def test_golden_path_configuration_health_monitoring(self):
        """
        Test Golden Path configuration health monitoring through SSOT.
        
        This test FAILS initially (no unified health monitoring) and PASSES after SSOT consolidation.
        Validates SSOT provides comprehensive Golden Path configuration monitoring.
        """
        # Golden Path comprehensive configuration
        golden_path_config = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': 'golden_path_jwt_secret_key_sufficient_length',
            'SERVICE_SECRET': 'golden_path_service_secret',
            'OAUTH_CLIENT_ID': 'golden_path_oauth_client_id',
            'OAUTH_CLIENT_SECRET': 'golden_path_oauth_client_secret_sufficient',
            'DATABASE_URL': 'postgresql://golden:path@staging-db:5432/netra_staging',
            'REDIS_URL': 'redis://staging-redis:6379/0',
            'WEBSOCKET_ORIGIN_ALLOWED': 'https://staging.netra.com',
            'LOG_LEVEL': 'INFO'
        }
        
        with patch.dict('os.environ', golden_path_config):
            ssot_validator = CentralConfigurationValidator()
            
            # Test comprehensive SSOT health monitoring
            try:
                # SSOT comprehensive validation
                health_result = ssot_validator.validate_complete_configuration()
                golden_path_healthy = True
                health_error = None
            except Exception as e:
                golden_path_healthy = False
                health_error = str(e)
            
            # Test individual component health through SSOT
            component_health = {}
            
            # Environment health
            try:
                env_health = ssot_validator.validate_environment_configuration()
                component_health['environment'] = True
            except Exception as e:
                component_health['environment'] = False
                component_health['environment_error'] = str(e)
            
            # Auth health
            try:
                auth_health = ssot_validator.validate_authentication_configuration()
                component_health['auth'] = True
            except Exception as e:
                component_health['auth'] = False
                component_health['auth_error'] = str(e)
            
            # Database health
            try:
                db_health = ssot_validator.validate_database_configuration()
                component_health['database'] = True
            except Exception as e:
                component_health['database'] = False
                component_health['database_error'] = str(e)
            
            # Validate Golden Path health monitoring works
            all_components_healthy = all(
                component_health.get(comp, False) 
                for comp in ['environment', 'auth', 'database']
            )
        
        # This assertion FAILS before SSOT consolidation (no unified health monitoring)
        # and PASSES after consolidation (SSOT health monitoring working)
        self.assertTrue(
            golden_path_healthy,
            f"SSOT Golden Path health monitoring must work: {health_error}"
        )
        
        self.assertTrue(
            all_components_healthy,
            f"SSOT component health monitoring must work: {component_health}"
        )
        
        # Validate SSOT health monitoring methods exist
        self.assertTrue(
            hasattr(ssot_validator, 'validate_complete_configuration'),
            "SSOT CentralConfigurationValidator must have comprehensive health monitoring"
        )

    def test_configuration_drift_detection_ssot(self):
        """
        Test configuration drift detection through SSOT.
        
        This test FAILS initially (no drift detection) and PASSES after SSOT consolidation.
        Validates SSOT can detect configuration changes that might break Golden Path.
        """
        # Baseline Golden Path configuration
        baseline_config = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': 'baseline_jwt_secret_key_sufficient_length',
            'OAUTH_CLIENT_ID': 'baseline_oauth_client_id',
            'DATABASE_URL': 'postgresql://baseline:config@localhost:5432/baseline_db'
        }
        
        # Configuration drift scenarios
        drift_scenarios = [
            {
                'name': 'environment_drift',
                'config': dict(baseline_config, ENVIRONMENT='production'),
                'should_detect_drift': True
            },
            {
                'name': 'jwt_secret_change',
                'config': dict(baseline_config, JWT_SECRET_KEY='changed_jwt_secret_key'),
                'should_detect_drift': True
            },
            {
                'name': 'database_drift',
                'config': dict(baseline_config, DATABASE_URL='postgresql://drift:config@localhost:5432/drift_db'),
                'should_detect_drift': True
            },
            {
                'name': 'no_drift',
                'config': baseline_config,
                'should_detect_drift': False
            }
        ]
        
        ssot_validator = CentralConfigurationValidator()
        
        # Establish baseline with SSOT
        with patch.dict('os.environ', baseline_config):
            try:
                baseline_fingerprint = ssot_validator.get_configuration_fingerprint()
                baseline_established = True
            except Exception as e:
                baseline_established = False
                baseline_error = str(e)
        
        # Test drift detection for each scenario
        drift_detection_results = {}
        
        for scenario in drift_scenarios:
            with patch.dict('os.environ', scenario['config']):
                try:
                    current_fingerprint = ssot_validator.get_configuration_fingerprint()
                    drift_detected = current_fingerprint != baseline_fingerprint
                    drift_detection_results[scenario['name']] = {
                        'drift_detected': drift_detected,
                        'expected_drift': scenario['should_detect_drift'],
                        'consistent': drift_detected == scenario['should_detect_drift']
                    }
                except Exception as e:
                    drift_detection_results[scenario['name']] = {
                        'drift_detected': None,
                        'expected_drift': scenario['should_detect_drift'],
                        'consistent': False,
                        'error': str(e)
                    }
        
        # Validate drift detection works correctly
        all_drift_detection_correct = all(
            result.get('consistent', False)
            for result in drift_detection_results.values()
        )
        
        # This assertion FAILS before SSOT consolidation (no drift detection)
        # and PASSES after consolidation (SSOT drift detection working)
        self.assertTrue(
            baseline_established,
            f"SSOT baseline configuration fingerprinting must work: {baseline_error if not baseline_established else 'OK'}"
        )
        
        self.assertTrue(
            all_drift_detection_correct,
            f"SSOT drift detection must work correctly: {drift_detection_results}"
        )
        
        # Validate SSOT drift detection method exists
        self.assertTrue(
            hasattr(ssot_validator, 'get_configuration_fingerprint'),
            "SSOT CentralConfigurationValidator must have drift detection capability"
        )

    def test_progressive_validation_mode_ssot_compliance(self):
        """
        Test progressive validation mode SSOT compliance.
        
        This test FAILS initially (no unified validation modes) and PASSES after SSOT consolidation.
        Validates SSOT supports different validation strictness levels.
        """
        # Test different validation modes
        validation_modes = ['warn', 'enforce_critical', 'enforce_all']
        
        # Configuration with intentional issues for mode testing
        test_config = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': 'short',  # Intentionally too short
            'OAUTH_CLIENT_ID': 'test_client',
            'DATABASE_URL': 'invalid_db_url'  # Intentionally invalid
        }
        
        ssot_validator = CentralConfigurationValidator()
        validation_mode_results = {}
        
        with patch.dict('os.environ', test_config):
            for mode in validation_modes:
                try:
                    # Test SSOT validation with different modes
                    if hasattr(ssot_validator, 'validate_with_mode'):
                        validation_result = ssot_validator.validate_with_mode(mode)
                        mode_behavior = 'passes_with_mode'
                    else:
                        # Test progressive enforcement
                        if mode == 'warn':
                            # Should warn but not fail
                            validation_result = ssot_validator.validate_configuration_warnings_only()
                            mode_behavior = 'warns_only'
                        elif mode == 'enforce_critical':
                            # Should enforce critical issues only
                            validation_result = ssot_validator.validate_critical_only()
                            mode_behavior = 'enforces_critical'
                        elif mode == 'enforce_all':
                            # Should enforce everything
                            validation_result = ssot_validator.validate_complete_configuration()
                            mode_behavior = 'enforces_all'
                        else:
                            mode_behavior = 'unknown_mode'
                    
                    validation_mode_results[mode] = {
                        'behavior': mode_behavior,
                        'result': validation_result,
                        'error': None
                    }
                    
                except Exception as e:
                    validation_mode_results[mode] = {
                        'behavior': 'fails',
                        'result': None,
                        'error': str(e)
                    }
        
        # Validate progressive validation modes work
        expected_behaviors = {
            'warn': ['warns_only', 'passes_with_mode'],
            'enforce_critical': ['enforces_critical', 'passes_with_mode'],
            'enforce_all': ['enforces_all', 'fails']  # Should fail with invalid config
        }
        
        progressive_validation_working = True
        for mode, result in validation_mode_results.items():
            if result['behavior'] not in expected_behaviors.get(mode, []):
                progressive_validation_working = False
                logger.warning(f"Progressive validation mode {mode} unexpected behavior: {result}")
        
        # This assertion FAILS before SSOT consolidation (no progressive validation)
        # and PASSES after consolidation (SSOT progressive validation working)
        self.assertTrue(
            progressive_validation_working,
            f"SSOT progressive validation modes must work: {validation_mode_results}"
        )
        
        # Validate SSOT has progressive validation capability
        has_progressive_validation = (
            hasattr(ssot_validator, 'validate_with_mode') or
            (hasattr(ssot_validator, 'validate_configuration_warnings_only') and
             hasattr(ssot_validator, 'validate_critical_only'))
        )
        
        self.assertTrue(
            has_progressive_validation,
            "SSOT CentralConfigurationValidator must have progressive validation modes"
        )

    def test_cross_service_configuration_consistency(self):
        """
        Test cross-service configuration consistency through SSOT.
        
        This test FAILS initially (services use different validators) and PASSES after SSOT consolidation.
        Validates all services use the same SSOT configuration validation.
        """
        # Service-specific configuration scenarios
        service_scenarios = [
            {
                'service': 'backend',
                'config': {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_KEY': 'backend_jwt_secret_key_sufficient_length',
                    'DATABASE_URL': 'postgresql://backend:service@localhost:5432/backend_db'
                }
            },
            {
                'service': 'auth',
                'config': {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_KEY': 'auth_jwt_secret_key_sufficient_length',
                    'OAUTH_CLIENT_ID': 'auth_oauth_client_id',
                    'OAUTH_CLIENT_SECRET': 'auth_oauth_client_secret_sufficient'
                }
            },
            {
                'service': 'websocket',
                'config': {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_KEY': 'websocket_jwt_secret_key_sufficient_length',
                    'WEBSOCKET_ORIGIN_ALLOWED': 'https://staging.netra.com'
                }
            }
        ]
        
        ssot_validator = CentralConfigurationValidator()
        cross_service_results = {}
        
        for scenario in service_scenarios:
            with patch.dict('os.environ', scenario['config']):
                try:
                    # All services should use the same SSOT validation
                    service_validation = ssot_validator.validate_service_configuration(scenario['service'])
                    cross_service_results[scenario['service']] = {
                        'valid': True,
                        'error': None,
                        'uses_ssot': True
                    }
                except Exception as e:
                    cross_service_results[scenario['service']] = {
                        'valid': False,
                        'error': str(e),
                        'uses_ssot': hasattr(ssot_validator, 'validate_service_configuration')
                    }
        
        # Validate all services can be validated through SSOT
        all_services_use_ssot = all(
            result.get('uses_ssot', False)
            for result in cross_service_results.values()
        )
        
        all_services_validated = all(
            result.get('valid', False)
            for result in cross_service_results.values()
        )
        
        # This assertion FAILS before SSOT consolidation (no cross-service validation)
        # and PASSES after consolidation (SSOT cross-service validation working)
        self.assertTrue(
            all_services_use_ssot,
            f"All services must use SSOT validation: {cross_service_results}"
        )
        
        self.assertTrue(
            all_services_validated,
            f"SSOT must validate all service configurations: {cross_service_results}"
        )
        
        # Validate SSOT cross-service validation method exists
        self.assertTrue(
            hasattr(ssot_validator, 'validate_service_configuration'),
            "SSOT CentralConfigurationValidator must have cross-service validation"
        )


if __name__ == '__main__':
    unittest.main()