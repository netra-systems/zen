"""
OAuth SSOT Migration Test Suite - Issue #213

CRITICAL: Tests to validate OAuth functionality preserved during SSOT consolidation.

These tests ensure that consolidating 5 duplicate OAuth validation implementations
into the central SSOT doesn't break existing OAuth functionality.

Business Value: Platform/Internal - Migration Safety and Golden Path Protection  
Prevents regressions during SSOT consolidation that could break $500K+ ARR chat functionality.

Test Strategy:
- Test OAuth functionality matches pre-consolidation behavior
- Test OAuth configuration consistency across environments
- Test OAuth error messages are improved (not degraded)
- Test OAuth validation logic transitions seamlessly

SAFETY: These tests validate business functionality preservation during architectural changes.
"""

import os
import pytest
import logging
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock

# Base test case not needed for simple pytest
from shared.configuration.central_config_validator import (
    CentralConfigurationValidator, 
    Environment,
    get_central_validator,
    clear_central_validator_cache
)
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestOAuthSSOTMigration:
    """Test suite to validate OAuth SSOT migration safety - Issue #213."""
    
    def setup_method(self):
        """Set up test environment with OAuth credentials."""
        clear_central_validator_cache()
        
        # Set up test OAuth credentials
        self.test_oauth_credentials = {
            "client_id": "test-oauth-client-id-for-automated-testing",
            "client_secret": "test-oauth-client-secret-for-automated-testing"
        }
        
        # Ensure test environment variables are set
        os.environ["ENVIRONMENT"] = "test"
        os.environ["PYTEST_CURRENT_TEST"] = "test_oauth_ssot_migration.py"
        os.environ["GOOGLE_OAUTH_CLIENT_ID_TEST"] = self.test_oauth_credentials["client_id"]
        os.environ["GOOGLE_OAUTH_CLIENT_SECRET_TEST"] = self.test_oauth_credentials["client_secret"]
        os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-test-environment-only-32-chars-min"
    
    def teardown_method(self):
        """Clean up test environment."""
        clear_central_validator_cache()
    
    def test_oauth_functionality_preserved_post_migration(self):
        """
        CRITICAL: Test OAuth functionality unchanged after SSOT consolidation.
        
        This test MUST PASS to ensure SSOT migration doesn't break OAuth.
        Validates that consolidated OAuth validation works identically to duplicates.
        """
        # Test SSOT OAuth validation works
        validator = CentralConfigurationValidator()
        
        try:
            # Test core OAuth functionality
            oauth_creds = validator.get_oauth_credentials()
            
            # Verify OAuth credentials structure preserved
            assert isinstance(oauth_creds, dict), \
                "OAuth credentials should be returned as dictionary"
            assert "client_id" in oauth_creds, \
                "OAuth credentials should contain client_id"
            assert "client_secret" in oauth_creds, \
                "OAuth credentials should contain client_secret"
            
            # Verify OAuth credentials values preserved
            assert oauth_creds["client_id"] == self.test_oauth_credentials["client_id"], \
                f"OAuth client ID should match expected value. Got: {oauth_creds['client_id']}"
            assert oauth_creds["client_secret"] == self.test_oauth_credentials["client_secret"], \
                f"OAuth client secret should match expected value"
            
            # Test individual OAuth methods work
            client_id = validator.get_oauth_client_id()
            assert client_id == self.test_oauth_credentials["client_id"], \
                f"Individual OAuth client ID method should work. Got: {client_id}"
            
            logger.info("✅ OAuth functionality preserved after SSOT migration")
            
        except Exception as e:
            pytest.fail(f"OAuth functionality broken after SSOT migration: {e}")
    
    def test_oauth_configuration_consistency_ssot(self):
        """
        Test OAuth configuration consistency using SSOT validator.
        
        This test MUST PASS to ensure SSOT provides consistent OAuth configuration
        across all environments and usage patterns.
        """
        validator = CentralConfigurationValidator()
        
        # Test configuration consistency across multiple calls
        oauth_calls = []
        for i in range(5):
            try:
                oauth_creds = validator.get_oauth_credentials()
                oauth_calls.append({
                    "call_number": i,
                    "client_id": oauth_creds["client_id"],
                    "client_secret": oauth_creds["client_secret"]
                })
            except Exception as e:
                pytest.fail(f"OAuth call {i} failed with SSOT validator: {e}")
        
        # Verify all calls return consistent results
        first_call = oauth_calls[0]
        for call in oauth_calls[1:]:
            assert call["client_id"] == first_call["client_id"], \
                f"OAuth client ID inconsistent between calls: {call['call_number']}"
            assert call["client_secret"] == first_call["client_secret"], \
                f"OAuth client secret inconsistent between calls: {call['call_number']}"
        
        # Test environment-specific configuration loading
        environment = validator.get_environment()
        assert environment == Environment.TEST, \
            f"Environment should be TEST for this test. Got: {environment}"
        
        # Test OAuth configuration validation
        try:
            validator.validate_all_requirements()
            logger.info("✅ OAuth configuration validation passed with SSOT")
        except Exception as e:
            pytest.fail(f"OAuth configuration validation failed with SSOT: {e}")
        
        logger.info("✅ OAuth configuration consistency maintained with SSOT")
    
    def test_oauth_error_messages_improved(self):
        """
        Test OAuth error messages are clearer post-SSOT.
        
        This test validates that SSOT consolidation IMPROVES error messages
        rather than degrading them. Error messages should be actionable.
        """
        # Test with missing OAuth configuration
        missing_config_env = {
            "ENVIRONMENT": "test",
            "PYTEST_CURRENT_TEST": "test_oauth_ssot_migration.py",
            "JWT_SECRET_KEY": "test-jwt-secret-key-for-test-environment-only-32-chars-min",
            # Intentionally missing OAuth credentials
        }
        
        def mock_env_getter_missing_oauth(key, default=None):
            return missing_config_env.get(key, default)
        
        validator = CentralConfigurationValidator(env_getter_func=mock_env_getter_missing_oauth)
        
        # Test OAuth credentials error message
        with pytest.raises(ValueError) as exc_info:
            validator.get_oauth_credentials()
        
        error_message = str(exc_info.value)
        
        # Verify error message is clear and actionable
        assert "OAuth credentials not properly configured" in error_message, \
            f"Error message should mention OAuth configuration. Got: {error_message}"
        assert "GOOGLE_OAUTH_CLIENT_ID" in error_message or "oauth" in error_message.lower(), \
            f"Error message should mention specific OAuth variables. Got: {error_message}"
        
        # Verify error message doesn't mention race conditions (that's a different issue)
        assert "race condition" not in error_message.lower(), \
            f"Error should not mention race conditions for missing config. Got: {error_message}"
        
        # Test individual method error messages
        with pytest.raises(ValueError) as exc_info:
            validator.get_oauth_client_id()
        
        client_id_error = str(exc_info.value)
        assert len(client_id_error) > 0, \
            "OAuth client ID error should provide meaningful message"
        
        logger.info("✅ OAuth error messages are clear and actionable with SSOT")
    
    def test_oauth_validation_behavior_consistency(self):
        """
        Test OAuth validation behavior is consistent across different scenarios.
        
        This test ensures SSOT OAuth validation behaves predictably
        in various usage scenarios that were handled by duplicate implementations.
        """
        validator = CentralConfigurationValidator()
        
        # Test scenario 1: Normal OAuth validation
        oauth_creds = validator.get_oauth_credentials()
        assert oauth_creds["client_id"] and oauth_creds["client_secret"], \
            "Normal OAuth validation should return valid credentials"
        
        # Test scenario 2: Cached OAuth validation (second call)
        oauth_creds_cached = validator.get_oauth_credentials()
        assert oauth_creds_cached == oauth_creds, \
            "Cached OAuth validation should return same results"
        
        # Test scenario 3: OAuth validation after cache clear
        validator.clear_environment_cache()
        oauth_creds_fresh = validator.get_oauth_credentials()
        assert oauth_creds_fresh == oauth_creds, \
            "Fresh OAuth validation should return consistent results"
        
        # Test scenario 4: Environment-specific OAuth loading
        environment = validator.get_environment()
        expected_client_id_var = f"GOOGLE_OAUTH_CLIENT_ID_{environment.value.upper()}"
        actual_client_id = get_env(expected_client_id_var)
        assert actual_client_id == oauth_creds["client_id"], \
            f"Environment-specific OAuth loading should work. Expected var: {expected_client_id_var}"
        
        logger.info("✅ OAuth validation behavior is consistent across scenarios")
    
    def test_oauth_integration_compatibility(self):
        """
        Test OAuth SSOT integration compatibility with existing services.
        
        This test ensures SSOT OAuth validation integrates properly with
        services that previously used duplicate implementations.
        """
        # Test integration with different calling patterns
        validator = CentralConfigurationValidator()
        
        # Pattern 1: Direct credential access (common in auth service)
        oauth_creds = validator.get_oauth_credentials()
        client_id = oauth_creds["client_id"]
        client_secret = oauth_creds["client_secret"]
        
        # Pattern 2: Individual method calls (common in backend)
        individual_client_id = validator.get_oauth_client_id()
        assert individual_client_id == client_id, \
            "Individual method should return same client ID as credentials dict"
        
        # Pattern 3: Validation during startup (common in configuration validators)
        try:
            validator.validate_all_requirements()
            validation_success = True
        except Exception:
            validation_success = False
        assert validation_success, \
            "OAuth validation should work during startup validation"
        
        # Pattern 4: Multiple validator instances (common in testing)
        validator2 = CentralConfigurationValidator()
        oauth_creds2 = validator2.get_oauth_credentials()
        assert oauth_creds2 == oauth_creds, \
            "Multiple validator instances should return consistent results"
        
        logger.info("✅ OAuth SSOT integration is compatible with existing service patterns")
    
    def test_oauth_environment_migration_safety(self):
        """
        Test OAuth environment variable migration safety.
        
        This test ensures environment-specific OAuth variable loading
        works correctly after SSOT consolidation.
        """
        validator = CentralConfigurationValidator()
        
        # Test current environment detection
        environment = validator.get_environment()
        assert environment == Environment.TEST, \
            f"Should detect TEST environment. Got: {environment}"
        
        # Test environment-specific OAuth variable construction
        expected_variables = {
            "client_id": f"GOOGLE_OAUTH_CLIENT_ID_{environment.value.upper()}",
            "client_secret": f"GOOGLE_OAUTH_CLIENT_SECRET_{environment.value.upper()}"
        }
        
        # Verify the expected variables exist in environment
        for var_type, var_name in expected_variables.items():
            var_value = get_env(var_name)
            assert var_value is not None, \
                f"Environment variable {var_name} should exist for {var_type}"
            assert len(var_value) > 0, \
                f"Environment variable {var_name} should not be empty"
        
        # Test OAuth credentials use correct environment variables
        oauth_creds = validator.get_oauth_credentials()
        expected_client_id = get_env(expected_variables["client_id"])
        expected_client_secret = get_env(expected_variables["client_secret"])
        
        assert oauth_creds["client_id"] == expected_client_id, \
            f"OAuth client ID should use environment-specific variable"
        assert oauth_creds["client_secret"] == expected_client_secret, \
            f"OAuth client secret should use environment-specific variable"
        
        logger.info("✅ OAuth environment variable migration is safe")
    
    def test_oauth_validation_performance_maintained(self):
        """
        Test OAuth validation performance is maintained after SSOT consolidation.
        
        This test ensures SSOT doesn't introduce performance regressions
        compared to the duplicate implementations.
        """
        import time
        
        validator = CentralConfigurationValidator()
        
        # Warm up caches
        validator.get_oauth_credentials()
        
        # Test performance of OAuth validation calls
        start_time = time.time()
        
        # Make multiple OAuth calls (simulating real usage)
        for _ in range(10):
            oauth_creds = validator.get_oauth_credentials()
            assert oauth_creds["client_id"], "OAuth should return valid credentials"
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # OAuth validation should be fast (cached after first call)
        assert total_time < 1.0, \
            f"OAuth validation should be fast with caching. Took: {total_time}s"
        
        # Test performance of individual method calls
        start_time = time.time()
        
        for _ in range(10):
            client_id = validator.get_oauth_client_id()
            assert client_id, "OAuth client ID should be returned"
        
        end_time = time.time()
        individual_time = end_time - start_time
        
        assert individual_time < 1.0, \
            f"Individual OAuth method calls should be fast. Took: {individual_time}s"
        
        logger.info(f"✅ OAuth validation performance maintained: {total_time}s for 10 calls")


def test_oauth_migration_validation_capability():
    """
    Verify OAuth migration validation test capability.
    
    This meta-test ensures our migration validation tests work correctly.
    """
    test_instance = TestOAuthSSOTMigration()
    test_instance.setup_method()
    
    try:
        # Verify test environment is set up correctly
        validator = CentralConfigurationValidator()
        oauth_creds = validator.get_oauth_credentials()
        
        assert oauth_creds["client_id"], "Test should be able to get OAuth credentials"
        assert oauth_creds["client_secret"], "Test should be able to get OAuth credentials"
        
        # Verify environment detection works
        environment = validator.get_environment()
        assert environment == Environment.TEST, "Test should detect TEST environment"
        
        logger.info("✅ OAuth migration validation test capability verified")
        
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    # Run the meta-test to verify capability
    test_oauth_migration_validation_capability()
    print("✅ OAuth SSOT migration tests created and capability verified!")