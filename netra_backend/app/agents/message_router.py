"""Message Router - Agents Module Compatibility

This module provides compatibility imports for agent tests that expect
MessageRouter in the agents module. The actual implementation is in
the websocket services module.
"""

# Import the actual MessageRouter implementation
from netra_backend.app.services.websocket.message_router import MessageRouter

# Re-export for compatibility
__all__ = ['MessageRouter']