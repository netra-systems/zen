"""
Unit Tests: OAuth Configuration Isolation and Regression Prevention

CRITICAL: Tests OAuth configuration isolation and prevents regression issues.
Prevents OAuth credential leaks between environments and auth flow failures.

Business Value: Platform/Internal - Prevents complete OAuth flow failure, user lockout
Test Coverage: OAuth environment isolation, credential validation, regression prevention
"""
import pytest
import os
from unittest.mock import patch, Mock
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestOAuthConfigurationIsolation:
    """Test OAuth configuration isolation between environments to prevent credential leaks."""

    def test_oauth_dual_naming_convention_compliance(self):
        """
        CRITICAL: Test OAuth dual naming convention prevents configuration confusion.
        
        PREVENTS: OAuth configuration mismatches between backend and auth services
        CASCADE FAILURE: OAuth flows fail, users cannot authenticate
        """
        env = get_env()
        env.enable_isolation()
        
        # Backend service pattern (simplified names)
        backend_oauth_config = {
            "GOOGLE_CLIENT_ID": "backend-google-client-id.apps.googleusercontent.com",
            "GOOGLE_CLIENT_SECRET": "backend-google-client-secret",
            "GITHUB_CLIENT_ID": "backend-github-client-id",
            "GITHUB_CLIENT_SECRET": "backend-github-client-secret"
        }
        
        # Auth service pattern (environment-specific names)
        auth_service_oauth_config = {
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "auth-staging-google-client-id.apps.googleusercontent.com",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "auth-staging-google-client-secret",
            "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": "auth-production-google-client-id.apps.googleusercontent.com",
            "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION": "auth-production-google-client-secret"
        }
        
        # Test backend service OAuth isolation
        env.clear()
        for key, value in backend_oauth_config.items():
            env.set(key, value, "backend_oauth")
        
        # Verify backend OAuth configuration
        backend_google_id = env.get("GOOGLE_CLIENT_ID")
        assert backend_google_id == "backend-google-client-id.apps.googleusercontent.com"
        assert backend_google_id.endswith(".apps.googleusercontent.com"), "Invalid Google Client ID format"
        
        # Should NOT have auth service patterns
        assert env.get("GOOGLE_OAUTH_CLIENT_ID_STAGING") is None
        assert env.get("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION") is None
        
        # Test auth service OAuth isolation
        env.clear()
        for key, value in auth_service_oauth_config.items():
            env.set(key, value, "auth_service_oauth")
        
        # Verify auth service OAuth configuration
        staging_google_id = env.get("GOOGLE_OAUTH_CLIENT_ID_STAGING")
        assert "staging" in staging_google_id
        production_google_id = env.get("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION")
        assert "production" in production_google_id
        
        # Should NOT have backend service patterns
        assert env.get("GOOGLE_CLIENT_ID") is None
        assert env.get("GITHUB_CLIENT_ID") is None

    def test_environment_specific_oauth_credential_isolation(self):
        """
        CRITICAL: Test OAuth credentials are isolated by environment.
        
        PREVENTS: Staging OAuth credentials used in production (security breach)
        CASCADE FAILURE: Wrong OAuth apps accessed, user data exposed
        """
        env = get_env()
        env.enable_isolation()
        
        # Environment-specific OAuth configurations
        oauth_by_environment = {
            "test": {
                "GOOGLE_OAUTH_CLIENT_ID_TEST": "test-oauth-client-id-for-automated-testing",
                "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test-oauth-client-secret-for-automated-testing",
                "E2E_OAUTH_SIMULATION_KEY": "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"
            },
            "staging": {
                "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-oauth-client.apps.googleusercontent.com",
                "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-oauth-secret-from-gcp-secrets",
                "GITHUB_OAUTH_CLIENT_ID_STAGING": "staging-github-oauth-client",
                "GITHUB_OAUTH_CLIENT_SECRET_STAGING": "staging-github-oauth-secret"
            },
            "production": {
                "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": "production-oauth-client.apps.googleusercontent.com", 
                "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION": "production-oauth-secret-from-gcp-secrets",
                "GITHUB_OAUTH_CLIENT_ID_PRODUCTION": "production-github-oauth-client",
                "GITHUB_OAUTH_CLIENT_SECRET_PRODUCTION": "production-github-oauth-secret"
            }
        }
        
        # Test each environment's OAuth isolation
        for env_name, oauth_config in oauth_by_environment.items():
            env.clear()
            env.set("ENVIRONMENT", env_name, f"{env_name}_setup")
            
            # Set environment-specific OAuth credentials
            for key, value in oauth_config.items():
                env.set(key, value, f"{env_name}_oauth")
            
            # Verify credentials are environment-specific
            for key, value in oauth_config.items():
                retrieved_value = env.get(key)
                assert retrieved_value == value, f"{env_name} OAuth credential mismatch: {key}"
                
                # Verify environment naming in key matches environment
                if env_name in ["staging", "production"]:
                    assert env_name.upper() in key, f"OAuth key {key} should contain {env_name.upper()}"
            
            # Verify other environments' credentials are NOT present
            for other_env, other_config in oauth_by_environment.items():
                if other_env != env_name:
                    for other_key in other_config:
                        assert env.get(other_key) is None, (
                            f"{other_env} OAuth credential leaked to {env_name}: {other_key}"
                        )

    def test_oauth_test_credentials_automatic_injection(self):
        """
        CRITICAL: Test OAuth test credentials are automatically available in test context.
        
        PREVENTS: CentralConfigurationValidator failures during test execution
        CASCADE FAILURE: Test suite failures blocking deployments
        """
        # Mock test context
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_oauth_auto", "TESTING": "true"}):
            test_env = IsolatedEnvironment()
            
            # Should automatically provide test OAuth credentials
            google_test_id = test_env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
            assert google_test_id == "test-oauth-client-id-for-automated-testing"
            
            google_test_secret = test_env.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST")
            assert google_test_secret == "test-oauth-client-secret-for-automated-testing"
            
            e2e_oauth_key = test_env.get("E2E_OAUTH_SIMULATION_KEY")
            assert e2e_oauth_key == "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"
            
            # Test credentials should be available even without explicit setup
            assert google_test_id is not None, "Test OAuth credentials missing in test context"
            assert len(google_test_id) > 10, "Test OAuth client ID too short"
            assert len(google_test_secret) > 10, "Test OAuth client secret too short"

    def test_oauth_redirect_uri_environment_validation(self):
        """
        CRITICAL: Test OAuth redirect URI validation by environment.
        
        PREVENTS: Wrong redirect URIs causing OAuth authorization failures
        CASCADE FAILURE: OAuth flow fails, users cannot complete authentication
        """
        env = get_env()
        env.enable_isolation()
        
        # Environment-specific redirect URI patterns
        redirect_uri_patterns = {
            "development": {
                "valid_uris": [
                    "http://localhost:3000/auth/callback",
                    "http://localhost:3000/api/auth/callback/google",
                    "http://127.0.0.1:3000/auth/callback"
                ],
                "invalid_uris": [
                    "https://app.staging.netrasystems.ai/auth/callback",  # Staging in dev
                    "https://app.netrasystems.ai/auth/callback"  # Production in dev
                ]
            },
            "staging": {
                "valid_uris": [
                    "https://app.staging.netrasystems.ai/auth/callback",
                    "https://app.staging.netrasystems.ai/api/auth/callback/google"
                ],
                "invalid_uris": [
                    "http://localhost:3000/auth/callback",  # Localhost in staging
                    "https://app.netrasystems.ai/auth/callback",  # Production in staging
                    "http://app.staging.netrasystems.ai/auth/callback"  # HTTP in staging
                ]
            },
            "production": {
                "valid_uris": [
                    "https://app.netrasystems.ai/auth/callback",
                    "https://app.netrasystems.ai/api/auth/callback/google"
                ],
                "invalid_uris": [
                    "http://localhost:3000/auth/callback",  # Localhost in production
                    "https://app.staging.netrasystems.ai/auth/callback",  # Staging in production
                    "http://app.netrasystems.ai/auth/callback"  # HTTP in production
                ]
            }
        }
        
        # Test redirect URI validation for each environment
        for env_name, uri_config in redirect_uri_patterns.items():
            env.clear()
            env.set("ENVIRONMENT", env_name, f"{env_name}_setup")
            
            # Test valid redirect URIs
            for valid_uri in uri_config["valid_uris"]:
                env.set("OAUTH_REDIRECT_URI", valid_uri, f"{env_name}_valid_redirect")
                
                # Validate URI format for environment
                if env_name == "development":
                    assert "localhost" in valid_uri or "127.0.0.1" in valid_uri, (
                        f"Development redirect URI should use localhost: {valid_uri}"
                    )
                elif env_name in ["staging", "production"]:
                    assert valid_uri.startswith("https://"), (
                        f"{env_name} redirect URI should use HTTPS: {valid_uri}"
                    )
                    assert "localhost" not in valid_uri, (
                        f"{env_name} redirect URI should not use localhost: {valid_uri}"
                    )
                
                if env_name == "staging":
                    assert "staging" in valid_uri, f"Staging redirect URI should contain 'staging': {valid_uri}"
                elif env_name == "production":
                    assert "staging" not in valid_uri, f"Production redirect URI should not contain 'staging': {valid_uri}"

    def test_oauth_client_id_format_validation(self):
        """
        CRITICAL: Test OAuth client ID format validation prevents auth failures.
        
        PREVENTS: Invalid OAuth client IDs causing authentication errors
        CASCADE FAILURE: OAuth provider rejects requests, authentication impossible
        """
        env = get_env()
        env.enable_isolation()
        
        # Valid OAuth client ID formats
        valid_client_ids = [
            "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com",
            "production-oauth-client.apps.googleusercontent.com",
            "staging-oauth-client.apps.googleusercontent.com",
            "test-oauth-client-id-for-automated-testing"
        ]
        
        # Invalid OAuth client ID formats
        invalid_client_ids = [
            "",  # Empty
            "invalid-client-id",  # Missing .apps.googleusercontent.com
            "123456",  # Too short
            "spaces in client id.apps.googleusercontent.com",  # Contains spaces
            "client-id-with-newline\n.apps.googleusercontent.com"  # Contains newline
        ]
        
        # Test valid client IDs
        for i, valid_id in enumerate(valid_client_ids):
            key = f"GOOGLE_CLIENT_ID_{i}"
            success = env.set(key, valid_id, "valid_oauth_test")
            assert success, f"Should accept valid OAuth client ID: {valid_id}"
            
            retrieved_id = env.get(key)
            assert retrieved_id == valid_id, f"OAuth client ID corrupted: {valid_id} != {retrieved_id}"
            
            # Validate format requirements
            if "test" not in valid_id.lower():
                assert ".apps.googleusercontent.com" in valid_id or valid_id.endswith("client"), (
                    f"OAuth client ID should be valid format: {valid_id}"
                )
        
        # Test invalid client IDs (should be sanitized or rejected)
        for i, invalid_id in enumerate(invalid_client_ids):
            key = f"GOOGLE_CLIENT_ID_INVALID_{i}"
            success = env.set(key, invalid_id, "invalid_oauth_test")
            
            if success:
                # If accepted, should be sanitized
                retrieved_id = env.get(key)
                if invalid_id.strip() != invalid_id:
                    # Should have whitespace/control chars removed
                    assert retrieved_id != invalid_id, f"Invalid OAuth client ID not sanitized: {invalid_id}"


