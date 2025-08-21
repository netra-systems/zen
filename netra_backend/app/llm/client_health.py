"""LLM client health monitoring.

Provides comprehensive health checks for LLM configurations,
circuit breaker status, and overall system health assessment.
"""

from typing import Any, Dict, Optional
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.client_circuit_breaker import LLMCircuitBreakerManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LLMHealthMonitor:
    """Monitors health of LLM operations and circuit breakers."""
    
    def __init__(self, llm_manager: LLMManager):
        """Initialize health monitor."""
        self.llm_manager = llm_manager
        self.circuit_manager = LLMCircuitBreakerManager()
    
    async def _get_health_components(self, config_name: str) -> tuple:
        """Get health check components for LLM and circuit."""
        llm_health = await self.llm_manager.health_check(config_name)
        circuit = await self.circuit_manager.get_circuit(config_name)
        circuit_status = circuit.get_metrics()
        return llm_health, circuit_status
    
    def _build_health_response(self, llm_health: Any, circuit_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build health check response from components."""
        return {
            "llm_health": llm_health,
            "circuit_status": circuit_status,
            "overall_health": self._assess_overall_health(llm_health, circuit_status)
        }
    
    def _build_error_response(self, config_name: str, error: Exception) -> Dict[str, Any]:
        """Build error response for health check failure."""
        logger.error(f"Health check failed for {config_name}: {error}")
        return {
            "error": str(error),
            "overall_health": "unhealthy"
        }
    
    async def health_check(self, config_name: str) -> Dict[str, Any]:
        """Comprehensive health check for LLM configuration."""
        try:
            llm_health, circuit_status = await self._get_health_components(config_name)
            return self._build_health_response(llm_health, circuit_status)
        except Exception as e:
            return self._build_error_response(config_name, e)
    
    def _check_llm_health_status(self, llm_health: Any) -> Optional[str]:
        """Check LLM health status and return override if unhealthy."""
        if not llm_health.healthy:
            return "unhealthy"
        return None
    
    def _check_circuit_health_status(self, circuit_status: Dict[str, Any]) -> str:
        """Check circuit health status and return appropriate state."""
        circuit_state = circuit_status["state"]
        if circuit_state == "open":
            return "degraded"
        elif circuit_state == "half_open":
            return "recovering"
        return "healthy"
    
    def _assess_overall_health(self, llm_health: Any, circuit_status: Dict[str, Any]) -> str:
        """Assess overall health from LLM and circuit status."""
        llm_override = self._check_llm_health_status(llm_health)
        if llm_override:
            return llm_override
        return self._check_circuit_health_status(circuit_status)
    
    async def get_all_circuit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all LLM circuits."""
        return await self.circuit_manager.get_all_circuit_status()