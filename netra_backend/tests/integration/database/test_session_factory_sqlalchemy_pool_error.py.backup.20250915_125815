"""
Session Factory SQLAlchemy Pool Error Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure database session management works correctly in real service scenarios
- Value Impact: Prevents 500 errors that would break user agent interactions and data persistence
- Strategic Impact: Database reliability is foundational to all business operations

CRITICAL: These integration tests reproduce the session factory issues that occurred
when QueuePool was incompatible with async engines. They test with real database connections.

Integration Points Tested:
1. RequestScopedSessionFactory with pool configuration errors
2. Session lifecycle management under different pool configurations
3. Concurrent session creation with incompatible pools
4. Database transaction handling with pool errors
5. Session isolation and cleanup with various pool types

IMPORTANT: These tests use REAL database connections and MUST take measurable time.
"""

import asyncio
import pytest
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, AsyncGenerator
from unittest.mock import patch, AsyncMock
from contextlib import asynccontextmanager
import uuid

# Database imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool, AsyncAdaptedQueuePool, StaticPool
from sqlalchemy.exc import ArgumentError, DatabaseError
from sqlalchemy import text

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.isolated_environment_fixtures import isolated_env

# Application imports - using SSOT database module
from netra_backend.app.database import get_database_url, get_engine, get_sessionmaker
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class MockRequestScopedSessionFactory:
    """Mock session factory that reproduces the original QueuePool issue."""
    
    def __init__(self, database_url: str, use_broken_config: bool = False):
        self.database_url = database_url
        self.use_broken_config = use_broken_config
        self._engine = None
        self._sessionmaker = None
        self.sessions_created = 0
        self.errors_encountered = []
        
    async def initialize(self):
        """Initialize the session factory with potentially broken configuration."""
        try:
            if self.use_broken_config:
                # This reproduces the original broken configuration
                self._engine = create_async_engine(
                    self.database_url,
                    poolclass=QueuePool,  # BROKEN: Incompatible with async engines
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=5,
                    echo=False,
                    future=True
                )
            else:
                # This uses the fixed configuration
                self._engine = create_async_engine(
                    self.database_url,
                    # poolclass omitted - uses default async-compatible pool
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=5,
                    echo=False,
                    future=True
                )
            
            self._sessionmaker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )
            
            logger.info(f"Initialized session factory with broken_config={self.use_broken_config}")
            
        except Exception as e:
            self.errors_encountered.append({
                "operation": "initialize",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            })
            raise
    
    @asynccontextmanager
    async def get_request_scoped_session(self, user_id: str, request_id: str) -> AsyncGenerator[AsyncSession, None]:
        """Create request-scoped session (may fail with broken config)."""
        session = None
        try:
            if not self._sessionmaker:
                raise RuntimeError("Session factory not initialized")
            
            session = self._sessionmaker()
            self.sessions_created += 1
            
            logger.info(f"Created session {self.sessions_created} for user {user_id}, request {request_id}")
            yield session
            
        except Exception as e:
            self.errors_encountered.append({
                "operation": "get_request_scoped_session",
                "user_id": user_id,
                "request_id": request_id,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            })
            
            if session:
                try:
                    await session.rollback()
                except:
                    pass
            raise
        finally:
            if session:
                try:
                    await session.close()
                except:
                    pass
    
    async def cleanup(self):
        """Clean up resources."""
        if self._engine:
            await self._engine.dispose()


