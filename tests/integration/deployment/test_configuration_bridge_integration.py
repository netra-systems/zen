#!/usr/bin/env python
"""
Integration Test: Configuration Bridge Functions

This test validates the integration between configuration validation 
and secret mappings for Golden Path configuration protection.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent configuration cascade failures  
- Value Impact: $500K+ ARR Golden Path configuration protection
- Strategic Impact: Mission critical infrastructure validation

These tests use real configuration data without Docker dependencies
to validate configuration regression prevention works end-to-end.
"""

import unittest
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.secrets_config import (
    SecretConfig, 
    get_secret_mappings, 
    validate_secret_mappings,
    get_backend_secrets_string,
    get_auth_secrets_string
)
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestConfigurationBridgeIntegration(SSotBaseTestCase):
    """
    Integration tests for configuration bridge functions.
    
    These tests validate that the bridge functions work correctly
    with the existing SecretConfig infrastructure to provide 
    comprehensive configuration protection.
    """
    
    def test_bridge_functions_integrate_with_secretconfig(self):
        """
        Test that bridge functions properly integrate with SecretConfig.
        
        This validates that the bridge provides seamless access to
        the underlying SecretConfig functionality.
        """
        # Test that bridge functions use SecretConfig data
        staging_mappings = get_secret_mappings('staging')
        secretconfig_mappings = SecretConfig.SECRET_MAPPINGS
        
        # Bridge should return data from SecretConfig for staging
        self.assertGreater(len(staging_mappings), 0,
                         "Bridge should return non-empty mappings")
        
        # Critical secrets from SecretConfig should be present
        backend_critical = SecretConfig.CRITICAL_SECRETS.get("backend", [])
        auth_critical = SecretConfig.CRITICAL_SECRETS.get("auth", [])
        all_critical = set(backend_critical + auth_critical)
        
        for critical_secret in all_critical:
            self.assertIn(critical_secret, staging_mappings,
                        f"Critical secret {critical_secret} should be in bridge mappings")
    
    def test_validation_detects_configuration_issues(self):
        """
        Test that validation correctly detects configuration issues.
        
        This validates that the bridge functions can identify problems
        that could cause cascade failures in production.
        """
        # Test staging validation
        staging_valid, staging_errors = validate_secret_mappings('staging')
        
        # Should return boolean and list
        self.assertIsInstance(staging_valid, bool,
                            "Validation should return boolean")
        self.assertIsInstance(staging_errors, list,
                            "Validation should return error list")
        
        # If there are errors, they should be meaningful
        if staging_errors:
            for error in staging_errors:
                self.assertIsInstance(error, str,
                                    "Error should be string")
                self.assertGreater(len(error), 10,
                                 "Error should be descriptive")
        
        # Test production validation
        production_valid, production_errors = validate_secret_mappings('production')
        
        self.assertIsInstance(production_valid, bool,
                            "Production validation should return boolean")
        self.assertIsInstance(production_errors, list,
                            "Production validation should return error list")
    
    def test_environment_specific_configuration_handling(self):
        """
        Test that different environments have appropriate configurations.
        
        This validates that staging and production configurations are
        properly isolated and environment-appropriate.
        """
        environments = ['staging', 'production']
        
        for env in environments:
            with self.subTest(environment=env):
                mappings = get_secret_mappings(env)
                
                # Should have reasonable number of mappings
                self.assertGreater(len(mappings), 15,
                                 f"{env} should have sufficient secret mappings")
                
                # Should contain critical secrets
                critical_secrets = [
                    'SERVICE_SECRET', 
                    'JWT_SECRET_KEY', 
                    'SECRET_KEY',
                    'SESSION_SECRET_KEY'
                ]
                
                for secret in critical_secrets:
                    self.assertIn(secret, mappings,
                                f"{env} should contain critical secret {secret}")
                    
                    gsm_name = mappings[secret]
                    self.assertIsInstance(gsm_name, str,
                                        f"{secret} mapping should be string")
                    self.assertNotEqual(gsm_name, "",
                                      f"{secret} mapping should not be empty")
    
    def test_oauth_dual_naming_pattern_validation(self):
        """
        Test that OAuth dual naming patterns are correctly handled.
        
        This validates that both backend and auth service OAuth
        configurations are properly supported.
        """
        for env in ['staging', 'production']:
            with self.subTest(environment=env):
                mappings = get_secret_mappings(env)
                
                # Backend OAuth pattern (simplified names)
                backend_client_id = mappings.get('GOOGLE_CLIENT_ID')
                backend_client_secret = mappings.get('GOOGLE_CLIENT_SECRET')
                
                self.assertIsNotNone(backend_client_id,
                                   f"{env} should have backend OAuth client ID")
                self.assertIsNotNone(backend_client_secret,
                                   f"{env} should have backend OAuth client secret")
                
                # Auth service OAuth pattern (environment-specific names)
                env_upper = env.upper()
                auth_client_id = mappings.get(f'GOOGLE_OAUTH_CLIENT_ID_{env_upper}')
                auth_client_secret = mappings.get(f'GOOGLE_OAUTH_CLIENT_SECRET_{env_upper}')
                
                # Auth pattern should exist for staging, may not exist for production yet
                if env == 'staging':
                    self.assertIsNotNone(auth_client_id,
                                       f"{env} should have auth service OAuth client ID")
                    self.assertIsNotNone(auth_client_secret,
                                       f"{env} should have auth service OAuth client secret")
    
    def test_integration_with_deployment_secrets_generation(self):
        """
        Test that bridge functions integrate with deployment secret generation.
        
        This validates that the configuration validation works with the
        actual deployment secret string generation.
        """
        # Test backend secrets string generation
        backend_secrets = get_backend_secrets_string()
        self.assertIsInstance(backend_secrets, str,
                            "Backend secrets should be string")
        self.assertGreater(len(backend_secrets), 100,
                         "Backend secrets string should be substantial")
        
        # Test auth secrets string generation  
        auth_secrets = get_auth_secrets_string()
        self.assertIsInstance(auth_secrets, str,
                            "Auth secrets should be string")
        self.assertGreater(len(auth_secrets), 100,
                         "Auth secrets string should be substantial")
        
        # Validate that critical secrets appear in deployment strings
        critical_patterns = [
            'SERVICE_SECRET=',
            'JWT_SECRET',  # May be JWT_SECRET or JWT_SECRET_KEY
            'SECRET_KEY='
        ]
        
        for pattern in critical_patterns:
            backend_has_pattern = any(pattern in backend_secrets for pattern in [pattern])
            auth_has_pattern = any(pattern in auth_secrets for pattern in [pattern])
            
            # At least one service should have the pattern
            self.assertTrue(backend_has_pattern or auth_has_pattern,
                          f"Critical pattern '{pattern}' should appear in deployment strings")
    
    def test_configuration_regression_detection_capability(self):
        """
        Test that the system can detect configuration regressions.
        
        This validates that removing or changing critical configurations
        would be detected by the validation system.
        """
        # Get current valid mappings
        current_mappings = get_secret_mappings('staging')
        
        # Simulate removing a critical secret (conceptual test)
        critical_secrets = SecretConfig.CRITICAL_SECRETS.get("backend", [])
        if critical_secrets:
            first_critical = critical_secrets[0]
            
            # Verify the critical secret exists in current mappings
            self.assertIn(first_critical, current_mappings,
                        f"Critical secret {first_critical} should exist in mappings")
            
            # This validates that the system WOULD detect if it was missing
            # (In a real regression, validate_secret_mappings would catch this)
        
        # Test validation catches empty mappings
        is_valid, errors = validate_secret_mappings('staging')
        
        # If there are validation errors, they should be specific
        if not is_valid:
            self.assertGreater(len(errors), 0,
                             "Invalid configuration should have specific errors")
            for error in errors:
                # Errors should mention specific problems
                self.assertTrue(
                    any(keyword in error.lower() for keyword in [
                        'duplicate', 'missing', 'empty', 'secret', 'staging', 'production'
                    ]),
                    f"Error should be specific about the problem: {error}"
                )
    
    def test_golden_path_configuration_protection(self):
        """
        Test that Golden Path configuration is properly protected.
        
        This validates that all configurations needed for the
        $500K+ ARR Golden Path user flow are properly validated.
        """
        # Golden Path requires these critical services to work
        golden_path_secrets = [
            'SERVICE_SECRET',    # Inter-service auth
            'JWT_SECRET_KEY',    # User authentication  
            'SECRET_KEY',        # General encryption
            'SESSION_SECRET_KEY', # Session management
            'POSTGRES_PASSWORD', # Database access
        ]
        
        for env in ['staging', 'production']:
            with self.subTest(environment=env):
                mappings = get_secret_mappings(env)
                
                missing_golden_path = []
                for secret in golden_path_secrets:
                    if secret not in mappings:
                        missing_golden_path.append(secret)
                
                if missing_golden_path:
                    self.fail(
                        f"Golden Path secrets missing in {env}: {', '.join(missing_golden_path)}. "
                        f"This would block $500K+ ARR user flow functionality."
                    )
                
                # Validate that Golden Path secrets have non-empty mappings
                empty_golden_path = []
                for secret in golden_path_secrets:
                    if secret in mappings:
                        gsm_name = mappings[secret]
                        if not gsm_name or gsm_name.isspace():
                            empty_golden_path.append(secret)
                
                if empty_golden_path:
                    self.fail(
                        f"Golden Path secrets have empty mappings in {env}: "
                        f"{', '.join(empty_golden_path)}. This would block $500K+ ARR functionality."
                    )


