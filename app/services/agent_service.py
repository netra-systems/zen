"""Agent service module - aggregates all agent service components.

This module provides a centralized import location for all agent-related 
service components that have been split into focused modules for better maintainability.
"""

# Core agent service
from .agent_service_core import AgentService

# Factory functions
from .agent_service_factory import get_agent_service

# Streaming components
from .agent_service_streaming import AgentResponseProcessor

# Backward compatibility
from .agent_service_compat import process_message, generate_stream

__all__ = [
    'AgentService',
    'get_agent_service',
    'AgentResponseProcessor',
    'process_message',
    'generate_stream'
]