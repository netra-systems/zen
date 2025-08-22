"""Circuit Breaker Integration for Supervisor.

Integrates circuit breaker patterns into supervisor workflow.
Business Value: Prevents cascade failures and ensures system stability.
"""

from typing import Any, Awaitable, Callable, Dict

from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


class SupervisorCircuitBreakerIntegration:
    """Integrates circuit breaker patterns into supervisor workflow."""
    
    def __init__(self):
        self.reliability_manager = self._create_reliability_manager()
        self._agent_circuit_breakers: Dict[str, ReliabilityManager] = {}
    
    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with supervisor-specific config."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        return ReliabilityManager(circuit_config, retry_config)
    
    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            name="supervisor_circuit_breaker",
            failure_threshold=5,
            recovery_timeout=30
        )
    
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0
        )
    
    async def execute_with_circuit_protection(self, 
                                            context: ExecutionContext,
                                            execute_func: Callable[[], Awaitable[ExecutionResult]]
                                            ) -> ExecutionResult:
        """Execute function with circuit breaker protection."""
        agent_manager = self._get_agent_reliability_manager(context.agent_name)
        return await agent_manager.execute_with_reliability(context, execute_func)
    
    def _get_agent_reliability_manager(self, agent_name: str) -> ReliabilityManager:
        """Get or create agent-specific reliability manager."""
        if agent_name not in self._agent_circuit_breakers:
            self._agent_circuit_breakers[agent_name] = self._create_agent_reliability_manager(agent_name)
        return self._agent_circuit_breakers[agent_name]
    
    def _create_agent_reliability_manager(self, agent_name: str) -> ReliabilityManager:
        """Create agent-specific reliability manager."""
        circuit_config = CircuitBreakerConfig(
            name=f"{agent_name}_circuit_breaker",
            failure_threshold=3,
            recovery_timeout=20
        )
        retry_config = RetryConfig(
            max_retries=2,
            base_delay=0.5,
            max_delay=10.0,
            backoff_multiplier=2.0
        )
        return ReliabilityManager(circuit_config, retry_config)
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for all agents."""
        status = {
            "supervisor": self.reliability_manager.get_health_status(),
            "agents": {}
        }
        
        for agent_name, manager in self._agent_circuit_breakers.items():
            status["agents"][agent_name] = manager.get_health_status()
        
        return status
    
    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers."""
        self.reliability_manager.reset_health_tracking()
        for manager in self._agent_circuit_breakers.values():
            manager.reset_health_tracking()
        logger.info("All circuit breakers reset")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        supervisor_health = self.reliability_manager.get_health_status()
        agent_healths = {name: mgr.get_health_status() 
                        for name, mgr in self._agent_circuit_breakers.items()}
        
        overall_healthy = (supervisor_health["overall_health"] == "healthy" and
                          all(h["overall_health"] == "healthy" for h in agent_healths.values()))
        
        return {
            "overall_healthy": overall_healthy,
            "supervisor_health": supervisor_health,
            "agent_health": agent_healths,
            "total_agents_monitored": len(self._agent_circuit_breakers)
        }
