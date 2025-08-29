"""Stress tests for database session cleanup under cancellation scenarios.

These tests ensure that the database session management can handle
aggressive cancellation patterns without corruption or resource leaks.
"""

import asyncio
import pytest
import random
import gc
import weakref
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IllegalStateChangeError
from contextlib import asynccontextmanager
from typing import List, Set

from netra_backend.app.db.database_manager import DatabaseManager


class TestCancellationStress:
    """Stress tests for session cancellation scenarios."""
    
    @pytest.mark.asyncio
    async def test_immediate_cancellation(self):
        """Test cancellation immediately after session creation."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            sessions_created = []
            sessions_cleaned = []
            
            @asynccontextmanager
            async def create_mock_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.id = len(sessions_created)
                sessions_created.append(mock_session)
                mock_session.in_transaction = MagicMock(return_value=True)
                mock_session.rollback = AsyncMock()
                
                try:
                    yield mock_session
                finally:
                    sessions_cleaned.append(mock_session.id)
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Create and immediately cancel many tasks
            tasks = []
            for i in range(50):
                async def cancellable_op():
                    async with DatabaseManager.get_async_session() as session:
                        await asyncio.sleep(1)  # Will be cancelled before this
                
                task = asyncio.create_task(cancellable_op())
                tasks.append(task)
                # Cancel immediately
                task.cancel()
            
            # Wait for all cancellations to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should be cancelled
            assert all(isinstance(r, asyncio.CancelledError) for r in results)
            
            # All created sessions should be cleaned up
            assert len(sessions_cleaned) == len(sessions_created)
    
    @pytest.mark.asyncio
    async def test_cancellation_during_commit(self):
        """Test cancellation during commit operation."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            commit_started = []
            commit_completed = []
            rollback_called = []
            
            @asynccontextmanager
            async def create_mock_session():
                mock_session = AsyncMock(spec=AsyncSession)
                session_id = len(commit_started)
                
                async def slow_commit():
                    commit_started.append(session_id)
                    await asyncio.sleep(0.1)  # Slow commit
                    commit_completed.append(session_id)
                
                async def rollback():
                    rollback_called.append(session_id)
                
                mock_session.commit = slow_commit
                mock_session.rollback = rollback
                mock_session.in_transaction = MagicMock(return_value=True)
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Start operations that will be cancelled during commit
            async def operation_with_commit():
                async with DatabaseManager.get_async_session() as session:
                    await session.commit()  # Will be cancelled during this
            
            tasks = []
            for _ in range(10):
                task = asyncio.create_task(operation_with_commit())
                tasks.append(task)
            
            # Let commits start
            await asyncio.sleep(0.01)
            
            # Cancel all tasks
            for task in tasks:
                task.cancel()
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should be cancelled
            assert all(isinstance(r, asyncio.CancelledError) for r in results)
            
            # Commits should have started but not completed
            assert len(commit_started) == 10
            assert len(commit_completed) < 10
    
    @pytest.mark.asyncio
    async def test_cancellation_during_rollback(self):
        """Test cancellation during rollback operation."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            rollback_started = []
            rollback_completed = []
            
            @asynccontextmanager
            async def create_mock_session():
                mock_session = AsyncMock(spec=AsyncSession)
                session_id = len(rollback_started)
                
                async def slow_rollback():
                    rollback_started.append(session_id)
                    try:
                        # Use shield to protect rollback
                        await asyncio.shield(asyncio.sleep(0.05))
                        rollback_completed.append(session_id)
                    except asyncio.CancelledError:
                        # Rollback was cancelled but we tried to shield it
                        pass
                
                mock_session.rollback = slow_rollback
                mock_session.in_transaction = MagicMock(return_value=True)
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Operations that will fail and trigger rollback
            async def failing_operation():
                async with DatabaseManager.get_async_session() as session:
                    raise ValueError("Trigger rollback")
            
            tasks = []
            for _ in range(10):
                task = asyncio.create_task(failing_operation())
                tasks.append(task)
            
            # Let rollbacks start
            await asyncio.sleep(0.01)
            
            # Cancel tasks during rollback
            for task in tasks:
                task.cancel()
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Should see mix of ValueError and CancelledError
            value_errors = [r for r in results if isinstance(r, ValueError)]
            cancelled = [r for r in results if isinstance(r, asyncio.CancelledError)]
            
            assert len(value_errors) > 0 or len(cancelled) > 0
            
            # Some rollbacks should have started
            assert len(rollback_started) > 0
    
    @pytest.mark.asyncio
    async def test_cascading_cancellations(self):
        """Test cascading cancellations in dependent operations."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            operation_chain = []
            
            @asynccontextmanager
            async def create_mock_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.in_transaction = MagicMock(return_value=False)
                
                async def execute(query):
                    operation_chain.append(("execute", query))
                    await asyncio.sleep(0.01)
                    return MagicMock()
                
                mock_session.execute = execute
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Create chain of dependent operations
            async def dependent_operations():
                async with DatabaseManager.get_async_session() as session:
                    await session.execute("QUERY_1")
                    
                    # Start nested operation
                    async def nested():
                        async with DatabaseManager.get_async_session() as nested_session:
                            await nested_session.execute("QUERY_2")
                            await asyncio.sleep(0.1)  # Will be cancelled
                            await nested_session.execute("QUERY_3")
                    
                    nested_task = asyncio.create_task(nested())
                    await asyncio.sleep(0.02)
                    nested_task.cancel()  # Cancel nested operation
                    
                    try:
                        await nested_task
                    except asyncio.CancelledError:
                        pass
                    
                    # Parent should continue
                    await session.execute("QUERY_4")
            
            await dependent_operations()
            
            # Check operation chain
            queries = [op[1] for op in operation_chain if op[0] == "execute"]
            assert "QUERY_1" in queries
            assert "QUERY_2" in queries
            assert "QUERY_3" not in queries  # Cancelled before this
            assert "QUERY_4" in queries  # Parent continued
    
    @pytest.mark.asyncio
    async def test_random_cancellation_pattern(self):
        """Test random cancellation patterns to find edge cases."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            
            @asynccontextmanager
            async def create_mock_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.in_transaction = MagicMock(return_value=random.choice([True, False]))
                
                async def random_delay_operation():
                    await asyncio.sleep(random.uniform(0.001, 0.05))
                    if random.random() > 0.8:
                        raise IllegalStateChangeError("Random state error")
                
                mock_session.commit = random_delay_operation
                mock_session.rollback = random_delay_operation
                mock_session.execute = AsyncMock(side_effect=random_delay_operation)
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Run many operations with random cancellation
            async def random_operation(op_id):
                try:
                    async with DatabaseManager.get_async_session() as session:
                        # Random operations
                        for _ in range(random.randint(1, 5)):
                            await session.execute(f"QUERY_{op_id}")
                            if random.random() > 0.7:
                                await asyncio.sleep(0.1)  # Long operation
                        return f"Completed {op_id}"
                except Exception as e:
                    return f"Failed {op_id}: {type(e).__name__}"
            
            # Create tasks with random cancellation timing
            tasks = []
            cancel_tasks = []
            
            for i in range(50):
                task = asyncio.create_task(random_operation(i))
                tasks.append(task)
                
                if random.random() > 0.5:  # 50% chance of cancellation
                    async def cancel_after_delay(t, delay):
                        await asyncio.sleep(delay)
                        t.cancel()
                    
                    cancel_task = asyncio.create_task(
                        cancel_after_delay(task, random.uniform(0.001, 0.02))
                    )
                    cancel_tasks.append(cancel_task)
            
            # Wait for all operations
            await asyncio.gather(*cancel_tasks, return_exceptions=True)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            completed = sum(1 for r in results if isinstance(r, str) and "Completed" in r)
            failed = sum(1 for r in results if isinstance(r, str) and "Failed" in r)
            cancelled = sum(1 for r in results if isinstance(r, asyncio.CancelledError))
            
            # Should have mix of all outcomes
            assert completed > 0
            assert cancelled > 0
            # Failed might be 0 due to randomness, but that's ok
    
    @pytest.mark.asyncio
    async def test_cancellation_with_resource_cleanup(self):
        """Test that resources are properly cleaned up even with cancellation."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # Track resource allocation and cleanup
            resources: Set[int] = set()
            cleaned_resources: Set[int] = set()
            
            @asynccontextmanager
            async def create_session_with_resources():
                mock_session = AsyncMock(spec=AsyncSession)
                resource_id = len(resources)
                resources.add(resource_id)
                
                mock_session.resource_id = resource_id
                mock_session.in_transaction = MagicMock(return_value=True)
                
                async def cleanup():
                    cleaned_resources.add(resource_id)
                
                mock_session.close = cleanup
                mock_session.rollback = AsyncMock()
                
                try:
                    yield mock_session
                finally:
                    await cleanup()
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_session_with_resources())
            
            # Create operations that will be cancelled
            async def operation_with_resources():
                async with DatabaseManager.get_async_session() as session:
                    await asyncio.sleep(0.1)  # Will be cancelled
                    return session.resource_id
            
            # Start many operations
            tasks = []
            for _ in range(20):
                task = asyncio.create_task(operation_with_resources())
                tasks.append(task)
            
            # Cancel them at different times
            await asyncio.sleep(0.01)
            for i, task in enumerate(tasks):
                if i % 2 == 0:
                    task.cancel()
            
            await asyncio.sleep(0.02)
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # All resources should be cleaned up
            assert resources == cleaned_resources
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test that cancelled sessions don't cause memory leaks."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # Use weak references to track session lifecycle
            session_refs: List[weakref.ref] = []
            
            @asynccontextmanager
            async def create_tracked_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.in_transaction = MagicMock(return_value=False)
                
                # Create weak reference
                session_refs.append(weakref.ref(mock_session))
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_tracked_session())
            
            # Create and cancel many sessions
            async def leaky_operation():
                async with DatabaseManager.get_async_session() as session:
                    # Allocate some memory (simulate real session)
                    session.data = bytearray(1024)  # 1KB per session
                    await asyncio.sleep(0.1)
            
            tasks = []
            for _ in range(100):
                task = asyncio.create_task(leaky_operation())
                tasks.append(task)
                # Cancel immediately
                task.cancel()
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Force garbage collection
            gc.collect()
            
            # Check that sessions have been garbage collected
            alive_sessions = sum(1 for ref in session_refs if ref() is not None)
            
            # Most sessions should be collected (allow some tolerance for Python GC)
            assert alive_sessions < 10  # Less than 10% still referenced
    
    @pytest.mark.asyncio 
    async def test_cancellation_with_sqlite_workaround(self):
        """Test cancellation handling with SQLite-specific workarounds."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            
            @asynccontextmanager
            async def create_sqlite_like_session():
                """Simulate SQLite session that doesn't support certain async operations."""
                mock_session = AsyncMock(spec=AsyncSession)
                
                # SQLite doesn't support in_transaction() method
                mock_session.in_transaction = None
                
                # SQLite has different error patterns
                async def sqlite_commit():
                    if random.random() > 0.5:
                        raise AttributeError("SQLite doesn't support this")
                
                mock_session.commit = sqlite_commit
                mock_session.rollback = AsyncMock(side_effect=AttributeError)
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_sqlite_like_session())
            
            # Should handle SQLite quirks during cancellation
            async def sqlite_operation():
                async with DatabaseManager.get_async_session() as session:
                    await asyncio.sleep(0.01)
                    return "Success"
            
            task = asyncio.create_task(sqlite_operation())
            await asyncio.sleep(0.005)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected
            
            # Should not raise AttributeError from SQLite quirks


