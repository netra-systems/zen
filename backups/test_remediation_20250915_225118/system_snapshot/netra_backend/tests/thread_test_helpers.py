"""Thread test helpers for testing thread-related functionality."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

def create_mock_thread(
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    title: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a mock thread object for testing."""
    return {
        "id": thread_id or str(uuid4()),
        "user_id": user_id or str(uuid4()),
        "title": title or "Test Thread",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "message_count": kwargs.get("message_count", 0),
        "is_active": kwargs.get("is_active", True),
        "metadata": kwargs.get("metadata", {}),
        **kwargs
    }

def setup_thread_repo_mock() -> AsyncMock:
    """Setup a mock thread repository."""
    # Mock: Generic component isolation for controlled unit testing
    mock_repo = AsyncMock()
    
    # Setup default return values
    mock_repo.create.return_value = create_mock_thread()
    mock_repo.get.return_value = create_mock_thread()
    mock_repo.list.return_value = [create_mock_thread() for _ in range(3)]
    mock_repo.update.return_value = create_mock_thread()
    mock_repo.delete.return_value = True
    mock_repo.exists.return_value = True
    
    return mock_repo

def setup_ws_manager_mock() -> MagicMock:
    """Setup a mock WebSocket manager."""
    # Mock: Generic component isolation for controlled unit testing
    mock_manager = MagicMock()
    
    # Setup default behaviors
    # Mock: Generic component isolation for controlled unit testing
    mock_manager.send_message = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_manager.broadcast = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_manager.disconnect = AsyncMock()
    # Mock: Service component isolation for predictable testing behavior
    mock_manager.is_connected = MagicMock(return_value=True)
    # Mock: Service component isolation for predictable testing behavior
    mock_manager.get_connections = MagicMock(return_value=[])
    
    return mock_manager

class ThreadTestValidator:
    """Validator for thread-related tests."""
    
    def __init__(self):
        self.errors = []
        
    def validate_thread_structure(self, thread: Dict) -> bool:
        """Validate that a thread has the required structure."""
        required_fields = ["id", "user_id", "title", "created_at", "updated_at"]
        
        for field in required_fields:
            if field not in thread:
                self.errors.append(f"Missing required field: {field}")
                return False
        
        return True
    
    def validate_thread_permissions(self, thread: Dict, user_id: str) -> bool:
        """Validate that a user has permissions for a thread."""
        if thread.get("user_id") != user_id:
            self.errors.append(f"User {user_id} does not have permission for thread {thread.get('id')}")
            return False
        return True
    
    def validate_thread_list(self, threads: List[Dict]) -> bool:
        """Validate a list of threads."""
        if not isinstance(threads, list):
            self.errors.append("Threads must be a list")
            return False
        
        for thread in threads:
            if not self.validate_thread_structure(thread):
                return False
        
        return True

class ThreadTestDataGenerator:
    """Generate test data for thread tests."""
    
    @staticmethod
    def generate_threads(count: int = 5, user_id: Optional[str] = None) -> List[Dict]:
        """Generate multiple test threads."""
        return [
            create_mock_thread(
                user_id=user_id,
                title=f"Test Thread {i}",
                message_count=i * 2
            )
            for i in range(count)
        ]
    
    @staticmethod
    def generate_thread_with_messages(message_count: int = 3) -> Dict:
        """Generate a thread with messages."""
        thread = create_mock_thread(message_count=message_count)
        thread["messages"] = [
            {
                "id": str(uuid4()),
                "thread_id": thread["id"],
                "content": f"Test message {i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "role": "user" if i % 2 == 0 else "assistant"
            }
            for i in range(message_count)
        ]
        return thread
    
    @staticmethod
    def generate_thread_update_payload() -> Dict:
        """Generate a payload for updating a thread."""
        return {
            "title": "Updated Thread Title",
            "metadata": {
                "updated": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }