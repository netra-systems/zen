"""
Agent Registry Module - Issue #485 Fix

This module provides a centralized registry for managing AI agents in the Netra platform.
Created to resolve missing import path issues in test infrastructure.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure  
- Business Goal: Enable reliable agent execution and validation testing
- Value Impact: Supports $500K+ ARR chat functionality through reliable agent management
- Strategic Impact: Foundation for all agent-based business value delivery

CRITICAL: This registry supports the Golden Path user flow:
Users login → AI agents process requests → Users receive AI responses
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Type, Union
from dataclasses import dataclass, field
from enum import Enum

# Setup logging
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration."""
    IDLE = "idle"
    BUSY = "busy"
    INITIALIZING = "initializing"
    ERROR = "error"
    OFFLINE = "offline"


class AgentType(Enum):
    """Agent type enumeration."""
    SUPERVISOR = "supervisor"
    TRIAGE = "triage"
    DATA_HELPER = "data_helper"
    OPTIMIZER = "optimizer"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    SYNTHETIC_DATA = "synthetic_data"
    CORPUS_ADMIN = "corpus_admin"


@dataclass
class AgentInfo:
    """Agent information structure."""
    agent_id: str
    agent_type: AgentType
    name: str
    description: str
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    execution_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "metadata": self.metadata
        }


