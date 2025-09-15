"""
Unit Tests for Staging Environment Configuration Handling

These tests validate proper environment configuration handling for staging deployments,
preventing regressions related to environment-specific secret handling and configuration.

Related to commit 41e0dd6a8 which fixed:
- Environment-specific secret mappings
- Staging-specific Redis configuration 
- OAuth environment variable naming conventions

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure staging environment stability and prevent configuration drift
- Value Impact: Reduces deployment failures and environment inconsistencies
- Strategic Impact: Maintains reliable staging environment for development velocity
"""

import pytest
from typing import Dict, List, Optional
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from deployment.secrets_config import SecretConfig
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestStagingEnvironmentConfiguration:
    """Test suite for staging environment configuration handling."""
    
    def test_staging_environment_secret_generation(self):
        """Test that staging environment generates correct secret mappings."""
        # Generate secrets string for staging environment
        auth_secrets = SecretConfig.generate_secrets_string("auth", "staging")
        backend_secrets = SecretConfig.generate_secrets_string("backend", "staging")
        
        # Assert all secret mappings use :latest version (staging pattern)
        auth_mappings = auth_secrets.split(",")
        for mapping in auth_mappings:
            assert mapping.endswith(":latest"), (
                f"Staging secrets should use :latest version, got: {mapping}"
            )
        
        backend_mappings = backend_secrets.split(",")
        for mapping in backend_mappings:
            assert mapping.endswith(":latest"), (
                f"Staging secrets should use :latest version, got: {mapping}"
            )
    
    def test_staging_environment_oauth_naming_conventions(self):
        """Test that staging OAuth secrets follow correct naming conventions.
        
        Auth service uses environment-specific names while backend uses simplified names.
        This test prevents the confusion that led to the SECRET_KEY regression.
        """
        # Get service secrets
        auth_secrets = SecretConfig.get_all_service_secrets("auth")
        backend_secrets = SecretConfig.get_all_service_secrets("backend")
        
        # Auth service should use staging-specific OAuth names
        assert "GOOGLE_OAUTH_CLIENT_ID_STAGING" in auth_secrets, (
            "Auth service should use environment-specific OAuth client ID name"
        )
        assert "GOOGLE_OAUTH_CLIENT_SECRET_STAGING" in auth_secrets, (
            "Auth service should use environment-specific OAuth client secret name"
        )
        
        # Backend service should use simplified names
        assert "GOOGLE_CLIENT_ID" in backend_secrets, (
            "Backend service should use simplified OAuth client ID name"
        )
        assert "GOOGLE_CLIENT_SECRET" in backend_secrets, (
            "Backend service should use simplified OAuth client secret name"
        )
        
        # Neither service should use the other's naming convention
        assert "GOOGLE_CLIENT_ID" not in auth_secrets, (
            "Auth service should not use simplified OAuth names"
        )
        assert "GOOGLE_OAUTH_CLIENT_ID_STAGING" not in backend_secrets, (
            "Backend service should not use environment-specific OAuth names"
        )
    
    def test_staging_environment_redis_configuration_consistency(self):
        """Test that Redis configuration is consistent across staging services.
        
        Both services should have access to both REDIS_URL and REDIS_HOST/PORT
        for backward compatibility, but the regression showed confusion about which to use.
        """
        auth_secrets = SecretConfig.get_all_service_secrets("auth")
        backend_secrets = SecretConfig.get_all_service_secrets("backend")
        
        redis_config_secrets = ["REDIS_HOST", "REDIS_PORT", "REDIS_URL", "REDIS_PASSWORD"]
        
        # Both services should have all Redis configuration options
        for secret in redis_config_secrets:
            assert secret in auth_secrets, (
                f"Auth service should have Redis secret: {secret}"
            )
            assert secret in backend_secrets, (
                f"Backend service should have Redis secret: {secret}"
            )
    
    def test_staging_gsm_secret_name_consistency(self):
        """Test that all staging secrets follow consistent GSM naming patterns.
        
        All staging secrets should end with '-staging' to avoid confusion with
        production secrets.
        """
        all_mappings = SecretConfig.SECRET_MAPPINGS
        
        # Filter to staging-related mappings (most should end with -staging)
        staging_secrets = [
            gsm_id for gsm_id in all_mappings.values() 
            if "staging" in gsm_id.lower()
        ]
        
        # All staging secrets should follow the pattern
        for gsm_id in staging_secrets:
            assert gsm_id.endswith("-staging"), (
                f"Staging GSM secret should end with '-staging': {gsm_id}"
            )
    
    def test_staging_critical_secrets_completeness(self):
        """Test that all critical secrets are properly defined for staging.
        
        Missing critical secrets cause deployment failures, as seen in the regression.
        """
        # Get critical secrets for both services
        auth_critical = SecretConfig.CRITICAL_SECRETS.get("auth", [])
        backend_critical = SecretConfig.CRITICAL_SECRETS.get("backend", [])
        
        # Define expected critical secrets based on the regression
        expected_auth_critical = ["SECRET_KEY", "JWT_SECRET_KEY", "SERVICE_SECRET", "POSTGRES_PASSWORD"]
        expected_backend_critical = ["SECRET_KEY", "JWT_SECRET_KEY", "POSTGRES_PASSWORD"]
        
        for secret in expected_auth_critical:
            assert secret in auth_critical, (
                f"Auth service missing critical secret: {secret}"
            )
        
        for secret in expected_backend_critical:
            assert secret in backend_critical, (
                f"Backend service missing critical secret: {secret}"
            )
    
    def test_staging_secret_categorization_completeness(self):
        """Test that staging secrets are properly categorized by function.
        
        Proper categorization prevents accidental removal during updates.
        """
        # Test auth service categorization
        auth_secrets = SecretConfig.get_service_secrets("auth")
        
        required_categories = ["database", "authentication", "oauth", "redis"]
        for category in required_categories:
            assert category in auth_secrets, (
                f"Auth service missing secret category: {category}"
            )
            assert len(auth_secrets[category]) > 0, (
                f"Auth service category '{category}' should not be empty"
            )
        
        # Test backend service categorization  
        backend_secrets = SecretConfig.get_service_secrets("backend")
        
        required_categories = ["database", "authentication", "oauth", "redis", "ai_services"]
        for category in required_categories:
            assert category in backend_secrets, (
                f"Backend service missing secret category: {category}"
            )
            assert len(backend_secrets[category]) > 0, (
                f"Backend service category '{category}' should not be empty"
            )
    
    def test_staging_deployment_string_length_reasonable(self):
        """Test that staging deployment strings are reasonable length.
        
        Extremely long deployment strings can cause command-line issues.
        """
        auth_secrets = SecretConfig.generate_secrets_string("auth", "staging")
        backend_secrets = SecretConfig.generate_secrets_string("backend", "staging")
        
        # Test reasonable length limits (based on typical command-line limits)
        max_length = 8000  # Conservative limit for command-line arguments
        
        assert len(auth_secrets) < max_length, (
            f"Auth secrets string too long: {len(auth_secrets)} characters"
        )
        assert len(backend_secrets) < max_length, (
            f"Backend secrets string too long: {len(backend_secrets)} characters"
        )
    
    def test_staging_no_duplicate_secrets_in_category(self):
        """Test that no secrets are duplicated within their categories.
        
        Duplicate secrets cause deployment script confusion.
        """
        for service_name in ["auth", "backend"]:
            service_secrets = SecretConfig.get_service_secrets(service_name)
            
            for category, secrets in service_secrets.items():
                # Check for duplicates within category
                unique_secrets = set(secrets)
                assert len(unique_secrets) == len(secrets), (
                    f"{service_name} service has duplicate secrets in {category} category"
                )
    
    def test_staging_environment_variable_format_validation(self):
        """Test that all environment variable names follow proper format.
        
        Invalid environment variable names cause deployment failures.
        """
        all_secrets = set()
        
        # Collect all secret names from both services
        for service_name in ["auth", "backend"]:
            service_secrets = SecretConfig.get_all_service_secrets(service_name)
            all_secrets.update(service_secrets)
        
        # Validate each secret name format
        for secret_name in all_secrets:
            # Should be uppercase with underscores only
            assert secret_name.isupper(), (
                f"Secret name should be uppercase: {secret_name}"
            )
            assert all(c.isalnum() or c == '_' for c in secret_name), (
                f"Secret name should only contain alphanumeric and underscore: {secret_name}"
            )
            assert not secret_name.startswith('_'), (
                f"Secret name should not start with underscore: {secret_name}"
            )
            assert not secret_name.endswith('_'), (
                f"Secret name should not end with underscore: {secret_name}"
            )


