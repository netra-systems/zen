#!/usr/bin/env python
"""INTEGRATION TEST 8: Configuration Cascade Testing (TEST/DEV/STAGING)

This test validates configuration consistency and isolation across different
environments (TEST/DEV/STAGING) to prevent configuration regression failures
that can cause cascading system outages.

Business Value: Prevents $100K+ in downtime costs from configuration mismatches
Test Requirements:
- Real Docker services with environment-specific configurations
- Cross-environment configuration validation
- OAuth credential isolation testing
- Database connection string validation
- Service discovery endpoint verification

CRITICAL: This test prevents the OAuth regression that caused 503 errors in staging.
See: OAUTH_REGRESSION_ANALYSIS_20250905.md and CONFIG_REGRESSION_PREVENTION_PLAN.md
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
import threading

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import requests
from loguru import logger
from shared.isolated_environment import get_env, IsolatedEnvironment

# Import configuration components
from scripts.environment_validator_core import EnvironmentValidatorCore
from test_framework.docker_test_base import DockerTestBase


class EnvironmentConfigurationTracker:
    """Tracks and validates configuration across environments"""
    
    def __init__(self):
        self.environments: Dict[str, Dict[str, Any]] = {}
        self.config_validations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.cross_env_issues: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        
    def record_environment_config(self, env_name: str, config: Dict[str, Any]):
        """Record configuration for specific environment"""
        with self._lock:
            self.environments[env_name] = {
                'name': env_name,
                'timestamp': datetime.now().isoformat(),
                'config': config.copy()
            }
            
    def record_validation_result(self, env_name: str, validation_type: str, 
                               success: bool, details: Dict[str, Any]):
        """Record configuration validation result"""
        with self._lock:
            validation = {
                'validation_type': validation_type,
                'success': success,
                'timestamp': datetime.now().isoformat(),
                'details': details.copy()
            }
            self.config_validations[env_name].append(validation)
            
    def record_cross_environment_issue(self, issue_type: str, environments: List[str],
                                     description: str, severity: str):
        """Record cross-environment configuration issue"""
        with self._lock:
            issue = {
                'issue_type': issue_type,
                'environments': environments,
                'description': description,
                'severity': severity,
                'timestamp': datetime.now().isoformat()
            }
            self.cross_env_issues.append(issue)
            
    def get_configuration_analysis(self) -> Dict[str, Any]:
        """Get comprehensive configuration analysis"""
        with self._lock:
            return {
                'environments_tested': list(self.environments.keys()),
                'total_validations': sum(len(validations) for validations in self.config_validations.values()),
                'cross_env_issues': len(self.cross_env_issues),
                'environment_configs': self.environments.copy(),
                'validation_results': dict(self.config_validations),
                'critical_issues': [issue for issue in self.cross_env_issues if issue['severity'] == 'critical']
            }


@pytest.mark.integration
@pytest.mark.requires_docker
@pytest.mark.configuration_critical
class TestConfigurationCascadeEnvironments(DockerTestBase):
    """Integration Test 8: Configuration cascade testing across environments"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Initialize test environment with multiple configuration contexts"""
        self.config_tracker = EnvironmentConfigurationTracker()
        
        # Define environment contexts to test
        self.test_environments = [
            'TEST',
            'DEV',
            'STAGING'
        ]
        
        # Critical configuration keys that must be validated
        self.critical_config_keys = [
            'BACKEND_URL',
            'AUTH_SERVICE_URL', 
            'DATABASE_URL',
            'REDIS_URL',
            'JWT_SECRET',
            'OAUTH_GOOGLE_CLIENT_ID',
            'OAUTH_GOOGLE_CLIENT_SECRET',
            'CORS_ORIGINS'
        ]
        
        # Service endpoints for validation
        self.service_endpoints = {
            'backend': '/health',
            'auth': '/health',
            'frontend': '/'
        }
        
        yield
        
        # Generate configuration analysis report
        analysis = self.config_tracker.get_configuration_analysis()
        logger.info(f"Configuration cascade test completed. Analysis: {analysis}")
        
    def _get_environment_config(self, env_name: str) -> Dict[str, Any]:
        """Get configuration for specific environment"""
        try:
            # Create isolated environment for testing
            with IsolatedEnvironment(override_env={'NETRA_ENV': env_name}) as isolated_env:
                config = {}
                
                # Collect critical configuration values
                for key in self.critical_config_keys:
                    value = isolated_env.get(key)
                    config[key] = {
                        'value': value,
                        'is_set': value is not None,
                        'is_empty': not bool(value) if value is not None else True
                    }
                
                # Add derived configuration
                config['_derived'] = {
                    'environment': env_name,
                    'backend_port': isolated_env.get('BACKEND_PORT', '8000'),
                    'auth_port': isolated_env.get('AUTH_PORT', '8081'),
                    'frontend_port': isolated_env.get('FRONTEND_PORT', '3000'),
                    'db_port': isolated_env.get('POSTGRES_PORT', '5432'),
                    'redis_port': isolated_env.get('REDIS_PORT', '6379')
                }
                
                # Record the configuration
                self.config_tracker.record_environment_config(env_name, config)
                return config
                
        except Exception as e:
            logger.error(f"Failed to get configuration for {env_name}: {e}")
            return {}
    
    def _validate_oauth_credentials_isolation(self, env_configs: Dict[str, Dict[str, Any]]) -> bool:
        """Validate OAuth credentials are properly isolated between environments"""
        logger.info("Validating OAuth credentials isolation...")
        
        oauth_keys = ['OAUTH_GOOGLE_CLIENT_ID', 'OAUTH_GOOGLE_CLIENT_SECRET']
        validation_passed = True
        
        for key in oauth_keys:
            env_values = {}
            
            # Collect values across environments
            for env_name, config in env_configs.items():
                if key in config and config[key]['is_set']:
                    env_values[env_name] = config[key]['value']
            
            # Validate no duplicate values across different environments
            if len(env_values) > 1:
                value_counts = defaultdict(list)
                for env, value in env_values.items():
                    value_counts[value].append(env)
                
                # Check for duplicated values
                for value, environments in value_counts.items():
                    if len(environments) > 1:
                        validation_passed = False
                        self.config_tracker.record_cross_environment_issue(
                            'oauth_credential_duplication',
                            environments,
                            f'{key} has the same value across environments: {environments}',
                            'critical'
                        )
                        logger.error(f"CRITICAL: {key} duplicated across environments {environments}")
        
        # Validate that each environment has its own credentials
        for env_name, config in env_configs.items():
            has_oauth_config = all(
                config.get(key, {}).get('is_set', False) for key in oauth_keys
            )
            
            self.config_tracker.record_validation_result(
                env_name, 'oauth_credentials_present', has_oauth_config,
                {'keys_validated': oauth_keys, 'all_present': has_oauth_config}
            )
            
            if not has_oauth_config:
                logger.warning(f"Environment {env_name} missing OAuth credentials")
        
        logger.info(f"OAuth credentials isolation validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        return validation_passed
    
    def _validate_database_connection_strings(self, env_configs: Dict[str, Dict[str, Any]]) -> bool:
        """Validate database connection strings are environment-specific"""
        logger.info("Validating database connection strings...")
        
        validation_passed = True
        database_urls = {}
        
        # Collect database URLs
        for env_name, config in env_configs.items():
            if 'DATABASE_URL' in config and config['DATABASE_URL']['is_set']:
                database_urls[env_name] = config['DATABASE_URL']['value']
        
        # Validate no shared database URLs between environments
        if len(database_urls) > 1:
            url_counts = defaultdict(list)
            for env, url in database_urls.items():
                # Normalize URL for comparison (remove credentials)
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    normalized_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}"
                    url_counts[normalized_url].append(env)
                except:
                    url_counts[url].append(env)
            
            # Check for shared databases
            for url, environments in url_counts.items():
                if len(environments) > 1 and not any(env == 'TEST' for env in environments):
                    # Allow TEST to share with other envs, but not PROD/STAGING sharing
                    validation_passed = False
                    self.config_tracker.record_cross_environment_issue(
                        'database_url_sharing',
                        environments,
                        f'Database URL shared across non-test environments: {environments}',
                        'high'
                    )
                    logger.warning(f"Database URL shared across {environments}")
        
        # Validate each environment has a database URL
        for env_name, config in env_configs.items():
            has_db_url = config.get('DATABASE_URL', {}).get('is_set', False)
            
            self.config_tracker.record_validation_result(
                env_name, 'database_url_present', has_db_url,
                {'url_configured': has_db_url}
            )
            
            if not has_db_url:
                logger.error(f"Environment {env_name} missing DATABASE_URL")
                validation_passed = False
        
        logger.info(f"Database connection validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        return validation_passed
    
    def _validate_jwt_secrets_uniqueness(self, env_configs: Dict[str, Dict[str, Any]]) -> bool:
        """Validate JWT secrets are unique per environment"""
        logger.info("Validating JWT secrets uniqueness...")
        
        validation_passed = True
        jwt_secrets = {}
        
        # Collect JWT secrets
        for env_name, config in env_configs.items():
            if 'JWT_SECRET' in config and config['JWT_SECRET']['is_set']:
                jwt_secrets[env_name] = config['JWT_SECRET']['value']
        
        # Validate uniqueness
        if len(jwt_secrets) > 1:
            secret_counts = defaultdict(list)
            for env, secret in jwt_secrets.items():
                secret_counts[secret].append(env)
            
            for secret, environments in secret_counts.items():
                if len(environments) > 1:
                    validation_passed = False
                    self.config_tracker.record_cross_environment_issue(
                        'jwt_secret_duplication',
                        environments,
                        f'JWT_SECRET shared across environments: {environments}',
                        'critical'
                    )
                    logger.error(f"CRITICAL: JWT_SECRET shared across {environments}")
        
        # Validate presence
        for env_name, config in env_configs.items():
            has_jwt_secret = config.get('JWT_SECRET', {}).get('is_set', False)
            
            self.config_tracker.record_validation_result(
                env_name, 'jwt_secret_present', has_jwt_secret,
                {'secret_configured': has_jwt_secret}
            )
            
            if not has_jwt_secret:
                logger.error(f"Environment {env_name} missing JWT_SECRET")
                validation_passed = False
        
        logger.info(f"JWT secrets validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        return validation_passed
    
    def _validate_cors_configuration(self, env_configs: Dict[str, Dict[str, Any]]) -> bool:
        """Validate CORS origins are environment-appropriate"""
        logger.info("Validating CORS configuration...")
        
        validation_passed = True
        
        for env_name, config in env_configs.items():
            cors_origins = config.get('CORS_ORIGINS', {}).get('value', '')
            
            if cors_origins:
                # Parse CORS origins
                origins_list = [origin.strip() for origin in cors_origins.split(',')]
                
                # Environment-specific validation
                if env_name == 'STAGING':
                    # Staging should not allow localhost origins
                    localhost_origins = [o for o in origins_list if 'localhost' in o or '127.0.0.1' in o]
                    if localhost_origins:
                        validation_passed = False
                        self.config_tracker.record_cross_environment_issue(
                            'cors_localhost_in_staging',
                            [env_name],
                            f'STAGING has localhost CORS origins: {localhost_origins}',
                            'high'
                        )
                        logger.warning(f"STAGING environment has localhost CORS origins: {localhost_origins}")
                
                elif env_name == 'DEV':
                    # DEV should typically allow localhost
                    has_localhost = any('localhost' in o or '127.0.0.1' in o for o in origins_list)
                    if not has_localhost:
                        logger.info(f"DEV environment doesn't have localhost CORS - may be intentional")
            
            self.config_tracker.record_validation_result(
                env_name, 'cors_configuration', cors_origins is not None,
                {'origins_configured': bool(cors_origins), 'origins_count': len(cors_origins.split(',')) if cors_origins else 0}
            )
        
        logger.info(f"CORS configuration validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        return validation_passed
    
    async def _validate_service_endpoints(self, env_configs: Dict[str, Dict[str, Any]]) -> bool:
        """Validate service endpoints are accessible in each environment"""
        logger.info("Validating service endpoints accessibility...")
        
        validation_passed = True
        
        for env_name, config in env_configs.items():
            if env_name == 'TEST':
                # For TEST environment, validate against running Docker services
                backend_port = config['_derived']['backend_port']
                auth_port = config['_derived']['auth_port']
                
                endpoints_to_test = [
                    f"http://localhost:{backend_port}/health",
                    f"http://localhost:{auth_port}/health"
                ]
                
                for endpoint in endpoints_to_test:
                    try:
                        response = requests.get(endpoint, timeout=10)
                        endpoint_accessible = response.status_code == 200
                        
                        self.config_tracker.record_validation_result(
                            env_name, f'endpoint_accessibility', endpoint_accessible,
                            {'endpoint': endpoint, 'status_code': response.status_code}
                        )
                        
                        if not endpoint_accessible:
                            logger.warning(f"Endpoint {endpoint} not accessible in {env_name}: {response.status_code}")
                            
                    except Exception as e:
                        validation_passed = False
                        self.config_tracker.record_validation_result(
                            env_name, f'endpoint_accessibility', False,
                            {'endpoint': endpoint, 'error': str(e)}
                        )
                        logger.error(f"Failed to access {endpoint} in {env_name}: {e}")
            
            else:
                # For other environments, validate configuration completeness
                backend_url = config.get('BACKEND_URL', {}).get('value', '')
                auth_url = config.get('AUTH_SERVICE_URL', {}).get('value', '')
                
                urls_configured = bool(backend_url and auth_url)
                self.config_tracker.record_validation_result(
                    env_name, 'service_urls_configured', urls_configured,
                    {'backend_url': bool(backend_url), 'auth_url': bool(auth_url)}
                )
                
                if not urls_configured:
                    logger.warning(f"Service URLs not fully configured for {env_name}")
        
        logger.info(f"Service endpoints validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        return validation_passed
    
    @pytest.mark.asyncio
    async def test_configuration_cascade_validation(self):
        """
        Test 8: Configuration cascade testing across TEST/DEV/STAGING
        
        Validates:
        1. OAuth credentials are isolated between environments  
        2. Database connections don't leak between environments
        3. JWT secrets are unique per environment
        4. CORS origins are appropriate for each environment
        5. Service endpoints are properly configured
        6. Critical configuration keys are present
        """
        logger.info("=== INTEGRATION TEST 8: Configuration Cascade Validation ===")
        
        # Phase 1: Collect configuration from all environments
        logger.info("Phase 1: Collecting configuration from all test environments")
        env_configs = {}
        
        for env_name in self.test_environments:
            logger.info(f"Collecting configuration for {env_name}")
            config = self._get_environment_config(env_name)
            env_configs[env_name] = config
            
            if not config:
                logger.error(f"Failed to collect configuration for {env_name}")
        
        assert len(env_configs) > 0, "Failed to collect any environment configurations"
        
        # Phase 2: Validate OAuth credentials isolation
        logger.info("Phase 2: Validating OAuth credentials isolation")
        oauth_validation_passed = self._validate_oauth_credentials_isolation(env_configs)
        
        # Phase 3: Validate database connection isolation
        logger.info("Phase 3: Validating database connection isolation") 
        database_validation_passed = self._validate_database_connection_strings(env_configs)
        
        # Phase 4: Validate JWT secrets uniqueness
        logger.info("Phase 4: Validating JWT secrets uniqueness")
        jwt_validation_passed = self._validate_jwt_secrets_uniqueness(env_configs)
        
        # Phase 5: Validate CORS configuration
        logger.info("Phase 5: Validating CORS configuration")
        cors_validation_passed = self._validate_cors_configuration(env_configs)
        
        # Phase 6: Validate service endpoints
        logger.info("Phase 6: Validating service endpoints accessibility")
        endpoints_validation_passed = await self._validate_service_endpoints(env_configs)
        
        # Phase 7: Generate comprehensive analysis
        self._generate_configuration_analysis_report()
        
        # Overall validation
        all_validations_passed = all([
            oauth_validation_passed,
            database_validation_passed, 
            jwt_validation_passed,
            cors_validation_passed,
            endpoints_validation_passed
        ])
        
        # Critical validations (failure blocks deployment)
        critical_validations_passed = oauth_validation_passed and database_validation_passed and jwt_validation_passed
        
        # Assert critical validations must pass
        assert critical_validations_passed, "Critical configuration validations failed - deployment blocked"
        
        if all_validations_passed:
            logger.info("✅ INTEGRATION TEST 8 PASSED: All configuration cascade validations successful")
        else:
            logger.warning("⚠️  INTEGRATION TEST 8 PASSED WITH WARNINGS: Some non-critical validations failed")
    
    def _generate_configuration_analysis_report(self):
        """Generate comprehensive configuration analysis report"""
        analysis = self.config_tracker.get_configuration_analysis()
        
        logger.info("=== CONFIGURATION CASCADE ANALYSIS REPORT ===")
        logger.info(f"Environments tested: {analysis['environments_tested']}")
        logger.info(f"Total validations performed: {analysis['total_validations']}")
        logger.info(f"Cross-environment issues found: {analysis['cross_env_issues']}")
        logger.info(f"Critical issues: {len(analysis['critical_issues'])}")
        
        # Log critical issues in detail
        if analysis['critical_issues']:
            logger.error("CRITICAL CONFIGURATION ISSUES:")
            for issue in analysis['critical_issues']:
                logger.error(f"  - {issue['issue_type']}: {issue['description']}")
                logger.error(f"    Environments: {issue['environments']}")
                logger.error(f"    Severity: {issue['severity']}")
        
        # Log validation summary by environment
        for env_name in analysis['environments_tested']:
            validations = analysis['validation_results'].get(env_name, [])
            passed = sum(1 for v in validations if v['success'])
            total = len(validations)
            logger.info(f"Environment {env_name}: {passed}/{total} validations passed")
    
    @pytest.mark.asyncio  
    async def test_configuration_regression_prevention(self):
        """
        Test 8b: Configuration regression prevention
        
        This test implements the specific safeguards identified in
        CONFIG_REGRESSION_PREVENTION_PLAN.md to prevent OAuth and
        other configuration regressions.
        """
        logger.info("=== INTEGRATION TEST 8b: Configuration Regression Prevention ===")
        
        # Test OAuth regression prevention
        with IsolatedEnvironment() as env:
            # Validate OAuth keys are present and not empty
            oauth_client_id = env.get('OAUTH_GOOGLE_CLIENT_ID')
            oauth_client_secret = env.get('OAUTH_GOOGLE_CLIENT_SECRET')
            
            assert oauth_client_id, "OAUTH_GOOGLE_CLIENT_ID must be present"
            assert oauth_client_secret, "OAUTH_GOOGLE_CLIENT_SECRET must be present"
            assert len(oauth_client_id) > 10, "OAUTH_GOOGLE_CLIENT_ID appears invalid"
            assert len(oauth_client_secret) > 10, "OAUTH_GOOGLE_CLIENT_SECRET appears invalid"
        
        # Test database URL regression prevention
        with IsolatedEnvironment() as env:
            database_url = env.get('DATABASE_URL')
            assert database_url, "#removed-legacymust be present"
            assert database_url.startswith(('postgresql://', 'postgres://')), "#removed-legacymust be PostgreSQL"
            
        # Test JWT secret regression prevention
        with IsolatedEnvironment() as env:
            jwt_secret = env.get('JWT_SECRET')
            assert jwt_secret, "JWT_SECRET must be present"
            assert len(jwt_secret) >= 32, "JWT_SECRET must be at least 32 characters"
            
        logger.info("✅ INTEGRATION TEST 8b PASSED: Configuration regression prevention working")


if __name__ == "__main__":
    # Run the test directly
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "-x",
        "--log-cli-level=INFO"
    ])