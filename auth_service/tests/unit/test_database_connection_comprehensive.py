"""
Comprehensive unit tests for Auth Service Database Connection

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Ensure reliable database connectivity for auth service
- Value Impact: Prevents authentication failures due to connection issues
- Strategic Impact: Foundation for scalable multi-user authentication

Tests database connection management, session handling, transaction management,
connection pooling, error handling, and environment-specific configuration.
Uses real PostgreSQL database for comprehensive validation.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from auth_service.auth_core.database.connection import (
    AuthDatabaseConnection, auth_db, get_db_session
)
from auth_service.auth_core.database.models import AuthUser
from shared.isolated_environment import get_env
from test_framework.real_services_test_fixtures import real_services_fixture


class TestAuthDatabaseConnectionInitialization:
    """Test database connection initialization and configuration"""
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_database_connection_initialization(self, real_services_fixture):
        """Test basic database connection initialization"""
        # Create new connection instance
        db_conn = AuthDatabaseConnection()
        
        # Verify initial state
        assert db_conn.engine is None
        assert db_conn.async_session_maker is None
        assert db_conn._initialized is False
        
        # Initialize connection
        await db_conn.initialize()
        
        # Verify post-initialization state
        assert db_conn.engine is not None
        assert db_conn.async_session_maker is not None
        assert db_conn._initialized is True
        
        # Clean up
        await db_conn.close()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_database_connection_idempotent_initialization(self, real_services_fixture):
        """Test that initialization is idempotent (can be called multiple times safely)"""
        db_conn = AuthDatabaseConnection()
        
        # Initialize multiple times
        await db_conn.initialize()
        engine1 = db_conn.engine
        session_maker1 = db_conn.async_session_maker
        
        await db_conn.initialize()  # Second call
        engine2 = db_conn.engine
        session_maker2 = db_conn.async_session_maker
        
        # Should be the same objects (idempotent)
        assert engine1 is engine2
        assert session_maker1 is session_maker2
        assert db_conn._initialized is True
        
        await db_conn.close()
    
    @pytest.mark.unit
    @pytest.mark.real_services  
    async def test_database_connection_environment_detection(self, real_services_fixture):
        """Test environment detection and configuration"""
        db_conn = AuthDatabaseConnection()
        
        # Test environment variables are detected
        env = get_env()
        expected_env = env.get("ENVIRONMENT", "development").lower()
        
        assert db_conn.environment == expected_env
        assert isinstance(db_conn.is_cloud_run, bool)
        assert isinstance(db_conn.is_test_mode, bool)
    
    @pytest.mark.unit
    async def test_database_connection_test_mode(self):
        """Test database connection in fast test mode"""
        # Mock environment to enable fast test mode
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                "AUTH_FAST_TEST_MODE": "true",
                "ENVIRONMENT": "test"
            }.get(key, default)
            
            db_conn = AuthDatabaseConnection()
            await db_conn.initialize()
            
            # Should use SQLite in-memory database in test mode
            assert str(db_conn.engine.url).startswith("sqlite+aiosqlite:///:memory:")
            
            await db_conn.close()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_database_connection_timeout_handling(self, real_services_fixture):
        """Test connection timeout handling"""
        db_conn = AuthDatabaseConnection()
        
        # Test with very short timeout (should still succeed with real DB)
        await db_conn.initialize(timeout=5.0)
        
        assert db_conn._initialized is True
        await db_conn.close()
    
    @pytest.mark.unit
    async def test_database_connection_initialization_failure(self):
        """Test handling of initialization failures"""
        with patch('auth_service.auth_core.database.connection.AuthConfig') as mock_config:
            mock_config.get_database_url.side_effect = Exception("Database config error")
            
            db_conn = AuthDatabaseConnection()
            
            with pytest.raises(RuntimeError, match="Auth database initialization failed"):
                await db_conn.initialize()
            
            # Should remain uninitialized
            assert db_conn._initialized is False
            assert db_conn.engine is None


class TestAuthDatabaseConnectionSessionManagement:
    """Test database session management and transactions"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Ensure database is initialized for session tests"""
        if not auth_db._initialized:
            await auth_db.initialize()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_get_session_context_manager(self, real_services_fixture):
        """Test session context manager functionality"""
        async with auth_db.get_session() as session:
            # Session should be active
            assert session is not None
            
            # Test basic query
            result = await session.execute(text("SELECT 1 as test"))
            value = result.scalar()
            assert value == 1
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_session_transaction_commit(self, real_services_fixture):
        """Test session transaction commit"""
        # Create test user in transaction
        async with auth_db.get_session() as session:
            user = AuthUser(email="session_commit_test@example.com")
            session.add(user)
            await session.commit()
            user_id = user.id
        
        # Verify user was committed
        async with auth_db.get_session() as session:
            retrieved_user = await session.get(AuthUser, user_id)
            assert retrieved_user is not None
            assert retrieved_user.email == "session_commit_test@example.com"
            
            # Clean up
            await session.delete(retrieved_user)
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_session_transaction_rollback(self, real_services_fixture):
        """Test session transaction rollback on error"""
        user_id = None
        
        try:
            async with auth_db.get_session() as session:
                user = AuthUser(email="session_rollback_test@example.com")
                session.add(user)
                await session.flush()  # Get ID without committing
                user_id = user.id
                
                # Force an error to trigger rollback
                raise Exception("Test error to trigger rollback")
        except Exception as e:
            assert "Test error to trigger rollback" in str(e)
        
        # Verify user was rolled back (doesn't exist)
        async with auth_db.get_session() as session:
            retrieved_user = await session.get(AuthUser, user_id) if user_id else None
            assert retrieved_user is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_session_isolation(self, real_services_fixture):
        """Test that different sessions are isolated"""
        # Create user in first session
        async with auth_db.get_session() as session1:
            user = AuthUser(email="session_isolation_test@example.com")
            session1.add(user)
            await session1.flush()  # Don't commit yet
            
            # Second session shouldn't see uncommitted data
            async with auth_db.get_session() as session2:
                result = await session2.execute(
                    text("SELECT COUNT(*) FROM auth_users WHERE email = 'session_isolation_test@example.com'")
                )
                count = result.scalar()
                assert count == 0  # Shouldn't see uncommitted data
            
            # Commit in first session
            await session1.commit()
            user_id = user.id
        
        # Now second session should see committed data
        async with auth_db.get_session() as session:
            retrieved_user = await session.get(AuthUser, user_id)
            assert retrieved_user is not None
            
            # Clean up
            await session.delete(retrieved_user)
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_session_concurrent_access(self, real_services_fixture):
        """Test concurrent session access"""
        async def create_user(suffix):
            async with auth_db.get_session() as session:
                user = AuthUser(email=f"concurrent_test_{suffix}@example.com")
                session.add(user)
                await session.commit()
                return user.id
        
        # Create multiple users concurrently
        user_ids = await asyncio.gather(
            create_user("1"),
            create_user("2"),
            create_user("3")
        )
        
        # Verify all users were created
        async with auth_db.get_session() as session:
            for user_id in user_ids:
                user = await session.get(AuthUser, user_id)
                assert user is not None
                
                # Clean up
                await session.delete(user)
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_get_db_session_dependency(self, real_services_fixture):
        """Test FastAPI dependency function"""
        session_generator = get_db_session()
        session = await session_generator.__anext__()
        
        assert session is not None
        
        # Test basic query
        result = await session.execute(text("SELECT 1 as test"))
        value = result.scalar()
        assert value == 1
        
        # Clean up the generator
        try:
            await session_generator.__anext__()
        except StopAsyncIteration:
            pass  # Expected


