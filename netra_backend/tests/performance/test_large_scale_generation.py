"""
Large Scale Generation Performance Tests

Tests for corpus generation at scale (100k+ records) with resource monitoring.
Focuses on memory efficiency and system resource utilization.
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import patch

import psutil
import pytest

from netra_backend.app.schemas.Generation import (
    ContentCorpusGenParams,
    ContentGenParams,
)

# Add project root to path
from netra_backend.app.services.generation_service import run_content_generation_job

# Add project root to path


@pytest.fixture
def large_corpus_params():
    """Large corpus generation parameters"""
    return ContentCorpusGenParams(
        samples_per_type=100,
        temperature=0.8,
        max_cores=4,
        clickhouse_table='perf_test_corpus'
    )


@pytest.fixture
def resource_monitor():
    """Resource utilization monitor"""
    class ResourceMonitor:
        def __init__(self):
            self.cpu_usage = []
            self.memory_usage = []

        def start_monitoring(self):
            """Start resource monitoring"""
            self.process = psutil.Process()
            self.monitoring = True

        async def collect_metrics(self):
            """Collect system metrics"""
            if not hasattr(self, 'monitoring'):
                return
            
            self.cpu_usage.append(psutil.cpu_percent())
            memory_info = self.process.memory_info()
            self.memory_usage.append(memory_info.rss / 1024 / 1024)
            
        def get_peak_usage(self) -> Dict[str, float]:
            """Get peak resource usage"""
            return {
                'peak_cpu': max(self.cpu_usage) if self.cpu_usage else 0,
                'peak_memory_mb': max(self.memory_usage) if self.memory_usage else 0,
                'avg_cpu': sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0
            }

    return ResourceMonitor()


class TestLargeScaleGeneration:
    """Test large corpus generation (100k+ records)"""
    @pytest.mark.performance
    async def test_large_corpus_generation_100k(self, large_corpus_params, resource_monitor):
        """Test generation of 100k+ records with performance monitoring"""
        resource_monitor.start_monitoring()
        
        with patch('app.services.generation_service.run_generation_in_pool') as mock_pool:
            mock_pool.return_value = self._create_mock_results(100000)
            
            start_time = time.perf_counter()
            job_id = str(uuid.uuid4())
            
            await run_content_generation_job(job_id, large_corpus_params)
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            metrics = resource_monitor.get_peak_usage()
            
            # Performance assertions
            assert duration < 3600  # Should complete within 1 hour
            assert metrics['peak_memory_mb'] < 8192  # Under 8GB RAM
            assert metrics['peak_cpu'] < 95  # Allow CPU headroom

    def _create_mock_results(self, count: int) -> List[Dict[str, Any]]:
        """Create mock generation results"""
        results = []
        workload_types = ['simple_chat', 'complex_analysis', 'code_generation']
        
        for i in range(count):
            result = {
                'type': workload_types[i % len(workload_types)],
                'data': (f'prompt_{i}', f'response_{i}')
            }
            results.append(result)
        return iter(results)
    @pytest.mark.performance  
    async def test_memory_efficient_generation(self):
        """Test memory-efficient generation patterns"""
        memory_samples = []
        process = psutil.Process()
        
        async def monitor_memory():
            """Monitor memory usage during generation"""
            while True:
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)
                await asyncio.sleep(0.5)

        monitor_task = asyncio.create_task(monitor_memory())
        
        perf_params = ContentGenParams(samples_per_type=100, max_cores=4)
        
        with patch('app.services.generation_service.generate_content_for_worker') as mock_gen:
            mock_gen.side_effect = self._simulate_memory_efficient_generation
            
            job_id = str(uuid.uuid4())
            await run_content_generation_job(job_id, perf_params)
            
        monitor_task.cancel()
        
        # Memory should not grow linearly with data
        max_memory = max(memory_samples) if memory_samples else 0
        assert max_memory < 2048  # Under 2GB for efficient generation

    def _simulate_memory_efficient_generation(self, task) -> Dict[str, Any]:
        """Simulate memory-efficient generation"""
        workload_type, config = task
        return {
            'type': workload_type,
            'data': (f'prompt_{workload_type}', f'response_{workload_type}')
        }
    @pytest.mark.performance
    async def test_scalability_patterns(self, large_corpus_params):
        """Test generation scalability patterns"""
        scale_factors = [100, 500, 800, 1000]
        execution_times = []
        
        for scale in scale_factors:
            test_params = ContentGenParams(
                samples_per_type=min(100, scale // 10),
                max_cores=4
            )
            
            with patch('app.services.generation_service.run_generation_in_pool') as mock_pool:
                mock_pool.return_value = iter([
                    {'type': 'test', 'data': ('p', 'r')} 
                    for _ in range(scale)
                ])
                
                start_time = time.perf_counter()
                job_id = str(uuid.uuid4())
                await run_content_generation_job(job_id, test_params)
                duration = time.perf_counter() - start_time
                
                execution_times.append(duration)
        
        # Execution time should scale sub-linearly
        for i in range(1, len(execution_times)):
            time_ratio = execution_times[i] / execution_times[i-1]
            scale_ratio = scale_factors[i] / scale_factors[i-1]
            assert time_ratio < scale_ratio * 1.5  # Allow 50% overhead


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-m", "performance"])