"""
Unit Tests for SECRET_KEY Staging Deployment Regression

These tests prevent the critical regression where SECRET_KEY mapping was accidentally 
removed from the auth service deployment, causing staging deployment failures.

Commit 41e0dd6a8 fixes: 
- Missing SECRET_KEY mapping for auth service in deploy_to_gcp.py
- AuthService session_manager references (use redis_client instead) 
- Duplicate Redis host/port mappings (use REDIS_URL only)
- Missing value in redis-host-staging secret

Root cause: SECRET_KEY mapping was accidentally removed during OAuth variable updates
Impact: Auth service failed to start in staging environment
Resolution: Restored SECRET_KEY mapping and fixed code compatibility issues

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent deployment failures and downtime
- Value Impact: Ensures reliable staging deployments and prevents service startup failures
- Strategic Impact: Maintains development velocity and staging environment stability
"""

import pytest
from typing import Dict, List, Set
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


@pytest.mark.unit
class SecretKeyDeploymentRegressionTests:
    """Test suite to prevent SECRET_KEY deployment regression."""
    
    def test_secret_key_present_in_auth_service_secrets(self):
        """Test that SECRET_KEY is included in auth service secret configuration.
        
        This test prevents the regression where SECRET_KEY was accidentally removed
        from the auth service deployment configuration.
        """
        # Get auth service secrets
        auth_secrets = SecretConfig.get_all_service_secrets("auth")
        
        # Assert SECRET_KEY is present
        assert "SECRET_KEY" in auth_secrets, (
            "SECRET_KEY must be included in auth service secrets. "
            "This is CRITICAL for auth service startup. "
            "Missing SECRET_KEY caused staging deployment failure in commit 41e0dd6a8."
        )
    
    def test_secret_key_present_in_backend_service_secrets(self):
        """Test that SECRET_KEY is included in backend service secret configuration."""
        # Get backend service secrets
        backend_secrets = SecretConfig.get_all_service_secrets("backend")
        
        # Assert SECRET_KEY is present
        assert "SECRET_KEY" in backend_secrets, (
            "SECRET_KEY must be included in backend service secrets. "
            "This is CRITICAL for backend service startup."
        )
    
    def test_secret_key_marked_as_critical_for_auth_service(self):
        """Test that SECRET_KEY is marked as critical for auth service.
        
        Critical secrets cause deployment failure if missing - this ensures
        SECRET_KEY absence is caught early in the deployment process.
        """
        # Get critical secrets for auth service
        critical_secrets = SecretConfig.CRITICAL_SECRETS.get("auth", [])
        
        # Assert SECRET_KEY is marked as critical
        assert "SECRET_KEY" in critical_secrets, (
            "SECRET_KEY must be marked as critical for auth service. "
            "Critical secrets cause deployment failure if missing, preventing "
            "the silent failure that occurred in the staging regression."
        )
    
    def test_secret_key_marked_as_critical_for_backend_service(self):
        """Test that SECRET_KEY is marked as critical for backend service."""
        # Get critical secrets for backend service
        critical_secrets = SecretConfig.CRITICAL_SECRETS.get("backend", [])
        
        # Assert SECRET_KEY is marked as critical
        assert "SECRET_KEY" in critical_secrets, (
            "SECRET_KEY must be marked as critical for backend service."
        )
    
    def test_secret_key_has_gsm_mapping(self):
        """Test that SECRET_KEY has a proper Google Secret Manager mapping.
        
        The regression occurred because the SECRET_KEY mapping was removed,
        so the deployment script couldn't find the secret in GSM.
        """
        # Get GSM mapping for SECRET_KEY
        gsm_mapping = SecretConfig.get_gsm_mapping("SECRET_KEY")
        
        # Assert mapping exists and points to correct GSM secret
        assert gsm_mapping is not None, (
            "SECRET_KEY must have a GSM mapping. "
            "Missing mapping caused deployment script failure."
        )
        assert gsm_mapping == "secret-key-staging", (
            f"SECRET_KEY must map to 'secret-key-staging', got '{gsm_mapping}'"
        )
    
    def test_auth_service_secrets_string_contains_secret_key(self):
        """Test that the generated secrets string for auth service includes SECRET_KEY.
        
        This test validates the complete flow from secret definition to 
        deployment script parameter generation.
        """
        # Generate secrets string for auth service
        secrets_string = SecretConfig.generate_secrets_string("auth", "staging")
        
        # Assert SECRET_KEY mapping is in the string
        expected_mapping = "SECRET_KEY=secret-key-staging:latest"
        assert expected_mapping in secrets_string, (
            f"Auth service secrets string must contain '{expected_mapping}'. "
            f"Generated string: {secrets_string}"
        )
    
    def test_backend_service_secrets_string_contains_secret_key(self):
        """Test that the generated secrets string for backend service includes SECRET_KEY."""
        # Generate secrets string for backend service  
        secrets_string = SecretConfig.generate_secrets_string("backend", "staging")
        
        # Assert SECRET_KEY mapping is in the string
        expected_mapping = "SECRET_KEY=secret-key-staging:latest"
        assert expected_mapping in secrets_string, (
            f"Backend service secrets string must contain '{expected_mapping}'. "
            f"Generated string: {secrets_string}"
        )
    
    def test_no_duplicate_secret_key_mappings(self):
        """Test that SECRET_KEY appears only once in each service's secrets string.
        
        Duplicate mappings could cause deployment script errors.
        """
        # Test auth service - use more precise pattern to avoid matching JWT_SECRET_KEY
        auth_secrets_string = SecretConfig.generate_secrets_string("auth", "staging")
        # Split by comma and count exact matches
        auth_mappings = [mapping.strip() for mapping in auth_secrets_string.split(",")]
        secret_key_mappings = [mapping for mapping in auth_mappings if mapping.startswith("SECRET_KEY=")]
        assert len(secret_key_mappings) == 1, (
            f"SECRET_KEY should appear exactly once in auth secrets string, "
            f"found {len(secret_key_mappings)} occurrences: {secret_key_mappings}"
        )
        
        # Test backend service
        backend_secrets_string = SecretConfig.generate_secrets_string("backend", "staging")
        backend_mappings = [mapping.strip() for mapping in backend_secrets_string.split(",")]
        secret_key_mappings = [mapping for mapping in backend_mappings if mapping.startswith("SECRET_KEY=")]
        assert len(secret_key_mappings) == 1, (
            f"SECRET_KEY should appear exactly once in backend secrets string, "
            f"found {len(secret_key_mappings)} occurrences: {secret_key_mappings}"
        )
    
    def test_validate_critical_secrets_detects_missing_secret_key(self):
        """Test that missing SECRET_KEY is detected by critical secrets validation.
        
        This test ensures the validation system would catch the regression
        before deployment completes.
        """
        # Test with SECRET_KEY missing from available secrets
        available_secrets_without_secret_key = {
            "JWT_SECRET_KEY", "SERVICE_SECRET", "POSTGRES_PASSWORD"
        }
        
        # Validate auth service secrets
        missing_auth = SecretConfig.validate_critical_secrets(
            "auth", available_secrets_without_secret_key
        )
        assert "SECRET_KEY" in missing_auth, (
            "validate_critical_secrets should detect missing SECRET_KEY for auth service"
        )
        
        # Validate backend service secrets  
        missing_backend = SecretConfig.validate_critical_secrets(
            "backend", available_secrets_without_secret_key
        )
        assert "SECRET_KEY" in missing_backend, (
            "validate_critical_secrets should detect missing SECRET_KEY for backend service"
        )
    
    def test_secret_key_explanation_indicates_criticality(self):
        """Test that SECRET_KEY explanation indicates its critical nature.
        
        Good documentation helps prevent accidental removal.
        """
        explanation = SecretConfig.explain_secret("SECRET_KEY")
        
        # Assert explanation indicates criticality
        assert "CRITICAL" in explanation.upper(), (
            "SECRET_KEY explanation should indicate its critical nature"
        )
        assert "required" in explanation.lower(), (
            "SECRET_KEY explanation should indicate it's required"
        )
    
    @pytest.mark.parametrize("service_name", ["auth", "backend"])
    def test_secret_key_in_authentication_category(self, service_name):
        """Test that SECRET_KEY is properly categorized in authentication category.
        
        Proper categorization helps with organization and prevents accidental removal.
        """
        service_secrets = SecretConfig.get_service_secrets(service_name)
        
        # Assert authentication category exists
        assert "authentication" in service_secrets, (
            f"{service_name} service must have authentication secrets category"
        )
        
        # Assert SECRET_KEY is in authentication category
        auth_secrets = service_secrets["authentication"]
        assert "SECRET_KEY" in auth_secrets, (
            f"SECRET_KEY must be in authentication category for {service_name} service"
        )
    
    def test_secret_categories_for_secret_key(self):
        """Test that SECRET_KEY belongs to the correct categories for each service."""
        # Test auth service
        auth_categories = SecretConfig.get_secret_categories("auth", "SECRET_KEY")
        assert "authentication" in auth_categories, (
            "SECRET_KEY should be in authentication category for auth service"
        )
        
        # Test backend service
        backend_categories = SecretConfig.get_secret_categories("backend", "SECRET_KEY")
        assert "authentication" in backend_categories, (
            "SECRET_KEY should be in authentication category for backend service"
        )


