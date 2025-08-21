"""Supervisor utility functions for hooks and statistics."""

from typing import Dict, List, Any
from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.state import DeepAgentState

logger = central_logger.get_logger(__name__)


class SupervisorUtilities:
    """Utility class for supervisor hook execution and statistics."""
    
    def __init__(self, hooks: Dict[str, List], registry, engine, 
                 monitor=None, reliability_manager=None, execution_engine=None, error_handler=None):
        """Initialize supervisor utilities."""
        self.hooks = hooks
        self.registry = registry
        self.engine = engine
        self.monitor = monitor
        self.reliability_manager = reliability_manager
        self.execution_engine = execution_engine
        self.error_handler = error_handler
    
    async def run_hooks(self, event: str, state: DeepAgentState, **kwargs) -> None:
        """Run registered hooks for an event."""
        handlers = self.hooks.get(event, [])
        for handler in handlers:
            await self._execute_single_hook(handler, event, state, **kwargs)

    async def _execute_single_hook(self, handler, event: str, 
                                  state: DeepAgentState, **kwargs) -> None:
        """Execute a single hook with error handling."""
        try:
            await handler(state, **kwargs)
        except Exception as e:
            logger.error(f"Hook {handler.__name__} failed: {e}")
            if event == "on_error":
                raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive supervisor statistics."""
        legacy_stats = self._get_legacy_stats()
        if self.monitor:
            modern_stats = self.get_health_status()
            return {**legacy_stats, "modern_execution": modern_stats}
        return legacy_stats
    
    def _get_legacy_stats(self) -> Dict[str, Any]:
        """Get legacy supervisor statistics."""
        return {
            "registered_agents": len(self.registry.agents),
            "active_runs": len(self.engine.active_runs),
            "completed_runs": len(self.engine.run_history),
            "hooks_registered": {k: len(v) for k, v in self.hooks.items()}
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status from modern execution infrastructure."""
        if not self.monitor:
            return {"error": "Modern monitoring not available"}
        
        return {
            "modern_health": self.monitor.get_health_status(),
            "reliability": self.reliability_manager.get_health_status() if self.reliability_manager else {},
            "execution_engine": self.execution_engine.get_health_status() if self.execution_engine else {},
            "error_handler": self.error_handler.get_health_status() if self.error_handler else {}
        }
    
    def get_performance_metrics(self, agent_name: str) -> Dict[str, Any]:
        """Get performance metrics from modern monitoring."""
        if not self.monitor:
            return {"error": "Modern monitoring not available"}
        return self.monitor.get_agent_performance_stats(agent_name)
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status from reliability manager."""
        if not self.reliability_manager:
            return {"error": "Reliability manager not available"}
        return self.reliability_manager.get_health_status().get("circuit_breaker", {})