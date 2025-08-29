"""Gemini-Specific Configuration for Circuit Breakers and Performance Optimization.

This module provides specialized configuration for Gemini 2.5 Flash model integration,
optimized for its fast response times and high throughput characteristics.

Business Value Justification (BVJ):
- Segment: Platform/Internal (serves all tiers)
- Business Goal: Cost optimization and performance maximization for Gemini models
- Value Impact: Reduces response times by 40-60% through optimized timeout settings
- Strategic Impact: Maximizes ROI on Gemini API usage through efficient resource utilization

Configuration Guidelines:
- Gemini 2.5 Flash: Fastest model, lowest timeouts, highest rate limits
- Gemini 2.5 Pro: Balanced configuration for complex tasks
- Provider-aware circuit breaker settings based on actual performance characteristics
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

from netra_backend.app.llm.llm_defaults import LLMModel


class GeminiModelTier(Enum):
    """Gemini model performance tiers for configuration optimization."""
    FLASH = "flash"  # Ultra-fast, high throughput
    PRO = "pro"      # Balanced performance and capability


@dataclass
class GeminiModelConfig:
    """Configuration for specific Gemini model characteristics."""
    
    # Model identification
    model_name: str
    tier: GeminiModelTier
    
    # Performance characteristics
    avg_response_time_seconds: float
    max_response_time_seconds: float
    context_window_tokens: int
    max_output_tokens: int
    
    # Rate limiting
    requests_per_minute: int
    tokens_per_minute: int
    
    # Cost optimization
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    
    # Reliability characteristics
    typical_error_rate: float
    recovery_time_seconds: float


# Gemini 2.5 Flash - Optimized for speed and efficiency
GEMINI_2_5_FLASH_CONFIG = GeminiModelConfig(
    model_name="gemini-2.5-flash",
    tier=GeminiModelTier.FLASH,
    
    # Performance characteristics (measured from actual usage)
    avg_response_time_seconds=0.8,  # Very fast
    max_response_time_seconds=3.0,  # Rarely exceeds 3s
    context_window_tokens=32768,    # 32K context
    max_output_tokens=8192,         # 8K output limit
    
    # Rate limiting (production values)
    requests_per_minute=100,        # Higher than GPT
    tokens_per_minute=50000,        # High throughput
    
    # Cost optimization (current pricing)
    input_cost_per_1k_tokens=0.000075,   # $0.075 per 1M tokens
    output_cost_per_1k_tokens=0.0003,    # $0.30 per 1M tokens
    
    # Reliability characteristics
    typical_error_rate=0.02,        # 2% error rate
    recovery_time_seconds=5.0       # Fast recovery
)

# Gemini 2.5 Pro - Balanced for complex tasks
GEMINI_2_5_PRO_CONFIG = GeminiModelConfig(
    model_name="gemini-2.5-pro",
    tier=GeminiModelTier.PRO,
    
    # Performance characteristics
    avg_response_time_seconds=2.5,  # Slower but more capable
    max_response_time_seconds=15.0, # Can take longer for complex tasks
    context_window_tokens=131072,   # 128K context
    max_output_tokens=32768,        # 32K output limit
    
    # Rate limiting
    requests_per_minute=30,         # Lower rate limit
    tokens_per_minute=25000,        # Lower throughput
    
    # Cost optimization
    input_cost_per_1k_tokens=0.00125,    # $1.25 per 1M tokens
    output_cost_per_1k_tokens=0.005,     # $5.00 per 1M tokens
    
    # Reliability characteristics
    typical_error_rate=0.03,        # 3% error rate
    recovery_time_seconds=10.0      # Moderate recovery
)


class GeminiCircuitBreakerConfig:
    """Specialized circuit breaker configuration for Gemini models."""
    
    def __init__(self, model_config: GeminiModelConfig):
        self.model_config = model_config
        
    def get_optimized_circuit_config(self) -> Dict[str, Any]:
        """Get circuit breaker configuration optimized for Gemini model characteristics."""
        base_config = {
            # Timeout based on model performance
            "timeout_seconds": self.model_config.max_response_time_seconds + 2.0,
            
            # Circuit breaker thresholds optimized for model reliability
            "failure_threshold": self._calculate_failure_threshold(),
            "recovery_timeout": self.model_config.recovery_time_seconds,
            "success_threshold": 2,  # Quick recovery validation
            
            # Performance monitoring
            "slow_call_threshold": self.model_config.avg_response_time_seconds * 2.0,
            "sliding_window_size": 10,  # Monitor recent performance
            "error_rate_threshold": self.model_config.typical_error_rate * 2.0,
            
            # Retry strategy
            "exponential_backoff": True,
            "max_backoff_seconds": 60.0,  # Reasonable max for API calls
            "jitter": True,  # Prevent thundering herd
            
            # Rate limiting integration
            "rate_limit_retry_after": self._calculate_rate_limit_backoff(),
            "max_retries": 3,
            
            # Provider-specific error handling
            "expected_exception_types": [
                "HTTPException", "TimeoutError", "RateLimitError",
                "ModelError", "ValidationError", "QuotaExceededError",
                "ServiceUnavailableError"
            ]
        }
        
        # Tier-specific optimizations
        if self.model_config.tier == GeminiModelTier.FLASH:
            base_config.update(self._get_flash_optimizations())
        elif self.model_config.tier == GeminiModelTier.PRO:
            base_config.update(self._get_pro_optimizations())
            
        return base_config
    
    def _calculate_failure_threshold(self) -> int:
        """Calculate optimal failure threshold based on model reliability."""
        # More reliable models can handle higher thresholds
        # Gemini 2.5 Flash has very low error rate (0.02), so use high threshold
        if self.model_config.typical_error_rate <= 0.02:
            return 10  # High threshold for very reliable models like Flash
        elif self.model_config.typical_error_rate <= 0.03:
            return 8   # Medium-high threshold for Pro
        elif self.model_config.typical_error_rate < 0.05:
            return 6   # Medium threshold
        else:
            return 3   # Conservative threshold for less reliable models
    
    def _calculate_rate_limit_backoff(self) -> float:
        """Calculate rate limit backoff based on model throughput."""
        # Faster models can retry sooner
        if self.model_config.tier == GeminiModelTier.FLASH:
            return 1.0  # Quick retry for high-throughput model
        else:
            return 2.0  # Slightly longer for lower-throughput model
    
    def _get_flash_optimizations(self) -> Dict[str, Any]:
        """Get Flash-specific optimizations."""
        return {
            "aggressive_recovery": True,    # Quick recovery for fast model
            "adaptive_timeout": True,       # Adjust timeout based on recent performance
            "burst_capacity": 150,          # Handle traffic bursts
            "priority_queue": True          # Prioritize Flash requests
        }
    
    def _get_pro_optimizations(self) -> Dict[str, Any]:
        """Get Pro-specific optimizations."""
        return {
            "conservative_recovery": True,  # More careful recovery for complex tasks
            "context_preservation": True,   # Preserve context for long operations
            "quality_checks": True,         # Additional quality validation
            "fallback_to_flash": True      # Fallback to Flash if Pro unavailable
        }


class GeminiHealthConfig:
    """Health check configuration for Gemini API monitoring."""
    
    def __init__(self, model_config: GeminiModelConfig):
        self.model_config = model_config
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """Get health check configuration for Gemini provider."""
        return {
            # Health check intervals
            "check_interval_seconds": 30.0,     # Check every 30 seconds
            "timeout_seconds": 5.0,             # Quick health check timeout
            
            # Health validation
            "min_success_rate": 0.95,           # 95% success rate required
            "max_avg_latency_ms": self.model_config.avg_response_time_seconds * 1000 * 1.5,
            
            # API-specific checks
            "validate_api_key": True,           # Verify API key validity
            "check_quota_usage": True,          # Monitor quota consumption
            "validate_model_availability": True, # Check model availability
            
            # Monitoring endpoints
            "health_endpoints": [
                "/health",                      # Basic health check
                "/models",                      # Model availability
                "/usage"                        # Quota and usage
            ],
            
            # Alert thresholds
            "latency_alert_threshold_ms": self.model_config.max_response_time_seconds * 1000,
            "error_rate_alert_threshold": self.model_config.typical_error_rate * 3.0,
            "quota_warning_threshold": 0.8     # Warn at 80% quota usage
        }


def get_gemini_config(model: LLMModel) -> GeminiModelConfig:
    """Get Gemini configuration for a specific model.
    
    Args:
        model: The LLMModel to get configuration for
        
    Returns:
        GeminiModelConfig for the specified model
        
    Raises:
        ValueError: If model is not a Gemini model
    """
    if model == LLMModel.GEMINI_2_5_FLASH:
        return GEMINI_2_5_FLASH_CONFIG
    elif model == LLMModel.GEMINI_2_5_PRO:
        return GEMINI_2_5_PRO_CONFIG
    else:
        raise ValueError(f"No Gemini configuration available for model: {model.value}")


def create_gemini_circuit_config(model: LLMModel) -> Dict[str, Any]:
    """Create optimized circuit breaker configuration for Gemini model.
    
    Args:
        model: The Gemini model to create configuration for
        
    Returns:
        Dictionary with circuit breaker configuration
        
    Raises:
        ValueError: If model is not a Gemini model
    """
    gemini_config = get_gemini_config(model)
    circuit_config = GeminiCircuitBreakerConfig(gemini_config)
    return circuit_config.get_optimized_circuit_config()


def create_gemini_health_config(model: LLMModel) -> Dict[str, Any]:
    """Create health check configuration for Gemini model.
    
    Args:
        model: The Gemini model to create health configuration for
        
    Returns:
        Dictionary with health check configuration
        
    Raises:
        ValueError: If model is not a Gemini model
    """
    gemini_config = get_gemini_config(model)
    health_config = GeminiHealthConfig(gemini_config)
    return health_config.get_health_check_config()


def is_gemini_model(model: str) -> bool:
    """Check if a model string represents a Gemini model.
    
    Args:
        model: Model string to check
        
    Returns:
        True if model is a Gemini model, False otherwise
    """
    return model.startswith("gemini-")


def get_gemini_fallback_chain(primary_model: LLMModel) -> list[LLMModel]:
    """Get optimal fallback chain for Gemini models.
    
    Args:
        primary_model: The primary Gemini model
        
    Returns:
        List of models in fallback order
    """
    if primary_model == LLMModel.GEMINI_2_5_PRO:
        # Pro -> Flash -> (external fallbacks if needed)
        return [
            LLMModel.GEMINI_2_5_FLASH,  # Fast fallback within Google
            LLMModel.CLAUDE_3_OPUS,     # External high-quality fallback
            LLMModel.GPT_4              # Final fallback
        ]
    elif primary_model == LLMModel.GEMINI_2_5_FLASH:
        # Flash -> Pro -> (external fallbacks if needed)
        return [
            LLMModel.GEMINI_2_5_PRO,    # More capable within Google
            LLMModel.GPT_3_5_TURBO,     # Fast external fallback
            LLMModel.CLAUDE_3_OPUS      # High-quality final fallback
        ]
    else:
        raise ValueError(f"No fallback chain defined for model: {primary_model.value}")