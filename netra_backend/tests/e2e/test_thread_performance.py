"""Thread Performance E2E Testing
Tests thread operations under load and stress conditions.
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any, Callable
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.thread_service import ThreadService
from netra_backend.tests.e2e.thread_test_fixtures import ThreadPerformanceTestUtils


class ThreadLoadTests:
    """Tests for thread operations under load."""
    async def test_concurrent_thread_creation_load(
        self, thread_service: ThreadService, mock_db_session: AsyncSession
    ):
        """Test concurrent thread creation under load."""
        user_count = 50
        user_ids = [f"load_user_{i}" for i in range(user_count)]
        
        performance_data = await self._measure_concurrent_thread_creation(
            thread_service, user_ids, mock_db_session
        )
        
        await self._validate_load_performance(performance_data, user_count)
    
    async def _measure_concurrent_thread_creation(
        self, thread_service: ThreadService, user_ids: List[str],
        db_session: AsyncSession
    ) -> Dict[str, Any]:
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
        
        return self._calculate_performance_metrics(
            successful_results, errors, start_time, end_time
        )
    
    def _calculate_performance_metrics(
        self, successful_results: List, errors: List,
        start_time: float, end_time: float
    ) -> Dict[str, Any]:
        """Calculate performance metrics."""
        total_time = end_time - start_time
        success_count = len(successful_results)
        error_count = len(errors)
        
        return {
            "total_time": total_time,
            "success_count": success_count,
            "error_count": error_count,
            "throughput": success_count / total_time if total_time > 0 else 0,
            "error_rate": error_count / (success_count + error_count) if (success_count + error_count) > 0 else 0
        }
    
    async def _validate_load_performance(
        self, performance_data: Dict[str, Any], expected_count: int
    ) -> None:
        """Validate load performance meets expectations."""
        # Validate throughput (should handle at least 10 operations/second)
        assert performance_data["throughput"] >= 10.0
        
        # Validate error rate (should be less than 5%)
        assert performance_data["error_rate"] < 0.05
        
        # Validate success count
        assert performance_data["success_count"] >= expected_count * 0.95
    async def test_message_creation_throughput(
        self, thread_service: ThreadService, mock_db_session: AsyncSession
    ):
        """Test message creation throughput."""
        thread = await thread_service.get_or_create_thread("throughput_user", mock_db_session)
        message_count = 100
        
        performance_data = await self._measure_message_creation_throughput(
            thread_service, thread.id, message_count, mock_db_session
        )
        
        await self._validate_message_throughput(performance_data, message_count)
    
    async def _measure_message_creation_throughput(
        self, thread_service: ThreadService, thread_id: str,
        message_count: int, db_session: AsyncSession
    ) -> Dict[str, Any]:
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
        
        return self._calculate_performance_metrics(
            successful_results, errors, start_time, end_time
        )
    
    async def _validate_message_throughput(
        self, performance_data: Dict[str, Any], expected_count: int
    ) -> None:
        """Validate message creation throughput."""
        # Should handle at least 20 messages/second
        assert performance_data["throughput"] >= 20.0
        
        # Error rate should be minimal
        assert performance_data["error_rate"] < 0.02
        
        # Should create most messages successfully
        assert performance_data["success_count"] >= expected_count * 0.98


class ThreadStressTests:
    """Stress tests for thread operations."""
    async def test_thread_memory_usage_stress(
        self, thread_service: ThreadService, mock_db_session: AsyncSession
    ):
        """Test thread operations under memory stress."""
        thread_count = 200
        messages_per_thread = 20
        
        stress_results = await self._execute_memory_stress_test(
            thread_service, thread_count, messages_per_thread, mock_db_session
        )
        
        await self._validate_memory_stress_results(stress_results)
    
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
            "thread_throughput": len(threads) / (thread_end - thread_start),
            "message_throughput": len(messages) / (message_end - message_start)
        }
    
    async def _validate_memory_stress_results(self, results: Dict[str, Any]) -> None:
        """Validate memory stress test results."""
        # Verify all entities were created
        assert results["thread_count"] > 0
        assert results["message_count"] > 0
        
        # Verify reasonable performance under stress
        assert results["thread_throughput"] > 5.0  # At least 5 threads/second
        assert results["message_throughput"] > 50.0  # At least 50 messages/second
    async def test_concurrent_read_write_stress(
        self, thread_service: ThreadService, mock_db_session: AsyncSession
    ):
        """Test concurrent read/write operations stress."""
        thread = await thread_service.get_or_create_thread("rw_stress_user", mock_db_session)
        
        stress_results = await self._execute_read_write_stress(
            thread_service, thread.id, mock_db_session
        )
        
        await self._validate_read_write_stress_results(stress_results)
    
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
            "write_success_rate": successful_writes / write_count,
            "read_success_rate": successful_reads / read_count,
            "total_time": total_time,
            "operations_per_second": (write_count + read_count) / total_time
        }
    
    async def _validate_read_write_stress_results(self, results: Dict[str, Any]) -> None:
        """Validate read/write stress results."""
        # High success rates expected
        assert results["write_success_rate"] >= 0.95
        assert results["read_success_rate"] >= 0.98
        
        # Reasonable throughput under stress
        assert results["operations_per_second"] >= 30.0


class ThreadScalabilityTests:
    """Tests for thread operation scalability."""
    async def test_thread_count_scalability(
        self, thread_service: ThreadService, mock_db_session: AsyncSession
    ):
        """Test scalability with increasing thread counts."""
        thread_counts = [10, 50, 100, 200]
        
        scalability_data = await self._measure_scalability_across_counts(
            thread_service, thread_counts, mock_db_session
        )
        
        await self._validate_scalability_characteristics(scalability_data)
    
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
            assert data["success_rate"] >= 0.95
            
            # Throughput should not degrade dramatically
            assert data["throughput"] >= 5.0  # Minimum acceptable throughput
            
            # Average time per operation should stay reasonable
            assert data["average_time_per_operation"] <= 1.0  # Max 1 second per operation


class ThreadLatencyTests:
    """Tests for thread operation latency characteristics."""
    async def test_thread_operation_latency_distribution(
        self, thread_service: ThreadService, mock_db_session: AsyncSession
    ):
        """Test latency distribution of thread operations."""
        operation_count = 100
        
        latency_data = await self._measure_operation_latencies(
            thread_service, operation_count, mock_db_session
        )
        
        await self._validate_latency_distribution(latency_data)
    
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
            # Calculate statistics
            mean_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = self._calculate_percentile(latencies, 95)
            p99_latency = self._calculate_percentile(latencies, 99)
            
            # Validate latency characteristics
            assert mean_latency <= 0.5  # Mean should be under 500ms
            assert median_latency <= 0.3  # Median should be under 300ms
            assert p95_latency <= 1.0  # 95th percentile under 1 second
            assert p99_latency <= 2.0  # 99th percentile under 2 seconds
    
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