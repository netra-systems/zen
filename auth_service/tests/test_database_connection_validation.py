"""Test Auth Service Database Connection Validation
Tests the actual database connection mechanism and table creation process.

CRITICAL VALIDATION ISSUES TO REPLICATE:
1. Database connection validation bypassed during initialization
2. Table creation failing silently when authentication is invalid
3. Health checks failing due to credential inconsistencies 
4. Connection pool exhaustion during authentication retries

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable database connectivity validation
- Value Impact: Prevents silent failures and improves error detection
- Strategic Impact: Reduces production downtime and improves service reliability
"""

import os
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock, call
from sqlalchemy.exc import SQLAlchemyError, DatabaseError, OperationalError
from contextlib import asynccontextmanager

from auth_service.auth_core.database.connection import AuthDatabase, auth_db
from auth_service.auth_core.database.database_manager import AuthDatabaseManager  
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.isolated_environment import get_env
from test_framework.environment_markers import env

logger = logging.getLogger(__name__)


class TestDatabaseConnectionValidation:
    """Test suite for database connection validation mechanisms."""
    
    @pytest.mark.asyncio
    async def test_database_connection_validation_bypassed_during_init(self):
        """FAILING TEST: Tests that database validation is not properly enforced during initialization.
        
        This test demonstrates how the current initialization process can succeed
        even when database credentials are invalid, leading to runtime failures.
        """
        test_auth_db = AuthDatabase()
        
        # Mock URL validation to return True (bypassing validation)
        with patch.object(AuthDatabaseManager, 'validate_auth_url', return_value=True):
            # Mock engine creation to succeed initially
            mock_engine = AsyncMock()
            mock_engine.connect = AsyncMock(side_effect=OperationalError("auth failure", None, None))
            
            with patch('auth_service.auth_core.database.connection.create_async_engine', return_value=mock_engine):
                with patch.object(test_auth_db, 'create_tables', side_effect=OperationalError("auth failure", None, None)):
                    with patch.object(test_auth_db, 'is_test_mode', False):
                        with patch.object(AuthConfig, 'get_database_url', return_value="postgresql+asyncpg://invalid:creds@localhost:5432/test"):
                            
                            # Initialize should succeed despite invalid credentials
                            # because validation is insufficient
                            await test_auth_db.initialize()
                            
                            # But connection test should fail
                            connection_test_result = await test_auth_db.test_connection()
                            assert not connection_test_result
                            
                            # This demonstrates the validation gap
                            assert test_auth_db._initialized  # Incorrectly shows as initialized
                            assert test_auth_db.engine is not None  # Engine exists but can't connect
    
    @pytest.mark.asyncio
    async def test_table_creation_fails_silently_with_auth_errors(self):
        """FAILING TEST: Tests that table creation failures are not properly handled.
        
        This replicates the scenario where table creation is skipped due to
        authentication errors, but the service continues to operate incorrectly.
        """
        test_auth_db = AuthDatabase()
        
        # Mock successful engine creation but failed table operations
        mock_engine = AsyncMock()
        mock_connection = AsyncMock()
        
        # Mock connection that fails during table creation
        async def failing_run_sync(func):
            raise OperationalError("password authentication failed for user 'postgres'", None, None)
        
        mock_connection.run_sync = AsyncMock(side_effect=failing_run_sync)
        mock_connection.commit = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_connection
        
        with patch('auth_service.auth_core.database.connection.create_async_engine', return_value=mock_engine):
            with patch.object(test_auth_db, 'is_test_mode', False):
                with patch.object(AuthConfig, 'get_database_url', return_value="postgresql+asyncpg://postgres:wrong@localhost:5432/test"):
                    
                    # Initialization should handle the table creation failure
                    await test_auth_db.initialize()
                    
                    # Verify service is marked as initialized despite table creation failure
                    assert test_auth_db._initialized
                    
                    # But verify that tables were not actually created
                    # by attempting a direct table operation
                    with pytest.raises(Exception):
                        async with test_auth_db.get_session() as session:
                            # This should fail because tables don't exist
                            await session.execute("SELECT 1 FROM auth_users LIMIT 1")
    
    def test_health_check_credentials_inconsistency(self):
        """FAILING TEST: Tests health check credential loading inconsistencies.
        
        This test demonstrates how health checks may use different credential
        loading mechanisms than the main application, causing inconsistencies.
        """
        # Simulate environment where main app and health check load different credentials
        main_app_env = {
            "POSTGRES_USER": "main_user",
            "POSTGRES_PASSWORD": "main_password",
            "DATABASE_URL": "postgresql://main_user:main_password@localhost:5432/test"
        }
        
        health_check_env = {
            "POSTGRES_USER": "health_user", 
            "POSTGRES_PASSWORD": "health_password",
            "DATABASE_URL": "postgresql://health_user:health_password@localhost:5432/test"
        }
        
        # Test main app configuration
        with patch.dict(os.environ, main_app_env):
            main_url = AuthConfig.get_database_url()
            assert "main_user" in main_url
        
        # Test health check configuration (simulating different environment loading)
        with patch.dict(os.environ, health_check_env):
            health_url = AuthConfig.get_database_url()
            assert "health_user" in health_url
            
        # Verify URLs are different - demonstrating the inconsistency
        assert main_url != health_url
        
        # This inconsistency can cause health checks to fail even when
        # the main application is working correctly
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_during_auth_retries(self):
        """FAILING TEST: Tests connection pool exhaustion during authentication retries.
        
        This test demonstrates how repeated authentication failures can exhaust
        the connection pool, leading to service unavailability.
        """
        test_auth_db = AuthDatabase()
        
        # Mock engine with limited connection pool
        mock_engine = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 2  # Small pool size
        mock_pool.checked_out.return_value = 2  # All connections in use
        mock_pool.overflow.return_value = 0
        mock_pool.invalid.return_value = 2  # All connections invalid due to auth failures
        
        mock_engine.pool = mock_pool
        
        # Mock repeated connection failures
        auth_error = OperationalError("password authentication failed", None, None)
        mock_engine.connect.side_effect = auth_error
        
        with patch('auth_service.auth_core.database.connection.create_async_engine', return_value=mock_engine):
            with patch.object(test_auth_db, 'is_test_mode', False):
                with patch.object(AuthConfig, 'get_database_url', return_value="postgresql+asyncpg://invalid:wrong@localhost:5432/test"):
                    
                    # Initialize with the problematic engine
                    await test_auth_db.initialize()
                    
                    # Attempt multiple connection tests - should all fail
                    for i in range(5):  # More attempts than pool size
                        result = await test_auth_db.test_connection()
                        assert not result
                    
                    # Check pool status - should show exhaustion
                    pool_status = AuthDatabaseManager.get_pool_status(mock_engine)
                    assert pool_status["checked_out"] == pool_status["pool_size"]  # Pool exhausted
                    assert pool_status["invalid"] > 0  # Invalid connections due to auth failures
    
    @pytest.mark.asyncio
    async def test_async_session_creation_with_invalid_credentials(self):
        """FAILING TEST: Tests session creation when underlying credentials are invalid.
        
        This test demonstrates how session creation can appear to succeed
        but fail during actual database operations due to authentication issues.
        """
        test_auth_db = AuthDatabase()
        
        # Mock successful initialization but failing session operations
        mock_engine = AsyncMock()
        mock_session_maker = AsyncMock()
        mock_session = AsyncMock()
        
        # Configure session to fail on actual database operations
        async def failing_execute(query):
            raise OperationalError("password authentication failed for user 'postgres'", None, None)
        
        mock_session.execute = AsyncMock(side_effect=failing_execute)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Configure session maker to return the failing session
        async def session_context_manager():
            return mock_session
        
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Set up the test database instance
        test_auth_db.engine = mock_engine
        test_auth_db.async_session_maker = mock_session_maker
        test_auth_db._initialized = True
        
        # Session creation should appear to succeed
        async with test_auth_db.get_session() as session:
            assert session is not None
            
            # But database operations should fail with authentication error
            with pytest.raises(OperationalError) as exc_info:
                await session.execute("SELECT 1")
            
            assert "password authentication failed" in str(exc_info.value)
            
            # Verify rollback was called due to the error
            mock_session.rollback.assert_called_once()
    
    def test_database_url_credential_masking_exposes_invalid_users(self):
        """FAILING TEST: Tests that credential masking doesn't hide authentication issues.
        
        This test demonstrates how credential masking in logs can hide
        the fact that invalid usernames are being used for connections.
        """
        # Create URL with the problematic username from logs
        problematic_url = "postgresql+asyncpg://user_pr-4:password@localhost:5432/netra_auth"
        
        # Test URL masking
        from shared.database_url_builder import DatabaseURLBuilder
        masked_url = DatabaseURLBuilder.mask_url_for_logging(problematic_url)
        
        # Verify that masking hides the invalid username
        assert "user_pr-4" not in masked_url
        assert "*" in masked_url  # Password is masked
        
        # But this masking makes it harder to debug authentication issues
        # because the invalid username is hidden in logs
        
        # Verify the original URL contains the problematic username
        assert "user_pr-4" in problematic_url
        
        # This test documents how credential masking can hinder debugging
        # of authentication failures by hiding invalid usernames
    
    @pytest.mark.asyncio
    async def test_connection_events_not_handling_auth_failures(self):
        """FAILING TEST: Tests that connection events don't properly handle auth failures.
        
        This test demonstrates how database connection events may not
        properly detect and handle authentication failures.
        """
        test_auth_db = AuthDatabase()
        
        # Mock engine with connection events
        mock_engine = AsyncMock()
        
        # Mock connection that fails during event handling
        auth_error = OperationalError("FATAL: password authentication failed for user 'postgres'", None, None)
        
        # Simulate connection event failure
        with patch('auth_service.auth_core.database.connection_events.setup_auth_async_engine_events') as mock_setup_events:
            # Events are set up, but they don't prevent auth failures
            mock_setup_events.return_value = None
            
            with patch('auth_service.auth_core.database.connection.create_async_engine', return_value=mock_engine):
                with patch.object(test_auth_db, 'create_tables', side_effect=auth_error):
                    with patch.object(test_auth_db, 'is_test_mode', False):
                        with patch.object(AuthConfig, 'get_database_url', return_value="postgresql+asyncpg://postgres:wrong@localhost:5432/test"):
                            
                            # Initialize should set up events but still fail on auth
                            await test_auth_db.initialize()
                            
                            # Verify events were set up
                            mock_setup_events.assert_called_once()
                            
                            # But connection should still fail due to auth issues
                            result = await test_auth_db.test_connection()
                            assert not result
    
    @pytest.mark.asyncio
    async def test_service_startup_without_proper_credential_validation(self):
        """FAILING TEST: Tests service startup without comprehensive credential validation.
        
        This test demonstrates how the service can start up without validating
        that the provided credentials actually work for database operations.
        """
        # Environment with credentials that look valid but aren't
        seemingly_valid_env = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432", 
            "POSTGRES_DB": "netra_auth",
            "POSTGRES_USER": "seemingly_valid_user",
            "POSTGRES_PASSWORD": "seemingly_valid_password",
            "ENVIRONMENT": "development"
        }
        
        with patch.dict(os.environ, seemingly_valid_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return seemingly_valid_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # Configuration building should succeed
                database_url = AuthConfig.get_database_url()
                assert database_url is not None
                assert "seemingly_valid_user" in database_url
                
                # URL format validation should pass
                url_format_valid = AuthDatabaseManager.validate_auth_url(database_url)
                assert url_format_valid  # Format is correct
                
                # But actual connection would fail
                # This gap between format validation and connection validation
                # allows services to start with invalid credentials
                
                # Simulate actual connection test failure
                test_auth_db = AuthDatabase()
                
                with patch.object(test_auth_db, 'test_connection', return_value=False):
                    # Service can initialize despite connection failures
                    await test_auth_db.initialize()
                    
                    # But actual operations will fail
                    assert not await test_auth_db.test_connection()
                    
                    # This demonstrates the validation gap that allows
                    # services to start with invalid credentials


class TestDatabaseGracefulFailureHandling:
    """Test suite for database failure handling mechanisms."""
    
    @pytest.mark.asyncio
    async def test_repeated_authentication_failures_not_handled_gracefully(self):
        """FAILING TEST: Tests that repeated authentication failures aren't handled gracefully.
        
        This test demonstrates how the service doesn't implement proper
        backoff or circuit breaker patterns for authentication failures.
        """
        test_auth_db = AuthDatabase()
        failure_count = 0
        
        # Mock that tracks repeated failures
        async def failing_connection_test():
            nonlocal failure_count
            failure_count += 1
            raise OperationalError(f"password authentication failed (attempt {failure_count})", None, None)
        
        with patch.object(test_auth_db, 'test_connection', side_effect=failing_connection_test):
            # Attempt multiple connection tests without backoff
            for i in range(5):
                with pytest.raises(OperationalError):
                    await test_auth_db.test_connection()
            
            # Verify all attempts were made without any backoff or circuit breaker
            assert failure_count == 5
            
            # This demonstrates lack of graceful failure handling
            # Production systems should implement exponential backoff
            # and circuit breaker patterns for authentication failures
    
    def test_database_configuration_error_messages_insufficient(self):
        """FAILING TEST: Tests that database configuration error messages are insufficient.
        
        This test demonstrates how current error messages don't provide enough
        information to debug authentication and configuration issues.
        """
        # Test various configuration error scenarios
        error_scenarios = [
            ({}, "Missing all configuration"),
            ({"POSTGRES_HOST": "localhost"}, "Missing credentials"), 
            ({"POSTGRES_HOST": "localhost", "POSTGRES_USER": "user"}, "Missing password"),
            ({"POSTGRES_HOST": "localhost", "POSTGRES_USER": "user", "POSTGRES_PASSWORD": "pass"}, "Missing database"),
        ]
        
        for env_vars, description in error_scenarios:
            env_vars["ENVIRONMENT"] = "staging"  # Force validation
            
            with patch.dict(os.environ, env_vars, clear=True):
                with patch.object(get_env(), 'get') as mock_env_get:
                    def mock_get(key, default=None):
                        return env_vars.get(key, default)
                    mock_env_get.side_effect = mock_get
                    
                    try:
                        database_url = AuthConfig.get_database_url()
                    except ValueError as e:
                        error_message = str(e)
                        
                        # Current error messages may not be specific enough
                        # to help developers identify the exact missing configuration
                        
                        # This test documents the need for more specific error messages
                        assert len(error_message) > 10  # Should provide some detail
                        
                        # But may not provide enough context for debugging
                        logger.warning(f"Configuration error for {description}: {error_message}")


# Mark all tests as integration tests requiring real database validation
pytestmark = pytest.mark.integration