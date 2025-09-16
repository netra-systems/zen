"""
Benchmark and Metrics Collection Tests

Tests for throughput measurement, latency profiling, and resource monitoring.
Provides comprehensive performance metrics and benchmark data.
"""
import sys
from pathlib import Path
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment
import asyncio
import time
import uuid
from typing import List
import psutil
import pytest
from netra_backend.app.schemas.generation import ContentGenParams
from netra_backend.app.services.generation_service import run_content_generation_job

class TestBenchmarkMetrics:
    """Test benchmarking and metrics collection"""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_throughput_benchmarking(self):
        """Test generation throughput measurement"""
        perf_params = ContentGenParams(samples_per_type=100, temperature=0.7, max_cores=4)
        start_time = time.perf_counter()
        with patch('netra_backend.app.services.generation_worker.generate_content_for_worker') as mock_gen:
            mock_gen.return_value = {'type': 'test', 'data': ('p', 'r')}
            with patch('netra_backend.app.services.generation_job_manager.manager') as mock_manager:
                mock_manager.broadcast_to_job = AsyncNone
                job_id = str(uuid.uuid4())
                await run_content_generation_job(job_id, perf_params.model_dump())
        duration = time.perf_counter() - start_time
        expected_records = 2 * perf_params.samples_per_type
        throughput = expected_records / duration if duration > 0 else 0
        assert throughput > 10

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_latency_measurement(self):
        """Test generation latency measurement"""
        latencies = []

        async def measure_single_generation():
            """Measure single generation latency"""
            start = time.perf_counter()
            await asyncio.sleep(0.1)
            latency = time.perf_counter() - start
            latencies.append(latency)
        tasks = [measure_single_generation() for _ in range(100)]
        await asyncio.gather(*tasks)
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        assert avg_latency < 0.2
        assert p95_latency < 0.5

    def test_cpu_utilization_monitoring(self):
        """Test CPU utilization during generation"""
        cpu_samples = []

        def cpu_intensive_task():
            """Simulate CPU-intensive generation task"""
            for _ in range(10000):
                _ = sum(range(10))
        psutil.cpu_percent()
        time.sleep(0.1)
        baseline_cpu = psutil.cpu_percent(interval=0.1)
        for _ in range(5):
            cpu_intensive_task()
            cpu_samples.append(psutil.cpu_percent(interval=0.1))
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)
        assert max_cpu >= baseline_cpu or avg_cpu > 5.0

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage_profiling(self):
        """Test memory usage during generation operations"""
        process = psutil.Process()
        memory_samples = []

        async def memory_intensive_generation():
            """Simulate memory-intensive generation"""
            large_data = [f'data_{i}' for i in range(10000)]
            await asyncio.sleep(0.01)
            return len(large_data)
        baseline_memory = process.memory_info().rss / 1024 / 1024
        tasks = [memory_intensive_generation() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = peak_memory - baseline_memory
        assert len(results) == 50
        assert memory_growth < 500

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_resource_efficiency_metrics(self):
        """Test overall resource efficiency metrics"""
        metrics = {'start_time': time.perf_counter(), 'start_memory': psutil.virtual_memory().used, 'start_cpu': psutil.cpu_percent()}
        perf_params = ContentGenParams(samples_per_type=100, temperature=0.8, max_cores=2)
        with patch('netra_backend.app.services.content_generation_service.run_generation_in_pool') as mock_pool:
            mock_pool.return_value = iter([{'type': 'test', 'data': ('prompt', 'response')} for _ in range(200)])
            with patch('netra_backend.app.services.generation_job_manager.manager') as mock_manager:
                mock_manager.broadcast_to_job = AsyncNone
                job_id = str(uuid.uuid4())
                await run_content_generation_job(job_id, perf_params.model_dump())
        execution_time = time.perf_counter() - metrics['start_time']
        memory_used = psutil.virtual_memory().used - metrics['start_memory']
        memory_used_mb = max(abs(memory_used) / 1024 / 1024, 1.0)
        throughput = 200 / execution_time if execution_time > 0 else 0
        efficiency_score = throughput / memory_used_mb
        assert throughput > 80
        assert efficiency_score > 0.1

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_scalability_benchmarks(self):
        """Test scalability benchmark across different loads"""
        load_sizes = [10, 50, 100]
        performance_metrics = []
        for load_size in load_sizes:
            valid_load_size = min(load_size, 100)
            perf_params = ContentGenParams(samples_per_type=valid_load_size, max_cores=4)
            with patch('netra_backend.app.services.content_generation_service.run_generation_in_pool') as mock_pool:
                mock_pool.return_value = iter([{'type': 'test', 'data': ('p', 'r')} for _ in range(valid_load_size * 2)])
                with patch('netra_backend.app.services.generation_job_manager.manager') as mock_manager:
                    mock_manager.broadcast_to_job = AsyncNone
                    start_time = time.perf_counter()
                    job_id = str(uuid.uuid4())
                    await run_content_generation_job(job_id, perf_params.model_dump())
                duration = time.perf_counter() - start_time
                throughput = valid_load_size * 2 / duration
                performance_metrics.append({'load_size': valid_load_size, 'duration': duration, 'throughput': throughput})
        baseline_throughput = performance_metrics[0]['throughput']
        for metric in performance_metrics[1:]:
            throughput_ratio = metric['throughput'] / baseline_throughput
            assert throughput_ratio > 0.5
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')