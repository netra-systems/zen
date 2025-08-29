"""Edge case tests for concurrent database session operations.

These tests ensure that the database session management can handle
extreme concurrent access patterns without raising IllegalStateChangeError.
"""

import asyncio
import pytest
import random
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IllegalStateChangeError, OperationalError
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from netra_backend.app.db.database_manager import DatabaseManager


class TestConcurrentEdgeCases:
    """Test edge cases in concurrent database session access."""
    
    @pytest.mark.asyncio
    async def test_thundering_herd_problem(self):
        """Test handling of many simultaneous session requests (thundering herd)."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            sessions_created = []
            creation_times = []
            
            @asynccontextmanager
            async def create_mock_session():
                creation_time = time.time()
                creation_times.append(creation_time)
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.id = len(sessions_created)
                mock_session.in_transaction = MagicMock(return_value=False)
                mock_session.created_at = creation_time
                sessions_created.append(mock_session)
                # Simulate some connection delay
                await asyncio.sleep(0.001)
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Create 100 simultaneous requests
            async def request_session(request_id):
                async with DatabaseManager.get_async_session() as session:
                    return f"Request {request_id} got session {session.id}"
            
            # Launch all at once
            tasks = [asyncio.create_task(request_session(i)) for i in range(100)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            assert all(isinstance(r, str) and "got session" in r for r in results)
            assert len(sessions_created) == 100
            
            # Check that creation was spread out (not all at exact same time)
            # This simulates connection pool throttling
            time_spread = max(creation_times) - min(creation_times)
            assert time_spread > 0  # Some time spread due to async scheduling
    
    @pytest.mark.asyncio
    async def test_session_leak_under_exceptions(self):
        """Test that sessions don't leak when exceptions occur during operations."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            active_sessions = []
            
            @asynccontextmanager
            async def create_tracked_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.id = len(active_sessions)
                mock_session.in_transaction = MagicMock(return_value=True)
                mock_session.rollback = AsyncMock()
                active_sessions.append(mock_session)
                try:
                    yield mock_session
                finally:
                    # Track cleanup
                    mock_session.cleaned_up = True
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_tracked_session())
            
            # Run operations that fail at different points
            async def failing_operation(fail_point):
                async with DatabaseManager.get_async_session() as session:
                    if fail_point == "early":
                        raise ValueError("Early failure")
                    await asyncio.sleep(0.001)
                    if fail_point == "middle":
                        raise ValueError("Middle failure")
                    await asyncio.sleep(0.001)
                    if fail_point == "late":
                        raise ValueError("Late failure")
                    return "success"
            
            # Run mixed successful and failing operations
            tasks = []
            for i in range(20):
                fail_point = ["early", "middle", "late", None][i % 4]
                tasks.append(failing_operation(fail_point))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check that all sessions were cleaned up
            assert all(hasattr(s, 'cleaned_up') and s.cleaned_up for s in active_sessions)
            
            # Verify rollback was called for failed transactions
            for session in active_sessions:
                if session.in_transaction():
                    session.rollback.assert_called()
    
    @pytest.mark.asyncio
    async def test_race_condition_in_state_check(self):
        """Test race conditions when checking session state during concurrent access."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            
            class RacySession:
                """Session that simulates race conditions in state checks."""
                def __init__(self):
                    self.state_check_count = 0
                    self.commit_count = 0
                    self.rollback_count = 0
                
                def in_transaction(self):
                    """Simulate race condition in transaction check."""
                    self.state_check_count += 1
                    if self.state_check_count == 1:
                        return True
                    elif self.state_check_count == 2:
                        # State changed between checks
                        raise IllegalStateChangeError("State changed during check")
                    return False
                
                async def commit(self):
                    self.commit_count += 1
                    if self.commit_count > 1:
                        raise IllegalStateChangeError("Already committed")
                
                async def rollback(self):
                    self.rollback_count += 1
            
            @asynccontextmanager
            async def create_racy_session():
                session = RacySession()
                yield session
            
            mock_factory.return_value = MagicMock(return_value=create_racy_session())
            
            # Should handle the race condition gracefully
            async with DatabaseManager.get_async_session() as session:
                pass  # The fix should handle state change errors
    
    @pytest.mark.asyncio
    async def test_interleaved_operations(self):
        """Test interleaved read and write operations on different sessions."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            operation_log = []
            
            @asynccontextmanager
            async def create_logging_session():
                mock_session = AsyncMock(spec=AsyncSession)
                session_id = len(operation_log)
                mock_session.id = session_id
                
                async def log_execute(query):
                    operation_log.append(("execute", session_id, query))
                    await asyncio.sleep(random.uniform(0.001, 0.005))  # Variable delay
                    return MagicMock()
                
                async def log_commit():
                    operation_log.append(("commit", session_id))
                    await asyncio.sleep(0.001)
                
                mock_session.execute = log_execute
                mock_session.commit = log_commit
                mock_session.in_transaction = MagicMock(return_value=True)
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_logging_session())
            
            # Run interleaved read and write operations
            async def read_operation(op_id):
                async with DatabaseManager.get_async_session() as session:
                    await session.execute(f"SELECT {op_id}")
                    await session.commit()
            
            async def write_operation(op_id):
                async with DatabaseManager.get_async_session() as session:
                    await session.execute(f"INSERT {op_id}")
                    await session.commit()
            
            # Mix reads and writes
            tasks = []
            for i in range(10):
                if i % 2 == 0:
                    tasks.append(read_operation(f"read_{i}"))
                else:
                    tasks.append(write_operation(f"write_{i}"))
            
            await asyncio.gather(*tasks)
            
            # Verify operations were interleaved (not serialized)
            session_ids = [op[1] for op in operation_log]
            assert len(set(session_ids)) == 10  # Each operation got its own session
            
            # Check that operations from different sessions are interleaved
            interleaved = False
            for i in range(len(operation_log) - 1):
                if operation_log[i][1] != operation_log[i+1][1]:
                    interleaved = True
                    break
            assert interleaved, "Operations should be interleaved, not serialized"
    
    @pytest.mark.asyncio
    async def test_session_timeout_handling(self):
        """Test handling of session timeouts during long operations."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            
            @asynccontextmanager
            async def create_timeout_session():
                mock_session = AsyncMock(spec=AsyncSession)
                
                async def execute_with_timeout(query):
                    if "long" in query:
                        # Simulate timeout
                        raise asyncio.TimeoutError("Query timeout")
                    return MagicMock()
                
                mock_session.execute = execute_with_timeout
                mock_session.in_transaction = MagicMock(return_value=True)
                mock_session.rollback = AsyncMock()
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(return_value=create_timeout_session())
            
            # Test timeout handling
            with pytest.raises(asyncio.TimeoutError):
                async with DatabaseManager.get_async_session() as session:
                    await session.execute("SELECT long_running_query")
            
            # Session should still be usable for other operations
            async with DatabaseManager.get_async_session() as session:
                result = await session.execute("SELECT quick_query")
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_nested_transactions_edge_case(self):
        """Test edge cases with nested transaction contexts."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            transaction_stack = []
            
            @asynccontextmanager
            async def create_nested_session():
                mock_session = AsyncMock(spec=AsyncSession)
                session_id = len(transaction_stack)
                
                def check_transaction():
                    return len([t for t in transaction_stack if t[1] == "active"]) > 0
                
                mock_session.in_transaction = check_transaction
                
                async def begin_nested():
                    transaction_stack.append((session_id, "active"))
                    return AsyncMock()
                
                async def commit():
                    if transaction_stack:
                        transaction_stack[-1] = (transaction_stack[-1][0], "committed")
                
                mock_session.begin_nested = begin_nested
                mock_session.commit = commit
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_nested_session())
            
            # Test nested context usage
            async with DatabaseManager.get_async_session() as outer:
                await outer.begin_nested()
                async with DatabaseManager.get_async_session() as inner:
                    await inner.begin_nested()
                    # Both sessions have active transactions
                    assert outer.in_transaction()
                    assert inner.in_transaction()
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            pool_size = 5
            active_connections = []
            
            @asynccontextmanager
            async def create_pooled_session():
                if len(active_connections) >= pool_size:
                    # Pool exhausted
                    raise OperationalError("Connection pool exhausted", None, None)
                
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.id = len(active_connections)
                active_connections.append(mock_session)
                
                try:
                    yield mock_session
                finally:
                    active_connections.remove(mock_session)
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_pooled_session())
            
            # Try to exceed pool size
            async def use_connection(conn_id):
                try:
                    async with DatabaseManager.get_async_session() as session:
                        await asyncio.sleep(0.01)  # Hold connection
                        return f"Connection {conn_id} succeeded"
                except OperationalError:
                    return f"Connection {conn_id} failed - pool exhausted"
            
            # Launch more tasks than pool size
            tasks = [use_connection(i) for i in range(pool_size + 3)]
            results = await asyncio.gather(*tasks)
            
            # Some should fail due to pool exhaustion
            successes = [r for r in results if "succeeded" in r]
            failures = [r for r in results if "failed" in r]
            
            assert len(successes) <= pool_size
            assert len(failures) > 0
    
    @pytest.mark.asyncio
    async def test_cascading_failures(self):
        """Test handling of cascading failures in dependent operations."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            failure_count = 0
            
            @asynccontextmanager
            async def create_failing_session():
                nonlocal failure_count
                mock_session = AsyncMock(spec=AsyncSession)
                
                async def cascade_failure(query=None):
                    nonlocal failure_count
                    failure_count += 1
                    if failure_count < 3:
                        # First few operations fail
                        raise OperationalError("Database unavailable", None, None)
                    # Then recover
                    return MagicMock()
                
                mock_session.execute = cascade_failure
                mock_session.commit = cascade_failure
                mock_session.in_transaction = MagicMock(return_value=False)
                
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_failing_session())
            
            # Run operations that will initially fail then recover
            results = []
            for i in range(5):
                try:
                    async with DatabaseManager.get_async_session() as session:
                        await session.execute(f"SELECT {i}")
                        results.append(f"Success {i}")
                except OperationalError:
                    results.append(f"Failed {i}")
            
            # Should see initial failures then recovery
            assert any("Failed" in r for r in results[:2])
            assert any("Success" in r for r in results[2:])


class TestMemoryAndResourceManagement:
    """Test memory and resource management under concurrent load."""
    
    @pytest.mark.asyncio
    async def test_no_memory_leak_on_exceptions(self):
        """Ensure no memory leaks when exceptions occur in concurrent sessions."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            session_refs = []
            
            @asynccontextmanager
            async def create_tracked_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.id = len(session_refs)
                mock_session.in_transaction = MagicMock(return_value=True)
                mock_session.rollback = AsyncMock()
                
                # Track session creation
                session_refs.append(mock_session)
                
                # Mark session as active
                mock_session.active = True
                
                try:
                    yield mock_session
                finally:
                    # Mark session as cleaned up
                    mock_session.active = False
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_tracked_session())
            
            # Create many sessions with random failures
            async def create_and_fail():
                for _ in range(10):
                    try:
                        async with DatabaseManager.get_async_session() as session:
                            if random.random() > 0.5:
                                raise ValueError("Random failure")
                    except ValueError:
                        pass  # Expected
            
            # Run multiple tasks creating sessions
            await asyncio.gather(*[create_and_fail() for _ in range(10)])
            
            # All sessions should be cleaned up (not active)
            assert all(not s.active for s in session_refs)
            assert len(session_refs) == 100  # 10 tasks * 10 sessions each
    
    @pytest.mark.asyncio
    async def test_cleanup_order_independence(self):
        """Test that cleanup order doesn't matter for concurrent sessions."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            cleanup_order = []
            
            @asynccontextmanager
            async def create_ordered_session():
                mock_session = AsyncMock(spec=AsyncSession)
                session_id = len(cleanup_order)
                mock_session.id = session_id
                mock_session.in_transaction = MagicMock(return_value=False)
                
                yield mock_session
                
                # Record cleanup order
                cleanup_order.append(session_id)
                # Simulate variable cleanup time
                await asyncio.sleep(random.uniform(0.001, 0.005))
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_ordered_session())
            
            # Create sessions in order but let them complete in random order
            async def delayed_operation(delay, op_id):
                await asyncio.sleep(delay)
                async with DatabaseManager.get_async_session() as session:
                    return f"Operation {op_id} with session {session.id}"
            
            # Create with different delays to cause out-of-order completion
            tasks = []
            for i in range(10):
                delay = random.uniform(0, 0.01)
                tasks.append(delayed_operation(delay, i))
            
            results = await asyncio.gather(*tasks)
            
            # All operations should complete successfully regardless of order
            assert all("Operation" in r for r in results)
            
            # Cleanup order should not be strictly sequential
            assert cleanup_order != list(range(10))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])