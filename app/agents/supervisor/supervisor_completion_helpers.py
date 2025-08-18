"""Supervisor completion and statistics helpers (≤300 lines).

Business Value: Centralized completion tracking and statistics for supervisor operations.
Supports monitoring and observability requirements for Enterprise segment.
"""

from typing import Dict, Any

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorCompletionHelpers:
    """Helper class for supervisor completion and statistics operations."""
    
    def __init__(self, supervisor_agent):
        """Initialize completion helpers with supervisor reference."""
        self.supervisor = supervisor_agent
        self.utilities = supervisor_agent.utilities
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive supervisor statistics."""
        return self.utilities.get_stats()
    
    def get_agent_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status from modern execution infrastructure."""
        return {"agent": self.supervisor.name, **self.utilities.get_health_status()}
    
    def get_agent_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from modern monitoring."""
        return self.utilities.get_performance_metrics(self.supervisor.name)
    
    def get_reliability_status(self) -> Dict[str, Any]:
        """Get circuit breaker status from reliability manager."""
        return self.utilities.get_circuit_breaker_status()