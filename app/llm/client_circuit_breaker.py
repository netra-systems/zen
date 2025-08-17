"""LLM client circuit breaker management.

Handles circuit breaker creation, configuration selection, and management
for different LLM types and configurations.
"""

from typing import Dict
from app.core.circuit_breaker import CircuitBreaker, circuit_registry
from app.schemas.core_models import CircuitBreakerConfig
from app.llm.client_config import LLMClientConfig


class LLMCircuitBreakerManager:
    """Manages circuit breakers for LLM operations."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self._circuits: Dict[str, CircuitBreaker] = {}
    
    async def get_circuit(self, config_name: str) -> CircuitBreaker:
        """Get circuit breaker for LLM configuration."""
        if config_name not in self._circuits:
            self._circuits[config_name] = await self._create_circuit(config_name)
        return self._circuits[config_name]
    
    async def _create_circuit(self, config_name: str) -> CircuitBreaker:
        """Create new circuit breaker for configuration."""
        circuit_config = self._select_circuit_config(config_name)
        return circuit_registry.get_breaker(
            f"llm_{config_name}", circuit_config
        )
    
    def _select_circuit_config(self, config_name: str) -> CircuitBreakerConfig:
        """Select appropriate circuit config based on LLM type."""
        if self._is_fast_llm(config_name):
            return LLMClientConfig.FAST_LLM_CONFIG
        elif self._is_slow_llm(config_name):
            return LLMClientConfig.SLOW_LLM_CONFIG
        return LLMClientConfig.STANDARD_LLM_CONFIG
    
    def _is_fast_llm(self, config_name: str) -> bool:
        """Check if LLM configuration is for fast models."""
        name_lower = config_name.lower()
        return "fast" in name_lower or "gpt-3.5" in name_lower
    
    def _is_slow_llm(self, config_name: str) -> bool:
        """Check if LLM configuration is for slow models."""
        name_lower = config_name.lower()
        return "gpt-4" in name_lower or "claude" in name_lower
    
    async def get_structured_circuit(self, config_name: str) -> CircuitBreaker:
        """Get circuit breaker for structured LLM requests."""
        circuit_name = f"{config_name}_structured"
        return circuit_registry.get_breaker(
            circuit_name, LLMClientConfig.STRUCTURED_LLM_CONFIG
        )
    
    async def get_all_circuit_status(self) -> Dict[str, Dict]:
        """Get status of all LLM circuits."""
        return {name: circuit.get_metrics() 
                for name, circuit in self._circuits.items()}