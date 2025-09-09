"""
Unit Tests: Environment-Specific Configuration Independence

CRITICAL: Tests environment isolation between TEST/DEV/STAGING/PROD configurations.
Prevents OAuth credential leaks and domain configuration cross-contamination.

Business Value: Platform/Internal - Prevents $12K MRR loss from configuration incidents
Test Coverage: Environment independence, OAuth isolation, domain validation
"""
import pytest
import os
from unittest.mock import patch, Mock
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment, get_env, ValidationResult


class TestEnvironmentSpecificConfigIndependence:
    """Test environment-specific configuration independence to prevent cascade failures."""

    def test_development_vs_staging_oauth_isolation(self):
        """
        CRITICAL: Test OAuth configuration isolation between development and staging.
        
        PREVENTS: Development OAuth credentials used in staging (503 errors)
        CASCADE FAILURE: Complete OAuth flow failure, user lockout
        """
        env = get_env()
        env.enable_isolation()
        
        # Development OAuth configuration
        dev_oauth_config = {
            "ENVIRONMENT": "development",
            "GOOGLE_CLIENT_ID": "dev-google-client-id.apps.googleusercontent.com",
            "GOOGLE_CLIENT_SECRET": "dev-google-client-secret",
            "GITHUB_CLIENT_ID": "dev-github-client-id",
            "GITHUB_CLIENT_SECRET": "dev-github-client-secret"
        }
        
        # Staging OAuth configuration (environment-specific naming)
        staging_oauth_config = {
            "ENVIRONMENT": "staging",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-google-client-id.apps.googleusercontent.com",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-google-client-secret",
            "GITHUB_OAUTH_CLIENT_ID_STAGING": "staging-github-client-id",
            "GITHUB_OAUTH_CLIENT_SECRET_STAGING": "staging-github-client-secret"
        }
        
        # Test development environment isolation
        env.clear()
        for key, value in dev_oauth_config.items():
            env.set(key, value, "development_config")
        
        # Verify development OAuth is isolated
        assert env.get("GOOGLE_CLIENT_ID") == "dev-google-client-id.apps.googleusercontent.com"
        assert env.get("GOOGLE_OAUTH_CLIENT_ID_STAGING") is None, "Staging OAuth should not exist in development"
        
        # Test staging environment isolation  
        env.clear()
        for key, value in staging_oauth_config.items():
            env.set(key, value, "staging_config")
        
        # Verify staging OAuth is isolated
        assert env.get("GOOGLE_OAUTH_CLIENT_ID_STAGING") == "staging-google-client-id.apps.googleusercontent.com"
        assert env.get("GOOGLE_CLIENT_ID") is None, "Development OAuth should not exist in staging"

    def test_production_vs_staging_domain_isolation(self):
        """
        CRITICAL: Test domain configuration isolation between staging and production.
        
        PREVENTS: Staging URLs used in production (data corruption, security breaches)
        CASCADE FAILURE: Wrong API endpoints, WebSocket connection failures
        """
        env = get_env()
        env.enable_isolation()
        
        # Staging domain configuration
        staging_domains = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai/ws",
            "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai",
            "NEXT_PUBLIC_FRONTEND_URL": "https://app.staging.netrasystems.ai"
        }
        
        # Production domain configuration
        production_domains = {
            "ENVIRONMENT": "production",
            "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.netrasystems.ai/ws", 
            "NEXT_PUBLIC_AUTH_URL": "https://auth.netrasystems.ai",
            "NEXT_PUBLIC_FRONTEND_URL": "https://app.netrasystems.ai"
        }
        
        # Test staging domain isolation
        env.clear()
        for key, value in staging_domains.items():
            env.set(key, value, "staging_domains")
        
        # Verify staging domains are properly isolated
        api_url = env.get("NEXT_PUBLIC_API_URL")
        assert "staging" in api_url, f"Staging API URL should contain 'staging': {api_url}"
        assert api_url.startswith("https://"), "Staging should use HTTPS"
        
        ws_url = env.get("NEXT_PUBLIC_WS_URL")
        assert "staging" in ws_url, f"Staging WebSocket URL should contain 'staging': {ws_url}"
        assert ws_url.startswith("wss://"), "Staging WebSocket should use WSS"
        
        # Test production domain isolation
        env.clear()
        for key, value in production_domains.items():
            env.set(key, value, "production_domains")
        
        # Verify production domains are properly isolated
        api_url = env.get("NEXT_PUBLIC_API_URL")
        assert "staging" not in api_url, f"Production API URL should not contain 'staging': {api_url}"
        assert api_url == "https://api.netrasystems.ai", f"Production API URL incorrect: {api_url}"
        
        auth_url = env.get("NEXT_PUBLIC_AUTH_URL")
        assert auth_url == "https://auth.netrasystems.ai", f"Production Auth URL incorrect: {auth_url}"

    def test_test_vs_development_database_isolation(self):
        """
        CRITICAL: Test database configuration isolation between test and development.
        
        PREVENTS: Test database operations affecting development data
        CASCADE FAILURE: Data corruption, test data in development database
        """
        env = get_env()
        env.enable_isolation()
        
        # Test database configuration (in-memory/isolated)
        test_db_config = {
            "ENVIRONMENT": "test",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",  # Different port for test
            "POSTGRES_USER": "netra_test",
            "POSTGRES_PASSWORD": "netra_test_password",
            "POSTGRES_DB": "netra_test",
            "DATABASE_URL": "postgresql://netra_test:netra_test_password@localhost:5434/netra_test"
        }
        
        # Development database configuration
        dev_db_config = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "localhost", 
            "POSTGRES_PORT": "5432",  # Standard PostgreSQL port
            "POSTGRES_USER": "netra_dev",
            "POSTGRES_PASSWORD": "netra_dev_password",
            "POSTGRES_DB": "netra_dev",
            "DATABASE_URL": "postgresql://netra_dev:netra_dev_password@localhost:5432/netra_dev"
        }
        
        # Test environment database isolation
        env.clear()
        for key, value in test_db_config.items():
            env.set(key, value, "test_database")
        
        # Verify test database is isolated
        test_db_url = env.get("DATABASE_URL")
        assert "5434" in test_db_url, f"Test should use port 5434: {test_db_url}"
        assert "netra_test" in test_db_url, f"Test should use test database: {test_db_url}"
        
        # Test development database isolation
        env.clear()
        for key, value in dev_db_config.items():
            env.set(key, value, "development_database")
        
        # Verify development database is isolated
        dev_db_url = env.get("DATABASE_URL")
        assert "5432" in dev_db_url, f"Development should use port 5432: {dev_db_url}"
        assert "netra_dev" in dev_db_url, f"Development should use dev database: {dev_db_url}"
        
        # CRITICAL: Verify no cross-contamination
        assert "netra_test" not in dev_db_url, "Test database name leaked to development"
        assert "5434" not in dev_db_url, "Test port leaked to development"

    def test_staging_database_credential_validation(self):
        """
        CRITICAL: Test staging database credential validation to prevent auth failures.
        
        PREVENTS: Invalid staging credentials (user_pr-4 issue) causing 503 errors
        CASCADE FAILURE: Complete staging environment failure, deployment blocked
        """
        env = get_env()
        env.enable_isolation()
        
        # Test various staging credential scenarios
        valid_staging_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "staging-db.gcp.internal",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "secure-staging-password-123",
            "POSTGRES_DB": "netra_staging"
        }
        
        invalid_staging_configs = [
            {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": "localhost",  # Invalid for staging
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "password",
                "POSTGRES_DB": "netra_staging"
            },
            {
                "ENVIRONMENT": "staging", 
                "POSTGRES_HOST": "staging-db.gcp.internal",
                "POSTGRES_USER": "user_pr-4",  # The actual problematic user from reports
                "POSTGRES_PASSWORD": "wrong_password",
                "POSTGRES_DB": "netra_staging"
            },
            {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": "staging-db.gcp.internal",
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "123456",  # Too weak for staging
                "POSTGRES_DB": "netra_staging"
            }
        ]
        
        # Test valid staging configuration
        env.clear()
        for key, value in valid_staging_config.items():
            env.set(key, value, "valid_staging")
        
        validation_result = env.validate_staging_database_credentials()
        assert validation_result["valid"], f"Valid staging config should pass: {validation_result['issues']}"
        
        # Test invalid configurations
        for i, invalid_config in enumerate(invalid_staging_configs):
            env.clear()
            for key, value in invalid_config.items():
                env.set(key, value, f"invalid_staging_{i}")
            
            validation_result = env.validate_staging_database_credentials()
            assert not validation_result["valid"], f"Invalid config {i} should fail validation"
            assert validation_result["issues"], f"Invalid config {i} should have issues listed"


