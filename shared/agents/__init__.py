"""
Shared agents module providing unified base classes for all agent development.

This module eliminates duplicate agent base class patterns by providing
standardized base classes that all agents must inherit from.
"""

from .base_agent import (
    BaseAgent,
    LLMAgent,
    SubAgent,
    BaseSubAgent,  # Backward compatibility
    AgentState,
    AgentFactory
)

__all__ = [
    'BaseAgent',
    'LLMAgent', 
    'SubAgent',
    'BaseSubAgent',  # Backward compatibility
    'AgentState',
    'AgentFactory'
]