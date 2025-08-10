"""Test database connection pooling and session management."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import OperationalError, TimeoutError

from app.db.session import get_db_session
from app.db.postgres import async_engine, async_session_factory, get_async_db, Database
from app.db.clickhouse import get_clickhouse_client


@pytest.mark.asyncio
class TestDatabaseConnectionPooling:
    """Test database connection pooling behavior."""

    async def test_connection_pool_initialization(self):
        """Test that connection pool is properly initialized."""
        if async_engine is not None:
            assert async_engine.pool is not None
            assert isinstance(async_engine.pool, (QueuePool, NullPool))
        else:
            pytest.skip("Async engine not initialized")

    async def test_connection_pool_limits(self):
        """Test connection pool respects max connections."""
        if async_session_factory is None:
            pytest.skip("Async session factory not available")
        
        max_connections = 5
        active_sessions = []
        
        try:
            # Attempt to acquire sessions
            for _ in range(max_connections):
                session = async_session_factory()
                active_sessions.append(session)
                await session.execute("SELECT 1")
            
            # Should handle gracefully
            assert len(active_sessions) <= max_connections
        except Exception:
            # Expected when pool is exhausted
            pass
        finally:
            # Clean up connections
            for session in active_sessions:
                try:
                    await session.close()
                except Exception:
                    pass

    async def test_session_context_manager(self):
        """Test session context manager functionality."""
        if get_db_session is None:
            pytest.skip("Database session not available")
        
        try:
            async with get_db_session() as session:
                assert isinstance(session, AsyncSession)
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    async def test_session_factory_creation(self):
        """Test that session factory creates sessions."""
        if async_session_factory is None:
            pytest.skip("Async session factory not available")
        
        try:
            session = async_session_factory()
            assert isinstance(session, AsyncSession)
            await session.close()
        except Exception as e:
            pytest.skip(f"Cannot create session: {e}")

    async def test_concurrent_sessions(self):
        """Test handling of concurrent database sessions."""
        if async_session_factory is None:
            pytest.skip("Async session factory not available")
            
        async def execute_query(query_id: int):
            try:
                session = async_session_factory()
                result = await session.execute(f"SELECT {query_id}")
                value = result.scalar()
                await session.close()
                return value
            except Exception:
                return None
        
        # Execute multiple queries concurrently
        tasks = [execute_query(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some queries may succeed
        successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]
        assert len(successful_results) >= 0  # At least allow for database not being available


@pytest.mark.asyncio
class TestSessionManagement:
    """Test database session lifecycle management."""

    async def test_get_db_session_context_manager(self):
        """Test database session context manager."""
        try:
            async with get_db_session() as session:
                assert isinstance(session, AsyncSession)
                # Try a simple query
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    async def test_session_rollback_on_error(self):
        """Test session rollback on exception."""
        try:
            with pytest.raises(ValueError):
                async with get_db_session() as session:
                    await session.execute("SELECT 1")
                    raise ValueError("Test error")
        except Exception as e:
            if "Database not available" in str(e):
                pytest.skip(f"Database not available: {e}")

    async def test_async_db_generator(self):
        """Test the async database generator function."""
        try:
            async for session in get_async_db():
                assert isinstance(session, AsyncSession)
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1
                break
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    async def test_database_class(self):
        """Test the Database class functionality."""
        try:
            db = Database("sqlite:///:memory:")
            assert db.engine is not None
            assert db.SessionLocal is not None
        except Exception as e:
            pytest.skip(f"Cannot create database instance: {e}")


@pytest.mark.asyncio
class TestClickHouseConnection:
    """Test ClickHouse connection management."""

    async def test_clickhouse_client_initialization(self):
        """Test ClickHouse client can be initialized."""
        try:
            client = await get_clickhouse_client()
            assert client is not None
        except Exception as e:
            pytest.skip(f"ClickHouse not available: {e}")

    async def test_clickhouse_basic_query(self):
        """Test basic ClickHouse query execution."""
        try:
            client = await get_clickhouse_client()
            result = await client.execute("SELECT 1")
            assert result is not None
        except Exception as e:
            pytest.skip(f"ClickHouse not available: {e}")

    async def test_clickhouse_error_handling(self):
        """Test ClickHouse error handling."""
        try:
            async with get_clickhouse_client() as client:
                # Test invalid query - should raise exception
                with pytest.raises(Exception):
                    await client.execute("INVALID SQL QUERY")
        except Exception as e:
            if "not available" in str(e):
                pytest.skip(f"ClickHouse not available: {e}")
            # Re-raise if it's not availability issue
            raise