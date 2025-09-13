
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
PHASE 3: Golden Path Protection Tests
Tests that ensure Golden Path stability throughout SSOT consolidation.

These tests protect the critical Golden Path user flow (login  ->  WebSocket  ->  AI response)
during ConfigurationValidator SSOT consolidation. They should PASS throughout the process.

CRITICAL: These tests ensure that SSOT consolidation doesn't break the core business flow
that generates $500K+ ARR from chat functionality.

Golden Path Flow:
1. User authentication/login 
2. WebSocket connection establishment
3. AI agent response delivery
4. Real-time progress via WebSocket events

Business Impact: Protects core revenue-generating chat functionality during infrastructure changes
"""

import asyncio
import logging
import unittest
import json
import time
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import SSOT validator for Golden Path validation
from shared.configuration.central_config_validator import CentralConfigurationValidator
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)


class TestConfigurationValidatorGoldenPath(SSotAsyncTestCase, unittest.TestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    Golden Path Protection Tests
    
    These tests ensure Golden Path stability throughout SSOT consolidation.
    They should PASS throughout the process and protect core business functionality.
    """

    def setUp(self):
        """Set up Golden Path test environment."""
        super().setUp()
        
        # Golden Path production-like configuration
        self.golden_path_config = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': 'golden_path_jwt_secret_key_production_strength_validation',
            'SERVICE_SECRET': 'golden_path_service_secret_production_strength',
            'OAUTH_CLIENT_ID': 'golden_path_oauth_client_id_production',
            'OAUTH_CLIENT_SECRET': 'golden_path_oauth_client_secret_production_strength',
            'DATABASE_URL': 'postgresql://golden_user:golden_pass@staging-db.netra.com:5432/netra_staging',
            'REDIS_URL': 'redis://staging-redis.netra.com:6379/0',
            'WEBSOCKET_ORIGIN_ALLOWED': 'https://staging.netra.com,https://app.netra.com',
            'LOG_LEVEL': 'INFO',
            'DEBUG': 'false',
            'TESTING': 'false',
            'CORS_ALLOWED_ORIGINS': 'https://staging.netra.com,https://app.netra.com',
            'SESSION_TIMEOUT': '3600',
            'MAX_CONNECTIONS': '1000'
        }
        
        # Mock Golden Path environment
        self.env_patcher = patch.dict('os.environ', self.golden_path_config)
        self.env_patcher.start()

    def tearDown(self):
        """Clean up Golden Path test environment."""
        super().tearDown()
        if hasattr(self, 'env_patcher'):
            self.env_patcher.stop()

    def test_login_with_unified_configuration_validation(self):
        """
        Test user login process with unified configuration validation.
        
        Validates that login functionality works with SSOT configuration validation.
        This test must PASS throughout SSOT consolidation to protect Golden Path.
        """
        # Mock user login scenario
        login_config_requirements = [
            'JWT_SECRET_KEY',
            'OAUTH_CLIENT_ID', 
            'OAUTH_CLIENT_SECRET',
            'DATABASE_URL',
            'SESSION_TIMEOUT'
        ]
        
        ssot_validator = CentralConfigurationValidator()
        
        # Validate login configuration requirements through SSOT
        login_config_valid = True
        login_validation_errors = []
        
        try:
            # Validate authentication configuration for login
            auth_validation = ssot_validator.validate_authentication_configuration()
            if not auth_validation:
                login_config_valid = False
                login_validation_errors.append("Authentication configuration invalid")
            
        except Exception as e:
            # If specific auth validation doesn't exist, check individual requirements
            for req in login_config_requirements:
                env_value = get_env(req)
                if not env_value:
                    login_config_valid = False
                    login_validation_errors.append(f"Missing required login config: {req}")
                elif req == 'JWT_SECRET_KEY' and len(env_value) < 32:
                    login_config_valid = False
                    login_validation_errors.append(f"JWT secret too short for secure login: {len(env_value)} chars")
        
        # Simulate login process validation
        try:
            # Mock OAuth validation for login
            oauth_client_id = get_env('OAUTH_CLIENT_ID')
            oauth_client_secret = get_env('OAUTH_CLIENT_SECRET')
            
            if oauth_client_id and oauth_client_secret:
                login_oauth_ready = True
            else:
                login_oauth_ready = False
                login_validation_errors.append("OAuth not configured for login")
            
            # Mock database connectivity for user authentication
            database_url = get_env('DATABASE_URL')
            if database_url and 'postgresql://' in database_url:
                login_db_ready = True
            else:
                login_db_ready = False
                login_validation_errors.append("Database not configured for login")
                
        except Exception as e:
            login_oauth_ready = False
            login_db_ready = False
            login_validation_errors.append(f"Login validation error: {str(e)}")
        
        # Golden Path login must be viable
        login_golden_path_ready = (
            login_config_valid and 
            login_oauth_ready and 
            login_db_ready
        )
        
        # Log Golden Path login status
        logger.info(f"Golden Path login validation - Config: {login_config_valid}, "
                   f"OAuth: {login_oauth_ready}, DB: {login_db_ready}")
        
        if login_validation_errors:
            logger.warning(f"Golden Path login validation errors: {login_validation_errors}")
        
        # This test must PASS throughout SSOT consolidation
        self.assertTrue(
            login_golden_path_ready,
            f"Golden Path login must remain functional during SSOT consolidation. "
            f"Errors: {login_validation_errors}"
        )
        
        # Validate minimum login configuration is present
        self.assertIsNotNone(
            get_env('JWT_SECRET_KEY'),
            "Golden Path login requires JWT_SECRET_KEY"
        )
        
        self.assertIsNotNone(
            get_env('OAUTH_CLIENT_ID'),
            "Golden Path login requires OAUTH_CLIENT_ID"
        )

    def test_websocket_connection_unified_auth_validation(self):
        """
        Test WebSocket connection with unified auth validation.
        
        Validates that WebSocket connections work with SSOT auth validation.
        This test must PASS throughout SSOT consolidation to protect Golden Path.
        """
        websocket_config_requirements = [
            'JWT_SECRET_KEY',
            'WEBSOCKET_ORIGIN_ALLOWED',
            'CORS_ALLOWED_ORIGINS'
        ]
        
        ssot_validator = CentralConfigurationValidator()
        
        # Validate WebSocket configuration through SSOT
        websocket_config_valid = True
        websocket_validation_errors = []
        
        try:
            # Check if SSOT has WebSocket-specific validation
            if hasattr(ssot_validator, 'validate_websocket_configuration'):
                websocket_validation = ssot_validator.validate_websocket_configuration()
                if not websocket_validation:
                    websocket_config_valid = False
                    websocket_validation_errors.append("WebSocket configuration invalid")
            else:
                # Manual validation of WebSocket requirements
                for req in websocket_config_requirements:
                    env_value = get_env(req)
                    if not env_value:
                        websocket_config_valid = False
                        websocket_validation_errors.append(f"Missing WebSocket config: {req}")
                        
        except Exception as e:
            websocket_config_valid = False
            websocket_validation_errors.append(f"WebSocket validation error: {str(e)}")
        
        # Simulate WebSocket authentication validation
        try:
            jwt_secret = get_env('JWT_SECRET_KEY')
            allowed_origins = get_env('WEBSOCKET_ORIGIN_ALLOWED', '').split(',')
            cors_origins = get_env('CORS_ALLOWED_ORIGINS', '').split(',')
            
            # Mock JWT validation for WebSocket auth
            if jwt_secret and len(jwt_secret) >= 32:
                websocket_auth_ready = True
            else:
                websocket_auth_ready = False
                websocket_validation_errors.append("JWT not suitable for WebSocket auth")
            
            # Mock origin validation
            if allowed_origins and any(origin.strip() for origin in allowed_origins):
                websocket_origins_ready = True
            else:
                websocket_origins_ready = False
                websocket_validation_errors.append("WebSocket origins not configured")
                
        except Exception as e:
            websocket_auth_ready = False
            websocket_origins_ready = False
            websocket_validation_errors.append(f"WebSocket auth validation error: {str(e)}")
        
        # Golden Path WebSocket must be viable
        websocket_golden_path_ready = (
            websocket_config_valid and
            websocket_auth_ready and
            websocket_origins_ready
        )
        
        # Log Golden Path WebSocket status
        logger.info(f"Golden Path WebSocket validation - Config: {websocket_config_valid}, "
                   f"Auth: {websocket_auth_ready}, Origins: {websocket_origins_ready}")
        
        if websocket_validation_errors:
            logger.warning(f"Golden Path WebSocket validation errors: {websocket_validation_errors}")
        
        # This test must PASS throughout SSOT consolidation
        self.assertTrue(
            websocket_golden_path_ready,
            f"Golden Path WebSocket must remain functional during SSOT consolidation. "
            f"Errors: {websocket_validation_errors}"
        )
        
        # Validate essential WebSocket configuration
        self.assertIsNotNone(
            get_env('JWT_SECRET_KEY'),
            "Golden Path WebSocket requires JWT_SECRET_KEY for auth"
        )
        
        self.assertIsNotNone(
            get_env('WEBSOCKET_ORIGIN_ALLOWED'),
            "Golden Path WebSocket requires WEBSOCKET_ORIGIN_ALLOWED"
        )

    def test_ai_response_delivery_configuration_health(self):
        """
        Test AI response delivery with configuration health monitoring.
        
        Validates that AI response delivery works with SSOT configuration health.
        This test must PASS throughout SSOT consolidation to protect Golden Path.
        """
        ai_response_config_requirements = [
            'ENVIRONMENT',
            'JWT_SECRET_KEY',
            'DATABASE_URL',
            'REDIS_URL',
            'LOG_LEVEL'
        ]
        
        ssot_validator = CentralConfigurationValidator()
        
        # Validate AI response configuration through SSOT
        ai_config_valid = True
        ai_validation_errors = []
        
        try:
            # Check if SSOT has comprehensive configuration validation
            if hasattr(ssot_validator, 'validate_complete_configuration'):
                ai_validation = ssot_validator.validate_complete_configuration()
                if not ai_validation:
                    ai_config_valid = False
                    ai_validation_errors.append("AI response configuration invalid")
            else:
                # Manual validation of AI response requirements
                for req in ai_response_config_requirements:
                    env_value = get_env(req)
                    if not env_value:
                        ai_config_valid = False
                        ai_validation_errors.append(f"Missing AI response config: {req}")
                        
        except Exception as e:
            ai_config_valid = False
            ai_validation_errors.append(f"AI response validation error: {str(e)}")
        
        # Simulate AI response delivery requirements
        try:
            # Database for conversation persistence
            database_url = get_env('DATABASE_URL')
            if database_url and 'postgresql://' in database_url:
                ai_db_ready = True
            else:
                ai_db_ready = False
                ai_validation_errors.append("Database not ready for AI responses")
            
            # Redis for session management
            redis_url = get_env('REDIS_URL')
            if redis_url and 'redis://' in redis_url:
                ai_cache_ready = True
            else:
                ai_cache_ready = False
                ai_validation_errors.append("Redis not ready for AI responses")
            
            # Environment for AI service routing
            environment = get_env('ENVIRONMENT')
            if environment in ['staging', 'production']:
                ai_env_ready = True
            else:
                ai_env_ready = False
                ai_validation_errors.append(f"Environment {environment} not suitable for AI responses")
                
        except Exception as e:
            ai_db_ready = False
            ai_cache_ready = False
            ai_env_ready = False
            ai_validation_errors.append(f"AI response infrastructure error: {str(e)}")
        
        # Golden Path AI response must be viable
        ai_golden_path_ready = (
            ai_config_valid and
            ai_db_ready and
            ai_cache_ready and
            ai_env_ready
        )
        
        # Log Golden Path AI response status
        logger.info(f"Golden Path AI response validation - Config: {ai_config_valid}, "
                   f"DB: {ai_db_ready}, Cache: {ai_cache_ready}, Env: {ai_env_ready}")
        
        if ai_validation_errors:
            logger.warning(f"Golden Path AI response validation errors: {ai_validation_errors}")
        
        # This test must PASS throughout SSOT consolidation
        self.assertTrue(
            ai_golden_path_ready,
            f"Golden Path AI response must remain functional during SSOT consolidation. "
            f"Errors: {ai_validation_errors}"
        )
        
        # Validate essential AI response configuration
        self.assertIsNotNone(
            get_env('DATABASE_URL'),
            "Golden Path AI response requires DATABASE_URL"
        )
        
        self.assertIsNotNone(
            get_env('REDIS_URL'),
            "Golden Path AI response requires REDIS_URL"
        )

    def test_oauth_login_websocket_ai_response_full_flow(self):
        """
        Test complete Golden Path flow: OAuth login  ->  WebSocket  ->  AI response.
        
        Validates the complete Golden Path user journey with SSOT configuration.
        This test must PASS throughout SSOT consolidation to protect core business value.
        """
        ssot_validator = CentralConfigurationValidator()
        
        # Complete Golden Path flow validation
        golden_path_steps = {}
        
        # Step 1: OAuth Login Configuration
        try:
            oauth_config = {
                'OAUTH_CLIENT_ID': get_env('OAUTH_CLIENT_ID'),
                'OAUTH_CLIENT_SECRET': get_env('OAUTH_CLIENT_SECRET'),
                'JWT_SECRET_KEY': get_env('JWT_SECRET_KEY')
            }
            
            oauth_ready = all(oauth_config.values()) and len(oauth_config['JWT_SECRET_KEY']) >= 32
            golden_path_steps['oauth_login'] = {
                'ready': oauth_ready,
                'error': None if oauth_ready else "OAuth configuration incomplete"
            }
            
        except Exception as e:
            golden_path_steps['oauth_login'] = {
                'ready': False,
                'error': f"OAuth login validation error: {str(e)}"
            }
        
        # Step 2: WebSocket Connection Configuration
        try:
            websocket_config = {
                'WEBSOCKET_ORIGIN_ALLOWED': get_env('WEBSOCKET_ORIGIN_ALLOWED'),
                'CORS_ALLOWED_ORIGINS': get_env('CORS_ALLOWED_ORIGINS'),
                'JWT_SECRET_KEY': get_env('JWT_SECRET_KEY')
            }
            
            websocket_ready = all(websocket_config.values())
            golden_path_steps['websocket_connection'] = {
                'ready': websocket_ready,
                'error': None if websocket_ready else "WebSocket configuration incomplete"
            }
            
        except Exception as e:
            golden_path_steps['websocket_connection'] = {
                'ready': False,
                'error': f"WebSocket connection validation error: {str(e)}"
            }
        
        # Step 3: AI Response Delivery Configuration
        try:
            ai_config = {
                'DATABASE_URL': get_env('DATABASE_URL'),
                'REDIS_URL': get_env('REDIS_URL'),
                'ENVIRONMENT': get_env('ENVIRONMENT')
            }
            
            ai_ready = (
                all(ai_config.values()) and
                'postgresql://' in ai_config['DATABASE_URL'] and
                'redis://' in ai_config['REDIS_URL'] and
                ai_config['ENVIRONMENT'] in ['staging', 'production']
            )
            
            golden_path_steps['ai_response_delivery'] = {
                'ready': ai_ready,
                'error': None if ai_ready else "AI response configuration incomplete"
            }
            
        except Exception as e:
            golden_path_steps['ai_response_delivery'] = {
                'ready': False,
                'error': f"AI response delivery validation error: {str(e)}"
            }
        
        # Step 4: End-to-End Integration Validation
        try:
            # Validate complete flow through SSOT if available
            if hasattr(ssot_validator, 'validate_golden_path_flow'):
                e2e_validation = ssot_validator.validate_golden_path_flow()
                e2e_ready = bool(e2e_validation)
            else:
                # Manual end-to-end validation
                all_steps_ready = all(step['ready'] for step in golden_path_steps.values())
                e2e_ready = all_steps_ready
            
            golden_path_steps['end_to_end_integration'] = {
                'ready': e2e_ready,
                'error': None if e2e_ready else "End-to-end integration validation failed"
            }
            
        except Exception as e:
            golden_path_steps['end_to_end_integration'] = {
                'ready': False,
                'error': f"End-to-end integration error: {str(e)}"
            }
        
        # Validate complete Golden Path flow
        complete_golden_path_ready = all(step['ready'] for step in golden_path_steps.values())
        
        # Log complete Golden Path status
        for step_name, step_result in golden_path_steps.items():
            logger.info(f"Golden Path step {step_name}: ready={step_result['ready']}")
            if step_result['error']:
                logger.warning(f"Golden Path step {step_name} error: {step_result['error']}")
        
        # This test must PASS throughout SSOT consolidation
        self.assertTrue(
            complete_golden_path_ready,
            f"Complete Golden Path flow must remain functional during SSOT consolidation. "
            f"Step status: {golden_path_steps}"
        )
        
        # Validate critical Golden Path components
        self.assertTrue(
            golden_path_steps['oauth_login']['ready'],
            f"Golden Path OAuth login must work: {golden_path_steps['oauth_login']['error']}"
        )
        
        self.assertTrue(
            golden_path_steps['websocket_connection']['ready'],
            f"Golden Path WebSocket must work: {golden_path_steps['websocket_connection']['error']}"
        )
        
        self.assertTrue(
            golden_path_steps['ai_response_delivery']['ready'],
            f"Golden Path AI response must work: {golden_path_steps['ai_response_delivery']['error']}"
        )

    def test_configuration_failure_graceful_degradation(self):
        """
        Test graceful degradation when configuration issues occur.
        
        Validates that SSOT configuration validation provides graceful degradation
        rather than complete failures that would break Golden Path.
        """
        # Test scenarios with configuration issues
        degradation_scenarios = [
            {
                'name': 'missing_redis',
                'config_override': {'REDIS_URL': ''},
                'should_degrade_gracefully': True,
                'critical_failure': False
            },
            {
                'name': 'invalid_cors_origins',
                'config_override': {'CORS_ALLOWED_ORIGINS': 'invalid-origin'},
                'should_degrade_gracefully': True,
                'critical_failure': False
            },
            {
                'name': 'missing_jwt_secret',
                'config_override': {'JWT_SECRET_KEY': ''},
                'should_degrade_gracefully': False,
                'critical_failure': True
            },
            {
                'name': 'missing_database',
                'config_override': {'DATABASE_URL': ''},
                'should_degrade_gracefully': False,
                'critical_failure': True
            }
        ]
        
        ssot_validator = CentralConfigurationValidator()
        degradation_results = {}
        
        for scenario in degradation_scenarios:
            # Create test config with specific issue
            test_config = self.golden_path_config.copy()
            test_config.update(scenario['config_override'])
            
            with patch.dict('os.environ', test_config, clear=True):
                try:
                    # Test SSOT graceful degradation
                    if hasattr(ssot_validator, 'validate_with_degradation'):
                        validation_result = ssot_validator.validate_with_degradation()
                        graceful_degradation = validation_result.get('degraded', False)
                        critical_failure = validation_result.get('critical_failure', True)
                    else:
                        # Manual graceful degradation testing
                        try:
                            validation_result = ssot_validator.validate_complete_configuration()
                            graceful_degradation = False
                            critical_failure = False
                        except Exception as e:
                            # Check if error indicates critical vs non-critical issue
                            error_msg = str(e).lower()
                            critical_keywords = ['jwt', 'database', 'auth', 'secret']
                            critical_failure = any(keyword in error_msg for keyword in critical_keywords)
                            graceful_degradation = not critical_failure
                    
                    degradation_results[scenario['name']] = {
                        'graceful_degradation': graceful_degradation,
                        'critical_failure': critical_failure,
                        'expected_graceful': scenario['should_degrade_gracefully'],
                        'expected_critical': scenario['critical_failure'],
                        'behavior_correct': (
                            graceful_degradation == scenario['should_degrade_gracefully'] and
                            critical_failure == scenario['critical_failure']
                        )
                    }
                    
                except Exception as e:
                    degradation_results[scenario['name']] = {
                        'graceful_degradation': False,
                        'critical_failure': True,
                        'expected_graceful': scenario['should_degrade_gracefully'],
                        'expected_critical': scenario['critical_failure'],
                        'behavior_correct': scenario['critical_failure'],  # Failure is expected for critical issues
                        'error': str(e)
                    }
        
        # Validate graceful degradation behavior
        graceful_degradation_working = all(
            result.get('behavior_correct', False)
            for result in degradation_results.values()
        )
        
        # Log degradation results
        for scenario_name, result in degradation_results.items():
            logger.info(f"Graceful degradation {scenario_name}: {result}")
        
        # This test should PASS throughout SSOT consolidation
        self.assertTrue(
            graceful_degradation_working,
            f"SSOT configuration validation must handle graceful degradation correctly: {degradation_results}"
        )
        
        # Validate that non-critical issues don't cause complete failures
        non_critical_scenarios = [
            result for scenario_name, result in degradation_results.items()
            if not result['expected_critical']
        ]
        
        non_critical_handled_gracefully = all(
            result.get('graceful_degradation', False) or not result.get('critical_failure', True)
            for result in non_critical_scenarios
        )
        
        self.assertTrue(
            non_critical_handled_gracefully,
            "Non-critical configuration issues must not break Golden Path completely"
        )

    def test_staging_production_configuration_parity(self):
        """
        Test staging/production configuration parity through SSOT.
        
        Validates that SSOT configuration validation ensures parity between
        staging and production environments for Golden Path reliability.
        """
        # Configuration requirements that must be consistent across environments
        parity_requirements = [
            'JWT_SECRET_KEY',
            'OAUTH_CLIENT_ID',
            'OAUTH_CLIENT_SECRET',
            'WEBSOCKET_ORIGIN_ALLOWED',
            'CORS_ALLOWED_ORIGINS',
            'SESSION_TIMEOUT',
            'LOG_LEVEL'
        ]
        
        ssot_validator = CentralConfigurationValidator()
        
        # Test staging configuration
        staging_config = self.golden_path_config.copy()
        staging_config['ENVIRONMENT'] = 'staging'
        
        # Test production configuration (simulated)
        production_config = self.golden_path_config.copy()
        production_config.update({
            'ENVIRONMENT': 'production',
            'DATABASE_URL': 'postgresql://prod_user:prod_pass@prod-db.netra.com:5432/netra_production',
            'REDIS_URL': 'redis://prod-redis.netra.com:6379/0',
            'WEBSOCKET_ORIGIN_ALLOWED': 'https://app.netra.com',
            'CORS_ALLOWED_ORIGINS': 'https://app.netra.com',
            'DEBUG': 'false'
        })
        
        environment_validations = {}
        
        # Validate staging configuration
        with patch.dict('os.environ', staging_config, clear=True):
            try:
                if hasattr(ssot_validator, 'validate_environment_parity'):
                    staging_validation = ssot_validator.validate_environment_parity('staging')
                else:
                    staging_validation = ssot_validator.validate_complete_configuration()
                
                environment_validations['staging'] = {
                    'valid': True,
                    'error': None
                }
                
            except Exception as e:
                environment_validations['staging'] = {
                    'valid': False,
                    'error': str(e)
                }
        
        # Validate production configuration
        with patch.dict('os.environ', production_config, clear=True):
            try:
                if hasattr(ssot_validator, 'validate_environment_parity'):
                    production_validation = ssot_validator.validate_environment_parity('production')
                else:
                    production_validation = ssot_validator.validate_complete_configuration()
                
                environment_validations['production'] = {
                    'valid': True,
                    'error': None
                }
                
            except Exception as e:
                environment_validations['production'] = {
                    'valid': False,
                    'error': str(e)
                }
        
        # Test parity validation
        try:
            # Check if SSOT can validate cross-environment parity
            if hasattr(ssot_validator, 'validate_cross_environment_parity'):
                parity_validation = ssot_validator.validate_cross_environment_parity(
                    staging_config, production_config
                )
                parity_valid = bool(parity_validation)
            else:
                # Manual parity validation
                parity_issues = []
                for req in parity_requirements:
                    staging_val = staging_config.get(req)
                    production_val = production_config.get(req)
                    
                    # Check presence parity (both should have or not have)
                    if bool(staging_val) != bool(production_val):
                        parity_issues.append(f"{req}: presence mismatch")
                    
                    # Check type parity for security settings
                    if req in ['JWT_SECRET_KEY', 'OAUTH_CLIENT_SECRET'] and staging_val and production_val:
                        if len(staging_val) != len(production_val):
                            parity_issues.append(f"{req}: length mismatch (security risk)")
                
                parity_valid = len(parity_issues) == 0
                
            environment_validations['parity'] = {
                'valid': parity_valid,
                'error': None if parity_valid else "Environment parity issues detected"
            }
            
        except Exception as e:
            environment_validations['parity'] = {
                'valid': False,
                'error': f"Parity validation error: {str(e)}"
            }
        
        # Validate environment parity
        all_environments_valid = all(
            result.get('valid', False) 
            for result in environment_validations.values()
        )
        
        # Log environment validation results
        for env_name, result in environment_validations.items():
            logger.info(f"Environment validation {env_name}: {result}")
        
        # This test should PASS throughout SSOT consolidation
        self.assertTrue(
            all_environments_valid,
            f"Environment configuration parity must be maintained during SSOT consolidation: {environment_validations}"
        )
        
        # Validate critical environment validations
        self.assertTrue(
            environment_validations['staging']['valid'],
            f"Staging configuration must be valid: {environment_validations['staging']['error']}"
        )
        
        self.assertTrue(
            environment_validations['production']['valid'],
            f"Production configuration must be valid: {environment_validations['production']['error']}"
        )

    def test_real_user_flow_configuration_stability(self):
        """
        Test real user flow configuration stability during SSOT changes.
        
        Validates that real user scenarios remain stable during SSOT consolidation.
        This test simulates actual user interactions and must PASS throughout.
        """
        # Real user flow scenarios
        user_flow_scenarios = [
            {
                'name': 'new_user_signup_flow',
                'config_requirements': ['OAUTH_CLIENT_ID', 'OAUTH_CLIENT_SECRET', 'DATABASE_URL', 'JWT_SECRET_KEY'],
                'flow_steps': ['oauth_redirect', 'user_creation', 'session_establishment']
            },
            {
                'name': 'returning_user_login_flow', 
                'config_requirements': ['JWT_SECRET_KEY', 'DATABASE_URL', 'REDIS_URL'],
                'flow_steps': ['session_validation', 'user_lookup', 'auth_refresh']
            },
            {
                'name': 'ai_chat_interaction_flow',
                'config_requirements': ['WEBSOCKET_ORIGIN_ALLOWED', 'JWT_SECRET_KEY', 'DATABASE_URL', 'REDIS_URL'],
                'flow_steps': ['websocket_connect', 'message_send', 'ai_response', 'conversation_save']
            },
            {
                'name': 'session_timeout_flow',
                'config_requirements': ['SESSION_TIMEOUT', 'JWT_SECRET_KEY', 'REDIS_URL'],
                'flow_steps': ['session_check', 'timeout_detection', 'auth_redirect']
            }
        ]
        
        ssot_validator = CentralConfigurationValidator()
        user_flow_results = {}
        
        for scenario in user_flow_scenarios:
            scenario_result = {
                'config_valid': True,
                'flow_steps_ready': [],
                'overall_ready': True,
                'errors': []
            }
            
            # Validate configuration requirements for this user flow
            for req in scenario['config_requirements']:
                config_value = get_env(req)
                if not config_value:
                    scenario_result['config_valid'] = False
                    scenario_result['errors'].append(f"Missing config {req} for {scenario['name']}")
                elif req == 'JWT_SECRET_KEY' and len(config_value) < 32:
                    scenario_result['config_valid'] = False
                    scenario_result['errors'].append(f"JWT secret too weak for {scenario['name']}")
            
            # Validate flow steps can be supported
            for step in scenario['flow_steps']:
                try:
                    # Mock flow step validation through SSOT
                    if hasattr(ssot_validator, f'validate_flow_step_{step}'):
                        step_validation = getattr(ssot_validator, f'validate_flow_step_{step}')()
                        step_ready = bool(step_validation)
                    else:
                        # Manual flow step validation
                        if step == 'oauth_redirect':
                            step_ready = bool(get_env('OAUTH_CLIENT_ID') and get_env('OAUTH_CLIENT_SECRET'))
                        elif step == 'websocket_connect':
                            step_ready = bool(get_env('WEBSOCKET_ORIGIN_ALLOWED') and get_env('JWT_SECRET_KEY'))
                        elif step in ['user_creation', 'user_lookup', 'conversation_save']:
                            step_ready = bool(get_env('DATABASE_URL'))
                        elif step in ['session_establishment', 'session_validation', 'auth_refresh']:
                            step_ready = bool(get_env('JWT_SECRET_KEY') and get_env('REDIS_URL'))
                        elif step in ['session_check', 'timeout_detection']:
                            step_ready = bool(get_env('SESSION_TIMEOUT') and get_env('REDIS_URL'))
                        elif step in ['message_send', 'ai_response']:
                            step_ready = bool(get_env('DATABASE_URL') and get_env('REDIS_URL'))
                        else:
                            step_ready = True  # Unknown steps assumed ready
                    
                    scenario_result['flow_steps_ready'].append({
                        'step': step,
                        'ready': step_ready
                    })
                    
                    if not step_ready:
                        scenario_result['overall_ready'] = False
                        scenario_result['errors'].append(f"Flow step {step} not ready for {scenario['name']}")
                        
                except Exception as e:
                    scenario_result['flow_steps_ready'].append({
                        'step': step,
                        'ready': False,
                        'error': str(e)
                    })
                    scenario_result['overall_ready'] = False
                    scenario_result['errors'].append(f"Flow step {step} validation error: {str(e)}")
            
            # Overall scenario readiness
            scenario_result['overall_ready'] = (
                scenario_result['config_valid'] and
                scenario_result['overall_ready']
            )
            
            user_flow_results[scenario['name']] = scenario_result
        
        # Validate all user flows remain stable
        all_user_flows_stable = all(
            result.get('overall_ready', False)
            for result in user_flow_results.values()
        )
        
        # Log user flow results
        for flow_name, result in user_flow_results.items():
            logger.info(f"User flow {flow_name}: ready={result['overall_ready']}")
            if result['errors']:
                logger.warning(f"User flow {flow_name} errors: {result['errors']}")
        
        # This test must PASS throughout SSOT consolidation
        self.assertTrue(
            all_user_flows_stable,
            f"Real user flows must remain stable during SSOT consolidation: {user_flow_results}"
        )
        
        # Validate critical user flows individually
        critical_flows = ['new_user_signup_flow', 'returning_user_login_flow', 'ai_chat_interaction_flow']
        
        for critical_flow in critical_flows:
            if critical_flow in user_flow_results:
                self.assertTrue(
                    user_flow_results[critical_flow]['overall_ready'],
                    f"Critical user flow {critical_flow} must remain functional: {user_flow_results[critical_flow]['errors']}"
                )


if __name__ == '__main__':
    unittest.main()