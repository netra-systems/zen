"""
Realistic Test Fixtures - Metrics and Data
Metrics, logs, corpus data, and ML models fixtures.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from netra_backend.app.services.realistic_test_data_service import (
    RealisticTestDataService,
)

class MetricsFixtures:
    """Generator for metrics and data-related test fixtures"""
    
    def __init__(self):
        self.data_service = RealisticTestDataService()
        
    def generate_log_data(self, volume: int) -> Dict[str, List[Dict[str, Any]]]:
        """Generate realistic log data with various patterns"""
        patterns = [
            ("normal_operation", 0.7),
            ("performance_degradation", 0.15),
            ("error_cascade", 0.1),
            ("memory_leak", 0.05)
        ]
        
        log_data = {}
        
        for pattern, weight in patterns:
            pattern_volume = int(volume * weight)
            logs = self.data_service.generate_realistic_log_data(
                pattern=pattern,
                duration_hours=168,  # 1 week
                volume=pattern_volume
            )
            log_data[pattern] = logs
        
        return log_data
    
    def generate_metrics_data(self, days: int) -> Dict[str, Any]:
        """Generate realistic metrics data"""
        metrics = self._init_metrics_structure()
        for day in range(days):
            self._add_daily_metrics(metrics, day)
        return metrics
    
    def _init_metrics_structure(self) -> Dict[str, List]:
        """Initialize empty metrics structure"""
        return {
            "gpu_utilization": [],
            "memory_usage": [],
            "request_latency": [],
            "cost_data": [],
            "error_rates": []
        }
    
    def _add_daily_metrics(self, metrics: Dict, day: int) -> None:
        """Add metrics for a full day"""
        for hour in range(24):
            timestamp = self._create_timestamp(day, hour)
            self._add_all_metrics(metrics, timestamp, day, hour)
    
    def _create_timestamp(self, day: int, hour: int) -> datetime:
        """Create timestamp for metrics data point"""
        return datetime.now(timezone.utc) - timedelta(days=day, hours=hour)
    
    def _add_all_metrics(self, metrics: Dict, timestamp: datetime, day: int, hour: int) -> None:
        """Add all metric types for a given timestamp"""
        metrics["gpu_utilization"].append(self._generate_gpu_metric(timestamp, hour))
        metrics["memory_usage"].append(self._generate_memory_metric(timestamp, day))
        metrics["request_latency"].append(self._generate_latency_metric(timestamp, hour))
        metrics["cost_data"].append(self._generate_cost_metric(timestamp))
        metrics["error_rates"].append(self._generate_error_rate_metric(timestamp, day, hour))
    
    def _generate_gpu_metric(self, timestamp: datetime, hour: int) -> Dict[str, Any]:
        """Generate GPU utilization metric"""
        base_gpu = self._calculate_gpu_base(hour)
        gpu_util = base_gpu + random.gauss(0, 10)
        return {
            "timestamp": timestamp.isoformat(),
            "value": max(0, min(100, gpu_util)),
            "gpu_id": "gpu_0"
        }
    
    def _calculate_gpu_base(self, hour: int) -> int:
        """Calculate base GPU utilization by hour"""
        return 40 if 8 <= hour <= 20 else 20
    
    def _generate_memory_metric(self, timestamp: datetime, day: int) -> Dict[str, Any]:
        """Generate memory usage metric"""
        base_memory = 50 + (day * 0.5)
        memory = base_memory + random.gauss(0, 5)
        return {
            "timestamp": timestamp.isoformat(),
            "value_gb": max(0, memory),
            "total_gb": 100
        }
    
    def _generate_latency_metric(self, timestamp: datetime, hour: int) -> Dict[str, Any]:
        """Generate request latency metric"""
        base_latency = self._calculate_latency_base(hour)
        latency = base_latency + random.gauss(0, 20)
        return {
            "timestamp": timestamp.isoformat(),
            "p50_ms": max(10, latency),
            "p95_ms": max(20, latency * 2),
            "p99_ms": max(30, latency * 3)
        }
    
    def _calculate_latency_base(self, hour: int) -> int:
        """Calculate base latency by hour"""
        return 100 if 9 <= hour <= 17 else 50
    
    def _generate_cost_metric(self, timestamp: datetime) -> Dict[str, Any]:
        """Generate cost breakdown metric"""
        hourly_cost = random.uniform(10, 100)
        return {
            "timestamp": timestamp.isoformat(),
            "compute_cost": hourly_cost * 0.6,
            "storage_cost": hourly_cost * 0.2,
            "network_cost": hourly_cost * 0.1,
            "other_cost": hourly_cost * 0.1,
            "total_cost": hourly_cost
        }
    
    def _generate_error_rate_metric(self, timestamp: datetime, day: int, hour: int) -> Dict[str, Any]:
        """Generate error rate metric"""
        base_error_rate = 0.01
        error_spike = self._calculate_error_spike(day, hour)
        final_rate = min(1.0, base_error_rate + error_spike + random.gauss(0, 0.002))
        return {
            "timestamp": timestamp.isoformat(),
            "rate": final_rate,
            "total_requests": random.randint(1000, 10000)
        }
    
    def _calculate_error_spike(self, day: int, hour: int) -> float:
        """Calculate error spike for weekly pattern"""
        return 0.1 if hour == 14 and day % 7 == 3 else 0
    
    def generate_corpus_data(self) -> Dict[str, Any]:
        """Generate realistic corpus data"""
        corpus_types = ["documentation", "knowledge_base", "training_data", "embeddings"]
        
        corpus_data = {}
        
        for corpus_type in corpus_types:
            corpus_data[corpus_type] = self._create_corpus_entry(corpus_type)
        
        return corpus_data
    
    def _create_corpus_entry(self, corpus_type: str) -> Dict[str, Any]:
        """Create individual corpus data entry"""
        base_info = self._build_corpus_base_info(corpus_type)
        metadata = self._build_corpus_metadata()
        quality_metrics = self._build_corpus_quality_metrics()
        
        return {**base_info, "metadata": metadata, "quality_metrics": quality_metrics}
    
    def _build_corpus_base_info(self, corpus_type: str) -> Dict[str, Any]:
        """Build basic corpus information"""
        created_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))
        updated_date = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))
        return {
            "id": f"corpus_{corpus_type}",
            "name": f"{corpus_type.replace('_', ' ').title()} Corpus",
            "type": corpus_type,
            "documents": random.randint(100, 10000),
            "size_gb": random.uniform(0.1, 50),
            "created_at": created_date.isoformat(),
            "last_updated": updated_date.isoformat()
        }
    
    def _build_corpus_metadata(self) -> Dict[str, str]:
        """Build corpus metadata"""
        formats = ["json", "parquet", "csv"]
        return {
            "version": f"v{random.randint(1, 5)}",
            "language": "en",
            "encoding": "utf-8",
            "format": random.choice(formats)
        }
    
    def _build_corpus_quality_metrics(self) -> Dict[str, float]:
        """Build corpus quality metrics"""
        return {
            "completeness": random.uniform(0.8, 1.0),
            "accuracy": random.uniform(0.85, 0.99),
            "consistency": random.uniform(0.9, 1.0)
        }
    
    def generate_ml_models(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic ML model data"""
        models = []
        model_types = ["classification", "regression", "clustering", "nlp", "vision"]
        frameworks = ["tensorflow", "pytorch", "scikit-learn", "transformers"]
        
        for i in range(count):
            model = self._create_ml_model(i, model_types, frameworks)
            models.append(model)
        
        return models
    
    def _create_ml_model(self, index: int, model_types: List[str], frameworks: List[str]) -> Dict[str, Any]:
        """Create individual ML model data"""
        base_info = self._build_model_base_info(index, model_types, frameworks)
        performance = self._build_model_performance()
        deployment = self._build_model_deployment(index)
        
        return {**base_info, "performance": performance, **deployment}
    
    def _build_model_base_info(self, index: int, model_types: List[str], frameworks: List[str]) -> Dict[str, Any]:
        """Build basic model information"""
        created_date = datetime.now(timezone.utc) - timedelta(days=index * 10)
        return {
            "id": f"model_{index:04d}",
            "name": f"model_v{index}",
            "type": model_types[index % len(model_types)],
            "framework": frameworks[index % len(frameworks)],
            "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
            "created_at": created_date.isoformat(),
            "size_mb": random.randint(10, 10000),
            "parameters": random.randint(1000000, 1000000000)
        }
    
    def _build_model_performance(self) -> Dict[str, float]:
        """Build model performance metrics"""
        return {
            "accuracy": random.uniform(0.7, 0.99),
            "f1_score": random.uniform(0.65, 0.95),
            "inference_time_ms": random.randint(10, 1000)
        }
    
    def _build_model_deployment(self, index: int) -> Dict[str, Any]:
        """Build model deployment information"""
        statuses = ["deployed", "testing", "archived"]
        return {
            "deployment_status": statuses[index % 3],
            "endpoints": random.randint(0, 5)
        }

# Pytest fixtures
@pytest.fixture
def metrics_fixtures():
    """Provide metrics test fixtures"""
    return MetricsFixtures()

@pytest.fixture
def error_cascade_logs(metrics_fixtures):
    """Generate error cascade log pattern"""
    service = metrics_fixtures.data_service
    return service.generate_realistic_log_data(
        pattern="error_cascade",
        duration_hours=24,
        volume=1000
    )

@pytest.fixture
def memory_leak_logs(metrics_fixtures):
    """Generate memory leak log pattern"""
    service = metrics_fixtures.data_service
    return service.generate_realistic_log_data(
        pattern="memory_leak",
        duration_hours=48,
        volume=2000
    )

@pytest.fixture
def performance_metrics(metrics_fixtures):
    """Generate performance metrics data"""
    return metrics_fixtures.generate_metrics_data(7)
