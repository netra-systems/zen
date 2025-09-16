import pytest
"""
Context generation utilities for Example Prompts E2E Tests
Generates synthetic contexts for different test scenarios
"""""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import IsolatedEnvironment


# Test framework import - using pytest fixtures instead

import random
from datetime import datetime, timedelta
from typing import Any, Dict

class ContextGenerator:
    """Generates synthetic contexts for different prompt types"""

    def generate_synthetic_context(self, prompt_type: str) -> Dict[str, Any]:
        """Generate synthetic context data based on prompt type"""
        context_generators = {
        "cost_reduction": self._generate_cost_context,
        "latency_optimization": self._generate_latency_context,
        "capacity_planning": self._generate_capacity_context,
        "function_optimization": self._generate_function_context,
        "model_evaluation": self._generate_model_context,
        "audit": self._generate_audit_context,
        "multi_objective": self._generate_multi_objective_context,
        "tool_migration": self._generate_tool_migration_context,
        "rollback_analysis": self._generate_rollback_context,
        }

        generator = context_generators.get(prompt_type, self._generate_default_context)
        return generator()

    def _generate_cost_context(self) -> Dict[str, Any]:
        """Generate context for cost reduction scenarios"""
        return {
    "current_costs": {
    "monthly_llm": random.uniform(5000, 20000),
    "monthly_compute": random.uniform(2000, 10000),
    "monthly_storage": random.uniform(500, 2000),
    },
    "usage_patterns": {
    "daily_requests": random.randint(10000, 100000),
    "peak_hour_requests": random.randint(1000, 10000),
    "average_tokens_per_request": random.randint(100, 1000),
    },
    "constraints": {
    "max_latency_ms": random.randint(200, 1000),
    "min_quality_score": random.uniform(0.8, 0.95),
    "budget_limit": random.uniform(10000, 50000),
    },
    "metadata": {
    "timestamp": datetime.now().isoformat(),
    "priority": random.choice(["high", "medium", "low"]),
    "department": random.choice(["engineering", "product", "operations"]),
    }
    }

    def _generate_latency_context(self) -> Dict[str, Any]:
        """Generate context for latency optimization scenarios"""
        return {
    "current_latencies": {
    "p50_ms": random.randint(100, 500),
    "p95_ms": random.randint(200, 1000),
    "p99_ms": random.randint(500, 2000),
    },
    "service_breakdown": {
    "llm_inference_ms": random.randint(50, 300),
    "preprocessing_ms": random.randint(10, 50),
    "postprocessing_ms": random.randint(10, 50),
    "network_ms": random.randint(20, 100),
    },
    "optimization_targets": {
    "target_p50_ms": random.randint(50, 200),
    "target_p95_ms": random.randint(100, 400),
    "acceptable_cost_increase_percent": random.uniform(0, 20),
    }
    }

    def _generate_capacity_context(self) -> Dict[str, Any]:
        """Generate context for capacity planning scenarios"""
        return {
    "current_capacity": {
    "max_concurrent_requests": random.randint(100, 1000),
    "daily_request_limit": random.randint(50000, 500000),
    "rate_limit_per_minute": random.randint(100, 1000),
    },
    "growth_projections": {
    "monthly_growth_percent": random.uniform(10, 50),
    "expected_peak_multiplier": random.uniform(1.5, 3.0),
    "seasonal_variation_percent": random.uniform(20, 100),
    },
    "resource_utilization": {
    "cpu_usage_percent": random.uniform(40, 80),
    "memory_usage_percent": random.uniform(30, 70),
    "gpu_usage_percent": random.uniform(50, 90),
    }
    }

    def _generate_function_context(self) -> Dict[str, Any]:
        """Generate context for function optimization scenarios"""
        return {
    "function_metrics": {
    "execution_time_ms": random.randint(100, 1000),
    "memory_usage_mb": random.randint(50, 500),
    "error_rate_percent": random.uniform(0.1, 5.0),
    },
    "dependencies": {
    "external_apis": random.randint(1, 5),
    "database_queries": random.randint(2, 10),
    "cache_hit_rate": random.uniform(0.5, 0.95),
    },
    "optimization_options": [
    "parallel_processing",
    "caching_strategy",
    "batch_processing",
    "async_operations",
    "query_optimization"
    ][:random.randint(2, 5)]
    }

    def _generate_model_context(self) -> Dict[str, Any]:
        """Generate context for model evaluation scenarios"""
        return {
    "current_models": {
    "primary": random.choice([LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "claude-2"]),
    "fallback": random.choice([LLMModel.GEMINI_2_5_FLASH.value, "claude-instant", "llama-2"]),
    },
    "performance_metrics": {
    "accuracy_score": random.uniform(0.7, 0.95),
    "latency_ms": random.randint(100, 500),
    "cost_per_1k_tokens": random.uniform(0.01, 0.10),
    },
    "evaluation_criteria": {
    "min_accuracy": random.uniform(0.8, 0.9),
    "max_latency_ms": random.randint(200, 600),
    "max_cost_per_request": random.uniform(0.05, 0.50),
    }
    }

    def _generate_audit_context(self) -> Dict[str, Any]:
        """Generate context for audit scenarios"""
        return {
    "system_components": {
    "total_services": random.randint(10, 50),
    "services_with_caching": random.randint(5, 30),
    "cache_configurations": random.randint(3, 10),
    },
    "cache_metrics": {
    "overall_hit_rate": random.uniform(0.4, 0.9),
    "memory_usage_gb": random.uniform(1, 50),
    "eviction_rate_per_hour": random.randint(100, 10000),
    },
    "optimization_opportunities": {
    "underutilized_caches": random.randint(0, 10),
    "oversized_caches": random.randint(0, 5),
    "inefficient_policies": random.randint(0, 8),
    }
    }

    def _generate_multi_objective_context(self) -> Dict[str, Any]:
        """Generate context for multi-objective optimization scenarios"""
        return {
    "objectives": {
    "cost_reduction_target_percent": random.uniform(10, 30),
    "latency_improvement_factor": random.uniform(1.5, 3.0),
    "capacity_increase_percent": random.uniform(20, 50),
    },
    "constraints": {
    "max_budget": random.uniform(10000, 100000),
    "min_quality_score": random.uniform(0.85, 0.95),
    "implementation_deadline_days": random.randint(30, 90),
    },
    "trade_offs": {
    "cost_vs_performance": random.uniform(0.3, 0.7),
    "quality_vs_speed": random.uniform(0.4, 0.6),
    "scalability_vs_simplicity": random.uniform(0.2, 0.8),
    }
    }

    def _generate_tool_migration_context(self) -> Dict[str, Any]:
        """Generate context for tool migration scenarios"""
        return {
    "current_tools": {
    "agent_count": random.randint(5, 20),
    "average_model": random.choice([LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "claude-2"]),
    "monthly_cost": random.uniform(5000, 20000),
    },
    "migration_candidates": {
    "new_model": "GPT-5",
    "expected_improvement_percent": random.uniform(20, 50),
    "migration_cost": random.uniform(1000, 5000),
    },
    "selection_criteria": {
    "min_improvement_threshold": random.uniform(15, 30),
    "max_migration_time_hours": random.randint(4, 24),
    "rollback_capability": True,
    }
    }

    def _generate_rollback_context(self) -> Dict[str, Any]:
        """Generate context for rollback analysis scenarios"""
        return {
    "upgrade_metrics": {
    "before_cost": random.uniform(5000, 15000),
    "after_cost": random.uniform(6000, 20000),
    "before_quality": random.uniform(0.8, 0.9),
    "after_quality": random.uniform(0.82, 0.95),
    "before_latency_ms": random.randint(200, 500),
    "after_latency_ms": random.randint(180, 450),
    },
    "affected_services": {
    "total_upgraded": random.randint(5, 15),
    "improved_significantly": random.randint(2, 8),
    "degraded_performance": random.randint(0, 3),
    "cost_increased": random.randint(3, 10),
    },
    "rollback_criteria": {
    "max_cost_increase_percent": random.uniform(10, 20),
    "min_quality_improvement_percent": random.uniform(5, 15),
    "performance_degradation_threshold": random.uniform(5, 10),
    }
    }

    def _generate_default_context(self) -> Dict[str, Any]:
        """Generate default context for unspecified prompt types"""
        return {
    "system_info": {
    "services_count": random.randint(10, 50),
    "daily_requests": random.randint(10000, 100000),
    "monthly_cost": random.uniform(5000, 50000),
    },
    "performance": {
    "average_latency_ms": random.randint(100, 500),
    "error_rate_percent": random.uniform(0.1, 2.0),
    "uptime_percent": random.uniform(99.0, 99.99),
    },
    "metadata": {
    "timestamp": datetime.now().isoformat(),
    "environment": random.choice(["production", "staging", "development"]),
    "region": random.choice(["us-east-1", "us-west-2", "eu-west-1"]),
    }
    }