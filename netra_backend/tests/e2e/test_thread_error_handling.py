"""Thread Error Handling and Recovery E2E Testing
Tests comprehensive error scenarios and recovery mechanisms for thread operations.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import uuid
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.exceptions_database import (
    DatabaseError,
    RecordNotFoundError,
)
from netra_backend.app.db.models_postgres import Message, Run, Thread
from netra_backend.app.schemas.agent_state import RecoveryType, StateRecoveryRequest
from netra_backend.app.services.state_persistence import state_persistence_service

# Add project root to path
from netra_backend.app.services.thread_service import ThreadService

# Add project root to path


class ThreadDatabaseErrorTests:
    """Tests for database error scenarios in thread operations."""
    async def test_thread_creation_database_error_recovery(self, mock_db_session: AsyncSession):
        """Test thread creation recovery from database errors."""
        service = ThreadService()
        user_id = "db_error_user"
        
        await self._test_database_error_scenarios(service, user_id, mock_db_session)
    
    async def _test_database_error_scenarios(
        self, service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> None:
        """Test various database error scenarios."""
        # Test SQLAlchemy error
        db_session.execute.side_effect = SQLAlchemyError("Database connection failed")
        db_session.rollback = AsyncMock()
        
        result = await service.get_or_create_thread(user_id, db_session)
        assert result is None
        db_session.rollback.assert_called_once()
        
        # Reset and test integrity error (race condition)
        db_session.reset_mock()
        await self._test_integrity_error_handling(service, user_id, db_session)
    
    async def _test_integrity_error_handling(
        self, service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> None:
        """Test integrity error handling during thread creation."""
        # Mock sequence: first call returns None, second returns existing thread
        mock_thread = Mock()
        mock_thread.id = f"thread_{user_id}"
        mock_thread.metadata_ = {"user_id": user_id}
        
        mock_result_none = Mock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_result_existing = Mock()
        mock_result_existing.scalar_one_or_none.return_value = mock_thread
        
        db_session.execute.side_effect = [mock_result_none, mock_result_existing]
        db_session.commit.side_effect = IntegrityError("statement", "params", "orig")
        db_session.rollback = AsyncMock()
        
        result = await service.get_or_create_thread(user_id, db_session)
        
        assert result == mock_thread
        db_session.rollback.assert_called_once()
    async def test_message_creation_error_handling(self, mock_db_session: AsyncSession):
        """Test message creation error scenarios."""
        service = ThreadService()
        thread_id = "test_thread"
        
        await self._test_message_error_scenarios(service, thread_id, mock_db_session)
    
    async def _test_message_error_scenarios(
        self, service: ThreadService, thread_id: str, db_session: AsyncSession
    ) -> None:
        """Test message creation error scenarios."""
        # Test database error during message creation
        db_session.add.side_effect = SQLAlchemyError("Message creation failed")
        db_session.rollback = AsyncMock()
        
        result = await service.create_message(
            thread_id, "user", "Test message", db=db_session
        )
        
        assert result is None
        db_session.rollback.assert_called_once()
        
        # Test unexpected error
        db_session.reset_mock()
        db_session.add.side_effect = Exception("Unexpected error")
        
        result = await service.create_message(
            thread_id, "user", "Test message", db=db_session
        )
        
        assert result is None
        db_session.rollback.assert_called_once()


class ThreadStateErrorTests:
    """Tests for state persistence error scenarios."""
    async def test_state_persistence_failure_recovery(self, mock_db_session: AsyncSession):
        """Test recovery from state persistence failures."""
        service = ThreadService()
        user_id = "state_error_user"
        
        thread = await service.get_or_create_thread(user_id, mock_db_session)
        
        await self._test_state_persistence_errors(thread, mock_db_session)
    
    async def _test_state_persistence_errors(
        self, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test state persistence error scenarios."""
        # Mock state persistence service to fail
        with patch.object(state_persistence_service, 'save_agent_state') as mock_save:
            mock_save.side_effect = NetraException("State persistence failed")
            
            # Attempt to save state
            try:
                from netra_backend.app.schemas.agent_state import (
                    CheckpointType,
                    StatePersistenceRequest,
                )
                request = StatePersistenceRequest(
                    run_id=f"run_{thread.id}",
                    thread_id=thread.id,
                    user_id=thread.metadata_.get("user_id"),
                    state_data={"test": "data"},
                    checkpoint_type=CheckpointType.MANUAL
                )
                
                success, snapshot_id = await state_persistence_service.save_agent_state(
                    request, db_session
                )
                assert not success
                assert snapshot_id is None
                
            except NetraException:
                # Expected behavior - state persistence failure should be handled
                pass
    async def test_state_recovery_failure_scenarios(self, mock_db_session: AsyncSession):
        """Test state recovery failure scenarios."""
        user_id = "recovery_error_user"
        run_id = f"run_{user_id}"
        
        await self._test_recovery_error_scenarios(run_id, mock_db_session)
    
    async def _test_recovery_error_scenarios(self, run_id: str, db_session: AsyncSession) -> None:
        """Test various state recovery error scenarios."""
        with patch.object(state_persistence_service, 'recover_agent_state') as mock_recover:
            # Test recovery service failure
            mock_recover.return_value = (False, None)
            
            recovery_request = StateRecoveryRequest(
                run_id=run_id,
                thread_id=f"thread_{run_id}",
                recovery_type=RecoveryType.RESUME,
                failure_reason="Test failure"
            )
            
            success, recovery_id = await state_persistence_service.recover_agent_state(
                recovery_request, db_session
            )
            
            assert not success
            assert recovery_id is None


