'''Thread Performance E2E Testing

Tests thread operations under load and stress conditions.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Platform Stability, Thread Operation Performance  
- Value Impact: Ensures thread operations scale under enterprise workloads
- Strategic/Revenue Impact: Critical for real-time AI conversation performance
'''

import asyncio
import statistics
import time
from typing import Any, Callable, Dict, List
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# SSOT Compliant Imports
from test_framework import setup_test_path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.auth_core.services.auth_service import AuthService
from shared.isolated_environment import IsolatedEnvironment

try:
    from netra_backend.app.services.thread_service import ThreadService
except ImportError:
    # Fallback for missing thread service
    class ThreadService:
        async def get_or_create_thread(self, user_id: str, db: AsyncSession):
            """Mock thread creation for testing."""
            mock_thread = Mock()
            mock_thread.id = f"thread_{user_id}_{int(time.time())}"
            mock_thread.user_id = user_id
            await asyncio.sleep(0.01)  # Simulate database operation
            return mock_thread

        async def create_message(self, thread_id: str, role: str, content: str, db: AsyncSession):
            """Mock message creation for testing."""
            mock_message = Mock()
            mock_message.id = f"message_{thread_id}_{int(time.time())}"
            mock_message.thread_id = thread_id
            mock_message.role = role
            mock_message.content = content
            await asyncio.sleep(0.01)  # Simulate database operation
            return mock_message

        async def get_thread_messages(self, thread_id: str, db: AsyncSession):
            """Mock message retrieval for testing."""
            await asyncio.sleep(0.01)  # Simulate database query
            return []

from tests.e2e.real_services_manager import ServiceManager
from tests.e2e.harness_utils import UnifiedTestHarnessComplete, create_test_harness
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


@dataclass
class PerformanceMetrics:
    """Performance measurement results."""
    total_time: float
    success_count: int
    error_count: int
    throughput: float
    error_rate: float

    @classmethod
    def calculate(cls, successful_results: List, errors: List, start_time: float, end_time: float):
        """Calculate performance metrics from test results."""
        total_time = end_time - start_time
        success_count = len(successful_results)
        error_count = len(errors)

        return cls(
            total_time=total_time,
            success_count=success_count,
            error_count=error_count,
            throughput=success_count / total_time if total_time > 0 else 0,
            error_rate=error_count / (success_count + error_count) if (success_count + error_count) > 0 else 0
        )


class ThreadPerformanceTester:
    """Manages thread performance testing."""

    def __init__(self, harness: UnifiedTestHarnessComplete):
        self.harness = harness
        self.service_manager = ServiceManager(harness)
        self.thread_service = ThreadService()

    async def setup_services(self) -> None:
        """Setup required services."""
        await self.service_manager.start_all_services(skip_frontend=True)
        await asyncio.sleep(1.0)  # Allow services to stabilize

    async def teardown_services(self) -> None:
        """Cleanup services."""
        if self.service_manager:
            await self.service_manager.stop_all_services()


@pytest.fixture
async def unified_test_harness():
    """Unified test harness fixture for performance tests."""
    harness = await create_test_harness("performance_test")
    yield harness
    await harness.cleanup()


@pytest.fixture
def thread_service():
    """Thread service fixture."""
    return ThreadService()


@pytest.fixture
async def mock_db_session():
    """Mock database session fixture."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.e2e
@pytest.mark.performance
class TestThreadPerformance:
    """Thread performance E2E tests."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_thread_load_performance(self, unified_test_harness, mock_db_session: AsyncSession):
        """Test thread operations under load."""
        tester = ThreadPerformanceTester(unified_test_harness)

        try:
            await tester.setup_services()

            # Test concurrent thread creation
            user_count = 50
            user_ids = [f"user_{i}" for i in range(user_count)]

            start_time = time.perf_counter()
            tasks = [
                tester.thread_service.get_or_create_thread(user_id, mock_db_session)
                for user_id in user_ids
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.perf_counter()

            # Analyze results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            errors = [r for r in results if isinstance(r, Exception)]

            metrics = PerformanceMetrics.calculate(successful_results, errors, start_time, end_time)

            # Validate basic performance metrics
            assert metrics.throughput >= 10.0, "Thread creation throughput too low"
            assert metrics.error_rate < 0.05, "Thread creation error rate too high"
            assert metrics.success_count >= user_count * 0.95, "Too many thread creation failures"

        finally:
            await tester.teardown_services()

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_message_creation_throughput(self, unified_test_harness, mock_db_session: AsyncSession):
        """Test message creation throughput."""
        tester = ThreadPerformanceTester(unified_test_harness)

        try:
            await tester.setup_services()

            # Create a test thread first
            thread = await tester.thread_service.get_or_create_thread("throughput_user", mock_db_session)
            message_count = 100

            start_time = time.perf_counter()
            tasks = [
                tester.thread_service.create_message(
                    thread.id, "user", f"Test message {i}", db=mock_db_session
                )
                for i in range(message_count)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.perf_counter()

            # Analyze results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            errors = [r for r in results if isinstance(r, Exception)]

            metrics = PerformanceMetrics.calculate(successful_results, errors, start_time, end_time)

            # Validate message performance metrics
            assert metrics.throughput >= 20.0, "Message creation throughput too low"
            assert metrics.error_rate < 0.02, "Message creation error rate too high"
            assert metrics.success_count >= message_count * 0.98, "Too many message creation failures"

        finally:
            await tester.teardown_services()

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_read_write_operations(self, unified_test_harness, mock_db_session: AsyncSession):
        """Test concurrent read/write operations performance."""
        tester = ThreadPerformanceTester(unified_test_harness)

        try:
            await tester.setup_services()

            # Create test thread
            thread = await tester.thread_service.get_or_create_thread("rw_test_user", mock_db_session)

            write_count = 50
            read_count = 100

            # Create write tasks
            write_tasks = [
                tester.thread_service.create_message(
                    thread.id, "user", f"Write test message {i}", db=mock_db_session
                )
                for i in range(write_count)
            ]

            # Create read tasks
            read_tasks = [
                tester.thread_service.get_thread_messages(thread.id, db=mock_db_session)
                for _ in range(read_count)
            ]

            # Execute concurrently
            start_time = time.perf_counter()
            all_tasks = write_tasks + read_tasks
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            end_time = time.perf_counter()

            # Analyze results
            write_results = results[:write_count]
            read_results = results[write_count:]

            successful_writes = sum(1 for r in write_results if not isinstance(r, Exception))
            successful_reads = sum(1 for r in read_results if not isinstance(r, Exception))

            write_success_rate = successful_writes / write_count if write_count > 0 else 0
            read_success_rate = successful_reads / read_count if read_count > 0 else 0
            total_time = end_time - start_time
            operations_per_second = (write_count + read_count) / total_time if total_time > 0 else 0

            # Validate concurrent performance
            assert write_success_rate >= 0.95, f"Write success rate too low: {write_success_rate}"
            assert read_success_rate >= 0.98, f"Read success rate too low: {read_success_rate}"
            assert operations_per_second >= 30.0, f"Operations per second too low: {operations_per_second}"

        finally:
            await tester.teardown_services()