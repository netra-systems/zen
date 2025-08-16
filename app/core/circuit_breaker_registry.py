"""Circuit breaker registry and context manager.

This module provides the registry for managing multiple circuit breakers
and the context manager for convenient circuit breaker usage.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from app.logging_config import central_logger
from .circuit_breaker_types import CircuitConfig, CircuitBreakerOpenError
from .circuit_breaker_core import CircuitBreaker

logger = central_logger.get_logger(__name__)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self) -> None:
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_circuit(self, name: str, config: Optional[CircuitConfig] = None) -> CircuitBreaker:
        """Get or create circuit breaker."""
        async with self._lock:
            if name not in self._circuits:
                if not config:
                    config = CircuitConfig(name=name)
                self._circuits[name] = CircuitBreaker(config)
            return self._circuits[name]
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered circuits."""
        async with self._lock:
            return {name: circuit.get_status() 
                    for name, circuit in self._circuits.items()}


# Global registry instance
circuit_registry = CircuitBreakerRegistry()


@asynccontextmanager
async def circuit_breaker(name: str, config: Optional[CircuitConfig] = None):
    """Context manager for circuit breaker protection."""
    circuit = await circuit_registry.get_circuit(name, config)
    try:
        yield circuit
    except CircuitBreakerOpenError:
        logger.warning(f"Circuit breaker '{name}' prevented execution")
        raise