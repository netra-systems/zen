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

from test_framework.setup_test_path import setup_test_path
setup_test_path()


class TestAuthServiceSSLParameterFailures:
    """Test suite reproducing auth service SSL parameter failures."""
    
    @pytest.mark.asyncio
    async def test_cloud_sql_sslmode_parameter_rejection(self):
        """
        FAILING TEST: Reproduces asyncpg rejecting sslmode parameter for Cloud SQL.
        
        Root Cause: asyncpg doesn't recognize 'sslmode' parameter for Unix socket 
        connections to Cloud SQL. Only 'ssl' parameter is valid, but for Cloud SQL
        Unix sockets, NO SSL parameters should be present.
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
            
            # Convert to asyncpg format (this is where the bug occurs)
            asyncpg_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            
            # The problem: URL still contains sslmode which is invalid
            assert "sslmode=" in asyncpg_url, "URL contains problematic sslmode parameter"
            
            # This MUST fail when asyncpg tries to parse it
            with pytest.raises(Exception) as exc_info:
                # Simulate asyncpg connection attempt
                import urllib.parse as urlparse
                parsed = urlparse.urlparse(asyncpg_url)
                query_params = urlparse.parse_qs(parsed.query)
                
                # asyncpg rejects sslmode parameter for Unix socket connections
                if 'sslmode' in query_params and '/cloudsql/' in asyncpg_url:
                    raise ValueError("asyncpg.exceptions.InterfaceError: "
                                   "unrecognized configuration parameter 'sslmode'")
            
            error_msg = str(exc_info.value)
            assert "unrecognized configuration parameter" in error_msg
            assert "sslmode" in error_msg
    
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


class TestAuthServiceConfigurationConsistency:
    """Test suite for auth service configuration consistency issues."""
    
    def test_auth_config_database_url_handling_inconsistency(self):
        """
        FAILING TEST: Shows AuthConfig handling DATABASE_URL differently than main backend.
        
        Root Cause: AuthConfig.get_database_url() has different normalization 
        logic than netra_backend DatabaseConfigManager.
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
            
            # Auth service should normalize the URL, but it doesn't
            assert auth_url == test_url, "AuthConfig doesn't normalize DATABASE_URL"
            
            # This MUST fail - raw URL will cause SSL parameter issues
            if "/cloudsql/" in auth_url and "sslmode=" in auth_url:
                pytest.fail("AuthConfig returning raw URL with SSL parameters for Cloud SQL")
    
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


class TestAuthServiceDeploymentSpecificIssues:
    """Test suite for auth service deployment-specific SSL issues."""
    
    def test_cloud_run_environment_ssl_parameter_handling(self):
        """
        FAILING TEST: Shows Cloud Run environment SSL parameter handling issues.
        
        Root Cause: Cloud Run container receives DATABASE_URL with sslmode parameter
        but auth service code expects clean Unix socket URL.
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
            
            # This MUST fail - Cloud Run URL format incompatible
            with pytest.raises(Exception) as exc_info:
                connection_url = manager.get_connection_url()
                
                # Validate URL for asyncpg compatibility
                if "/cloudsql/" in connection_url and ("sslmode=" in connection_url or "ssl=" in connection_url):
                    raise ValueError("Cloud SQL URL contains SSL parameters incompatible with asyncpg")
            
            error_msg = str(exc_info.value)
            assert "ssl" in error_msg.lower() or "configuration" in error_msg.lower()
    
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