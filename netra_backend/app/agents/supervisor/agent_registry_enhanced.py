"""Enhanced Agent Registry with safety features and health monitoring.

This module provides an enhanced version of the agent registry with:
- Safe agent registration with error handling
- Health monitoring capabilities
- Async registration support
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

if TYPE_CHECKING:
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EnhancedAgentRegistry:
    """Enhanced agent registry with safety features and health monitoring."""
    
    def __init__(self, llm_manager: 'LLMManager', tool_dispatcher: 'ToolDispatcher'):
        """Initialize the enhanced agent registry.
        
        Args:
            llm_manager: The LLM manager instance
            tool_dispatcher: The tool dispatcher instance
        """
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.agents: Dict[str, BaseSubAgent] = {}
        self.websocket_manager = None
        self.registration_errors: Dict[str, str] = {}
        
    async def register_agent_safely(self, name: str, agent_class: Type[BaseSubAgent], **kwargs) -> bool:
        """Register an agent safely with error handling.
        
        Args:
            name: Name of the agent
            agent_class: The agent class to instantiate
            **kwargs: Additional keyword arguments for agent initialization
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            logger.info(f"Attempting to register agent: {name}")
            
            # Create agent instance
            agent = agent_class(
                self.llm_manager,
                self.tool_dispatcher,
                **kwargs
            )
            
            # Set websocket manager if available
            if self.websocket_manager:
                agent.websocket_manager = self.websocket_manager
                
            # Store the agent
            self.agents[name] = agent
            
            # Clear any previous registration errors
            self.registration_errors.pop(name, None)
            
            logger.info(f"Successfully registered agent: {name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to register agent {name}: {str(e)}"
            logger.error(error_msg)
            self.registration_errors[name] = error_msg
            return False
            
    def get(self, name: str) -> Optional[BaseSubAgent]:
        """Get agent by name.
        
        Args:
            name: Name of the agent to retrieve
            
        Returns:
            The agent instance if found, None otherwise
        """
        return self.agents.get(name)
        
    def get_registry_health(self) -> Dict[str, Any]:
        """Get the health status of the registry.
        
        Returns:
            Dictionary containing health information
        """
        healthy_agents = 0
        agent_health_details = {}
        
        for name, agent in self.agents.items():
            try:
                if hasattr(agent, 'get_health_status'):
                    health_status = agent.get_health_status()
                    agent_health_details[name] = health_status
                    # Consider agent healthy if it has a 'status' field that's not 'error' or 'failed'
                    if isinstance(health_status, dict):
                        status = health_status.get('status', 'unknown')
                        if status not in ['error', 'failed', 'critical']:
                            healthy_agents += 1
                    else:
                        healthy_agents += 1
                else:
                    # Agent doesn't have health status method, assume healthy if it exists
                    healthy_agents += 1
                    agent_health_details[name] = {"status": "unknown"}
            except Exception as e:
                logger.warning(f"Failed to get health status for agent {name}: {e}")
                agent_health_details[name] = {"status": "error", "error": str(e)}
        
        return {
            "total_agents": len(self.agents),
            "healthy_agents": healthy_agents,
            "failed_registrations": len(self.registration_errors),
            "agent_health": agent_health_details,
            "registration_errors": self.registration_errors.copy()
        }
        
    def list_agents(self) -> list[str]:
        """List all registered agent names.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())
        
    def get_all_agents(self) -> list[BaseSubAgent]:
        """Get all registered agents.
        
        Returns:
            List of agent instances
        """
        return list(self.agents.values())
        
    def set_websocket_manager(self, manager) -> None:
        """Set websocket manager for all agents.
        
        Args:
            manager: The websocket manager instance
        """
        self.websocket_manager = manager
        for agent in self.agents.values():
            if hasattr(agent, 'websocket_manager'):
                agent.websocket_manager = manager
                
    def remove_agent(self, name: str) -> bool:
        """Remove an agent from the registry.
        
        Args:
            name: Name of the agent to remove
            
        Returns:
            bool: True if agent was removed, False if not found
        """
        if name in self.agents:
            del self.agents[name]
            logger.info(f"Removed agent: {name}")
            return True
        return False