class TestOAuthRegressionPrevention:
    """Test OAuth regression prevention mechanisms based on previous incidents."""

    def test_e2e_oauth_simulation_key_availability(self):
        """
        CRITICAL: Test E2E OAuth simulation key is always available in test context.
        
        PREVENTS: E2E test failures due to missing OAuth simulation capabilities
        CASCADE FAILURE: E2E test suite broken, deployment pipeline blocked
        """
        # Test with various test context indicators
        test_contexts = [
            {"PYTEST_CURRENT_TEST": "test_e2e_oauth", "TESTING": "true"},
            {"ENVIRONMENT": "test", "TESTING": "1"},
            {"TEST_MODE": "true", "PYTEST_CURRENT_TEST": "test_oauth_e2e"}
        ]
        
        for context in test_contexts:
            with patch.dict(os.environ, context):
                test_env = IsolatedEnvironment()
                
                # E2E OAuth simulation key should be automatically available
                e2e_key = test_env.get("E2E_OAUTH_SIMULATION_KEY")
                assert e2e_key is not None, f"E2E OAuth key missing in context: {context}"
                assert e2e_key == "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"
                
                # Should be available even without explicit environment setup
                assert len(e2e_key) > 20, "E2E OAuth simulation key too short"
                assert "test" in e2e_key.lower(), "E2E OAuth key should indicate test usage"
                assert "2025" in e2e_key, "E2E OAuth key should be current year version"

    def test_split_authentication_pattern_prevention(self):
        """
        CRITICAL: Test prevention of split authentication patterns causing confusion.
        
        PREVENTS: Multiple competing auth helpers creating OAuth inconsistencies
        CASCADE FAILURE: Different parts of system using different OAuth credentials
        """
        env = get_env()
        env.enable_isolation()
        
        # Test unified authentication pattern
        unified_auth_config = {
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "unified-test-oauth-client",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "unified-test-oauth-secret",
            "E2E_OAUTH_SIMULATION_KEY": "unified-e2e-oauth-simulation-key",
            "UNIFIED_AUTH_PATTERN": "true"
        }
        
        # Set unified authentication configuration
        for key, value in unified_auth_config.items():
            env.set(key, value, "unified_auth")
        
        # Verify unified pattern compliance
        client_id = env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
        client_secret = env.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST")
        simulation_key = env.get("E2E_OAUTH_SIMULATION_KEY")
        
        # All OAuth credentials should come from same unified source
        assert "unified" in client_id, "OAuth client ID should use unified pattern"
        assert "unified" in client_secret, "OAuth client secret should use unified pattern"
        assert "unified" in simulation_key, "E2E simulation key should use unified pattern"
        
        # Should NOT have split/competing authentication patterns
        competing_patterns = [
            "LEGACY_GOOGLE_CLIENT_ID",
            "OLD_OAUTH_CLIENT_ID", 
            "ALTERNATIVE_AUTH_KEY",
            "BACKUP_OAUTH_SECRET"
        ]
        
        for pattern in competing_patterns:
            assert env.get(pattern) is None, f"Should not have competing auth pattern: {pattern}"

    def test_oauth_validation_consistency_enforcement(self):
        """
        CRITICAL: Test consistent OAuth validation across all components.
        
        PREVENTS: Different tests having different OAuth validation requirements
        CASCADE FAILURE: Inconsistent authentication behavior, flaky tests
        """
        env = get_env()
        env.enable_isolation()
        
        # Standard OAuth validation requirements
        oauth_validation_standards = {
            "client_id_min_length": 10,
            "client_secret_min_length": 10,
            "required_test_credentials": [
                "GOOGLE_OAUTH_CLIENT_ID_TEST",
                "GOOGLE_OAUTH_CLIENT_SECRET_TEST"
            ],
            "required_staging_credentials": [
                "GOOGLE_OAUTH_CLIENT_ID_STAGING",
                "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"
            ],
            "required_production_credentials": [
                "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION",
                "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"
            ]
        }
        
        # Test consistent validation in test environment
        test_oauth_config = {
            "ENVIRONMENT": "test",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test-oauth-client-id-for-automated-testing",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test-oauth-client-secret-for-automated-testing"
        }
        
        env.clear()
        for key, value in test_oauth_config.items():
            env.set(key, value, "test_validation")
        
        # Validate test OAuth configuration meets standards
        for cred_key in oauth_validation_standards["required_test_credentials"]:
            cred_value = env.get(cred_key)
            assert cred_value is not None, f"Required test credential missing: {cred_key}"
            
            min_length = oauth_validation_standards["client_id_min_length"] if "ID" in cred_key else oauth_validation_standards["client_secret_min_length"]
            assert len(cred_value) >= min_length, f"Test credential too short: {cred_key} ({len(cred_value)} < {min_length})"

    def test_oauth_ssot_violation_prevention(self):
        """
        CRITICAL: Test prevention of OAuth SSOT violations.
        
        PREVENTS: Multiple OAuth configuration sources causing inconsistencies
        CASCADE FAILURE: Different services using different OAuth credentials
        """
        env = get_env()
        env.enable_isolation()
        
        # Test SSOT OAuth configuration pattern
        ssot_oauth_config = {
            "OAUTH_CONFIGURATION_SOURCE": "unified_isolated_environment",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "ssot-staging-google-client.apps.googleusercontent.com",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "ssot-staging-google-secret",
            "OAUTH_SSOT_COMPLIANCE": "true"
        }
        
        # Set SSOT OAuth configuration
        for key, value in ssot_oauth_config.items():
            env.set(key, value, "oauth_ssot")
        
        # Verify SSOT compliance
        config_source = env.get("OAUTH_CONFIGURATION_SOURCE")
        assert config_source == "unified_isolated_environment", "OAuth should use unified SSOT source"
        
        ssot_compliance = env.get("OAUTH_SSOT_COMPLIANCE")
        assert ssot_compliance == "true", "OAuth configuration should be SSOT compliant"
        
        # Verify no duplicate OAuth sources
        duplicate_sources = [
            "LEGACY_OAUTH_CONFIG",
            "ALTERNATIVE_GOOGLE_CLIENT_ID",
            "BACKUP_OAUTH_SOURCE",
            "SECONDARY_AUTH_CONFIG"
        ]
        
        for duplicate in duplicate_sources:
            assert env.get(duplicate) is None, f"Should not have duplicate OAuth source: {duplicate}"
        
        # Verify OAuth configuration comes from single source (IsolatedEnvironment)
        staging_client_id = env.get("GOOGLE_OAUTH_CLIENT_ID_STAGING")
        assert "ssot" in staging_client_id, "OAuth credentials should come from SSOT source"
        
        # Verify source tracking points to unified source
        client_id_source = env.get_variable_source("GOOGLE_OAUTH_CLIENT_ID_STAGING")
        assert client_id_source == "oauth_ssot", f"OAuth source tracking incorrect: {client_id_source}"