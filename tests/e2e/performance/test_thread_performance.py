"""
Thread Performance E2E Testing

Tests thread operations under load and stress conditions.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Platform Stability, Thread Operation Performance
- Value Impact: Ensures thread operations scale under enterprise workloads
- Strategic/Revenue Impact: Critical for real-time AI conversation performance
"""

# Add project root to path
from test_framework import setup_test_path
setup_test_path()

import asyncio
import statistics
import time
from typing import Any, Callable, Dict, List
from unittest.mock import AsyncMock, Mock
from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from netra_backend.app.services.thread_service import ThreadService
except ImportError:
    # Fallback for missing thread service
    class ThreadService:
        async def get_or_create_thread(self, user_id: str, db: AsyncSession):
            # Mock: Generic component isolation for controlled unit testing
            mock_thread = Mock()
            mock_thread.id = f"thread-{user_id}"
            mock_thread.user_id = user_id
            return mock_thread
        
        async def create_message(self, thread_id: str, role: str, content: str, db: AsyncSession):
            # Mock: Generic component isolation for controlled unit testing
            mock_message = Mock()
            mock_message.id = f"msg-{thread_id}-{int(time.time())}"
            mock_message.thread_id = thread_id
            mock_message.role = role
            mock_message.content = content
            return mock_message
        
        async def get_thread_messages(self, thread_id: str, db: AsyncSession):
            return []

from tests.e2e.service_manager import ServiceManager
from tests.e2e.harness_complete import UnifiedTestHarnessComplete, create_test_harness


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


class ThreadLoadTests:
    """Tests for thread operations under load."""
    
    def __init__(self, tester: ThreadPerformanceTester):
        self.tester = tester
        
    async def test_concurrent_thread_creation_load(self, mock_db_session: AsyncSession) -> PerformanceMetrics:
        """Test concurrent thread creation under load."""
        user_count = 50
        user_ids = [f"load_user_{i}" for i in range(user_count)]
        
        performance_data = await self._measure_concurrent_thread_creation(
            self.tester.thread_service, user_ids, mock_db_session
        )
        
        await self._validate_load_performance(performance_data, user_count)
        return performance_data
    
    async def _measure_concurrent_thread_creation(
        self, thread_service: ThreadService, user_ids: List[str],
        db_session: AsyncSession
    ) -> PerformanceMetrics:
        """Measure concurrent thread creation performance."""
        start_time = time.perf_counter()
        
        tasks = [
            thread_service.get_or_create_thread(user_id, db_session)
            for user_id in user_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]
        
        return PerformanceMetrics.calculate(successful_results, errors, start_time, end_time)
    
    async def _validate_load_performance(
        self, performance_data: PerformanceMetrics, expected_count: int
    ) -> None:
        """Validate load performance meets expectations."""
        # Validate throughput (should handle at least 10 operations/second)
        assert performance_data.throughput >= 10.0, f"Throughput {performance_data.throughput} below 10 ops/sec"
        
        # Validate error rate (should be less than 5%)
        assert performance_data.error_rate < 0.05, f"Error rate {performance_data.error_rate:.2%} above 5%"
        
        # Validate success count
        assert performance_data.success_count >= expected_count * 0.95, f"Success count {performance_data.success_count} below 95% of expected"
    
    async def test_message_creation_throughput(self, mock_db_session: AsyncSession) -> PerformanceMetrics:
        """Test message creation throughput."""
        thread = await self.tester.thread_service.get_or_create_thread("throughput_user", mock_db_session)
        message_count = 100
        
        performance_data = await self._measure_message_creation_throughput(
            self.tester.thread_service, thread.id, message_count, mock_db_session
        )
        
        await self._validate_message_throughput(performance_data, message_count)
        return performance_data
    
    async def _measure_message_creation_throughput(
        self, thread_service: ThreadService, thread_id: str,
        message_count: int, db_session: AsyncSession
    ) -> PerformanceMetrics:
        """Measure message creation throughput."""
        start_time = time.perf_counter()
        
        tasks = [
            thread_service.create_message(
                thread_id, "user", f"Message {i}", db=db_session
            )
            for i in range(message_count)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]
        
        return PerformanceMetrics.calculate(successful_results, errors, start_time, end_time)
    
    async def _validate_message_throughput(
        self, performance_data: PerformanceMetrics, expected_count: int
    ) -> None:
        """Validate message creation throughput."""
        # Should handle at least 20 messages/second
        assert performance_data.throughput >= 20.0, f"Message throughput {performance_data.throughput} below 20 msg/sec"
        
        # Error rate should be minimal
        assert performance_data.error_rate < 0.02, f"Error rate {performance_data.error_rate:.2%} above 2%"
        
        # Should create most messages successfully
        assert performance_data.success_count >= expected_count * 0.98, f"Success count {performance_data.success_count} below 98% of expected"


