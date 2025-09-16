"""
E2E Test Data Generation: Production-Mirror and Stress Test Datasets

This module provides comprehensive test data generation for E2E testing with:
- Production-mirror datasets (100K records)
- Stress-test datasets (1M records) 
- Domain-specific datasets (finance, healthcare, retail, manufacturing)
- Realistic statistical distributions and temporal patterns

ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines
- Maximum function size: 8 lines
- Single responsibility: Test data generation
- Strong typing: All functions typed
- Modular design: Composable generators

Usage:
    from netra_backend.tests.e2e.data.seeded_data_generator import (
        ProductionMirrorGenerator,
        StressTestGenerator,
        DomainSpecificGenerator
    )
"""

import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import numpy as np
from faker import Faker
from faker.providers import BaseProvider

from netra_backend.app.schemas.agent_models import AgentMetadata, ToolResultData
from netra_backend.app.schemas.core_enums import MessageType
from netra_backend.app.schemas.core_models import Message, Thread, User

@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""
    size: int
    temporal_span_days: int = 90
    error_rate: float = 0.02
    domain: Optional[str] = None
    include_edge_cases: bool = True

class BaseDataGenerator(ABC):
    """Abstract base for all data generators."""
    
    def __init__(self, config: DatasetConfig):
        self.config = config
        self.fake = Faker()
        self._setup_providers()
    
    def _setup_providers(self) -> None:
        """Setup faker providers."""
        self.fake.add_provider(WorkloadProvider)
        self.fake.add_provider(MetricsProvider)
    
    @abstractmethod
    def generate_dataset(self) -> Iterator[Dict[str, Any]]:
        """Generate complete dataset."""
        pass

class ProductionMirrorGenerator(BaseDataGenerator):
    """Generates production-mirror datasets (100K records)."""
    
    def generate_dataset(self) -> Iterator[Dict[str, Any]]:
        """Generate production-mirror dataset."""
        for i in range(self.config.size):
            yield self._create_realistic_record(i)
            if i % 10000 == 0:
                yield self._create_edge_case_record(i)
    
    def _create_realistic_record(self, index: int) -> Dict[str, Any]:
        """Create realistic production record."""
        timestamp = self._get_realistic_timestamp(index)
        user = self._generate_production_user(index)
        workload = self._generate_production_workload()
        metrics = self._generate_production_metrics(workload)
        return self._build_record(timestamp, user, workload, metrics)
    
    def _create_edge_case_record(self, index: int) -> Dict[str, Any]:
        """Create edge case record."""
        return self._create_realistic_record(index)
    
    def _get_realistic_timestamp(self, index: int) -> datetime:
        """Generate realistic timestamp."""
        days_back = (index / self.config.size) * self.config.temporal_span_days
        return datetime.now(timezone.utc) - timedelta(days=days_back)
    
    def _generate_production_user(self, index: int) -> Dict[str, str]:
        """Generate production-like user."""
        return {
            "id": str(uuid.uuid4()),
            "email": self.fake.email(),
            "name": self.fake.name()
        }

class StressTestGenerator(BaseDataGenerator):
    """Generates stress-test datasets (1M records)."""
    
    def generate_dataset(self) -> Iterator[Dict[str, Any]]:
        """Generate stress-test dataset."""
        for i in range(self.config.size):
            yield self._create_stress_record(i)
            if i % 50000 == 0:
                yield self._create_burst_pattern_record(i)
    
    def _create_stress_record(self, index: int) -> Dict[str, Any]:
        """Create stress test record."""
        timestamp = self._get_burst_timestamp(index)
        workload = self._generate_high_volume_workload()
        metrics = self._generate_stress_metrics(workload)
        user = self._generate_concurrent_user(index)
        return self._build_record(timestamp, user, workload, metrics)
    
    def _create_burst_pattern_record(self, index: int) -> Dict[str, Any]:
        """Create burst pattern record."""
        return self._create_stress_record(index)
    
    def _get_burst_timestamp(self, index: int) -> datetime:
        """Generate burst pattern timestamp."""
        burst_cycle = index % 1000
        base_time = datetime.now(timezone.utc)
        return base_time - timedelta(seconds=burst_cycle * 0.1)
    
    def _generate_high_volume_workload(self) -> Dict[str, Any]:
        """Generate high volume workload."""
        return {
            "type": random.choice(["batch", "stream", "interactive"]),
            "concurrent_requests": random.randint(100, 1000)
        }