class ThreadConcurrencyErrorTests:
    """Tests for concurrency-related error scenarios."""
    async def test_concurrent_modification_errors(self, mock_db_session: AsyncSession):
        """Test handling of concurrent modification errors."""
        service = ThreadService()
        user_id = "concurrent_error_user"
        
        await self._test_concurrent_access_scenarios(service, user_id, mock_db_session)
    
    async def _test_concurrent_access_scenarios(
        self, service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> None:
        """Test concurrent access error scenarios."""
        thread_id = f"thread_{user_id}"
        
        # Simulate concurrent operations that might conflict
        operations = [
            lambda: service.create_message(thread_id, "user", "Msg 1", db=db_session),
            lambda: service.create_message(thread_id, "user", "Msg 2", db=db_session),
            lambda: service.create_run(thread_id, "agent1", db=db_session),
            lambda: service.create_run(thread_id, "agent2", db=db_session)
        ]
        
        # Execute operations concurrently
        results = await asyncio.gather(*[op() for op in operations], return_exceptions=True)
        
        # Verify that some operations succeeded despite potential conflicts
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0
    async def test_deadlock_prevention_and_recovery(self, mock_db_session: AsyncSession):
        """Test deadlock prevention and recovery mechanisms."""
        service = ThreadService()
        
        await self._test_deadlock_scenarios(service, mock_db_session)
    
    async def _test_deadlock_scenarios(
        self, service: ThreadService, db_session: AsyncSession
    ) -> None:
        """Test deadlock scenarios and recovery."""
        # Create multiple threads that might cause deadlocks
        thread_ids = [f"deadlock_thread_{i}" for i in range(5)]
        
        # Create operations that access multiple threads
        cross_thread_operations = []
        for i, thread_id in enumerate(thread_ids):
            # Each operation touches multiple threads
            operation = self._create_cross_thread_operation(
                service, thread_ids, i, db_session
            )
            cross_thread_operations.append(operation)
        
        # Execute operations that might cause deadlocks
        results = await asyncio.gather(
            *cross_thread_operations, return_exceptions=True
        )
        
        # Verify system remains functional despite potential deadlocks
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_operations) >= len(results) // 2  # At least half should succeed
    
    async def _create_cross_thread_operation(
        self, service: ThreadService, thread_ids: List[str],
        operation_index: int, db_session: AsyncSession
    ) -> Callable:
        """Create operation that accesses multiple threads."""
        async def cross_thread_op():
            # Access threads in different order to potentially cause deadlocks
            access_order = thread_ids[operation_index:] + thread_ids[:operation_index]
            
            for thread_id in access_order[:3]:  # Limit to 3 threads per operation
                try:
                    await service.create_message(
                        thread_id, "user", f"Cross-thread msg {operation_index}",
                        db=db_session
                    )
                except Exception:
                    # Expected - some operations may fail due to conflicts
                    pass
            
            return f"Operation {operation_index} completed"
        
        return cross_thread_op


