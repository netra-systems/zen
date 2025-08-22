"""
Realistic Test Fixtures - Workloads
Workload fixtures including training jobs, inference endpoints, and batch jobs.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from netra_backend.app.services.realistic_test_data_service import (
    RealisticTestDataService,
)

class WorkloadFixtures:
    """Generator for workload-related test fixtures"""
    
    def __init__(self):
        self.data_service = RealisticTestDataService()
        
    def generate_workloads(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic AI workload data"""
        workload_types = ["ecommerce", "financial", "healthcare"]
        workloads = self._generate_simulation_workloads(workload_types, config)
        
        # Add specialized workload types
        workloads["training_jobs"] = self._generate_training_jobs(50)
        workloads["inference_endpoints"] = self._generate_inference_endpoints(20)
        workloads["batch_jobs"] = self._generate_batch_jobs(100)
        
        return workloads
    
    def _generate_simulation_workloads(self, workload_types: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate workload simulations for each type"""
        workloads = {}
        for wtype in workload_types:
            workload = self.data_service.generate_workload_simulation(
                workload_type=wtype,
                duration_days=config["workload_days"],
                include_seasonality=True
            )
            workloads[wtype] = workload
        return workloads
    
    def _generate_training_jobs(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic training job data"""
        jobs = []
        statuses = ["completed", "running", "failed", "queued"]
        for i in range(count):
            job = self._create_training_job(i, statuses)
            jobs.append(job)
        return jobs
    
    def _create_training_job(self, index: int, statuses: List[str]) -> Dict[str, Any]:
        """Create individual training job data"""
        start_time = datetime.now(timezone.utc) - timedelta(days=index)
        duration_hours = random.randint(1, 72)
        base_info = self._build_training_job_base(index, start_time, duration_hours, statuses)
        hyperparams = self._build_training_hyperparams()
        metrics = self._build_training_metrics()
        resource_usage = self._build_training_resource_usage(duration_hours)
        cost = random.uniform(10, 10000)
        
        return {**base_info, "hyperparams": hyperparams, "metrics": metrics, 
                "resource_usage": resource_usage, "cost_usd": cost}
    
    def _build_training_job_base(self, index: int, start_time: datetime, duration_hours: int, statuses: List[str]) -> Dict[str, Any]:
        """Build basic training job information"""
        completed_time = start_time + timedelta(hours=duration_hours) if index % 4 != 1 else None
        return {
            "id": f"train_{index:04d}",
            "model_name": f"model_v{index % 10}",
            "status": statuses[index % len(statuses)],
            "started_at": start_time.isoformat(),
            "completed_at": completed_time.isoformat() if completed_time else None,
            "duration_hours": duration_hours
        }
    
    def _build_training_hyperparams(self) -> Dict[str, Any]:
        """Build training hyperparameters"""
        return {
            "epochs": random.randint(10, 100),
            "batch_size": 2 ** random.randint(5, 10),
            "learning_rate": 10 ** random.uniform(-5, -2)
        }
    
    def _build_training_metrics(self) -> Dict[str, float]:
        """Build training metrics"""
        return {
            "loss": random.uniform(0.1, 2.0),
            "accuracy": random.uniform(0.7, 0.99),
            "val_loss": random.uniform(0.15, 2.5),
            "val_accuracy": random.uniform(0.65, 0.95)
        }
    
    def _build_training_resource_usage(self, duration_hours: int) -> Dict[str, int]:
        """Build resource usage data"""
        return {
            "gpu_hours": duration_hours * random.randint(1, 8),
            "cpu_hours": duration_hours * random.randint(4, 32),
            "memory_gb_hours": duration_hours * random.randint(16, 256),
            "storage_gb": random.randint(10, 1000)
        }
    
    def _generate_inference_endpoints(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic inference endpoint data"""
        endpoints = []
        
        for i in range(count):
            endpoint = self._create_inference_endpoint(i)
            endpoints.append(endpoint)
        
        return endpoints
    
    def _create_inference_endpoint(self, index: int) -> Dict[str, Any]:
        """Create individual inference endpoint data"""
        base_info = self._build_endpoint_base_info(index)
        performance_metrics = self._build_endpoint_performance()
        autoscaling_config = self._build_endpoint_autoscaling(index)
        cost = random.uniform(10, 1000)
        
        return {**base_info, **performance_metrics, 
                "autoscaling": autoscaling_config, "cost_24h_usd": cost}
    
    def _build_endpoint_base_info(self, index: int) -> Dict[str, Any]:
        """Build basic endpoint information"""
        created_date = datetime.now(timezone.utc) - timedelta(days=index * 5)
        model_list = list(self.data_service.llm_models.keys())
        return {
            "id": f"endpoint_{index:04d}",
            "name": f"inference-endpoint-{index}",
            "model": random.choice(model_list),
            "status": "active" if index % 5 != 0 else "inactive",
            "created_at": created_date.isoformat()
        }
    
    def _build_endpoint_performance(self) -> Dict[str, Any]:
        """Build endpoint performance metrics"""
        return {
            "requests_24h": random.randint(100, 100000),
            "avg_latency_ms": random.randint(50, 500),
            "p99_latency_ms": random.randint(200, 2000),
            "error_rate": random.uniform(0, 0.05)
        }
    
    def _build_endpoint_autoscaling(self, index: int) -> Dict[str, Any]:
        """Build autoscaling configuration"""
        return {
            "enabled": index % 2 == 0,
            "min_replicas": 1,
            "max_replicas": 10,
            "target_utilization": 0.7
        }
    
    def _generate_batch_jobs(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic batch job data"""
        jobs = []
        job_types = ["data_processing", "model_evaluation", "batch_inference", "data_validation"]
        
        for i in range(count):
            job = self._create_batch_job(i, job_types)
            jobs.append(job)
        
        return jobs
    
    def _create_batch_job(self, index: int, job_types: List[str]) -> Dict[str, Any]:
        """Create individual batch job data"""
        base_info = self._build_batch_job_base(index, job_types)
        timing_info = self._build_batch_job_timing(index)
        processing_info = self._build_batch_job_processing(index)
        cost = random.uniform(1, 100)
        
        return {**base_info, **timing_info, **processing_info, "cost_usd": cost}
    
    def _build_batch_job_base(self, index: int, job_types: List[str]) -> Dict[str, Any]:
        """Build basic batch job information"""
        status_list = ["completed", "running", "failed", "pending"]
        created_time = datetime.now(timezone.utc) - timedelta(hours=index * 2)
        return {
            "id": f"batch_{index:04d}",
            "type": job_types[index % len(job_types)],
            "status": status_list[index % 4],
            "created_at": created_time.isoformat()
        }
    
    def _build_batch_job_timing(self, index: int) -> Dict[str, Any]:
        """Build batch job timing information"""
        base_time = datetime.now(timezone.utc) - timedelta(hours=index * 2)
        started_time = base_time - timedelta(hours=1) if index % 4 != 3 else None
        completed_time = base_time - timedelta(hours=2) if index % 4 == 0 else None
        duration = random.randint(60, 7200)
        
        return {
            "started_at": started_time.isoformat() if started_time else None,
            "completed_at": completed_time.isoformat() if completed_time else None,
            "duration_seconds": duration
        }
    
    def _build_batch_job_processing(self, index: int) -> Dict[str, Any]:
        """Build batch job processing information"""
        input_records = random.randint(1000, 1000000)
        processed_records = random.randint(900, 1000000) if index % 4 != 2 else 0
        failed_records = random.randint(0, 100) if index % 4 == 2 else 0
        
        return {
            "input_records": input_records,
            "processed_records": processed_records,
            "failed_records": failed_records
        }

# Pytest fixtures
@pytest.fixture
def workload_fixtures():
    """Provide workload test fixtures"""
    return WorkloadFixtures()

@pytest.fixture
def training_jobs(workload_fixtures):
    """Generate training job fixtures"""
    return workload_fixtures._generate_training_jobs(20)

@pytest.fixture
def inference_endpoints(workload_fixtures):
    """Generate inference endpoint fixtures"""
    return workload_fixtures._generate_inference_endpoints(10)

@pytest.fixture
def batch_jobs(workload_fixtures):
    """Generate batch job fixtures"""
    return workload_fixtures._generate_batch_jobs(30)
