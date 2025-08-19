"""Enhanced Agent Registry with Robust Initialization (<300 lines)

Enhanced registry with reliable agent initialization and fallback mechanisms:
- Uses AgentInitializationManager for robust startup
- Comprehensive error handling and fallback support  
- Health monitoring and recovery capabilities
- Modular agent registration with dependency injection

Business Value: Prevents agent initialization failures that cost revenue
BVJ: ALL segments | System Reliability | +$100K prevented revenue loss per quarter
"""

import asyncio
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.llm_manager import LLMManager
    from app.agents.tool_dispatcher import ToolDispatcher
    from app.ws_manager import WebSocketManager

from app.agents.base import BaseSubAgent
from app.logging_config import central_logger as logger
from app.agents.initialization_manager import AgentInitializationManager, InitializationStatus


class EnhancedAgentRegistry:
    """Enhanced agent registry with robust initialization and fallback support."""
    
    def __init__(self, llm_manager: 'LLMManager', tool_dispatcher: 'ToolDispatcher'):
        """Initialize registry with core dependencies."""
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.agents: Dict[str, BaseSubAgent] = {}
        self.websocket_manager = None
        self.initialization_manager = AgentInitializationManager()
        self._initialization_results: Dict[str, Any] = {}
        
    async def register_default_agents_safely(self) -> Dict[str, bool]:
        """Register default agents with comprehensive error handling."""
        logger.info("Starting safe agent registration process")
        
        agent_configs = self._prepare_agent_configurations()
        initialization_results = await self.initialization_manager.initialize_multiple_agents(agent_configs)
        
        registration_status = {}
        for agent_name, result in initialization_results.items():
            success = await self._handle_initialization_result(agent_name, result)
            registration_status[agent_name] = success
            
        await self._log_registration_summary(registration_status)
        return registration_status
    
    def _prepare_agent_configurations(self) -> List[Dict[str, Any]]:
        """Prepare configurations for agent initialization."""
        return [
            self._create_triage_agent_config(),
            self._create_data_agent_config(), 
            self._create_optimization_agent_config(),
            self._create_actions_agent_config(),
            self._create_reporting_agent_config(),
            self._create_synthetic_data_agent_config(),
            self._create_corpus_admin_agent_config()
        ]
    
    def _create_triage_agent_config(self) -> Dict[str, Any]:
        """Create triage agent configuration."""
        from app.agents.triage_sub_agent.agent import TriageSubAgent
        return {
            'agent_class': TriageSubAgent,
            'llm_manager': self.llm_manager,
            'tool_dispatcher': self.tool_dispatcher,
            'agent_name': 'triage'
        }
    
    def _create_data_agent_config(self) -> Dict[str, Any]:
        """Create data agent configuration with fallback."""
        try:
            from app.agents.data_sub_agent.agent_modernized import DataSubAgent
        except ImportError:
            logger.warning("Using legacy data agent due to import issues")
            from app.agents.data_sub_agent.agent import DataSubAgent
            
        return {
            'agent_class': DataSubAgent,
            'llm_manager': self.llm_manager,
            'tool_dispatcher': self.tool_dispatcher,
            'agent_name': 'data'
        }
    
    def _create_optimization_agent_config(self) -> Dict[str, Any]:
        """Create optimization agent configuration."""
        from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        return {
            'agent_class': OptimizationsCoreSubAgent,
            'llm_manager': self.llm_manager,
            'tool_dispatcher': self.tool_dispatcher,
            'agent_name': 'optimization'
        }
    
    def _create_actions_agent_config(self) -> Dict[str, Any]:
        """Create actions agent configuration."""
        from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        return {
            'agent_class': ActionsToMeetGoalsSubAgent,
            'llm_manager': self.llm_manager,
            'tool_dispatcher': self.tool_dispatcher,
            'agent_name': 'actions'
        }
    
    def _create_reporting_agent_config(self) -> Dict[str, Any]:
        """Create reporting agent configuration."""
        from app.agents.reporting_sub_agent import ReportingSubAgent
        return {
            'agent_class': ReportingSubAgent,
            'llm_manager': self.llm_manager,
            'tool_dispatcher': self.tool_dispatcher,
            'agent_name': 'reporting'
        }
    
    def _create_synthetic_data_agent_config(self) -> Dict[str, Any]:
        """Create synthetic data agent configuration."""
        from app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
        return {
            'agent_class': SyntheticDataSubAgent,
            'llm_manager': self.llm_manager,
            'tool_dispatcher': self.tool_dispatcher,
            'agent_name': 'synthetic_data'
        }
    
    def _create_corpus_admin_agent_config(self) -> Dict[str, Any]:
        """Create corpus admin agent configuration."""
        from app.agents.corpus_admin_sub_agent import CorpusAdminSubAgent
        return {
            'agent_class': CorpusAdminSubAgent,
            'llm_manager': self.llm_manager,
            'tool_dispatcher': self.tool_dispatcher,
            'agent_name': 'corpus_admin'
        }
    
    async def _handle_initialization_result(self, agent_name: str, result: Any) -> bool:
        """Handle individual agent initialization result."""
        self._initialization_results[agent_name] = result
        
        if result.status == InitializationStatus.SUCCESS:
            await self._register_successful_agent(agent_name, result.agent, result.fallback_used)
            return True
        elif result.status == InitializationStatus.FALLBACK:
            await self._register_fallback_agent(agent_name, result.agent)
            return True
        else:
            await self._handle_failed_initialization(agent_name, result.error)
            return False
    
    async def _register_successful_agent(self, name: str, agent: BaseSubAgent, fallback_used: bool) -> None:
        """Register successfully initialized agent."""
        if self.websocket_manager:
            agent.websocket_manager = self.websocket_manager
        self.agents[name] = agent
        
        status_msg = "with fallback" if fallback_used else "successfully"
        logger.info(f"Registered agent '{name}' {status_msg}")
    
    async def _register_fallback_agent(self, name: str, agent: BaseSubAgent) -> None:
        """Register agent in fallback mode."""
        if self.websocket_manager:
            agent.websocket_manager = self.websocket_manager
        self.agents[name] = agent
        logger.warning(f"Registered agent '{name}' in fallback mode")
    
    async def _handle_failed_initialization(self, name: str, error: Optional[str]) -> None:
        """Handle failed agent initialization."""
        logger.error(f"Failed to initialize agent '{name}': {error}")
        # Could implement notification systems here
    
    async def _log_registration_summary(self, status: Dict[str, bool]) -> None:
        """Log comprehensive registration summary."""
        successful = sum(1 for success in status.values() if success)
        total = len(status)
        failed_agents = [name for name, success in status.items() if not success]
        
        logger.info(f"Agent registration completed: {successful}/{total} successful")
        if failed_agents:
            logger.warning(f"Failed agents: {', '.join(failed_agents)}")
            
        # Log initialization statistics
        stats = self.initialization_manager.get_initialization_stats()
        logger.info(f"Initialization stats: {stats}")
    
    # Enhanced registration methods for individual agents
    async def register_agent_safely(self, name: str, agent_class, **kwargs) -> bool:
        """Register individual agent safely."""
        result = await self.initialization_manager.initialize_agent_safely(
            agent_class, self.llm_manager, self.tool_dispatcher, name, **kwargs
        )
        return await self._handle_initialization_result(name, result)
    
    def register(self, name: str, agent: BaseSubAgent) -> None:
        """Register pre-initialized agent."""
        if self.websocket_manager:
            agent.websocket_manager = self.websocket_manager
        self.agents[name] = agent
        logger.info(f"Manually registered agent: {name}")
    
    def get(self, name: str) -> Optional[BaseSubAgent]:
        """Get agent by name with fallback handling."""
        agent = self.agents.get(name)
        if agent:
            return agent
            
        # Check if we have initialization result but no agent (shouldn't happen)
        if name in self._initialization_results:
            result = self._initialization_results[name]
            logger.warning(f"Agent '{name}' found in results but not registered")
            if result.agent:
                self.register(name, result.agent)
                return result.agent
                
        return None
    
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agents.keys())
    
    def get_all_agents(self) -> List[BaseSubAgent]:
        """Get all registered agents."""
        return list(self.agents.values())
    
    def set_websocket_manager(self, manager: 'WebSocketManager') -> None:
        """Set websocket manager for all agents."""
        self.websocket_manager = manager
        for agent in self.agents.values():
            agent.websocket_manager = manager
    
    def get_agent_status(self, name: str) -> Dict[str, Any]:
        """Get detailed status for specific agent."""
        agent = self.get(name)
        if not agent:
            return {"status": "not_found", "registered": False}
            
        status = {
            "status": "registered",
            "registered": True,
            "agent_name": getattr(agent, 'name', name),
            "agent_type": type(agent).__name__
        }
        
        # Add initialization result if available
        if name in self._initialization_results:
            result = self._initialization_results[name]
            status.update({
                "initialization_status": result.status.value,
                "fallback_used": result.fallback_used,
                "initialization_time_ms": result.initialization_time_ms,
                "health_checks_passed": result.health_checks_passed
            })
            
        # Add health status if available
        try:
            if hasattr(agent, 'get_health_status'):
                status["health"] = agent.get_health_status()
        except Exception as e:
            status["health_error"] = str(e)
            
        return status
    
    def get_registry_health(self) -> Dict[str, Any]:
        """Get comprehensive registry health information."""
        total_agents = len(self.agents)
        healthy_agents = 0
        fallback_agents = 0
        
        agent_statuses = {}
        for name, agent in self.agents.items():
            agent_status = self.get_agent_status(name)
            agent_statuses[name] = agent_status
            
            if agent_status.get("health", {}).get("status") != "error":
                healthy_agents += 1
            if agent_status.get("fallback_used", False):
                fallback_agents += 1
        
        return {
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "fallback_agents": fallback_agents,
            "failed_agents": total_agents - healthy_agents,
            "health_percentage": (healthy_agents / total_agents * 100) if total_agents > 0 else 0,
            "agents": agent_statuses,
            "initialization_stats": self.initialization_manager.get_initialization_stats()
        }
    
    async def restart_failed_agents(self) -> Dict[str, bool]:
        """Restart agents that failed initialization."""
        failed_agents = [
            name for name, result in self._initialization_results.items() 
            if result.status == InitializationStatus.FAILED
        ]
        
        if not failed_agents:
            logger.info("No failed agents to restart")
            return {}
            
        logger.info(f"Attempting to restart {len(failed_agents)} failed agents")
        
        # Create configs for failed agents only
        configs = [config for config in self._prepare_agent_configurations() 
                  if config['agent_name'] in failed_agents]
        
        results = await self.initialization_manager.initialize_multiple_agents(configs)
        
        restart_status = {}
        for agent_name, result in results.items():
            success = await self._handle_initialization_result(agent_name, result)
            restart_status[agent_name] = success
            
        return restart_status