@pytest.mark.integration
@pytest.mark.real_services
class TestSessionFactorySQLAlchemyPoolError:
    """Integration tests for session factory pool configuration errors."""
    
    @pytest.fixture
    async def sqlite_database_url(self, isolated_env):
        """Provide SQLite database URL for integration testing."""
        # Use a file-based SQLite for more realistic testing
        db_path = f"/tmp/test_pool_error_{int(time.time())}.db"
        return f"sqlite+aiosqlite:///{db_path}"
    
    @pytest.fixture
    async def broken_session_factory(self, sqlite_database_url):
        """Provide session factory with broken QueuePool configuration."""
        factory = MockRequestScopedSessionFactory(sqlite_database_url, use_broken_config=True)
        
        # This should fail during initialization
        with pytest.raises(ArgumentError, match=r"Pool class QueuePool cannot be used with asyncio engine"):
            await factory.initialize()
            
        return factory
    
    @pytest.fixture
    async def working_session_factory(self, sqlite_database_url):
        """Provide session factory with correct configuration."""
        factory = MockRequestScopedSessionFactory(sqlite_database_url, use_broken_config=False)
        await factory.initialize()
        
        yield factory
        
        # Cleanup
        await factory.cleanup()
    
    async def test_get_request_scoped_db_session_fails(self, sqlite_database_url, isolated_env):
        """MUST fail when get_request_scoped_db_session() tries to create session with QueuePool.
        
        This test reproduces the exact error that would occur when the dependencies.py
        function tries to create a session with the broken pool configuration.
        """
        start_time = time.time()
        
        # Arrange: Mock the database configuration to use broken QueuePool
        with patch('netra_backend.app.database.get_database_url') as mock_get_url:
            mock_get_url.return_value = sqlite_database_url
            
            # Mock the engine creation to use broken config
            original_create_engine = create_async_engine
            
            def broken_create_engine(*args, **kwargs):
                # Force QueuePool usage (reproducing original bug)
                kwargs['poolclass'] = QueuePool
                return original_create_engine(*args, **kwargs)
            
            with patch('netra_backend.app.database.create_async_engine', side_effect=broken_create_engine):
                # Act & Assert: Attempt to use the broken configuration
                with pytest.raises(ArgumentError, match=r"Pool class QueuePool cannot be used with asyncio engine"):
                    # This should fail when trying to get the engine
                    from netra_backend.app.dependencies import get_request_scoped_db_session
                    
                    # Force re-creation of global engine with broken config
                    import netra_backend.app.database
                    netra_backend.app.database._engine = None  # Reset global state
                    
                    # This should fail at engine creation
                    async for session in get_request_scoped_db_session():
                        # This should never be reached
                        assert False, "Session creation should have failed with QueuePool error"
        
        # Verify test execution time (integration test must take time)
        execution_time = time.time() - start_time
        assert execution_time > 2.0, f"Integration test execution time {execution_time:.3f}s too fast - must use real services"
    
    async def test_session_factory_initialization_fails(self, sqlite_database_url, isolated_env):
        """MUST fail when RequestScopedSessionFactory tries to create sessions with QueuePool.
        
        This test validates that session factory initialization properly fails
        when configured with incompatible pool classes.
        """
        start_time = time.time()
        
        # Arrange: Create factory with broken configuration
        factory = MockRequestScopedSessionFactory(sqlite_database_url, use_broken_config=True)
        
        # Act & Assert: Factory initialization should fail
        with pytest.raises(ArgumentError, match=r"Pool class QueuePool cannot be used with asyncio engine"):
            await factory.initialize()
        
        # Verify error was recorded
        assert len(factory.errors_encountered) == 1
        error = factory.errors_encountered[0]
        assert error["operation"] == "initialize"
        assert "cannot be used with asyncio engine" in error["error"]
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 2.0, f"Integration test execution time {execution_time:.3f}s too fast"
    
    async def test_concurrent_session_creation_fails(self, sqlite_database_url, isolated_env):
        """MUST fail for multiple concurrent session attempts with QueuePool.
        
        This test validates that concurrent session creation attempts all fail
        consistently when using incompatible pool configuration.
        """
        start_time = time.time()
        
        # Arrange: Prepare concurrent session creation tasks
        async def attempt_session_creation(user_id: str, request_id: str) -> Dict:
            """Attempt to create a session and return result."""
            try:
                factory = MockRequestScopedSessionFactory(sqlite_database_url, use_broken_config=True)
                await factory.initialize()  # This should fail
                
                # If we somehow get here, try to create a session
                async with factory.get_request_scoped_session(user_id, request_id) as session:
                    result = await session.execute(text("SELECT 1"))
                    return {"success": True, "user_id": user_id, "error": None}
                    
            except Exception as e:
                return {"success": False, "user_id": user_id, "error": str(e)}
        
        # Act: Attempt concurrent session creation (all should fail)
        concurrent_tasks = [
            attempt_session_creation(f"user_{i}", f"req_{i}") 
            for i in range(5)
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=False)
        
        # Assert: All attempts should fail with QueuePool error
        for result in results:
            assert not result["success"], f"Session creation should have failed for user {result['user_id']}"
            assert "cannot be used with asyncio engine" in result["error"], (
                f"Expected QueuePool error for user {result['user_id']}, got: {result['error']}"
            )
        
        # Verify all users failed
        failed_users = [r["user_id"] for r in results if not r["success"]]
        assert len(failed_users) == 5, f"Expected 5 failures, got {len(failed_users)}"
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 2.0, f"Integration test execution time {execution_time:.3f}s too fast"
    
    async def test_working_session_factory_succeeds(self, working_session_factory, isolated_env):
        """Test that properly configured session factory works correctly.
        
        This serves as a positive control test to validate that the fixed
        configuration works as expected in integration scenarios.
        """
        start_time = time.time()
        
        # Act: Create multiple sessions concurrently with working config
        async def create_and_test_session(user_id: str, request_id: str) -> Dict:
            """Create session and perform database operations."""
            try:
                async with working_session_factory.get_request_scoped_session(user_id, request_id) as session:
                    # Test basic database operations
                    result = await session.execute(text("SELECT 1 as test_value"))
                    row = result.fetchone()
                    
                    # Test transaction
                    await session.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER, value TEXT)"))
                    await session.execute(text("INSERT INTO test_table (id, value) VALUES (:id, :value)"), 
                                        {"id": int(user_id.split("_")[1]), "value": f"test_{request_id}"})
                    await session.commit()
                    
                    # Verify insertion
                    result = await session.execute(text("SELECT COUNT(*) FROM test_table WHERE id = :id"), 
                                                 {"id": int(user_id.split("_")[1])})
                    count = result.scalar()
                    
                    return {
                        "success": True,
                        "user_id": user_id,
                        "test_value": row[0],
                        "record_count": count,
                        "error": None
                    }
                    
            except Exception as e:
                return {"success": False, "user_id": user_id, "error": str(e)}
        
        # Create concurrent sessions
        tasks = [
            create_and_test_session(f"user_{i}", f"req_{i}")
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Assert: All sessions should work correctly
        for result in results:
            assert result["success"], f"Session should work for user {result['user_id']}: {result.get('error')}"
            assert result["test_value"] == 1, f"Test query failed for user {result['user_id']}"
            assert result["record_count"] == 1, f"Transaction failed for user {result['user_id']}"
        
        # Verify factory statistics
        assert working_session_factory.sessions_created >= 3, "Factory should track created sessions"
        assert len(working_session_factory.errors_encountered) == 0, "No errors should occur with working config"
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 2.0, f"Integration test execution time {execution_time:.3f}s too fast"
    
    async def test_session_isolation_with_different_pools(self, sqlite_database_url, isolated_env):
        """Test session isolation when using different pool configurations.
        
        This test validates that different pool configurations maintain proper
        session isolation and don't interfere with each other.
        """
        start_time = time.time()
        
        # Create factories with different pool configurations
        working_factories = []
        
        # Factory 1: NullPool
        factory1 = MockRequestScopedSessionFactory(sqlite_database_url.replace(".db", "_1.db"), use_broken_config=False)
        
        # Manually set different pool for variety
        factory1.database_url = sqlite_database_url.replace(".db", "_1.db")
        factory1._engine = create_async_engine(
            factory1.database_url,
            poolclass=NullPool,
            echo=False,
            future=True
        )
        factory1._sessionmaker = async_sessionmaker(
            factory1._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        working_factories.append(("NullPool", factory1))
        
        # Factory 2: StaticPool  
        factory2 = MockRequestScopedSessionFactory(sqlite_database_url.replace(".db", "_2.db"), use_broken_config=False)
        factory2.database_url = sqlite_database_url.replace(".db", "_2.db")
        factory2._engine = create_async_engine(
            factory2.database_url,
            poolclass=StaticPool,
            pool_size=1,
            echo=False,
            future=True
        )
        factory2._sessionmaker = async_sessionmaker(
            factory2._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        working_factories.append(("StaticPool", factory2))
        
        try:
            # Test each factory independently
            for pool_name, factory in working_factories:
                # Create isolated data in each factory's database
                async with factory.get_request_scoped_session(f"user_{pool_name}", f"req_{pool_name}") as session:
                    await session.execute(text("CREATE TABLE IF NOT EXISTS isolation_test (pool_name TEXT, data TEXT)"))
                    await session.execute(text("INSERT INTO isolation_test (pool_name, data) VALUES (:pool, :data)"),
                                        {"pool": pool_name, "data": f"data_from_{pool_name}"})
                    await session.commit()
                    
                    # Verify data isolation
                    result = await session.execute(text("SELECT COUNT(*) FROM isolation_test WHERE pool_name = :pool"),
                                                 {"pool": pool_name})
                    count = result.scalar()
                    assert count == 1, f"Data isolation failed for {pool_name}"
            
            # Verify data isolation between factories
            for pool_name, factory in working_factories:
                async with factory.get_request_scoped_session(f"verify_{pool_name}", f"verify_req_{pool_name}") as session:
                    result = await session.execute(text("SELECT data FROM isolation_test WHERE pool_name = :pool"),
                                                 {"pool": pool_name})
                    row = result.fetchone()
                    assert row is not None, f"Data not found for {pool_name}"
                    assert row[0] == f"data_from_{pool_name}", f"Data corruption detected for {pool_name}"
                    
                    # Verify other pool's data is NOT in this database
                    other_pools = [p for p, _ in working_factories if p != pool_name]
                    for other_pool in other_pools:
                        result = await session.execute(text("SELECT COUNT(*) FROM isolation_test WHERE pool_name = :pool"),
                                                     {"pool": other_pool})
                        count = result.scalar()
                        assert count == 0, f"Data leak detected: {other_pool} data found in {pool_name} database"
            
        finally:
            # Cleanup all factories
            for _, factory in working_factories:
                await factory.cleanup()
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 3.0, f"Integration test execution time {execution_time:.3f}s too fast"
    
    async def test_real_database_url_configuration_integration(self, isolated_env, real_services_fixture):
        """Test integration with real database URL configuration.
        
        This test validates that our database URL building and pool configuration
        works correctly with real database services.
        """
        start_time = time.time()
        
        # Arrange: Get real database configuration
        db_info = real_services_fixture.get("db")
        if not db_info:
            pytest.skip("Real database services not available")
        
        # Test with the current (fixed) configuration
        try:
            # Use the actual database module functions
            database_url = get_database_url()
            assert database_url, "Database URL should be available"
            
            # Test engine creation (should use fixed configuration)
            engine = get_engine()
            assert engine is not None, "Engine should be created successfully"
            
            # Test sessionmaker
            sessionmaker = get_sessionmaker()
            assert sessionmaker is not None, "Sessionmaker should be created successfully"
            
            # Test actual session creation and basic operation
            async with sessionmaker() as session:
                # Test basic query
                result = await session.execute(text("SELECT 1 as integration_test"))
                row = result.fetchone()
                assert row[0] == 1, "Basic database query should work"
                
                # Test table operations
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS pool_integration_test (
                        id SERIAL PRIMARY KEY,
                        test_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                test_data = f"integration_test_{int(time.time())}"
                await session.execute(text("""
                    INSERT INTO pool_integration_test (test_data) 
                    VALUES (:data)
                """), {"data": test_data})
                
                await session.commit()
                
                # Verify insertion
                result = await session.execute(text("""
                    SELECT test_data FROM pool_integration_test 
                    WHERE test_data = :data
                """), {"data": test_data})
                
                row = result.fetchone()
                assert row is not None, "Inserted data should be retrievable"
                assert row[0] == test_data, "Inserted data should match"
        
        except Exception as e:
            pytest.fail(f"Real database integration failed: {e}")
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 2.5, f"Integration test execution time {execution_time:.3f}s too fast"