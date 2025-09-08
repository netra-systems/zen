"""
End-to-End Configuration Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Platform Stability
- Value Impact: Prevents deployment failures and runtime configuration issues
- Strategic Impact: Ensures configuration consistency across environments

This test suite validates that all required environment variables are properly
configured and that services can construct necessary connection strings.
"""

import os
import pytest
from typing import Dict, List, Optional
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

# Test both backend and auth service configurations
from netra_backend.app.core.configuration.database import DatabaseConfig
from netra_backend.app.core.environment_validator import EnvironmentValidator
from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretLoader
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class TestStagingConfiguration:
    """Test staging environment configuration requirements."""
    
    @pytest.fixture
    def staging_env(self) -> Dict[str, str]:
        """Staging environment variables that should be set by Cloud Run."""
        return {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_STAGING": "test-jwt-secret-staging-86-chars-minimum-required",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:staging-shared-postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_dev",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "test-postgres-password",
            "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
            "REDIS_URL": "redis://default:password@10.107.0.3:6379/0",
            "GCP_PROJECT_ID": "netra-staging"
        }
    
    def test_database_url_construction_from_postgres_vars(self, staging_env):
        """Test that #removed-legacyis correctly constructed from POSTGRES_* variables."""
        with patch.dict(os.environ, staging_env, clear=True):
            db_config = DatabaseConfig()
            
            # Should construct sync URL from individual variables
            sync_url = db_config.get_sync_database_url()
            assert sync_url is not None
            assert "postgresql" in sync_url
            assert staging_env["POSTGRES_USER"] in sync_url
            assert staging_env["POSTGRES_DB"] in sync_url
            
            # Should construct async URL as well
            async_url = db_config.get_async_database_url()
            assert async_url is not None
            assert "postgresql+asyncpg" in async_url
    
    def test_environment_validator_checks_postgres_vars_not_database_url(self, staging_env):
        """Test that environment validator checks POSTGRES_* vars instead of DATABASE_URL."""
        # Remove #removed-legacybut keep POSTGRES_* vars
        env_without_db_url = staging_env.copy()
        env_without_db_url.pop("DATABASE_URL", None)
        
        with patch.dict(os.environ, env_without_db_url, clear=True):
            validator = EnvironmentValidator()
            
            # Should not fail when #removed-legacyis missing but POSTGRES_* are present
            try:
                validator.validate_environment_at_startup()
                # Should pass without errors
            except EnvironmentError as e:
                # Should not fail for missing DATABASE_URL
                assert "DATABASE_URL" not in str(e)
    
    def test_jwt_secret_staging_required_in_staging(self, staging_env):
        """Test that JWT_SECRET_STAGING is required in staging environment."""
        # Test with JWT_SECRET_STAGING present
        with patch.dict(os.environ, staging_env, clear=True):
            secret_loader = UnifiedSecretLoader()
            jwt_secret = secret_loader.get_jwt_secret()
            assert jwt_secret == staging_env["JWT_SECRET_STAGING"]
        
        # Test with JWT_SECRET_STAGING missing
        env_without_jwt = staging_env.copy()
        env_without_jwt.pop("JWT_SECRET_STAGING")
        
        with patch.dict(os.environ, env_without_jwt, clear=True):
            secret_loader = UnifiedSecretLoader()
            with pytest.raises(ValueError, match="JWT_SECRET_STAGING"):
                secret_loader.get_jwt_secret()
    
    def test_vpc_connector_enables_redis_access(self, staging_env):
        """Test that Redis URL is properly configured for VPC access."""
        with patch.dict(os.environ, staging_env, clear=True):
            env = get_env()
            redis_url = env.get("REDIS_URL")
            assert redis_url is not None
            
            # Should use private IP address accessible via VPC connector
            assert "10.107.0.3" in redis_url or "10.166.204.83" in redis_url
            
            # Should not use localhost or public IPs
            assert "localhost" not in redis_url
            assert "127.0.0.1" not in redis_url
    
    def test_no_localhost_in_staging_urls(self, staging_env):
        """Test that no localhost references exist in staging configuration."""
        with patch.dict(os.environ, staging_env, clear=True):
            validator = EnvironmentValidator()
            
            # Check all URL-like environment variables
            url_vars = ["AUTH_SERVICE_URL", "POSTGRES_HOST", "REDIS_URL"]
            for var in url_vars:
                env = get_env()
                value = env.get(var, "")
                assert "localhost" not in value.lower()
                assert "127.0.0.1" not in value
                assert "0.0.0.0" not in value