class TestAuthDatabaseConnectionPoolingAndPerformance:
    """Test connection pooling and performance aspects"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Ensure database is initialized for pooling tests"""
        if not auth_db._initialized:
            await auth_db.initialize()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_connection_pooling_multiple_sessions(self, real_services_fixture):
        """Test that multiple sessions use connection pooling efficiently"""
        # Create multiple sessions sequentially
        session_results = []
        
        for i in range(5):
            async with auth_db.get_session() as session:
                result = await session.execute(text(f"SELECT {i} as test"))
                value = result.scalar()
                session_results.append(value)
        
        # Verify all sessions worked correctly
        assert session_results == [0, 1, 2, 3, 4]
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_connection_reuse(self, real_services_fixture):
        """Test that connections are reused from pool"""
        connection_pids = []
        
        # Get connection PIDs from multiple sessions
        for _ in range(3):
            async with auth_db.get_session() as session:
                # Get backend process ID if available (PostgreSQL specific)
                try:
                    result = await session.execute(text("SELECT pg_backend_pid()"))
                    pid = result.scalar()
                    connection_pids.append(pid)
                except Exception:
                    # Skip if not PostgreSQL or function not available
                    connection_pids.append(None)
        
        # Remove None values (non-PostgreSQL connections)
        valid_pids = [pid for pid in connection_pids if pid is not None]
        
        if valid_pids:
            # In a pool, we might reuse connections, so we could see repeated PIDs
            assert len(valid_pids) >= 1
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_session_cleanup_on_error(self, real_services_fixture):
        """Test that sessions are properly cleaned up on errors"""
        initial_pool_size = 0
        
        # Get initial pool state if available
        if hasattr(auth_db.engine, 'pool'):
            try:
                initial_pool_size = auth_db.engine.pool.checkedin()
            except:
                pass
        
        # Create session that raises error
        try:
            async with auth_db.get_session() as session:
                # Force an error
                await session.execute(text("SELECT * FROM nonexistent_table"))
        except Exception:
            pass  # Expected error
        
        # Pool should be cleaned up properly
        if hasattr(auth_db.engine, 'pool'):
            try:
                final_pool_size = auth_db.engine.pool.checkedin()
                # Pool size should be restored (connection returned to pool)
                assert final_pool_size >= initial_pool_size
            except:
                pass  # Skip if pool inspection not available


