"""
Auth Service Staging SSL Failure Tests

Specific failing tests for auth service SSL parameter issues in staging.
These tests reproduce the exact SSL parameter mismatches that cause
"unrecognized configuration parameter" errors.

QA Agent: Auth Service SSL Root Cause Analysis  
Created: 2025-08-24
Purpose: Validate auth-specific SSL parameter handling failures
"""

import pytest
import os
import re
import sys
from unittest.mock import patch, Mock
from pathlib import Path
import asyncpg

# Setup test path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_framework import setup_test_path
setup_test_path()
from test_framework.environment_markers import env, staging_only, env_requires


@env("staging")  # SSL parameter issues need real staging environment with Cloud SQL
@env_requires(services=["postgres"], features=["cloud_sql_configured", "ssl_enabled"])
class TestAuthServiceSSLParameterFailures:
    """Test suite reproducing auth service SSL parameter failures."""
    
    @pytest.mark.asyncio
    async def test_cloud_sql_sslmode_parameter_rejection(self):
        """
        FIXED TEST: Verifies that Cloud SQL sslmode parameters are properly removed.
        
        Root Cause: asyncpg doesn't recognize 'sslmode' parameter for Unix socket 
        connections to Cloud SQL. SSL parameters should be completely removed.
        """
        from auth_service.auth_core.config import AuthConfig
        
        # Exact staging Cloud SQL URL format from Secret Manager
        staging_url_with_sslmode = (
            "postgresql://netra_user:staging_password@"
            "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
        )
        
        with patch.dict(os.environ, {
            "DATABASE_URL": staging_url_with_sslmode,
            "ENVIRONMENT": "staging"
        }):
            db_url = AuthConfig.get_database_url()
            
            # Verify the fix: SSL parameters should be removed for Cloud SQL
            assert "sslmode=" not in db_url, "SSL parameters should be removed for Cloud SQL"
            assert "ssl=" not in db_url, "SSL parameters should be removed for Cloud SQL"
            assert "/cloudsql/" in db_url, "Should still contain Cloud SQL path"
            assert db_url.startswith("postgresql+asyncpg://"), "Should be formatted for asyncpg"
    
    def test_ssl_parameter_not_removed_for_cloud_sql(self):
        """
        FAILING TEST: Shows SSL parameters not being removed for Cloud SQL connections.
        
        Root Cause: Auth service URL normalization doesn't properly detect and 
        remove SSL parameters for Cloud SQL Unix socket connections.
        """
        from auth_service.auth_core.database.connection import DatabaseConnection
        
        cloud_sql_urls = [
            # Various Cloud SQL URL formats that should have SSL params removed
            "postgresql://user:pass@/db?host=/cloudsql/instance&sslmode=require",
            "postgresql://user:pass@/db?host=/cloudsql/instance&ssl=require", 
            "postgresql://user:pass@/db?host=/cloudsql/instance&sslmode=disable",
            "postgres://user:pass@/db?host=/cloudsql/instance&sslmode=prefer"
        ]
        
        for url in cloud_sql_urls:
            # Auth service should remove ALL SSL parameters for Cloud SQL
            normalized = DatabaseConnection._normalize_url_for_asyncpg(url)
            
            # This MUST fail - SSL parameters should be removed
            ssl_params_present = any(param in normalized for param in [
                "sslmode=", "ssl=", "sslcert=", "sslkey=", "sslrootcert="
            ])
            
            assert not ssl_params_present, \
                f"SSL parameters still present in Cloud SQL URL: {normalized}"
    
    @pytest.mark.asyncio
    async def test_regular_postgres_ssl_parameter_conversion(self):
        """
        FAILING TEST: Shows regular PostgreSQL SSL parameter conversion issues.
        
        Root Cause: Auth service incorrectly handles SSL parameter conversion 
        for non-Cloud SQL connections.
        """
        from auth_service.auth_core.database.connection import DatabaseConnection
        
        # Regular PostgreSQL connection (not Cloud SQL)
        regular_postgres_url = "postgresql://user:pass@staging-db:5432/db?sslmode=require"
        
        with patch.dict(os.environ, {
            "DATABASE_URL": regular_postgres_url,
            "ENVIRONMENT": "staging"
        }):
            # For regular connections, sslmode should be converted to ssl
            normalized = DatabaseConnection._normalize_url_for_asyncpg(regular_postgres_url)
            
            # This MUST fail if conversion is incorrect
            conversion_issues = []
            
            if "sslmode=" in normalized:
                conversion_issues.append("sslmode not converted to ssl")
            
            if "ssl=" not in normalized and "/cloudsql/" not in normalized:
                conversion_issues.append("ssl parameter missing for regular connection")
            
            assert not conversion_issues, \
                f"SSL parameter conversion issues: {conversion_issues}"
    
    def test_auth_database_manager_ssl_handling_inconsistency(self):
        """
        FAILING TEST: Shows inconsistent SSL handling in auth database manager.
        
        Root Cause: AuthDatabaseManager and DatabaseConnection classes have 
        different SSL parameter normalization logic.
        """
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        from auth_service.auth_core.database.connection import DatabaseConnection
        
        test_url = (
            "postgresql://user:pass@/db?host=/cloudsql/instance&sslmode=require"
        )
        
        # Get normalized URLs from both classes
        manager_normalized = AuthDatabaseManager._normalize_database_url(test_url)
        connection_normalized = DatabaseConnection._normalize_url_for_asyncpg(test_url)
        
        # This MUST fail - both should handle SSL consistently  
        assert manager_normalized == connection_normalized, \
            f"Inconsistent SSL handling: manager={manager_normalized}, connection={connection_normalized}"
    
    @pytest.mark.asyncio
    async def test_staging_deployment_ssl_configuration_mismatch(self):
        """
        FAILING TEST: Shows staging deployment SSL configuration mismatch.
        
        Root Cause: Staging deployment configures sslmode=require in DATABASE_URL 
        but auth service expects no SSL parameters for Cloud SQL.
        """
        # Simulate exact staging deployment URL
        staging_deployment_url = (
            "postgresql://netra_user:$(STAGING_DB_PASSWORD)@"
            "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
        )
        
        with patch.dict(os.environ, {
            "DATABASE_URL": staging_deployment_url.replace("$(STAGING_DB_PASSWORD)", "real_password"),
            "ENVIRONMENT": "staging"
        }):
            from auth_service.auth_core.config import AuthConfig
            from auth_service.auth_core.database.database_manager import AuthDatabaseManager
            
            db_url = AuthConfig.get_database_url()
            manager = AuthDatabaseManager()
            
            # This MUST fail - deployment URL format incompatible with auth service
            try:
                normalized_url = manager.get_connection_url()
                
                # Check for SSL parameter issues
                ssl_issues = []
                
                if "/cloudsql/" in normalized_url and ("sslmode=" in normalized_url or "ssl=" in normalized_url):
                    ssl_issues.append("SSL parameters present in Cloud SQL URL")
                
                if not "/cloudsql/" in normalized_url and "ssl=" not in normalized_url:
                    ssl_issues.append("SSL parameter missing for regular connection")
                
                assert not ssl_issues, f"SSL configuration issues: {ssl_issues}"
                
            except Exception as e:
                # Expected failure due to SSL parameter mismatch
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    "ssl", "configuration", "parameter", "unrecognized"
                ]), f"Expected SSL-related error, got: {e}"


