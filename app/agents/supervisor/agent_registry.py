"""Agent registry and management for supervisor."""

from typing import Dict, List, Any
from app.agents.base import BaseSubAgent
from app.logging_config import central_logger

# Import all sub-agents
from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.data_sub_agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent
from app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
from app.agents.corpus_admin_sub_agent import CorpusAdminSubAgent

logger = central_logger.get_logger(__name__)


class AgentRegistry:
    """Manages agent registration and lifecycle."""
    
    def __init__(self, llm_manager: Any, tool_dispatcher: Any):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.agents: Dict[str, BaseSubAgent] = {}
        self.websocket_manager = None
        
    def register_default_agents(self) -> None:
        """Register default sub-agents"""
        self.register("triage", TriageSubAgent(
            self.llm_manager, self.tool_dispatcher))
        self.register("data", DataSubAgent(
            self.llm_manager, self.tool_dispatcher))
        self.register("optimization", OptimizationsCoreSubAgent(
            self.llm_manager, self.tool_dispatcher))
        self.register("actions", ActionsToMeetGoalsSubAgent(
            self.llm_manager, self.tool_dispatcher))
        self.register("reporting", ReportingSubAgent(
            self.llm_manager, self.tool_dispatcher))
        self.register("synthetic_data", SyntheticDataSubAgent(
            self.llm_manager, self.tool_dispatcher))
        self.register("corpus_admin", CorpusAdminSubAgent(
            self.llm_manager, self.tool_dispatcher))
    
    def register(self, name: str, agent: BaseSubAgent) -> None:
        """Register a sub-agent"""
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
    
    def set_websocket_manager(self, manager: Any) -> None:
        """Set websocket manager for all agents"""
        self.websocket_manager = manager
        for agent in self.agents.values():
            agent.websocket_manager = manager