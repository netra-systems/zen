"""
SSOT conversation models using existing thread and message implementations.
"""

# SSOT imports from existing models
from netra_backend.app.schemas.core_models import Thread, Message
from netra_backend.app.models.user import User, UserSession

# Create aliases for backward compatibility
ConversationThread = Thread
ConversationMessage = Message

# Re-export existing models
__all__ = [
    'ConversationThread',
    'ConversationMessage', 
    'User',
    'UserSession'
]