class DomainSpecificGenerator(BaseDataGenerator):
    """Generates domain-specific datasets."""
    
    def __init__(self, config: DatasetConfig):
        super().__init__(config)
        self.domain_generators = {
            "finance": self._generate_finance_data,
            "healthcare": self._generate_healthcare_data,
            "retail": self._generate_retail_data,
            "manufacturing": self._generate_manufacturing_data
        }
    
    def generate_dataset(self) -> Iterator[Dict[str, Any]]:
        """Generate domain-specific dataset."""
        if self.config.domain not in self.domain_generators:
            raise ValueError(f"Unsupported domain: {self.config.domain}")
        
        generator_func = self.domain_generators[self.config.domain]
        for i in range(self.config.size):
            yield generator_func(i)
    
    def _generate_finance_data(self, index: int) -> Dict[str, Any]:
        """Generate finance domain data."""
        return {
            "domain": "finance",
            "portfolio_id": f"port_{index}",
            "risk_score": random.uniform(0.1, 10.0),
            "trade_volume": random.randint(1000, 1000000)
        }
    
    def _generate_healthcare_data(self, index: int) -> Dict[str, Any]:
        """Generate healthcare domain data."""
        return {
            "domain": "healthcare", 
            "patient_id": f"pat_{index}",
            "diagnosis_confidence": random.uniform(0.7, 0.99),
            "treatment_complexity": random.randint(1, 5)
        }
    
    def _generate_retail_data(self, index: int) -> Dict[str, Any]:
        """Generate retail domain data."""
        return {
            "domain": "retail",
            "product_id": f"prod_{index}",
            "demand_forecast": random.uniform(0.8, 1.2),
            "inventory_turnover": random.randint(4, 12)
        }
    
    def _generate_manufacturing_data(self, index: int) -> Dict[str, Any]:
        """Generate manufacturing domain data."""
        return {
            "domain": "manufacturing",
            "production_line": f"line_{index % 10}",
            "efficiency_score": random.uniform(0.75, 0.98),
            "quality_rating": random.randint(85, 99)
        }

class WorkloadProvider(BaseProvider):
    """Faker provider for workload data."""
    
    def workload_type(self) -> str:
        """Generate workload type."""
        types = ["inference", "training", "batch", "streaming"]
        return self.random.choice(types)
    
    def cost_model(self) -> str:
        """Generate cost model."""
        models = ["pay_per_use", "reserved", "spot", "commitment"]
        return self.random.choice(models)

class MetricsProvider(BaseProvider):
    """Faker provider for metrics data."""
    
    def latency_ms(self) -> float:
        """Generate realistic latency."""
        return max(10.0, np.random.lognormal(4.0, 1.0))
    
    def throughput_rps(self) -> float:
        """Generate realistic throughput."""
        return max(1.0, np.random.gamma(2.0, 50.0))

# Helper functions for common record building
def _build_record(timestamp: datetime, user: Dict, workload: Dict, metrics: Dict) -> Dict[str, Any]:
    """Build complete record from components."""
    return {
        "timestamp": timestamp.isoformat(),
        "user": user,
        "workload": workload, 
        "metrics": metrics,
        "id": str(uuid.uuid4())
    }

def _generate_production_workload() -> Dict[str, Any]:
    """Generate production workload data."""
    fake = Faker()
    return {
        "type": fake.workload_type(),
        "cost_model": fake.cost_model(),
        "resource_usage": random.uniform(0.1, 0.9)
    }

def _generate_production_metrics(workload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate production metrics."""
    fake = Faker()
    fake.add_provider(MetricsProvider)
    return {
        "latency_ms": fake.latency_ms(),
        "throughput_rps": fake.throughput_rps(),
        "cost_usd": random.uniform(0.01, 100.0)
    }

def _generate_stress_metrics(workload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate stress test metrics."""
    multiplier = workload.get("concurrent_requests", 1) / 100
    return {
        "latency_ms": random.uniform(50, 2000) * multiplier,
        "throughput_rps": random.uniform(10, 1000) / multiplier,
        "error_rate": random.uniform(0.0, 0.1) * multiplier
    }

def _generate_concurrent_user(index: int) -> Dict[str, str]:
    """Generate concurrent user for stress testing."""
    user_pool_size = 1000
    user_id = index % user_pool_size
    return {
        "id": f"stress_user_{user_id}",
        "email": f"user{user_id}@stress.test",
        "name": f"StressUser{user_id}"
    }