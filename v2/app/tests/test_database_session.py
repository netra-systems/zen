"""Test database connection pooling and session management."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import OperationalError, TimeoutError

from app.db.session import (
    get_db, 
    AsyncSessionLocal,
    engine,
    get_clickhouse_client
)


@pytest.mark.asyncio
class TestDatabaseConnectionPooling:
    """Test database connection pooling behavior."""

    async def test_connection_pool_initialization(self):
        """Test that connection pool is properly initialized."""
        assert engine.pool is not None
        assert isinstance(engine.pool, (QueuePool, NullPool))
        assert engine.pool.size() >= 0

    async def test_connection_pool_limits(self):
        """Test connection pool respects max connections."""
        max_connections = 10
        active_connections = []
        
        try:
            # Attempt to acquire more connections than pool limit
            for _ in range(max_connections + 5):
                session = AsyncSessionLocal()
                active_connections.append(session)
            
            # Should handle gracefully when pool is exhausted
            assert len(active_connections) <= max_connections + engine.pool.overflow()
        finally:
            # Clean up connections
            for session in active_connections:
                await session.close()

    async def test_connection_pool_timeout(self):
        """Test connection acquisition timeout handling."""
        with patch.object(engine.pool, 'connect', side_effect=TimeoutError("Pool timeout")):
            with pytest.raises(TimeoutError):
                async with AsyncSessionLocal() as session:
                    await session.execute("SELECT 1")

    async def test_connection_reuse(self):
        """Test that connections are properly reused from pool."""
        connection_ids = set()
        
        for _ in range(5):
            async with AsyncSessionLocal() as session:
                # Get underlying connection ID
                result = await session.execute("SELECT CONNECTION_ID()")
                conn_id = result.scalar()
                connection_ids.add(conn_id)
        
        # Should reuse connections, not create new ones each time
        assert len(connection_ids) < 5

    async def test_concurrent_connections(self):
        """Test handling of concurrent database connections."""
        async def execute_query(query_id: int):
            async with AsyncSessionLocal() as session:
                await asyncio.sleep(0.1)  # Simulate work
                result = await session.execute(f"SELECT {query_id}")
                return result.scalar()
        
        # Execute multiple queries concurrently
        tasks = [execute_query(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All queries should complete without connection errors
        assert all(not isinstance(r, Exception) for r in results)
        assert results == list(range(20))


@pytest.mark.asyncio
class TestSessionManagement:
    """Test database session lifecycle management."""

    async def test_session_creation_and_cleanup(self):
        """Test session is properly created and cleaned up."""
        session = None
        async for session in get_db():
            assert isinstance(session, AsyncSession)
            assert session.is_active
            break
        
        # Session should be closed after generator exits
        assert session is not None
        assert not session.is_active

    async def test_session_rollback_on_error(self):
        """Test session rollback on exception."""
        with pytest.raises(ValueError):
            async for session in get_db():
                # Start a transaction
                await session.execute("BEGIN")
                # Simulate an error
                raise ValueError("Test error")
        
        # Verify session was rolled back (new session should work)
        async for session in get_db():
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1
            break

    async def test_session_commit_on_success(self):
        """Test session commits on successful operation."""
        async for session in get_db():
            # Mock the commit method
            session.commit = AsyncMock()
            
            # Perform operation
            await session.execute("SELECT 1")
            
            # Exit context to trigger cleanup
            break
        
        # Verify commit was called
        session.commit.assert_called_once()

    async def test_session_isolation(self):
        """Test that sessions are isolated from each other."""
        async def modify_session_state(session_id: int):
            async for session in get_db():
                # Set session variable
                await session.execute(f"SET @session_var = {session_id}")
                result = await session.execute("SELECT @session_var")
                return result.scalar()
        
        # Run multiple sessions concurrently
        tasks = [modify_session_state(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Each session should maintain its own state
        assert results == list(range(5))

    async def test_session_reconnect_on_connection_lost(self):
        """Test session reconnection when database connection is lost."""
        async for session in get_db():
            # Simulate connection loss
            with patch.object(session, 'execute', side_effect=OperationalError("Connection lost", None, None)):
                with pytest.raises(OperationalError):
                    await session.execute("SELECT 1")
            break
        
        # New session should work
        async for session in get_db():
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1
            break


@pytest.mark.asyncio
class TestClickHouseConnection:
    """Test ClickHouse connection management."""

    async def test_clickhouse_client_initialization(self):
        """Test ClickHouse client is properly initialized."""
        client = await get_clickhouse_client()
        assert client is not None
        
        # Test basic query
        result = await client.execute("SELECT 1")
        assert result[0][0] == 1

    async def test_clickhouse_connection_pooling(self):
        """Test ClickHouse connection pooling."""
        clients = []
        
        # Get multiple clients
        for _ in range(5):
            client = await get_clickhouse_client()
            clients.append(client)
        
        # Should reuse connections from pool
        assert len(set(id(c) for c in clients)) < 5

    async def test_clickhouse_concurrent_queries(self):
        """Test concurrent ClickHouse queries."""
        async def execute_clickhouse_query(query_id: int):
            client = await get_clickhouse_client()
            result = await client.execute(f"SELECT {query_id}")
            return result[0][0]
        
        # Execute queries concurrently
        tasks = [execute_clickhouse_query(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert results == list(range(10))

    async def test_clickhouse_error_handling(self):
        """Test ClickHouse error handling."""
        client = await get_clickhouse_client()
        
        # Test invalid query
        with pytest.raises(Exception):
            await client.execute("INVALID SQL QUERY")
        
        # Client should still work after error
        result = await client.execute("SELECT 1")
        assert result[0][0] == 1

    async def test_dual_database_transaction_coordination(self):
        """Test coordination between PostgreSQL and ClickHouse."""
        # Start PostgreSQL transaction
        async for pg_session in get_db():
            # Insert into PostgreSQL
            await pg_session.execute("INSERT INTO test_table VALUES (1, 'test')")
            
            # Insert into ClickHouse
            ch_client = await get_clickhouse_client()
            await ch_client.execute("INSERT INTO events VALUES (1, 'test_event', now())")
            
            # Both should succeed or both should fail
            await pg_session.commit()
            break
        
        # Verify both databases have the data
        async for pg_session in get_db():
            pg_result = await pg_session.execute("SELECT COUNT(*) FROM test_table WHERE id = 1")
            assert pg_result.scalar() == 1
            break
        
        ch_client = await get_clickhouse_client()
        ch_result = await ch_client.execute("SELECT COUNT(*) FROM events WHERE id = 1")
        assert ch_result[0][0] == 1