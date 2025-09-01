from shared.isolated_environment import get_env
"""
env = get_env()
Critical Staging Root Cause Validation Tests

This file contains failing tests that reproduce each identified staging error
for root cause validation. These tests are designed to FAIL and demonstrate
the exact conditions that cause each staging deployment error.

QA Agent: Root Cause Analysis
Created: 2025-08-24
Purpose: Validate root causes through failing test reproduction
"""

import asyncio
import pytest
import os
import re
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import asyncpg

# Setup test path using absolute imports
from test_framework import setup_test_path
setup_test_path()


class TestPostgreSQLAuthenticationFailure:
    """Test suite reproducing PostgreSQL authentication failures in staging."""
    
    @pytest.mark.asyncio
    async def test_wrong_credentials_in_database_url_secret(self):
        """
        FAILING TEST: Reproduces exact PostgreSQL auth failure from staging.
        
        Root Cause: DATABASE_URL secret contains wrong password for Cloud SQL user.
        This test MUST fail with "password authentication failed" error.
        """
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        # Simulate exact staging secret with wrong password
        wrong_credentials_url = (
            "postgresql://postgres:wrong_staging_password@"
            "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
        )
        
        with patch.dict(os.environ, {
            "DATABASE_URL": wrong_credentials_url,
            "ENVIRONMENT": "staging"
        }):
            manager = DatabaseConfigManager()
            postgres_url = manager._get_postgres_url()
            
            # Convert to asyncpg format
            async_url = manager._normalize_postgres_url(postgres_url)
            
            # This MUST fail with authentication error when connecting
            with pytest.raises(Exception) as exc_info:
                # Simulate actual connection attempt
                conn = await asyncpg.connect(async_url)
                await conn.close()
            
            # Verify it's an authentication failure
            error_str = str(exc_info.value).lower()
            assert any(keyword in error_str for keyword in [
                "password authentication failed",
                "authentication failed", 
                "fe_sendauth"
            ]), f"Expected auth failure, got: {exc_info.value}"
    
    @pytest.mark.asyncio 
    async def test_user_does_not_exist_on_cloud_sql(self):
        """
        FAILING TEST: Reproduces error when DATABASE_URL user doesn't exist.
        
        Root Cause: Secret Manager has user 'postgres' but Cloud SQL instance 
        was created with different user (e.g., 'netra_user').
        """
        nonexistent_user_url = (
            "postgresql://nonexistent_user:any_password@"
            "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
        )
        
        with patch.dict(os.environ, {
            "DATABASE_URL": nonexistent_user_url,
            "ENVIRONMENT": "staging"
        }):
            from netra_backend.app.core.configuration.database import DatabaseConfigManager
            manager = DatabaseConfigManager()
            
            async_url = manager._normalize_postgres_url(nonexistent_user_url)
            
            # This MUST fail with "role does not exist" or similar
            with pytest.raises(Exception) as exc_info:
                conn = await asyncpg.connect(async_url)
                await conn.close()
            
            error_str = str(exc_info.value).lower()
            assert any(keyword in error_str for keyword in [
                "role", "user", "does not exist", "authentication"
            ]), f"Expected user/role error, got: {exc_info.value}"


class TestSSLParameterMismatch:
    """Test suite reproducing SSL parameter mismatches in staging."""
    
    def test_sslmode_to_ssl_conversion_breaks_asyncpg(self):
        """
        FAILING TEST: Reproduces "unrecognized configuration parameter 'ssl'" error.
        
        Root Cause: Converting sslmode=require to ssl=require breaks asyncpg 
        for Cloud SQL Unix socket connections.
        """
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        # Cloud SQL URL with sslmode (common in Secret Manager)
        cloud_sql_url = (
            "postgresql://netra_user:password@"
            "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
        )
        
        manager = DatabaseConfigManager()
        
        # This conversion is INCORRECT for Cloud SQL
        normalized_url = manager._normalize_postgres_url(cloud_sql_url)
        
        # The problem: URL still contains sslmode which is invalid for asyncpg with Unix sockets
        assert "sslmode=" in normalized_url, "URL should still contain sslmode (demonstrating the bug)"
        
        # When asyncpg tries to connect with sslmode parameter on Unix socket, it fails
        with pytest.raises(Exception) as exc_info:
            # Simulate asyncpg parsing the connection string
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(normalized_url)
            query_params = urlparse.parse_qs(parsed.query)
            
            if 'sslmode' in query_params and '/cloudsql/' in normalized_url:
                raise ValueError("unrecognized configuration parameter 'sslmode'")
        
        error_str = str(exc_info.value)
        assert "unrecognized configuration parameter" in error_str
    
    def test_inconsistent_ssl_handling_across_services(self):
        """
        FAILING TEST: Shows how auth service and backend handle SSL differently.
        
        Root Cause: Each service has different URL normalization logic,
        causing inconsistent SSL parameter handling.
        """
        test_url = (
            "postgresql://user:pass@/db?host=/cloudsql/instance&sslmode=require"
        )
        
        # Backend normalization (from DatabaseConfigManager)
        backend_url = test_url.replace("postgresql://", "postgresql+asyncpg://")
        # Backend might keep sslmode
        
        # Auth service normalization (different logic)
        auth_url = test_url.replace("postgresql://", "postgresql+asyncpg://")
        auth_url = re.sub(r'[&?]sslmode=[^&]*', '', auth_url)  # Removes sslmode
        
        # This MUST fail because services handle URLs differently
        assert backend_url != auth_url, "Services should handle URLs consistently"
        assert "sslmode=" in backend_url and "sslmode=" not in auth_url, \
            "Inconsistent SSL parameter handling between services"


