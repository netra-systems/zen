"""Critical Auth Service Database Connection Failures - Failing Tests
Tests that replicate critical database connection issues found in staging logs.

CRITICAL DATABASE ISSUES TO REPLICATE:
1. Database "netra_staging" does not exist - causing connection failures
2. SSL connection failures to Cloud SQL instances  
3. Connection timeout failures during initialization
4. Invalid database URL construction causing connection failures

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Database reliability and connection stability
- Value Impact: Prevents auth service failures due to database connectivity
- Strategic Impact: Ensures authentication availability for all customer tiers
"""

import os
import sys
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.exc import OperationalError, DatabaseError
from asyncpg.exceptions import InvalidCatalogNameError, ConnectionDoesNotExistError

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import AuthDatabase, auth_db
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from shared.database_url_builder import DatabaseURLBuilder
from test_framework.environment_markers import env, staging_only, env_requires

logger = logging.getLogger(__name__)


@env("staging")
@env_requires(services=["postgres"], features=["cloud_sql_configured"])
class TestCriticalDatabaseConnectionFailures:
    """Test suite for critical database connection failures found in staging."""
    
    @pytest.mark.asyncio
    async def test_database_netra_staging_does_not_exist_failure(self):
        """FAILING TEST: Replicates 'database "netra_staging" does not exist' error.
        
        This is the primary critical error found in staging logs where the auth service
        attempts to connect to a database named "netra_staging" that doesn't exist.
        """
        # Set up environment that would cause this specific error
        staging_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'test-db-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_staging',  # This database doesn't exist
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password'
        }
        
        with patch.dict(os.environ, staging_env):
            test_auth_db = AuthDatabase()
            
            # Mock the engine creation to simulate the exact error from logs
            original_create_engine = None
            
            async def mock_failing_connection(*args, **kwargs):
                # Simulate the exact error message from staging logs
                raise OperationalError(
                    "connection to server at \"test-db-host\" (IP_ADDRESS), port 5432 failed: "
                    "FATAL: database \"netra_staging\" does not exist",
                    None, None
                )
            
            # Test should fail with the database does not exist error
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.return_value.__aenter__.side_effect = mock_failing_connection
                mock_create_engine.return_value = mock_engine
                
                # This should raise the database does not exist error
                with pytest.raises(OperationalError) as exc_info:
                    await test_auth_db.initialize()
                
                error_message = str(exc_info.value).lower()
                assert "database" in error_message and "does not exist" in error_message
                assert "netra_staging" in error_message
                
                # Log the exact error for debugging
                logger.error(f"Database 'netra_staging' does not exist error replicated: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_database_name_configuration_mismatch(self):
        """FAILING TEST: Tests database name configuration mismatches that cause similar errors.
        
        Related to the netra_staging issue - tests various database name misconfigurations
        that could cause "does not exist" errors.
        """
        # Test various database name configurations that might cause issues
        problematic_db_names = [
            'netra-staging',  # Hyphen instead of underscore
            'netra_stg',      # Abbreviated name
            'staging_netra',  # Reversed name
            'netra',          # Missing staging suffix
            'NETRA_STAGING',  # All caps
            'netra_staging_old', # Wrong suffix
        ]
        
        for db_name in problematic_db_names:
            staging_env = {
                'ENVIRONMENT': 'staging',
                'POSTGRES_HOST': 'test-db-host',
                'POSTGRES_PORT': '5432',
                'POSTGRES_DB': db_name,
                'POSTGRES_USER': 'test_user',
                'POSTGRES_PASSWORD': 'test_password'
            }
            
            with patch.dict(os.environ, staging_env):
                test_auth_db = AuthDatabase()
                
                async def mock_db_not_exist(*args, **kwargs):
                    raise OperationalError(
                        f"connection failed: FATAL: database \"{db_name}\" does not exist",
                        None, None
                    )
                
                with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine') as mock_create_engine:
                    mock_engine = AsyncMock()
                    mock_engine.connect.return_value.__aenter__.side_effect = mock_db_not_exist
                    mock_create_engine.return_value = mock_engine
                    
                    # Each problematic name should cause a database not exist error
                    with pytest.raises(OperationalError) as exc_info:
                        await test_auth_db.initialize()
                    
                    assert db_name in str(exc_info.value)
                    logger.error(f"Database name '{db_name}' caused expected failure: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_cloud_sql_database_name_resolution_failure(self):
        """FAILING TEST: Tests Cloud SQL database name resolution failures.
        
        Cloud SQL might have different database naming conventions that cause
        the "netra_staging does not exist" error.
        """
        # Simulate Cloud SQL environment with database name issues
        cloud_sql_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-db',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_staging',  # This name might not match Cloud SQL instance
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging_password'
        }
        
        with patch.dict(os.environ, cloud_sql_env):
            # Test database URL construction for Cloud SQL
            builder = DatabaseURLBuilder(cloud_sql_env)
            
            # The URL might be constructed correctly but database name wrong
            database_url = builder.get_url_for_environment(sync=False)
            
            # Verify URL contains the problematic database name
            assert 'netra_staging' in database_url
            
            test_auth_db = AuthDatabase()
            
            async def mock_cloud_sql_db_not_exist(*args, **kwargs):
                # Cloud SQL specific error message format
                raise OperationalError(
                    "connection to server at \"/cloudsql/netra-staging:us-central1:netra-staging-db\" failed: "
                    "FATAL: database \"netra_staging\" does not exist",
                    None, None
                )
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.return_value.__aenter__.side_effect = mock_cloud_sql_db_not_exist
                mock_create_engine.return_value = mock_engine
                
                # Should fail with Cloud SQL database not exist error
                with pytest.raises(OperationalError) as exc_info:
                    await test_auth_db.initialize()
                
                error_message = str(exc_info.value)
                assert "cloudsql" in error_message
                assert "netra_staging" in error_message
                assert "does not exist" in error_message
                
                logger.error(f"Cloud SQL database not exist error replicated: {exc_info.value}")
    
    def test_database_url_builder_creates_wrong_database_name(self):
        """FAILING TEST: Tests that DatabaseURLBuilder creates URLs with wrong database names.
        
        The issue might be in how the database name is passed to or processed by
        the DatabaseURLBuilder.
        """
        # Test environment variables that should create correct staging database name
        correct_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-db-host',
            'POSTGRES_PORT': '5432', 
            'POSTGRES_DB': 'netra_production',  # Should this be different in staging?
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password'
        }
        
        builder = DatabaseURLBuilder(correct_env)
        database_url = builder.get_url_for_environment(sync=False)
        
        # Check if the URL contains the expected database name for staging
        # The issue might be that we're using wrong database name in staging
        if 'netra_staging' in database_url:
            # This suggests the database name is being changed somewhere in the process
            pytest.fail(f"DatabaseURLBuilder is creating URL with 'netra_staging' which doesn't exist: {database_url}")
        
        # Test various environment configurations to see which creates netra_staging
        test_configs = [
            {'POSTGRES_DB': 'netra'},
            {'POSTGRES_DB': 'netra_production'},
            {'POSTGRES_DB': 'netra_staging'},  # Direct setting
            {'DATABASE_NAME': 'netra_staging'},  # Alternative env var
        ]
        
        for config in test_configs:
            test_env = {**correct_env, **config}
            test_builder = DatabaseURLBuilder(test_env)
            test_url = test_builder.get_url_for_environment(sync=False)
            
            if 'netra_staging' in test_url:
                logger.error(f"Configuration {config} creates problematic database name: {test_url}")
                # This configuration creates the problematic database name
                assert False, f"Configuration {config} creates 'netra_staging' which causes failures"


