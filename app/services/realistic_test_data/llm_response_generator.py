"""LLM Response Generator

This module generates realistic LLM responses with production-like characteristics.
"""

import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import numpy as np

from .models import ConfigManager


class LLMResponseGenerator:
    """Generates realistic LLM responses"""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize LLM response generator"""
        self.config = config_manager
    
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
        model_config = self.config.get_llm_model_config(model)
        
        # Generate token counts
        if prompt_tokens is None:
            prompt_tokens = random.randint(50, min(2000, model_config["token_limits"]["input"]))
        
        completion_tokens = random.randint(
            10,
            min(1000, model_config["token_limits"]["output"])
        )
        
        # Check for errors
        if include_errors and random.random() < model_config["error_rate"]:
            return self._generate_error_response(model, prompt_tokens)
        
        # Generate successful response
        return self._generate_success_response(model, model_config, prompt_tokens, completion_tokens)
    
    def _generate_error_response(self, model: str, prompt_tokens: int) -> Dict[str, Any]:
        """Generate an error response"""
        error_type = random.choice(list(self.config.error_patterns.keys()))
        error_config = self.config.error_patterns[error_type]
        
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
    
    def _generate_success_response(
        self,
        model: str,
        model_config: Dict[str, Any],
        prompt_tokens: int,
        completion_tokens: int
    ) -> Dict[str, Any]:
        """Generate a successful response"""
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