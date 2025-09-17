"""
Domain-specific circuit breakers for different service areas.
Provides specialized circuit breaker configurations for various domains.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC
from enum import Enum
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DomainType(Enum):
    """Different domain types for circuit breakers."""
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    LLM_SERVICE = "llm_service"
    CACHE = "cache"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class AgentCircuitBreakerConfig:
    """Configuration for agent circuit breakers."""
    failure_threshold: int = 3
    recovery_timeout_seconds: int = 60
    half_open_max_calls: int = 2
    success_threshold: int = 3  # Number of successes needed to close circuit
    task_timeout_seconds: float = 120.0  # Task timeout in seconds
    sliding_window_size: int = 10  # Size of sliding window for failure tracking
    error_rate_threshold: float = 0.5  # Error rate threshold for opening circuit
    slow_task_threshold_seconds: float = 120.0  # Threshold for slow tasks
    max_backoff_seconds: float = 300.0  # Maximum backoff time
    preserve_context_on_failure: bool = True  # Whether to preserve context on failure
    nested_task_support: bool = True  # Whether to support nested tasks
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
            "half_open_max_calls": self.half_open_max_calls,
            "success_threshold": self.success_threshold,
            "task_timeout_seconds": self.task_timeout_seconds,
            "sliding_window_size": self.sliding_window_size,
            "error_rate_threshold": self.error_rate_threshold,
            "slow_task_threshold_seconds": self.slow_task_threshold_seconds,
            "max_backoff_seconds": self.max_backoff_seconds,
            "preserve_context_on_failure": self.preserve_context_on_failure,
            "nested_task_support": self.nested_task_support,
            "enabled": self.enabled
        }


class DomainCircuitBreaker:
    """Circuit breaker for a specific domain with domain-specific thresholds."""
    
    def __init__(self, 
                 domain: DomainType,
                 name: str,
                 failure_threshold: int = 5,
                 recovery_timeout_seconds: int = 60,
                 half_open_max_calls: int = 3):
        """
        Initialize domain circuit breaker.
        
        Args:
            domain: Domain type this circuit breaker protects
            name: Name of the specific service/resource
            failure_threshold: Number of failures before opening
            recovery_timeout_seconds: Seconds before trying half-open
            half_open_max_calls: Max calls in half-open state
        """
        self.domain = domain
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        
        # State tracking
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._success_count = 0
        self._total_calls = 0
        
        logger.debug(f"Initialized {domain.value} circuit breaker: {name}")
    
    def can_execute(self) -> bool:
        """Check if calls can be executed through this circuit breaker."""
        if self._state == CircuitBreakerState.CLOSED:
            return True
        
        if self._state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self._last_failure_time and 
                datetime.now(UTC) - self._last_failure_time >= 
                timedelta(seconds=self.recovery_timeout_seconds)):
                self._transition_to_half_open()
                return True
            return False
        
        if self._state == CircuitBreakerState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self) -> None:
        """Record a successful operation."""
        self._success_count += 1
        self._total_calls += 1
        
        if self._state == CircuitBreakerState.HALF_OPEN:
            # After a few successes in half-open, close the circuit
            if self._success_count >= 2:
                self._transition_to_closed()
            else:
                self._half_open_calls += 1
        elif self._state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    def record_failure(self, error_message: str = "") -> None:
        """Record a failed operation."""
        self._failure_count += 1
        self._total_calls += 1
        self._last_failure_time = datetime.now(UTC)
        
        logger.warning(f"{self.domain.value} circuit breaker '{self.name}' recorded failure: {error_message}")
        
        if self._state == CircuitBreakerState.HALF_OPEN:
            # Failure in half-open state - go back to open
            self._transition_to_open()
        elif (self._state == CircuitBreakerState.CLOSED and 
              self._failure_count >= self.failure_threshold):
            # Too many failures - open the circuit
            self._transition_to_open()
    
    def _transition_to_open(self) -> None:
        """Transition circuit breaker to open state."""
        self._state = CircuitBreakerState.OPEN
        self._half_open_calls = 0
        self._success_count = 0
        logger.warning(f"{self.domain.value} circuit breaker '{self.name}' OPENED after {self._failure_count} failures")
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to half-open state."""
        self._state = CircuitBreakerState.HALF_OPEN
        self._half_open_calls = 0
        self._success_count = 0
        logger.info(f"{self.domain.value} circuit breaker '{self.name}' moved to HALF_OPEN")
    
    def _transition_to_closed(self) -> None:
        """Transition circuit breaker to closed state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info(f"{self.domain.value} circuit breaker '{self.name}' CLOSED after recovery")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of circuit breaker."""
        return {
            "domain": self.domain.value,
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "success_rate": self._success_count / max(self._total_calls, 1),
            "last_failure_time": self._last_failure_time,
            "can_execute": self.can_execute(),
            "half_open_calls": self._half_open_calls if self._state == CircuitBreakerState.HALF_OPEN else None
        }
    
    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info(f"{self.domain.value} circuit breaker '{self.name}' manually reset")


