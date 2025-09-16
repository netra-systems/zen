"""
Workload Metric Generator
Generates realistic workload metric data for testing
"""

import random
from datetime import datetime, timedelta
from typing import List, Optional

from netra_backend.tests.clickhouse.data_models import WorkloadMetric
from netra_backend.tests.clickhouse.generator_base import DataGeneratorBase

class WorkloadMetricGenerator(DataGeneratorBase):
    """Generate realistic workload metrics"""
    
    def _generate_correlated_metrics(self) -> tuple[float, float, float, float]:
        """Generate correlated performance metrics"""
        gpu_util = random.uniform(0, 100)
        memory_usage = 2048 + gpu_util * 50 + random.uniform(-500, 500)
        throughput = gpu_util * 10 + random.uniform(0, 50)
        latency = 100 / max(1, throughput) * 1000  # Inverse relationship
        return gpu_util, memory_usage, throughput, latency
    
    def _apply_metric_anomalies(self, gpu_util: float, memory_usage: float, 
                              latency: float) -> tuple[float, float, float]:
        """Apply realistic anomalies to metrics"""
        if random.random() < 0.05:  # 5% anomaly rate
            if random.random() < 0.5:
                gpu_util = random.uniform(95, 100)  # High GPU
                memory_usage = random.uniform(7500, 8192)  # High memory
            else:
                latency = random.uniform(5000, 10000)  # High latency spike
        return gpu_util, memory_usage, latency
    
    def _create_workload_metric(self, timestamp: datetime, workload_id: str,
                              gpu_util: float, memory_usage: float, 
                              throughput: float, latency: float) -> WorkloadMetric:
        """Create a single workload metric"""
        return WorkloadMetric(
            timestamp=timestamp,
            user_id=random.randint(1, 100),
            workload_id=workload_id,
            metrics={
                "name": ["gpu_utilization", "memory_usage", "throughput", "latency_ms", "cost_cents"],
                "value": [gpu_util, memory_usage, throughput, latency, throughput * 0.01],
                "unit": ["percent", "MB", "req/s", "ms", "cents"]
            },
            metadata={
                "node_id": f"node_{random.randint(1, 10)}",
                "cluster": random.choice(["prod-us-east", "prod-us-west", "prod-eu"]),
                "version": random.choice(["1.0.0", "1.1.0", "1.2.0"])
            }
        )
    
    def generate_workload_metrics(self, count: int, start_time: Optional[datetime] = None,
                                 interval_seconds: int = 60) -> List[WorkloadMetric]:
        """Generate realistic workload metrics with nested arrays"""
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        
        metrics = []
        workload_ids = [f"wl_{random.randint(1000, 9999)}" for _ in range(10)]
        
        for i in range(count):
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            gpu_util, memory_usage, throughput, latency = self._generate_correlated_metrics()
            gpu_util, memory_usage, latency = self._apply_metric_anomalies(gpu_util, memory_usage, latency)
            
            metric = self._create_workload_metric(timestamp, random.choice(workload_ids),
                                                gpu_util, memory_usage, throughput, latency)
            metrics.append(metric)
        
        return metrics