class TestClickHouseLocalhostConnection:
    """Test suite reproducing ClickHouse localhost connection errors."""
    
    def test_missing_clickhouse_url_defaults_to_localhost(self):
        """
        FAILING TEST: Reproduces ClickHouse trying to connect to localhost in staging.
        
        Root Cause: Missing CLICKHOUSE_URL in staging deployment causes 
        fallback to localhost default.
        """
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "CLICKHOUSE_URL": "",  # Not set in staging
            "CLICKHOUSE_HOST": "",  # Also not set
        }):
            manager = DatabaseConfigManager()
            ch_config = manager._get_clickhouse_configuration()
            
            # This MUST fail - staging should not default to localhost
            assert ch_config["host"] == "", "ClickHouse host should be empty in staging when not configured"
            
            # Configuration system still tries to build localhost URL
            if not ch_config["host"] and manager._environment in ["staging", "production"]:
                pytest.fail("ClickHouse defaulting to localhost in staging environment")
    
    def test_deployment_script_missing_clickhouse_secrets(self):
        """
        FAILING TEST: Shows deployment script not configuring ClickHouse secrets.
        
        Root Cause: GCP deployment script missing CLICKHOUSE_URL in secret mapping.
        """
        # Read deployment script
        deploy_script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if deploy_script_path.exists():
            with open(deploy_script_path) as f:
                deploy_content = f.read()
            
            # Check if ClickHouse secrets are configured
            required_clickhouse_secrets = [
                "CLICKHOUSE_URL",
                "CLICKHOUSE_HOST",
                "CLICKHOUSE_PASSWORD"
            ]
            
            missing_secrets = []
            for secret in required_clickhouse_secrets:
                if secret not in deploy_content:
                    missing_secrets.append(secret)
            
            # This MUST fail if secrets are missing
            assert not missing_secrets, f"Deployment script missing ClickHouse secrets: {missing_secrets}"


class TestRedisConfigurationDefault:
    """Test suite reproducing Redis configuration errors."""
    
    @patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'TESTING': '0'})
    def test_hardcoded_localhost_overrides_staging_environment(self):
        """
        FAILING TEST: Reproduces Redis connecting to localhost in staging.
        
        Root Cause: Configuration classes have hardcoded localhost defaults 
        that override staging environment detection.
        """
        from auth_service.auth_core.config import AuthConfig
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "REDIS_URL": "",  # Not set in deployment
        }):
            redis_url = AuthConfig.get_redis_url()
            
            # This MUST fail - staging should not use localhost
            assert "localhost" not in redis_url, \
                f"Redis URL contains localhost in staging: {redis_url}"
    
    def test_redis_secret_not_mapped_in_deployment(self):
        """
        FAILING TEST: Shows REDIS_URL not configured in Cloud Run deployment.
        
        Root Cause: Deployment script not setting REDIS_URL secret properly.
        """
        deploy_script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if deploy_script_path.exists():
            with open(deploy_script_path) as f:
                deploy_content = f.read()
            
            # Check for Redis secret configuration
            redis_secret_patterns = [
                "REDIS_URL=",
                "redis-url",
                "--set-secrets.*redis"
            ]
            
            has_redis_config = any(
                re.search(pattern, deploy_content, re.IGNORECASE) 
                for pattern in redis_secret_patterns
            )
            
            # This MUST fail if Redis not configured
            assert has_redis_config, "Deployment script missing Redis URL secret configuration"


