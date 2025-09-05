"""Agent interfaces module - restored to fix critical imports.

This module provides the base protocol interfaces for agents.
"""

from typing import Protocol, Any, Dict, Optional, runtime_checkable
from abc import abstractmethod


@runtime_checkable
class BaseAgentProtocol(Protocol):
    """Protocol defining the base agent interface."""
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the agent's main logic."""
        ...
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the agent's name."""
        ...
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get the agent's configuration."""
        ...


@runtime_checkable
class AgentStateProtocol(Protocol):
    """Protocol defining agent state interface."""
    
    @abstractmethod
    def merge_from(self, other: "AgentStateProtocol") -> None:
        """Merge state from another state object."""
        ...
        
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        ...
        
    @abstractmethod
    def copy(self) -> "AgentStateProtocol":
        """Create a copy of the state."""
        ...