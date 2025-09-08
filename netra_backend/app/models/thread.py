# Thread models - import from canonical sources
from netra_backend.app.schemas.core_models import Thread, ThreadMetadata

# Stub Message class for backward compatibility
class Message:
    """Message model for thread integration tests."""
    
    def __init__(self, content: str = "", role: str = "user", thread_id: str = None):
        self.content = content
        self.role = role
        self.thread_id = thread_id
        self.id = None
        self.created_at = None