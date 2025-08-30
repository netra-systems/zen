"""Agent registry and management for supervisor."""

from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import (
    ActionsToMeetGoalsSubAgent,
)
from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.corpus_admin_sub_agent import CorpusAdminSubAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent

# DataSubAgent is imported later to avoid circular dependency
from netra_backend.app.agents.optimizations_core_sub_agent import (
    OptimizationsCoreSubAgent,
)
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent

# Import all sub-agents
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentRegistry:
    """Manages agent registration and lifecycle."""
    
    def __init__(self, llm_manager: 'LLMManager', tool_dispatcher: 'ToolDispatcher'):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.agents: Dict[str, BaseSubAgent] = {}
        self.websocket_manager = None
        self._agents_registered = False
        
    def register_default_agents(self) -> None:
        """Register default sub-agents"""
        if self._agents_registered:
            logger.debug("Agents already registered, skipping re-registration")
            return
        
        self._register_core_agents()
        self._register_auxiliary_agents()
        self._agents_registered = True
    
    def _register_core_agents(self) -> None:
        """Register core workflow agents."""
        # Import DataSubAgent here to avoid circular dependency
        from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
        
        self._register_workflow_agents(DataSubAgent)
    
    def _register_workflow_agents(self, DataSubAgent) -> None:
        """Register workflow agents with manager and dispatcher."""
        self._register_core_workflow_agents(DataSubAgent)
        self._register_optimization_agents()
    
    def _register_core_workflow_agents(self, DataSubAgent) -> None:
        """Register core workflow agents."""
        self.register("triage", TriageSubAgent(
            self.llm_manager, self.tool_dispatcher))
        self.register("data", DataSubAgent(
            self.llm_manager, self.tool_dispatcher))
    
    def _register_optimization_agents(self) -> None:
        """Register optimization and action agents."""
        self.register("optimization", OptimizationsCoreSubAgent(
            self.llm_manager, self.tool_dispatcher))
        self.register("actions", ActionsToMeetGoalsSubAgent(
            self.llm_manager, self.tool_dispatcher))
    
    def _register_auxiliary_agents(self) -> None:
        """Register auxiliary agents."""
        self._register_reporting_agent()
        self._register_data_helper_agent()
        self._register_synthetic_data_agent()
        self._register_corpus_admin_agent()
    
    def register(self, name: str, agent: BaseSubAgent) -> None:
        """Register a sub-agent"""
        if name in self.agents:
            logger.debug(f"Agent {name} already registered, skipping")
            return
            
        if self.websocket_manager:
            agent.websocket_manager = self.websocket_manager
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")
    
    def get(self, name: str) -> BaseSubAgent:
        """Get agent by name"""
        return self.agents.get(name)
    
    def list_agents(self) -> List[str]:
        """List registered agent names"""
        return list(self.agents.keys())
    
    def get_all_agents(self) -> List[BaseSubAgent]:
        """Get all registered agents"""
        return list(self.agents.values())
    
    def _register_reporting_agent(self) -> None:
        """Register reporting agent."""
        self.register("reporting", ReportingSubAgent(
            self.llm_manager, self.tool_dispatcher))
    
    def _register_synthetic_data_agent(self) -> None:
        """Register synthetic data agent."""
        self.register("synthetic_data", SyntheticDataSubAgent(
            self.llm_manager, self.tool_dispatcher))
    
    def _register_data_helper_agent(self) -> None:
        """Register data helper agent."""
        self.register("data_helper", DataHelperAgent(self.llm_manager, self.tool_dispatcher))
    
    def _register_corpus_admin_agent(self) -> None:
        """Register corpus admin agent."""
        self.register("corpus_admin", CorpusAdminSubAgent(
            self.llm_manager, self.tool_dispatcher))

    def set_websocket_manager(self, manager: 'WebSocketManager') -> None:
        """Set websocket manager for all agents"""
        self.websocket_manager = manager
        for agent in self.agents.values():
            agent.websocket_manager = manager