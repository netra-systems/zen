"""Agent Communication Manager

Provides a manager interface for agent communication functionality.
This is a compatibility shim for tests that expect an AgentCommunicationManager class.
"""

import asyncio
from typing import Any, Dict, List, Optional
from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentCommunicationManager:
    """Manager for agent-to-agent communication.
    
    This class provides a centralized interface for managing communication
    between agents in the system. It's primarily used for testing and
    coordination scenarios.
    """
    
    def __init__(self, websocket_manager=None):
        """Initialize the communication manager.
        
        Args:
            websocket_manager: WebSocket manager instance for communication
        """
        self.websocket_manager = websocket_manager
        self.active_connections: Dict[str, Any] = {}
        self.message_queue: List[Dict[str, Any]] = []
        self.communication_metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'active_agents': 0
        }
        
    async def initialize(self) -> None:
        """Initialize the communication manager."""
        logger.info("Initializing AgentCommunicationManager")
        # Placeholder for actual initialization logic
        
    async def register_agent(self, agent_id: str, agent_instance: Any) -> bool:
        """Register an agent for communication.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_instance: The agent instance
            
        Returns:
            True if registration successful
        """
        try:
            self.active_connections[agent_id] = agent_instance
            self.communication_metrics['active_agents'] = len(self.active_connections)
            logger.info(f"Registered agent {agent_id} for communication")
            return True
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from communication.
        
        Args:
            agent_id: Agent identifier to unregister
            
        Returns:
            True if unregistration successful
        """
        try:
            if agent_id in self.active_connections:
                del self.active_connections[agent_id]
                self.communication_metrics['active_agents'] = len(self.active_connections)
                logger.info(f"Unregistered agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def send_message(self, from_agent: str, to_agent: str, message: Dict[str, Any]) -> bool:
        """Send a message from one agent to another.
        
        Args:
            from_agent: Source agent ID
            to_agent: Target agent ID
            message: Message content
            
        Returns:
            True if message sent successfully
        """
        try:
            if to_agent not in self.active_connections:
                logger.warning(f"Target agent {to_agent} not found")
                return False
                
            # Simulate message sending
            message_envelope = {
                'from': from_agent,
                'to': to_agent,
                'content': message,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            self.message_queue.append(message_envelope)
            self.communication_metrics['messages_sent'] += 1
            
            logger.debug(f"Message sent from {from_agent} to {to_agent}")
            return True
            
        except Exception as e:
            self.communication_metrics['messages_failed'] += 1
            logger.error(f"Failed to send message from {from_agent} to {to_agent}: {e}")
            return False
    
    async def broadcast_message(self, from_agent: str, message: Dict[str, Any]) -> int:
        """Broadcast a message to all registered agents.
        
        Args:
            from_agent: Source agent ID
            message: Message content
            
        Returns:
            Number of agents that received the message
        """
        sent_count = 0
        for agent_id in self.active_connections:
            if agent_id != from_agent:  # Don't send to self
                success = await self.send_message(from_agent, agent_id, message)
                if success:
                    sent_count += 1
        
        logger.info(f"Broadcast message from {from_agent} to {sent_count} agents")
        return sent_count
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get communication metrics.
        
        Returns:
            Dictionary of current metrics
        """
        return {
            **self.communication_metrics,
            'queue_size': len(self.message_queue),
            'registered_agents': list(self.active_connections.keys())
        }
    
    def get_active_agents(self) -> List[str]:
        """Get list of active agent IDs.
        
        Returns:
            List of registered agent IDs
        """
        return list(self.active_connections.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on communication system.
        
        Returns:
            Health status information
        """
        return {
            'healthy': True,
            'active_agents': len(self.active_connections),
            'queue_size': len(self.message_queue),
            'metrics': self.communication_metrics
        }
    
    async def shutdown(self) -> None:
        """Shutdown the communication manager."""
        logger.info("Shutting down AgentCommunicationManager")
        self.active_connections.clear()
        self.message_queue.clear()
        self.communication_metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'active_agents': 0
        }


# For compatibility with existing imports
AgentCommunicationMixin = AgentCommunicationMixin