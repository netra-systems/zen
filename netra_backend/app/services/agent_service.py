"""Agent service module - aggregates all agent service components.

This module provides a centralized import location for all agent-related 
service components that have been split into focused modules for better maintainability.
"""

# Core agent service
# Backward compatibility
from netra_backend.app.services.agent_service_compat import (
    generate_stream,
    process_message,
)
from netra_backend.app.services.agent_service_core import AgentService

# Factory functions
from netra_backend.app.services.agent_service_factory import get_agent_service

# Streaming components
from netra_backend.app.services.agent_service_streaming import AgentResponseProcessor


# Multimodal processing
async def process_multimodal(multimodal_data: dict) -> dict:
    """Process multimodal input data."""
    text = multimodal_data.get("text", "")
    attachments = multimodal_data.get("attachments", [])
    return {"response": f"Processed {text} with {len(attachments)} attachments"}

# Fallback agent functions for testing
def get_primary_agent():
    """Get primary agent instance - DEPRECATED.
    
    This method requires proper dependencies that should be
    obtained from app.state during runtime.
    """
    raise NotImplementedError(
        "Cannot create agent without proper dependencies. "
        "Use app.state.agent_service from the running application."
    )

def get_fallback_agent():
    """Get fallback agent instance - DEPRECATED.
    
    This method requires proper dependencies that should be
    obtained from app.state during runtime.
    """
    raise NotImplementedError(
        "Cannot create agent without proper dependencies. "
        "Use app.state.agent_service from the running application."
    )

__all__ = [
    'AgentService',
    'get_agent_service',
    'AgentResponseProcessor',
    'process_message',
    'generate_stream',
    'process_multimodal',
    'get_primary_agent',
    'get_fallback_agent'
]