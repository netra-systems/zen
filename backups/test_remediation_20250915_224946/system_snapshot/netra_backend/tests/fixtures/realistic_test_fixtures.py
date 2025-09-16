"""
Realistic Test Fixtures - Index
Central index for all realistic test fixtures split across multiple modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import asyncio
from typing import Any, Dict, List
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest

from netra_backend.app.services.realistic_test_data_service import (
    RealisticTestDataService,
)

# Import all fixture modules
# Import all fixture functions
from netra_backend.tests.fixtures.fixtures_core import (
    CoreTestFixtures,
    core_fixtures,
    large_core_data,
    medium_core_data,
    small_core_data,
)
from netra_backend.tests.fixtures.fixtures_metrics import (
    MetricsFixtures,
    error_cascade_logs,
    memory_leak_logs,
    metrics_fixtures,
    performance_metrics,
)
from netra_backend.tests.fixtures.fixtures_workloads import (
    WorkloadFixtures,
    batch_jobs,
    inference_endpoints,
    training_jobs,
    workload_fixtures,
)

# Import ClickHouse-specific functions from the clickhouse fixtures module
from netra_backend.tests.clickhouse.realistic_test_fixtures import (
    create_query_interceptor_with_mock,
    validate_array_query_syntax,
    create_mock_clickhouse_client,
    generate_realistic_logs,
    generate_llm_metrics,
)

class RealisticTestFixtures:
    """Main generator combining all fixture modules"""
    
    def __init__(self):
        self.core_fixtures = CoreTestFixtures()
        self.workload_fixtures = WorkloadFixtures()
        self.metrics_fixtures = MetricsFixtures()
        self.data_service = RealisticTestDataService()
        self.fixture_cache = {}
        
    def generate_production_seed_data(self, scale: str = "small") -> Dict[str, Any]:
        """
        Generate complete production-like seed data by combining all modules
        
        Args:
            scale: Data scale - "small" (dev), "medium" (staging), "large" (prod-like)
            
        Returns:
            Complete seed data package
        """
        config = self._get_scale_config(scale)
        core_data = self.core_fixtures.generate_production_seed_data(scale)
        workload_data = self.workload_fixtures.generate_workloads(config)
        metrics_data = self._generate_combined_metrics(config)
        
        return {
            **core_data,
            "workloads": workload_data,
            "logs": self.metrics_fixtures.generate_log_data(config["log_volume"]),
            "metrics": metrics_data,
            "corpus_data": self.metrics_fixtures.generate_corpus_data(),
            "ml_models": self.metrics_fixtures.generate_ml_models(config["models"])
        }
    
    def _get_scale_config(self, scale: str) -> Dict[str, int]:
        """Get configuration for the specified scale"""
        scale_configs = self.core_fixtures._get_scale_configs()
        return scale_configs.get(scale, scale_configs["small"])
    
    def _generate_combined_metrics(self, config: Dict[str, int]) -> Dict[str, Any]:
        """Generate metrics data using the metrics fixtures"""
        return self.metrics_fixtures.generate_metrics_data(config["workload_days"])

# Main fixtures
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
    for model in [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "gemini-pro"]:
        for _ in range(10):
            response = service.generate_realistic_llm_response(
                model=model,
                include_errors=True
            )
            responses.append(response)
    
    yield responses

# Re-export all fixture functions
__all__ = [
    "RealisticTestFixtures",
    "CoreTestFixtures", 
    "WorkloadFixtures",
    "MetricsFixtures",
    "realistic_fixtures",
    "small_seed_data",
    "medium_seed_data", 
    "large_seed_data",
    "realistic_llm_responses",
    "core_fixtures",
    "small_core_data",
    "medium_core_data",
    "large_core_data",
    "workload_fixtures",
    "training_jobs",
    "inference_endpoints",
    "batch_jobs",
    "metrics_fixtures",
    "error_cascade_logs",
    "memory_leak_logs",
    "performance_metrics",
    # ClickHouse-specific functions
    "create_query_interceptor_with_mock",
    "validate_array_query_syntax",
    "create_mock_clickhouse_client",
    "generate_realistic_logs",
    "generate_llm_metrics"
]