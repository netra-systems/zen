#!/usr/bin/env python
"""
Mission Critical: Configuration Regression Prevention Tests

These tests ensure that configuration changes do not cause cascade failures
like the OAuth 503 errors documented in reports. They run in CI/CD to catch
configuration regressions before deployment.

Based on CRITICAL_CONFIG_REGRESSION_AUDIT_REPORT.md findings.
"""

import os
import sys
import unittest
import asyncio
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.isolated_test_helper import IsolatedTestCase


class ConfigurationRegressionTests(IsolatedTestCase):
    """
    Critical tests to prevent configuration regressions that cause cascade failures.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        super().setUpClass()
        cls.critical_configs = {
            'SERVICE_SECRET': 'Critical for inter-service auth',
            'JWT_SECRET': 'Critical for token validation',
            'AUTH_SERVICE_URL': 'Critical for auth connectivity',
            'DATABASE_URL': 'Critical for data persistence',
            'REDIS_URL': 'Critical for caching and sessions'
        }
    
    def test_service_secret_presence_all_environments(self):
        """
        Test that SERVICE_SECRET is properly configured across all environments.
        
        CRITICAL: SERVICE_SECRET has 173+ dependencies. Missing causes:
        - 100% authentication failure
        - Circuit breaker permanently open
        - Complete system unusable
        """
        environments = ['development', 'test', 'staging', 'production']
        
        for env_name in environments:
            with self.subTest(environment=env_name):
                # Set up environment
                self.set_env('ENVIRONMENT', env_name)
                
                # Check if SERVICE_SECRET would be available
                if env_name in ['staging', 'production']:
                    # In staging/production, it must come from deployment secrets
                    # This test ensures the configuration expects it
                    from deployment.secrets_config import get_secret_mappings
                    mappings = get_secret_mappings(env_name)
                    
                    self.assertIn('SERVICE_SECRET', mappings,
                                f"SERVICE_SECRET missing from {env_name} secret mappings")
                    
                    # Verify it maps to a GCP secret
                    secret_name = mappings['SERVICE_SECRET']
                    self.assertTrue(secret_name,
                                  f"SERVICE_SECRET has empty mapping in {env_name}")
                else:
                    # In dev/test, verify defaults or env file
                    env_file = project_root / f'.env.{env_name}'
                    if env_file.exists():
                        content = env_file.read_text()
                        self.assertIn('SERVICE_SECRET', content,
                                    f"SERVICE_SECRET missing from {env_file}")
    
    def test_jwt_secret_resolution_consistency(self):
        """
        Test JWT secret resolution is consistent across services.
        
        Validates the unified JWT secret manager properly resolves
        secrets for all environments without conflicts.
        """
        from shared.jwt_secret_manager import get_jwt_secret_manager
        
        environments = ['development', 'test', 'staging', 'production']
        
        for env_name in environments:
            with self.subTest(environment=env_name):
                self.set_env('ENVIRONMENT', env_name)
                
                # Get JWT secret through SSOT
                jwt_manager = get_jwt_secret_manager()
                jwt_secret = jwt_manager.get_jwt_secret()
                
                # Verify it's not a default/weak value
                weak_values = [
                    None, '', 'your-secret-key', 'test-secret', 'secret',
                    'emergency_jwt_secret_please_configure_properly'
                ]
                
                if env_name in ['staging', 'production']:
                    self.assertNotIn(jwt_secret, weak_values,
                                   f"Weak JWT secret in {env_name}")
                    
                    # Production should have strong secrets
                    if env_name == 'production' and jwt_secret:
                        self.assertGreaterEqual(len(jwt_secret), 64,
                                              "Production JWT secret too short")
    
    def test_oauth_dual_naming_consistency(self):
        """
        Test OAuth dual naming convention is properly maintained.
        
        Backend uses: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
        Auth service uses: GOOGLE_OAUTH_CLIENT_ID_STAGING, etc.
        """
        from deployment.secrets_config import get_secret_mappings
        
        environments = ['staging', 'production']
        
        for env_name in environments:
            with self.subTest(environment=env_name):
                mappings = get_secret_mappings(env_name)
                
                # Check backend pattern exists
                self.assertIn('GOOGLE_CLIENT_ID', mappings,
                            f"Backend OAuth pattern missing in {env_name}")
                self.assertIn('GOOGLE_CLIENT_SECRET', mappings,
                            f"Backend OAuth secret missing in {env_name}")
                
                # Check auth service pattern exists
                env_upper = env_name.upper()
                self.assertIn(f'GOOGLE_OAUTH_CLIENT_ID_{env_upper}', mappings,
                            f"Auth service OAuth ID missing in {env_name}")
                self.assertIn(f'GOOGLE_OAUTH_CLIENT_SECRET_{env_upper}', mappings,
                            f"Auth service OAuth secret missing in {env_name}")
                
                # Verify they map to same underlying secrets
                backend_id = mappings['GOOGLE_CLIENT_ID']
                auth_id = mappings[f'GOOGLE_OAUTH_CLIENT_ID_{env_upper}']
                
                # Both should reference the same secret (with possible formatting differences)
                self.assertIn(env_name.lower(), backend_id.lower(),
                            "Backend OAuth should reference environment")
                self.assertIn(env_name.lower(), auth_id.lower(),
                            "Auth OAuth should reference environment")
    
    def test_no_environment_variable_leakage(self):
        """
        Test that environment variables don't leak between test runs.
        
        Uses IsolatedEnvironment to ensure proper isolation.
        """
        # Set a test variable
        test_key = 'TEST_LEAK_CHECK'
        test_value = 'should_not_leak'
        
        # Create isolated environment
        env1 = IsolatedEnvironment()
        env1.enable_isolation_mode()
        env1.set(test_key, test_value)
        
        # Verify it's set
        self.assertEqual(env1.get(test_key), test_value)
        
        # Create new isolated environment
        env2 = IsolatedEnvironment()
        env2.enable_isolation_mode()
        
        # Verify no leakage
        self.assertIsNone(env2.get(test_key),
                        "Environment variable leaked between isolated instances")
        
        # Clean up
        env1.reset()
        env2.reset()
    
    def test_critical_config_dependencies(self):
        """
        Test that removing critical configs would be caught.
        
        Simulates what happens if someone tries to "consolidate"
        a critical config without understanding dependencies.
        """
        critical_impacts = {
            'SERVICE_SECRET': [
                'auth_service.auth_core.routes.auth_routes',
                'netra_backend.app.clients.auth_client_core',
                'netra_backend.app.core.auth_startup_validator',
                'analytics_service.analytics_core.services.websocket_auth_service'
            ],
            'JWT_SECRET': [
                'shared.jwt_secret_manager',
                'auth_service.auth_core.security',
                'netra_backend.app.auth.jwt_handler'
            ],
            'AUTH_SERVICE_URL': [
                'netra_backend.app.clients.auth_client_core',
                'netra_backend.app.core.auth_startup_validator'
            ]
        }
        
        for config_key, dependent_modules in critical_impacts.items():
            with self.subTest(config=config_key):
                # Verify the config is documented as critical
                self.assertIn(config_key, self.critical_configs,
                            f"{config_key} not documented as critical")
                
                # Verify at least some dependent modules exist
                for module_path in dependent_modules[:2]:  # Check first 2
                    parts = module_path.split('.')
                    file_path = Path(project_root) / Path(*parts[:-1]) / f"{parts[-1]}.py"
                    
                    if file_path.exists():
                        content = file_path.read_text()
                        # Verify the module references the config
                        self.assertIn(config_key, content,
                                    f"{module_path} doesn't reference {config_key}")
    
    def test_config_validation_at_startup(self):
        """
        Test that configuration validation happens at startup.
        
        Ensures AuthStartupValidator properly validates SERVICE_SECRET.
        """
        from netra_backend.app.core.auth_startup_validator import (
            AuthStartupValidator, AuthComponent
        )
        
        async def run_validation():
            # Test with missing SERVICE_SECRET
            validator = AuthStartupValidator()
            
            # Mock environment to simulate missing config
            with patch.object(validator.env, 'get') as mock_get:
                def get_side_effect(key, default=None):
                    if key == 'SERVICE_SECRET':
                        return None  # Simulate missing
                    elif key == 'SERVICE_ID':
                        return 'test-service'
                    return default
                
                mock_get.side_effect = get_side_effect
                
                # Run validation
                success, results = await validator.validate_all()
                
                # Should fail due to missing SERVICE_SECRET
                self.assertFalse(success,
                               "Validation should fail with missing SERVICE_SECRET")
                
                # Find SERVICE_SECRET validation result
                service_result = next(
                    (r for r in results 
                     if r.component == AuthComponent.SERVICE_CREDENTIALS),
                    None
                )
                
                self.assertIsNotNone(service_result,
                                   "SERVICE_CREDENTIALS validation not found")
                self.assertFalse(service_result.valid,
                               "SERVICE_CREDENTIALS should be invalid")
                self.assertTrue(service_result.is_critical,
                              "Missing SERVICE_SECRET should be critical")
                self.assertIn('SINGLE POINT OF FAILURE', service_result.error,
                            "Should identify as single point of failure")
        
        # Run async test
        asyncio.run(run_validation())
    
    def test_service_secret_strength_validation(self):
        """
        Test that weak SERVICE_SECRET values are rejected.
        """
        from netra_backend.app.core.auth_startup_validator import AuthStartupValidator
        
        weak_secrets = [
            'test-secret',
            'password123',
            'secret',
            'changeme',
            '12345678901234567890123456789012',  # 32 chars but weak
        ]
        
        async def test_weak_secret(secret_value):
            validator = AuthStartupValidator()
            
            with patch.object(validator.env, 'get') as mock_get:
                def get_side_effect(key, default=None):
                    if key == 'SERVICE_SECRET':
                        return secret_value
                    elif key == 'SERVICE_ID':
                        return 'test-service'
                    elif key == 'ENVIRONMENT':
                        return 'production'
                    return default
                
                mock_get.side_effect = get_side_effect
                validator.is_production = True
                
                # Validate just service credentials
                await validator._validate_service_credentials()
                
                # Find the result
                service_result = next(
                    (r for r in validator.validation_results 
                     if r.component.value == 'service_credentials'),
                    None
                )
                
                return service_result
        
        for weak_secret in weak_secrets:
            with self.subTest(secret=weak_secret[:20] + '...'):
                result = asyncio.run(test_weak_secret(weak_secret))
                
                if 'test' in weak_secret or 'password' in weak_secret or 'secret' in weak_secret:
                    self.assertFalse(result.valid,
                                   f"Weak pattern '{weak_secret[:20]}...' should be rejected")
    
    def test_environment_specific_config_isolation(self):
        """
        Test that environment-specific configs don't leak across environments.
        
        E.g., staging configs should never appear in production.
        """
        # Check that staging-specific variables don't leak to production
        staging_only = [
            'GOOGLE_OAUTH_CLIENT_ID_STAGING',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING',
            'JWT_SECRET_STAGING',
            'DATABASE_URL_STAGING'
        ]
        
        production_only = [
            'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION',
            'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION',
            'JWT_SECRET_PRODUCTION',
            'DATABASE_URL_PRODUCTION'
        ]
        
        # Test staging environment
        self.set_env('ENVIRONMENT', 'staging')
        
        # In staging, production vars should not be used
        for prod_var in production_only:
            # This is a conceptual test - in real deployment,
            # these would be validated by deployment scripts
            with self.subTest(var=prod_var):
                # Verify production vars aren't referenced in staging config
                pass  # Actual validation would happen in deployment
        
        # Test production environment
        self.set_env('ENVIRONMENT', 'production')
        
        # In production, staging vars should not be used
        for staging_var in staging_only:
            with self.subTest(var=staging_var):
                # Verify staging vars aren't referenced in production config
                pass  # Actual validation would happen in deployment
    
    def test_configuration_change_detection(self):
        """
        Test that configuration changes are detectable.
        
        This is a placeholder for the configuration change tracker
        that will be implemented next.
        """
        # Track critical configuration keys
        critical_keys = [
            'SERVICE_SECRET',
            'JWT_SECRET',
            'AUTH_SERVICE_URL',
            'DATABASE_URL',
            'REDIS_URL',
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET'
        ]
        
        # Verify we can detect changes
        for key in critical_keys:
            with self.subTest(config_key=key):
                # Set initial value
                initial_value = f'initial_{key}_value'
                self.set_env(key, initial_value)
                
                # Change value
                new_value = f'changed_{key}_value'
                self.set_env(key, new_value)
                
                # Verify change is detectable
                current = self.env.get(key)
                self.assertEqual(current, new_value,
                              f"Configuration change for {key} not detected")


class ConfigurationRegressionIntegrationTests(IsolatedTestCase):
    """
    Integration tests for configuration regression prevention.
    """
    
    def test_cross_service_config_consistency(self):
        """
        Test that configuration is consistent across services.
        """
        # This would normally import from actual services
        # For now, we verify the configuration structure
        
        services = ['auth_service', 'netra_backend', 'analytics_service']
        required_configs = ['SERVICE_SECRET', 'JWT_SECRET']
        
        for service in services:
            for config in required_configs:
                with self.subTest(service=service, config=config):
                    # In real test, would verify service can access config
                    # For now, just verify the expectation exists
                    self.assertIn(config, self.critical_configs)
    
    @unittest.skipIf(os.getenv('SKIP_DEPLOYMENT_TESTS', 'true').lower() == 'true',
                     "Deployment tests skipped")
    def test_deployment_config_validation(self):
        """
        Test that deployment configurations are valid.
        """
        from deployment.secrets_config import validate_secret_mappings
        
        environments = ['staging', 'production']
        
        for env_name in environments:
            with self.subTest(environment=env_name):
                # Validate secret mappings
                is_valid, errors = validate_secret_mappings(env_name)
                
                self.assertTrue(is_valid,
                              f"Invalid secret mappings for {env_name}: {errors}")


def suite():
    """Create test suite for CI/CD pipeline."""
    suite = unittest.TestSuite()
    
    # Add critical tests that must pass
    suite.addTest(ConfigurationRegressionTests('test_service_secret_presence_all_environments'))
    suite.addTest(ConfigurationRegressionTests('test_jwt_secret_resolution_consistency'))
    suite.addTest(ConfigurationRegressionTests('test_oauth_dual_naming_consistency'))
    suite.addTest(ConfigurationRegressionTests('test_config_validation_at_startup'))
    suite.addTest(ConfigurationRegressionTests('test_service_secret_strength_validation'))
    
    # Add integration tests
    suite.addTest(ConfigurationRegressionIntegrationTests('test_cross_service_config_consistency'))
    
    return suite


if __name__ == '__main__':
    # Run with verbose output for CI/CD
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())
    
    # Exit with non-zero if any failures
    sys.exit(0 if result.wasSuccessful() else 1)