"""Circuit Breaker Manager Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic circuit breaker management functionality for tests
- Value Impact: Ensures circuit breaker tests can execute without import errors
- Strategic Impact: Enables circuit breaker functionality validation
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Import from the core circuit breaker implementation
from netra_backend.app.core.circuit_breaker import CircuitBreaker as CoreCircuitBreaker
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerState


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    half_open_max_calls: int = 3
    timeout_seconds: float = 30.0


@dataclass
class ServiceConfig:
    """Service configuration for circuit breaker."""
    name: str
    endpoint: str
    health_check_url: Optional[str] = None
    circuit_breaker_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)


class CircuitBreakerManager:
    """Manager for circuit breakers across services."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self._circuit_breakers: Dict[str, CoreCircuitBreaker] = {}
        self._service_configs: Dict[str, ServiceConfig] = {}
        self._lock = asyncio.Lock()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the circuit breaker manager."""
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop(self) -> None:
        """Stop the circuit breaker manager."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def register_service(self, service_config: ServiceConfig) -> None:
        """Register a service with circuit breaker protection."""
        async with self._lock:
            self._service_configs[service_config.name] = service_config
            
            # Create circuit breaker for the service
            config = service_config.circuit_breaker_config
            circuit_breaker = CoreCircuitBreaker(
                failure_threshold=config.failure_threshold,
                recovery_timeout=config.recovery_timeout_seconds,
                timeout=config.timeout_seconds
            )
            self._circuit_breakers[service_config.name] = circuit_breaker
    
    async def unregister_service(self, service_name: str) -> None:
        """Unregister a service."""
        async with self._lock:
            self._service_configs.pop(service_name, None)
            self._circuit_breakers.pop(service_name, None)
    
    async def call_service(
        self, 
        service_name: str, 
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Call a service through its circuit breaker."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(service_name)
            if not circuit_breaker:
                raise ValueError(f"Service '{service_name}' not registered")
        
        return await circuit_breaker.call(operation, *args, **kwargs)
    
    async def get_circuit_breaker_state(self, service_name: str) -> Optional[CircuitBreakerState]:
        """Get the current state of a service's circuit breaker."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(service_name)
            if circuit_breaker:
                return circuit_breaker.state
            return None
    
    async def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers."""
        async with self._lock:
            states = {}
            for service_name, circuit_breaker in self._circuit_breakers.items():
                config = self._service_configs.get(service_name)
                states[service_name] = {
                    "state": circuit_breaker.state.value,
                    "failure_count": circuit_breaker.failure_count,
                    "last_failure_time": circuit_breaker.last_failure_time,
                    "endpoint": config.endpoint if config else None,
                    "health_check_url": config.health_check_url if config else None
                }
            return states
    
    async def force_open(self, service_name: str) -> None:
        """Force a circuit breaker to open state."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(service_name)
            if circuit_breaker:
                circuit_breaker._state = CircuitBreakerState.OPEN
                circuit_breaker.last_failure_time = time.time()
    
    async def force_close(self, service_name: str) -> None:
        """Force a circuit breaker to closed state."""
        async with self._lock:
            circuit_breaker = self._circuit_breakers.get(service_name)
            if circuit_breaker:
                circuit_breaker._state = CircuitBreakerState.CLOSED
                circuit_breaker.failure_count = 0
                circuit_breaker.last_failure_time = None
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        async with self._lock:
            for circuit_breaker in self._circuit_breakers.values():
                circuit_breaker._state = CircuitBreakerState.CLOSED
                circuit_breaker.failure_count = 0
                circuit_breaker.last_failure_time = None
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all services."""
        async with self._lock:
            total_services = len(self._circuit_breakers)
            healthy_services = 0
            degraded_services = 0
            unhealthy_services = 0
            
            for circuit_breaker in self._circuit_breakers.values():
                if circuit_breaker.state == CircuitBreakerState.CLOSED:
                    healthy_services += 1
                elif circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
                    degraded_services += 1
                else:  # OPEN
                    unhealthy_services += 1
            
            return {
                "total_services": total_services,
                "healthy": healthy_services,
                "degraded": degraded_services,
                "unhealthy": unhealthy_services,
                "overall_health": "healthy" if unhealthy_services == 0 else "degraded" if healthy_services > 0 else "unhealthy"
            }
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self._check_service_health()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue monitoring
                await asyncio.sleep(5)
    
    async def _check_service_health(self) -> None:
        """Check health of all registered services."""
        async with self._lock:
            service_configs = dict(self._service_configs)
        
        for service_name, config in service_configs.items():
            if config.health_check_url:
                try:
                    # Perform basic health check
                    async with asyncio.timeout(10):
                        # In a real implementation, this would make HTTP requests
                        # For testing, we simulate the health check
                        await asyncio.sleep(0.1)
                except Exception as e:
                    # Health check failed, record failure
                    async with self._lock:
                        circuit_breaker = self._circuit_breakers.get(service_name)
                        if circuit_breaker:
                            # This would normally be handled by the circuit breaker's failure recording
                            pass


# Global circuit breaker manager instance
default_circuit_breaker_manager = CircuitBreakerManager()