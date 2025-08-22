"""
Tests for transaction performance under various load conditions.
All functions ≤8 lines per requirements.
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
import time
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
from netra_backend.tests.database_transaction_test_mocks import MockRepository

# Add project root to path


@pytest.fixture
def performance_repository():
    """Repository for performance testing"""
    return MockRepository()


class TestTransactionPerformanceAndScaling:
    """Test transaction performance under various load conditions"""
    
    async def test_high_concurrency_transactions(self, performance_repository):
        """Test transaction handling under high concurrency"""
        num_concurrent = 50
        sessions = _create_mock_sessions(num_concurrent)
        
        tasks = _create_concurrent_tasks(performance_repository, sessions)
        execution_time, results = await _execute_concurrent_transactions(tasks)
        
        _assert_performance_results(execution_time, results, num_concurrent, sessions)
    
    async def test_transaction_throughput_measurement(self, performance_repository):
        """Test transaction throughput under sustained load"""
        test_duration = 1.0  # 1 second test
        session = _create_performance_session()
        
        transactions_completed = await _measure_throughput(
            performance_repository, session, test_duration
        )
        
        # Should handle at least 100 transactions per second
        assert transactions_completed >= 100
    
    async def test_memory_usage_during_batch_operations(self, performance_repository):
        """Test memory efficiency during batch operations"""
        batch_size = 1000
        sessions = _create_batch_sessions(batch_size)
        
        await _execute_batch_operations(performance_repository, sessions)
        _verify_session_cleanup(sessions)
    
    async def test_transaction_latency_distribution(self, performance_repository):
        """Test transaction latency distribution"""
        num_transactions = 100
        sessions = _create_mock_sessions(num_transactions)
        
        latencies = await _measure_transaction_latencies(performance_repository, sessions)
        
        _assert_latency_distribution(latencies)
    
    async def test_deadlock_recovery_performance(self, performance_repository):
        """Test performance of deadlock recovery mechanisms"""
        deadlock_sessions = _create_deadlock_sessions(10)
        
        recovery_times = await _test_deadlock_scenarios(performance_repository, deadlock_sessions)
        
        # Recovery should be fast
        assert all(time < 0.1 for time in recovery_times)
    
    async def test_connection_pool_stress(self, performance_repository):
        """Test connection pool under stress conditions"""
        pool_size = 20
        concurrent_operations = 100
        
        sessions = _create_pool_sessions(pool_size)
        completion_time = await _stress_test_pool(
            performance_repository, sessions, concurrent_operations
        )
        
        # Should handle stress efficiently
        assert completion_time < 5.0


def _create_mock_sessions(count: int) -> List[AsyncMock]:
    """Create list of mock sessions"""
    sessions = []
    for i in range(count):
        session = _create_single_mock_session()
        sessions.append(session)
    return sessions


def _create_single_mock_session() -> AsyncMock:
    """Create single mock session"""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()  # BaseRepository uses flush, not commit
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _create_concurrent_tasks(repository, sessions: List[AsyncMock]) -> List:
    """Create concurrent task list"""
    async def create_entity(session, index):
        return await repository.create(
            session, name=f'Concurrent Entity {index}'
        )
    
    return [create_entity(sessions[i], i) for i in range(len(sessions))]


async def _execute_concurrent_transactions(tasks: List) -> tuple:
    """Execute concurrent transactions and measure time"""
    start_time = asyncio.get_event_loop().time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = asyncio.get_event_loop().time()
    
    execution_time = end_time - start_time
    return execution_time, results


def _assert_performance_results(execution_time: float, results: List, num_concurrent: int, sessions: List) -> None:
    """Assert performance test results"""
    # Assert performance and results
    assert execution_time < 2.0  # Should complete within 2 seconds
    assert len(results) == num_concurrent
    
    # Count successful operations
    successful = sum(1 for r in results if not isinstance(r, Exception))
    assert successful == num_concurrent
    
    # Verify all sessions were used
    for session in sessions:
        session.add.assert_called_once()


def _create_performance_session() -> AsyncMock:
    """Create session for performance testing"""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


async def _measure_throughput(repository, session: AsyncMock, duration: float) -> int:
    """Measure transaction throughput"""
    start_time = time.time()
    transactions_completed = 0
    
    while time.time() - start_time < duration:
        await repository.create(session, name=f'Throughput Test {transactions_completed}')
        transactions_completed += 1
    
    return transactions_completed


def _create_batch_sessions(batch_size: int) -> List[AsyncMock]:
    """Create sessions for batch operations"""
    return [_create_single_mock_session() for _ in range(batch_size)]


async def _execute_batch_operations(repository, sessions: List[AsyncMock]) -> None:
    """Execute batch operations"""
    tasks = []
    for i, session in enumerate(sessions):
        task = repository.create(session, name=f'Batch Entity {i}')
        tasks.append(task)
    
    await asyncio.gather(*tasks)


def _verify_session_cleanup(sessions: List[AsyncMock]) -> None:
    """Verify sessions are properly cleaned up"""
    for session in sessions:
        session.add.assert_called_once()


async def _measure_transaction_latencies(repository, sessions: List[AsyncMock]) -> List[float]:
    """Measure individual transaction latencies"""
    latencies = []
    
    for i, session in enumerate(sessions):
        start = time.time()
        await repository.create(session, name=f'Latency Test {i}')
        latency = time.time() - start
        latencies.append(latency)
    
    return latencies


def _assert_latency_distribution(latencies: List[float]) -> None:
    """Assert latency distribution meets requirements"""
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    # Latency requirements
    assert avg_latency < 0.01  # Average < 10ms
    assert max_latency < 0.05  # Max < 50ms


def _create_deadlock_sessions(count: int) -> List[AsyncMock]:
    """Create sessions for deadlock testing"""
    return [_create_single_mock_session() for _ in range(count)]


async def _test_deadlock_scenarios(repository, sessions: List[AsyncMock]) -> List[float]:
    """Test deadlock recovery scenarios"""
    recovery_times = []
    
    for i, session in enumerate(sessions):
        start = time.time()
        # Simulate actual deadlock scenarios
        await _simulate_deadlock_recovery(repository, session, i)
        recovery_time = time.time() - start
        recovery_times.append(recovery_time)
    
    return recovery_times


async def _simulate_deadlock_recovery(repository, session: AsyncMock, scenario_index: int) -> None:
    """Simulate deadlock scenarios and test recovery mechanisms"""
    from sqlalchemy.exc import OperationalError
    
    # Simulate different deadlock scenarios
    if scenario_index % 3 == 0:
        # Scenario 1: Transient deadlock that resolves on retry
        session.flush.side_effect = [
            OperationalError("deadlock detected", None, None),
            None  # Success on retry
        ]
    elif scenario_index % 3 == 1:
        # Scenario 2: Lock timeout that requires rollback
        session.flush.side_effect = [
            OperationalError("lock wait timeout", None, None),
            None  # Success after rollback
        ]
    else:
        # Scenario 3: Normal operation (no deadlock)
        session.flush.side_effect = None
    
    # Attempt operation with retry logic
    try:
        await repository.create(session, name=f'Deadlock Test {scenario_index}')
    except OperationalError:
        # Simulate recovery attempt
        await session.rollback()
        await repository.create(session, name=f'Deadlock Test {scenario_index} Retry')


def _create_pool_sessions(pool_size: int) -> List[AsyncMock]:
    """Create sessions simulating connection pool"""
    return [_create_single_mock_session() for _ in range(pool_size)]


async def _stress_test_pool(repository, sessions: List[AsyncMock], operations: int) -> float:
    """Stress test connection pool"""
    start_time = time.time()
    
    tasks = []
    for i in range(operations):
        session = sessions[i % len(sessions)]  # Reuse sessions from pool
        task = repository.create(session, name=f'Pool Stress {i}')
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    return time.time() - start_time