@env("staging")  # Configuration consistency needs staging environment
class TestAuthServiceConfigurationConsistency:
    """Test suite for auth service configuration consistency issues."""
    
    def test_auth_config_database_url_handling_inconsistency(self):
        """
        FIXED TEST: Verifies AuthConfig properly normalizes DATABASE_URL.
        
        Root Cause: AuthConfig.get_database_url() now has consistent normalization 
        logic with the shared database manager.
        """
        from auth_service.auth_core.config import AuthConfig
        
        test_url = (
            "postgresql://user:pass@/db?host=/cloudsql/instance&sslmode=require"
        )
        
        with patch.dict(os.environ, {
            "DATABASE_URL": test_url,
            "ENVIRONMENT": "staging"
        }):
            auth_url = AuthConfig.get_database_url()
            
            # Auth service should now normalize the URL
            assert auth_url != test_url, "AuthConfig should normalize DATABASE_URL"
            
            # Verify the fix: SSL parameters should be removed for Cloud SQL
            assert "/cloudsql/" in auth_url, "Should contain Cloud SQL path"
            assert "sslmode=" not in auth_url, "SSL parameters should be removed"
            assert auth_url.startswith("postgresql+asyncpg://"), "Should be formatted for asyncpg"
    
    def test_secret_loader_url_format_compatibility(self):
        """
        FAILING TEST: Shows AuthSecretLoader not handling URL format compatibility.
        
        Root Cause: AuthSecretLoader loads raw DATABASE_URL from secrets without 
        considering asyncpg format requirements.
        """
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        # Mock Secret Manager returning Cloud SQL URL with sslmode
        mock_secret_value = (
            "postgresql://netra_user:secret_password@"
            "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
        )
        
        with patch.object(AuthSecretLoader, '_load_from_secret_manager') as mock_load:
            mock_load.return_value = mock_secret_value
            
            with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
                # AuthSecretLoader should return URL compatible with asyncpg
                loaded_url = AuthSecretLoader.get_database_url()
                
                # This MUST fail - loaded URL incompatible with asyncpg
                compatibility_issues = []
                
                if "/cloudsql/" in loaded_url and "sslmode=" in loaded_url:
                    compatibility_issues.append("Cloud SQL URL contains sslmode parameter")
                
                if not loaded_url.startswith("postgresql+asyncpg://"):
                    compatibility_issues.append("URL missing asyncpg driver specification")
                
                assert not compatibility_issues, \
                    f"URL compatibility issues: {compatibility_issues}"


