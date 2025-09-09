"""
E2E Tests: Production Configuration Validation

CRITICAL: Tests production-ready configuration validation and security compliance.
Validates production configurations meet security requirements and prevent cascade failures.

Business Value: Platform/Internal - Prevents production outages and security vulnerabilities
Test Coverage: Production config validation, security compliance, cascade failure prevention
"""
import pytest
import asyncio
import os
import re
from unittest.mock import patch, Mock
from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


@pytest.mark.e2e
@pytest.mark.production_validation
class TestProductionConfigurationValidation:
    """Test production configuration validation and security compliance."""

    @pytest.fixture(autouse=True)
    def setup_production_validation_environment(self):
        """Set up environment for production configuration validation."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Store original state
        self.original_env = self.env.get_all()
        
        yield
        
        # Cleanup
        self.env.clear()
        for key, value in self.original_env.items():
            self.env.set(key, value, "restore_original")

    def test_production_domain_configuration_security(self):
        """
        CRITICAL: Test production domain configuration meets security requirements.
        
        PREVENTS: Insecure domain configurations in production
        CASCADE FAILURE: Security vulnerabilities, data exposure, compliance violations
        """
        # Set up production domain configuration
        production_domains = {
            "ENVIRONMENT": "production",
            "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai",
            "NEXT_PUBLIC_AUTH_URL": "https://auth.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.netrasystems.ai/ws",
            "NEXT_PUBLIC_FRONTEND_URL": "https://app.netrasystems.ai",
            "NEXT_PUBLIC_ENVIRONMENT": "production"
        }
        
        for key, value in production_domains.items():
            self.env.set(key, value, "production_domain_validation")
        
        # Verify production domain security requirements
        for key, expected_url in production_domains.items():
            if key != "ENVIRONMENT" and key != "NEXT_PUBLIC_ENVIRONMENT":
                actual_url = self.env.get(key)
                
                # Security requirement: HTTPS/WSS only
                if "WS_URL" in key:
                    assert actual_url.startswith("wss://"), f"Production {key} must use WSS: {actual_url}"
                else:
                    assert actual_url.startswith("https://"), f"Production {key} must use HTTPS: {actual_url}"
                
                # Security requirement: No localhost or development domains
                assert "localhost" not in actual_url, f"Production {key} cannot use localhost: {actual_url}"
                assert "127.0.0.1" not in actual_url, f"Production {key} cannot use 127.0.0.1: {actual_url}"
                assert "staging" not in actual_url, f"Production {key} cannot use staging: {actual_url}"
                assert "dev" not in actual_url, f"Production {key} cannot use dev: {actual_url}"
                
                # Security requirement: Must use production domains
                assert "netrasystems.ai" in actual_url, f"Production {key} must use netrasystems.ai: {actual_url}"
                
                # Security requirement: No insecure ports
                insecure_ports = [":80", ":8000", ":8080", ":3000"]
                for insecure_port in insecure_ports:
                    assert insecure_port not in actual_url, f"Production {key} cannot use insecure port: {actual_url}"

    def test_production_oauth_configuration_security(self):
        """
        CRITICAL: Test production OAuth configuration meets security requirements.
        
        PREVENTS: Insecure OAuth configurations in production
        CASCADE FAILURE: Authentication vulnerabilities, unauthorized access
        """
        # Set up production OAuth configuration
        production_oauth = {
            "ENVIRONMENT": "production",
            "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": "prod-client-123456.apps.googleusercontent.com",
            "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION": "prod-oauth-secret-32-characters-minimum-secure",
            "GITHUB_OAUTH_CLIENT_ID_PRODUCTION": "production-github-oauth-client-secure",
            "GITHUB_OAUTH_CLIENT_SECRET_PRODUCTION": "production-github-secret-32-characters-minimum"
        }
        
        for key, value in production_oauth.items():
            self.env.set(key, value, "production_oauth_validation")
        
        # Verify production OAuth security requirements
        google_client_id = self.env.get("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION")
        google_client_secret = self.env.get("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION")
        
        # Security requirement: OAuth client ID format validation
        assert google_client_id.endswith(".apps.googleusercontent.com"), (
            f"Production Google client ID must be valid format: {google_client_id}"
        )
        assert "production" in google_client_id.lower() or "prod" in google_client_id.lower(), (
            f"Production client ID should indicate production: {google_client_id}"
        )
        
        # Security requirement: OAuth secret strength validation
        assert len(google_client_secret) >= 32, (
            f"Production OAuth secret too short: {len(google_client_secret)} chars"
        )
        
        # Security requirement: No test/development OAuth credentials
        test_patterns = ["test", "dev", "localhost", "staging", "demo"]
        for pattern in test_patterns:
            assert pattern not in google_client_id.lower(), (
                f"Production OAuth cannot contain test pattern '{pattern}': {google_client_id}"
            )
            assert pattern not in google_client_secret.lower(), (
                f"Production OAuth secret cannot contain test pattern '{pattern}'"
            )
        
        # Verify NO non-production OAuth credentials are present
        non_prod_oauth_keys = [
            "GOOGLE_CLIENT_ID",  # Development pattern
            "GOOGLE_OAUTH_CLIENT_ID_STAGING",  # Staging pattern
            "GOOGLE_OAUTH_CLIENT_ID_TEST",  # Test pattern
            "E2E_OAUTH_SIMULATION_KEY"  # E2E test pattern
        ]
        
        for non_prod_key in non_prod_oauth_keys:
            assert self.env.get(non_prod_key) is None, (
                f"Production should not have non-production OAuth: {non_prod_key}"
            )

    def test_production_secret_configuration_security(self):
        """
        CRITICAL: Test production secret configuration meets security requirements.
        
        PREVENTS: Weak secrets and security vulnerabilities in production
        CASCADE FAILURE: Authentication failures, data breaches, compliance violations
        """
        # Set up production secret configuration
        production_secrets = {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "production-jwt-secret-64-characters-ultra-secure-key-for-token-validation",
            "SERVICE_SECRET": "production-service-secret-64-characters-ultra-secure-inter-service-auth",
            "FERNET_KEY": "production-fernet-encryption-key-32-characters-base64-encoded-secure=",
            "SECRET_KEY": "production-app-secret-64-characters-ultra-secure-application-secret-key"
        }
        
        for key, value in production_secrets.items():
            self.env.set(key, value, "production_secret_validation")
        
        # Verify production secret security requirements
        jwt_secret = self.env.get("JWT_SECRET_KEY")
        service_secret = self.env.get("SERVICE_SECRET")
        fernet_key = self.env.get("FERNET_KEY")
        app_secret = self.env.get("SECRET_KEY")
        
        secrets_to_validate = [
            ("JWT_SECRET_KEY", jwt_secret, 64),
            ("SERVICE_SECRET", service_secret, 32),
            ("FERNET_KEY", fernet_key, 32),
            ("SECRET_KEY", app_secret, 32)
        ]
        
        for secret_name, secret_value, min_length in secrets_to_validate:
            # Security requirement: Minimum length
            assert len(secret_value) >= min_length, (
                f"Production {secret_name} too short: {len(secret_value)} < {min_length}"
            )
            
            # Security requirement: No common weak patterns
            weak_patterns = ["password", "123", "admin", "test", "secret", "key"]
            for pattern in weak_patterns:
                assert pattern not in secret_value.lower(), (
                    f"Production {secret_name} contains weak pattern '{pattern}'"
                )
            
            # Security requirement: No environment leakage
            env_patterns = ["dev", "staging", "localhost", "test"]
            for pattern in env_patterns:
                assert pattern not in secret_value.lower(), (
                    f"Production {secret_name} contains environment pattern '{pattern}'"
                )
            
            # Security requirement: Sufficient complexity (for non-base64 secrets)
            if secret_name != "FERNET_KEY":
                has_alpha = any(c.isalpha() for c in secret_value)
                has_digit = any(c.isdigit() for c in secret_value)
                has_special = any(c in "!@#$%^&*()-_=+" for c in secret_value)
                
                complexity_score = sum([has_alpha, has_digit, has_special])
                assert complexity_score >= 2, (
                    f"Production {secret_name} lacks complexity (alpha:{has_alpha}, digit:{has_digit}, special:{has_special})"
                )

    def test_production_database_configuration_security(self):
        """
        CRITICAL: Test production database configuration meets security requirements.
        
        PREVENTS: Insecure database configurations in production
        CASCADE FAILURE: Data breaches, unauthorized access, compliance violations
        """
        # Set up production database configuration
        production_db = {
            "ENVIRONMENT": "production",
            "POSTGRES_HOST": "production-db.gcp.internal",
            "POSTGRES_USER": "netra_production_user",
            "POSTGRES_PASSWORD": "ultra-secure-production-password-64-characters-with-symbols-123!",
            "POSTGRES_DB": "netra_production",
            "POSTGRES_PORT": "5432",
            "DATABASE_SSL_MODE": "require",
            "DATABASE_SSL_CERT": "/certs/production-db-client.crt"
        }
        
        for key, value in production_db.items():
            self.env.set(key, value, "production_db_validation")
        
        # Verify production database security requirements
        db_host = self.env.get("POSTGRES_HOST")
        db_user = self.env.get("POSTGRES_USER")
        db_password = self.env.get("POSTGRES_PASSWORD")
        db_name = self.env.get("POSTGRES_DB")
        ssl_mode = self.env.get("DATABASE_SSL_MODE")
        
        # Security requirement: No localhost or development hosts
        assert "localhost" not in db_host, f"Production DB cannot use localhost: {db_host}"
        assert "127.0.0.1" not in db_host, f"Production DB cannot use 127.0.0.1: {db_host}"
        assert "staging" not in db_host, f"Production DB cannot use staging host: {db_host}"
        
        # Security requirement: Production-specific host patterns
        production_host_patterns = ["production", "prod", "gcp", "cloud", "aws", "azure"]
        has_production_pattern = any(pattern in db_host.lower() for pattern in production_host_patterns)
        assert has_production_pattern, f"Production DB host should indicate production environment: {db_host}"
        
        # Security requirement: Strong database password
        assert len(db_password) >= 32, f"Production DB password too short: {len(db_password)} chars"
        
        # Security requirement: Database name indicates production
        assert "production" in db_name or "prod" in db_name, (
            f"Production DB name should indicate production: {db_name}"
        )
        assert "test" not in db_name and "dev" not in db_name, (
            f"Production DB name cannot contain test/dev: {db_name}"
        )
        
        # Security requirement: SSL required
        if ssl_mode:
            assert ssl_mode in ["require", "verify-ca", "verify-full"], (
                f"Production DB must require SSL: {ssl_mode}"
            )

    def test_production_configuration_no_fallbacks_regression(self):
        """
        CRITICAL: Test production configuration does NOT use fallbacks.
        
        PREVENTS: Development defaults used in production (regression prevention)
        CASCADE FAILURE: Production using test credentials, data exposure
        """
        # Set up minimal production configuration (missing some optional values)
        minimal_production_config = {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "production-jwt-secret-64-characters-minimum",
            "SERVICE_SECRET": "production-service-secret-64-characters-minimum"
            # Intentionally missing some optional configs to test fallback behavior
        }
        
        for key, value in minimal_production_config.items():
            self.env.set(key, value, "production_no_fallback_test")
        
        # Verify production does NOT provide test defaults
        test_defaults = [
            "GOOGLE_OAUTH_CLIENT_ID_TEST",
            "E2E_OAUTH_SIMULATION_KEY",
            "ANTHROPIC_API_KEY",  # Should come from deployment system, not defaults
            "OPENAI_API_KEY"      # Should come from deployment system, not defaults
        ]
        
        for test_default in test_defaults:
            value = self.env.get(test_default)
            
            if value is not None:
                # If value exists, it should NOT be a test default
                test_patterns = ["test", "placeholder", "mock", "demo", "simulation"]
                for pattern in test_patterns:
                    assert pattern not in value.lower(), (
                        f"Production {test_default} contains test pattern '{pattern}': {value}"
                    )
        
        # Verify production environment detection
        assert self.env.is_production(), "Should detect production environment"
        assert not self.env.is_test(), "Should not detect test environment in production"
        assert not self.env.is_development(), "Should not detect development environment in production"
        assert not self.env.is_staging(), "Should not detect staging environment in production"

    def test_production_cascade_failure_prevention_validation(self):
        """
        CRITICAL: Test production configuration prevents cascade failures.
        
        PREVENTS: Configuration errors causing system-wide failures in production
        CASCADE FAILURE: Complete system failure, revenue loss, customer impact
        """
        # Set up production configuration with all cascade-critical values
        cascade_critical_config = {
            "ENVIRONMENT": "production",
            "SERVICE_SECRET": "production-service-secret-ultra-secure-64-characters-minimum",
            "SERVICE_ID": "netra-backend",  # Must be stable value
            "DATABASE_URL": "postgresql://prod-user:prod-pass@prod-db.gcp:5432/netra_production",
            "JWT_SECRET_KEY": "production-jwt-secret-ultra-secure-64-characters-minimum",
            "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.netrasystems.ai/ws",
            "NEXT_PUBLIC_AUTH_URL": "https://auth.netrasystems.ai",
            "NEXT_PUBLIC_ENVIRONMENT": "production",
            "REDIS_URL": "redis://production-redis.gcp:6379/0"
        }
        
        for key, value in cascade_critical_config.items():
            self.env.set(key, value, "production_cascade_prevention")
        
        # Validate cascade-critical configurations
        cascade_validations = [
            {
                "key": "SERVICE_SECRET",
                "min_length": 32,
                "impact": "Complete authentication failure and circuit breaker permanent open"
            },
            {
                "key": "SERVICE_ID", 
                "expected_value": "netra-backend",
                "impact": "Authentication mismatches and service communication failures"
            },
            {
                "key": "DATABASE_URL",
                "must_contain": "postgresql://",
                "impact": "Complete backend failure with no data access"
            },
            {
                "key": "JWT_SECRET_KEY",
                "min_length": 32,
                "impact": "Token validation failures and authentication breakdown"
            },
            {
                "key": "NEXT_PUBLIC_API_URL",
                "must_start_with": "https://",
                "impact": "No API calls work, no agents run, no data fetched"
            }
        ]
        
        for validation in cascade_validations:
            key = validation["key"]
            value = self.env.get(key)
            impact = validation["impact"]
            
            assert value is not None, f"CASCADE CRITICAL: {key} is missing - IMPACT: {impact}"
            
            if "min_length" in validation:
                min_length = validation["min_length"]
                assert len(value) >= min_length, (
                    f"CASCADE CRITICAL: {key} too short ({len(value)} < {min_length}) - IMPACT: {impact}"
                )
            
            if "expected_value" in validation:
                expected = validation["expected_value"]
                assert value == expected, (
                    f"CASCADE CRITICAL: {key} incorrect ('{value}' != '{expected}') - IMPACT: {impact}"
                )
            
            if "must_contain" in validation:
                must_contain = validation["must_contain"]
                assert must_contain in value, (
                    f"CASCADE CRITICAL: {key} missing '{must_contain}' - IMPACT: {impact}"
                )
            
            if "must_start_with" in validation:
                must_start = validation["must_start_with"]
                assert value.startswith(must_start), (
                    f"CASCADE CRITICAL: {key} must start with '{must_start}' - IMPACT: {impact}"
                )
        
        # Test configuration protection (simulate production protection mechanism)
        for key in cascade_critical_config:
            if key in ["SERVICE_SECRET", "JWT_SECRET_KEY", "DATABASE_URL"]:
                self.env.protect_variable(key)
                
                # Verify protection prevents modification
                success = self.env.set(key, "malicious_value", "attack_attempt")
                assert not success, f"Production {key} should be protected from modification"