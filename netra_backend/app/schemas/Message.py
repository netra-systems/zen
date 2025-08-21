"""Message type definitions - imports from single source of truth in registry.py"""

# Import all Message types from single source of truth  
# For backward compatibility, also expose Thread types
from netra_backend.app.schemas.registry import (
    Message,
    MessageMetadata,
    MessageType,
    Thread,
    ThreadMetadata,
)