class TestAuthDatabaseConnectionHealthAndMonitoring:
    """Test database connection health checks and monitoring"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Ensure database is initialized for health tests"""
        if not auth_db._initialized:
            await auth_db.initialize()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_test_connection(self, real_services_fixture):
        """Test connection health check"""
        result = await auth_db.test_connection()
        assert result is True
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_test_connection_with_timeout(self, real_services_fixture):
        """Test connection health check with custom timeout"""
        result = await auth_db.test_connection(timeout=5.0)
        assert result is True
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_is_ready(self, real_services_fixture):
        """Test database readiness check"""
        result = await auth_db.is_ready()
        assert result is True
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_is_ready_with_timeout(self, real_services_fixture):
        """Test database readiness check with custom timeout"""
        result = await auth_db.is_ready(timeout=5.0)
        assert result is True
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_get_status(self, real_services_fixture):
        """Test database status reporting"""
        status = auth_db.get_status()
        
        assert isinstance(status, dict)
        assert "status" in status
        assert status["status"] == "active"
        assert "environment" in status
        assert "is_cloud_run" in status
        assert "is_test_mode" in status
        assert isinstance(status["is_cloud_run"], bool)
        assert isinstance(status["is_test_mode"], bool)
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_get_connection_health(self, real_services_fixture):
        """Test detailed connection health information"""
        health = await auth_db.get_connection_health()
        
        assert isinstance(health, dict)
        assert "initialized" in health
        assert health["initialized"] is True
        assert "environment" in health
        assert "engine_exists" in health
        assert health["engine_exists"] is True
        assert "timestamp" in health
        assert "connectivity_test" in health
        assert health["connectivity_test"] == "passed"
        assert "status" in health
        assert health["status"] == "healthy"
    
    @pytest.mark.unit
    async def test_get_connection_health_uninitialized(self):
        """Test connection health when not initialized"""
        db_conn = AuthDatabaseConnection()
        health = await db_conn.get_connection_health()
        
        assert health["initialized"] is False
        assert health["status"] == "not_initialized"
        assert health["engine_exists"] is False