class AgentCircuitBreaker(DomainCircuitBreaker):
    """Specialized circuit breaker for agent operations."""
    
    def __init__(self, agent_name: str, **kwargs):
        """Initialize agent-specific circuit breaker."""
        # Set agent-specific defaults
        agent_defaults = {
            "failure_threshold": 3,
            "recovery_timeout_seconds": 60,
            "half_open_max_calls": 2
        }
        agent_defaults.update(kwargs)
        
        super().__init__(
            domain=DomainType.LLM_SERVICE,
            name=agent_name,
            **agent_defaults
        )
        
        self.agent_name = agent_name
        
        # Create a config object for compatibility with ReliabilityManager
        self.config = AgentCircuitBreakerConfig(
            failure_threshold=agent_defaults.get("failure_threshold", 3),
            recovery_timeout_seconds=agent_defaults.get("recovery_timeout_seconds", 60),
            half_open_max_calls=agent_defaults.get("half_open_max_calls", 2),
            success_threshold=agent_defaults.get("success_threshold", 3),
            enabled=agent_defaults.get("enabled", True)
        )
        
        logger.debug(f"Initialized AgentCircuitBreaker for agent: {agent_name}")
    
    def record_agent_timeout(self) -> None:
        """Record agent timeout as a failure."""
        self.record_failure("Agent operation timed out")
    
    def record_agent_error(self, error_type: str, error_message: str) -> None:
        """Record agent-specific error."""
        self.record_failure(f"{error_type}: {error_message}")
    
    def can_execute_agent(self) -> bool:
        """Check if agent can execute operations."""
        return self.can_execute()


