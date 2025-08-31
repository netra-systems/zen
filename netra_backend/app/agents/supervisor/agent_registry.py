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
        logger.info(f"Successfully registered {len(self.agents)} agents")
    
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
        logger.debug(f"Registered agent: {name}")
    
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
        """Set websocket manager for all agents and enhance tool dispatcher with concurrency optimization."""
        self.websocket_manager = manager
        
        # CRITICAL: Enhance tool dispatcher with WebSocket notifications
        # This enables real-time tool execution events
        if self.tool_dispatcher and manager:
            from netra_backend.app.agents.unified_tool_execution import (
                enhance_tool_dispatcher_with_notifications
            )
            logger.info("Enhancing tool dispatcher with WebSocket notifications")
            enhance_tool_dispatcher_with_notifications(self.tool_dispatcher, manager)
            
            # CONCURRENCY OPTIMIZATION: Verify enhancement succeeded
            if not getattr(self.tool_dispatcher, '_websocket_enhanced', False):
                logger.error("CRITICAL: Tool dispatcher enhancement failed - WebSocket events will not work")
                raise RuntimeError("Tool dispatcher WebSocket enhancement failed")
            else:
                logger.info("✅ Tool dispatcher WebSocket enhancement verified")
        elif manager is None:
            # Graceful degradation when manager is None - log but don't fail
            logger.warning("WebSocket manager is None - agent events will not be available")
        
        # Set WebSocket manager for all registered agents with verification
        agent_count = 0
        for agent_name, agent in self.agents.items():
            try:
                agent.websocket_manager = manager
                agent_count += 1
            except Exception as e:
                logger.warning(f"Failed to set WebSocket manager for agent {agent_name}: {e}")
        
        if manager is not None:
            logger.info(f"✅ WebSocket manager set for {agent_count}/{len(self.agents)} agents")
        else:
            logger.info(f"WebSocket manager set to None for {agent_count}/{len(self.agents)} agents")