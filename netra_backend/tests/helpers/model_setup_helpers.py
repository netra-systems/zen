"""Model setup helpers for tests."""

from typing import Any, Dict
from unittest.mock import MagicMock

def create_test_user(email: str = "test@example.com") -> Dict[str, Any]:
    """Create a test user."""
    return {
        "id": "test-user-id",
        "email": email,
        "name": "Test User"
    }

def create_test_thread() -> Dict[str, Any]:
    """Create a test thread."""
    return {
        "id": "test-thread-id",
        "title": "Test Thread",
        "user_id": "test-user-id"
    }

def create_mock_llm_response(content: str = "Test response") -> MagicMock:
    """Create a mock LLM response."""
    mock = MagicMock()
    mock.content = content
    return mock

async def get_test_token(user_id: str = "test-user-id") -> str:
    """Get a test authentication token."""
    return f"test-token-{user_id}"
