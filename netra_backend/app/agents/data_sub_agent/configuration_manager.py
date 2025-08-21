"""Configuration Management for DataSubAgent

Separates configuration creation logic to maintain 450-line limit.
Handles reliability, circuit breaker and retry configurations.

Business Value: Modular configuration for maintainability.
"""

from typing import Dict, Any
from app.agents.config import agent_config
from app.core.reliability import CircuitBreakerConfig, RetryConfig
from app.schemas.shared_types import RetryConfig as ModernRetryConfig
from app.agents.base.circuit_breaker import CircuitBreakerConfig as ModernCircuitConfig
from app.agents.base.reliability_manager import ReliabilityManager


class DataSubAgentConfigurationManager:
    """Manages configuration for DataSubAgent reliability patterns."""
    
    def create_legacy_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create legacy circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=agent_config.failure_threshold,
            recovery_timeout=agent_config.timeout.recovery_timeout,
            name="DataSubAgent"
        )
    
    def create_legacy_retry_config(self) -> RetryConfig:
        """Create legacy retry configuration."""
        return RetryConfig(
            max_retries=agent_config.retry.max_retries,
            base_delay=agent_config.retry.base_delay,
            max_delay=agent_config.retry.max_delay
        )
    
    def create_modern_reliability_manager(self) -> ReliabilityManager:
        """Create modern reliability manager with data agent optimized settings."""
        circuit_config = self.create_modern_circuit_config()
        retry_config = self.create_modern_retry_config()
        return ReliabilityManager(circuit_config, retry_config)
    
    def create_modern_circuit_config(self) -> ModernCircuitConfig:
        """Create modern circuit breaker configuration."""
        return ModernCircuitConfig(
            name="DataSubAgent",
            failure_threshold=agent_config.failure_threshold,
            recovery_timeout=agent_config.timeout.recovery_timeout
        )
    
    def create_modern_retry_config(self) -> ModernRetryConfig:
        """Create modern retry configuration."""
        return ModernRetryConfig(
            max_retries=agent_config.retry.max_retries,
            base_delay=agent_config.retry.base_delay,
            max_delay=agent_config.retry.max_delay
        )
    
    def get_modern_health_status(self, agent_name: str, execution_engine, 
                               execution_monitor, legacy_status: Dict[str, Any]) -> Dict[str, Any]:
        """Get modern component health status."""
        return {
            "agent_name": agent_name,
            "execution_engine": execution_engine.get_health_status(),
            "execution_monitor": execution_monitor.get_health_status(),
            "legacy_reliability": legacy_status
        }