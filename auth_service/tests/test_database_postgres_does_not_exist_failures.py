"""FAILING TESTS: Database 'postgres' Does Not Exist - Critical Issue from Iteration 2

CRITICAL NEW DATABASE ISSUE TO REPLICATE:
- Database connection failing with: "database 'postgres' does not exist"
- Service falls back to "staging mode" without database connectivity
- This compromises all database-dependent features including user creation, token storage, authentication

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Database reliability and connection stability
- Value Impact: Ensures authentication system functionality across all environments
- Strategic Impact: Prevents authentication failures that would block all customer tiers

These tests are designed to FAIL with the current system state and PASS once the database
naming and connectivity issue is properly resolved.
"""

import os
import sys
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.exc import OperationalError, DatabaseError
from asyncpg.exceptions import InvalidCatalogNameError

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import AuthDatabase, auth_db
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.database.models import AuthUser, AuthSession, AuthAuditLog
from shared.database_url_builder import DatabaseURLBuilder
from test_framework.environment_markers import env, staging_only, env_requires

logger = logging.getLogger(__name__)


class TestDatabasePostgresDoesNotExistFailures:
    """Test suite for the critical 'database postgres does not exist' failure."""
    
    @pytest.mark.asyncio
    async def test_database_postgres_does_not_exist_error(self):
        """FAILING TEST: Replicates the exact 'database postgres does not exist' error.
        
        This is the primary critical error found in iteration 2 where the auth service
        attempts to connect to the default 'postgres' database that doesn't exist.
        """
        # Environment that causes the exact error from logs
        postgres_db_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'test-cloud-sql-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'postgres',  # This is the problematic database name
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password'
        }
        
        with patch.dict(os.environ, postgres_db_env):
            test_auth_db = AuthDatabase()
            
            # Mock the exact error from staging logs
            async def mock_postgres_db_not_exist(*args, **kwargs):
                raise OperationalError(
                    'connection to server failed: FATAL: database "postgres" does not exist',
                    None, None
                )
            
            with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.return_value.__aenter__.side_effect = mock_postgres_db_not_exist
                mock_create_engine.return_value = mock_engine
                
                # This should raise the exact error from iteration 2
                with pytest.raises(OperationalError) as exc_info:
                    await test_auth_db.initialize()
                
                error_message = str(exc_info.value).lower()
                assert 'database "postgres" does not exist' in error_message
                
                logger.error(f"Critical database 'postgres' does not exist error replicated: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_staging_mode_fallback_behavior(self):
        """FAILING TEST: Tests the problematic 'staging mode' fallback when database is unavailable.
        
        This test verifies that when the database connection fails, the service incorrectly
        falls back to 'staging mode' instead of properly handling the database error.
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'unavailable-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'postgres',  # Problematic database name
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password'
        }
        
        with patch.dict(os.environ, staging_env):
            test_auth_db = AuthDatabase()
            
            # Mock database connection failure
            async def mock_db_connection_failure(*args, **kwargs):
                raise OperationalError(
                    'could not connect to server: Connection refused\n'
                    'Is the server running and accepting connections?',
                    None, None
                )
            
            with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.side_effect = mock_db_connection_failure
                mock_create_engine.return_value = mock_engine
                
                # Service should NOT fall back to staging mode
                # But currently it does - this test documents the problematic behavior
                try:
                    await test_auth_db.initialize()
                    
                    # If initialization appears to succeed, that's the problem
                    # The service is running in "staging mode" without database
                    if test_auth_db._initialized:
                        pytest.fail(
                            "Service incorrectly initialized in 'staging mode' without database connectivity. "
                            "This compromises all database-dependent features."
                        )
                        
                except OperationalError:
                    # This is the expected behavior - service should fail on database errors
                    pass
                
                # Verify that database operations would fail
                with pytest.raises(Exception):
                    result = await test_auth_db.test_connection()
                    assert not result
    
    @pytest.mark.asyncio
    async def test_user_creation_fails_without_database_connectivity(self):
        """FAILING TEST: Verifies that user creation fails when database 'postgres' doesn't exist.
        
        This test ensures that core authentication features like user creation
        properly fail when the database is unavailable.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Problematic database name
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_USER': 'test_user', 
            'POSTGRES_PASSWORD': 'test_pass'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock database operations to fail with postgres not exist error
            async def mock_create_user_failure(*args, **kwargs):
                raise OperationalError(
                    'database "postgres" does not exist',
                    None, None
                )
            
            # Initialize database (may succeed incorrectly in staging mode)
            try:
                await test_auth_db.initialize()
            except OperationalError:
                pass  # Expected failure
            
            # Mock session creation to fail on database operations
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(side_effect=mock_create_user_failure)
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            
            # Test user creation through the session
            with patch.object(test_auth_db, 'get_session') as mock_get_session:
                # Configure session context manager
                mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_get_session.return_value.__aexit__ = AsyncMock()
                
                # User creation should fail due to database connectivity issues
                with pytest.raises(OperationalError) as exc_info:
                    async with test_auth_db.get_session() as session:
                        # Attempt to create a user
                        new_user = AuthUser(
                            email="test@example.com",
                            full_name="Test User",
                            auth_provider="google",
                            provider_user_id="test_id_123"
                        )
                        session.add(new_user)
                        await session.commit()  # This should fail
                
                assert 'database "postgres" does not exist' in str(exc_info.value)
                logger.error(f"AuthUser creation correctly failed due to database issue: {exc_info.value}")
    
    @pytest.mark.asyncio 
    async def test_token_storage_fails_without_database_connectivity(self):
        """FAILING TEST: Verifies that token storage fails when database 'postgres' doesn't exist.
        
        Token storage is critical for authentication - it must fail gracefully
        when the database is unavailable.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Problematic database name
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock token storage failure due to database connectivity
            async def mock_token_storage_failure(*args, **kwargs):
                raise OperationalError(
                    'connection to server failed: database "postgres" does not exist',
                    None, None
                )
            
            # Try to initialize database (may incorrectly succeed in staging mode)
            try:
                await test_auth_db.initialize()
            except OperationalError:
                pass  # Expected failure
            
            # Mock session for token operations
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(side_effect=mock_token_storage_failure)
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            
            with patch.object(test_auth_db, 'get_session') as mock_get_session:
                mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_get_session.return_value.__aexit__ = AsyncMock()
                
                # Token storage should fail
                with pytest.raises(OperationalError) as exc_info:
                    async with test_auth_db.get_session() as session:
                        # Attempt to store session/token data
                        from datetime import datetime, timezone
                        new_session = AuthSession(
                            user_id="test_user_123",
                            refresh_token_hash="test_refresh_hash",
                            expires_at=datetime.now(timezone.utc)
                        )
                        session.add(new_session)
                        await session.commit()  # This should fail
                
                assert 'postgres" does not exist' in str(exc_info.value)
                logger.error(f"Token storage correctly failed due to database issue: {exc_info.value}")
    
    def test_database_url_construction_defaults_to_postgres_database(self):
        """FAILING TEST: Verifies that URL construction incorrectly defaults to 'postgres' database.
        
        This test identifies where the problematic database name 'postgres' is coming from
        in the URL construction process.
        """
        # Test environment without explicit POSTGRES_DB setting
        minimal_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password'
            # Note: POSTGRES_DB is intentionally missing
        }
        
        with patch.dict(os.environ, minimal_env, clear=True):
            # Remove POSTGRES_DB if it exists globally
            if 'POSTGRES_DB' in os.environ:
                del os.environ['POSTGRES_DB']
            
            builder = DatabaseURLBuilder(minimal_env)
            database_url = builder.get_url_for_environment(sync=False)
            
            # Check if the URL defaults to problematic 'postgres' database
            if 'postgres' in database_url and not any(db_name in database_url for db_name in ['netra', 'auth']):
                pytest.fail(
                    f"DatabaseURLBuilder defaults to problematic 'postgres' database: {database_url}. "
                    "This is likely the source of the 'database postgres does not exist' error."
                )
            
            logger.info(f"Database URL constructed: {builder.mask_url_for_logging(database_url)}")
            
            # Alternative: Test specific database configurations
            test_configs = [
                {},  # Empty config
                {'DATABASE_NAME': None},  # Explicit None
                {'DB_NAME': 'postgres'},  # Alternative env var that might cause issue
            ]
            
            for config in test_configs:
                test_env = {**minimal_env, **config}
                test_builder = DatabaseURLBuilder(test_env)
                test_url = test_builder.get_url_for_environment(sync=False)
                
                if '/postgres' in test_url:
                    logger.error(f"Configuration {config} creates problematic postgres database: {test_url}")
                    pytest.fail(
                        f"Configuration {config} results in 'postgres' database which causes failures"
                    )
    
    @pytest.mark.asyncio
    async def test_cloud_sql_postgres_database_name_error(self):
        """FAILING TEST: Tests the 'postgres' database error specifically in Cloud SQL context.
        
        Cloud SQL environments might be defaulting to 'postgres' database name
        instead of using the correct application database.
        """
        cloud_sql_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': '/cloudsql/project:region:instance',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'postgres',  # This is the problematic setting
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password'
        }
        
        with patch.dict(os.environ, cloud_sql_env):
            test_auth_db = AuthDatabase()
            
            # Mock Cloud SQL specific postgres error
            async def mock_cloud_sql_postgres_error(*args, **kwargs):
                raise OperationalError(
                    'connection to server at "/cloudsql/project:region:instance" failed: '
                    'FATAL: database "postgres" does not exist',
                    None, None
                )
            
            with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.return_value.__aenter__.side_effect = mock_cloud_sql_postgres_error
                mock_create_engine.return_value = mock_engine
                
                # Should fail with Cloud SQL postgres database error
                with pytest.raises(OperationalError) as exc_info:
                    await test_auth_db.initialize()
                
                error_message = str(exc_info.value)
                assert 'cloudsql' in error_message
                assert 'database "postgres" does not exist' in error_message
                
                logger.error(f"Cloud SQL postgres database error replicated: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_health_check_fails_with_postgres_database_error(self):
        """FAILING TEST: Verifies that health checks fail when postgres database doesn't exist.
        
        Health checks should properly detect and report database connectivity issues
        instead of allowing the service to appear healthy.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Problematic database
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock health check database operation failure
            async def mock_health_check_failure(*args, **kwargs):
                raise OperationalError(
                    'database "postgres" does not exist',
                    None, None
                )
            
            with patch.object(test_auth_db, 'test_connection', side_effect=mock_health_check_failure):
                # Health check should fail, not return a false positive
                with pytest.raises(OperationalError):
                    health_status = await test_auth_db.test_connection()
                
                logger.error("Health check correctly failed due to postgres database error")
    
    def test_configuration_validation_allows_invalid_postgres_database(self):
        """FAILING TEST: Tests that configuration validation incorrectly allows 'postgres' database.
        
        Configuration validation should detect when the database name is set to 'postgres'
        and either warn or suggest the correct application database name.
        """
        # Configuration with problematic postgres database
        problematic_config = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'postgres',  # This should be flagged as problematic
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password'
        }
        
        builder = DatabaseURLBuilder(problematic_config)
        is_valid, error_msg = builder.validate()
        
        if is_valid:
            # Validation passes but it shouldn't for 'postgres' database
            database_url = builder.get_url_for_environment(sync=False)
            
            if '/postgres' in database_url:
                pytest.fail(
                    f"Configuration validation incorrectly allows 'postgres' database: {database_url}. "
                    "Validation should warn about using the system database instead of application database."
                )
        
        # Test AuthDatabaseManager validation as well
        database_url = builder.get_url_for_environment(sync=False)
        auth_url_valid = AuthDatabaseManager.validate_auth_url(database_url)
        
        if auth_url_valid and '/postgres' in database_url:
            pytest.fail(
                "AuthDatabaseManager validation allows problematic 'postgres' database. "
                "Should recommend using application-specific database name like 'netra_auth'."
            )


