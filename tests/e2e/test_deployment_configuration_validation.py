from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
End-to-End Deployment Configuration Validation Tests

Comprehensive failing tests that validate deployment configuration issues
across all services. These tests reproduce the exact conditions that cause
staging deployment failures.

QA Agent: E2E Configuration Validation
Created: 2025-08-24 
Purpose: Validate deployment configuration root causes end-to-end
"""

import pytest
import os
import json
import yaml
import subprocess
import sys
from pathlib import Path

# Setup test path



@pytest.mark.e2e
class TestDeploymentConfigurationFailures:
    """Test suite reproducing deployment configuration failures."""
    
    @pytest.mark.e2e
    def test_gcp_deployment_script_missing_critical_secrets(self):
        """
        FAILING TEST: Shows GCP deployment script missing critical secrets mapping.
        
        Root Cause: deploy_to_gcp.py not mapping all required secrets from 
        Secret Manager to Cloud Run environment variables.
        """
        deploy_script_path = Path(__file__).parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if not deploy_script_path.exists():
            pytest.skip("Deployment script not found")
        
        with open(deploy_script_path) as f:
            deploy_content = f.read()
        
        # Critical secrets required for staging deployment
        critical_secrets = {
            "backend": [
                "DATABASE_URL",
                "JWT_SECRET_KEY", 
                "SECRET_KEY",
                "GOOGLE_API_KEY",
                "FERNET_KEY",
                "GEMINI_API_KEY",
                "GOOGLE_CLIENT_ID",
                "GOOGLE_CLIENT_SECRET",
                "SERVICE_SECRET",
                "CLICKHOUSE_PASSWORD",
                "REDIS_URL"  # This is typically missing
            ],
            "auth": [
                "DATABASE_URL",
                "JWT_SECRET_KEY",
                "GOOGLE_CLIENT_ID", 
                "GOOGLE_CLIENT_SECRET",
                "SERVICE_SECRET",
                "SERVICE_ID",
                "REDIS_URL"  # This is typically missing
            ]
        }
        
        # Find secret mapping sections for each service
        missing_secrets = {}
        
        for service, secrets in critical_secrets.items():
            service_section_match = f"# {service.title()} service"
            service_start = deploy_content.find(service_section_match)
            
            if service_start == -1:
                missing_secrets[service] = secrets
                continue
            
            # Look for --set-secrets in the service section
            service_end = deploy_content.find("# ", service_start + 1)
            if service_end == -1:
                service_end = len(deploy_content)
            
            service_section = deploy_content[service_start:service_end]
            
            missing_for_service = []
            for secret in secrets:
                # Check if secret is mapped in deployment
                if f"{secret}=" not in service_section and secret.lower() not in service_section.lower():
                    missing_for_service.append(secret)
            
            if missing_for_service:
                missing_secrets[service] = missing_for_service
        
        # This MUST fail if critical secrets are missing
        assert not missing_secrets, \
            f"Critical secrets missing from deployment script: {missing_secrets}"
    
    @pytest.mark.e2e
    def test_cloud_run_service_configuration_incomplete(self):
        """
        FAILING TEST: Shows Cloud Run service configuration missing required settings.
        
        Root Cause: Cloud Run services not configured with proper Cloud SQL connections,
        memory limits, and environment variable mappings.
        """
        deploy_script_path = Path(__file__).parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if not deploy_script_path.exists():
            pytest.skip("Deployment script not found")
        
        with open(deploy_script_path) as f:
            deploy_content = f.read()
        
        # Required Cloud Run configurations
        required_cloud_run_configs = {
            "cloud_sql_instances": [
                "--add-cloudsql-instances",
                "netra-staging:us-central1:netra-postgres"
            ],
            "memory_cpu": [
                "--memory", "--cpu"
            ],
            "service_account": [
                "--service-account"
            ],
            "allow_unauthenticated": [
                "--allow-unauthenticated"
            ]
        }
        
        missing_configs = {}
        
        for config_category, required_flags in required_cloud_run_configs.items():
            missing_flags = []
            for flag in required_flags:
                if flag not in deploy_content:
                    missing_flags.append(flag)
            
            if missing_flags:
                missing_configs[config_category] = missing_flags
        
        # This MUST fail if required Cloud Run configs are missing
        assert not missing_configs, \
            f"Required Cloud Run configurations missing: {missing_configs}"
    
    @pytest.mark.e2e
    def test_secret_manager_secret_creation_incomplete(self):
        """
        FAILING TEST: Shows Secret Manager secrets not properly created for staging.
        
        Root Cause: Deployment script references secrets that don't exist in
        Secret Manager, causing Cloud Run deployment to fail.
        """
        deploy_script_path = Path(__file__).parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if not deploy_script_path.exists():
            pytest.skip("Deployment script not found")
        
        with open(deploy_script_path) as f:
            deploy_content = f.read()
        
        # Extract all secret references from deployment script
        import re
        secret_references = re.findall(r'([a-zA-Z-_]+)=([a-zA-Z-_]+):latest', deploy_content)
        
        # Secrets that should exist in Secret Manager
        expected_secrets = [
            "database-url-staging",
            "jwt-secret-key-staging", 
            "session-secret-key-staging",
            "openai-api-key-staging",
            "fernet-key-staging",
            "gemini-api-key-staging",
            "google-client-id-staging",
            "google-client-secret-staging",
            "service-secret-staging",
            "clickhouse-password-staging",
            "redis-url-staging"  # Often missing
        ]
        
        referenced_secrets = [secret_name for _, secret_name in secret_references]
        missing_secret_refs = []
        
        for expected in expected_secrets:
            if expected not in referenced_secrets:
                missing_secret_refs.append(expected)
        
        # This MUST fail if secret references are incomplete
        assert not missing_secret_refs, \
            f"Secret Manager secrets not referenced in deployment: {missing_secret_refs}"
    
    @pytest.mark.e2e
    def test_environment_variable_precedence_issues(self):
        """
        FAILING TEST: Shows environment variable precedence causing wrong values.
        
        Root Cause: Local development environment variables overriding 
        Cloud Run secret values during deployment.
        """
        # Simulate conflicting environment variables
        local_overrides = {
            "DATABASE_URL": "postgresql://localhost:5432/local_dev",
            "REDIS_URL": "redis://localhost:6379/0",
            "CLICKHOUSE_URL": "http://localhost:8123",
            "ENVIRONMENT": "development"  # Wrong environment
        }
        
        expected_staging_values = {
            "DATABASE_URL": "postgresql://.*cloudsql.*netra-staging",
            "REDIS_URL": "redis://.*staging.*",
            "CLICKHOUSE_URL": "https://.*staging.*",
            "ENVIRONMENT": "staging"
        }
        
        with patch.dict(os.environ, local_overrides):
            from netra_backend.app.core.configuration.database import DatabaseConfigManager
            
            manager = DatabaseConfigManager()
            
            # This MUST fail - local values should not override staging secrets
            precedence_issues = []
            
            # Check database URL
            db_url = manager._get_postgres_url()
            if "localhost" in db_url or "127.0.0.1" in db_url:
                precedence_issues.append("#removed-legacyusing local override in staging")
            
            # Check ClickHouse config
            ch_config = manager._get_clickhouse_configuration()
            if ch_config.get("host") == "localhost":
                precedence_issues.append("CLICKHOUSE_HOST using local override in staging")
            
            assert not precedence_issues, \
                f"Environment variable precedence issues: {precedence_issues}"


@pytest.mark.e2e
class TestServiceSpecificConfigurationFailures:
    """Test suite for service-specific configuration failures."""
    
    @pytest.mark.e2e
    def test_backend_clickhouse_configuration_missing(self):
        """
        FAILING TEST: Shows backend ClickHouse configuration missing in staging.
        
        Root Cause: Backend service deployed without CLICKHOUSE_URL or 
        CLICKHOUSE_HOST environment variables.
        """
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        # Simulate staging deployment missing ClickHouse config
        staging_env_without_clickhouse = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://user:pass@/db?host=/cloudsql/instance",
            # CLICKHOUSE_URL missing
            # CLICKHOUSE_HOST missing
        }
        
        with patch.dict(os.environ, staging_env_without_clickhouse, clear=True):
            manager = DatabaseConfigManager()
            ch_config = manager._get_clickhouse_configuration()
            
            # This MUST fail - staging should not use empty/default ClickHouse config
            staging_clickhouse_issues = []
            
            if not ch_config.get("host"):
                staging_clickhouse_issues.append("ClickHouse host not configured")
            
            if ch_config.get("host") == "localhost":
                staging_clickhouse_issues.append("ClickHouse defaulting to localhost")
            
            if not ch_config.get("password"):
                staging_clickhouse_issues.append("ClickHouse password not configured")
            
            assert not staging_clickhouse_issues, \
                f"Backend ClickHouse configuration issues in staging: {staging_clickhouse_issues}"
    
    @pytest.mark.e2e
    def test_auth_service_redis_configuration_missing(self):
        """
        FAILING TEST: Shows auth service Redis configuration missing in staging.
        
        Root Cause: Auth service deployed without REDIS_URL, falling back to
        localhost default which doesn't exist in Cloud Run.
        """
        from auth_service.auth_core.config import AuthConfig
        
        # Simulate staging deployment missing Redis config
        staging_env_without_redis = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://user:pass@/db?host=/cloudsql/instance",
            # REDIS_URL missing
        }
        
        with patch.dict(os.environ, staging_env_without_redis, clear=True):
            redis_url = AuthConfig.get_redis_url()
            
            # This MUST fail - staging should not use localhost Redis
            assert "localhost" not in redis_url, \
                f"Auth service using localhost Redis in staging: {redis_url}"
    
    @pytest.mark.e2e
    def test_frontend_api_url_configuration_mismatch(self):
        """
        FAILING TEST: Shows frontend API URL configuration mismatch in staging.
        
        Root Cause: Frontend deployed with wrong NEXT_PUBLIC_API_URL pointing
        to localhost instead of staging backend URL.
        """
        # Frontend environment variables for staging
        frontend_staging_env = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_API_URL": "http://localhost:8888",  # Wrong - should be staging URL
            "NEXT_PUBLIC_AUTH_URL": "http://localhost:8081"   # Wrong - should be staging URL
        }
        
        expected_staging_urls = {
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai"
        }
        
        with patch.dict(os.environ, frontend_staging_env):
            # This MUST fail - frontend using wrong URLs in staging
            url_mismatches = []
            
            for env_var, expected_url in expected_staging_urls.items():
                if actual_url and "localhost" in actual_url:
                    url_mismatches.append(f"{env_var} pointing to localhost in staging")
            
            assert not url_mismatches, \
                f"Frontend URL configuration mismatches: {url_mismatches}"


@pytest.mark.e2e
class TestDeploymentValidationFailures:
    """Test suite for deployment validation failures."""
    
    @pytest.mark.e2e
    def test_no_pre_deployment_configuration_validation(self):
        """
        FAILING TEST: Shows lack of pre-deployment configuration validation.
        
        Root Cause: Deployment script doesn't validate that all required
        secrets exist before attempting Cloud Run deployment.
        """
        deploy_script_path = Path(__file__).parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if not deploy_script_path.exists():
            pytest.skip("Deployment script not found")
        
        with open(deploy_script_path) as f:
            deploy_content = f.read()
        
        # Check for validation functions
        validation_patterns = [
            "validate_secrets",
            "check_secret_exists", 
            "validate_configuration",
            "pre_deployment_check"
        ]
        
        has_validation = any(pattern in deploy_content for pattern in validation_patterns)
        
        # This MUST fail if no pre-deployment validation exists
        assert has_validation, \
            "Deployment script missing pre-deployment configuration validation"
    
    @pytest.mark.e2e
    def test_no_post_deployment_health_verification(self):
        """
        FAILING TEST: Shows lack of post-deployment health verification.
        
        Root Cause: Deployment script doesn't verify services are healthy
        after deployment, leading to failed deployments being marked as successful.
        """
        deploy_script_path = Path(__file__).parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if not deploy_script_path.exists():
            pytest.skip("Deployment script not found")
        
        with open(deploy_script_path) as f:
            deploy_content = f.read()
        
        # Check for health verification
        health_check_patterns = [
            "/health",
            "health_check",
            "verify_deployment",
            "post_deployment",
            "service_ready"
        ]
        
        has_health_verification = any(pattern in deploy_content for pattern in health_check_patterns)
        
        # This MUST fail if no post-deployment verification exists
        assert has_health_verification, \
            "Deployment script missing post-deployment health verification"
    
    @pytest.mark.e2e
    def test_deployment_rollback_strategy_missing(self):
        """
        FAILING TEST: Shows deployment rollback strategy missing.
        
        Root Cause: No automated rollback when deployment fails or 
        services don't pass health checks.
        """
        deploy_script_path = Path(__file__).parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if not deploy_script_path.exists():
            pytest.skip("Deployment script not found")
        
        with open(deploy_script_path) as f:
            deploy_content = f.read()
        
        # Check for rollback functionality
        rollback_patterns = [
            "rollback",
            "revert",
            "previous_version",
            "rollback_deployment"
        ]
        
        has_rollback = any(pattern in deploy_content for pattern in rollback_patterns)
        
        # This MUST fail if no rollback strategy exists
        assert has_rollback, \
            "Deployment script missing rollback strategy for failed deployments"


@pytest.mark.e2e
class TestConfigurationIntegrationFailures:
    """Test suite for cross-service configuration integration failures."""
    
    @pytest.mark.e2e
    def test_service_to_service_url_mismatch(self):
        """
        FAILING TEST: Shows service-to-service URL configuration mismatches.
        
        Root Cause: Services configured with wrong URLs for communicating
        with each other in staging environment.
        """
        # Backend configuration for auth service URL
        backend_env = {
            "ENVIRONMENT": "staging",
            "AUTH_SERVICE_URL": "http://localhost:8081"  # Wrong - should be staging URL
        }
        
        # Auth service configuration for frontend URL  
        auth_env = {
            "ENVIRONMENT": "staging",
            "FRONTEND_URL": "http://localhost:3000"  # Wrong - should be staging URL
        }
        
        # Expected staging URLs
        expected_staging_service_urls = {
            "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
            "FRONTEND_URL": "https://app.staging.netrasystems.ai"
        }
        
        # Test backend configuration
        with patch.dict(os.environ, backend_env):
            from netra_backend.app.core.configuration.base import get_auth_service_url
            
            auth_url = get_auth_service_url()
            
            # This MUST fail - backend using wrong auth service URL
            if "localhost" in auth_url:
                pytest.fail(f"Backend using localhost auth service URL in staging: {auth_url}")
        
        # Test auth service configuration
        with patch.dict(os.environ, auth_env):
            from auth_service.auth_core.config import AuthConfig
            
            frontend_url = AuthConfig.get_frontend_url()
            
            # This MUST fail - auth service using wrong frontend URL
            if "localhost" in frontend_url:
                pytest.fail(f"Auth service using localhost frontend URL in staging: {frontend_url}")
    
    @pytest.mark.e2e
    def test_database_url_sharing_inconsistency(self):
        """
        FAILING TEST: Shows #removed-legacysharing inconsistency between services.
        
        Root Cause: Backend and auth service handle the same DATABASE_URL
        differently, causing connection issues.
        """
        shared_database_url = (
            "postgresql://netra_user:password@"
            "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
        )
        
        shared_env = {
            "DATABASE_URL": shared_database_url,
            "ENVIRONMENT": "staging"
        }
        
        with patch.dict(os.environ, shared_env):
            # Get backend normalized URL
            from netra_backend.app.core.configuration.database import DatabaseConfigManager
            backend_manager = DatabaseConfigManager()
            backend_url = backend_manager._get_postgres_url()
            backend_normalized = backend_manager._normalize_postgres_url(backend_url)
            
            # Get auth service normalized URL
            from auth_service.auth_core.config import AuthConfig
            auth_url = AuthConfig.get_database_url()
            
            # This MUST fail - services should handle URL consistently
            consistency_issues = []
            
            # Check driver consistency
            if "postgresql+asyncpg://" in backend_normalized and "postgresql+asyncpg://" not in auth_url:
                consistency_issues.append("Backend uses asyncpg driver, auth service doesn't")
            
            # Check SSL parameter handling
            backend_has_ssl = "ssl=" in backend_normalized or "sslmode=" in backend_normalized
            auth_has_ssl = "ssl=" in auth_url or "sslmode=" in auth_url
            
            if backend_has_ssl != auth_has_ssl:
                consistency_issues.append("Inconsistent SSL parameter handling between services")
            
            assert not consistency_issues, \
                f"Database URL handling inconsistency: {consistency_issues}"


if __name__ == "__main__":
    # These tests are designed to FAIL and demonstrate deployment configuration issues
    # Run with: pytest -v --tb=short test_deployment_configuration_validation.py
    pass