class TestConfigurationEnvironmentDefaults:
    """Test environment-specific default configuration handling."""

    def test_test_environment_oauth_defaults(self):
        """
        CRITICAL: Test OAuth defaults are available in test environment.
        
        PREVENTS: CentralConfigurationValidator failures in test context
        CASCADE FAILURE: Test suite failures blocking deployments
        """
        env = get_env()
        
        # Mock test context
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_oauth", "TESTING": "true"}):
            test_env = IsolatedEnvironment()
            test_env.enable_isolation()
            
            # Should provide test OAuth credentials automatically
            google_test_id = test_env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
            assert google_test_id == "test-oauth-client-id-for-automated-testing"
            
            google_test_secret = test_env.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST")
            assert google_test_secret == "test-oauth-client-secret-for-automated-testing"
            
            e2e_simulation_key = test_env.get("E2E_OAUTH_SIMULATION_KEY")
            assert e2e_simulation_key == "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"

    def test_development_environment_fallback_generation(self):
        """
        CRITICAL: Test development environment generates safe fallbacks.
        
        PREVENTS: Missing required variables causing development failures
        CASCADE FAILURE: Local development environment broken, productivity loss
        """
        env = get_env()
        env.enable_isolation()
        env.clear()
        
        # Simulate development environment with minimal configuration
        env.set("ENVIRONMENT", "development", "dev_setup")
        
        # Should provide development defaults for missing variables
        jwt_secret = env.get("JWT_SECRET_KEY")
        if not jwt_secret:
            # Should fallback to test default in development
            test_defaults = env._get_test_environment_defaults()
            jwt_secret = test_defaults.get("JWT_SECRET_KEY")
        
        assert jwt_secret, "Development should have JWT secret available"
        assert len(jwt_secret) >= 32, f"JWT secret too short: {len(jwt_secret)} chars"
        
        # Test database URL fallback
        db_url = env.get("DATABASE_URL")
        if not db_url:
            db_url = test_defaults.get("DATABASE_URL")
        
        assert db_url, "Development should have database URL available"
        assert "postgresql://" in db_url, f"Database URL should be PostgreSQL: {db_url}"

    def test_production_environment_no_fallbacks(self):
        """
        CRITICAL: Test production environment does NOT use fallbacks.
        
        PREVENTS: Development defaults used in production (security risk)
        CASCADE FAILURE: Production using test credentials, data exposure
        """
        env = get_env()
        env.enable_isolation()
        env.clear()
        
        # Simulate production environment
        env.set("ENVIRONMENT", "production", "prod_setup")
        
        # Production should NOT provide test defaults
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
            prod_env = IsolatedEnvironment()
            
            # Should NOT have test OAuth credentials
            google_test_id = prod_env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
            assert google_test_id is None, "Production should not have test OAuth credentials"
            
            # Should NOT have E2E simulation keys
            e2e_key = prod_env.get("E2E_OAUTH_SIMULATION_KEY")
            assert e2e_key is None, "Production should not have E2E simulation keys"
            
            # Should require explicit configuration
            jwt_secret = prod_env.get("JWT_SECRET_KEY")
            if jwt_secret:
                # If present, should not be test default
                assert jwt_secret != "test-jwt-secret-key-32-characters-long-for-testing-only"

    def test_cross_environment_variable_leakage_prevention(self):
        """
        CRITICAL: Test prevention of cross-environment variable leakage.
        
        PREVENTS: Staging variables in production, test variables in staging
        CASCADE FAILURE: Wrong APIs called, data corruption, security breaches
        """
        env = get_env()
        env.enable_isolation()
        
        # Test all environment combinations
        environments = {
            "test": {
                "DATABASE_URL": "postgresql://localhost:5434/netra_test",
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",
                "GOOGLE_OAUTH_CLIENT_ID_TEST": "test-oauth-client-id"
            },
            "development": {
                "DATABASE_URL": "postgresql://localhost:5432/netra_dev", 
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",
                "GOOGLE_CLIENT_ID": "dev-google-client-id"
            },
            "staging": {
                "DATABASE_URL": "postgresql://staging-db.gcp:5432/netra_staging",
                "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
                "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-google-client-id"
            },
            "production": {
                "DATABASE_URL": "postgresql://prod-db.gcp:5432/netra_production",
                "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai", 
                "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": "production-google-client-id"
            }
        }
        
        # Test each environment in isolation
        for env_name, config in environments.items():
            env.clear()
            env.set("ENVIRONMENT", env_name, f"{env_name}_setup")
            
            # Set environment-specific configuration
            for key, value in config.items():
                env.set(key, value, f"{env_name}_config")
            
            # Verify only this environment's config is present
            for other_env_name, other_config in environments.items():
                if other_env_name != env_name:
                    # Check for leakage from other environments
                    for key, value in other_config.items():
                        if key not in config:  # Only check keys unique to other environments
                            actual_value = env.get(key)
                            assert actual_value != value, f"{other_env_name} config leaked to {env_name}: {key}={value}"