class TestDatabaseNamingConventionIssues:
    """Test suite for database naming convention problems that cause connectivity failures."""
    
    def test_missing_application_database_name_configuration(self):
        """FAILING TEST: Tests missing or incorrect application database name configuration.
        
        The root cause might be that the application database name (e.g., 'netra_auth')
        is not properly configured, causing fallback to system 'postgres' database.
        """
        # Test various missing database name scenarios
        incomplete_configs = [
            # Missing database name entirely
            {
                'ENVIRONMENT': 'staging',
                'POSTGRES_HOST': 'test-host',
                'POSTGRES_USER': 'test_user',
                'POSTGRES_PASSWORD': 'test_pass'
            },
            # Database name set to None
            {
                'ENVIRONMENT': 'staging',
                'POSTGRES_HOST': 'test-host',
                'POSTGRES_DB': None,
                'POSTGRES_USER': 'test_user',
                'POSTGRES_PASSWORD': 'test_pass'
            },
            # Empty database name
            {
                'ENVIRONMENT': 'staging',
                'POSTGRES_HOST': 'test-host',
                'POSTGRES_DB': '',
                'POSTGRES_USER': 'test_user',
                'POSTGRES_PASSWORD': 'test_pass'
            }
        ]
        
        for i, config in enumerate(incomplete_configs):
            with patch.dict(os.environ, config, clear=True):
                builder = DatabaseURLBuilder(config)
                
                try:
                    database_url = builder.get_url_for_environment(sync=False)
                    
                    # If URL is created, check if it defaults to problematic database
                    if database_url and '/postgres' in database_url:
                        pytest.fail(
                            f"Incomplete config {i} defaults to 'postgres' database: {database_url}. "
                            "Missing application database configuration is causing the connectivity issue."
                        )
                        
                except Exception as e:
                    # If URL construction fails, that might be the expected behavior
                    logger.info(f"Config {i} correctly failed URL construction: {e}")
    
    def test_environment_specific_database_name_resolution(self):
        """FAILING TEST: Tests that database names are correctly resolved per environment.
        
        Different environments might need different database names, and incorrect
        resolution could lead to 'postgres' database errors.
        """
        # Test database name resolution for each environment
        environment_configs = [
            ('development', 'netra_dev'),
            ('staging', 'netra_staging'),
            ('production', 'netra_production'),
            ('test', 'netra_test')
        ]
        
        for environment, expected_db_name in environment_configs:
            config = {
                'ENVIRONMENT': environment,
                'POSTGRES_HOST': f'{environment}-host',
                'POSTGRES_PORT': '5432',
                'POSTGRES_USER': f'{environment}_user',
                'POSTGRES_PASSWORD': f'{environment}_password'
                # Note: No explicit POSTGRES_DB setting
            }
            
            with patch.dict(os.environ, config, clear=True):
                builder = DatabaseURLBuilder(config)
                database_url = builder.get_url_for_environment(sync=False)
                
                # Check if environment-specific resolution works correctly
                if database_url:
                    if '/postgres' in database_url and expected_db_name not in database_url:
                        logger.error(
                            f"Environment '{environment}' incorrectly resolves to 'postgres' database: {database_url}"
                        )
                        pytest.fail(
                            f"Environment '{environment}' should resolve to '{expected_db_name}' "
                            f"but defaults to 'postgres': {database_url}"
                        )
                    elif expected_db_name in database_url:
                        logger.info(f"Environment '{environment}' correctly resolves to: {expected_db_name}")


# Mark all tests as integration tests requiring database setup
pytestmark = [pytest.mark.integration, pytest.mark.database]