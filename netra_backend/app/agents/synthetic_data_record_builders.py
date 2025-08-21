"""
Synthetic Data Record Builders Module

Handles creation of individual synthetic data records 
with different formats and schemas.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SyntheticDataRecordBuilders:
    """Handles creation of individual synthetic data records"""
    
    def calculate_record_timestamp(self, base_time: datetime, time_range_days: int) -> datetime:
        """Calculate timestamp for record with random offset"""
        time_offset = random.randint(0, time_range_days * 86400)
        return base_time + timedelta(seconds=time_offset)
    
    def create_base_inference_data(self, timestamp: datetime, models: List[str]) -> Dict[str, Any]:
        """Create base inference data fields"""
        return {
            "timestamp": timestamp.isoformat(),
            "model": random.choice(models),
            "tokens_input": random.randint(10, 2000),
            "tokens_output": random.randint(10, 1000)
        }
    
    def create_inference_performance_data(self, profile: WorkloadProfile) -> Dict[str, Any]:
        """Create performance-related inference data"""
        return {
            "latency_ms": random.gauss(100, 20 * profile.noise_level),
            "status": "success" if random.random() > 0.02 else "error",
            "cost_usd": round(random.uniform(0.01, 1.0), 4)
        }
    
    def create_latency_metrics(self, profile: WorkloadProfile) -> Dict[str, Any]:
        """Create latency-related performance metrics"""
        return {
            "throughput_rps": random.gauss(1000, 100 * profile.noise_level),
            "p50_latency_ms": random.gauss(50, 10 * profile.noise_level),
            "p95_latency_ms": random.gauss(150, 30 * profile.noise_level),
            "p99_latency_ms": random.gauss(300, 50 * profile.noise_level)
        }
    
    def create_system_metrics(self) -> Dict[str, Any]:
        """Create system resource metrics"""
        return {
            "error_rate": random.uniform(0, 0.05),
            "cpu_usage": random.uniform(20, 80),
            "memory_usage": random.uniform(30, 70)
        }