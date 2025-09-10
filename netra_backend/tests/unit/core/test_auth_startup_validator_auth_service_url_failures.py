"""
Unit Test: AUTH_SERVICE_URL Validation Failures in AuthStartupValidator

This test specifically focuses on the _validate_auth_service_url() method
and the specific line 303 error condition that causes startup failures.

CRITICAL REQUIREMENT: This test validates the exact error condition:
netra_backend/app/core/auth_startup_validator.py:303
- if not auth_url:
-     result.error = "AUTH_SERVICE_URL not configured"

Business Value: Platform/Internal - System Stability
Ensures AUTH_SERVICE_URL validation behaves correctly in isolation.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from typing import Dict, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthComponent,
    AuthValidationResult
)
from netra_backend.app.core.environment_constants import Environment

logger = logging.getLogger(__name__)


class TestAuthStartupValidatorAuthServiceUrlFailures(SSotAsyncTestCase):
    """
    Unit tests for AUTH_SERVICE_URL validation failures.
    
    These tests isolate the _validate_auth_service_url() method to verify
    specific error conditions and edge cases.
    """

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.test_env = IsolatedEnvironment(test_mode=True)

    def create_validator_with_environment(self, env_vars: Dict[str, Optional[str]], environment: str = "staging"):
        """Create AuthStartupValidator with mocked environment."""
        with patch.object(self.test_env, 'get') as mock_get:
            def get_side_effect(key, default=None):
                if key in env_vars:
                    return env_vars[key]
                return default
                
            mock_get.side_effect = get_side_effect
            
            with patch('netra_backend.app.core.auth_startup_validator.get_env', return_value=self.test_env):
                with patch('netra_backend.app.core.auth_startup_validator.get_current_environment', return_value=environment):
                    validator = AuthStartupValidator()
                    return validator

    async def test_validate_auth_service_url_missing_auth_service_url(self):
        """
        Unit test for line 303 error: AUTH_SERVICE_URL not configured.
        
        This tests the exact condition:
        if not auth_url:
            result.error = "AUTH_SERVICE_URL not configured"
        """
        # Environment without AUTH_SERVICE_URL
        env_vars = {
            'AUTH_SERVICE_ENABLED': 'true'
        }
        
        validator = self.create_validator_with_environment(env_vars, "staging")
        
        # Call the specific method under test
        await validator._validate_auth_service_url()
        
        # Verify result was added to validation_results
        self.assertEqual(len(validator.validation_results), 1)
        
        result = validator.validation_results[0]
        self.assertEqual(result.component, AuthComponent.AUTH_SERVICE_URL)
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "AUTH_SERVICE_URL not configured")
        self.assertTrue(result.is_critical)

    async def test_validate_auth_service_url_empty_string(self):
        """
        Unit test for empty string AUTH_SERVICE_URL.
        
        Empty string should trigger the same "not configured" error.
        """
        env_vars = {
            'AUTH_SERVICE_URL': '',
            'AUTH_SERVICE_ENABLED': 'true'
        }
        
        validator = self.create_validator_with_environment(env_vars, "staging")
        
        await validator._validate_auth_service_url()
        
        self.assertEqual(len(validator.validation_results), 1)
        result = validator.validation_results[0]
        self.assertEqual(result.component, AuthComponent.AUTH_SERVICE_URL)
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "AUTH_SERVICE_URL not configured")

    async def test_validate_auth_service_url_none_value(self):
        """
        Unit test for explicit None AUTH_SERVICE_URL.
        """
        env_vars = {
            'AUTH_SERVICE_URL': None,
            'AUTH_SERVICE_ENABLED': 'true'
        }
        
        validator = self.create_validator_with_environment(env_vars, "staging")
        
        await validator._validate_auth_service_url()
        
        self.assertEqual(len(validator.validation_results), 1)
        result = validator.validation_results[0]
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "AUTH_SERVICE_URL not configured")

    async def test_validate_auth_service_url_invalid_format(self):
        """
        Unit test for invalid AUTH_SERVICE_URL format.
        
        This tests the condition:
        elif not auth_url.startswith(('http://', 'https://')):
            result.error = f"Invalid AUTH_SERVICE_URL format: {auth_url}"
        """
        invalid_urls = [
            'not-a-url',
            'ftp://example.com', 
            'auth.example.com',
            'ws://websocket.com'
        ]
        
        for invalid_url in invalid_urls:
            with self.subTest(url=invalid_url):
                env_vars = {
                    'AUTH_SERVICE_URL': invalid_url,
                    'AUTH_SERVICE_ENABLED': 'true'
                }
                
                validator = self.create_validator_with_environment(env_vars, "staging")
                
                await validator._validate_auth_service_url()
                
                self.assertEqual(len(validator.validation_results), 1)
                result = validator.validation_results[0]
                self.assertFalse(result.valid)
                self.assertEqual(result.error, f"Invalid AUTH_SERVICE_URL format: {invalid_url}")

    async def test_validate_auth_service_url_production_requires_https(self):
        """
        Unit test for production HTTPS requirement.
        
        This tests the condition:
        if self.is_production and not auth_url.startswith('https://'):
            result.error = "AUTH_SERVICE_URL must use HTTPS in production"
        """
        env_vars = {
            'AUTH_SERVICE_URL': 'http://auth.example.com',
            'AUTH_SERVICE_ENABLED': 'true'
        }
        
        validator = self.create_validator_with_environment(env_vars, "production")
        
        await validator._validate_auth_service_url()
        
        self.assertEqual(len(validator.validation_results), 1)
        result = validator.validation_results[0]
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "AUTH_SERVICE_URL must use HTTPS in production")
        self.assertIsNotNone(result.details)
        self.assertEqual(result.details["url"], "http://auth.example.com")

    async def test_validate_auth_service_url_development_auth_disabled(self):
        """
        Unit test for development environment with auth disabled.
        
        This tests the condition:
        if not auth_enabled and not self.is_production:
            result.valid = True
            result.is_critical = False
        """
        env_vars = {
            'AUTH_SERVICE_ENABLED': 'false'
            # No AUTH_SERVICE_URL
        }
        
        validator = self.create_validator_with_environment(env_vars, "development")
        
        await validator._validate_auth_service_url()
        
        self.assertEqual(len(validator.validation_results), 1)
        result = validator.validation_results[0]
        self.assertTrue(result.valid)
        self.assertFalse(result.is_critical)

    async def test_validate_auth_service_url_valid_https_staging(self):
        """
        Unit test for valid HTTPS URL in staging.
        """
        env_vars = {
            'AUTH_SERVICE_URL': 'https://auth.staging.com',
            'AUTH_SERVICE_ENABLED': 'true'
        }
        
        validator = self.create_validator_with_environment(env_vars, "staging")
        
        await validator._validate_auth_service_url()
        
        self.assertEqual(len(validator.validation_results), 1)
        result = validator.validation_results[0]
        self.assertTrue(result.valid)
        self.assertTrue(result.is_critical)

    async def test_validate_auth_service_url_valid_http_staging(self):
        """
        Unit test for valid HTTP URL in staging (should be allowed).
        """
        env_vars = {
            'AUTH_SERVICE_URL': 'http://auth.staging.com',
            'AUTH_SERVICE_ENABLED': 'true'
        }
        
        validator = self.create_validator_with_environment(env_vars, "staging")
        
        await validator._validate_auth_service_url()
        
        self.assertEqual(len(validator.validation_results), 1)
        result = validator.validation_results[0]
        self.assertTrue(result.valid)

    async def test_validate_auth_service_url_valid_https_production(self):
        """
        Unit test for valid HTTPS URL in production.
        """
        env_vars = {
            'AUTH_SERVICE_URL': 'https://auth.netra.com',
            'AUTH_SERVICE_ENABLED': 'true'
        }
        
        validator = self.create_validator_with_environment(env_vars, "production")
        
        await validator._validate_auth_service_url()
        
        self.assertEqual(len(validator.validation_results), 1)
        result = validator.validation_results[0]
        self.assertTrue(result.valid)

    async def test_validate_auth_service_url_exception_handling(self):
        """
        Unit test for exception handling in _validate_auth_service_url().
        """
        # Mock env.get to raise an exception
        validator = AuthStartupValidator()
        
        with patch.object(validator.env, 'get', side_effect=Exception("Mock exception")):
            await validator._validate_auth_service_url()
            
            self.assertEqual(len(validator.validation_results), 1)
            result = validator.validation_results[0]
            self.assertFalse(result.valid)
            self.assertIn("Auth service URL validation error", result.error)
            self.assertIn("Mock exception", result.error)

    async def test_validate_auth_service_url_environment_handling(self):
        """
        Unit test for different environment handling logic.
        """
        test_cases = [
            {
                'environment': 'development',
                'auth_enabled': 'false',
                'auth_url': None,
                'should_pass': True,
                'should_be_critical': False
            },
            {
                'environment': 'testing',
                'auth_enabled': 'false', 
                'auth_url': None,
                'should_pass': True,
                'should_be_critical': False
            },
            {
                'environment': 'staging',
                'auth_enabled': 'true',
                'auth_url': None,
                'should_pass': False,
                'should_be_critical': True
            },
            {
                'environment': 'production',
                'auth_enabled': 'true',
                'auth_url': None,
                'should_pass': False,
                'should_be_critical': True
            }
        ]
        
        for case in test_cases:
            with self.subTest(environment=case['environment']):
                env_vars = {
                    'AUTH_SERVICE_ENABLED': case['auth_enabled']
                }
                if case['auth_url']:
                    env_vars['AUTH_SERVICE_URL'] = case['auth_url']
                
                validator = self.create_validator_with_environment(env_vars, case['environment'])
                
                await validator._validate_auth_service_url()
                
                self.assertEqual(len(validator.validation_results), 1)
                result = validator.validation_results[0]
                
                if case['should_pass']:
                    self.assertTrue(result.valid, f"Should pass for {case['environment']}")
                else:
                    self.assertFalse(result.valid, f"Should fail for {case['environment']}")
                
                self.assertEqual(result.is_critical, case['should_be_critical'],
                               f"Critical flag incorrect for {case['environment']}")

    async def test_validate_auth_service_url_auth_enabled_string_variations(self):
        """
        Unit test for different AUTH_SERVICE_ENABLED string values.
        """
        auth_enabled_values = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', False),  # Only 'true' should be considered true
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('', False),
            (None, False)  # Default when not set
        ]
        
        for auth_value, expected_enabled in auth_enabled_values:
            with self.subTest(auth_enabled=auth_value):
                env_vars = {}
                if auth_value is not None:
                    env_vars['AUTH_SERVICE_ENABLED'] = auth_value
                # No AUTH_SERVICE_URL
                
                validator = self.create_validator_with_environment(env_vars, "development")
                
                await validator._validate_auth_service_url()
                
                self.assertEqual(len(validator.validation_results), 1)
                result = validator.validation_results[0]
                
                if expected_enabled:
                    # Auth enabled but no URL - should fail
                    self.assertFalse(result.valid)
                    self.assertEqual(result.error, "AUTH_SERVICE_URL not configured")
                else:
                    # Auth disabled in development - should pass
                    self.assertTrue(result.valid)

    async def test_validate_auth_service_url_localhost_development(self):
        """
        Unit test for localhost URLs in development.
        """
        localhost_urls = [
            'http://localhost:8001',
            'http://127.0.0.1:8001',
            'https://localhost:8001'
        ]
        
        for url in localhost_urls:
            with self.subTest(url=url):
                env_vars = {
                    'AUTH_SERVICE_URL': url,
                    'AUTH_SERVICE_ENABLED': 'true'
                }
                
                validator = self.create_validator_with_environment(env_vars, "development")
                
                await validator._validate_auth_service_url()
                
                self.assertEqual(len(validator.validation_results), 1)
                result = validator.validation_results[0]
                self.assertTrue(result.valid, f"Localhost URL should be valid in development: {url}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])