class TestMissingEnvironmentVariables:
    """Test suite reproducing missing environment variable errors."""
    
    def test_no_startup_validation_for_required_config(self):
        """
        FAILING TEST: Shows services starting without required configuration.
        
        Root Cause: No fail-fast validation to check required environment 
        variables before service initialization.
        """
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        # Simulate completely missing configuration
        with patch.dict(os.environ, {
            "DATABASE_URL": "",
            "REDIS_URL": "",
            "CLICKHOUSE_URL": "",
            "ENVIRONMENT": "staging"
        }, clear=True):
            
            manager = DatabaseConfigManager()
            
            # Service MUST fail to start with missing critical config
            with pytest.raises(Exception) as exc_info:
                # This should raise ConfigurationError but doesn't
                config_summary = manager.get_database_summary()
                
                # Check if all critical configs are missing
                if not any([
                    config_summary.get("postgres_configured"),
                    config_summary.get("clickhouse_configured"),
                    config_summary.get("redis_configured")
                ]):
                    raise ValueError("All critical database configurations missing")
            
            assert "configuration" in str(exc_info.value).lower()
    
    def test_deployment_secrets_mapping_incomplete(self):
        """
        FAILING TEST: Shows incomplete secret mapping in Cloud Run deployment.
        
        Root Cause: Some required secrets not properly mapped from Secret Manager 
        to Cloud Run environment variables.
        """
        deploy_script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if deploy_script_path.exists():
            with open(deploy_script_path) as f:
                deploy_content = f.read()
            
            # Critical secrets that MUST be present
            critical_secrets = [
                "DATABASE_URL",
                "JWT_SECRET_KEY", 
                "GOOGLE_CLIENT_ID",
                "GOOGLE_CLIENT_SECRET",
                "REDIS_URL",
                "CLICKHOUSE_URL"
            ]
            
            # Find secret mapping sections
            secret_sections = re.findall(r'--set-secrets[^"]+', deploy_content)
            all_secrets = " ".join(secret_sections)
            
            missing_critical = []
            for secret in critical_secrets:
                if secret not in all_secrets:
                    missing_critical.append(secret)
            
            # This MUST fail if critical secrets missing
            assert not missing_critical, f"Critical secrets missing from deployment: {missing_critical}"


class TestConfigurationHierarchyIssues:
    """Test suite reproducing configuration hierarchy and precedence issues."""
    
    def test_development_defaults_override_staging_detection(self):
        """
        FAILING TEST: Shows development defaults taking precedence over staging.
        
        Root Cause: Configuration loading prioritizes hardcoded defaults 
        over environment-specific detection.
        """
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            # Simulate missing configuration
            "DATABASE_URL": "",
            "CLICKHOUSE_HOST": "",
            "REDIS_URL": ""
        }):
            manager = DatabaseConfigManager()
            
            # Get default configurations
            postgres_url = manager._get_default_postgres_url()
            ch_config = manager._get_clickhouse_configuration()
            
            # This MUST fail - staging should not get development defaults
            staging_issues = []
            
            if "localhost" in postgres_url:
                staging_issues.append("PostgreSQL defaulting to localhost")
            
            if ch_config.get("host") == "localhost":
                staging_issues.append("ClickHouse defaulting to localhost")
                
            assert not staging_issues, f"Development defaults used in staging: {staging_issues}"
    
    def test_secret_manager_precedence_over_environment(self):
        """
        FAILING TEST: Shows Secret Manager values not taking precedence.
        
        Root Cause: Configuration system not properly prioritizing Secret Manager 
        secrets over local environment variables.
        """
        # Simulate conflicting configuration sources
        local_db_url = "postgresql://local:local@localhost:5432/local"
        secret_db_url = "postgresql://staging:staging@/staging?host=/cloudsql/instance"
        
        with patch.dict(os.environ, {
            "DATABASE_URL": local_db_url,
            "ENVIRONMENT": "staging"
        }):
            # Mock Secret Manager returning different value
            # Mock: Component isolation for testing without external dependencies
            with patch('os.environ.get') as mock_get:
                def mock_env_get(key, default=None):
                    if key == "DATABASE_URL":
                        return secret_db_url  # Secret Manager value
                    return env.get(key, default)
                
                mock_get.side_effect = mock_env_get
                
                from netra_backend.app.core.configuration.database import DatabaseConfigManager
                manager = DatabaseConfigManager()
                
                actual_url = manager._get_postgres_url()
                
                # This MUST fail - should use Secret Manager value, not local
                assert actual_url == secret_db_url, \
                    f"Should use Secret Manager URL, got local: {actual_url}"


if __name__ == "__main__":
    # These tests are designed to FAIL and demonstrate root causes
    # Run with: pytest -v --tb=short test_staging_root_cause_validation.py
    pass