class AgentRegistry:
    """
    Central registry for managing AI agents.
    
    This registry provides:
    - Agent registration and discovery
    - Status tracking and health monitoring
    - Execution metrics and performance data
    - Thread-safe operations for concurrent access
    - Integration with WebSocket events for real-time updates
    
    Features:
    - Automatic agent health monitoring
    - Performance metrics collection
    - Agent lifecycle management
    - Multi-user agent isolation
    - Real-time status updates via WebSocket
    
    Usage:
        registry = AgentRegistry()
        agent_id = registry.register_agent(AgentType.TRIAGE, "Triage Agent")
        registry.update_agent_status(agent_id, AgentStatus.BUSY)
        agent_info = registry.get_agent_info(agent_id)
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, AgentInfo] = {}
        self._agent_instances: Dict[str, Any] = {}  # Store actual agent instances
        self._lock = threading.Lock()
        self._websocket_manager = None
        
        # Registry metadata
        self.created_at = datetime.now()
        self.last_cleanup = datetime.now()
        self.total_registrations = 0
        
        logger.info("AgentRegistry initialized")
    
    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager for real-time updates."""
        self._websocket_manager = websocket_manager
        logger.debug("WebSocket manager set for AgentRegistry")
    
    def register_agent(self, agent_type: AgentType, name: str, 
                      description: str = "", metadata: Optional[Dict[str, Any]] = None,
                      agent_instance: Optional[Any] = None) -> str:
        """
        Register a new agent in the registry.
        
        Args:
            agent_type: Type of agent
            name: Agent name
            description: Agent description
            metadata: Optional metadata
            agent_instance: Optional agent instance
            
        Returns:
            Agent ID for the registered agent
        """
        agent_id = f"{agent_type.value}_{uuid.uuid4().hex[:8]}"
        
        with self._lock:
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_type,
                name=name,
                description=description,
                metadata=metadata or {}
            )
            
            self._agents[agent_id] = agent_info
            if agent_instance:
                self._agent_instances[agent_id] = agent_instance
                
            self.total_registrations += 1
            
            logger.info(f"Agent registered: {agent_id} ({agent_type.value}: {name})")
            
            # Notify via WebSocket if available
            self._notify_agent_event("agent_registered", agent_info)
            
            return agent_id
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: ID of agent to unregister
            
        Returns:
            True if agent was unregistered, False if not found
        """
        with self._lock:
            if agent_id not in self._agents:
                logger.warning(f"Attempted to unregister non-existent agent: {agent_id}")
                return False
            
            agent_info = self._agents.pop(agent_id)
            self._agent_instances.pop(agent_id, None)
            
            logger.info(f"Agent unregistered: {agent_id} ({agent_info.agent_type.value})")
            
            # Notify via WebSocket if available
            self._notify_agent_event("agent_unregistered", agent_info)
            
            return True
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information by ID."""
        with self._lock:
            return self._agents.get(agent_id)
    
    def get_agent_instance(self, agent_id: str) -> Optional[Any]:
        """Get agent instance by ID."""
        with self._lock:
            return self._agent_instances.get(agent_id)
    
    def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        Update agent status.
        
        Args:
            agent_id: Agent ID
            status: New status
            
        Returns:
            True if updated, False if agent not found
        """
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            old_status = self._agents[agent_id].status
            self._agents[agent_id].status = status
            self._agents[agent_id].last_active = datetime.now()
            
            logger.debug(f"Agent status updated: {agent_id} ({old_status.value} -> {status.value})")
            
            # Notify via WebSocket if available
            self._notify_agent_event("agent_status_updated", self._agents[agent_id])
            
            return True
    
    def increment_execution_count(self, agent_id: str) -> bool:
        """Increment agent execution count."""
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            self._agents[agent_id].execution_count += 1
            self._agents[agent_id].last_active = datetime.now()
            return True
    
    def increment_error_count(self, agent_id: str) -> bool:
        """Increment agent error count."""
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            self._agents[agent_id].error_count += 1
            self._agents[agent_id].last_active = datetime.now()
            return True
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[AgentInfo]:
        """Get all agents of a specific type."""
        with self._lock:
            return [info for info in self._agents.values() if info.agent_type == agent_type]
    
    def get_agents_by_status(self, status: AgentStatus) -> List[AgentInfo]:
        """Get all agents with a specific status."""
        with self._lock:
            return [info for info in self._agents.values() if info.status == status]
    
    def get_all_agents(self) -> List[AgentInfo]:
        """Get information for all registered agents."""
        with self._lock:
            return list(self._agents.values())
    
    def get_available_agents(self, agent_type: Optional[AgentType] = None) -> List[AgentInfo]:
        """Get all available (idle) agents, optionally filtered by type."""
        with self._lock:
            agents = [info for info in self._agents.values() if info.status == AgentStatus.IDLE]
            if agent_type:
                agents = [info for info in agents if info.agent_type == agent_type]
            return agents
    
    def find_agent_by_name(self, name: str) -> Optional[AgentInfo]:
        """Find agent by name."""
        with self._lock:
            for info in self._agents.values():
                if info.name == name:
                    return info
            return None
    
    def cleanup_inactive_agents(self, inactive_threshold: timedelta = timedelta(hours=1)):
        """
        Clean up agents that have been inactive for too long.
        
        Args:
            inactive_threshold: Time threshold for considering agents inactive
        """
        current_time = datetime.now()
        inactive_agents = []
        
        with self._lock:
            for agent_id, info in self._agents.items():
                if (current_time - info.last_active) > inactive_threshold:
                    inactive_agents.append(agent_id)
        
        # Unregister inactive agents
        for agent_id in inactive_agents:
            logger.info(f"Cleaning up inactive agent: {agent_id}")
            self.unregister_agent(agent_id)
        
        self.last_cleanup = current_time
        
        if inactive_agents:
            logger.info(f"Cleaned up {len(inactive_agents)} inactive agents")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            stats = {
                "total_agents": len(self._agents),
                "total_registrations": self.total_registrations,
                "agents_by_type": {},
                "agents_by_status": {},
                "total_executions": 0,
                "total_errors": 0,
                "created_at": self.created_at.isoformat(),
                "last_cleanup": self.last_cleanup.isoformat()
            }
            
            # Calculate stats
            for info in self._agents.values():
                # By type
                type_name = info.agent_type.value
                stats["agents_by_type"][type_name] = stats["agents_by_type"].get(type_name, 0) + 1
                
                # By status
                status_name = info.status.value
                stats["agents_by_status"][status_name] = stats["agents_by_status"].get(status_name, 0) + 1
                
                # Execution counts
                stats["total_executions"] += info.execution_count
                stats["total_errors"] += info.error_count
            
            return stats
    
    def _notify_agent_event(self, event_type: str, agent_info: AgentInfo):
        """Notify WebSocket clients of agent events."""
        if not self._websocket_manager:
            return
        
        try:
            # Send agent event via WebSocket
            event_data = {
                "type": event_type,
                "agent": agent_info.to_dict(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Async call to WebSocket manager (don't await in sync method)
            import asyncio
            if hasattr(self._websocket_manager, 'broadcast'):
                # Schedule the coroutine to run in the event loop
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._websocket_manager.broadcast(event_data))
                except RuntimeError:
                    # No event loop running, skip WebSocket notification
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to notify agent event via WebSocket: {e}")
    
    def __len__(self) -> int:
        """Return number of registered agents."""
        with self._lock:
            return len(self._agents)
    
    def __contains__(self, agent_id: str) -> bool:
        """Check if agent ID is registered."""
        with self._lock:
            return agent_id in self._agents


# Global agent registry instance - Issue #485 fix
agent_registry = AgentRegistry()


# Convenience functions for common operations
def register_agent(agent_type: Union[AgentType, str], name: str, 
                  description: str = "", metadata: Optional[Dict[str, Any]] = None,
                  agent_instance: Optional[Any] = None) -> str:
    """Register an agent with the global registry."""
    if isinstance(agent_type, str):
        agent_type = AgentType(agent_type)
    return agent_registry.register_agent(agent_type, name, description, metadata, agent_instance)


def get_agent_info(agent_id: str) -> Optional[AgentInfo]:
    """Get agent info from the global registry."""
    return agent_registry.get_agent_info(agent_id)


def update_agent_status(agent_id: str, status: Union[AgentStatus, str]) -> bool:
    """Update agent status in the global registry."""
    if isinstance(status, str):
        status = AgentStatus(status)
    return agent_registry.update_agent_status(agent_id, status)


def get_available_agents(agent_type: Optional[Union[AgentType, str]] = None) -> List[AgentInfo]:
    """Get available agents from the global registry."""
    if isinstance(agent_type, str):
        agent_type = AgentType(agent_type)
    return agent_registry.get_available_agents(agent_type)


def cleanup_inactive_agents():
    """Clean up inactive agents in the global registry."""
    agent_registry.cleanup_inactive_agents()


# Export all public classes and functions for Issue #485 compatibility
__all__ = [
    'AgentRegistry',
    'AgentInfo',
    'AgentStatus',
    'AgentType',
    'agent_registry',
    'register_agent',
    'get_agent_info',
    'update_agent_status',
    'get_available_agents',
    'cleanup_inactive_agents'
]