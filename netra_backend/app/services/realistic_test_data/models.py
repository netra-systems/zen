"""Realistic Test Data Models and Configuration

This module defines models, enums, and configuration data for realistic test data generation.
"""

from enum import Enum
from typing import Any, Dict, List, Tuple
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig



class RealisticDataPatterns(Enum):
    """Realistic data generation patterns"""
    LLM_RESPONSES = "llm_responses"
    LOG_PATTERNS = "log_patterns"
    PERFORMANCE_METRICS = "performance_metrics"
    ERROR_CASCADES = "error_cascades"
    WORKLOAD_PATTERNS = "workload_patterns"


class RealisticTestDataConfigManager:
    """Manages configuration data for realistic test generation"""
    
    def __init__(self):
        """Initialize configuration manager"""
        self.llm_models = self._init_llm_models()
        self.log_patterns = self._init_log_patterns()
        self.error_patterns = self._init_error_patterns()
    
    def _init_llm_models(self) -> Dict[str, Dict[str, Any]]:
        """Initialize realistic LLM model characteristics"""
        return {
            LLMModel.GEMINI_2_5_FLASH.value: {
                "latency_range_ms": (500, 30000),
                "latency_distribution": "lognormal",
                "token_limits": {"input": 8192, "output": 4096},
                "cost_per_1k_input": 0.03,
                "cost_per_1k_output": 0.06,
                "error_rate": 0.002,
                "rate_limit": 10000,  # per minute
                "timeout_rate": 0.001
            },
            LLMModel.GEMINI_2_5_FLASH.value: {
                "latency_range_ms": (300, 15000),
                "latency_distribution": "lognormal",
                "token_limits": {"input": 128000, "output": 4096},
                "cost_per_1k_input": 0.01,
                "cost_per_1k_output": 0.03,
                "error_rate": 0.001,
                "rate_limit": 50000,
                "timeout_rate": 0.0005
            },
            LLMModel.GEMINI_2_5_FLASH.value: {
                "latency_range_ms": (400, 25000),
                "latency_distribution": "gamma",
                "token_limits": {"input": 200000, "output": 4096},
                "cost_per_1k_input": 0.015,
                "cost_per_1k_output": 0.075,
                "error_rate": 0.0015,
                "rate_limit": 5000,
                "timeout_rate": 0.001
            },
            "gemini-pro": {
                "latency_range_ms": (200, 10000),
                "latency_distribution": "normal",
                "token_limits": {"input": 30720, "output": 2048},
                "cost_per_1k_input": 0.00025,
                "cost_per_1k_output": 0.0005,
                "error_rate": 0.003,
                "rate_limit": 60000,
                "timeout_rate": 0.002
            },
            "llama-2-70b": {
                "latency_range_ms": (100, 5000),
                "latency_distribution": "exponential",
                "token_limits": {"input": 4096, "output": 2048},
                "cost_per_1k_input": 0.0007,
                "cost_per_1k_output": 0.0009,
                "error_rate": 0.005,
                "rate_limit": 100000,
                "timeout_rate": 0.003
            }
        }
    
    def _init_log_patterns(self) -> List[Dict[str, Any]]:
        """Initialize realistic log patterns"""
        return [
            {
                "pattern": "memory_leak",
                "signature": "gradual_increase",
                "indicators": ["heap size", "GC frequency", "response time degradation"]
            },
            {
                "pattern": "error_cascade",
                "signature": "exponential_spread",
                "indicators": ["connection refused", "timeout", "service unavailable"]
            },
            {
                "pattern": "performance_degradation",
                "signature": "linear_decline",
                "indicators": ["p99 latency", "throughput", "error rate"]
            },
            {
                "pattern": "normal_operation",
                "signature": "stable_with_noise",
                "indicators": ["consistent latency", "low error rate", "predictable patterns"]
            }
        ]
    
    def _init_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize realistic error patterns"""
        return {
            "rate_limiting": {
                "error_code": 429,
                "message": "Rate limit exceeded",
                "retry_after": (1, 60),
                "occurrence_rate": 0.05
            },
            "token_limit": {
                "error_code": 400,
                "message": "Maximum token limit exceeded",
                "occurrence_rate": 0.02
            },
            "service_unavailable": {
                "error_code": 503,
                "message": "Service temporarily unavailable",
                "retry_after": (5, 300),
                "occurrence_rate": 0.001
            },
            "malformed_response": {
                "error_code": 500,
                "message": "Failed to parse LLM response",
                "occurrence_rate": 0.003
            },
            "timeout": {
                "error_code": 408,
                "message": "Request timeout",
                "occurrence_rate": 0.01
            }
        }
    
    def get_llm_model_config(self, model: str) -> Dict[str, Any]:
        """Get configuration for specific LLM model"""
        return self.llm_models.get(model, self.llm_models[LLMModel.GEMINI_2_5_FLASH.value])
    
    def get_log_pattern_config(self, pattern: str) -> Dict[str, Any]:
        """Get configuration for specific log pattern"""
        return next(
            (p for p in self.log_patterns if p["pattern"] == pattern),
            self.log_patterns[3]  # Default to normal_operation
        )
    
    def get_error_pattern_config(self, pattern: str) -> Dict[str, Any]:
        """Get configuration for specific error pattern"""
        return self.error_patterns.get(pattern, {})