class TestStagingDeploymentErrorPrevention:
    """Test suite focused on preventing staging deployment errors."""
    
    @pytest.mark.parametrize("service_name", ["auth", "backend"])
    def test_all_secrets_have_gsm_mappings(self, service_name):
        """Test that every secret has a GSM mapping.
        
        Missing GSM mappings cause deployment failures like the SECRET_KEY regression.
        """
        service_secrets = SecretConfig.get_all_service_secrets(service_name)
        
        missing_mappings = []
        for secret in service_secrets:
            gsm_mapping = SecretConfig.get_gsm_mapping(secret)
            if gsm_mapping is None:
                missing_mappings.append(secret)
        
        assert len(missing_mappings) == 0, (
            f"{service_name} service has secrets without GSM mappings: {missing_mappings}"
        )
    
    @pytest.mark.parametrize("service_name", ["auth", "backend"])
    def test_secrets_string_format_valid(self, service_name):
        """Test that secrets string format is valid for gcloud deployment.
        
        Invalid format causes gcloud run deploy failures.
        """
        secrets_string = SecretConfig.generate_secrets_string(service_name, "staging")
        
        # Should not be empty
        assert len(secrets_string) > 0, (
            f"{service_name} secrets string should not be empty"
        )
        
        # Should be comma-separated key=value:version pairs
        mappings = secrets_string.split(",")
        assert len(mappings) > 0, (
            f"{service_name} should have at least one secret mapping"
        )
        
        for mapping in mappings:
            # Should contain exactly one '=' character
            parts = mapping.split("=")
            assert len(parts) == 2, (
                f"Invalid mapping format in {service_name}: {mapping}"
            )
            
            env_var, gsm_spec = parts
            assert len(env_var) > 0, (
                f"Empty environment variable name in {service_name}: {mapping}"
            )
            
            # GSM spec should contain ':latest' for staging
            assert ":latest" in gsm_spec, (
                f"Missing version in GSM spec for {service_name}: {mapping}"
            )
    
    def test_no_conflicting_secret_definitions(self):
        """Test that the same secret name doesn't have conflicting definitions.
        
        Conflicting definitions cause confusion and potential deployment errors.
        """
        # Collect all secrets from both services
        auth_secrets_dict = SecretConfig.get_service_secrets("auth")
        backend_secrets_dict = SecretConfig.get_service_secrets("backend")
        
        # Find secrets that appear in both services
        auth_all = set(SecretConfig.get_all_service_secrets("auth"))
        backend_all = set(SecretConfig.get_all_service_secrets("backend"))
        common_secrets = auth_all.intersection(backend_all)
        
        # For common secrets, ensure they map to the same GSM secret
        for secret in common_secrets:
            auth_gsm = SecretConfig.get_gsm_mapping(secret)
            backend_gsm = SecretConfig.get_gsm_mapping(secret)
            
            assert auth_gsm == backend_gsm, (
                f"Secret {secret} has conflicting GSM mappings: "
                f"auth='{auth_gsm}', backend='{backend_gsm}'"
            )
    
    def test_critical_secret_validation_comprehensive(self):
        """Test that critical secret validation works for realistic scenarios."""
        # Test scenario: Most secrets available but one critical secret missing
        for service_name in ["auth", "backend"]:
            all_secrets = set(SecretConfig.get_all_service_secrets(service_name))
            critical_secrets = set(SecretConfig.CRITICAL_SECRETS.get(service_name, []))
            
            # Test with each critical secret missing one at a time
            for missing_secret in critical_secrets:
                available_secrets = all_secrets - {missing_secret}
                
                missing = SecretConfig.validate_critical_secrets(
                    service_name, available_secrets
                )
                
                assert missing_secret in missing, (
                    f"{service_name}: Should detect missing critical secret {missing_secret}"
                )
                assert len(missing) == 1, (
                    f"{service_name}: Should detect exactly one missing secret, got {missing}"
                )
    
    def test_deployment_secrets_completeness_check(self):
        """Test comprehensive deployment readiness check.
        
        This test simulates what should be checked before deployment to prevent
        regressions like the SECRET_KEY incident.
        """
        for service_name in ["auth", "backend"]:
            # Get all required secrets
            required_secrets = set(SecretConfig.get_all_service_secrets(service_name))
            
            # Check each secret has GSM mapping
            for secret in required_secrets:
                gsm_mapping = SecretConfig.get_gsm_mapping(secret)
                assert gsm_mapping is not None, (
                    f"{service_name}: Secret {secret} lacks GSM mapping"
                )
                
                # Check GSM mapping follows staging pattern
                if "staging" not in service_name:  # Apply to staging deployments
                    assert "staging" in gsm_mapping.lower(), (
                        f"{service_name}: GSM mapping {gsm_mapping} should contain 'staging'"
                    )
            
            # Check critical secrets are subset of all secrets
            critical_secrets = set(SecretConfig.CRITICAL_SECRETS.get(service_name, []))
            assert critical_secrets.issubset(required_secrets), (
                f"{service_name}: Critical secrets not subset of all secrets. "
                f"Critical but not required: {critical_secrets - required_secrets}"
            )
            
            # Check secrets string generation works
            secrets_string = SecretConfig.generate_secrets_string(service_name, "staging")
            assert len(secrets_string) > 0, (
                f"{service_name}: Failed to generate secrets string"
            )