@pytest.mark.unit
class RedisConfigurationRegressionTests:
    """Test suite to prevent Redis configuration regressions.
    
    The commit also fixed Redis configuration issues:
    - AuthService session_manager references (should use redis_client)
    - Duplicate Redis host/port mappings (should use REDIS_URL only)
    """
    
    def test_auth_service_has_redis_secrets(self):
        """Test that auth service has all required Redis secrets."""
        auth_secrets = SecretConfig.get_all_service_secrets("auth")
        
        # Check for Redis-related secrets
        redis_secrets = ["REDIS_HOST", "REDIS_PORT", "REDIS_URL", "REDIS_PASSWORD"]
        for secret in redis_secrets:
            assert secret in auth_secrets, (
                f"{secret} must be available for auth service Redis configuration"
            )
    
    def test_backend_service_has_redis_secrets(self):
        """Test that backend service has all required Redis secrets."""
        backend_secrets = SecretConfig.get_all_service_secrets("backend")
        
        # Check for Redis-related secrets
        redis_secrets = ["REDIS_HOST", "REDIS_PORT", "REDIS_URL", "REDIS_PASSWORD"]
        for secret in redis_secrets:
            assert secret in backend_secrets, (
                f"{secret} must be available for backend service Redis configuration"
            )
    
    def test_redis_host_has_gsm_mapping(self):
        """Test that REDIS_HOST has proper GSM mapping.
        
        The commit mentioned adding value to redis-host-staging secret.
        """
        gsm_mapping = SecretConfig.get_gsm_mapping("REDIS_HOST")
        assert gsm_mapping == "redis-host-staging", (
            f"REDIS_HOST must map to 'redis-host-staging', got '{gsm_mapping}'"
        )
    
    def test_redis_port_has_gsm_mapping(self):
        """Test that REDIS_PORT has proper GSM mapping."""
        gsm_mapping = SecretConfig.get_gsm_mapping("REDIS_PORT")
        assert gsm_mapping == "redis-port-staging", (
            f"REDIS_PORT must map to 'redis-port-staging', got '{gsm_mapping}'"
        )
    
    def test_redis_url_has_gsm_mapping(self):
        """Test that REDIS_URL has proper GSM mapping."""
        gsm_mapping = SecretConfig.get_gsm_mapping("REDIS_URL")
        assert gsm_mapping == "redis-url-staging", (
            f"REDIS_URL must map to 'redis-url-staging', got '{gsm_mapping}'"
        )


