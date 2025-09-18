"""Unified Reliability Manager for comprehensive system reliability.

Provides centralized reliability management including circuit breakers,
retry strategies, fallback mechanisms, and health monitoring.

Business Value:
- Ensures 99.99% uptime for enterprise customers
- Provides graceful degradation during outages
- Enables reliable multi-agent system operations
"""

from typing import Dict, Any, Optional, List, Callable, Awaitable, TypeVar, Generic
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
import asyncio
import logging
import time

from netra_backend.app.core.resilience.domain_circuit_breakers import (
    DomainCircuitBreaker, 
    DomainType,
    CircuitBreakerState,
    domain_circuit_breaker_manager
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ReliabilityLevel(Enum):
    """Reliability levels for different operations."""
    CRITICAL = "critical"
    HIGH = "high"  
    MEDIUM = "medium"
    LOW = "low"


class FailureMode(Enum):
    """Types of failure modes."""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_ERROR = "authentication_error"
    INTERNAL_ERROR = "internal_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"


@dataclass
class ReliabilityConfig:
    """Configuration for reliability settings."""
    level: ReliabilityLevel = ReliabilityLevel.MEDIUM
    max_retries: int = 3
    timeout_seconds: float = 30.0
    circuit_breaker_enabled: bool = True
    fallback_enabled: bool = True
    health_check_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "fallback_enabled": self.fallback_enabled,
            "health_check_enabled": self.health_check_enabled,
        }


