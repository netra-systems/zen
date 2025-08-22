"""Enhanced WebSocket message handler - Backward Compatibility Layer.

Provides backward compatibility imports while delegating to focused modules.
Keeps file under 300 lines as required by architecture standards.
"""

# Import all classes and functions from focused modules for backward compatibility
from netra_backend.app.websocket.message_handler_core import ReliableMessageHandler
from netra_backend.app.websocket.message_router import MessageTypeRouter

# Create default instances for backward compatibility
default_reliable_handler = ReliableMessageHandler()
default_message_router = MessageTypeRouter()

# Re-export all classes and instances for backward compatibility
__all__ = [
    'ReliableMessageHandler',
    'MessageTypeRouter',
    'default_reliable_handler',
    'default_message_router'
]