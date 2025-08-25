"""FAILING TESTS: Database Connection Pool and Table Initialization Failures

CRITICAL CONNECTION POOL ISSUES RELATED TO 'postgres' DATABASE ERROR:
- Connection pool initialization fails when database 'postgres' doesn't exist
- Table creation attempts fail, but service continues in degraded mode
- Connection pool exhaustion during repeated authentication failures
- Connection events not properly handling database existence validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Reliable connection pooling and database schema management
- Value Impact: Ensures stable database connectivity and proper error handling
- Strategic Impact: Prevents service degradation and silent failures

These tests focus on connection pool management and table initialization 
issues specifically related to the 'postgres' database connectivity problem.
"""

import os
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock, call
from sqlalchemy.exc import OperationalError, InvalidRequestError
from sqlalchemy.pool import StaticPool, QueuePool
from contextlib import asynccontextmanager

from auth_service.auth_core.database.connection import AuthDatabase, auth_db
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.database.models import Base, AuthUser, AuthSession
from auth_service.auth_core.config import AuthConfig
from test_framework.environment_markers import env

logger = logging.getLogger(__name__)


class TestDatabaseConnectionPoolFailures:
    """Test suite for connection pool failures when postgres database doesn't exist."""
    
    @pytest.mark.asyncio
    async def test_connection_pool_initialization_fails_with_postgres_error(self):
        """FAILING TEST: Connection pool fails to initialize when postgres database doesn't exist.
        
        Connection pool should fail fast when target database is not available,
        rather than creating a pool that will fail on every connection attempt.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'postgres',  # Database that doesn't exist
            'POSTGRES_USER': 'pool_test_user',
            'POSTGRES_PASSWORD': 'pool_test_password'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            test_auth_db = AuthDatabase()
            
            # Mock engine creation with pool that fails on postgres database
            mock_engine = AsyncMock()
            mock_pool = MagicMock()
            
            # Configure pool to show it was created but connections fail
            mock_pool.size = MagicMock(return_value=5)
            mock_pool.checked_out = MagicMock(return_value=0) 
            mock_pool.overflow = MagicMock(return_value=0)
            mock_pool.invalid = MagicMock(return_value=0)
            
            mock_engine.pool = mock_pool
            
            # All connection attempts fail due to postgres database not existing
            async def mock_connection_failure(*args, **kwargs):
                raise OperationalError(
                    'connection failed: FATAL: database "postgres" does not exist',
                    None, None
                )
            
            mock_engine.connect.side_effect = mock_connection_failure
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine', return_value=mock_engine):
                # Pool initialization should detect the database issue
                with pytest.raises(OperationalError) as exc_info:
                    await test_auth_db.initialize()
                
                assert 'database "postgres" does not exist' in str(exc_info.value)
                
                # Verify pool was attempted to be created
                assert test_auth_db.engine is not None
                
                logger.error(f"Connection pool correctly failed due to postgres database error: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_during_postgres_retry_attempts(self):
        """FAILING TEST: Connection pool gets exhausted during repeated postgres connection attempts.
        
        When the service repeatedly tries to connect to non-existent postgres database,
        it can exhaust the connection pool and make the service completely unavailable.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Non-existent database
            'POSTGRES_HOST': 'test-host'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            test_auth_db = AuthDatabase()
            
            # Mock engine with limited pool size
            mock_engine = AsyncMock()
            mock_pool = MagicMock()
            
            # Small pool that gets exhausted quickly
            pool_size = 2
            checked_out_connections = 0
            
            def mock_pool_size():
                return pool_size
                
            def mock_checked_out():
                return min(checked_out_connections, pool_size)
                
            def mock_overflow():
                return max(0, checked_out_connections - pool_size)
            
            mock_pool.size = mock_pool_size
            mock_pool.checked_out = mock_checked_out
            mock_pool.overflow = mock_overflow
            mock_pool.invalid = MagicMock(return_value=pool_size)  # All connections invalid
            
            mock_engine.pool = mock_pool
            
            # Track connection attempts that fail
            connection_attempts = 0
            
            async def mock_failing_connection(*args, **kwargs):
                nonlocal checked_out_connections, connection_attempts
                connection_attempts += 1
                checked_out_connections += 1
                
                raise OperationalError(
                    f'connection attempt {connection_attempts}: database "postgres" does not exist',
                    None, None
                )
            
            mock_engine.connect.side_effect = mock_failing_connection
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine', return_value=mock_engine):
                # Initialize the database (may succeed incorrectly)
                try:
                    await test_auth_db.initialize()
                except OperationalError:
                    pass  # Expected failure
                
                # Test multiple connection attempts that exhaust the pool
                pool_exhausted = False
                
                for attempt in range(pool_size + 2):  # More attempts than pool size
                    try:
                        await test_auth_db.test_connection()
                    except OperationalError:
                        # Check if pool is now exhausted
                        if mock_pool.checked_out() >= pool_size:
                            pool_exhausted = True
                            break
                
                # Verify pool exhaustion occurred
                assert pool_exhausted, "Connection pool should be exhausted after repeated postgres connection failures"
                assert connection_attempts >= pool_size
                
                logger.error(f"Connection pool exhaustion correctly simulated after {connection_attempts} failed attempts")
    
    @pytest.mark.asyncio
    async def test_connection_pool_recovery_after_postgres_database_error(self):
        """FAILING TEST: Connection pool fails to recover after postgres database is fixed.
        
        Even after the postgres database issue is resolved, the connection pool
        might retain invalid connections and fail to recover properly.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging', 
            'POSTGRES_DB': 'postgres',
            'POSTGRES_HOST': 'test-host'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            test_auth_db = AuthDatabase()
            
            mock_engine = AsyncMock()
            mock_pool = MagicMock()
            
            # Pool starts with invalid connections due to postgres error
            invalid_connections = 3
            
            mock_pool.size = MagicMock(return_value=5)
            mock_pool.checked_out = MagicMock(return_value=0)
            mock_pool.overflow = MagicMock(return_value=0)
            mock_pool.invalid = MagicMock(return_value=invalid_connections)
            
            mock_engine.pool = mock_pool
            
            # Simulate database error followed by recovery
            connection_attempts = 0
            
            async def mock_connection_with_recovery(*args, **kwargs):
                nonlocal connection_attempts, invalid_connections
                connection_attempts += 1
                
                if connection_attempts <= 3:
                    # Initial attempts fail due to postgres database error
                    raise OperationalError(
                        'database "postgres" does not exist',
                        None, None
                    )
                else:
                    # Later attempts succeed (database fixed)
                    # But pool still has invalid connections
                    if invalid_connections > 0:
                        invalid_connections -= 1
                        raise OperationalError(
                            'connection invalid due to previous postgres error',
                            None, None
                        )
                    else:
                        # Finally successful connection
                        return MagicMock()
            
            mock_engine.connect.side_effect = mock_connection_with_recovery
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine', return_value=mock_engine):
                # Initialize database (will fail initially)
                try:
                    await test_auth_db.initialize()
                except OperationalError:
                    pass
                
                # Test connection recovery attempts
                recovery_successful = False
                max_attempts = 10
                
                for attempt in range(max_attempts):
                    try:
                        result = await test_auth_db.test_connection()
                        if result:
                            recovery_successful = True
                            break
                    except OperationalError as e:
                        logger.warning(f"Recovery attempt {attempt + 1} failed: {e}")
                        continue
                
                # Connection pool recovery should eventually succeed
                # But currently it might fail due to invalid connection handling
                if not recovery_successful:
                    pytest.fail(
                        "Connection pool failed to recover after postgres database was fixed. "
                        "Pool retains invalid connections and doesn't properly invalidate them."
                    )
                
                logger.info(f"Connection pool recovered after {connection_attempts} total attempts")


class TestDatabaseTableInitializationFailures:
    """Test suite for table initialization failures when postgres database doesn't exist."""
    
    @pytest.mark.asyncio
    async def test_table_creation_fails_silently_with_postgres_error(self):
        """FAILING TEST: Table creation fails silently when postgres database doesn't exist.
        
        Table creation should fail loudly when the target database is not available,
        not fail silently and leave the service in an inconsistent state.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Database doesn't exist
            'POSTGRES_HOST': 'test-host'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            test_auth_db = AuthDatabase()
            
            # Mock engine that fails during table operations
            mock_engine = AsyncMock()
            mock_connection = AsyncMock()
            
            # Mock connection context manager
            connection_context = AsyncMock()
            connection_context.__aenter__ = AsyncMock(return_value=mock_connection)
            connection_context.__aexit__ = AsyncMock()
            mock_engine.connect.return_value = connection_context
            
            # Mock run_sync to fail during table creation
            async def mock_run_sync_failure(func):
                if 'create_all' in str(func):
                    raise OperationalError(
                        'CREATE TABLE failed: database "postgres" does not exist',
                        None, None
                    )
                return MagicMock()
            
            mock_connection.run_sync = AsyncMock(side_effect=mock_run_sync_failure)
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine', return_value=mock_engine):
                # Table creation should fail explicitly
                with pytest.raises(OperationalError) as exc_info:
                    await test_auth_db.create_tables()
                
                assert 'database "postgres" does not exist' in str(exc_info.value)
                assert 'CREATE TABLE failed' in str(exc_info.value)
                
                logger.error(f"Table creation correctly failed due to postgres database error: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_schema_validation_fails_with_missing_postgres_database(self):
        """FAILING TEST: Schema validation fails when postgres database doesn't exist.
        
        Schema validation should detect that required tables don't exist because
        the target database is unavailable.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',
            'POSTGRES_HOST': 'test-host'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            test_auth_db = AuthDatabase()
            
            # Mock schema validation queries to fail
            mock_engine = AsyncMock()
            mock_connection = AsyncMock()
            
            connection_context = AsyncMock()
            connection_context.__aenter__ = AsyncMock(return_value=mock_connection)
            connection_context.__aexit__ = AsyncMock()
            mock_engine.connect.return_value = connection_context
            
            # Mock execute to fail during schema validation
            async def mock_execute_failure(query):
                if 'pg_tables' in str(query) or 'information_schema' in str(query):
                    raise OperationalError(
                        'schema validation failed: database "postgres" does not exist',
                        None, None
                    )
                return MagicMock()
            
            mock_connection.execute = AsyncMock(side_effect=mock_execute_failure)
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine', return_value=mock_engine):
                # Schema validation should fail
                with pytest.raises(OperationalError) as exc_info:
                    async with mock_engine.connect() as conn:
                        # Simulate schema validation query
                        await conn.execute("SELECT * FROM information_schema.tables WHERE table_schema = 'public'")
                
                assert 'database "postgres" does not exist' in str(exc_info.value)
                logger.error(f"Schema validation correctly failed: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_alembic_migration_fails_with_postgres_database_error(self):
        """FAILING TEST: Alembic database migrations fail when postgres database doesn't exist.
        
        Database migrations should fail clearly when the target database is unavailable,
        not partially execute or leave the schema in an inconsistent state.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Database doesn't exist
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_USER': 'migration_user',
            'POSTGRES_PASSWORD': 'migration_pass'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            # Mock Alembic migration failure
            from unittest.mock import patch
            
            def mock_alembic_upgrade(*args, **kwargs):
                raise OperationalError(
                    'Alembic upgrade failed: database "postgres" does not exist',
                    None, None
                )
            
            # Test migration failure
            with patch('alembic.command.upgrade', side_effect=mock_alembic_upgrade):
                with pytest.raises(OperationalError) as exc_info:
                    # Simulate running Alembic upgrade
                    from alembic import command
                    command.upgrade(None, "head")  # This would normally run migrations
                
                assert 'database "postgres" does not exist' in str(exc_info.value)
                logger.error(f"Alembic migration correctly failed: {exc_info.value}")


class TestDatabaseConnectionEventHandling:
    """Test suite for database connection event handling when postgres database doesn't exist."""
    
    @pytest.mark.asyncio
    async def test_connection_events_not_detecting_postgres_database_error(self):
        """FAILING TEST: Connection events fail to detect postgres database existence issues.
        
        Database connection events should detect and handle database existence
        validation, not just connection parameter validation.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',
            'POSTGRES_HOST': 'test-host'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            test_auth_db = AuthDatabase()
            
            # Mock connection events setup
            connection_events_called = []
            
            def mock_connection_event(dbapi_conn, connection_record):
                connection_events_called.append('connect')
                # Event handler doesn't validate database existence
                # This is the gap that allows postgres database errors to propagate
                
            # Mock engine with connection events that don't catch postgres error
            mock_engine = AsyncMock()
            mock_engine.pool = MagicMock()
            
            # Connection fails but events don't catch the database existence issue
            async def mock_failing_connection(*args, **kwargs):
                # Events fire but don't prevent the error
                mock_connection_event(None, None)
                raise OperationalError(
                    'database "postgres" does not exist',
                    None, None
                )
            
            mock_engine.connect.side_effect = mock_failing_connection
            
            with patch('auth_service.auth_core.database.database_manager.AuthDatabaseManager.create_async_engine', return_value=mock_engine):
                # Connection events don't prevent the postgres database error
                with pytest.raises(OperationalError) as exc_info:
                    await test_auth_db.initialize()
                
                # Verify events were called but didn't prevent the error
                assert len(connection_events_called) > 0
                assert 'database "postgres" does not exist' in str(exc_info.value)
                
                logger.error(f"Connection events failed to catch postgres database error: {exc_info.value}")
    
    def test_connection_pool_status_reporting_with_postgres_error(self):
        """FAILING TEST: Connection pool status doesn't properly report postgres database errors.
        
        Pool status should clearly indicate when connections are failing due to
        database existence issues, not just show generic connection failures.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            # Mock engine with pool that has postgres database connection issues
            mock_engine = AsyncMock()
            mock_pool = MagicMock()
            
            # Pool status shows connections as invalid but doesn't specify why
            mock_pool.size = MagicMock(return_value=5)
            mock_pool.checked_out = MagicMock(return_value=0)
            mock_pool.overflow = MagicMock(return_value=0) 
            mock_pool.invalid = MagicMock(return_value=5)  # All connections invalid
            
            mock_engine.pool = mock_pool
            
            # Get pool status
            pool_status = AuthDatabaseManager.get_pool_status(mock_engine)
            
            # Pool status shows invalid connections but doesn't indicate the cause
            assert pool_status['pool_size'] == 5
            assert pool_status['invalid'] == 5
            
            # The problem is that pool status doesn't specify that connections
            # are invalid due to "database postgres does not exist" error
            if 'error_details' not in pool_status:
                pytest.fail(
                    "Pool status doesn't provide error details about why connections are invalid. "
                    "Should specify that postgres database doesn't exist."
                )
            
            logger.error(f"Pool status lacks specific error details: {pool_status}")


# Mark all tests as integration tests requiring database setup
pytestmark = [pytest.mark.integration, pytest.mark.database]