@dataclass
class ReliabilityResult(Generic[T]):
    """Result of a reliability-managed operation."""
    success: bool
    result: Optional[T] = None
    error: Optional[Exception] = None
    attempts: int = 1
    duration_ms: float = 0.0
    circuit_breaker_used: bool = False
    fallback_used: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class UnifiedReliabilityManager:
    """Unified manager for all reliability patterns."""
    
    def __init__(self):
        self._domain_configs: Dict[str, ReliabilityConfig] = {}
        self._health_status: Dict[str, Dict[str, Any]] = {}
        self._failure_stats: Dict[str, Dict[FailureMode, int]] = {}
        
        # Set up default reliability configs
        self._setup_default_configs()
        
        logger.debug("UnifiedReliabilityManager initialized")
    
    def _setup_default_configs(self):
        """Set up default reliability configurations."""
        self._domain_configs.update({
            "agent": ReliabilityConfig(
                level=ReliabilityLevel.HIGH,
                max_retries=2,
                timeout_seconds=120.0,
                circuit_breaker_enabled=True,
                fallback_enabled=True,
            ),
            "database": ReliabilityConfig(
                level=ReliabilityLevel.CRITICAL,
                max_retries=3,
                timeout_seconds=10.0,
                circuit_breaker_enabled=True,
                fallback_enabled=False,
            ),
            "llm": ReliabilityConfig(
                level=ReliabilityLevel.HIGH,
                max_retries=3,
                timeout_seconds=60.0,
                circuit_breaker_enabled=True,
                fallback_enabled=True,
            ),
            "external_api": ReliabilityConfig(
                level=ReliabilityLevel.MEDIUM,
                max_retries=5,
                timeout_seconds=30.0,
                circuit_breaker_enabled=True,
                fallback_enabled=True,
            ),
        })
    
    def register_service(self, service_name: str, domain: str, config: Optional[ReliabilityConfig] = None):
        """Register a service with reliability management."""
        if config is None:
            config = self._domain_configs.get(domain, ReliabilityConfig())
        
        self._domain_configs[service_name] = config
        self._health_status[service_name] = {
            "status": "unknown",
            "last_check": None,
            "consecutive_failures": 0,
        }
        self._failure_stats[service_name] = {mode: 0 for mode in FailureMode}
        
        logger.info(f"Registered service '{service_name}' with domain '{domain}'")
    
    async def execute_with_reliability(
        self, 
        service_name: str, 
        operation: Callable[..., Awaitable[T]],
        *args, 
        **kwargs
    ) -> ReliabilityResult[T]:
        """Execute operation with full reliability management."""
        start_time = time.time()
        config = self._domain_configs.get(service_name, ReliabilityConfig())
        
        # Check circuit breaker
        circuit_breaker = domain_circuit_breaker_manager.get_circuit_breaker(
            DomainType.LLM_SERVICE, service_name
        )
        
        if config.circuit_breaker_enabled and not circuit_breaker.can_execute():
            # Circuit breaker is open - try fallback if available
            if config.fallback_enabled:
                logger.warning(f"Circuit breaker open for {service_name}, attempting fallback")
                return await self._execute_fallback(service_name, start_time)
            else:
                return ReliabilityResult(
                    success=False,
                    error=Exception("Circuit breaker open and no fallback available"),
                    duration_ms=(time.time() - start_time) * 1000,
                    circuit_breaker_used=True,
                )
        
        # Execute with retry logic
        last_error = None
        for attempt in range(1, config.max_retries + 2):  # +1 for initial attempt
            try:
                # Apply timeout if configured
                if config.timeout_seconds > 0:
                    result = await asyncio.wait_for(
                        operation(*args, **kwargs),
                        timeout=config.timeout_seconds
                    )
                else:
                    result = await operation(*args, **kwargs)
                
                # Record success
                if config.circuit_breaker_enabled:
                    circuit_breaker.record_success()
                
                self._record_success(service_name)
                
                return ReliabilityResult(
                    success=True,
                    result=result,
                    attempts=attempt,
                    duration_ms=(time.time() - start_time) * 1000,
                    circuit_breaker_used=config.circuit_breaker_enabled,
                )
                
            except asyncio.TimeoutError as e:
                last_error = e
                failure_mode = FailureMode.TIMEOUT
                
            except ConnectionError as e:
                last_error = e
                failure_mode = FailureMode.CONNECTION_ERROR
                
            except Exception as e:
                last_error = e
                failure_mode = FailureMode.INTERNAL_ERROR
            
            # Record failure
            if config.circuit_breaker_enabled:
                circuit_breaker.record_failure(str(last_error))
            
            self._record_failure(service_name, failure_mode)
            
            # If this was the last attempt, break
            if attempt > config.max_retries:
                break
            
            # Wait before retry (exponential backoff)
            wait_time = min(2 ** (attempt - 1), 30)  # Cap at 30 seconds
            logger.debug(f"Retrying {service_name} in {wait_time}s (attempt {attempt}/{config.max_retries})")
            await asyncio.sleep(wait_time)
        
        # All retries failed - try fallback if available
        if config.fallback_enabled:
            logger.warning(f"All retries failed for {service_name}, attempting fallback")
            fallback_result = await self._execute_fallback(service_name, start_time)
            fallback_result.attempts = config.max_retries + 1
            return fallback_result
        
        # Return failure result
        return ReliabilityResult(
            success=False,
            error=last_error,
            attempts=config.max_retries + 1,
            duration_ms=(time.time() - start_time) * 1000,
            circuit_breaker_used=config.circuit_breaker_enabled,
        )
    
    async def _execute_fallback(self, service_name: str, start_time: float) -> ReliabilityResult:
        """Execute fallback for failed service."""
        try:
            # Simple fallback - return cached result or default
            fallback_result = self._get_fallback_result(service_name)
            
            return ReliabilityResult(
                success=True,
                result=fallback_result,
                duration_ms=(time.time() - start_time) * 1000,
                fallback_used=True,
                metadata={"fallback_type": "cached_or_default"}
            )
            
        except Exception as e:
            return ReliabilityResult(
                success=False,
                error=e,
                duration_ms=(time.time() - start_time) * 1000,
                fallback_used=True,
                metadata={"fallback_error": str(e)}
            )
    
    def _get_fallback_result(self, service_name: str) -> Any:
        """Get fallback result for service."""
        # This would normally fetch from cache or return a safe default
        # For now, return a simple default based on service type
        if "llm" in service_name.lower():
            return {"response": "Service temporarily unavailable. Please try again later."}
        elif "database" in service_name.lower():
            return []
        else:
            return {"status": "fallback", "message": "Service temporarily unavailable"}
    
    def _record_success(self, service_name: str):
        """Record successful operation."""
        if service_name in self._health_status:
            self._health_status[service_name].update({
                "status": "healthy",
                "last_check": datetime.now(UTC),
                "consecutive_failures": 0,
            })
    
    def _record_failure(self, service_name: str, failure_mode: FailureMode):
        """Record failed operation."""
        if service_name in self._health_status:
            current = self._health_status[service_name]
            current.update({
                "status": "unhealthy",
                "last_check": datetime.now(UTC),
                "consecutive_failures": current.get("consecutive_failures", 0) + 1,
            })
        
        if service_name in self._failure_stats:
            self._failure_stats[service_name][failure_mode] += 1
    
    async def health_check(self, service_name: str) -> Dict[str, Any]:
        """Perform health check for service."""
        if service_name not in self._health_status:
            return {"status": "unknown", "error": "Service not registered"}
        
        health_status = self._health_status[service_name]
        circuit_breaker = domain_circuit_breaker_manager.get_circuit_breaker(
            DomainType.LLM_SERVICE, service_name
        )
        
        return {
            "service": service_name,
            "status": health_status["status"],
            "last_check": health_status["last_check"],
            "consecutive_failures": health_status["consecutive_failures"],
            "circuit_breaker": circuit_breaker.get_status(),
            "failure_stats": self._failure_stats.get(service_name, {}),
            "config": self._domain_configs.get(service_name, ReliabilityConfig()).to_dict(),
            "timestamp": datetime.now(UTC),
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        service_healths = {}
        total_services = len(self._health_status)
        healthy_services = 0
        
        for service_name in self._health_status:
            health = await self.health_check(service_name)
            service_healths[service_name] = health
            
            if health["status"] == "healthy":
                healthy_services += 1
        
        overall_health = "healthy" if healthy_services == total_services else "degraded"
        if healthy_services < total_services * 0.5:
            overall_health = "critical"
        
        return {
            "overall_status": overall_health,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": total_services - healthy_services,
            "health_percentage": (healthy_services / max(total_services, 1)) * 100,
            "services": service_healths,
            "timestamp": datetime.now(UTC),
        }
    
    def get_reliability_config(self, service_name: str) -> Optional[ReliabilityConfig]:
        """Get reliability configuration for service."""
        return self._domain_configs.get(service_name)
    
    def update_reliability_config(self, service_name: str, config: ReliabilityConfig):
        """Update reliability configuration for service."""
        self._domain_configs[service_name] = config
        logger.info(f"Updated reliability config for {service_name}")


# Global unified reliability manager instance
unified_reliability_manager = UnifiedReliabilityManager()


def get_reliability_manager() -> UnifiedReliabilityManager:
    """Get the global unified reliability manager instance."""
    return unified_reliability_manager


def reset_reliability_manager():
    """Reset the global reliability manager (for testing)."""
    global unified_reliability_manager
    unified_reliability_manager = UnifiedReliabilityManager()


__all__ = [
    "UnifiedReliabilityManager",
    "ReliabilityLevel",
    "ReliabilityConfig", 
    "ReliabilityResult",
    "FailureMode",
    "unified_reliability_manager",
    "get_reliability_manager",
    "reset_reliability_manager",
]