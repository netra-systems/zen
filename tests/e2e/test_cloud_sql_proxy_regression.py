"""
Regression test suite for Cloud SQL proxy database URL construction.

This test suite ensures that:
1. DatabaseURLBuilder correctly handles Cloud SQL Unix socket connections
2. Deployment scripts don't bypass the SSOT by setting DATABASE_URL
3. Services properly use DatabaseURLBuilder for URL construction
4. Cloud SQL proxy format is correctly detected and handled

CRITICAL: These tests prevent regression of the Cloud SQL proxy fix from 2025-09-07
"""

import pytest
import os
import sys
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database_url_builder import DatabaseURLBuilder
from netra_backend.app.core.backend_environment import BackendEnvironment
from auth_service.auth_core.auth_environment import AuthEnvironment


class TestCloudSQLProxyURLConstruction:
    """Test Cloud SQL proxy URL construction in DatabaseURLBuilder."""
    
    def test_cloud_sql_detection(self):
        """Test that Cloud SQL paths are correctly detected."""
        # Cloud SQL path
        cloud_env = {
            "POSTGRES_HOST": "/cloudsql/project:region:instance",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db"
        }
        builder = DatabaseURLBuilder(cloud_env)
        assert builder.cloud_sql.is_cloud_sql is True
        
        # Regular TCP host
        tcp_env = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db"
        }
        builder = DatabaseURLBuilder(tcp_env)
        assert builder.cloud_sql.is_cloud_sql is False
    
    def test_cloud_sql_async_url_format(self):
        """Test async URL format for Cloud SQL Unix socket."""
        env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:postgres",
            "POSTGRES_USER": "netra_user",
            "POSTGRES_PASSWORD": "secure_pass",
            "POSTGRES_DB": "netra_staging"
        }
        builder = DatabaseURLBuilder(env)
        
        async_url = builder.cloud_sql.async_url
        assert async_url is not None
        assert "postgresql+asyncpg://" in async_url
        assert "@/" in async_url  # Unix socket format
        assert "?host=/cloudsql/" in async_url
        assert "netra_staging" in async_url
    
    def test_cloud_sql_sync_url_format(self):
        """Test sync URL format for Cloud SQL Unix socket."""
        env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:postgres",
            "POSTGRES_USER": "netra_user",
            "POSTGRES_PASSWORD": "secure_pass",
            "POSTGRES_DB": "netra_staging"
        }
        builder = DatabaseURLBuilder(env)
        
        sync_url = builder.cloud_sql.sync_url
        assert sync_url is not None
        assert sync_url.startswith("postgresql://")
        assert "@/" in sync_url  # Unix socket format
        assert "?host=/cloudsql/" in sync_url
        assert "netra_staging" in sync_url
    
    def test_staging_environment_prefers_cloud_sql(self):
        """Test that staging environment prefers Cloud SQL when available."""
        env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:postgres",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db"
        }
        builder = DatabaseURLBuilder(env)
        
        url = builder.get_url_for_environment(sync=False)
        assert url == builder.cloud_sql.async_url
        
        sync_url = builder.get_url_for_environment(sync=True)
        assert sync_url == builder.cloud_sql.sync_url
    
    def test_url_encoding_in_cloud_sql(self):
        """Test that special characters in credentials are properly encoded."""
        env = {
            "POSTGRES_HOST": "/cloudsql/project:region:instance",
            "POSTGRES_USER": "user@example.com",
            "POSTGRES_PASSWORD": "p@ss#word&special",
            "POSTGRES_DB": "db_name"
        }
        builder = DatabaseURLBuilder(env)
        
        url = builder.cloud_sql.async_url
        assert url is not None
        # Check that special characters are encoded
        assert "user%40example.com" in url
        assert "p%40ss%23word%26special" in url


class TestBackendEnvironmentCloudSQL:
    """Test that backend environment correctly uses DatabaseURLBuilder."""
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:postgres",
        "POSTGRES_USER": "backend_user",
        "POSTGRES_PASSWORD": "backend_pass",
        "POSTGRES_DB": "netra_staging",
        "JWT_SECRET_KEY": "test_jwt",
        "SECRET_KEY": "test_secret"
    })
    def test_backend_uses_database_url_builder(self):
        """Test that backend environment uses DatabaseURLBuilder for Cloud SQL."""
        backend_env = BackendEnvironment()
        
        # Get database URL
        db_url = backend_env.get_database_url(sync=False)
        
        # Verify it's a Cloud SQL URL
        assert db_url is not None
        assert "postgresql+asyncpg://" in db_url
        assert "@/" in db_url
        assert "?host=/cloudsql/" in db_url
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:postgres",
        "POSTGRES_USER": "backend_user",
        "POSTGRES_PASSWORD": "backend_pass",
        "POSTGRES_DB": "netra_staging",
        "JWT_SECRET_KEY": "test_jwt",
        "SECRET_KEY": "test_secret"
    })
    def test_backend_sync_url_for_alembic(self):
        """Test that backend can provide sync URL for Alembic migrations."""
        backend_env = BackendEnvironment()
        
        # Get sync database URL for Alembic
        db_url = backend_env.get_database_url(sync=True)
        
        # Verify it's a sync Cloud SQL URL
        assert db_url is not None
        assert db_url.startswith("postgresql://")
        assert "@/" in db_url
        assert "?host=/cloudsql/" in db_url