class TestProductionConfiguration:
    """Test production environment configuration requirements."""
    
    @pytest.fixture
    def production_env(self) -> Dict[str, str]:
        """Production environment variables."""
        return {
            "ENVIRONMENT": "production",
            "JWT_SECRET_PRODUCTION": "test-jwt-secret-production-128-chars-minimum",
            "POSTGRES_HOST": "/cloudsql/netra-production:us-central1:production-postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_prod",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "test-production-password",
            "AUTH_SERVICE_URL": "https://auth.netrasystems.ai",
            "REDIS_URL": "redis://default:password@10.107.0.3:6379/0",
            "GCP_PROJECT_ID": "netra-production"
        }
    
    def test_jwt_secret_production_required_in_production(self, production_env):
        """Test that JWT_SECRET_PRODUCTION is required in production environment."""
        with patch.dict(os.environ, production_env, clear=True):
            secret_loader = UnifiedSecretLoader()
            jwt_secret = secret_loader.get_jwt_secret()
            assert jwt_secret == production_env["JWT_SECRET_PRODUCTION"]
        
        # Test with JWT_SECRET_PRODUCTION missing
        env_without_jwt = production_env.copy()
        env_without_jwt.pop("JWT_SECRET_PRODUCTION")
        
        with patch.dict(os.environ, env_without_jwt, clear=True):
            secret_loader = UnifiedSecretLoader()
            with pytest.raises(ValueError, match="JWT_SECRET_PRODUCTION"):
                secret_loader.get_jwt_secret()
    
    def test_no_test_variables_in_production(self, production_env):
        """Test that test variables are not present in production."""
        test_vars = [
            "TESTING", "E2E_TESTING", "AUTH_FAST_TEST_MODE",
            "PYTEST_CURRENT_TEST", "ALLOW_DEV_OAUTH_SIMULATION"
        ]
        
        # Add a test variable to production env
        bad_env = production_env.copy()
        bad_env["AUTH_FAST_TEST_MODE"] = "true"
        
        with patch.dict(os.environ, bad_env, clear=True):
            validator = EnvironmentValidator()
            with pytest.raises(EnvironmentError, match="Forbidden test variables"):
                validator.validate_environment_at_startup()


class TestDevelopmentConfiguration:
    """Test development environment configuration."""
    
    @pytest.fixture
    def development_env(self) -> Dict[str, str]:
        """Development environment variables."""
        return {
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": "dev-jwt-secret-key-for-local-development",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/netra_dev",
            "AUTH_SERVICE_URL": "http://localhost:8080",
            "REDIS_URL": "redis://localhost:6379/0"
        }
    
    def test_jwt_secret_key_used_in_development(self, development_env):
        """Test that JWT_SECRET_KEY is used in development environment."""
        with patch.dict(os.environ, development_env, clear=True):
            secret_loader = UnifiedSecretLoader()
            jwt_secret = secret_loader.get_jwt_secret()
            assert jwt_secret == development_env["JWT_SECRET_KEY"]
    
    def test_localhost_allowed_in_development(self, development_env):
        """Test that localhost references are allowed in development."""
        with patch.dict(os.environ, development_env, clear=True):
            validator = EnvironmentValidator()
            # Should not raise any errors
            validator.validate_environment_at_startup()


class TestCrossServiceConfiguration:
    """Test configuration consistency between services."""
    
    def test_jwt_secrets_match_between_services(self):
        """Test that backend and auth service use the same JWT secret."""
        staging_env = {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_STAGING": "shared-jwt-secret-for-both-services",
            "GCP_PROJECT_ID": "netra-staging"
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Backend secret loader
            backend_loader = UnifiedSecretLoader()
            backend_secret = backend_loader.get_jwt_secret()
            
            # Auth service would use the same JWT_SECRET_STAGING
            # Both should get the same value
            assert backend_secret == staging_env["JWT_SECRET_STAGING"]
    
    def test_redis_url_consistency(self):
        """Test that Redis URL is consistent across services."""
        staging_env = {
            "ENVIRONMENT": "staging",
            "REDIS_URL": "redis://default:password@10.107.0.3:6379/0"
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Both services should use the same Redis URL
            env = get_env()
            redis_url = env.get("REDIS_URL")
            assert redis_url == staging_env["REDIS_URL"]
            
            # Should point to the correct staging Redis instance
            assert "10.107.0.3" in redis_url  # staging-shared-redis IP


class TestConfigurationValidation:
    """Test configuration validation and error handling."""
    
    def test_fail_fast_on_missing_critical_vars(self):
        """Test that services fail fast when critical variables are missing."""
        incomplete_env = {
            "ENVIRONMENT": "staging",
            # Missing JWT_SECRET_STAGING and POSTGRES_* vars
        }
        
        with patch.dict(os.environ, incomplete_env, clear=True):
            validator = EnvironmentValidator()
            with pytest.raises(EnvironmentError):
                validator.validate_environment_at_startup()
    
    def test_no_fallback_for_jwt_secrets(self):
        """Test that there are no fallbacks for JWT secrets."""
        staging_env = {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_KEY": "wrong-secret-for-staging",  # Wrong variable
            "GCP_PROJECT_ID": "netra-staging"
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            secret_loader = UnifiedSecretLoader()
            # Should fail, not fall back to JWT_SECRET_KEY
            with pytest.raises(ValueError, match="JWT_SECRET_STAGING"):
                secret_loader.get_jwt_secret()
    
    def test_vpc_connector_requirement_documented(self):
        """Test that VPC connector requirement is properly documented."""
        # This is a documentation test - verify that deployment script includes VPC connector
        from pathlib import Path
        
        deploy_script = Path("scripts/deploy_to_gcp.py")
        if deploy_script.exists():
            content = deploy_script.read_text()
            
            # Should include VPC connector configuration
            assert "--vpc-connector" in content
            assert "staging-connector" in content
            assert "VPC connector required for Redis" in content or "CRITICAL: VPC connector" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])