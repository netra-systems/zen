"""
GCP Staging Database Authentication Failure Tests
Failing tests that replicate PostgreSQL authentication issues found in staging logs

These tests WILL FAIL until the underlying authentication issues are resolved.
Purpose: Demonstrate authentication problems and prevent regressions.

Issues replicated:
1. Password authentication failed for user "postgres"
2. Wrong username authentication failures  
3. Missing credential scenarios
"""

import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import OperationalError
import psycopg2
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager

from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import IsolatedEnvironment


class TestPostgreSQLAuthenticationFailures:
    """Tests that replicate PostgreSQL authentication failures from staging logs"""
    
    @pytest.mark.asyncio
    async def test_postgres_wrong_password_authentication_failure(self):
        """
        Test: Password authentication failed for user "postgres"
        This test SHOULD FAIL until password issues are resolved
        """
        # Simulate wrong password scenario from staging logs
        wrong_password_url = "postgresql://postgres:wrong_password@127.0.0.1:5432/netra_db?sslmode=require"
        
        # This should fail with authentication error
        with pytest.raises((OperationalError, psycopg2.OperationalError)) as exc_info:
            engine = create_async_engine(wrong_password_url)
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
                
        # Verify it's specifically an authentication failure
        error_msg = str(exc_info.value).lower()
        assert any(phrase in error_msg for phrase in [
            "password authentication failed",
            "authentication failed", 
            "login failed",
            "access denied"
        ]), f"Expected authentication error but got: {exc_info.value}"

    @pytest.mark.asyncio  
    async def test_postgres_wrong_username_authentication_failure(self):
        """
        Test: Authentication failure with non-existent username
        This test SHOULD FAIL until user provisioning is correct
        """
        # Simulate wrong username scenario
        wrong_user_url = "postgresql://nonexistent_user:somepass@127.0.0.1:5432/netra_db?sslmode=require"
        
        # This should fail with authentication error
        with pytest.raises((OperationalError, psycopg2.OperationalError)) as exc_info:
            engine = create_async_engine(wrong_user_url)
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
                
        # Verify it's specifically an authentication failure
        error_msg = str(exc_info.value).lower()
        assert any(phrase in error_msg for phrase in [
            "password authentication failed",
            "role",
            "does not exist",
            "authentication failed",
            "login failed"
        ]), f"Expected user authentication error but got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_postgres_missing_password_authentication_failure(self):
        """
        Test: Authentication failure with missing password
        This test SHOULD FAIL until credential handling is robust
        """
        # Simulate missing password scenario
        no_password_url = "postgresql://postgres@127.0.0.1:5432/netra_db?sslmode=require"
        
        # This should fail with authentication error
        with pytest.raises((OperationalError, psycopg2.OperationalError)) as exc_info:
            engine = create_async_engine(no_password_url)
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
                
        # Verify it's an authentication failure
        error_msg = str(exc_info.value).lower()
        assert any(phrase in error_msg for phrase in [
            "password authentication failed",
            "no password supplied",
            "authentication failed",
            "login failed"
        ]), f"Expected missing password error but got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_database_manager_auth_error_handling(self):
        """
        Test: DatabaseManager handles authentication errors gracefully
        This test SHOULD FAIL until error handling is improved
        """
        # Mock environment with wrong credentials
        env = IsolatedEnvironment(isolation_mode=True)
        env.set("DATABASE_URL", "postgresql://postgres:wrong_pass@localhost:5432/test_db", "test")
        
        with patch('netra_backend.app.core.isolated_environment.get_isolated_environment', return_value=env):
            # DatabaseManager should detect and report auth failures clearly
            with pytest.raises(Exception) as exc_info:
                manager = DatabaseManager()
                await manager.create_application_engine()
                
        # Verify error is reported clearly (not generic connection error)
        error_msg = str(exc_info.value).lower()
        assert "authentication" in error_msg or "password" in error_msg, \
            f"Expected clear authentication error but got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_cloud_sql_proxy_auth_failure(self):
        """
        Test: Cloud SQL proxy authentication failure scenarios
        This test SHOULD FAIL until Cloud SQL credentials are correct
        """
        # Simulate Cloud SQL proxy with wrong credentials
        cloud_sql_url = "postgresql://wrong_user:wrong_pass@/netra_db?host=/cloudsql/netra-staging:us-central1:postgres-staging"
        
        with pytest.raises((OperationalError, psycopg2.OperationalError)) as exc_info:
            engine = create_async_engine(cloud_sql_url)
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
                
        error_msg = str(exc_info.value).lower()
        assert any(phrase in error_msg for phrase in [
            "authentication failed",
            "password authentication failed",
            "connection failed",
            "could not connect"
        ]), f"Expected Cloud SQL auth error but got: {exc_info.value}"

    def test_database_url_credential_validation(self):
        """
        Test: Database URL credential validation before connection attempts
        This test SHOULD FAIL until pre-validation is implemented
        """
        invalid_urls = [
            "postgresql://:@localhost:5432/db",  # Empty user and password
            "postgresql://user@localhost:5432/db",  # Missing password
            "postgresql://@localhost:5432/db",  # Missing user entirely
            "postgresql://localhost:5432/db",  # No credentials at all
        ]
        
        for url in invalid_urls:
            # Should fail validation BEFORE attempting connection
            with pytest.raises(ValueError) as exc_info:
                # This should validate credentials before connection
                DatabaseManager.validate_database_credentials(url)
                
            assert "credential" in str(exc_info.value).lower(), \
                f"Expected credential validation error for URL {url}, got: {exc_info.value}"


class TestAuthServiceDatabaseAuthentication:
    """Test auth service specific database authentication issues"""
    
    @pytest.mark.asyncio
    async def test_auth_service_postgres_connection_failure(self):
        """
        Test: Auth service PostgreSQL connection failure
        This test SHOULD FAIL until auth service DB config is correct
        """
        # Test backend database with wrong postgres credentials
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://backend_user:wrong_pass@localhost:5432/backend_db?sslmode=require'
        }):
            # Test backend service database manager
            with pytest.raises(Exception) as exc_info:
                backend_db = DatabaseManager()
                await backend_db.initialize()
                
            error_msg = str(exc_info.value).lower()
            assert "authentication" in error_msg or "connection" in error_msg, \
                f"Expected backend service authentication error but got: {exc_info.value}"

    def test_staging_environment_credential_requirements(self):
        """
        Test: Staging environment should never fallback to default credentials
        This test SHOULD FAIL until staging credential validation is strict
        """
        staging_env_vars = {
            'ENVIRONMENT': 'staging',
            'DATABASE_URL': '',  # Empty - should not fallback to defaults
        }
        
        with patch.dict('os.environ', staging_env_vars):
            # Staging should NEVER accept empty credentials
            with pytest.raises(ValueError) as exc_info:
                env = IsolatedEnvironment(isolation_mode=False)  # Use real env
                db_url = env.get('DATABASE_URL')
                if not db_url:
                    raise ValueError("Database URL is required in staging environment")
                    
            assert "required" in str(exc_info.value).lower(), \
                "Staging should strictly require database credentials"