class TestAuthEnvironmentCloudSQL:
    """Test that auth environment correctly uses DatabaseURLBuilder."""
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:postgres",
        "POSTGRES_USER": "auth_user",
        "POSTGRES_PASSWORD": "auth_pass",
        "POSTGRES_DB": "netra_staging",
        "JWT_SECRET_KEY": "test_jwt"
    })
    def test_auth_uses_database_url_builder(self):
        """Test that auth environment uses DatabaseURLBuilder for Cloud SQL."""
        auth_env = AuthEnvironment()
        
        # Get database URL
        db_url = auth_env.get_database_url()
        
        # Verify it's a Cloud SQL URL
        assert db_url is not None
        assert "postgresql+asyncpg://" in db_url
        assert "@/" in db_url
        assert "?host=/cloudsql/" in db_url
    
    def test_auth_test_environment_uses_sqlite(self):
        """Test that auth service uses SQLite in test environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            auth_env = AuthEnvironment()
            db_url = auth_env.get_database_url()
            assert "sqlite+aiosqlite:///:memory:" in db_url


class TestDeploymentScriptCompliance:
    """Test that deployment scripts follow SSOT principles."""
    
    def test_deploy_script_no_database_url_construction(self):
        """Verify deploy_to_gcp.py doesn't construct DATABASE_URL."""
        deploy_script = project_root / "scripts" / "deploy_to_gcp.py"
        
        with open(deploy_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that DATABASE_URL is not being constructed
        assert 'env_vars["DATABASE_URL"]' not in content, \
            "Deployment script should not construct DATABASE_URL"
        
        # Check that DatabaseURLBuilder is mentioned
        assert "DatabaseURLBuilder" in content, \
            "Deployment script should reference DatabaseURLBuilder"
        
        # Check that SSOT principle is documented
        assert "SSOT" in content, \
            "Deployment script should document SSOT principle"
    
    def test_deploy_script_provides_postgres_vars(self):
        """Verify deploy script provides POSTGRES_* variables."""
        deploy_script = project_root / "scripts" / "deploy_to_gcp.py"
        
        with open(deploy_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that POSTGRES_* variables are handled
        postgres_vars = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
        for var in postgres_vars:
            assert var in content, f"Deployment script should handle {var}"
        
        # Check for Cloud SQL instance configuration
        assert "/cloudsql/" in content, \
            "Deployment script should configure Cloud SQL socket path"


class TestCloudSQLValidation:
    """Test Cloud SQL configuration validation."""
    
    def test_cloud_sql_path_validation(self):
        """Test validation of Cloud SQL socket paths."""
        valid_paths = [
            "/cloudsql/project:region:instance",
            "/cloudsql/netra-staging:us-central1:postgres",
            "/cloudsql/my-project:europe-west1:my-instance"
        ]
        
        for path in valid_paths:
            env = {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": path,
                "POSTGRES_USER": "user",
                "POSTGRES_PASSWORD": "pass",
                "POSTGRES_DB": "db"
            }
            builder = DatabaseURLBuilder(env)
            is_valid, error = builder.validate()
            assert is_valid, f"Valid Cloud SQL path {path} should pass validation: {error}"
    
    def test_invalid_cloud_sql_format_detection(self):
        """Test detection of invalid Cloud SQL formats."""
        invalid_env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/invalid-format",  # Missing region and instance
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db"
        }
        builder = DatabaseURLBuilder(invalid_env)
        is_valid, error = builder.validate()
        assert not is_valid
        assert "Invalid Cloud SQL format" in error


class TestURLMasking:
    """Test that sensitive information is properly masked in logs."""
    
    def test_cloud_sql_url_masking(self):
        """Test masking of Cloud SQL URLs for logging."""
        url = "postgresql+asyncpg://user:password@/database?host=/cloudsql/project:region:instance"
        masked = DatabaseURLBuilder.mask_url_for_logging(url)
        
        assert "password" not in masked
        assert "user" not in masked
        assert "***" in masked
        assert "/cloudsql/project:region:instance" in masked  # Path should remain visible
    
    def test_tcp_url_masking(self):
        """Test masking of TCP URLs for logging."""
        url = "postgresql+asyncpg://user:password@localhost:5432/database"
        masked = DatabaseURLBuilder.mask_url_for_logging(url)
        
        assert "password" not in masked
        assert "user" not in masked
        assert "***" in masked
        assert "localhost:5432/database" in masked  # Host and DB should remain visible


@pytest.mark.integration
class TestCloudSQLIntegration:
    """Integration tests for Cloud SQL with real environment setup."""
    
    @pytest.mark.skipif(
        os.environ.get("ENVIRONMENT") != "staging",
        reason="Only run in staging environment"
    )
    def test_real_cloud_sql_connection(self):
        """Test actual Cloud SQL connection in staging (when available)."""
        backend_env = BackendEnvironment()
        db_url = backend_env.get_database_url()
        
        # Just verify URL is constructed correctly
        assert db_url is not None
        assert "/cloudsql/" in db_url or "localhost" in db_url


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])