"""Gemini API Health Checker Implementation.

This module provides comprehensive health monitoring for Gemini API integration,
including API availability, quota usage, latency patterns, and provider-specific
error monitoring optimized for Gemini 2.5 Flash characteristics.

Business Value Justification (BVJ):
- Segment: Platform/Internal (serves all tiers)
- Business Goal: Proactive reliability monitoring and cost optimization
- Value Impact: Prevents service outages, optimizes API usage patterns
- Strategic Impact: Ensures 99.9% uptime for Gemini-powered features
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum
import aiohttp

from netra_backend.app.core.shared_health_types import HealthChecker, HealthStatus
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.llm.llm_defaults import LLMModel
from netra_backend.app.llm.gemini_config import (
    get_gemini_config, 
    create_gemini_health_config,
    is_gemini_model
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class GeminiHealthStatus(Enum):
    """Gemini-specific health status levels."""
    OPTIMAL = "optimal"           # All systems performing excellently
    HEALTHY = "healthy"           # Normal operation
    DEGRADED = "degraded"         # Some performance issues
    CRITICAL = "critical"         # Severe issues requiring attention
    UNAVAILABLE = "unavailable"   # Service not reachable


@dataclass
class GeminiHealthMetrics:
    """Comprehensive health metrics for Gemini API."""
    
    # API Connectivity
    api_available: bool
    api_response_time_ms: float
    api_key_valid: bool
    
    # Model Availability
    model_available: bool
    model_name: str
    model_version: Optional[str]
    
    # Performance Metrics
    avg_latency_ms: float
    p95_latency_ms: float
    success_rate: float
    error_rate: float
    
    # Quota and Usage
    quota_remaining: Optional[int]
    quota_limit: Optional[int]
    quota_reset_time: Optional[int]
    daily_usage: Optional[int]
    
    # Error Analysis
    recent_errors: List[Dict[str, Any]]
    error_patterns: Dict[str, int]
    
    # Provider-Specific
    region: Optional[str]
    service_status: str
    rate_limit_status: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            'api_available': self.api_available,
            'api_response_time_ms': self.api_response_time_ms,
            'api_key_valid': self.api_key_valid,
            'model_available': self.model_available,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'avg_latency_ms': self.avg_latency_ms,
            'p95_latency_ms': self.p95_latency_ms,
            'success_rate': self.success_rate,
            'error_rate': self.error_rate,
            'quota_remaining': self.quota_remaining,
            'quota_limit': self.quota_limit,
            'quota_reset_time': self.quota_reset_time,
            'daily_usage': self.daily_usage,
            'recent_errors': self.recent_errors,
            'error_patterns': dict(self.error_patterns),
            'region': self.region,
            'service_status': self.service_status,
            'rate_limit_status': self.rate_limit_status
        }


class GeminiHealthChecker(HealthChecker):
    """Comprehensive health checker for Gemini API services."""
    
    def __init__(
        self, 
        model: LLMModel = LLMModel.GEMINI_2_5_FLASH,
        check_interval_seconds: float = 30.0
    ):
        """Initialize Gemini health checker.
        
        Args:
            model: Gemini model to monitor health for
            check_interval_seconds: How often to perform health checks
        """
        self.model = model
        self.check_interval = check_interval_seconds
        self.env = IsolatedEnvironment()
        
        # Load model-specific configuration
        try:
            self.model_config = get_gemini_config(model)
            self.health_config = create_gemini_health_config(model)
        except ValueError as e:
            logger.error(f"Failed to load Gemini config for {model}: {e}")
            raise
        
        # Health tracking
        self._last_check_time = 0.0
        self._health_history: List[GeminiHealthMetrics] = []
        self._current_status = GeminiHealthStatus.HEALTHY
        self._api_key = None
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Performance tracking
        self._latency_samples: List[float] = []
        self._error_counts: Dict[str, int] = {}
        
    async def check_health(self) -> HealthStatus:
        """Perform comprehensive health check for Gemini API.
        
        Returns:
            HealthStatus indicating current health state
        """
        try:
            # Ensure we have API session
            await self._ensure_session()
            
            # Perform all health checks concurrently
            results = await asyncio.gather(
                self._check_api_connectivity(),
                self._check_model_availability(),
                self._check_quota_status(),
                self._check_performance_metrics(),
                return_exceptions=True
            )
            
            # Process results
            api_connectivity = results[0] if not isinstance(results[0], Exception) else False
            model_availability = results[1] if not isinstance(results[1], Exception) else False
            quota_info = results[2] if not isinstance(results[2], Exception) else {}
            perf_metrics = results[3] if not isinstance(results[3], Exception) else {}
            
            # Create comprehensive metrics
            metrics = await self._create_health_metrics(
                api_connectivity, model_availability, quota_info, perf_metrics
            )
            
            # Update health history
            self._health_history.append(metrics)
            if len(self._health_history) > 100:  # Keep last 100 entries
                self._health_history.pop(0)
            
            # Determine overall health status
            health_status = self._evaluate_health_status(metrics)
            self._current_status = health_status
            self._last_check_time = time.time()
            
            return self._convert_to_health_status(health_status, metrics)
            
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return HealthStatus.UNHEALTHY
    
    async def _ensure_session(self) -> None:
        """Ensure we have an active HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.health_config.get("timeout_seconds", 5.0)
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Load API key if not already loaded
        if self._api_key is None:
            self._api_key = self.env.get("GOOGLE_API_KEY")
            if not self._api_key:
                logger.warning("No GOOGLE_API_KEY found in environment")
    
    async def _check_api_connectivity(self) -> bool:
        """Check basic API connectivity and response time.
        
        Returns:
            True if API is reachable and responsive
        """
        if not self._api_key:
            return False
        
        try:
            start_time = time.time()
            
            # Use a simple API endpoint to test connectivity
            url = "https://generativelanguage.googleapis.com/v1/models"
            headers = {"Authorization": f"Bearer {self._api_key}"}
            
            async with self._session.get(url, headers=headers) as response:
                response_time_ms = (time.time() - start_time) * 1000
                self._latency_samples.append(response_time_ms)
                
                # Keep only recent latency samples
                if len(self._latency_samples) > 50:
                    self._latency_samples.pop(0)
                
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Gemini API connectivity check failed: {e}")
            self._error_counts["connectivity"] = self._error_counts.get("connectivity", 0) + 1
            return False
    
    async def _check_model_availability(self) -> bool:
        """Check if the specific Gemini model is available.
        
        Returns:
            True if model is available for use
        """
        if not self._api_key:
            return False
        
        try:
            # Check model-specific availability
            model_name = self.model_config.model_name
            url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}"
            headers = {"Authorization": f"Bearer {self._api_key}"}
            
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    model_info = await response.json()
                    # Check if model is actually usable
                    return model_info.get("supportedGenerationMethods", []) != []
                else:
                    logger.warning(f"Model {model_name} not available: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Gemini model availability check failed: {e}")
            self._error_counts["model_availability"] = self._error_counts.get("model_availability", 0) + 1
            return False
    
    async def _check_quota_status(self) -> Dict[str, Any]:
        """Check API quota and usage status.
        
        Returns:
            Dictionary with quota information
        """
        if not self._api_key:
            return {}
        
        try:
            # Note: This is a placeholder - actual quota API endpoints may differ
            # Google's quota API endpoints are not always publicly documented
            url = "https://generativelanguage.googleapis.com/v1/usage"
            headers = {"Authorization": f"Bearer {self._api_key}"}
            
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    # If quota endpoint not available, return default info
                    logger.debug(f"Quota endpoint not available: {response.status}")
                    return {
                        "quota_remaining": None,
                        "quota_limit": None,
                        "status": "unknown"
                    }
                    
        except Exception as e:
            logger.debug(f"Quota check failed (this may be normal): {e}")
            return {"status": "unavailable"}
    
    async def _check_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics from recent samples.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self._latency_samples:
            return {"avg_latency_ms": 0.0, "p95_latency_ms": 0.0}
        
        # Calculate statistics
        sorted_samples = sorted(self._latency_samples)
        avg_latency = sum(sorted_samples) / len(sorted_samples)
        p95_index = int(0.95 * len(sorted_samples))
        p95_latency = sorted_samples[p95_index] if p95_index < len(sorted_samples) else sorted_samples[-1]
        
        return {
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "sample_count": len(sorted_samples)
        }
    
    async def _create_health_metrics(
        self, 
        api_connectivity: bool,
        model_availability: bool,
        quota_info: Dict[str, Any],
        perf_metrics: Dict[str, float]
    ) -> GeminiHealthMetrics:
        """Create comprehensive health metrics from check results.
        
        Args:
            api_connectivity: Whether API is reachable
            model_availability: Whether model is available
            quota_info: Quota and usage information
            perf_metrics: Performance metrics
            
        Returns:
            GeminiHealthMetrics with all health information
        """
        # Calculate error rates
        total_checks = sum(self._error_counts.values()) + len(self._health_history)
        total_errors = sum(self._error_counts.values())
        error_rate = total_errors / max(total_checks, 1)
        success_rate = 1.0 - error_rate
        
        return GeminiHealthMetrics(
            # API Connectivity
            api_available=api_connectivity,
            api_response_time_ms=perf_metrics.get("avg_latency_ms", 0.0),
            api_key_valid=self._api_key is not None,
            
            # Model Availability
            model_available=model_availability,
            model_name=self.model_config.model_name,
            model_version=None,  # Would need specific API call to get version
            
            # Performance Metrics
            avg_latency_ms=perf_metrics.get("avg_latency_ms", 0.0),
            p95_latency_ms=perf_metrics.get("p95_latency_ms", 0.0),
            success_rate=success_rate,
            error_rate=error_rate,
            
            # Quota and Usage
            quota_remaining=quota_info.get("quota_remaining"),
            quota_limit=quota_info.get("quota_limit"),
            quota_reset_time=quota_info.get("quota_reset_time"),
            daily_usage=quota_info.get("daily_usage"),
            
            # Error Analysis
            recent_errors=[],  # Could be populated from error logs
            error_patterns=dict(self._error_counts),
            
            # Provider-Specific
            region=None,  # Would need to detect from API response
            service_status="operational" if api_connectivity else "degraded",
            rate_limit_status="normal"  # Could be enhanced with rate limit detection
        )
    
    def _evaluate_health_status(self, metrics: GeminiHealthMetrics) -> GeminiHealthStatus:
        """Evaluate overall health status based on metrics.
        
        Args:
            metrics: Current health metrics
            
        Returns:
            GeminiHealthStatus representing overall health
        """
        # Critical issues
        if not metrics.api_available or not metrics.model_available:
            return GeminiHealthStatus.UNAVAILABLE
        
        if not metrics.api_key_valid:
            return GeminiHealthStatus.CRITICAL
        
        # Performance-based evaluation
        if metrics.error_rate > 0.1:  # More than 10% error rate
            return GeminiHealthStatus.CRITICAL
        elif metrics.error_rate > 0.05:  # More than 5% error rate
            return GeminiHealthStatus.DEGRADED
        
        # Latency-based evaluation
        max_acceptable_latency = self.health_config.get("max_avg_latency_ms", 5000)
        if metrics.avg_latency_ms > max_acceptable_latency:
            return GeminiHealthStatus.DEGRADED
        
        # Quota-based evaluation
        if metrics.quota_remaining is not None and metrics.quota_limit is not None:
            quota_ratio = metrics.quota_remaining / metrics.quota_limit
            if quota_ratio < 0.1:  # Less than 10% quota remaining
                return GeminiHealthStatus.DEGRADED
        
        # Optimal vs healthy distinction
        if (metrics.avg_latency_ms < self.model_config.avg_response_time_seconds * 1000 and
            metrics.error_rate < 0.01 and  # Less than 1% error rate
            metrics.success_rate > 0.99):  # Greater than 99% success rate
            return GeminiHealthStatus.OPTIMAL
        
        return GeminiHealthStatus.HEALTHY
    
    def _convert_to_health_status(
        self, 
        gemini_status: GeminiHealthStatus, 
        metrics: GeminiHealthMetrics
    ) -> HealthStatus:
        """Convert Gemini-specific status to standard HealthStatus.
        
        Args:
            gemini_status: Gemini-specific health status
            metrics: Current health metrics
            
        Returns:
            Standard HealthStatus
        """
        if gemini_status in [GeminiHealthStatus.UNAVAILABLE, GeminiHealthStatus.CRITICAL]:
            return HealthStatus.UNHEALTHY
        elif gemini_status == GeminiHealthStatus.DEGRADED:
            return HealthStatus.DEGRADED
        else:  # HEALTHY or OPTIMAL
            return HealthStatus.HEALTHY
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed health status including Gemini-specific metrics.
        
        Returns:
            Dictionary with comprehensive health information
        """
        latest_metrics = self._health_history[-1] if self._health_history else None
        
        return {
            "service": "gemini",
            "model": self.model.value,
            "status": self._current_status.value,
            "last_check": self._last_check_time,
            "check_interval": self.check_interval,
            "metrics": latest_metrics.to_dict() if latest_metrics else {},
            "configuration": {
                "model_config": {
                    "avg_response_time_seconds": self.model_config.avg_response_time_seconds,
                    "max_response_time_seconds": self.model_config.max_response_time_seconds,
                    "context_window_tokens": self.model_config.context_window_tokens,
                    "requests_per_minute": self.model_config.requests_per_minute,
                    "tier": self.model_config.tier.value
                },
                "health_config": dict(self.health_config)
            },
            "history_length": len(self._health_history)
        }
    
    async def cleanup(self) -> None:
        """Clean up resources used by health checker."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None


