"""Supervisor initialization helpers ( <= 300 lines).

Business Value: Modular initialization patterns for supervisor agent setup.
Supports clean architecture and 25-line function compliance.
"""

from typing import Any, Tuple

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorInitializationHelpers:
    """Helper class for supervisor initialization operations."""
    
    @staticmethod
    def create_reliability_manager():
        """Create reliability manager with circuit breaker and retry configs."""
        from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
        from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
        from netra_backend.app.schemas.shared_types import RetryConfig
        circuit_config = CircuitBreakerConfig(name="Supervisor", failure_threshold=5, recovery_timeout=60)
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_breaker_config=circuit_config, retry_config=retry_config)
    
    @staticmethod
    def init_utilities_for_supervisor(supervisor):
        """Initialize utilities with modern execution components."""
        from netra_backend.app.agents.supervisor.supervisor_utilities import (
            SupervisorUtilities,
        )
        return SupervisorUtilities(supervisor.hooks, supervisor.registry, supervisor.engine,
            supervisor.monitor, supervisor.reliability_manager, supervisor.execution_engine, 
            supervisor.error_handler)
    
    @staticmethod
    def init_helper_components(supervisor) -> Tuple[Any, Any, Any, Any]:
        """Initialize all helper components for supervisor."""
        from netra_backend.app.agents.supervisor.agent_routing import (
            SupervisorAgentRouter,
        )
        from netra_backend.app.agents.supervisor.modern_execution_helpers import (
            SupervisorExecutionHelpers,
        )
        from netra_backend.app.agents.supervisor.supervisor_completion_helpers import (
            SupervisorCompletionHelpers,
        )
        from netra_backend.app.agents.supervisor.workflow_execution import (
            SupervisorWorkflowExecutor,
        )
        return (SupervisorExecutionHelpers(supervisor), SupervisorWorkflowExecutor(supervisor),
                SupervisorAgentRouter(supervisor), SupervisorCompletionHelpers(supervisor))