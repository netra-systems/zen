"""LLM client circuit breaker management.

Handles circuit breaker creation, configuration selection, and management
for different LLM types and configurations.
"""

import asyncio
from typing import Dict
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


from netra_backend.app.core.circuit_breaker import CircuitBreaker, circuit_registry
from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitConfig
from netra_backend.app.llm.client_config import LLMClientConfig
from netra_backend.app.schemas.core_models import CircuitBreakerConfig


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
        # Convert legacy CircuitBreakerConfig to UnifiedCircuitConfig
        unified_config = self._convert_to_unified_config(f"llm_{config_name}", circuit_config)
        return circuit_registry.create_circuit_breaker(f"llm_{config_name}", unified_config)
    
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
        return (LLMModel.GEMINI_2_5_FLASH.value in name_lower or 
                LLMModel.GEMINI_2_5_PRO.value in name_lower or 
                "claude" in name_lower)
    
    def _convert_to_unified_config(self, name: str, legacy_config: CircuitBreakerConfig) -> UnifiedCircuitConfig:
        """Convert legacy CircuitBreakerConfig to UnifiedCircuitConfig."""
        return UnifiedCircuitConfig(
            name=name,
            failure_threshold=getattr(legacy_config, 'failure_threshold', 5),
            recovery_timeout=getattr(legacy_config, 'recovery_timeout', 60.0),
            timeout_seconds=getattr(legacy_config, 'timeout_seconds', 30.0),
            success_threshold=getattr(legacy_config, 'success_threshold', 3)
        )
    
    async def get_structured_circuit(self, config_name: str) -> CircuitBreaker:
        """Get circuit breaker for structured LLM requests."""
        circuit_name = f"{config_name}_structured"
        unified_config = self._convert_to_unified_config(circuit_name, LLMClientConfig.STRUCTURED_LLM_CONFIG)
        return circuit_registry.create_circuit_breaker(circuit_name, unified_config)
    
    async def get_all_circuit_status(self) -> Dict[str, Dict]:
        """Get status of all LLM circuits."""
        return {name: circuit.get_metrics() 
                for name, circuit in self._circuits.items()}
                
    async def reset_all_circuits(self) -> None:
        """Reset all LLM circuit breakers."""
        for name, circuit in self._circuits.items():
            try:
                if hasattr(circuit, 'reset'):
                    if asyncio.iscoroutinefunction(circuit.reset):
                        await circuit.reset()
                    else:
                        circuit.reset()
                    logger.info(f"Reset LLM circuit breaker: {name}")
                else:
                    logger.warning(f"LLM circuit breaker {name} does not support reset")
            except Exception as e:
                logger.error(f"Failed to reset LLM circuit breaker {name}: {e}")
                
    async def reset_circuit(self, config_name: str) -> None:
        """Reset specific LLM circuit breaker."""
        if config_name in self._circuits:
            circuit = self._circuits[config_name]
            try:
                if hasattr(circuit, 'reset'):
                    if asyncio.iscoroutinefunction(circuit.reset):
                        await circuit.reset()
                    else:
                        circuit.reset()
                    logger.info(f"Reset LLM circuit breaker: {config_name}")
                else:
                    logger.warning(f"LLM circuit breaker {config_name} does not support reset")
            except Exception as e:
                logger.error(f"Failed to reset LLM circuit breaker {config_name}: {e}")
        else:
            logger.warning(f"LLM circuit breaker not found: {config_name}")