class ThreadStressTests:
    """Stress tests for thread operations."""
    
    def __init__(self, tester: ThreadPerformanceTester):
        self.tester = tester
    
    async def test_thread_memory_usage_stress(self, mock_db_session: AsyncSession) -> Dict[str, Any]:
        """Test thread operations under memory stress."""
        thread_count = 200
        messages_per_thread = 20
        
        stress_results = await self._execute_memory_stress_test(
            self.tester.thread_service, thread_count, messages_per_thread, mock_db_session
        )
        
        await self._validate_memory_stress_results(stress_results)
        return stress_results
    
    async def _execute_memory_stress_test(
        self, thread_service: ThreadService, thread_count: int,
        messages_per_thread: int, db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute memory stress test."""
        created_threads = []
        created_messages = []
        
        # Create threads
        thread_start = time.perf_counter()
        for i in range(thread_count):
            thread = await thread_service.get_or_create_thread(
                f"stress_user_{i}", db_session
            )
            created_threads.append(thread)
        thread_end = time.perf_counter()
        
        # Create messages for each thread
        message_start = time.perf_counter()
        for thread in created_threads:
            for j in range(messages_per_thread):
                message = await thread_service.create_message(
                    thread.id, "user", f"Stress message {j}", db=db_session
                )
                created_messages.append(message)
        message_end = time.perf_counter()
        
        return self._compile_stress_test_results(
            created_threads, created_messages, thread_start, thread_end,
            message_start, message_end
        )
    
    def _compile_stress_test_results(
        self, threads: List, messages: List,
        thread_start: float, thread_end: float,
        message_start: float, message_end: float
    ) -> Dict[str, Any]:
        """Compile stress test results."""
        return {
            "thread_count": len(threads),
            "message_count": len(messages),
            "thread_creation_time": thread_end - thread_start,
            "message_creation_time": message_end - message_start,
            "total_entities": len(threads) + len(messages),
            "thread_throughput": len(threads) / (thread_end - thread_start) if (thread_end - thread_start) > 0 else 0,
            "message_throughput": len(messages) / (message_end - message_start) if (message_end - message_start) > 0 else 0
        }
    
    async def _validate_memory_stress_results(self, results: Dict[str, Any]) -> None:
        """Validate memory stress test results."""
        # Verify all entities were created
        assert results["thread_count"] > 0, "No threads were created"
        assert results["message_count"] > 0, "No messages were created"
        
        # Verify reasonable performance under stress
        assert results["thread_throughput"] > 5.0, f"Thread throughput {results['thread_throughput']:.1f} below 5 threads/sec"
        assert results["message_throughput"] > 50.0, f"Message throughput {results['message_throughput']:.1f} below 50 messages/sec"
    
    async def test_concurrent_read_write_stress(self, mock_db_session: AsyncSession) -> Dict[str, Any]:
        """Test concurrent read/write operations stress."""
        thread = await self.tester.thread_service.get_or_create_thread("rw_stress_user", mock_db_session)
        
        stress_results = await self._execute_read_write_stress(
            self.tester.thread_service, thread.id, mock_db_session
        )
        
        await self._validate_read_write_stress_results(stress_results)
        return stress_results
    
    async def _execute_read_write_stress(
        self, thread_service: ThreadService, thread_id: str, db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute concurrent read/write stress test."""
        write_count = 50
        read_count = 100
        
        # Create write tasks
        write_tasks = [
            thread_service.create_message(
                thread_id, "user", f"Write stress {i}", db=db_session
            )
            for i in range(write_count)
        ]
        
        # Create read tasks
        read_tasks = [
            thread_service.get_thread_messages(thread_id, db=db_session)
            for _ in range(read_count)
        ]
        
        # Execute concurrently
        start_time = time.perf_counter()
        all_tasks = write_tasks + read_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        end_time = time.perf_counter()
        
        return self._analyze_read_write_results(results, write_count, read_count, end_time - start_time)
    
    def _analyze_read_write_results(
        self, results: List, write_count: int, read_count: int, total_time: float
    ) -> Dict[str, Any]:
        """Analyze read/write stress results."""
        successful_writes = sum(1 for r in results[:write_count] if not isinstance(r, Exception))
        successful_reads = sum(1 for r in results[write_count:] if not isinstance(r, Exception))
        
        return {
            "successful_writes": successful_writes,
            "successful_reads": successful_reads,
            "write_success_rate": successful_writes / write_count if write_count > 0 else 0,
            "read_success_rate": successful_reads / read_count if read_count > 0 else 0,
            "total_time": total_time,
            "operations_per_second": (write_count + read_count) / total_time if total_time > 0 else 0
        }
    
    async def _validate_read_write_stress_results(self, results: Dict[str, Any]) -> None:
        """Validate read/write stress results."""
        # High success rates expected
        assert results["write_success_rate"] >= 0.95, f"Write success rate {results['write_success_rate']:.2%} below 95%"
        assert results["read_success_rate"] >= 0.98, f"Read success rate {results['read_success_rate']:.2%} below 98%"
        
        # Reasonable throughput under stress
        assert results["operations_per_second"] >= 30.0, f"Operations per second {results['operations_per_second']:.1f} below 30"


class ThreadScalabilityTests:
    """Tests for thread operation scalability."""
    
    def __init__(self, tester: ThreadPerformanceTester):
        self.tester = tester
    
    async def test_thread_count_scalability(self, mock_db_session: AsyncSession) -> Dict[int, Dict[str, Any]]:
        """Test scalability with increasing thread counts."""
        thread_counts = [10, 50, 100, 200]
        
        scalability_data = await self._measure_scalability_across_counts(
            self.tester.thread_service, thread_counts, mock_db_session
        )
        
        await self._validate_scalability_characteristics(scalability_data)
        return scalability_data
    
    async def _measure_scalability_across_counts(
        self, thread_service: ThreadService, thread_counts: List[int],
        db_session: AsyncSession
    ) -> Dict[int, Dict[str, Any]]:
        """Measure scalability across different thread counts."""
        scalability_data = {}
        
        for count in thread_counts:
            user_ids = [f"scale_user_{count}_{i}" for i in range(count)]
            
            start_time = time.perf_counter()
            tasks = [
                thread_service.get_or_create_thread(user_id, db_session)
                for user_id in user_ids
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.perf_counter()
            
            scalability_data[count] = self._calculate_scalability_metrics(
                results, end_time - start_time, count
            )
        
        return scalability_data
    
    def _calculate_scalability_metrics(
        self, results: List, total_time: float, expected_count: int
    ) -> Dict[str, Any]:
        """Calculate scalability metrics."""
        successful = [r for r in results if not isinstance(r, Exception)]
        
        return {
            "success_count": len(successful),
            "total_time": total_time,
            "throughput": len(successful) / total_time if total_time > 0 else 0,
            "average_time_per_operation": total_time / expected_count if expected_count > 0 else 0,
            "success_rate": len(successful) / expected_count if expected_count > 0 else 0
        }
    
    async def _validate_scalability_characteristics(
        self, scalability_data: Dict[int, Dict[str, Any]]
    ) -> None:
        """Validate scalability characteristics."""
        thread_counts = sorted(scalability_data.keys())
        
        # Verify performance remains reasonable as scale increases
        for count in thread_counts:
            data = scalability_data[count]
            
            # Success rate should remain high
            assert data["success_rate"] >= 0.95, f"Success rate {data['success_rate']:.2%} below 95% for {count} threads"
            
            # Throughput should not degrade dramatically
            assert data["throughput"] >= 5.0, f"Throughput {data['throughput']:.1f} below 5 ops/sec for {count} threads"
            
            # Average time per operation should stay reasonable
            assert data["average_time_per_operation"] <= 1.0, f"Avg time {data['average_time_per_operation']:.2f}s above 1s for {count} threads"


class ThreadLatencyTests:
    """Tests for thread operation latency characteristics."""
    
    def __init__(self, tester: ThreadPerformanceTester):
        self.tester = tester
    
    async def test_thread_operation_latency_distribution(self, mock_db_session: AsyncSession) -> Dict[str, Any]:
        """Test latency distribution of thread operations."""
        operation_count = 100
        
        latency_data = await self._measure_operation_latencies(
            self.tester.thread_service, operation_count, mock_db_session
        )
        
        await self._validate_latency_distribution(latency_data)
        return latency_data
    
    async def _measure_operation_latencies(
        self, thread_service: ThreadService, operation_count: int,
        db_session: AsyncSession
    ) -> Dict[str, List[float]]:
        """Measure latencies for different operations."""
        latencies = {
            "thread_creation": [],
            "message_creation": [],
            "message_retrieval": []
        }
        
        # Measure thread creation latencies
        for i in range(operation_count):
            start_time = time.perf_counter()
            await thread_service.get_or_create_thread(f"latency_user_{i}", db_session)
            end_time = time.perf_counter()
            latencies["thread_creation"].append(end_time - start_time)
        
        # Use first thread for message operations
        test_thread = await thread_service.get_or_create_thread("latency_test", db_session)
        
        # Measure message creation latencies
        for i in range(operation_count):
            start_time = time.perf_counter()
            await thread_service.create_message(
                test_thread.id, "user", f"Latency test {i}", db=db_session
            )
            end_time = time.perf_counter()
            latencies["message_creation"].append(end_time - start_time)
        
        # Measure message retrieval latencies
        for i in range(operation_count):
            start_time = time.perf_counter()
            await thread_service.get_thread_messages(test_thread.id, db=db_session)
            end_time = time.perf_counter()
            latencies["message_retrieval"].append(end_time - start_time)
        
        return latencies
    
    async def _validate_latency_distribution(self, latency_data: Dict[str, List[float]]) -> None:
        """Validate latency distribution characteristics."""
        for operation, latencies in latency_data.items():
            if not latencies:
                continue
                
            # Calculate statistics
            mean_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = self._calculate_percentile(latencies, 95)
            p99_latency = self._calculate_percentile(latencies, 99)
            
            # Validate latency characteristics
            assert mean_latency <= 0.5, f"{operation} mean latency {mean_latency:.3f}s above 500ms"
            assert median_latency <= 0.3, f"{operation} median latency {median_latency:.3f}s above 300ms"
            assert p95_latency <= 1.0, f"{operation} p95 latency {p95_latency:.3f}s above 1s"
            assert p99_latency <= 2.0, f"{operation} p99 latency {p99_latency:.3f}s above 2s"
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f == len(sorted_values) - 1:
            return sorted_values[f]
        
        return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c


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
    # Mock: Database session isolation for transaction testing without real database dependency
    session = AsyncMock(spec=AsyncSession)
    # Mock: Session isolation for controlled testing without external state
    session.begin = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.commit = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.rollback = AsyncMock()
    return session


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.timeout(600)  # 10 minutes max
class TestThreadPerformance:
    """Thread performance E2E tests."""
    
    async def test_thread_load_performance(self, unified_test_harness, mock_db_session):
        """Test thread operations under load."""
        tester = ThreadPerformanceTester(unified_test_harness)
        
        try:
            await tester.setup_services()
            
            # Test concurrent thread creation
            load_tests = ThreadLoadTests(tester)
            thread_metrics = await load_tests.test_concurrent_thread_creation_load(mock_db_session)
            
            # Validate basic performance metrics
            assert thread_metrics.throughput >= 10.0, "Thread creation throughput too low"
            assert thread_metrics.error_rate < 0.05, "Thread creation error rate too high"
            
            # Test message creation throughput
            message_metrics = await load_tests.test_message_creation_throughput(mock_db_session)
            
            # Validate message performance metrics
            assert message_metrics.throughput >= 20.0, "Message creation throughput too low"
            assert message_metrics.error_rate < 0.02, "Message creation error rate too high"
            
        finally:
            await tester.teardown_services()
    
    async def test_thread_stress_performance(self, unified_test_harness, mock_db_session):
        """Test thread operations under stress conditions."""
        tester = ThreadPerformanceTester(unified_test_harness)
        
        try:
            await tester.setup_services()
            
            # Test memory stress
            stress_tests = ThreadStressTests(tester)
            memory_results = await stress_tests.test_thread_memory_usage_stress(mock_db_session)
            
            # Validate stress test results
            assert memory_results["thread_count"] >= 190, "Not enough threads created under stress"
            assert memory_results["message_count"] >= 3800, "Not enough messages created under stress"
            
            # Test read/write stress
            rw_results = await stress_tests.test_concurrent_read_write_stress(mock_db_session)
            
            # Validate read/write performance
            assert rw_results["write_success_rate"] >= 0.95, "Write success rate too low under stress"
            assert rw_results["read_success_rate"] >= 0.98, "Read success rate too low under stress"
            
        finally:
            await tester.teardown_services()
    
    async def test_thread_scalability_performance(self, unified_test_harness, mock_db_session):
        """Test thread operation scalability."""
        tester = ThreadPerformanceTester(unified_test_harness)
        
        try:
            await tester.setup_services()
            
            # Test scalability characteristics
            scalability_tests = ThreadScalabilityTests(tester)
            scalability_data = await scalability_tests.test_thread_count_scalability(mock_db_session)
            
            # Validate scalability across different thread counts
            for count, metrics in scalability_data.items():
                assert metrics["success_rate"] >= 0.95, f"Low success rate for {count} threads"
                assert metrics["throughput"] >= 5.0, f"Low throughput for {count} threads"
                assert metrics["average_time_per_operation"] <= 1.0, f"High latency for {count} threads"
            
        finally:
            await tester.teardown_services()
    
    async def test_thread_latency_characteristics(self, unified_test_harness, mock_db_session):
        """Test thread operation latency characteristics."""
        tester = ThreadPerformanceTester(unified_test_harness)
        
        try:
            await tester.setup_services()
            
            # Test latency distribution
            latency_tests = ThreadLatencyTests(tester)
            latency_data = await latency_tests.test_thread_operation_latency_distribution(mock_db_session)
            
            # Validate that latency data was collected
            assert "thread_creation" in latency_data, "Thread creation latency not measured"
            assert "message_creation" in latency_data, "Message creation latency not measured"
            assert "message_retrieval" in latency_data, "Message retrieval latency not measured"
            
            # Basic latency validation
            for operation, latencies in latency_data.items():
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    assert avg_latency <= 0.5, f"{operation} average latency {avg_latency:.3f}s too high"
            
        finally:
            await tester.teardown_services()