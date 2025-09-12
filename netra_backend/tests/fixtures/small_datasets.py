"""
Small, Fast-Loading Test Datasets for Unit Tests
Provides realistic test data matching production schemas.
Maximum 300 lines, functions  <= 8 lines.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from netra_backend.app.schemas.agent import AgentStatus, SubAgentLifecycle, TodoStatus
from netra_backend.app.schemas.finops import CostComparison, FinOps
from netra_backend.app.schemas.llm_request_types import (
    LLMFunction,
    LLMRequest,
    StructuredOutputSchema,
)
from netra_backend.app.schemas.metrics import (
    CorpusMetric,
    MetricType,
    QualityMetrics,
    ResourceType,
    ResourceUsage,
)
from netra_backend.app.schemas.performance import Performance
from netra_backend.app.schemas.policy import LearnedPolicy, PredictedOutcome
from netra_backend.app.schemas.supply import ModelIdentifier, SupplyOption

class SmallTestDatasets:
    """Generator for small, fast-loading test datasets"""
    
    def __init__(self):
        self._current_timestamp = datetime.now(timezone.utc)

    def get_agent_optimization_requests(self) -> List[Dict[str, Any]]:
        """Generate 10 agent optimization request records"""
        return [self._create_agent_request(i) for i in range(10)]

    def get_cost_latency_constraints(self) -> List[Dict[str, Any]]:
        """Generate 20 cost/latency constraint records"""
        return [self._create_cost_constraint(i) for i in range(20)]

    def get_model_performance_metrics(self) -> List[Dict[str, Any]]:
        """Generate 15 model performance metric records"""
        return [self._create_performance_metric(i) for i in range(15)]

    def get_kv_cache_configurations(self) -> List[Dict[str, Any]]:
        """Generate 10 KV cache configuration records"""
        return [self._create_kv_cache_config(i) for i in range(10)]

    def get_multi_constraint_scenarios(self) -> List[Dict[str, Any]]:
        """Generate 25 multi-constraint scenario records"""
        return [self._create_multi_constraint_scenario(i) for i in range(25)]

    def _create_agent_request(self, index: int) -> Dict[str, Any]:
        """Create single agent optimization request"""
        providers = ["openai", "anthropic", "google", "cohere"]
        models = [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "gemini-pro", "command-r"]
        statuses = [AgentStatus.RUNNING, AgentStatus.COMPLETED, AgentStatus.FAILED]
        
        return {
            "id": f"req_{index:03d}",
            "user_id": f"user_{index % 5:02d}",
            "model_provider": providers[index % 4],
            "model_name": models[index % 4],
            "status": statuses[index % 3].value,
            "created_at": (self._current_timestamp - timedelta(hours=index)).isoformat()
        }

    def _create_cost_constraint(self, index: int) -> Dict[str, Any]:
        """Create cost/latency constraint record"""
        cost_values = [0.001, 0.01, 0.1, 1.0, 10.0]
        latency_values = [50, 100, 200, 500, 1000]
        
        return {
            "constraint_id": f"const_{index:03d}",
            "max_cost_per_token": cost_values[index % 5],
            "max_latency_ms": latency_values[index % 5],
            "priority": "high" if index < 5 else "medium" if index < 15 else "low",
            "workload_type": ["inference", "batch", "training"][index % 3]
        }

    def _create_performance_metric(self, index: int) -> Dict[str, Any]:
        """Create model performance metric record"""
        models = [LLMModel.GEMINI_2_5_FLASH.value, "claude-3", "gemini-pro"]
        metrics = ["throughput", "latency", "accuracy", "cost_efficiency"]
        
        return {
            "metric_id": f"perf_{index:03d}",
            "model_name": models[index % 3],
            "metric_type": metrics[index % 4],
            "value": round(50 + (index * 3.7) % 100, 2),
            "unit": self._get_metric_unit(metrics[index % 4]),
            "timestamp": (self._current_timestamp - timedelta(minutes=index * 5)).isoformat()
        }

    def _create_kv_cache_config(self, index: int) -> Dict[str, Any]:
        """Create KV cache configuration record"""
        cache_sizes = [1024, 2048, 4096, 8192, 16384]
        strategies = ["lru", "fifo", "adaptive", "priority"]
        
        return {
            "config_id": f"kv_{index:03d}",
            "cache_size_mb": cache_sizes[index % 5],
            "eviction_strategy": strategies[index % 4],
            "ttl_seconds": 300 + (index * 60),
            "hit_rate": round(0.7 + (index * 0.02), 3),
            "enabled": index % 3 != 0
        }

    def _create_multi_constraint_scenario(self, index: int) -> Dict[str, Any]:
        """Create multi-constraint scenario record"""
        scenario_types = ["cost_latency", "quality_speed", "efficiency_scale"]
        complexity = ["simple", "moderate", "complex"]
        
        return {
            "scenario_id": f"multi_{index:03d}",
            "scenario_type": scenario_types[index % 3],
            "complexity": complexity[index % 3],
            "target_cost": round(0.01 + (index * 0.005), 4),
            "target_latency": 100 + (index * 10),
            "quality_threshold": round(0.8 + (index * 0.005), 3),
            "success_rate": round(0.85 + (index * 0.003), 3)
        }

    def _get_metric_unit(self, metric_type: str) -> str:
        """Get appropriate unit for metric type"""
        units = {
            "throughput": "req/s",
            "latency": "ms", 
            "accuracy": "score",
            "cost_efficiency": "$/token"
        }
        return units.get(metric_type, "unit")

    def get_edge_case_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate edge case test data"""
        return {
            "zero_values": self._create_zero_value_cases(),
            "max_values": self._create_max_value_cases(),
            "invalid_states": self._create_invalid_state_cases(),
            "boundary_conditions": self._create_boundary_cases()
        }

    def _create_zero_value_cases(self) -> List[Dict[str, Any]]:
        """Create edge cases with zero values"""
        return [
            {"cost": 0.0, "latency": 0, "scenario": "zero_cost"},
            {"cost": 0.001, "latency": 1, "scenario": "minimal_values"}
        ]

    def _create_max_value_cases(self) -> List[Dict[str, Any]]:
        """Create edge cases with maximum values"""
        return [
            {"cost": 999.99, "latency": 60000, "scenario": "max_values"},
            {"cost": 100.0, "latency": 30000, "scenario": "high_values"}
        ]

    def _create_invalid_state_cases(self) -> List[Dict[str, Any]]:
        """Create edge cases with invalid states"""
        return [
            {"status": "unknown", "error": "invalid_status"},
            {"status": None, "error": "null_status"}
        ]

    def _create_boundary_cases(self) -> List[Dict[str, Any]]:
        """Create boundary condition test cases"""
        return [
            {"threshold": 0.999, "scenario": "near_max_threshold"},
            {"threshold": 0.001, "scenario": "near_min_threshold"}
        ]

