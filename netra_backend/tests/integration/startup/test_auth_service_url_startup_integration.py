"""
Integration Test: AUTH_SERVICE_URL Startup Integration

This test validates that the AUTH_SERVICE_URL configuration is properly
integrated into the complete system startup sequence, including interaction
with other components.

CRITICAL REQUIREMENT: This test validates that missing AUTH_SERVICE_URL
causes the entire startup process to fail, preventing system initialization.

Business Value: Platform/Internal - System Stability
Ensures authentication configuration failures prevent unsafe system startup.

Line 303 Integration Reference:
netra_backend/app/core/auth_startup_validator.py:303
- Validates that this error propagates through the startup chain
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import asynccontextmanager
from typing import Dict, Optional, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthValidationError,
    validate_auth_at_startup
)
from netra_backend.app.core.environment_constants import Environment

logger = logging.getLogger(__name__)


class TestAuthServiceUrlStartupIntegration(SSotAsyncTestCase):
    """
    Integration tests for AUTH_SERVICE_URL in complete startup sequence.
    
    These tests validate that AUTH_SERVICE_URL validation properly integrates
    with the overall system startup process and fails appropriately.
    """

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.test_env = IsolatedEnvironment(test_mode=True)
        
        # Complete environment config for startup integration
        self.complete_config = {
            'SERVICE_ID': 'test-backend-service',
            'SERVICE_SECRET': 'test-service-secret-32-characters-long-for-integration',
            'JWT_SECRET_KEY': 'test-jwt-secret-32-characters-long-for-integration',
            'CORS_ALLOWED_ORIGINS': 'http://localhost:3000,https://staging.netra.com',
            'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
            'REFRESH_TOKEN_EXPIRE_DAYS': '7',
            'AUTH_CIRCUIT_FAILURE_THRESHOLD': '3',
            'AUTH_CIRCUIT_TIMEOUT': '30',
            'AUTH_CACHE_TTL': '300',
            'AUTH_CACHE_ENABLED': 'true',
            'AUTH_SERVICE_ENABLED': 'true',
            'FRONTEND_URL': 'https://staging.netra.com',
            'BACKEND_URL': 'https://api.staging.netra.com'
        }

    @asynccontextmanager
    async def mock_startup_environment(self, env_vars: Dict[str, Optional[str]], environment: str = "staging"):
        """Mock complete startup environment for integration testing."""
        with patch.object(self.test_env, 'get') as mock_get:
            def get_side_effect(key, default=None):
                if key in env_vars:
                    return env_vars[key]
                return default
                
            mock_get.side_effect = get_side_effect
            
            with patch('netra_backend.app.core.auth_startup_validator.get_env', return_value=self.test_env):
                with patch('netra_backend.app.core.auth_startup_validator.get_current_environment', return_value=environment):
                    # Mock JWT secret manager to avoid additional dependencies
                    with patch('netra_backend.app.core.auth_startup_validator.get_jwt_secret_manager') as mock_jwt_manager:
                        mock_jwt_instance = MagicMock()
                        mock_jwt_instance.get_jwt_secret.return_value = env_vars.get('JWT_SECRET_KEY', 'test-jwt-secret-32-chars-long')
                        mock_jwt_instance.get_debug_info.return_value = {'source': 'test', 'environment': environment}
                        mock_jwt_manager.return_value = mock_jwt_instance
                        
                        # Mock OAuth config generator to avoid additional dependencies
                        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as mock_oauth_gen:
                            mock_oauth_instance = MagicMock()
                            mock_oauth_config = MagicMock()
                            mock_oauth_config.redirect_uri = 'https://staging.netra.com/auth/callback'
                            mock_oauth_instance.get_oauth_config.return_value = mock_oauth_config
                            mock_oauth_gen.return_value = mock_oauth_instance
                            
                            yield

    async def test_startup_fails_when_auth_service_url_missing_staging(self):
        """
        INTEGRATION TEST: Complete startup fails when AUTH_SERVICE_URL missing in staging.
        
        This test validates that the AUTH_SERVICE_URL validation error
        propagates through the startup process and prevents system initialization.
        """
        # Complete config except missing AUTH_SERVICE_URL
        env_config = self.complete_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)  # Ensure missing
        
        async with self.mock_startup_environment(env_config, "staging"):
            # Test validate_auth_at_startup() entry point
            with self.assertRaises(AuthValidationError) as context:
                await validate_auth_at_startup()
            
            # Verify the specific error propagated
            error_message = str(context.exception)
            self.assertIn("AUTH_SERVICE_URL not configured", error_message)
            self.assertIn("auth_service_url", error_message.lower())

    async def test_startup_fails_when_auth_service_url_missing_production(self):
        """
        INTEGRATION TEST: Complete startup fails when AUTH_SERVICE_URL missing in production.
        """
        env_config = self.complete_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)
        env_config['FRONTEND_URL'] = 'https://netra.com'
        env_config['BACKEND_URL'] = 'https://api.netra.com'
        
        async with self.mock_startup_environment(env_config, "production"):
            with self.assertRaises(AuthValidationError) as context:
                await validate_auth_at_startup()
            
            error_message = str(context.exception)
            self.assertIn("AUTH_SERVICE_URL not configured", error_message)

    async def test_startup_succeeds_with_valid_auth_service_url_staging(self):
        """
        INTEGRATION TEST: Complete startup succeeds with valid AUTH_SERVICE_URL in staging.
        """
        env_config = self.complete_config.copy()
        env_config['AUTH_SERVICE_URL'] = 'https://auth.staging.netra.com'
        
        async with self.mock_startup_environment(env_config, "staging"):
            # This should not raise an exception
            try:
                await validate_auth_at_startup()
                # If we reach here, validation passed
                self.assertTrue(True, "Startup validation should succeed with valid AUTH_SERVICE_URL")
            except AuthValidationError as e:
                self.fail(f"Startup validation should succeed with valid AUTH_SERVICE_URL: {e}")

    async def test_startup_succeeds_with_valid_auth_service_url_production(self):
        """
        INTEGRATION TEST: Complete startup succeeds with valid AUTH_SERVICE_URL in production.
        """
        env_config = self.complete_config.copy()
        env_config['AUTH_SERVICE_URL'] = 'https://auth.netra.com'
        env_config['FRONTEND_URL'] = 'https://netra.com'
        env_config['BACKEND_URL'] = 'https://api.netra.com'
        
        async with self.mock_startup_environment(env_config, "production"):
            try:
                await validate_auth_at_startup()
                self.assertTrue(True, "Production startup should succeed with valid HTTPS AUTH_SERVICE_URL")
            except AuthValidationError as e:
                self.fail(f"Production startup should succeed with valid HTTPS AUTH_SERVICE_URL: {e}")

    async def test_startup_integration_with_other_validation_failures(self):
        """
        INTEGRATION TEST: AUTH_SERVICE_URL failure combined with other validation failures.
        
        This test ensures that AUTH_SERVICE_URL validation is properly integrated
        with other auth validations and all critical failures are reported.
        """
        # Environment with multiple auth failures
        env_config = {
            # Missing SERVICE_SECRET (critical)
            'SERVICE_ID': 'test-service',
            # Missing JWT_SECRET_KEY (critical) 
            'CORS_ALLOWED_ORIGINS': 'http://localhost:3000',
            'AUTH_SERVICE_ENABLED': 'true'
            # Missing AUTH_SERVICE_URL (critical)
        }
        
        async with self.mock_startup_environment(env_config, "staging"):
            with self.assertRaises(AuthValidationError) as context:
                await validate_auth_at_startup()
            
            error_message = str(context.exception)
            
            # Should contain multiple critical failures including AUTH_SERVICE_URL
            self.assertIn("AUTH_SERVICE_URL not configured", error_message)
            # May also contain other failures
            self.assertIn("Critical auth validation failures", error_message)

    async def test_development_startup_with_auth_disabled(self):
        """
        INTEGRATION TEST: Development environment with auth disabled should start successfully.
        """
        env_config = {
            'SERVICE_ID': 'test-service',
            'SERVICE_SECRET': 'test-service-secret-32-characters-long',
            'JWT_SECRET_KEY': 'test-jwt-secret-32-characters-long',
            'CORS_ALLOWED_ORIGINS': 'http://localhost:3000',
            'AUTH_SERVICE_ENABLED': 'false'
            # No AUTH_SERVICE_URL
        }
        
        async with self.mock_startup_environment(env_config, "development"):
            try:
                await validate_auth_at_startup()
                self.assertTrue(True, "Development startup should succeed with auth disabled")
            except AuthValidationError as e:
                self.fail(f"Development startup should succeed with auth disabled: {e}")

    async def test_auth_service_url_validation_timing_in_startup_sequence(self):
        """
        INTEGRATION TEST: Validate AUTH_SERVICE_URL is checked in proper startup sequence.
        
        This test ensures that AUTH_SERVICE_URL validation happens at the right time
        and doesn't interfere with other startup components.
        """
        env_config = self.complete_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)
        
        async with self.mock_startup_environment(env_config, "staging"):
            # Create validator and run full validation
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Should fail overall
            self.assertFalse(success, "Validation should fail when AUTH_SERVICE_URL missing")
            
            # Verify all expected validation components ran
            component_types = {result.component for result in results}
            
            # AUTH_SERVICE_URL should be validated along with other components
            from netra_backend.app.core.auth_startup_validator import AuthComponent
            expected_components = {
                AuthComponent.JWT_SECRET,
                AuthComponent.SERVICE_CREDENTIALS,
                AuthComponent.AUTH_SERVICE_URL,
                AuthComponent.OAUTH_CREDENTIALS,
                AuthComponent.CORS_ORIGINS,
                AuthComponent.TOKEN_EXPIRY,
                AuthComponent.CIRCUIT_BREAKER,
                AuthComponent.CACHE_CONFIG
            }
            
            # All components should have been validated
            for component in expected_components:
                self.assertIn(component, component_types, 
                             f"Component {component} should be validated in startup sequence")

    async def test_auth_service_url_error_propagation_details(self):
        """
        INTEGRATION TEST: Validate error details propagate correctly through startup.
        """
        env_config = self.complete_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)
        
        async with self.mock_startup_environment(env_config, "staging"):
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Find AUTH_SERVICE_URL result
            auth_url_result = None
            for result in results:
                if result.component.value == 'auth_service_url':
                    auth_url_result = result
                    break
            
            # Verify detailed error information
            self.assertIsNotNone(auth_url_result, "AUTH_SERVICE_URL result should exist")
            self.assertFalse(auth_url_result.valid)
            self.assertEqual(auth_url_result.error, "AUTH_SERVICE_URL not configured")
            self.assertTrue(auth_url_result.is_critical)
            
            # Critical failures should be identified correctly
            critical_failures = [r for r in results if not r.valid and r.is_critical]
            auth_url_failures = [r for r in critical_failures 
                               if r.component.value == 'auth_service_url']
            
            self.assertEqual(len(auth_url_failures), 1, 
                           "Should have exactly one AUTH_SERVICE_URL critical failure")

    async def test_concurrent_auth_validation_stability(self):
        """
        INTEGRATION TEST: Validate AUTH_SERVICE_URL validation is stable under concurrent access.
        
        This test ensures that the validation doesn't have race conditions
        when multiple startup processes run concurrently.
        """
        env_config = self.complete_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)
        
        async def run_validation():
            async with self.mock_startup_environment(env_config, "staging"):
                try:
                    await validate_auth_at_startup()
                    return "SUCCESS"
                except AuthValidationError as e:
                    return f"FAILED: {str(e)}"
        
        # Run multiple concurrent validations
        tasks = [run_validation() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should fail consistently
        for result in results:
            self.assertIn("FAILED", result, "All concurrent validations should fail consistently")
            self.assertIn("AUTH_SERVICE_URL not configured", result)

    async def test_auth_service_url_edge_case_integration(self):
        """
        INTEGRATION TEST: Edge cases for AUTH_SERVICE_URL in complete startup context.
        """
        edge_cases = [
            {
                'name': 'whitespace_only_url',
                'auth_service_url': '   ',
                'environment': 'staging',
                'should_fail': True
            },
            {
                'name': 'malformed_url',
                'auth_service_url': 'http://',
                'environment': 'staging', 
                'should_fail': True
            },
            {
                'name': 'port_in_url',
                'auth_service_url': 'https://auth.staging.com:8443',
                'environment': 'staging',
                'should_fail': False
            },
            {
                'name': 'path_in_url',
                'auth_service_url': 'https://auth.staging.com/v1',
                'environment': 'staging',
                'should_fail': False
            }
        ]
        
        for case in edge_cases:
            with self.subTest(case=case['name']):
                env_config = self.complete_config.copy()
                env_config['AUTH_SERVICE_URL'] = case['auth_service_url']
                
                async with self.mock_startup_environment(env_config, case['environment']):
                    if case['should_fail']:
                        with self.assertRaises(AuthValidationError) as context:
                            await validate_auth_at_startup()
                        
                        error_message = str(context.exception)
                        # Should contain some auth service URL related error
                        self.assertTrue(
                            "AUTH_SERVICE_URL" in error_message or 
                            "Invalid AUTH_SERVICE_URL format" in error_message,
                            f"Should contain AUTH_SERVICE_URL error for {case['name']}: {error_message}"
                        )
                    else:
                        try:
                            await validate_auth_at_startup()
                            # Success expected
                            self.assertTrue(True, f"Should succeed for {case['name']}")
                        except AuthValidationError as e:
                            self.fail(f"Should not fail for {case['name']}: {e}")

    async def test_auth_service_url_deployment_scenario_integration(self):
        """
        INTEGRATION TEST: Simulate real deployment scenarios where AUTH_SERVICE_URL fails.
        
        This test simulates the exact scenario causing production issues:
        - Deployment chain sets all other environment variables
        - AUTH_SERVICE_URL is missed or misconfigured
        - System attempts to start but fails auth validation
        """
        # Simulate GCP Cloud Run deployment environment
        deployment_config = {
            'SERVICE_ID': 'netra-backend-staging',
            'SERVICE_SECRET': 'production-grade-service-secret-64-characters-long-deployment',
            'JWT_SECRET_KEY': 'production-grade-jwt-secret-64-characters-long-deployment',
            'CORS_ALLOWED_ORIGINS': 'https://staging.netra.com,https://admin.staging.netra.com',
            'FRONTEND_URL': 'https://staging.netra.com',
            'BACKEND_URL': 'https://api.staging.netra.com',
            'DATABASE_URL': 'postgresql://user:pass@staging-db:5432/netra',
            'REDIS_URL': 'redis://staging-redis:6379/0',
            'ACCESS_TOKEN_EXPIRE_MINUTES': '60',
            'REFRESH_TOKEN_EXPIRE_DAYS': '30',
            'AUTH_CIRCUIT_FAILURE_THRESHOLD': '5',
            'AUTH_CIRCUIT_TIMEOUT': '60',
            'AUTH_CACHE_TTL': '900',
            'AUTH_CACHE_ENABLED': 'true',
            'AUTH_SERVICE_ENABLED': 'true',
            'GOOGLE_CLIENT_ID': 'staging-google-client-id',
            'GOOGLE_CLIENT_SECRET': 'staging-google-client-secret'
            # AUTH_SERVICE_URL is missing - this causes the deployment failure
        }
        
        async with self.mock_startup_environment(deployment_config, "staging"):
            # This simulates the exact startup failure scenario
            with self.assertRaises(AuthValidationError) as context:
                await validate_auth_at_startup()
            
            error_message = str(context.exception)
            
            # Verify this is the specific error that blocks deployment
            self.assertIn("AUTH_SERVICE_URL not configured", error_message)
            self.assertIn("Critical auth validation failures", error_message)
            
            # This error should prevent the entire service from starting
            # which is the correct behavior to prevent misconfigured deployments


if __name__ == '__main__':
    pytest.main([__file__, '-v'])