"""
Integration Test for GitHub Issue #259 - Staging Environment Secrets Validation Failure

This test reproduces the exact failure described in GitHub issue #259:
Missing staging test defaults for critical secrets in dev_launcher/isolated_environment.py

Business Value: Platform/Internal - Configuration validation prevents deployment failures
Strategic Impact: Catches configuration gaps before they cause $500K+ ARR service outages

EXPECTED BEHAVIOR: This test should FAIL before remediation due to missing staging defaults.
AFTER REMEDIATION: Should PASS when staging defaults are added to isolated_environment.py.

ROOT CAUSE: CentralConfigurationValidator requires 4 staging-specific secrets that are not
provided as test defaults in the IsolatedEnvironment test configuration.
"""

import pytest
from unittest.mock import patch
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.configuration.central_config_validator import CentralConfigurationValidator, Environment


class TestStagingSecretsValidationFailure(BaseTestCase):
    """Test that reproduces the exact staging secrets validation failure from GitHub #259."""

    def setup_method(self):
        """Setup isolated test environment for staging validation."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        
        # CRITICAL: Clear all environment variables to ensure clean test state
        self.env.clear()
        
        # Set staging environment (triggers the validation failure)
        self.env.set("ENVIRONMENT", "staging", "test_setup")
        
        # Initialize validator with staging environment
        self.validator = CentralConfigurationValidator()

    def teardown_method(self):
        """Clean up test environment."""
        self.env.reset_to_original()
        super().teardown_method()

    @pytest.mark.integration
    def test_staging_secrets_validation_failure(self):
        """
        TEST FOR GITHUB ISSUE #259: Missing staging test defaults cause validation failures.
        
        This test reproduces the exact issue where CentralConfigurationValidator fails
        because IsolatedEnvironment doesn't provide staging-specific test defaults.
        
        EXPECTED: This test should FAIL due to missing staging secrets.
        ROOT CAUSE: 4 missing secrets in staging test defaults.
        """
        # VERIFY: Environment is properly set to staging
        detected_env = self.validator.get_environment()
        assert detected_env == Environment.STAGING, f"Expected staging environment, got {detected_env}"
        
        # MAIN TEST: This should FAIL due to missing staging defaults
        # The validator requires these 4 staging secrets that aren't in test defaults:
        missing_secrets = [
            "JWT_SECRET_STAGING",
            "REDIS_PASSWORD", 
            "GOOGLE_OAUTH_CLIENT_ID_STAGING",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"
        ]
        
        # Verify each secret is missing (this confirms the root cause)
        for secret in missing_secrets:
            value = self.env.get(secret)
            assert value is None or value == "", f"Secret {secret} should be missing to reproduce issue #259, but found: {value}"
        
        # THE CORE FAILURE: validate_all_requirements() should fail
        with pytest.raises(ValueError) as exc_info:
            self.validator.validate_all_requirements()
        
        # VERIFY: Error message mentions the missing staging secrets
        error_message = str(exc_info.value)
        
        # Check that the error mentions staging environment
        assert "staging" in error_message.lower(), f"Error should mention staging environment: {error_message}"
        
        # Check that at least one of the missing secrets is mentioned in the error
        secrets_mentioned = [secret for secret in missing_secrets if secret in error_message]
        assert len(secrets_mentioned) > 0, (
            f"Error should mention at least one missing staging secret {missing_secrets}. "
            f"Actual error: {error_message}"
        )
        
        # BUSINESS IMPACT VALIDATION: Confirm this prevents startup
        assert "required" in error_message.lower() or "missing" in error_message.lower(), (
            f"Error should indicate required configuration is missing: {error_message}"
        )
        
        # SUCCESS: Test reproduces the exact GitHub #259 issue
        print(f"✅ ISSUE #259 REPRODUCED: {len(secrets_mentioned)} missing staging secrets detected")
        print(f"Missing secrets found in error: {secrets_mentioned}")
        print(f"Root cause confirmed: staging test defaults missing in isolated_environment.py")

    @pytest.mark.integration 
    def test_individual_staging_secret_validation_failures(self):
        """
        Test individual validation of each missing staging secret.
        
        This provides detailed diagnosis of which specific secrets are missing
        and helps confirm the exact scope of issue #259.
        """
        # Test each missing secret individually
        missing_secrets = {
            "JWT_SECRET_STAGING": "JWT authentication for staging environment",
            "REDIS_PASSWORD": "Redis authentication for staging/production", 
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "OAuth client ID for staging environment",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "OAuth client secret for staging environment"
        }
        
        failures = []
        
        for secret_name, description in missing_secrets.items():
            try:
                # Try to get validated config for this secret
                value = self.validator.get_validated_config(secret_name)
                
                # If we get here without exception, the secret was found (unexpected)
                if not value or value.strip() == "":
                    failures.append(f"{secret_name} is empty (expected for issue #259)")
                else:
                    # This would indicate the issue is already fixed
                    pytest.fail(f"UNEXPECTED: {secret_name} has value '{value}' - issue #259 may already be fixed")
                    
            except ValueError as e:
                # Expected failure due to missing secret
                failures.append(f"{secret_name}: {str(e)}")
                
        # VERIFY: All secrets should be missing (confirming issue #259)
        assert len(failures) == len(missing_secrets), (
            f"Expected all {len(missing_secrets)} secrets to be missing for issue #259. "
            f"Failures found: {len(failures)}\n" + "\n".join(failures)
        )
        
        # SUCCESS: All staging secrets are missing as expected
        print(f"✅ DETAILED DIAGNOSIS: All {len(failures)} staging secrets missing")
        for failure in failures:
            print(f"  - {failure}")

    @pytest.mark.integration
    def test_staging_environment_detection_accuracy(self):
        """
        Verify that environment detection correctly identifies staging context.
        
        This ensures the validation failure is due to missing secrets, not environment detection issues.
        """
        # VERIFY: Multiple ways of detecting staging environment all agree
        
        # Method 1: Direct environment variable
        env_var = self.env.get("ENVIRONMENT")
        assert env_var == "staging", f"ENVIRONMENT variable should be 'staging', got '{env_var}'"
        
        # Method 2: Validator environment detection
        detected_env = self.validator.get_environment()
        assert detected_env == Environment.STAGING, f"Validator should detect STAGING, got {detected_env}"
        
        # Method 3: Environment name normalization
        assert detected_env.value == "staging", f"Environment value should be 'staging', got '{detected_env.value}'"
        
        # SUCCESS: Environment detection is accurate
        print("✅ ENVIRONMENT DETECTION: Staging environment correctly identified by all methods")

    @pytest.mark.integration
    def test_test_defaults_availability_in_test_mode(self):
        """
        Verify that test defaults ARE available in test mode, but NOT in staging mode.
        
        This confirms that the issue is specifically about missing staging defaults,
        not a general problem with test defaults.
        """
        # Switch to test environment to verify test defaults work
        self.env.set("ENVIRONMENT", "test", "test_validation")
        
        # Clear validator cache to pick up environment change
        self.validator.clear_environment_cache()
        
        # VERIFY: Test environment is detected
        test_env = self.validator.get_environment()
        assert test_env == Environment.TEST, f"Should detect TEST environment, got {test_env}"
        
        # VERIFY: Test OAuth credentials ARE available in test mode
        test_oauth_id = self.env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
        test_oauth_secret = self.env.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST")
        
        assert test_oauth_id is not None, "Test OAuth client ID should be available in test mode"
        assert test_oauth_secret is not None, "Test OAuth client secret should be available in test mode"
        assert test_oauth_id.strip() != "", "Test OAuth client ID should not be empty"
        assert test_oauth_secret.strip() != "", "Test OAuth client secret should not be empty"
        
        # Switch back to staging to verify issue persists
        self.env.set("ENVIRONMENT", "staging", "staging_validation")
        self.validator.clear_environment_cache()
        
        # VERIFY: Staging OAuth credentials are NOT available
        staging_oauth_id = self.env.get("GOOGLE_OAUTH_CLIENT_ID_STAGING")
        staging_oauth_secret = self.env.get("GOOGLE_OAUTH_CLIENT_SECRET_STAGING")
        
        assert staging_oauth_id is None or staging_oauth_id.strip() == "", (
            f"Staging OAuth client ID should be missing to reproduce issue #259, got '{staging_oauth_id}'"
        )
        assert staging_oauth_secret is None or staging_oauth_secret.strip() == "", (
            f"Staging OAuth client secret should be missing to reproduce issue #259, got '{staging_oauth_secret}'"
        )
        
        # SUCCESS: Test defaults work in test mode but not staging mode
        print("✅ TEST DEFAULTS SCOPE: Available in test mode, missing in staging mode (confirms issue #259)")

    @pytest.mark.integration
    def test_comprehensive_staging_validation_failure_scenario(self):
        """
        Comprehensive test that validates the complete staging validation failure scenario.
        
        This test covers the full scope of issue #259 by testing all aspects of the
        staging environment configuration validation that should fail.
        """
        # SETUP: Ensure we're in staging environment with clean state
        assert self.validator.get_environment() == Environment.STAGING
        
        # TEST 1: OAuth validation should fail
        with pytest.raises(ValueError) as oauth_exc:
            self.validator.get_oauth_credentials()
        oauth_error = str(oauth_exc.value)
        assert any(oauth_term in oauth_error.lower() for oauth_term in ['oauth', 'client', 'staging']), (
            f"OAuth error should mention staging OAuth issue: {oauth_error}"
        )
        
        # TEST 2: JWT validation should fail
        with pytest.raises(ValueError) as jwt_exc:
            self.validator.get_jwt_secret()
        jwt_error = str(jwt_exc.value) 
        assert any(jwt_term in jwt_error.lower() for jwt_term in ['jwt', 'secret', 'staging']), (
            f"JWT error should mention staging JWT issue: {jwt_error}"
        )
        
        # TEST 3: Redis validation should fail
        with pytest.raises(ValueError) as redis_exc:
            self.validator.get_redis_credentials()
        redis_error = str(redis_exc.value)
        assert any(redis_term in redis_error.lower() for redis_term in ['redis', 'password']), (
            f"Redis error should mention Redis password issue: {redis_error}"
        )
        
        # TEST 4: Complete startup validation should fail
        with pytest.raises(ValueError) as startup_exc:
            self.validator.validate_startup_requirements()
        startup_error = str(startup_exc.value)
        assert "staging" in startup_error.lower(), (
            f"Startup validation error should mention staging: {startup_error}"
        )
        
        # SUCCESS: All validation scenarios fail as expected for issue #259
        print("✅ COMPREHENSIVE VALIDATION: All staging validation scenarios fail as expected")
        print(f"OAuth error: {oauth_error[:100]}...")
        print(f"JWT error: {jwt_error[:100]}...")
        print(f"Redis error: {redis_error[:100]}...")
        print(f"Startup error: {startup_error[:100]}...")

    @pytest.mark.integration
    def test_production_environment_similar_issue(self):
        """
        Test if production environment has similar missing defaults (scope expansion).
        
        This helps determine if issue #259 affects only staging or also production.
        """
        # Switch to production environment
        self.env.set("ENVIRONMENT", "production", "production_test")
        self.validator.clear_environment_cache()
        
        # VERIFY: Production environment is detected
        prod_env = self.validator.get_environment()
        assert prod_env == Environment.PRODUCTION, f"Should detect PRODUCTION environment, got {prod_env}"
        
        # TEST: Check if production has similar missing secrets
        production_secrets = [
            "JWT_SECRET_PRODUCTION",
            "REDIS_PASSWORD",  # This is shared between staging and production
            "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION", 
            "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"
        ]
        
        production_failures = []
        for secret in production_secrets:
            value = self.env.get(secret)
            if value is None or value.strip() == "":
                production_failures.append(secret)
        
        # ANALYSIS: Report production missing secrets for scope assessment
        if len(production_failures) > 0:
            print(f"⚠️ SCOPE EXPANSION: Production also missing {len(production_failures)} secrets")
            print(f"Production missing secrets: {production_failures}")
            print("Issue #259 likely affects production environment as well")
        else:
            print("✅ SCOPE LIMITED: Production secrets are available (issue #259 staging-specific)")
        
        # This test doesn't assert - it's diagnostic for scope assessment
        # The main issue #259 is about staging, but this helps understand the full scope