@pytest.mark.unit
class OAuthConfigurationRegressionTests:
    """Test suite to prevent OAuth configuration regressions.
    
    The commit mentioned that OAuth variable updates caused the SECRET_KEY removal.
    This ensures OAuth configuration is correct without breaking other secrets.
    """
    
    def test_auth_service_oauth_secrets_have_staging_suffix(self):
        """Test that auth service OAuth secrets use environment-specific naming."""
        auth_secrets = SecretConfig.get_all_service_secrets("auth")
        
        # Auth service should use environment-specific OAuth secret names
        assert "GOOGLE_OAUTH_CLIENT_ID_STAGING" in auth_secrets, (
            "Auth service should use GOOGLE_OAUTH_CLIENT_ID_STAGING"
        )
        assert "GOOGLE_OAUTH_CLIENT_SECRET_STAGING" in auth_secrets, (
            "Auth service should use GOOGLE_OAUTH_CLIENT_SECRET_STAGING"
        )
    
    def test_backend_service_oauth_secrets_simplified_naming(self):
        """Test that backend service OAuth secrets use simplified naming."""
        backend_secrets = SecretConfig.get_all_service_secrets("backend")
        
        # Backend service should use simplified OAuth secret names
        assert "GOOGLE_CLIENT_ID" in backend_secrets, (
            "Backend service should use GOOGLE_CLIENT_ID"
        )
        assert "GOOGLE_CLIENT_SECRET" in backend_secrets, (
            "Backend service should use GOOGLE_CLIENT_SECRET"
        )
    
    def test_oauth_secrets_have_correct_gsm_mappings(self):
        """Test that OAuth secrets map to the same GSM secrets despite different names."""
        # Both services should map to the same underlying GSM secrets
        auth_client_id_mapping = SecretConfig.get_gsm_mapping("GOOGLE_OAUTH_CLIENT_ID_STAGING")
        backend_client_id_mapping = SecretConfig.get_gsm_mapping("GOOGLE_CLIENT_ID")
        
        assert auth_client_id_mapping == "google-oauth-client-id-staging", (
            "Auth service OAuth client ID should map to google-oauth-client-id-staging"
        )
        assert backend_client_id_mapping == "google-oauth-client-id-staging", (
            "Backend service OAuth client ID should map to google-oauth-client-id-staging"
        )
        
        # Both should point to the same GSM secret
        assert auth_client_id_mapping == backend_client_id_mapping, (
            "Both services should use the same underlying OAuth client ID secret"
        )