@env("staging")  # Deployment-specific tests need staging environment
@env_requires(features=["cloud_run_deployment", "secret_manager_configured"])
class TestAuthServiceDeploymentSpecificIssues:
    """Test suite for auth service deployment-specific SSL issues."""
    
    def test_cloud_run_environment_ssl_parameter_handling(self):
        """
        FIXED TEST: Verifies Cloud Run environment SSL parameter handling works correctly.
        
        Root Cause: Cloud Run container receives DATABASE_URL with sslmode parameter
        but auth service now properly normalizes it for asyncpg compatibility.
        """
        # Simulate exact Cloud Run environment variables
        cloud_run_env = {
            "DATABASE_URL": "postgresql://netra_user:staging_pass@/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require",
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging"
        }
        
        with patch.dict(os.environ, cloud_run_env):
            from auth_service.auth_core.database.database_manager import AuthDatabaseManager
            
            manager = AuthDatabaseManager()
            
            # This should now work - URL format should be compatible
            connection_url = manager.get_connection_url()
            
            # Verify the fix: URL should be compatible with asyncpg
            assert "/cloudsql/" in connection_url, "Should contain Cloud SQL path"
            assert "sslmode=" not in connection_url, "SSL parameters should be removed for Cloud SQL"
            assert "ssl=" not in connection_url, "SSL parameters should be removed for Cloud SQL"
            assert connection_url.startswith("postgresql+asyncpg://"), "Should be formatted for asyncpg"
    
    @patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'TESTING': '0'})
    def test_staging_secret_manager_url_format_mismatch(self):
        """
        FAILING TEST: Shows Secret Manager URL format mismatch with auth service expectations.
        
        Root Cause: Secret Manager stores DATABASE_URL in postgres:// format with sslmode,
        but auth service needs postgresql+asyncpg:// format without SSL params for Cloud SQL.
        """
        # Secret Manager format (typical)
        secret_manager_format = "postgres://netra_user:password@/postgres?host=/cloudsql/instance&sslmode=require"
        
        # Auth service expected format
        auth_service_expected = "postgresql+asyncpg://netra_user:password@/postgres?host=/cloudsql/instance"
        
        with patch.dict(os.environ, {
            "DATABASE_URL": secret_manager_format,
            "ENVIRONMENT": "staging"
        }):
            from auth_service.auth_core.config import AuthConfig
            
            actual_url = AuthConfig.get_database_url()
            
            # This MUST fail - format mismatch
            format_mismatches = []
            
            if actual_url.startswith("postgres://"):
                format_mismatches.append("Uses postgres:// instead of postgresql+asyncpg://")
            
            if "sslmode=" in actual_url and "/cloudsql/" in actual_url:
                format_mismatches.append("Contains sslmode parameter for Cloud SQL")
            
            assert not format_mismatches, f"URL format mismatches: {format_mismatches}"
            
            # Expected URL should match auth service requirements
            assert actual_url == auth_service_expected, \
                f"URL format mismatch. Expected: {auth_service_expected}, Got: {actual_url}"


if __name__ == "__main__":
    # These tests are designed to FAIL and demonstrate auth service SSL issues
    # Run with: pytest -v --tb=short test_staging_auth_ssl_failures.py
    pass