# Factory function for easy instantiation
def create_gemini_health_checker(
    model: LLMModel = LLMModel.GEMINI_2_5_FLASH,
    check_interval_seconds: float = 30.0
) -> GeminiHealthChecker:
    """Create a Gemini health checker for the specified model.
    
    Args:
        model: Gemini model to monitor
        check_interval_seconds: Health check interval
        
    Returns:
        Configured GeminiHealthChecker instance
        
    Raises:
        ValueError: If model is not a Gemini model
    """
    if not is_gemini_model(model.value):
        raise ValueError(f"Model {model.value} is not a Gemini model")
    
    return GeminiHealthChecker(model, check_interval_seconds)


# Health checker registry integration
async def register_gemini_health_checkers(registry: Any) -> None:
    """Register Gemini health checkers with the health registry.
    
    Args:
        registry: Health checker registry to register with
    """
    # Register health checkers for all Gemini models
    gemini_models = [LLMModel.GEMINI_2_5_FLASH, LLMModel.GEMINI_2_5_PRO]
    
    for model in gemini_models:
        try:
            health_checker = create_gemini_health_checker(model)
            registry.register(f"gemini_{model.value.replace('-', '_')}", health_checker)
            logger.info(f"Registered health checker for {model.value}")
        except Exception as e:
            logger.error(f"Failed to register health checker for {model.value}: {e}")