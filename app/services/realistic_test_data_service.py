"""
Realistic Test Data Service
Generates production-like test data for comprehensive testing
Addresses gaps identified in test_realism_analysis_20250811.md
"""

import random
import json
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import numpy as np

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RealisticDataPatterns(Enum):
    """Realistic data generation patterns"""
    LLM_RESPONSES = "llm_responses"
    LOG_PATTERNS = "log_patterns"
    PERFORMANCE_METRICS = "performance_metrics"
    ERROR_CASCADES = "error_cascades"
    WORKLOAD_PATTERNS = "workload_patterns"


class RealisticTestDataService:
    """Service for generating realistic test data that mimics production patterns"""
    
    def __init__(self):
        self.llm_models = self._init_llm_models()
        self.log_patterns = self._init_log_patterns()
        self.error_patterns = self._init_error_patterns()
        
    def _init_llm_models(self) -> Dict[str, Dict[str, Any]]:
        """Initialize realistic LLM model characteristics"""
        return {
            "gpt-4": {
                "latency_range_ms": (500, 30000),
                "latency_distribution": "lognormal",
                "token_limits": {"input": 8192, "output": 4096},
                "cost_per_1k_input": 0.03,
                "cost_per_1k_output": 0.06,
                "error_rate": 0.002,
                "rate_limit": 10000,  # per minute
                "timeout_rate": 0.001
            },
            "gpt-4-turbo": {
                "latency_range_ms": (300, 15000),
                "latency_distribution": "lognormal",
                "token_limits": {"input": 128000, "output": 4096},
                "cost_per_1k_input": 0.01,
                "cost_per_1k_output": 0.03,
                "error_rate": 0.001,
                "rate_limit": 50000,
                "timeout_rate": 0.0005
            },
            "claude-3-opus": {
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
    
    def generate_realistic_llm_response(
        self,
        model: str = "gpt-4",
        prompt_tokens: Optional[int] = None,
        include_errors: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a realistic LLM response with production-like characteristics
        
        Args:
            model: LLM model name
            prompt_tokens: Number of input tokens (auto-generated if None)
            include_errors: Whether to include realistic errors
            
        Returns:
            Realistic LLM response data
        """
        model_config = self.llm_models.get(model, self.llm_models["gpt-4"])
        
        # Generate token counts
        if prompt_tokens is None:
            prompt_tokens = random.randint(50, min(2000, model_config["token_limits"]["input"]))
        
        completion_tokens = random.randint(
            10,
            min(1000, model_config["token_limits"]["output"])
        )
        
        # Check for errors
        if include_errors and random.random() < model_config["error_rate"]:
            error_type = random.choice(list(self.error_patterns.keys()))
            error_config = self.error_patterns[error_type]
            
            return {
                "success": False,
                "error": {
                    "type": error_type,
                    "code": error_config["error_code"],
                    "message": error_config["message"],
                    "retry_after": random.randint(*error_config.get("retry_after", (0, 0)))
                },
                "model": model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": 0,
                "total_tokens": prompt_tokens,
                "cost_usd": 0
            }
        
        # Generate latency based on distribution
        latency_ms = self._generate_latency(
            model_config["latency_range_ms"],
            model_config["latency_distribution"]
        )
        
        # Calculate cost
        cost_usd = (
            (prompt_tokens / 1000) * model_config["cost_per_1k_input"] +
            (completion_tokens / 1000) * model_config["cost_per_1k_output"]
        )
        
        # Generate realistic response content
        response_content = self._generate_response_content(completion_tokens)
        
        return {
            "success": True,
            "model": model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
            "cost_usd": round(cost_usd, 6),
            "response": response_content,
            "finish_reason": random.choice(["stop", "length", "stop"]),  # More "stop" than "length"
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        }
    
    def _generate_latency(self, range_ms: Tuple[int, int], distribution: str) -> int:
        """Generate realistic latency based on distribution type"""
        min_ms, max_ms = range_ms
        
        if distribution == "lognormal":
            # Log-normal distribution (most requests fast, some very slow)
            mean = np.log(min_ms * 2)
            sigma = 0.8
            latency = np.random.lognormal(mean, sigma)
            return int(min(max(latency, min_ms), max_ms))
        
        elif distribution == "gamma":
            # Gamma distribution (right-skewed)
            shape = 2.0
            scale = (max_ms - min_ms) / 10
            latency = min_ms + np.random.gamma(shape, scale)
            return int(min(latency, max_ms))
        
        elif distribution == "exponential":
            # Exponential distribution (many fast, few slow)
            scale = (max_ms - min_ms) / 5
            latency = min_ms + np.random.exponential(scale)
            return int(min(latency, max_ms))
        
        else:  # normal
            # Normal distribution with some skew
            mean = min_ms * 3
            std = (max_ms - min_ms) / 6
            latency = np.random.normal(mean, std)
            return int(min(max(latency, min_ms), max_ms))
    
    def _generate_response_content(self, token_count: int) -> str:
        """Generate realistic response content based on token count"""
        # Approximate 1 token = 4 characters
        char_count = token_count * 4
        
        templates = [
            "Based on the analysis of your AI workload, I've identified several optimization opportunities. ",
            "The current configuration shows potential for improvement in the following areas: ",
            "After examining the performance metrics, here are my recommendations: ",
            "The system analysis reveals the following insights: "
        ]
        
        content = random.choice(templates)
        
        # Add realistic content based on token count
        if token_count > 500:
            content += self._generate_detailed_analysis()
        elif token_count > 100:
            content += self._generate_summary_analysis()
        else:
            content += self._generate_brief_response()
        
        # Truncate to approximate character count
        return content[:char_count]
    
    def _generate_detailed_analysis(self) -> str:
        """Generate detailed analysis content"""
        return """
        1. **Resource Utilization Analysis**
           - GPU utilization averaging 67% with peaks at 95%
           - Memory usage shows gradual increase pattern
           - CPU bottleneck detected during data preprocessing
        
        2. **Cost Optimization Opportunities**
           - Switch to spot instances for batch workloads (30% savings)
           - Implement request batching for 40% throughput improvement
           - Consider model quantization for inference optimization
        
        3. **Performance Recommendations**
           - Enable tensor parallelism for large models
           - Implement gradient checkpointing to reduce memory
           - Use mixed precision training for 2x speedup
        
        4. **Scaling Considerations**
           - Current setup can handle 10x load with modifications
           - Recommend horizontal scaling for API endpoints
           - Database connection pooling needs adjustment
        """
    
    def _generate_summary_analysis(self) -> str:
        """Generate summary analysis content"""
        return """
        Key findings: Your AI workloads show 30% optimization potential.
        Main bottlenecks: Memory allocation and network I/O.
        Quick wins: Enable caching, batch requests, optimize prompts.
        Estimated savings: $2,400/month with recommended changes.
        """
    
    def _generate_brief_response(self) -> str:
        """Generate brief response content"""
        responses = [
            "Analysis complete. 3 optimization opportunities identified.",
            "Workload optimized. Performance improved by 25%.",
            "Configuration updated successfully.",
            "Error rate reduced from 2.3% to 0.8%.",
            "Cost savings of $1,200/month achieved."
        ]
        return random.choice(responses)
    
    def generate_realistic_log_data(
        self,
        pattern: str = "normal_operation",
        duration_hours: int = 24,
        volume: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic log data with specific patterns
        
        Args:
            pattern: Type of log pattern to generate
            duration_hours: Time span for logs
            volume: Number of log entries
            
        Returns:
            List of realistic log entries
        """
        logs = []
        start_time = datetime.now(timezone.utc) - timedelta(hours=duration_hours)
        time_increment = timedelta(hours=duration_hours) / volume
        
        pattern_config = next(
            (p for p in self.log_patterns if p["pattern"] == pattern),
            self.log_patterns[3]  # Default to normal_operation
        )
        
        for i in range(volume):
            timestamp = start_time + (time_increment * i)
            
            log_entry = {
                "timestamp": timestamp.isoformat(),
                "level": self._select_log_level(pattern, i, volume),
                "service": random.choice(["api", "worker", "scheduler", "agent", "database"]),
                "message": self._generate_log_message(pattern, i, volume),
                "metrics": self._generate_log_metrics(pattern, i, volume, pattern_config)
            }
            
            # Add trace information
            if random.random() < 0.3:
                log_entry["trace_id"] = str(uuid.uuid4())
                log_entry["span_id"] = str(uuid.uuid4())[:8]
            
            logs.append(log_entry)
        
        return logs
    
    def _select_log_level(self, pattern: str, index: int, total: int) -> str:
        """Select appropriate log level based on pattern"""
        if pattern == "error_cascade":
            # Increasing error rate
            error_probability = (index / total) * 0.8
            if random.random() < error_probability:
                return random.choice(["ERROR", "CRITICAL"])
            elif random.random() < 0.3:
                return "WARNING"
            else:
                return "INFO"
        
        elif pattern == "memory_leak":
            # Increasing warnings
            if index > total * 0.7:
                return random.choice(["WARNING", "ERROR"])
            else:
                return random.choice(["INFO", "DEBUG"])
        
        else:  # normal_operation
            weights = [0.7, 0.2, 0.08, 0.02]  # INFO, DEBUG, WARNING, ERROR
            return random.choices(
                ["INFO", "DEBUG", "WARNING", "ERROR"],
                weights=weights
            )[0]
    
    def _generate_log_message(self, pattern: str, index: int, total: int) -> str:
        """Generate realistic log message based on pattern"""
        if pattern == "error_cascade":
            if index < total * 0.3:
                return random.choice([
                    "Request processed successfully",
                    "Cache hit for query",
                    "Model inference completed"
                ])
            elif index < total * 0.6:
                return random.choice([
                    "Connection pool exhausted, queuing request",
                    "Retry attempt 1 of 3",
                    "Upstream service responding slowly"
                ])
            else:
                return random.choice([
                    "Connection refused: Too many connections",
                    "Circuit breaker opened for service",
                    "Cascading failure detected",
                    "Emergency shutdown initiated"
                ])
        
        elif pattern == "memory_leak":
            base_messages = [
                f"Heap size: {1000 + (index * 10)}MB",
                f"GC pause: {50 + (index / total * 500)}ms",
                f"Active connections: {100 + (index // 10)}",
                "Memory allocation failed, retrying"
            ]
            return random.choice(base_messages)
        
        else:
            return random.choice([
                "Request processed in 45ms",
                "Model loaded successfully",
                "Batch processing completed",
                "Cache refreshed",
                "Health check passed",
                "Metrics exported",
                "Configuration reloaded"
            ])
    
    def _generate_log_metrics(
        self,
        pattern: str,
        index: int,
        total: int,
        pattern_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """Generate metrics that follow the pattern"""
        progress = index / total
        
        if pattern == "memory_leak":
            return {
                "memory_mb": 500 + (progress * 3000),  # Gradual increase
                "gc_count": int(10 + progress * 100),
                "response_time_ms": 50 + (progress * 200),  # Degrading
                "cpu_percent": min(20 + (progress * 60), 95)
            }
        
        elif pattern == "error_cascade":
            error_rate = 0.01 if progress < 0.3 else min(progress * 0.5, 0.8)
            return {
                "error_rate": error_rate,
                "success_rate": 1 - error_rate,
                "response_time_ms": 100 * (1 + progress * 5),  # Exponential degradation
                "queue_depth": int(10 * (1 + progress ** 2 * 100))
            }
        
        elif pattern == "performance_degradation":
            return {
                "p50_latency_ms": 50 + (progress * 50),
                "p95_latency_ms": 150 + (progress * 300),
                "p99_latency_ms": 300 + (progress * 700),
                "throughput_rps": max(1000 - (progress * 800), 100),
                "error_rate": min(0.01 + (progress * 0.1), 0.15)
            }
        
        else:  # normal_operation
            # Add realistic noise
            return {
                "response_time_ms": 50 + random.gauss(0, 10),
                "throughput_rps": 1000 + random.gauss(0, 50),
                "error_rate": max(0, 0.01 + random.gauss(0, 0.002)),
                "cpu_percent": 40 + random.gauss(0, 5),
                "memory_mb": 2000 + random.gauss(0, 100)
            }
    
    def generate_workload_simulation(
        self,
        workload_type: str = "ecommerce",
        duration_days: int = 7,
        include_seasonality: bool = True
    ) -> Dict[str, Any]:
        """
        Generate complete workload simulation data
        
        Args:
            workload_type: Type of workload (ecommerce, financial, healthcare, etc.)
            duration_days: Duration of simulation
            include_seasonality: Whether to include time-based patterns
            
        Returns:
            Complete workload simulation data
        """
        workload_configs = {
            "ecommerce": {
                "peak_hours": [10, 14, 19, 20, 21],
                "weekend_multiplier": 1.5,
                "models": ["gpt-4", "gpt-4-turbo", "claude-3-opus"],
                "request_distribution": {"search": 0.4, "chat": 0.3, "recommend": 0.3}
            },
            "financial": {
                "peak_hours": [9, 10, 11, 14, 15],
                "weekend_multiplier": 0.3,
                "models": ["gpt-4", "claude-3-opus"],
                "request_distribution": {"analysis": 0.5, "compliance": 0.3, "reporting": 0.2}
            },
            "healthcare": {
                "peak_hours": [8, 9, 10, 11, 14, 15, 16],
                "weekend_multiplier": 0.5,
                "models": ["gpt-4", "gemini-pro"],
                "request_distribution": {"diagnosis": 0.4, "research": 0.4, "admin": 0.2}
            }
        }
        
        config = workload_configs.get(workload_type, workload_configs["ecommerce"])
        
        # Generate time series data
        data_points = []
        start_time = datetime.now(timezone.utc) - timedelta(days=duration_days)
        
        for day in range(duration_days):
            for hour in range(24):
                timestamp = start_time + timedelta(days=day, hours=hour)
                
                # Calculate load multiplier
                load_multiplier = 1.0
                
                # Hour of day pattern
                if hour in config["peak_hours"]:
                    load_multiplier *= random.uniform(2.0, 3.5)
                elif 6 <= hour <= 22:
                    load_multiplier *= random.uniform(0.8, 1.2)
                else:
                    load_multiplier *= random.uniform(0.2, 0.4)
                
                # Day of week pattern
                if include_seasonality:
                    if timestamp.weekday() >= 5:  # Weekend
                        load_multiplier *= config["weekend_multiplier"]
                
                # Generate requests for this hour
                base_requests = random.randint(100, 200)
                total_requests = int(base_requests * load_multiplier)
                
                # Distribute across request types
                for request_type, weight in config["request_distribution"].items():
                    request_count = int(total_requests * weight)
                    
                    for _ in range(request_count):
                        model = random.choice(config["models"])
                        
                        data_points.append({
                            "timestamp": timestamp.isoformat(),
                            "workload_type": workload_type,
                            "request_type": request_type,
                            "model": model,
                            **self.generate_realistic_llm_response(model, include_errors=True)
                        })
        
        return {
            "workload_type": workload_type,
            "duration_days": duration_days,
            "total_requests": len(data_points),
            "data_points": data_points,
            "summary": self._generate_workload_summary(data_points)
        }
    
    def _generate_workload_summary(self, data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for workload"""
        successful = [d for d in data_points if d.get("success", False)]
        failed = [d for d in data_points if not d.get("success", False)]
        
        if successful:
            latencies = [d["latency_ms"] for d in successful]
            costs = [d["cost_usd"] for d in successful]
            tokens = [d["total_tokens"] for d in successful]
            
            return {
                "total_requests": len(data_points),
                "successful_requests": len(successful),
                "failed_requests": len(failed),
                "error_rate": len(failed) / len(data_points) if data_points else 0,
                "avg_latency_ms": np.mean(latencies),
                "p50_latency_ms": np.percentile(latencies, 50),
                "p95_latency_ms": np.percentile(latencies, 95),
                "p99_latency_ms": np.percentile(latencies, 99),
                "total_cost_usd": sum(costs),
                "avg_cost_per_request": np.mean(costs),
                "total_tokens": sum(tokens),
                "avg_tokens_per_request": np.mean(tokens)
            }
        
        return {
            "total_requests": len(data_points),
            "successful_requests": 0,
            "failed_requests": len(failed),
            "error_rate": 1.0
        }


# Global instance
realistic_test_data_service = RealisticTestDataService()