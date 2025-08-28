from netra_backend.app.core.isolated_environment import get_env
"""Base Agent Core Module

Main base agent class that composes functionality from focused modular components.
"""

from abc import ABC
from typing import Dict, Optional

from netra_backend.app.agents.agent_communication import AgentCommunicationMixin

# Import modular components
from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
from netra_backend.app.agents.agent_observability import AgentObservabilityMixin
from netra_backend.app.agents.agent_state import AgentStateMixin
from netra_backend.app.agents.interfaces import BaseAgentProtocol
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.config import get_config
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import generate_llm_correlation_id
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import SubAgentLifecycle

# Import timing components
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector


class BaseSubAgent(
    AgentLifecycleMixin, 
    AgentCommunicationMixin, 
    AgentStateMixin, 
    AgentObservabilityMixin,
    ABC
):
    """Base agent class combining all agent functionality through modular mixins"""
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, name: str = "BaseSubAgent", description: str = "This is the base sub-agent."):
        self.llm_manager = llm_manager
        self.state = SubAgentLifecycle.PENDING
        self.name = name
        self.description = description
        self.start_time = None
        self.end_time = None
        self.context = {}  # Protected context for this agent
        self.websocket_manager = None  # Will be set by Supervisor
        self.user_id = None  # Will be set by Supervisor for WebSocket messages
        self.logger = central_logger.get_logger(name)
        self.correlation_id = generate_llm_correlation_id()  # Unique ID for tracing
        self._subagent_logging_enabled = self._get_subagent_logging_enabled()
        
        # Initialize timing collector
        self.timing_collector = ExecutionTimingCollector(agent_name=name)

    def _get_subagent_logging_enabled(self) -> bool:
        """Get subagent logging configuration setting."""
        import os
        # Skip heavy config loading during test collection
        if get_env().get('TEST_COLLECTION_MODE') == '1':
            return False
        try:
            config = get_config()
            return getattr(config, 'subagent_logging_enabled', True)
        except Exception:
            return True  # Default to enabled if config unavailable

    async def shutdown(self) -> None:
        """Graceful shutdown of the agent."""
        self.logger.info(f"Shutting down {self.name}")
        self.set_state(SubAgentLifecycle.SHUTDOWN)
        # Clear any remaining context
        self.context.clear()
        # Subclasses can override to add specific shutdown logic