class DomainCircuitBreakerManager:
    """Manages circuit breakers for different domains and services."""
    
    def __init__(self):
        self._circuit_breakers: Dict[str, DomainCircuitBreaker] = {}
        self._domain_configs = self._get_default_domain_configs()
        logger.debug("Initialized DomainCircuitBreakerManager")
    
    def _get_default_domain_configs(self) -> Dict[DomainType, Dict[str, Any]]:
        """Get default configurations for different domain types."""
        return {
            DomainType.DATABASE: {
                "failure_threshold": 3,
                "recovery_timeout_seconds": 30,
                "half_open_max_calls": 2
            },
            DomainType.EXTERNAL_API: {
                "failure_threshold": 5,
                "recovery_timeout_seconds": 60,
                "half_open_max_calls": 3
            },
            DomainType.LLM_SERVICE: {
                "failure_threshold": 2,
                "recovery_timeout_seconds": 120,
                "half_open_max_calls": 1
            },
            DomainType.CACHE: {
                "failure_threshold": 10,
                "recovery_timeout_seconds": 15,
                "half_open_max_calls": 5
            },
            DomainType.FILE_SYSTEM: {
                "failure_threshold": 3,
                "recovery_timeout_seconds": 45,
                "half_open_max_calls": 2
            },
            DomainType.NETWORK: {
                "failure_threshold": 5,
                "recovery_timeout_seconds": 30,
                "half_open_max_calls": 3
            }
        }
    
    def get_circuit_breaker(self, domain: DomainType, name: str) -> DomainCircuitBreaker:
        """Get or create circuit breaker for domain and service."""
        key = f"{domain.value}:{name}"
        
        if key not in self._circuit_breakers:
            config = self._domain_configs.get(domain, {})
            self._circuit_breakers[key] = DomainCircuitBreaker(
                domain=domain,
                name=name,
                **config
            )
            logger.info(f"Created {domain.value} circuit breaker for: {name}")
        
        return self._circuit_breakers[key]
    
    def record_success(self, domain: DomainType, name: str) -> None:
        """Record success for domain service."""
        circuit_breaker = self.get_circuit_breaker(domain, name)
        circuit_breaker.record_success()
    
    def record_failure(self, domain: DomainType, name: str, error_message: str = "") -> None:
        """Record failure for domain service."""
        circuit_breaker = self.get_circuit_breaker(domain, name)
        circuit_breaker.record_failure(error_message)
    
    def can_execute(self, domain: DomainType, name: str) -> bool:
        """Check if operations can be executed for domain service."""
        circuit_breaker = self.get_circuit_breaker(domain, name)
        return circuit_breaker.can_execute()
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers."""
        status = {}
        for key, circuit_breaker in self._circuit_breakers.items():
            status[key] = circuit_breaker.get_status()
        
        return {
            "circuit_breakers": status,
            "total_count": len(self._circuit_breakers),
            "domains": list(set(cb.domain for cb in self._circuit_breakers.values())),
            "timestamp": datetime.now(UTC)
        }
    
    def get_domain_status(self, domain: DomainType) -> Dict[str, Any]:
        """Get status of all circuit breakers for a specific domain."""
        domain_breakers = {
            key: cb for key, cb in self._circuit_breakers.items() 
            if cb.domain == domain
        }
        
        status = {}
        for key, circuit_breaker in domain_breakers.items():
            status[key] = circuit_breaker.get_status()
        
        # Domain-level summary
        total_breakers = len(domain_breakers)
        open_breakers = len([cb for cb in domain_breakers.values() if cb._state == CircuitBreakerState.OPEN])
        healthy_breakers = len([cb for cb in domain_breakers.values() if cb._state == CircuitBreakerState.CLOSED])
        
        return {
            "domain": domain.value,
            "circuit_breakers": status,
            "summary": {
                "total": total_breakers,
                "open": open_breakers,
                "closed": healthy_breakers,
                "half_open": total_breakers - open_breakers - healthy_breakers,
                "health_percentage": (healthy_breakers / max(total_breakers, 1)) * 100
            },
            "timestamp": datetime.now(UTC)
        }
    
    def reset_circuit_breaker(self, domain: DomainType, name: str) -> bool:
        """Reset specific circuit breaker."""
        key = f"{domain.value}:{name}"
        if key in self._circuit_breakers:
            self._circuit_breakers[key].reset()
            return True
        return False
    
    def reset_all_domain_breakers(self, domain: DomainType) -> int:
        """Reset all circuit breakers for a domain."""
        reset_count = 0
        for circuit_breaker in self._circuit_breakers.values():
            if circuit_breaker.domain == domain:
                circuit_breaker.reset()
                reset_count += 1
        
        logger.info(f"Reset {reset_count} circuit breakers for domain: {domain.value}")
        return reset_count


# Global instance
domain_circuit_breaker_manager = DomainCircuitBreakerManager()


__all__ = [
    "DomainCircuitBreaker",
    "DomainCircuitBreakerManager", 
    "AgentCircuitBreaker",
    "AgentCircuitBreakerConfig",
    "DomainType",
    "CircuitBreakerState",
    "domain_circuit_breaker_manager",
]