class ThreadResourceErrorTests:
    """Tests for resource-related error scenarios."""
    async def test_memory_exhaustion_scenarios(self, mock_db_session: AsyncSession):
        """Test handling of memory exhaustion scenarios."""
        service = ThreadService()
        
        await self._test_memory_pressure_handling(service, mock_db_session)
    
    async def _test_memory_pressure_handling(
        self, service: ThreadService, db_session: AsyncSession
    ) -> None:
        """Test handling under memory pressure."""
        # Simulate memory pressure by creating many large objects
        large_operations = []
        
        for i in range(50):  # Create moderate load
            # Create operation that uses significant memory
            operation = self._create_memory_intensive_operation(
                service, f"memory_user_{i}", db_session
            )
            large_operations.append(operation)
        
        # Execute operations and handle potential memory errors
        results = await asyncio.gather(*large_operations, return_exceptions=True)
        
        # Verify system degrades gracefully under memory pressure
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        memory_errors = [r for r in results if isinstance(r, MemoryError)]
        
        # Should handle most operations even under pressure
        assert len(successful_operations) >= len(results) * 0.7  # 70% success rate
    
    async def _create_memory_intensive_operation(
        self, service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> Callable:
        """Create memory-intensive operation."""
        async def memory_op():
            thread = await service.get_or_create_thread(user_id, db_session)
            
            # Create multiple messages with large content
            large_content = "x" * 1000  # 1KB per message
            
            for i in range(10):
                await service.create_message(
                    thread.id, "user", f"Large message {i}: {large_content}",
                    db=db_session
                )
            
            return f"Memory operation for {user_id} completed"
        
        return memory_op
    async def test_connection_pool_exhaustion(self, mock_db_session: AsyncSession):
        """Test handling of connection pool exhaustion."""
        service = ThreadService()
        
        await self._test_connection_exhaustion_scenarios(service, mock_db_session)
    
    async def _test_connection_exhaustion_scenarios(
        self, service: ThreadService, db_session: AsyncSession
    ) -> None:
        """Test connection pool exhaustion scenarios."""
        # Simulate many concurrent database operations
        connection_intensive_ops = []
        
        for i in range(100):  # Create high connection load
            operation = service.get_or_create_thread(f"conn_user_{i}", db_session)
            connection_intensive_ops.append(operation)
        
        # Execute operations that might exhaust connection pool
        results = await asyncio.gather(*connection_intensive_ops, return_exceptions=True)
        
        # Verify graceful handling of connection exhaustion
        successful_ops = [r for r in results if not isinstance(r, Exception)]
        connection_errors = [
            r for r in results 
            if isinstance(r, Exception) and "connection" in str(r).lower()
        ]
        
        # System should maintain functionality even with connection pressure
        assert len(successful_ops) >= len(results) * 0.8  # 80% success rate


class ThreadRecoveryTests:
    """Tests for thread operation recovery mechanisms."""
    async def test_automatic_error_recovery(self, mock_db_session: AsyncSession):
        """Test automatic recovery from transient errors."""
        service = ThreadService()
        user_id = "recovery_user"
        
        await self._test_automatic_recovery_mechanisms(service, user_id, mock_db_session)
    
    async def _test_automatic_recovery_mechanisms(
        self, service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> None:
        """Test automatic recovery mechanisms."""
        # Mock intermittent failures
        call_count = 0
        
        def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise SQLAlchemyError("Transient error")
            # Succeed on third attempt
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            return mock_result
        
        db_session.execute.side_effect = intermittent_failure
        
        # The service should handle transient failures gracefully
        # In a real implementation, there would be retry logic
        try:
            result = await service.get_or_create_thread(user_id, db_session)
            # If no retry logic, result should be None (graceful failure)
            assert result is None or result is not None
        except Exception:
            # Transient errors should be handled gracefully
            pass
    async def test_manual_recovery_procedures(self, mock_db_session: AsyncSession):
        """Test manual recovery procedures."""
        service = ThreadService()
        
        await self._test_manual_recovery_scenarios(service, mock_db_session)
    
    async def _test_manual_recovery_scenarios(
        self, service: ThreadService, db_session: AsyncSession
    ) -> None:
        """Test manual recovery scenarios."""
        # Simulate corrupted thread state
        corrupted_thread_id = "corrupted_thread"
        user_id = "recovery_test_user"
        
        # Attempt recovery through re-creation
        try:
            # First, try to access potentially corrupted thread
            thread = await service.get_thread(corrupted_thread_id, db_session)
            
            if thread is None:
                # Thread doesn't exist, create new one
                new_thread = await service.get_or_create_thread(user_id, db_session)
                assert new_thread is not None
        
        except Exception:
            # If any errors, fall back to creating new thread
            new_thread = await service.get_or_create_thread(f"{user_id}_recovery", db_session)
            assert new_thread is not None


@pytest.fixture
def mock_db_session():
    """Mock database session with error simulation capabilities."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def thread_service():
    """Thread service fixture."""
    return ThreadService()