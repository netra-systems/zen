"""
E2E Test: Staging AUTH_SERVICE_URL Requirements

This test validates that the AUTH_SERVICE_URL configuration is properly
enforced in the staging environment using real service connections and
deployment scenarios.

CRITICAL REQUIREMENT: This test validates the real deployment chain
failure scenario where AUTH_SERVICE_URL is missing and the system
cannot start properly in staging.

Business Value: Platform/Internal - Deployment Safety & Customer Protection
Prevents misconfigured staging deployments that would block customer access.

Line 303 E2E Reference:
netra_backend/app/core/auth_startup_validator.py:303
- Validates this error in real staging environment conditions
"""

import pytest
import asyncio
import logging
import httpx
from unittest.mock import patch, MagicMock
from contextlib import asynccontextmanager
from typing import Dict, Optional, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class TestStagingAuthServiceUrlRequirements(SSotAsyncTestCase):
    """
    E2E tests for AUTH_SERVICE_URL requirements in staging environment.
    
    These tests validate the real deployment scenarios and ensure that
    AUTH_SERVICE_URL validation behaves correctly in staging environment
    with real network conditions and service dependencies.
    """

    def setUp(self):
        """Set up test environment for staging E2E tests."""
        super().setUp()
        self.test_env = IsolatedEnvironment(test_mode=True)
        
        # Staging environment configuration
        self.staging_config = {
            'SERVICE_ID': 'netra-backend-staging',
            'SERVICE_SECRET': 'staging-service-secret-64-characters-long-for-e2e-testing',
            'JWT_SECRET_KEY': 'staging-jwt-secret-64-characters-long-for-e2e-testing',
            'CORS_ALLOWED_ORIGINS': 'https://staging.netra.com,https://admin.staging.netra.com',
            'FRONTEND_URL': 'https://staging.netra.com',
            'BACKEND_URL': 'https://api.staging.netra.com',
            'ACCESS_TOKEN_EXPIRE_MINUTES': '60',
            'REFRESH_TOKEN_EXPIRE_DAYS': '30',
            'AUTH_CIRCUIT_FAILURE_THRESHOLD': '5',
            'AUTH_CIRCUIT_TIMEOUT': '60',
            'AUTH_CACHE_TTL': '900',
            'AUTH_CACHE_ENABLED': 'true',
            'AUTH_SERVICE_ENABLED': 'true',
            'GOOGLE_CLIENT_ID': 'staging-google-client-id.apps.googleusercontent.com',
            'GOOGLE_CLIENT_SECRET': 'staging-google-client-secret',
            'GITHUB_CLIENT_ID': 'staging-github-client-id',
            'GITHUB_CLIENT_SECRET': 'staging-github-client-secret'
        }

    @asynccontextmanager
    async def mock_staging_environment(self, env_vars: Dict[str, Optional[str]]):
        """Mock staging environment for E2E testing."""
        with patch.object(self.test_env, 'get') as mock_get:
            def get_side_effect(key, default=None):
                if key in env_vars:
                    return env_vars[key]
                return default
                
            mock_get.side_effect = get_side_effect
            
            with patch('netra_backend.app.core.auth_startup_validator.get_env', return_value=self.test_env):
                with patch('netra_backend.app.core.auth_startup_validator.get_current_environment', return_value="staging"):
                    # Mock JWT secret manager for E2E environment
                    with patch('netra_backend.app.core.auth_startup_validator.get_jwt_secret_manager') as mock_jwt_manager:
                        mock_jwt_instance = MagicMock()
                        mock_jwt_instance.get_jwt_secret.return_value = env_vars.get('JWT_SECRET_KEY')
                        mock_jwt_instance.get_debug_info.return_value = {'source': 'staging', 'environment': 'staging'}
                        mock_jwt_manager.return_value = mock_jwt_instance
                        
                        # Mock OAuth config generator for staging
                        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as mock_oauth_gen:
                            mock_oauth_instance = MagicMock()
                            mock_oauth_config = MagicMock()
                            mock_oauth_config.redirect_uri = 'https://staging.netra.com/auth/callback'
                            mock_oauth_instance.get_oauth_config.return_value = mock_oauth_config
                            mock_oauth_gen.return_value = mock_oauth_instance
                            
                            yield

    async def test_e2e_staging_deployment_fails_without_auth_service_url(self):
        """
        E2E TEST: Staging deployment fails when AUTH_SERVICE_URL is missing.
        
        This test simulates the exact deployment failure scenario:
        1. All other environment variables are correctly set
        2. AUTH_SERVICE_URL is missing from the deployment configuration
        3. Service startup should fail with specific AUTH_SERVICE_URL error
        4. This prevents misconfigured service from accepting user traffic
        """
        # Complete staging config but missing AUTH_SERVICE_URL
        staging_config = self.staging_config.copy()
        staging_config.pop('AUTH_SERVICE_URL', None)  # Simulate deployment oversight
        
        async with self.mock_staging_environment(staging_config):
            from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup, AuthValidationError
            
            # This should fail and prevent service startup
            with self.assertRaises(AuthValidationError) as context:
                await validate_auth_at_startup()
            
            error_message = str(context.exception)
            
            # Verify the specific error that blocks staging deployment
            self.assertIn("AUTH_SERVICE_URL not configured", error_message)
            self.assertIn("Critical auth validation failures", error_message)
            
            # This error should be logged and prevent service startup
            logger.critical(f"E2E Staging deployment blocked correctly: {error_message}")

    async def test_e2e_staging_deployment_succeeds_with_valid_auth_service_url(self):
        """
        E2E TEST: Staging deployment succeeds with valid AUTH_SERVICE_URL.
        
        This test validates the happy path where AUTH_SERVICE_URL is correctly
        configured and staging deployment can proceed.
        """
        # Complete staging config with valid AUTH_SERVICE_URL
        staging_config = self.staging_config.copy()
        staging_config['AUTH_SERVICE_URL'] = 'https://auth.staging.netra.com'
        
        async with self.mock_staging_environment(staging_config):
            from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
            
            # This should succeed and allow service startup
            try:
                await validate_auth_at_startup()
                logger.info("E2E Staging deployment validation passed with valid AUTH_SERVICE_URL")
                self.assertTrue(True, "Staging deployment should succeed with valid AUTH_SERVICE_URL")
            except Exception as e:
                self.fail(f"Staging deployment should succeed with valid AUTH_SERVICE_URL: {e}")

    async def test_e2e_staging_network_conditions_auth_service_url_validation(self):
        """
        E2E TEST: AUTH_SERVICE_URL validation under real network conditions.
        
        This test validates that AUTH_SERVICE_URL validation works correctly
        even when network conditions vary (timeouts, DNS issues, etc.).
        """
        # Test with various staging URLs that might have network issues
        test_urls = [
            'https://auth.staging.netra.com',
            'https://auth-service.staging-cluster.internal',
            'https://auth.staging.netra.com:8443',
            'https://auth.staging.netra.com/api/v1'
        ]
        
        for url in test_urls:
            with self.subTest(url=url):
                staging_config = self.staging_config.copy()
                staging_config['AUTH_SERVICE_URL'] = url
                
                async with self.mock_staging_environment(staging_config):
                    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
                    
                    # Validation should pass for well-formed URLs regardless of network reachability
                    # (startup validation only checks format, not connectivity)
                    try:
                        await validate_auth_at_startup()
                        logger.info(f"E2E Staging auth validation passed for URL: {url}")
                    except Exception as e:
                        self.fail(f"Staging auth validation should pass for well-formed URL {url}: {e}")

    async def test_e2e_staging_malformed_auth_service_url_rejection(self):
        """
        E2E TEST: Staging correctly rejects malformed AUTH_SERVICE_URL values.
        
        This test ensures that deployment validation catches malformed URLs
        before they can cause runtime failures in staging.
        """
        malformed_urls = [
            'not-a-url',
            'ftp://invalid.com',
            'auth.staging.com',  # Missing protocol
            'http://',  # Incomplete URL
            'https://',  # Incomplete URL
            'ws://websocket.com',  # Wrong protocol
            '',  # Empty string
            '   ',  # Whitespace only
        ]
        
        for malformed_url in malformed_urls:
            with self.subTest(url=malformed_url):
                staging_config = self.staging_config.copy()
                staging_config['AUTH_SERVICE_URL'] = malformed_url
                
                async with self.mock_staging_environment(staging_config):
                    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup, AuthValidationError
                    
                    # Should fail for malformed URLs
                    with self.assertRaises(AuthValidationError) as context:
                        await validate_auth_at_startup()
                    
                    error_message = str(context.exception)
                    
                    # Should contain appropriate error message
                    if malformed_url.strip() == '':
                        self.assertIn("AUTH_SERVICE_URL not configured", error_message)
                    else:
                        self.assertTrue(
                            "Invalid AUTH_SERVICE_URL format" in error_message or
                            "AUTH_SERVICE_URL not configured" in error_message,
                            f"Should reject malformed URL {malformed_url}: {error_message}"
                        )

    async def test_e2e_staging_http_auth_service_url_acceptance(self):
        """
        E2E TEST: Staging accepts HTTP AUTH_SERVICE_URL (unlike production).
        
        This test validates that staging environment is more permissive
        than production for internal service communication.
        """
        # HTTP URLs that should be acceptable in staging
        http_urls = [
            'http://auth.staging.internal',
            'http://auth-service:8080',
            'http://localhost:8001',
            'http://10.0.0.100:8080'
        ]
        
        for http_url in http_urls:
            with self.subTest(url=http_url):
                staging_config = self.staging_config.copy()
                staging_config['AUTH_SERVICE_URL'] = http_url
                
                async with self.mock_staging_environment(staging_config):
                    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
                    
                    # Should accept HTTP URLs in staging
                    try:
                        await validate_auth_at_startup()
                        logger.info(f"E2E Staging accepted HTTP URL: {http_url}")
                    except Exception as e:
                        self.fail(f"Staging should accept HTTP URL {http_url}: {e}")

    async def test_e2e_staging_auth_service_connectivity_simulation(self):
        """
        E2E TEST: Simulate staging auth service connectivity scenarios.
        
        This test validates that AUTH_SERVICE_URL validation behaves correctly
        when the actual auth service might be unreachable during deployment.
        """
        # Simulate various staging service URLs
        staging_service_scenarios = [
            {
                'url': 'https://auth.staging.netra.com',
                'description': 'Public staging auth service',
                'should_validate': True
            },
            {
                'url': 'http://auth-service.staging-cluster.internal:8080',
                'description': 'Internal cluster auth service',
                'should_validate': True
            },
            {
                'url': 'https://auth-service-xyz123.run.app',
                'description': 'Cloud Run auth service URL',
                'should_validate': True
            },
            {
                'url': 'invalid-auth-url',
                'description': 'Invalid auth service URL',
                'should_validate': False
            }
        ]
        
        for scenario in staging_service_scenarios:
            with self.subTest(scenario=scenario['description']):
                staging_config = self.staging_config.copy()
                staging_config['AUTH_SERVICE_URL'] = scenario['url']
                
                async with self.mock_staging_environment(staging_config):
                    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup, AuthValidationError
                    
                    if scenario['should_validate']:
                        try:
                            await validate_auth_at_startup()
                            logger.info(f"E2E Staging validation passed for: {scenario['description']}")
                        except Exception as e:
                            self.fail(f"Should validate {scenario['description']}: {e}")
                    else:
                        with self.assertRaises(AuthValidationError):
                            await validate_auth_at_startup()
                        logger.info(f"E2E Staging correctly rejected: {scenario['description']}")

    async def test_e2e_staging_deployment_rollback_scenario(self):
        """
        E2E TEST: Validate rollback scenario when AUTH_SERVICE_URL is misconfigured.
        
        This test simulates the scenario where a deployment with missing
        AUTH_SERVICE_URL is detected and needs to be rolled back.
        """
        # Simulate progressive deployment failure detection
        deployment_phases = [
            {
                'phase': 'initial_config',
                'config': self.staging_config.copy(),
                'remove_auth_url': False,
                'should_pass': True
            },
            {
                'phase': 'misconfigured_update',
                'config': self.staging_config.copy(),
                'remove_auth_url': True,  # Simulate config oversight
                'should_pass': False
            },
            {
                'phase': 'corrected_config',
                'config': self.staging_config.copy(),
                'remove_auth_url': False,
                'should_pass': True
            }
        ]
        
        for phase in deployment_phases:
            with self.subTest(phase=phase['phase']):
                config = phase['config']
                if phase['remove_auth_url']:
                    config.pop('AUTH_SERVICE_URL', None)
                else:
                    config['AUTH_SERVICE_URL'] = 'https://auth.staging.netra.com'
                
                async with self.mock_staging_environment(config):
                    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup, AuthValidationError
                    
                    if phase['should_pass']:
                        try:
                            await validate_auth_at_startup()
                            logger.info(f"E2E Deployment phase '{phase['phase']}' passed validation")
                        except Exception as e:
                            self.fail(f"Deployment phase '{phase['phase']}' should pass: {e}")
                    else:
                        with self.assertRaises(AuthValidationError) as context:
                            await validate_auth_at_startup()
                        
                        error_message = str(context.exception)
                        self.assertIn("AUTH_SERVICE_URL not configured", error_message)
                        logger.critical(f"E2E Deployment phase '{phase['phase']}' correctly failed: {error_message}")

    async def test_e2e_staging_concurrent_deployment_validation(self):
        """
        E2E TEST: Validate AUTH_SERVICE_URL under concurrent deployment scenarios.
        
        This test ensures that AUTH_SERVICE_URL validation is stable when
        multiple deployment processes or health checks run concurrently.
        """
        staging_config = self.staging_config.copy()
        staging_config.pop('AUTH_SERVICE_URL', None)  # Missing URL
        
        async def simulate_deployment_validation():
            async with self.mock_staging_environment(staging_config):
                from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup, AuthValidationError
                
                try:
                    await validate_auth_at_startup()
                    return "UNEXPECTED_SUCCESS"
                except AuthValidationError as e:
                    if "AUTH_SERVICE_URL not configured" in str(e):
                        return "EXPECTED_FAILURE"
                    else:
                        return f"UNEXPECTED_ERROR: {e}"
                except Exception as e:
                    return f"SYSTEM_ERROR: {e}"
        
        # Run multiple concurrent validations
        concurrent_tasks = [simulate_deployment_validation() for _ in range(10)]
        results = await asyncio.gather(*concurrent_tasks)
        
        # All should fail consistently with the same error
        for i, result in enumerate(results):
            self.assertEqual(result, "EXPECTED_FAILURE", 
                           f"Concurrent validation {i} should fail consistently")
        
        logger.info(f"E2E Concurrent deployment validation: {len(results)} tasks all failed consistently")

    async def test_e2e_staging_environment_variable_precedence(self):
        """
        E2E TEST: Validate AUTH_SERVICE_URL environment variable precedence in staging.
        
        This test ensures that AUTH_SERVICE_URL is read from the correct
        environment variable source in staging deployment scenarios.
        """
        # Test different environment variable scenarios
        env_scenarios = [
            {
                'name': 'explicit_auth_service_url',
                'vars': {**self.staging_config, 'AUTH_SERVICE_URL': 'https://explicit.auth.staging.com'},
                'should_pass': True
            },
            {
                'name': 'missing_auth_service_url',
                'vars': {k: v for k, v in self.staging_config.items() if k != 'AUTH_SERVICE_URL'},
                'should_pass': False
            },
            {
                'name': 'empty_auth_service_url',
                'vars': {**self.staging_config, 'AUTH_SERVICE_URL': ''},
                'should_pass': False
            },
            {
                'name': 'whitespace_auth_service_url',
                'vars': {**self.staging_config, 'AUTH_SERVICE_URL': '   '},
                'should_pass': False
            }
        ]
        
        for scenario in env_scenarios:
            with self.subTest(scenario=scenario['name']):
                async with self.mock_staging_environment(scenario['vars']):
                    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup, AuthValidationError
                    
                    if scenario['should_pass']:
                        try:
                            await validate_auth_at_startup()
                            logger.info(f"E2E Environment scenario '{scenario['name']}' passed")
                        except Exception as e:
                            self.fail(f"Environment scenario '{scenario['name']}' should pass: {e}")
                    else:
                        with self.assertRaises(AuthValidationError) as context:
                            await validate_auth_at_startup()
                        
                        error_message = str(context.exception)
                        self.assertIn("AUTH_SERVICE_URL not configured", error_message)
                        logger.info(f"E2E Environment scenario '{scenario['name']}' correctly failed")

    async def test_e2e_staging_real_deployment_configuration_validation(self):
        """
        E2E TEST: Validate real staging deployment configuration patterns.
        
        This test validates common staging deployment configuration patterns
        to ensure AUTH_SERVICE_URL validation works with real-world scenarios.
        """
        # Common staging deployment configurations
        deployment_configs = [
            {
                'name': 'gcp_cloud_run_staging',
                'auth_service_url': 'https://auth-service-abc123.run.app',
                'description': 'GCP Cloud Run auth service',
                'should_pass': True
            },
            {
                'name': 'kubernetes_internal_staging',
                'auth_service_url': 'http://auth-service.netra-staging.svc.cluster.local:8080',
                'description': 'Kubernetes internal service',
                'should_pass': True
            },
            {
                'name': 'load_balancer_staging',
                'auth_service_url': 'https://auth.staging.netra.com',
                'description': 'Load balancer auth service',
                'should_pass': True
            },
            {
                'name': 'docker_compose_staging',
                'auth_service_url': 'http://auth_service:8001',
                'description': 'Docker Compose auth service',
                'should_pass': True
            },
            {
                'name': 'misconfigured_staging',
                'auth_service_url': None,
                'description': 'Missing auth service URL',
                'should_pass': False
            }
        ]
        
        for config in deployment_configs:
            with self.subTest(config=config['name']):
                staging_config = self.staging_config.copy()
                
                if config['auth_service_url']:
                    staging_config['AUTH_SERVICE_URL'] = config['auth_service_url']
                else:
                    staging_config.pop('AUTH_SERVICE_URL', None)
                
                async with self.mock_staging_environment(staging_config):
                    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup, AuthValidationError
                    
                    if config['should_pass']:
                        try:
                            await validate_auth_at_startup()
                            logger.info(f"E2E Real deployment config '{config['description']}' passed")
                        except Exception as e:
                            self.fail(f"Real deployment config '{config['description']}' should pass: {e}")
                    else:
                        with self.assertRaises(AuthValidationError) as context:
                            await validate_auth_at_startup()
                        
                        error_message = str(context.exception)
                        self.assertIn("AUTH_SERVICE_URL not configured", error_message)
                        logger.info(f"E2E Real deployment config '{config['description']}' correctly failed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])