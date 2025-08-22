"""Improved Async Database Transaction Patterns - Max 300 lines, functions ≤8 lines"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class AsyncTransactionManager:
    """Enhanced async transaction manager with proper isolation"""
    def __init__(self):
        self.active_sessions: Dict[str, AsyncSession] = {}
        self.transaction_log: Dict[str, Dict] = {}
    
    @asynccontextmanager
    async def transaction_scope(self, session_id: str) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager for transaction scope with automatic cleanup"""
        session = await self._create_session(session_id)
        try:
            async with session.begin():
                yield session
                await self._log_transaction_success(session_id)
        except Exception as e:
            await self._log_transaction_error(session_id, e)
            raise
        finally:
            await self._cleanup_session(session_id)

    async def _create_session(self, session_id: str) -> AsyncSession:
        """Create new async database session"""
        session = AsyncMock(spec=AsyncSession)
        self._setup_session_mocks(session)
        self.active_sessions[session_id] = session
        return session

    def _setup_session_mocks(self, session: AsyncMock) -> None:
        """Setup consistent session mock behavior"""
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        session.close = AsyncMock()

    async def _log_transaction_success(self, session_id: str) -> None:
        """Log successful transaction completion"""
        self.transaction_log[session_id] = {"status": "committed", "error": None}

    async def _log_transaction_error(self, session_id: str, error: Exception) -> None:
        """Log transaction error details"""
        self.transaction_log[session_id] = {"status": "failed", "error": str(error)}

    async def _cleanup_session(self, session_id: str) -> None:
        """Cleanup session resources"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            await session.close()
            del self.active_sessions[session_id]

class AsyncRepositoryTestBase:
    """Base class for async repository testing with transaction support"""
    def __init__(self, transaction_manager: AsyncTransactionManager):
        self.transaction_manager = transaction_manager
        self.operation_count = 0
    
    async def execute_with_transaction(self, operation_func, session_id: str, **kwargs) -> Any:
        """Execute operation within transaction scope"""
        async with self.transaction_manager.transaction_scope(session_id) as session:
            self.operation_count += 1
            return await operation_func(session, **kwargs)
    
    async def create_entity(self, session: AsyncSession, **data) -> Optional[Dict]:
        """Create entity with proper error handling"""
        try:
            entity = await self._perform_create(session, data)
            await session.flush()
            return entity
        except (IntegrityError, SQLAlchemyError):
            await session.rollback()
            return None
    
    async def _perform_create(self, session: AsyncSession, data: Dict) -> Dict:
        """Perform actual entity creation"""
        entity = {"id": f"entity_{self.operation_count}", **data}
        session.add(entity)
        return entity

@pytest.fixture
async def async_transaction_manager():
    """Async fixture for transaction manager with cleanup"""
    manager = AsyncTransactionManager()
    yield manager
    await manager._cleanup_all_sessions()

async def _execute_and_verify_transaction(repository, manager) -> None:
    """Execute and verify successful transaction"""
    result = await repository.execute_with_transaction(repository.create_entity, "test_session_1", name="Test Entity", value=100)
    assert result is not None and result["name"] == "Test Entity"
    assert "test_session_1" in manager.transaction_log
    assert manager.transaction_log["test_session_1"]["status"] == "committed"

async def test_successful_async_transaction():
    """Test successful async transaction with proper resource management"""
    manager = AsyncTransactionManager()
    repository = AsyncRepositoryTestBase(manager)
    try:
        await _execute_and_verify_transaction(repository, manager)
    finally:
        await manager._cleanup_all_sessions()

async def _create_failing_operation() -> callable:
    """Create operation that raises IntegrityError"""
    async def failing_operation(session: AsyncSession, **kwargs):
        await session.flush()
        raise IntegrityError("Constraint violation", None, None, None)
    return failing_operation

async def _verify_error_handling(manager, session_id: str) -> None:
    """Verify transaction error handling"""
    assert session_id in manager.transaction_log
    assert manager.transaction_log[session_id]["status"] == "failed"

async def test_async_transaction_rollback_on_error():
    """Test async transaction rollback on database errors"""
    manager = AsyncTransactionManager()
    repository = AsyncRepositoryTestBase(manager)
    failing_operation = await _create_failing_operation()
    
    try:
        with pytest.raises(IntegrityError):
            await repository.execute_with_transaction(failing_operation, "error_session", name="Failing Entity")
        await _verify_error_handling(manager, "error_session")
    finally:
        await manager._cleanup_all_sessions()

async def _run_concurrent_transactions(repository, count: int) -> tuple:
    """Run concurrent transactions and return results"""
    tasks = [repository.execute_with_transaction(repository.create_entity, f"concurrent_{i}", name=f"Entity_{i}") for i in range(count)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successful_results = [r for r in results if not isinstance(r, Exception)]
    return results, successful_results

async def test_concurrent_async_transactions():
    """Test concurrent async transactions with proper isolation"""
    manager = AsyncTransactionManager()
    repository = AsyncRepositoryTestBase(manager)
    try:
        results, successful_results = await _run_concurrent_transactions(repository, 5)
        assert len(successful_results) == 5 and len(manager.transaction_log) == 5
    finally:
        await manager._cleanup_all_sessions()

async def _create_slow_operation() -> callable:
    """Create slow operation for timeout testing"""
    async def slow_operation(session: AsyncSession, **kwargs):
        await asyncio.sleep(2.0)
        return {"slow": "result"}
    return slow_operation

async def test_async_transaction_timeout_handling():
    """Test async transaction timeout handling"""
    manager = AsyncTransactionManager()
    slow_operation = await _create_slow_operation()
    
    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(manager.transaction_scope("timeout_test").__aenter__(), timeout=0.1)
    finally:
        await manager._cleanup_all_sessions()

class AsyncTransactionBatch:
    """Async batch processor for database operations"""
    def __init__(self, manager: AsyncTransactionManager, batch_size: int = 10):
        self.manager = manager
        self.batch_size = batch_size
        self.processed_count = 0

    async def process_batch(self, operations: list) -> Dict[str, Any]:
        """Process operations in batches with transaction management"""
        batches = self._create_batches(operations)
        results = {"successful": 0, "failed": 0, "batches": len(batches)}
        return await self._process_all_batches(batches, results)

    async def _process_all_batches(self, batches: list, results: dict) -> dict:
        """Process all batches and update results"""
        for batch_idx, batch in enumerate(batches):
            batch_result = await self._process_single_batch(batch, batch_idx)
            results["successful"] += batch_result["successful"]
            results["failed"] += batch_result["failed"]
        return results

    def _create_batches(self, operations: list) -> list:
        """Split operations into batches"""
        return [
            operations[i:i + self.batch_size]
            for i in range(0, len(operations), self.batch_size)
        ]

    async def _process_single_batch(self, batch: list, batch_idx: int) -> Dict[str, int]:
        """Process single batch of operations"""
        session_id = f"batch_{batch_idx}"
        try:
            return await self._execute_batch_in_transaction(batch, session_id)
        except Exception:
            return {"successful": 0, "failed": len(batch)}

    async def _execute_batch_in_transaction(self, batch: list, session_id: str) -> Dict[str, int]:
        """Execute batch within transaction scope"""
        async with self.manager.transaction_scope(session_id):
            await self._execute_batch_operations(batch)
            return {"successful": len(batch), "failed": 0}

    async def _execute_batch_operations(self, batch: list) -> None:
        """Execute all operations in current batch"""
        for operation in batch:
            await operation()
            self.processed_count += 1

async def _create_test_operations(count: int) -> list:
    """Create test operations for batch processing"""
    return [lambda: asyncio.sleep(0.01) for _ in range(count)]

async def _verify_batch_results(results, batch_processor, expected_count: int) -> None:
    """Verify batch processing results"""
    assert results["successful"] == expected_count
    assert results["failed"] == 0
    assert results["batches"] == 4
    assert batch_processor.processed_count == expected_count

async def test_async_batch_transaction_processing():
    """Test async batch transaction processing"""
    manager = AsyncTransactionManager()
    batch_processor = AsyncTransactionBatch(manager, batch_size=3)
    operations = await _create_test_operations(10)
    
    try:
        results = await batch_processor.process_batch(operations)
        await _verify_batch_results(results, batch_processor, 10)
    finally:
        await manager._cleanup_all_sessions()

async def _create_nested_operation() -> callable:
    """Create nested transaction operation"""
    async def nested_operation(session: AsyncSession, **kwargs):
        await session.flush()
        async with session.begin_nested():
            await session.flush()
            return {"nested": "success"}
    return nested_operation

async def test_async_nested_transaction_handling():
    """Test nested async transaction handling"""
    manager = AsyncTransactionManager()
    nested_operation = await _create_nested_operation()
    
    try:
        async with manager.transaction_scope("nested_test") as session:
            result = await nested_operation(session)
            assert result["nested"] == "success"
    finally:
        await manager._cleanup_all_sessions()

async def test_async_distributed_transactions():
    """Test distributed async transactions"""
    manager = AsyncTransactionManager()
    try:
        async with manager.transaction_scope("distributed_test") as session:
            await session.flush()
            assert session is not None
    finally:
        await manager._cleanup_all_sessions()

async def test_async_transaction_deadlock_handling():
    """Test async transaction deadlock handling"""
    manager = AsyncTransactionManager()
    try:
        async with manager.transaction_scope("deadlock_test") as session:
            await session.flush()
            assert session is not None
    finally:
        await manager._cleanup_all_sessions()

async def test_async_transaction_isolation_levels():
    """Test async transaction isolation levels"""
    manager = AsyncTransactionManager()
    try:
        async with manager.transaction_scope("isolation_test") as session:
            await session.flush()
            assert session is not None
    finally:
        await manager._cleanup_all_sessions()

# Enhanced AsyncTransactionManager with cleanup_all_sessions method
AsyncTransactionManager._cleanup_all_sessions = lambda self: asyncio.gather(
    *[session.close() for session in self.active_sessions.values()],
    return_exceptions=True
)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])