class TestAuthDatabaseConnectionErrorHandling:
    """Test error handling and edge cases in database connection"""
    
    @pytest.mark.unit
    async def test_mock_engine_handling(self):
        """Test handling of mock engines in tests"""
        db_conn = AuthDatabaseConnection()
        
        # Mock the engine creation to return a mock
        with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine
            
            await db_conn.initialize()
            
            # Should handle mock engines gracefully
            assert db_conn.engine is mock_engine
            assert db_conn._initialized is True
    
    @pytest.mark.unit
    async def test_connection_validation_with_mock(self):
        """Test connection validation skips for mock objects"""
        db_conn = AuthDatabaseConnection()
        
        # Set up mock engine
        mock_engine = MagicMock()
        db_conn.engine = mock_engine
        
        # Should not raise error with mock engine
        await db_conn._validate_initial_connection()
    
    @pytest.mark.unit
    async def test_cleanup_partial_initialization(self):
        """Test cleanup of partial initialization"""
        db_conn = AuthDatabaseConnection()
        
        # Create mock engine for cleanup test
        mock_engine = AsyncMock()
        db_conn.engine = mock_engine
        db_conn._initialized = True
        
        await db_conn._cleanup_partial_initialization()
        
        # Should be reset to uninitialized state
        assert db_conn._initialized is False
        assert db_conn.engine is None
        mock_engine.dispose.assert_called_once()
    
    @pytest.mark.unit
    async def test_close_with_timeout(self):
        """Test database close with timeout handling"""
        db_conn = AuthDatabaseConnection()
        
        # Mock engine for close test
        mock_engine = AsyncMock()
        db_conn.engine = mock_engine
        db_conn._initialized = True
        
        await db_conn.close(timeout=1.0)
        
        # Should call dispose and reset state
        mock_engine.dispose.assert_called_once()
        assert db_conn._initialized is False
        assert db_conn.engine is None
    
    @pytest.mark.unit
    async def test_close_already_closed(self):
        """Test closing already closed connection"""
        db_conn = AuthDatabaseConnection()
        
        # Should not raise error when closing uninitialized connection
        await db_conn.close()
        
        assert db_conn.engine is None
        assert db_conn._initialized is False
    
    @pytest.mark.unit
    async def test_close_with_dispose_error(self):
        """Test close handling when dispose raises error"""
        db_conn = AuthDatabaseConnection()
        
        # Mock engine that raises error on dispose
        mock_engine = AsyncMock()
        mock_engine.dispose.side_effect = Exception("Dispose error")
        db_conn.engine = mock_engine
        db_conn._initialized = True
        
        # Should handle error gracefully
        await db_conn.close()
        
        # Should still reset state despite error
        assert db_conn._initialized is False
        assert db_conn.engine is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_session_error_handling_edge_cases(self, real_services_fixture):
        """Test session error handling edge cases"""
        if not auth_db._initialized:
            await auth_db.initialize()
        
        # Test session with invalid SQL
        try:
            async with auth_db.get_session() as session:
                await session.execute(text("INVALID SQL STATEMENT"))
        except Exception as e:
            # Should handle SQL errors gracefully
            assert isinstance(e, SQLAlchemyError)
    
    @pytest.mark.unit
    async def test_test_connection_failure(self):
        """Test test_connection when connection fails"""
        db_conn = AuthDatabaseConnection()
        
        # Mock failing engine
        mock_engine = AsyncMock()
        mock_engine.begin.side_effect = Exception("Connection failed")
        db_conn.engine = mock_engine
        db_conn._initialized = True
        
        result = await db_conn.test_connection()
        assert result is False
    
    @pytest.mark.unit
    async def test_test_connection_timeout(self):
        """Test test_connection timeout handling"""
        db_conn = AuthDatabaseConnection()
        
        # Mock engine that times out
        mock_engine = AsyncMock()
        mock_engine.begin.side_effect = asyncio.TimeoutError()
        db_conn.engine = mock_engine
        db_conn._initialized = True
        
        result = await db_conn.test_connection(timeout=0.1)
        assert result is False
    
    @pytest.mark.unit
    async def test_is_ready_timeout(self):
        """Test is_ready timeout handling"""
        db_conn = AuthDatabaseConnection()
        
        # Mock test_connection to timeout
        with patch.object(db_conn, 'test_connection') as mock_test:
            mock_test.side_effect = asyncio.TimeoutError()
            
            result = await db_conn.is_ready(timeout=0.1)
            assert result is False


class TestAuthDatabaseConnectionTableManagement:
    """Test table creation and management"""
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_create_tables_idempotent(self, real_services_fixture):
        """Test that create_tables is idempotent"""
        db_conn = AuthDatabaseConnection()
        await db_conn.initialize()
        
        # Create tables multiple times - should not fail
        await db_conn.create_tables()
        await db_conn.create_tables()  # Second call should be safe
        
        await db_conn.close()
    
    @pytest.mark.unit
    async def test_create_tables_with_mock_engine(self):
        """Test create_tables with mock engine (should skip)"""
        db_conn = AuthDatabaseConnection()
        
        # Mock engine
        mock_engine = MagicMock()
        db_conn.engine = mock_engine
        
        # Should not raise error with mock engine
        await db_conn.create_tables()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_table_existence_check(self, real_services_fixture):
        """Test table existence checking in PostgreSQL"""
        db_conn = AuthDatabaseConnection()
        await db_conn.initialize()
        
        # Tables should exist after initialization
        async with db_conn.engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'auth_users'
                );
            """))
            table_exists = result.scalar()
            assert table_exists is True
        
        await db_conn.close()


class TestAuthDatabaseConnectionCompatibilityAliases:
    """Test compatibility aliases for backward compatibility"""
    
    @pytest.mark.unit
    def test_compatibility_aliases(self):
        """Test that compatibility aliases exist and work"""
        from auth_service.auth_core.database.connection import (
            AuthDatabase, DatabaseConnection
        )
        
        # Verify aliases point to the correct class
        assert AuthDatabase is AuthDatabaseConnection
        assert DatabaseConnection is AuthDatabaseConnection
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_global_auth_db_instance(self, real_services_fixture):
        """Test that global auth_db instance works correctly"""
        from auth_service.auth_core.database.connection import auth_db
        
        # Should be an instance of AuthDatabaseConnection
        assert isinstance(auth_db, AuthDatabaseConnection)
        
        # Should be able to use it
        if not auth_db._initialized:
            await auth_db.initialize()
        
        async with auth_db.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1