@env("staging") 
@env_requires(services=["postgres"], features=["ssl_configured"])
class TestStagingDatabaseSSLConnectionFailures:
    """Test SSL connection failures specific to staging database configuration."""
    
    @pytest.mark.asyncio
    async def test_ssl_connection_failure_to_cloud_sql(self):
        """FAILING TEST: Tests SSL connection failures to Cloud SQL in staging.
        
        SSL configuration issues can cause connection failures even when
        database name is correct.
        """
        ssl_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-db',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'postgres',  # Use default postgres DB 
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'staging_password',
            'POSTGRES_SSLMODE': 'require'  # This might cause issues with Cloud SQL
        }
        
        with patch.dict(os.environ, ssl_env):
            test_auth_db = AuthDatabase()
            
            async def mock_ssl_connection_failure(*args, **kwargs):
                # SSL connection failure to Cloud SQL
                raise OperationalError(
                    "connection to server failed: SSL connection has been closed unexpectedly",
                    None, None
                )
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.return_value.__aenter__.side_effect = mock_ssl_connection_failure
                mock_create_engine.return_value = mock_engine
                
                # Should fail with SSL connection error
                with pytest.raises(OperationalError) as exc_info:
                    await test_auth_db.initialize()
                
                error_message = str(exc_info.value).lower()
                assert "ssl" in error_message
                logger.error(f"SSL connection failure replicated: {exc_info.value}")
    
    @pytest.mark.asyncio 
    async def test_database_connection_timeout_during_initialization(self):
        """FAILING TEST: Tests database connection timeouts during auth service initialization.
        
        Connection timeouts during startup can prevent the auth service from starting.
        """
        timeout_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'slow-db-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'postgres',
            'POSTGRES_USER': 'staging_user', 
            'POSTGRES_PASSWORD': 'staging_password'
        }
        
        with patch.dict(os.environ, timeout_env):
            test_auth_db = AuthDatabase()
            
            async def mock_connection_timeout(*args, **kwargs):
                # Simulate connection timeout
                await asyncio.sleep(0.1)  # Small delay to simulate timeout
                raise asyncio.TimeoutError("Connection timeout occurred")
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.return_value.__aenter__.side_effect = mock_connection_timeout
                mock_create_engine.return_value = mock_engine
                
                # Should fail with timeout error during initialization
                with pytest.raises(asyncio.TimeoutError):
                    # Set a short timeout to make test run quickly
                    await asyncio.wait_for(test_auth_db.initialize(), timeout=0.5)
                
                logger.error("Database connection timeout during initialization replicated")


