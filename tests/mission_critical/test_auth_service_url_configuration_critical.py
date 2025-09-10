"""
Mission Critical Test: AUTH_SERVICE_URL Configuration Validation

This test validates that the AUTH_SERVICE_URL configuration is properly
set across all environments and that startup failures occur when it's missing.

CRITICAL REQUIREMENT: This test MUST FAIL when AUTH_SERVICE_URL is missing
to prevent deployment of misconfigured systems.

Business Value: Platform/Internal - System Stability & Revenue Protection
Prevents 100% authentication failure causing complete customer lockout.

Line 303 Error Reference:
netra_backend/app/core/auth_startup_validator.py:303
- if not auth_url:
-     result.error = "AUTH_SERVICE_URL not configured"
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthValidationError,
    AuthComponent,
    AuthValidationResult
)
from netra_backend.app.core.environment_constants import Environment

logger = logging.getLogger(__name__)


class TestAuthServiceUrlConfigurationCritical(SSotAsyncTestCase):
    """
    Mission critical tests for AUTH_SERVICE_URL configuration.
    
    These tests validate the specific failure scenario causing production
    outages when AUTH_SERVICE_URL is not properly configured in deployment.
    """

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.test_env = get_env()
        
        # Base environment config (minimal required for auth validator)
        self.base_config = {
            'SERVICE_ID': 'test-backend-service',
            'SERVICE_SECRET': 'b8f9c2e5d1a7f4e9c0b3a6d9f2e5c8b1',  # Strong 32-char hex
            'JWT_SECRET_KEY': 'a1b2c3d4e5f6789012345678901234567890',
            'CORS_ALLOWED_ORIGINS': 'http://localhost:3000',
            'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
            'REFRESH_TOKEN_EXPIRE_DAYS': '7',
            'AUTH_CIRCUIT_FAILURE_THRESHOLD': '3',
            'AUTH_CIRCUIT_TIMEOUT': '30',
            'AUTH_CACHE_TTL': '300',
            'AUTH_SERVICE_ENABLED': 'true'
        }

    @contextmanager
    def mock_environment(self, env_vars: Dict[str, Optional[str]], environment: str = "staging"):
        """Mock environment variables for testing."""
        with patch.object(self.test_env, 'get') as mock_get:
            def get_side_effect(key, default=None):
                if key in env_vars:
                    return env_vars[key]
                return default
                
            mock_get.side_effect = get_side_effect
            
            with patch('netra_backend.app.core.auth_startup_validator.get_env', return_value=self.test_env):
                with patch('netra_backend.app.core.auth_startup_validator.get_current_environment', return_value=environment):
                    yield

    async def test_missing_auth_service_url_critical_failure(self):
        """
        CRITICAL TEST: Validate that missing AUTH_SERVICE_URL causes startup failure.
        
        This test reproduces the exact line 303 error:
        netra_backend/app/core/auth_startup_validator.py:303
        """
        # Environment with all required config EXCEPT AUTH_SERVICE_URL
        env_config = self.base_config.copy()
        # Deliberately omit AUTH_SERVICE_URL to trigger the error
        env_config.pop('AUTH_SERVICE_URL', None)  # Ensure it's not present
        
        with self.mock_environment(env_config, "staging"):
            validator = AuthStartupValidator()
            
            # This should fail due to missing AUTH_SERVICE_URL
            success, results = await validator.validate_all()
            
            # CRITICAL: Validation MUST FAIL
            assert not success, "Auth validation should FAIL when AUTH_SERVICE_URL is missing"
            
            # Find the specific AUTH_SERVICE_URL validation result
            auth_url_result = None
            for result in results:
                if result.component == AuthComponent.AUTH_SERVICE_URL:
                    auth_url_result = result
                    break
            
            # Validate the specific error condition from line 303
            assert auth_url_result is not None, "AUTH_SERVICE_URL validation result should exist"
            assert not auth_url_result.valid, "AUTH_SERVICE_URL validation should fail"
            assert auth_url_result.error == "AUTH_SERVICE_URL not configured", \
                "Error message should match line 303 expectation"
            assert auth_url_result.is_critical, "AUTH_SERVICE_URL validation should be critical"

    async def test_validate_auth_at_startup_raises_exception_for_missing_auth_service_url(self):
        """
        CRITICAL TEST: Validate that validate_auth_at_startup() raises AuthValidationError
        when AUTH_SERVICE_URL is missing.
        """
        from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
        
        # Environment missing AUTH_SERVICE_URL
        env_config = self.base_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)
        
        with self.mock_environment(env_config, "staging"):
            # This should raise AuthValidationError
            with self.assertRaises(AuthValidationError) as context:
                await validate_auth_at_startup()
            
            # Verify the exception contains AUTH_SERVICE_URL error
            error_message = str(context.exception)
            self.assertIn("AUTH_SERVICE_URL not configured", error_message)
            self.assertIn("auth_service_url", error_message)

    async def test_staging_environment_requires_auth_service_url(self):
        """
        CRITICAL TEST: Staging environment requires AUTH_SERVICE_URL.
        
        This validates the specific deployment scenario causing failures.
        """
        env_config = self.base_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)
        
        with self.mock_environment(env_config, "staging"):
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # In staging, AUTH_SERVICE_URL is required
            self.assertFalse(success, "Staging should require AUTH_SERVICE_URL")
            
            # Verify critical failure exists
            critical_failures = [r for r in results if not r.valid and r.is_critical]
            auth_url_failures = [r for r in critical_failures 
                               if r.component == AuthComponent.AUTH_SERVICE_URL]
            
            self.assertGreater(len(auth_url_failures), 0, 
                             "Should have AUTH_SERVICE_URL critical failure in staging")

    async def test_production_environment_requires_auth_service_url(self):
        """
        CRITICAL TEST: Production environment requires AUTH_SERVICE_URL.
        """
        env_config = self.base_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)
        
        with self.mock_environment(env_config, "production"):
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # In production, AUTH_SERVICE_URL is absolutely required
            self.assertFalse(success, "Production MUST require AUTH_SERVICE_URL")
            
            # Verify critical failure exists
            critical_failures = [r for r in results if not r.valid and r.is_critical]
            auth_url_failures = [r for r in critical_failures 
                               if r.component == AuthComponent.AUTH_SERVICE_URL]
            
            self.assertGreater(len(auth_url_failures), 0, 
                             "Should have AUTH_SERVICE_URL critical failure in production")

    async def test_development_auth_service_url_can_be_disabled(self):
        """
        TEST: Development environment can disable auth service.
        """
        env_config = self.base_config.copy()
        env_config.pop('AUTH_SERVICE_URL', None)
        env_config['AUTH_SERVICE_ENABLED'] = 'false'
        
        with self.mock_environment(env_config, "development"):
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Find AUTH_SERVICE_URL validation result
            auth_url_result = None
            for result in results:
                if result.component == AuthComponent.AUTH_SERVICE_URL:
                    auth_url_result = result
                    break
            
            # In development with AUTH_SERVICE_ENABLED=false, this should be non-critical
            self.assertIsNotNone(auth_url_result, "AUTH_SERVICE_URL validation should exist")
            if not auth_url_result.valid:
                self.assertFalse(auth_url_result.is_critical, 
                               "AUTH_SERVICE_URL should be non-critical in development when disabled")

    async def test_valid_auth_service_url_passes_validation(self):
        """
        TEST: Valid AUTH_SERVICE_URL configuration passes validation.
        """
        env_config = self.base_config.copy()
        env_config['AUTH_SERVICE_URL'] = 'https://auth.netra.staging.com'
        
        with self.mock_environment(env_config, "staging"):
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Find AUTH_SERVICE_URL validation result
            auth_url_result = None
            for result in results:
                if result.component == AuthComponent.AUTH_SERVICE_URL:
                    auth_url_result = result
                    break
            
            # Should pass validation
            self.assertIsNotNone(auth_url_result, "AUTH_SERVICE_URL validation should exist")
            self.assertTrue(auth_url_result.valid, "Valid AUTH_SERVICE_URL should pass validation")

    async def test_invalid_auth_service_url_format_fails(self):
        """
        TEST: Invalid AUTH_SERVICE_URL format fails validation.
        """
        invalid_urls = [
            'not-a-url',
            'ftp://invalid.com',
            'auth.example.com',  # Missing protocol
            ''
        ]
        
        for invalid_url in invalid_urls:
            with self.subTest(url=invalid_url):
                env_config = self.base_config.copy()
                env_config['AUTH_SERVICE_URL'] = invalid_url
                
                with self.mock_environment(env_config, "staging"):
                    validator = AuthStartupValidator()
                    success, results = await validator.validate_all()
                    
                    # Should fail validation for invalid format
                    auth_url_result = None
                    for result in results:
                        if result.component == AuthComponent.AUTH_SERVICE_URL:
                            auth_url_result = result
                            break
                    
                    if invalid_url == '':
                        # Empty URL triggers the "not configured" error
                        self.assertIsNotNone(auth_url_result)
                        self.assertFalse(auth_url_result.valid)
                        self.assertEqual(auth_url_result.error, "AUTH_SERVICE_URL not configured")
                    else:
                        # Invalid format triggers format error
                        self.assertIsNotNone(auth_url_result)
                        self.assertFalse(auth_url_result.valid)
                        self.assertIn("Invalid AUTH_SERVICE_URL format", auth_url_result.error)

    async def test_production_requires_https_auth_service_url(self):
        """
        TEST: Production environment requires HTTPS for AUTH_SERVICE_URL.
        """
        env_config = self.base_config.copy()
        env_config['AUTH_SERVICE_URL'] = 'http://auth.example.com'  # HTTP not HTTPS
        
        with self.mock_environment(env_config, "production"):
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Should fail validation in production
            auth_url_result = None
            for result in results:
                if result.component == AuthComponent.AUTH_SERVICE_URL:
                    auth_url_result = result
                    break
            
            self.assertIsNotNone(auth_url_result)
            self.assertFalse(auth_url_result.valid)
            self.assertIn("must use HTTPS in production", auth_url_result.error)

    async def test_staging_accepts_http_auth_service_url(self):
        """
        TEST: Staging environment accepts HTTP for AUTH_SERVICE_URL.
        """
        env_config = self.base_config.copy()
        env_config['AUTH_SERVICE_URL'] = 'http://auth.staging.com'
        
        with self.mock_environment(env_config, "staging"):
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            # Should pass validation in staging
            auth_url_result = None
            for result in results:
                if result.component == AuthComponent.AUTH_SERVICE_URL:
                    auth_url_result = result
                    break
            
            self.assertIsNotNone(auth_url_result)
            self.assertTrue(auth_url_result.valid, "HTTP should be acceptable in staging")

    async def test_multiple_environment_configurations(self):
        """
        COMPREHENSIVE TEST: Test AUTH_SERVICE_URL across multiple environments.
        """
        test_cases = [
            {
                'environment': 'development',
                'auth_service_url': None,
                'auth_service_enabled': 'false',
                'should_pass': True,
                'description': 'Development with auth disabled'
            },
            {
                'environment': 'development', 
                'auth_service_url': 'http://localhost:8001',
                'auth_service_enabled': 'true',
                'should_pass': True,
                'description': 'Development with local auth service'
            },
            {
                'environment': 'staging',
                'auth_service_url': None,
                'auth_service_enabled': 'true',
                'should_pass': False,
                'description': 'Staging missing AUTH_SERVICE_URL'
            },
            {
                'environment': 'staging',
                'auth_service_url': 'https://auth.staging.com',
                'auth_service_enabled': 'true',
                'should_pass': True,
                'description': 'Staging with proper HTTPS auth service'
            },
            {
                'environment': 'production',
                'auth_service_url': None,
                'auth_service_enabled': 'true',
                'should_pass': False,
                'description': 'Production missing AUTH_SERVICE_URL'
            },
            {
                'environment': 'production',
                'auth_service_url': 'https://auth.netra.com',
                'auth_service_enabled': 'true',
                'should_pass': True,
                'description': 'Production with proper HTTPS auth service'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['description']):
                env_config = self.base_config.copy()
                
                if case['auth_service_url']:
                    env_config['AUTH_SERVICE_URL'] = case['auth_service_url']
                else:
                    env_config.pop('AUTH_SERVICE_URL', None)
                
                env_config['AUTH_SERVICE_ENABLED'] = case['auth_service_enabled']
                
                with self.mock_environment(env_config, case['environment']):
                    validator = AuthStartupValidator()
                    success, results = await validator.validate_all()
                    
                    if case['should_pass']:
                        # Should pass overall validation or AUTH_SERVICE_URL should be non-critical
                        auth_url_result = None
                        for result in results:
                            if result.component == AuthComponent.AUTH_SERVICE_URL:
                                auth_url_result = result
                                break
                        
                        if auth_url_result and not auth_url_result.valid:
                            self.assertFalse(auth_url_result.is_critical, 
                                           f"AUTH_SERVICE_URL should be non-critical for {case['description']}")
                    else:
                        # Should fail validation
                        self.assertFalse(success, f"Should fail for {case['description']}")
                        
                        # Should have AUTH_SERVICE_URL critical failure
                        critical_failures = [r for r in results if not r.valid and r.is_critical]
                        auth_url_failures = [r for r in critical_failures 
                                           if r.component == AuthComponent.AUTH_SERVICE_URL]
                        
                        self.assertGreater(len(auth_url_failures), 0, 
                                         f"Should have AUTH_SERVICE_URL critical failure for {case['description']}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])