"""
Integration Tests: Staging Configuration Validation Failures

CRITICAL MISSION: Demonstrate the localhost URL validation failures that exist in StagingConfig objects.

This test suite PROVES the bug exists by showing that:
1. StagingConfig objects contain localhost URLs even though validation rules forbid it
2. The validator correctly identifies these as violations
3. This is a genuine configuration bug that needs fixing

Business Impact: These tests should FAIL initially, proving the configuration bug exists.
After the bug is fixed, they should PASS, proving the solution works.

Test Strategy: Use real configuration loading with NO MOCKS - real integration testing.
"""

import pytest
import os
from typing import Dict, Any
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.schemas.config import StagingConfig
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator, validate_staging_config


@pytest.mark.integration
class TestStagingConfigurationValidationFailures(SSotBaseTestCase):
    """
    Integration tests that demonstrate the localhost validation failures in staging configuration.
    
    These tests use real configuration loading and should FAIL initially to prove the bugs exist.
    """

    def test_staging_config_contains_localhost_frontend_url_bug(self):
        """
        CRITICAL BUG TEST: Proves StagingConfig.frontend_url contains localhost when ENVIRONMENT=staging.
        
        This test should FAIL initially, proving the bug exists.
        Expected behavior: StagingConfig should NOT contain localhost URLs in staging environment.
        Actual behavior: StagingConfig DOES contain localhost URLs, violating staging environment rules.
        
        Bug Impact: Staging deployments fail because frontend tries to connect to localhost instead of
        proper staging URLs, breaking the entire user experience.
        """
        # Set up staging environment with realistic staging configuration
        staging_env_config = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',  # Staging project ID
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_staging',
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'staging-fernet-key-32-chars-base64-encoded-value',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
            'CLICKHOUSE_URL': 'https://staging.clickhouse.cloud/netra-staging',
            # NOTE: We don't set FRONTEND_URL explicitly - this tests the default behavior
        }
        
        # Apply staging environment configuration
        with self.temp_env_vars(**staging_env_config):
            # Create StagingConfig object using real configuration loading
            staging_config = StagingConfig()
            
            # Extract the frontend URL from the staging config
            frontend_url = staging_config.frontend_url
            
            # CRITICAL ASSERTION: This should FAIL initially, proving the bug
            # StagingConfig should NOT contain localhost URLs when ENVIRONMENT=staging
            assert 'localhost' not in frontend_url.lower(), (
                f"STAGING BUG DETECTED: StagingConfig.frontend_url contains localhost URL: {frontend_url}\n"
                f"In staging environment, frontend_url should be a proper staging URL like "
                f"'https://staging.netrasystems.ai' or 'https://netra-staging.web.app', NOT localhost.\n"
                f"This causes staging deployments to fail because frontend cannot connect to localhost."
            )
            
            # Additional validation: Should be a proper staging URL
            expected_staging_patterns = ['staging', 'netra-staging', '.web.app', 'netrasystems.ai']
            has_staging_pattern = any(pattern in frontend_url for pattern in expected_staging_patterns)
            
            assert has_staging_pattern, (
                f"STAGING BUG: frontend_url '{frontend_url}' doesn't contain expected staging patterns.\n"
                f"Expected patterns: {expected_staging_patterns}\n"
                f"Staging environment should use proper staging domain names."
            )
            
            # Log configuration details for debugging
            self.record_metric("staging_frontend_url", frontend_url)
            self.record_metric("contains_localhost", 'localhost' in frontend_url.lower())

    def test_staging_config_contains_localhost_api_base_url_bug(self):
        """
        CRITICAL BUG TEST: Proves StagingConfig.api_base_url contains localhost when ENVIRONMENT=staging.
        
        This test should FAIL initially, proving the bug exists.
        Expected behavior: StagingConfig API URLs should point to staging services, not localhost.
        Actual behavior: StagingConfig contains localhost API URLs, breaking service communication.
        
        Bug Impact: Services cannot communicate in staging because they try to connect to localhost
        instead of proper Cloud Run service URLs.
        """
        # Set up staging environment configuration
        staging_env_config = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',  # Staging project ID
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-postgres',
            'POSTGRES_USER': 'postgres', 
            'POSTGRES_PASSWORD': 'staging-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_staging',
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'staging-fernet-key-32-chars-base64-encoded-value',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
            'CLICKHOUSE_URL': 'https://staging.clickhouse.cloud/netra-staging',
            # NOTE: We don't set API_BASE_URL explicitly - this tests the default behavior
        }
        
        # Apply staging environment configuration
        with self.temp_env_vars(**staging_env_config):
            # Create StagingConfig object using real configuration loading
            staging_config = StagingConfig()
            
            # Extract the API base URL from the staging config
            api_base_url = staging_config.api_base_url
            
            # CRITICAL ASSERTION: This should FAIL initially, proving the bug
            # StagingConfig should NOT contain localhost URLs when ENVIRONMENT=staging
            assert 'localhost' not in api_base_url.lower(), (
                f"STAGING BUG DETECTED: StagingConfig.api_base_url contains localhost URL: {api_base_url}\n"
                f"In staging environment, api_base_url should be a proper Cloud Run URL like "
                f"'https://netra-backend-staging-xyz.a.run.app' or staging service URL, NOT localhost.\n"
                f"This causes service communication failures in staging deployments."
            )
            
            # Additional validation: Should be a proper staging URL
            expected_staging_patterns = ['staging', 'run.app', 'netra-staging', 'gcp']
            has_staging_pattern = any(pattern in api_base_url for pattern in expected_staging_patterns)
            
            assert has_staging_pattern, (
                f"STAGING BUG: api_base_url '{api_base_url}' doesn't contain expected staging patterns.\n"
                f"Expected patterns: {expected_staging_patterns}\n"
                f"Staging environment should use proper Cloud Run or staging service URLs."
            )
            
            # Log configuration details for debugging
            self.record_metric("staging_api_base_url", api_base_url)
            self.record_metric("contains_localhost", 'localhost' in api_base_url.lower())

    def test_staging_validator_correctly_identifies_localhost_violations(self):
        """
        VALIDATION TEST: Proves the staging validator correctly identifies localhost URLs as violations.
        
        This test should PASS, proving the validation system works correctly.
        The validator logic is correct - it's the StagingConfig defaults that are wrong.
        
        Purpose: Shows that we have working validation logic, but StagingConfig bypasses it.
        """
        # Set up staging environment with localhost URLs that should be flagged
        localhost_staging_config = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_staging',  
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'staging-fernet-key-32-chars-base64-encoded-value',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
            'CLICKHOUSE_URL': 'https://staging.clickhouse.cloud/netra-staging',
            
            # These should be flagged as violations by the validator
            'API_BASE_URL': 'http://localhost:8000',
            'FRONTEND_URL': 'http://localhost:3000',
            'AUTH_SERVICE_URL': 'http://localhost:8081',
            'REDIS_HOST': 'localhost',
        }
        
        # Apply the configuration with localhost URLs
        with self.temp_env_vars(**localhost_staging_config):
            # Run the staging configuration validator
            validator = StagingConfigurationValidator()
            validation_result = validator.validate()
            
            # The validator should correctly identify these as violations
            assert not validation_result.is_valid, (
                "VALIDATOR FAILURE: Staging validator should identify localhost URLs as invalid, "
                "but validation passed. This indicates the validator is not working properly."
            )
            
            # Check that specific localhost violations were detected
            localhost_errors = [error for error in validation_result.errors if 'localhost' in error.lower()]
            
            assert len(localhost_errors) > 0, (
                f"VALIDATOR FAILURE: Expected localhost validation errors, but got:\n"
                f"Errors: {validation_result.errors}\n"
                f"Warnings: {validation_result.warnings}\n"
                f"The validator should detect localhost URLs as violations in staging."
            )
            
            # Verify specific violations were detected
            expected_violations = ['API_BASE_URL', 'FRONTEND_URL', 'AUTH_SERVICE_URL', 'REDIS_HOST']
            detected_violations = []
            
            for error in localhost_errors:
                for violation in expected_violations:
                    if violation in error:
                        detected_violations.append(violation)
            
            assert len(detected_violations) >= 2, (
                f"VALIDATOR INCOMPLETE: Expected multiple localhost violations to be detected.\n"
                f"Detected violations: {detected_violations}\n"
                f"Expected violations: {expected_violations}\n"  
                f"Localhost errors found: {localhost_errors}"
            )
            
            # Log validation results for debugging
            self.record_metric("validation_errors_count", len(validation_result.errors))
            self.record_metric("localhost_errors_count", len(localhost_errors))
            self.record_metric("detected_violations", detected_violations)

    def test_staging_config_localhost_bug_with_unified_config_manager(self):
        """
        INTEGRATION TEST: Tests the localhost bug through UnifiedConfigManager integration.
        
        This test should FAIL initially, proving the bug exists at the integration level.
        Shows that even when using the unified configuration system, localhost URLs leak through.
        
        Bug Impact: The entire configuration system fails to enforce staging URL requirements.
        """
        # Set up staging environment
        staging_env_config = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_staging',
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'staging-fernet-key-32-chars-base64-encoded-value', 
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
            'CLICKHOUSE_URL': 'https://staging.clickhouse.cloud/netra-staging',
        }
        
        # Apply staging environment configuration
        with self.temp_env_vars(**staging_env_config):
            # Use UnifiedConfigurationManager to load configuration
            config_manager = UnifiedConfigurationManager(
                environment="staging",
                service_name="backend-staging", 
                enable_validation=True
            )
            
            # Get configuration values through the unified manager
            frontend_url = config_manager.get_str("frontend_url", "http://localhost:3010")  # Default from AppConfig
            api_base_url = config_manager.get_str("api_base_url", "http://localhost:8000")    # Default from AppConfig
            
            # CRITICAL ASSERTIONS: These should FAIL initially, proving the integration bug
            assert 'localhost' not in frontend_url.lower(), (
                f"UNIFIED CONFIG BUG: UnifiedConfigurationManager returns localhost frontend_url: {frontend_url}\n"
                f"Even with staging environment and validation enabled, localhost URLs leak through.\n"
                f"This proves the configuration system has systemic localhost URL issues."
            )
            
            assert 'localhost' not in api_base_url.lower(), (
                f"UNIFIED CONFIG BUG: UnifiedConfigurationManager returns localhost api_base_url: {api_base_url}\n"
                f"Even with staging environment and validation enabled, localhost URLs leak through.\n"
                f"This proves the configuration system has systemic localhost URL issues."
            )
            
            # Validate that configuration manager should enforce staging URLs
            config_status = config_manager.get_status()
            
            # The configuration system should prevent localhost URLs in staging
            assert config_status['validation_enabled'], (
                "Configuration validation should be enabled to prevent localhost URLs in staging"
            )
            
            # Log unified configuration details for debugging
            self.record_metric("unified_frontend_url", frontend_url)
            self.record_metric("unified_api_base_url", api_base_url)
            self.record_metric("validation_enabled", config_status['validation_enabled'])
            self.record_metric("environment", config_status['environment'])

    def test_prove_staging_defaults_override_environment_detection(self):
        """
        ROOT CAUSE TEST: Proves that StagingConfig class defaults override environment-specific logic.
        
        This test should FAIL initially, proving the root cause of the bug.
        The issue is that StagingConfig inherits defaults from AppConfig that contain localhost URLs,
        and these defaults are not overridden based on the staging environment.
        
        Root Cause: StagingConfig class should override frontend_url and api_base_url defaults
        to be proper staging URLs, but currently inherits localhost defaults from AppConfig.
        """
        # Set up clean staging environment (no URL overrides)
        clean_staging_config = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging-database-password-32-chars-long',
            'POSTGRES_DB': 'netra_staging',
            'JWT_SECRET_KEY': 'staging-jwt-secret-key-32-chars-minimum-length-required',
            'FERNET_KEY': 'staging-fernet-key-32-chars-base64-encoded-value',
            'SERVICE_SECRET': 'staging-service-secret-32-chars-minimum-required-length',
            'SERVICE_ID': 'netra-backend-staging',
            'CLICKHOUSE_URL': 'https://staging.clickhouse.cloud/netra-staging',
            # CRITICAL: No FRONTEND_URL or API_BASE_URL set - should use class defaults
        }
        
        # Remove any existing URL environment variables to test pure class defaults
        url_vars_to_clear = ['FRONTEND_URL', 'API_BASE_URL', 'AUTH_SERVICE_URL']
        for var in url_vars_to_clear:
            if var in clean_staging_config:
                del clean_staging_config[var]
        
        with self.temp_env_vars(**clean_staging_config):
            # Ensure URL variables are not set in environment
            env = get_env()
            for var in url_vars_to_clear:
                env.delete(var, "test_cleanup")
            
            # Create StagingConfig to test class defaults
            staging_config = StagingConfig()
            
            # Get the default values that the class provides
            class_frontend_default = staging_config.frontend_url
            class_api_default = staging_config.api_base_url
            
            # CRITICAL ASSERTIONS: These should FAIL, proving the root cause
            # Class defaults should be environment-aware, not hardcoded localhost
            
            assert 'localhost' not in class_frontend_default.lower(), (
                f"ROOT CAUSE IDENTIFIED: StagingConfig class default frontend_url is localhost: {class_frontend_default}\n"
                f"The StagingConfig class should override AppConfig defaults with proper staging URLs.\n"
                f"Instead, it inherits localhost defaults from AppConfig, causing staging deployment failures.\n"
                f"FIX NEEDED: StagingConfig.__init__ should set staging-appropriate URL defaults."
            )
            
            assert 'localhost' not in class_api_default.lower(), (
                f"ROOT CAUSE IDENTIFIED: StagingConfig class default api_base_url is localhost: {class_api_default}\n"
                f"The StagingConfig class should override AppConfig defaults with proper staging URLs.\n"
                f"Instead, it inherits localhost defaults from AppConfig, causing service communication failures.\n"
                f"FIX NEEDED: StagingConfig.__init__ should set staging-appropriate URL defaults."
            )
            
            # Document the root cause for fixing
            self.record_metric("root_cause_frontend_default", class_frontend_default)
            self.record_metric("root_cause_api_default", class_api_default) 
            self.record_metric("staging_config_class", staging_config.__class__.__name__)
            self.record_metric("environment_setting", staging_config.environment)
            
            # Verify environment is correctly set to staging
            assert staging_config.environment == "staging", (
                f"Environment detection failed: Expected 'staging', got '{staging_config.environment}'"
            )

    def test_document_expected_staging_url_patterns(self):
        """
        SPECIFICATION TEST: Documents what the correct staging URLs should look like.
        
        This test should PASS and serves as documentation for the expected staging URL patterns.
        Use this as a guide for implementing the fix.
        """
        # Expected staging URL patterns that should be used instead of localhost
        expected_staging_patterns = {
            'frontend_url_patterns': [
                'https://staging.netrasystems.ai',
                'https://netra-staging.web.app',
                'https://netra-frontend-staging-*.a.run.app',
                'https://staging-frontend.netra.dev'
            ],
            'api_base_url_patterns': [
                'https://netra-backend-staging-*.a.run.app',
                'https://api-staging.netrasystems.ai', 
                'https://staging-api.netra.dev',
                'https://backend-staging.netra.gcp.dev'
            ],
            'auth_service_url_patterns': [
                'https://netra-auth-staging-*.a.run.app',
                'https://auth-staging.netrasystems.ai',
                'https://staging-auth.netra.dev'
            ]
        }
        
        # Validate that these patterns don't contain localhost
        for category, patterns in expected_staging_patterns.items():
            for pattern in patterns:
                assert 'localhost' not in pattern.lower(), (
                    f"Expected staging pattern should not contain localhost: {pattern}"
                )
                
                # Should contain staging indicators
                staging_indicators = ['staging', 'run.app', '.dev', 'netra']
                has_indicator = any(indicator in pattern for indicator in staging_indicators)
                assert has_indicator, (
                    f"Expected staging pattern should contain staging indicators: {pattern}"
                )
        
        # Log expected patterns for reference during bug fixing
        self.record_metric("expected_frontend_patterns", expected_staging_patterns['frontend_url_patterns'])
        self.record_metric("expected_api_patterns", expected_staging_patterns['api_base_url_patterns'])
        self.record_metric("expected_auth_patterns", expected_staging_patterns['auth_service_url_patterns'])
        
        # This test should PASS - it documents expected behavior
        assert True, "Expected staging URL patterns documented successfully"