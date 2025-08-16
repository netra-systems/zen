"""
Realistic Test Fixtures
Production-like test data for comprehensive testing
Uses RealisticTestDataService to generate high-fidelity test data
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.realistic_test_data_service import (
    RealisticTestDataService,
    RealisticDataPatterns
)
from app.db import models_postgres as models
from app import schemas


class RealisticTestFixtures:
    """Generator for realistic test fixtures"""
    
    def __init__(self):
        self.data_service = RealisticTestDataService()
        self.fixture_cache = {}
        
    def generate_production_seed_data(
        self,
        scale: str = "small"
    ) -> Dict[str, Any]:
        """
        Generate complete production-like seed data
        
        Args:
            scale: Data scale - "small" (dev), "medium" (staging), "large" (prod-like)
            
        Returns:
            Complete seed data package
        """
        scale_configs = {
            "small": {
                "users": 10,
                "organizations": 2,
                "workload_days": 7,
                "log_volume": 10000,
                "models": 3
            },
            "medium": {
                "users": 100,
                "organizations": 10,
                "workload_days": 30,
                "log_volume": 100000,
                "models": 5
            },
            "large": {
                "users": 1000,
                "organizations": 50,
                "workload_days": 90,
                "log_volume": 1000000,
                "models": 10
            }
        }
        
        config = scale_configs.get(scale, scale_configs["small"])
        
        return {
            "users": self._generate_users(config["users"], config["organizations"]),
            "organizations": self._generate_organizations(config["organizations"]),
            "workloads": self._generate_workloads(config),
            "logs": self._generate_log_data(config["log_volume"]),
            "metrics": self._generate_metrics_data(config["workload_days"]),
            "corpus_data": self._generate_corpus_data(),
            "ml_models": self._generate_ml_models(config["models"])
        }
    
    def _generate_users(self, count: int, org_count: int) -> List[Dict[str, Any]]:
        """Generate realistic user data"""
        users = []
        roles = ["admin", "developer", "analyst", "viewer"]
        for i in range(count):
            user = {**self._build_user_base_info(i, org_count, roles), 
                   **self._build_user_timestamps(i), 
                   "api_keys": self._build_user_api_keys(i), 
                   "preferences": self._build_user_preferences(i)}
            users.append(user)
        return users
    
    def _build_user_base_info(self, index: int, org_count: int, roles: List[str]) -> Dict[str, Any]:
        """Build basic user information"""
        org_id = index % org_count
        return {
            "id": f"user_{index:04d}",
            "email": f"user{index}@example.com",
            "name": f"Test User {index}",
            "organization_id": f"org_{org_id:03d}",
            "role": roles[index % len(roles)]
        }
    
    def _build_user_timestamps(self, index: int) -> Dict[str, str]:
        """Build user timestamp data"""
        return {
            "created_at": (datetime.now(timezone.utc) - timedelta(days=index)).isoformat(),
            "last_login": (datetime.now(timezone.utc) - timedelta(hours=index % 48)).isoformat()
        }
    
    def _build_user_api_keys(self, user_index: int) -> List[Dict[str, Any]]:
        """Build user API keys"""
        return [
            {
                "key": f"sk-test-{user_index:04d}-{j:02d}",
                "name": f"Key {j}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_used": (datetime.now(timezone.utc) - timedelta(hours=j * 24)).isoformat()
            }
            for j in range(2)
        ]
    
    def _build_user_preferences(self, index: int) -> Dict[str, Any]:
        """Build user preferences"""
        return {
            "theme": "dark" if index % 2 else "light",
            "notifications": True,
            "timezone": "UTC"
        }
    
    def _generate_organizations(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic organization data"""
        org_types = ["enterprise", "startup", "academic", "non-profit"]
        industries = ["tech", "finance", "healthcare", "retail", "education"]
        
        orgs = []
        for i in range(count):
            org = {
                "id": f"org_{i:03d}",
                "name": f"Organization {i}",
                "type": org_types[i % len(org_types)],
                "industry": industries[i % len(industries)],
                "created_at": (datetime.now(timezone.utc) - timedelta(days=i * 30)).isoformat(),
                "subscription": {
                    "plan": ["basic", "pro", "enterprise"][i % 3],
                    "seats": 10 * (i + 1),
                    "usage_limit": 100000 * (i + 1),
                    "billing_cycle": "monthly" if i % 2 else "annual"
                },
                "settings": {
                    "data_retention_days": 90,
                    "audit_logging": True,
                    "sso_enabled": i % 3 == 0,
                    "ip_whitelist": []
                }
            }
            orgs.append(org)
        
        return orgs
    
    def _generate_workloads(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic AI workload data"""
        workload_types = ["ecommerce", "financial", "healthcare"]
        workloads = {}
        
        for wtype in workload_types:
            workload = self.data_service.generate_workload_simulation(
                workload_type=wtype,
                duration_days=config["workload_days"],
                include_seasonality=True
            )
            workloads[wtype] = workload
        
        # Add training jobs
        workloads["training_jobs"] = self._generate_training_jobs(50)
        
        # Add inference endpoints
        workloads["inference_endpoints"] = self._generate_inference_endpoints(20)
        
        # Add batch jobs
        workloads["batch_jobs"] = self._generate_batch_jobs(100)
        
        return workloads
    
    def _generate_training_jobs(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic training job data"""
        jobs = []
        statuses = ["completed", "running", "failed", "queued"]
        for i in range(count):
            start_time = datetime.now(timezone.utc) - timedelta(days=i)
            duration_hours = random.randint(1, 72)
            job = {**self._build_training_job_base(i, start_time, duration_hours, statuses), 
                   **self._build_training_hyperparams(), "metrics": self._build_training_metrics(), 
                   "resource_usage": self._build_training_resource_usage(duration_hours), "cost_usd": random.uniform(10, 10000)}
            jobs.append(job)
        return jobs
    
    def _build_training_job_base(self, index: int, start_time: datetime, duration_hours: int, statuses: List[str]) -> Dict[str, Any]:
        """Build basic training job information"""
        return {
            "id": f"train_{index:04d}",
            "model_name": f"model_v{index % 10}",
            "status": statuses[index % len(statuses)],
            "started_at": start_time.isoformat(),
            "completed_at": (start_time + timedelta(hours=duration_hours)).isoformat() if index % 4 != 1 else None,
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
            endpoint = {
                "id": f"endpoint_{i:04d}",
                "name": f"inference-endpoint-{i}",
                "model": random.choice(list(self.data_service.llm_models.keys())),
                "status": "active" if i % 5 != 0 else "inactive",
                "created_at": (datetime.now(timezone.utc) - timedelta(days=i * 5)).isoformat(),
                "requests_24h": random.randint(100, 100000),
                "avg_latency_ms": random.randint(50, 500),
                "p99_latency_ms": random.randint(200, 2000),
                "error_rate": random.uniform(0, 0.05),
                "autoscaling": {
                    "enabled": i % 2 == 0,
                    "min_replicas": 1,
                    "max_replicas": 10,
                    "target_utilization": 0.7
                },
                "cost_24h_usd": random.uniform(10, 1000)
            }
            endpoints.append(endpoint)
        
        return endpoints
    
    def _generate_batch_jobs(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic batch job data"""
        jobs = []
        job_types = ["data_processing", "model_evaluation", "batch_inference", "data_validation"]
        
        for i in range(count):
            job = {
                "id": f"batch_{i:04d}",
                "type": job_types[i % len(job_types)],
                "status": ["completed", "running", "failed", "pending"][i % 4],
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=i * 2)).isoformat(),
                "started_at": (datetime.now(timezone.utc) - timedelta(hours=i * 2 - 1)).isoformat() if i % 4 != 3 else None,
                "completed_at": (datetime.now(timezone.utc) - timedelta(hours=max(0, i * 2 - 2))).isoformat() if i % 4 == 0 else None,
                "input_records": random.randint(1000, 1000000),
                "processed_records": random.randint(900, 1000000) if i % 4 != 2 else 0,
                "failed_records": random.randint(0, 100) if i % 4 == 2 else 0,
                "duration_seconds": random.randint(60, 7200),
                "cost_usd": random.uniform(1, 100)
            }
            jobs.append(job)
        
        return jobs
    
    def _generate_log_data(self, volume: int) -> Dict[str, List[Dict[str, Any]]]:
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
    
    def _generate_metrics_data(self, days: int) -> Dict[str, Any]:
        """Generate realistic metrics data"""
        metrics = self._init_metrics_structure()
        for day in range(days):
            for hour in range(24):
                timestamp = self._create_timestamp(day, hour)
                self._add_all_metrics(metrics, timestamp, day, hour)
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
    
    def _generate_corpus_data(self) -> Dict[str, Any]:
        """Generate realistic corpus data"""
        corpus_types = ["documentation", "knowledge_base", "training_data", "embeddings"]
        
        corpus_data = {}
        
        for corpus_type in corpus_types:
            corpus_data[corpus_type] = {
                "id": f"corpus_{corpus_type}",
                "name": f"{corpus_type.replace('_', ' ').title()} Corpus",
                "type": corpus_type,
                "documents": random.randint(100, 10000),
                "size_gb": random.uniform(0.1, 50),
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))).isoformat(),
                "last_updated": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))).isoformat(),
                "metadata": {
                    "version": f"v{random.randint(1, 5)}",
                    "language": "en",
                    "encoding": "utf-8",
                    "format": random.choice(["json", "parquet", "csv"])
                },
                "quality_metrics": {
                    "completeness": random.uniform(0.8, 1.0),
                    "accuracy": random.uniform(0.85, 0.99),
                    "consistency": random.uniform(0.9, 1.0)
                }
            }
        
        return corpus_data
    
    def _generate_ml_models(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic ML model data"""
        models = []
        model_types = ["classification", "regression", "clustering", "nlp", "vision"]
        frameworks = ["tensorflow", "pytorch", "scikit-learn", "transformers"]
        
        for i in range(count):
            model = {
                "id": f"model_{i:04d}",
                "name": f"model_v{i}",
                "type": model_types[i % len(model_types)],
                "framework": frameworks[i % len(frameworks)],
                "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
                "created_at": (datetime.now(timezone.utc) - timedelta(days=i * 10)).isoformat(),
                "size_mb": random.randint(10, 10000),
                "parameters": random.randint(1000000, 1000000000),
                "performance": {
                    "accuracy": random.uniform(0.7, 0.99),
                    "f1_score": random.uniform(0.65, 0.95),
                    "inference_time_ms": random.randint(10, 1000)
                },
                "deployment_status": ["deployed", "testing", "archived"][i % 3],
                "endpoints": random.randint(0, 5)
            }
            models.append(model)
        
        return models


# Pytest fixtures
@pytest.fixture
def realistic_fixtures():
    """Provide realistic test fixtures"""
    return RealisticTestFixtures()


@pytest.fixture
def small_seed_data(realistic_fixtures):
    """Small-scale seed data for development"""
    return realistic_fixtures.generate_production_seed_data("small")


@pytest.fixture
def medium_seed_data(realistic_fixtures):
    """Medium-scale seed data for staging"""
    return realistic_fixtures.generate_production_seed_data("medium")


@pytest.fixture
def large_seed_data(realistic_fixtures):
    """Large-scale seed data for production-like testing"""
    return realistic_fixtures.generate_production_seed_data("large")


@pytest.fixture
async def realistic_llm_responses(realistic_fixtures):
    """Generate realistic LLM responses"""
    service = realistic_fixtures.data_service
    
    responses = []
    for model in ["gpt-4", "claude-3-opus", "gemini-pro"]:
        for _ in range(10):
            response = service.generate_realistic_llm_response(
                model=model,
                include_errors=True
            )
            responses.append(response)
    
    return responses


@pytest.fixture
def error_cascade_logs(realistic_fixtures):
    """Generate error cascade log pattern"""
    service = realistic_fixtures.data_service
    return service.generate_realistic_log_data(
        pattern="error_cascade",
        duration_hours=24,
        volume=1000
    )


@pytest.fixture
def memory_leak_logs(realistic_fixtures):
    """Generate memory leak log pattern"""
    service = realistic_fixtures.data_service
    return service.generate_realistic_log_data(
        pattern="memory_leak",
        duration_hours=48,
        volume=2000
    )


# Import required for random
import random