class TestCancellationRecovery:
    """Test recovery from cancellation scenarios."""
    
    @pytest.mark.asyncio
    async def test_session_reuse_after_cancellation(self):
        """Test that new sessions work correctly after previous cancellations."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            session_counter = 0
            
            @asynccontextmanager
            async def create_numbered_session():
                nonlocal session_counter
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.id = session_counter
                session_counter += 1
                mock_session.in_transaction = MagicMock(return_value=False)
                mock_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=mock_session.id)))
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_numbered_session())
            
            # First operation gets cancelled
            task1 = asyncio.create_task(DatabaseManager.get_async_session().__aenter__())
            await asyncio.sleep(0.001)
            task1.cancel()
            try:
                await task1
            except asyncio.CancelledError:
                pass
            
            # Second operation should work fine
            async with DatabaseManager.get_async_session() as session:
                result = await session.execute("SELECT 1")
                value = result.scalar()
                assert value >= 0  # Should get a valid session ID
            
            # Third operation should also work
            async with DatabaseManager.get_async_session() as session:
                result = await session.execute("SELECT 2")
                value = result.scalar()
                assert value >= 0
    
    @pytest.mark.asyncio
    async def test_partial_cancellation_recovery(self):
        """Test recovery when only some operations in a batch are cancelled."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            
            @asynccontextmanager
            async def create_mock_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.in_transaction = MagicMock(return_value=False)
                mock_session.execute = AsyncMock(return_value=MagicMock())
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Run batch of operations
            async def batch_operation(op_id, should_cancel):
                if should_cancel:
                    await asyncio.sleep(0.01)
                    # Will be cancelled externally
                    await asyncio.sleep(1)
                    return f"Should not reach here {op_id}"
                else:
                    async with DatabaseManager.get_async_session() as session:
                        await session.execute(f"SELECT {op_id}")
                        return f"Completed {op_id}"
            
            # Create mixed batch
            tasks = []
            for i in range(10):
                should_cancel = i % 3 == 0  # Cancel every 3rd
                task = asyncio.create_task(batch_operation(i, should_cancel))
                if should_cancel:
                    # Schedule cancellation
                    asyncio.create_task(self._cancel_after(task, 0.02))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            completed = [r for r in results if isinstance(r, str) and "Completed" in r]
            cancelled = [r for r in results if isinstance(r, asyncio.CancelledError)]
            
            assert len(completed) > 0
            assert len(cancelled) > 0
            
            # Non-cancelled operations should have completed successfully
            for i, result in enumerate(results):
                if i % 3 != 0:  # Not cancelled
                    assert isinstance(result, str) and f"Completed {i}" in result
    
    async def _cancel_after(self, task, delay):
        """Helper to cancel a task after a delay."""
        await asyncio.sleep(delay)
        task.cancel()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])