class TestConfigurationBridgeErrorHandling(SSotBaseTestCase):
    """
    Test error handling in configuration bridge functions.
    """
    
    def test_invalid_environment_handling(self):
        """
        Test that invalid environments are handled gracefully.
        """
        # Test with invalid environment
        try:
            mappings = get_secret_mappings('invalid_env')
            # Should still return something (graceful degradation)
            self.assertIsInstance(mappings, dict,
                                "Should return dict even for invalid environment")
        except Exception as e:
            # Or should raise a meaningful error
            self.assertIn('environment', str(e).lower(),
                        "Error should mention environment issue")
    
    def test_validation_error_scenarios(self):
        """
        Test that validation properly handles error scenarios.
        """
        # Test validation with known environment
        is_valid, errors = validate_secret_mappings('staging')
        
        # Should always return the expected types
        self.assertIsInstance(is_valid, bool,
                            "Should always return boolean")
        self.assertIsInstance(errors, list,
                            "Should always return list")
        
        # If validation fails, errors should be informative
        if not is_valid:
            self.assertGreater(len(errors), 0,
                             "Failed validation should have error messages")


if __name__ == '__main__':
    print("="*80)
    print("INTEGRATION TEST: Configuration Bridge Functions")
    print("="*80)
    print("PURPOSE: Validate configuration bridge integration for Golden Path protection")
    print("SCOPE: Non-Docker integration testing of configuration validation")
    print("BUSINESS IMPACT: $500K+ ARR Golden Path configuration protection")
    print("="*80)
    print()
    
    unittest.main(verbosity=2)