# Singleton instance for global access
small_datasets = SmallTestDatasets()

# Export functions for direct access
def get_agent_optimization_requests() -> List[Dict[str, Any]]:
    """Get agent optimization request test data"""
    return small_datasets.get_agent_optimization_requests()

def get_cost_latency_constraints() -> List[Dict[str, Any]]:
    """Get cost/latency constraint test data"""
    return small_datasets.get_cost_latency_constraints()

def get_model_performance_metrics() -> List[Dict[str, Any]]:
    """Get model performance metrics test data"""
    return small_datasets.get_model_performance_metrics()

def get_kv_cache_configurations() -> List[Dict[str, Any]]:
    """Get KV cache configuration test data"""
    return small_datasets.get_kv_cache_configurations()

def get_multi_constraint_scenarios() -> List[Dict[str, Any]]:
    """Get multi-constraint scenario test data"""
    return small_datasets.get_multi_constraint_scenarios()

def get_edge_case_data() -> Dict[str, List[Dict[str, Any]]]:
    """Get edge case test data"""
    return small_datasets.get_edge_case_data()

def get_all_small_datasets() -> Dict[str, List[Dict[str, Any]]]:
    """Get all small test datasets in single call"""
    return {
        "agent_requests": get_agent_optimization_requests(),
        "cost_constraints": get_cost_latency_constraints(),
        "performance_metrics": get_model_performance_metrics(),
        "kv_cache_configs": get_kv_cache_configurations(),
        "multi_constraint_scenarios": get_multi_constraint_scenarios(),
        "edge_cases": get_edge_case_data()
    }

# Pydantic model instances for type validation
def get_typed_performance_metrics() -> List[Performance]:
    """Get Performance model instances"""
    data = get_model_performance_metrics()
    return [
        Performance(latency_ms={
            item["model_name"]: float(item["value"]) if item["metric_type"] == "latency" else 100.0
        })
        for item in data[:5]  # Sample subset
    ]

def get_typed_finops_data() -> List[FinOps]:
    """Get FinOps model instances"""
    cost_data = get_cost_latency_constraints()
    return [
        FinOps(
            attribution={"workload": item["workload_type"]},
            cost={"per_token": item["max_cost_per_token"]},
            pricing_info={"priority": item["priority"]}
        )
        for item in cost_data[:5]  # Sample subset
    ]

def get_typed_supply_options() -> List[SupplyOption]:
    """Get SupplyOption model instances"""
    return [
        SupplyOption(
            id=i,
            name=f"supply_option_{i}",
            description=f"Test supply option {i}"
        )
        for i in range(1, 6)
    ]