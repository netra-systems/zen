"""Critical Test: Database Connection Leak Prevention

This test verifies that SQLAlchemy connections are properly returned to the pool
and not leaked when garbage collection occurs.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Prevent connection pool exhaustion and system crashes
- Value Impact: Ensures database connections are properly managed
- Strategic Impact: Critical for system reliability and scalability
"""

import asyncio
import gc
import logging
import warnings
from typing import List
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import QueuePool, NullPool

from netra_backend.app.database import get_db
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.services.database.unit_of_work import UnitOfWork


class TestDatabaseConnectionLeaks:
    """Test suite for database connection leak prevention."""
    
    @pytest.mark.asyncio
    async def test_session_cleanup_no_garbage_collection_warning(self, caplog):
        """Verify sessions are properly cleaned up without GC warnings.
        
        The error we're preventing:
        'The garbage collector is trying to clean up non-checked-in connection'
        """
        with caplog.at_level(logging.WARNING):
            # Create and use sessions normally
            sessions_created = []
            
            for _ in range(5):
                async for session in get_db():
                    assert isinstance(session, AsyncSession)
                    result = await session.execute(text("SELECT 1"))
                    assert result.scalar() == 1
                    sessions_created.append(id(session))
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)  # Allow async cleanup
            
            # Check no warnings about non-checked-in connections
            gc_warnings = [
                record for record in caplog.records 
                if "garbage collector" in record.message.lower() 
                and "non-checked-in connection" in record.message.lower()
            ]
            
            assert len(gc_warnings) == 0, f"Found GC warnings: {[w.message for w in gc_warnings]}"
    
    @pytest.mark.asyncio
    async def test_unit_of_work_cleanup_on_exception(self, caplog):
        """Verify UnitOfWork properly cleans up sessions on exceptions."""
        with caplog.at_level(logging.WARNING):
            
            async def failing_operation():
                """Operation that fails after creating a session."""
                async with UnitOfWork() as uow:
                    # Verify session is created
                    assert uow.session is not None
                    # Simulate an operation failure
                    raise ValueError("Test exception")
            
            # Run the failing operation
            with pytest.raises(ValueError, match="Test exception"):
                await failing_operation()
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)
            
            # Verify no connection leak warnings
            gc_warnings = [
                record for record in caplog.records 
                if "garbage collector" in record.message.lower() 
                and "non-checked-in connection" in record.message.lower()
            ]
            
            assert len(gc_warnings) == 0, f"UnitOfWork leaked connections: {[w.message for w in gc_warnings]}"
    
    @pytest.mark.asyncio
    async def test_connection_pool_metrics_after_usage(self):
        """Verify connection pool properly tracks connection state."""
        # Get initial pool state
        engine = DatabaseManager.create_application_engine()
        pool = engine.pool
        
        # Skip test for NullPool (used with SQLite)
        if isinstance(pool, NullPool):
            pytest.skip("NullPool doesn't track connections")
        
        if isinstance(pool, QueuePool):
            initial_checked_out = pool.checkedout()
            
            # Use multiple sessions
            async def use_session():
                async with DatabaseManager.get_async_session() as session:
                    await session.execute(text("SELECT 1"))
            
            # Run concurrent sessions
            await asyncio.gather(*[use_session() for _ in range(5)])
            
            # Verify all connections returned to pool
            final_checked_out = pool.checkedout()
            assert final_checked_out == initial_checked_out, \
                f"Connections leaked: initial={initial_checked_out}, final={final_checked_out}"
    
    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup(self, caplog):
        """Test that async context managers properly clean up sessions."""
        with caplog.at_level(logging.WARNING):
            
            async def create_and_abandon_session():
                """Create a session and let it go out of scope."""
                async with DatabaseManager.get_async_session() as session:
                    await session.execute(text("SELECT 1"))
                    # Session should be cleaned up when context exits
            
            # Create multiple sessions
            for _ in range(10):
                await create_and_abandon_session()
            
            # Force GC
            gc.collect()
            await asyncio.sleep(0.1)
            
            # Check for leak warnings
            gc_warnings = [
                record for record in caplog.records 
                if "garbage collector" in record.message.lower() 
                and "non-checked-in connection" in record.message.lower()
            ]
            
            assert len(gc_warnings) == 0, "Sessions not properly cleaned up by context manager"
    
    @pytest.mark.asyncio
    async def test_concurrent_session_usage_no_leaks(self, caplog):
        """Test concurrent session usage doesn't cause leaks."""
        with caplog.at_level(logging.WARNING):
            
            async def worker(worker_id: int):
                """Simulate a worker using database sessions."""
                for i in range(3):
                    async with DatabaseManager.get_async_session() as session:
                        result = await session.execute(
                            text("SELECT :worker_id, :iteration"),
                            {"worker_id": worker_id, "iteration": i}
                        )
                        assert result.first() == (worker_id, i)
            
            # Run multiple workers concurrently
            await asyncio.gather(*[worker(i) for i in range(10)])
            
            # Force cleanup
            gc.collect()
            await asyncio.sleep(0.1)
            
            # Verify no leaks
            gc_warnings = [
                record for record in caplog.records 
                if "garbage collector" in record.message.lower() 
                and "non-checked-in connection" in record.message.lower()
            ]
            
            assert len(gc_warnings) == 0, f"Concurrent usage caused leaks: {len(gc_warnings)} warnings"
    
    @pytest.mark.asyncio
    async def test_session_factory_warning_suppression(self):
        """Verify that direct session factory usage is discouraged."""
        # Get the session factory
        session_factory = DatabaseManager.get_application_session()
        
        # Direct usage should work but is dangerous
        session = session_factory()
        
        # This would leak if not properly closed
        try:
            await session.execute(text("SELECT 1"))
        finally:
            # Manual cleanup required
            await session.close()
        
        # Verify session was closed
        assert session.is_active == False


@pytest.mark.asyncio
async def test_connection_leak_prevention_integration():
    """Integration test for connection leak prevention."""
    # Track warnings
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")
        
        # Simulate heavy session usage
        tasks = []
        for i in range(20):
            async def task(task_id):
                async with DatabaseManager.get_async_session() as session:
                    await session.execute(text(f"SELECT {task_id}"))
            tasks.append(task(i))
        
        await asyncio.gather(*tasks)
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.2)
        
        # Check for SQLAlchemy warnings
        sqlalchemy_warnings = [
            w for w in warning_list 
            if "SQLAlchemy" in str(w.category) 
            or "garbage collector" in str(w.message)
        ]
        
        assert len(sqlalchemy_warnings) == 0, \
            f"Found SQLAlchemy warnings: {[str(w.message) for w in sqlalchemy_warnings]}"