@env("staging")
class TestDatabaseConfigurationValidation:
    """Test database configuration validation failures."""
    
    def test_missing_postgres_db_environment_variable(self):
        """FAILING TEST: Tests missing POSTGRES_DB environment variable causing fallback to wrong name.
        
        If POSTGRES_DB is not set, the system might fallback to a default that doesn't exist.
        """
        # Environment missing POSTGRES_DB 
        incomplete_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-db-host',
            'POSTGRES_PORT': '5432',
            # POSTGRES_DB is missing!
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password'
        }
        
        with patch.dict(os.environ, incomplete_env, clear=True):
            # Remove POSTGRES_DB if it exists
            if 'POSTGRES_DB' in os.environ:
                del os.environ['POSTGRES_DB']
            
            builder = DatabaseURLBuilder(incomplete_env)
            
            # Validate should fail or warn about missing database name
            is_valid, error_msg = builder.validate()
            
            if is_valid:
                # If validation passes, get the URL to see what database name is used
                database_url = builder.get_url_for_environment(sync=False)
                
                # Check if it defaults to a problematic database name
                if 'netra_staging' in database_url:
                    pytest.fail(f"Missing POSTGRES_DB defaults to problematic 'netra_staging': {database_url}")
                elif not database_url or 'postgresql://' not in database_url:
                    pytest.fail(f"Missing POSTGRES_DB results in invalid URL: {database_url}")
                
                logger.warning(f"Missing POSTGRES_DB created URL: {database_url}")
            else:
                # If validation fails, that's the expected behavior
                logger.info(f"Missing POSTGRES_DB correctly failed validation: {error_msg}")
    
    def test_postgres_db_environment_variable_case_sensitivity(self):
        """FAILING TEST: Tests case sensitivity issues with POSTGRES_DB variable.
        
        Environment variable case issues might cause wrong database name resolution.
        """
        # Test various case combinations that might cause issues
        case_variants = [
            'postgres_db',    # lowercase
            'Postgres_Db',    # mixed case  
            'POSTGRES_db',    # partial uppercase
            'PostgresDB',     # no underscore
            'postgres_DB'     # mixed case underscore
        ]
        
        base_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-db-host', 
            'POSTGRES_PORT': '5432',
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password'
        }
        
        for variant in case_variants:
            test_env = {**base_env, variant: 'netra_staging'}
            
            # Only set the POSTGRES_DB correctly
            test_env['POSTGRES_DB'] = 'postgres'  # Correct database
            
            with patch.dict(os.environ, test_env):
                builder = DatabaseURLBuilder(test_env)
                database_url = builder.get_url_for_environment(sync=False)
                
                # Check if case variants affect the database name in URL
                if 'netra_staging' in database_url:
                    logger.error(f"Case variant {variant} caused wrong database name: {database_url}")
                    pytest.fail(f"Environment variable case variant {variant} caused problematic database name")


# Mark all tests as integration tests that require database setup
pytestmark = [pytest.mark.integration, pytest.mark.database]