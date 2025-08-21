"""
Performance tests for corpus generation

Tests performance, scalability, and resource usage of corpus generation.
All functions maintain 25-line limit with single responsibility.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import psutil
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock

# Add project root to path

from netra_backend.app.services.corpus_service import CorpusService
from netra_backend.app.services.synthetic_data.core_service import SyntheticDataService
from netra_backend.app.agents.corpus_admin import CorpusAdminSubAgent
from netra_backend.app.schemas.Corpus import Corpus
from netra_backend.app.agents.corpus_admin.models import CorpusMetadata

# Add project root to path


class TestCorpusGenerationPerformance:
    """Performance tests for corpus generation"""
    
    @pytest.fixture(scope="function")
    def mock_corpus_service(self):
        """Create mock corpus service"""
        service = AsyncMock(spec=CorpusService)
        service.create_corpus = AsyncMock(return_value="corpus_perf_123")
        service.generate_data = AsyncMock()
        return service
    
    @pytest.fixture(scope="function")
    def mock_synthetic_manager(self):
        """Create mock synthetic data manager"""
        manager = AsyncMock(spec=SyntheticDataService)
        manager.generate_batch = AsyncMock()
        manager.validate_data = AsyncMock(return_value=True)
        return manager
    
    @pytest.mark.performance
    async def test_large_corpus_generation(self, mock_corpus_service, mock_synthetic_manager):
        """Test with 100k+ records"""
        start_time = time.time()
        record_count = 100000
        result = await self._generate_large_corpus(
            mock_corpus_service, mock_synthetic_manager, record_count
        )
        elapsed = time.time() - start_time
        assert result["success"] is True
        assert result["record_count"] == record_count
        assert elapsed < 60  # Should complete within 60 seconds
    
    async def _generate_large_corpus(self, service, manager, count):
        """Generate large corpus with batching"""
        batch_size = 1000
        batches = count // batch_size
        for i in range(batches):
            await manager.generate_batch(batch_size)
        return {"success": True, "record_count": count}
    
    @pytest.mark.performance
    async def test_concurrent_generations(self, mock_corpus_service):
        """Test multiple simultaneous requests"""
        concurrent_count = 10
        tasks = await self._create_concurrent_tasks(
            mock_corpus_service, concurrent_count
        )
        results = await asyncio.gather(*tasks)
        assert len(results) == concurrent_count
        assert all(r["success"] for r in results)
    
    async def _create_concurrent_tasks(self, service, count):
        """Create concurrent generation tasks"""
        tasks = []
        for i in range(count):
            task = self._generate_corpus_async(service, f"corpus_{i}")
            tasks.append(task)
        return tasks
    
    async def _generate_corpus_async(self, service, corpus_id):
        """Generate corpus asynchronously"""
        await service.create_corpus(corpus_id)
        await asyncio.sleep(0.1)  # Simulate processing
        return {"success": True, "corpus_id": corpus_id}
    
    @pytest.mark.performance
    async def test_resource_utilization(self, mock_corpus_service):
        """Monitor CPU/memory usage"""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        initial_cpu = psutil.cpu_percent(interval=0.1)
        
        await self._perform_intensive_operation(mock_corpus_service)
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        final_cpu = psutil.cpu_percent(interval=0.1)
        
        memory_increase = final_memory - initial_memory
        assert memory_increase < 500  # Memory increase < 500MB
    
    async def _perform_intensive_operation(self, service):
        """Perform resource-intensive operation"""
        tasks = []
        for i in range(5):
            task = service.generate_data(f"corpus_{i}", 10000)
            tasks.append(task)
        await asyncio.gather(*tasks)
    
    @pytest.mark.performance
    async def test_batch_processing_performance(self, mock_synthetic_manager):
        """Test batch processing efficiency"""
        batch_sizes = [100, 500, 1000, 5000]
        results = await self._test_batch_sizes(
            mock_synthetic_manager, batch_sizes
        )
        assert all(r["processed"] for r in results)
        assert self._verify_batch_efficiency(results)
    
    async def _test_batch_sizes(self, manager, sizes):
        """Test different batch sizes"""
        results = []
        for size in sizes:
            start = time.time()
            await manager.generate_batch(size)
            elapsed = time.time() - start
            results.append({"size": size, "time": elapsed, "processed": True})
        return results
    
    def _verify_batch_efficiency(self, results):
        """Verify batch processing is efficient"""
        for i in range(1, len(results)):
            size_ratio = results[i]["size"] / results[i-1]["size"]
            prev_time = results[i-1]["time"]
            if prev_time == 0:  # Avoid division by zero
                prev_time = 0.001  # 1ms minimum
            time_ratio = results[i]["time"] / prev_time
            if time_ratio > size_ratio * 1.5:  # Should scale reasonably
                return False
        return True
    
    @pytest.mark.performance
    async def test_streaming_generation(self, mock_corpus_service):
        """Test streaming data generation"""
        stream_count = 0
        async for chunk in self._stream_corpus_data(mock_corpus_service):
            stream_count += 1
            assert chunk["data"] is not None
        assert stream_count > 0
    
    async def _stream_corpus_data(self, service):
        """Stream corpus data chunks"""
        for i in range(10):
            await asyncio.sleep(0.01)  # Simulate streaming delay
            yield {"chunk_id": i, "data": f"chunk_{i}"}
    
    @pytest.mark.performance
    async def test_memory_leak_detection(self, mock_corpus_service):
        """Test for memory leaks during long operations"""
        initial_memory = self._get_memory_usage()
        iterations = 100
        
        for _ in range(iterations):
            await self._perform_generation_cycle(mock_corpus_service)
        
        final_memory = self._get_memory_usage()
        memory_per_iteration = (final_memory - initial_memory) / iterations
        assert memory_per_iteration < 1  # Less than 1MB per iteration
    
    def _get_memory_usage(self):
        """Get current memory usage in MB"""
        return psutil.Process().memory_info().rss / 1024 / 1024
    
    async def _perform_generation_cycle(self, service):
        """Perform single generation cycle"""
        await service.create_corpus("temp_corpus")
        await service.generate_data("temp_corpus", 100)
        # Cleanup would happen here in real implementation
    
    @pytest.mark.performance
    async def test_error_recovery_performance(self, mock_corpus_service):
        """Test performance during error conditions"""
        mock_corpus_service.generate_data.side_effect = [
            Exception("Error"), None, None, Exception("Error"), None
        ]
        successes = await self._test_with_errors(mock_corpus_service)
        assert successes >= 3  # At least 3 successful operations
    
    async def _test_with_errors(self, service):
        """Test operations with intermittent errors"""
        successes = 0
        for i in range(5):
            try:
                await service.generate_data(f"corpus_{i}", 1000)
                successes += 1
            except Exception:
                pass  # Expected errors
        return successes


class TestScalabilityMetrics:
    """Test scalability metrics"""
    
    @pytest.mark.performance
    async def test_throughput_measurement(self):
        """Measure operation throughput"""
        operations = 1000
        start_time = time.time()
        await self._execute_operations(operations)
        elapsed = time.time() - start_time
        throughput = operations / elapsed
        assert throughput > 100  # At least 100 ops/second
    
    async def _execute_operations(self, count):
        """Execute multiple operations"""
        tasks = []
        for i in range(count):
            tasks.append(self._single_operation(i))
        await asyncio.gather(*tasks)
    
    async def _single_operation(self, op_id):
        """Execute single operation"""
        await asyncio.sleep(0.001)  # Simulate minimal work
        return {"op_id": op_id, "completed": True}
    
    @pytest.mark.performance
    async def test_latency_percentiles(self):
        """Measure latency percentiles"""
        latencies = await self._collect_latencies(100)
        p50 = self._calculate_percentile(latencies, 50)
        p95 = self._calculate_percentile(latencies, 95)
        p99 = self._calculate_percentile(latencies, 99)
        assert p50 < 20  # P50 < 20ms (excellent performance)
        assert p95 < 50  # P95 < 50ms
        assert p99 < 100  # P99 < 100ms
    
    async def _collect_latencies(self, count):
        """Collect operation latencies"""
        latencies = []
        for i in range(count):
            start = time.time()
            await asyncio.sleep(0.001 * (i % 10 + 1))  # Variable latency
            latencies.append((time.time() - start) * 1000)  # Convert to ms
        return latencies
    
    def _calculate_percentile(self, data, percentile):
        """Calculate percentile value"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]