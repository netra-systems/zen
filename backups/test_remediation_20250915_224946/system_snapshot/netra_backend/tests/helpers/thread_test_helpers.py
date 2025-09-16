"""Test helpers for threads route tests"""

import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

def create_mock_thread(
    thread_id: str = "thread_abc123",
    user_id: str = "test_user_123", 
    title: str = "Test Thread",
    updated_at: int = 1234567900
) -> Mock:
    """Create a mock thread object"""
    # Mock: Generic component isolation for controlled unit testing
    thread = Mock()
    thread.id = thread_id
    thread.object = "thread"
    thread.created_at = 1234567890
    thread.metadata_ = {
        "user_id": user_id,
        "title": title,
        "updated_at": updated_at
    }
    return thread

def create_mock_message(
    msg_id: str = "msg_123",
    role: str = "user",
    content: str = "Test message content"
) -> Mock:
    """Create a mock message object"""
    # Mock: Generic component isolation for controlled unit testing
    message = Mock()
    message.id = msg_id
    message.role = role
    message.content = content
    message.created_at = 1234567890
    message.metadata_ = {}
    return message

def setup_thread_repo_mock(mock_thread: Mock = None, find_result: List = None) -> Mock:
    """Setup thread repository mock with standard responses"""
    if mock_thread is None:
        mock_thread = create_mock_thread()
    if find_result is None:
        find_result = [mock_thread]
    
    # Mock: Generic component isolation for controlled unit testing
    thread_repo = Mock()
    # Mock: Async component isolation for testing without real async operations
    thread_repo.find_by_user = AsyncMock(return_value=find_result)
    # Mock: Async component isolation for testing without real async operations
    thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
    # Mock: Async component isolation for testing without real async operations
    thread_repo.create = AsyncMock(return_value=mock_thread)
    # Mock: Async component isolation for testing without real async operations
    thread_repo.archive_thread = AsyncMock(return_value=True)
    return thread_repo

def setup_message_repo_mock(message_count: int = 5, messages: List = None) -> Mock:
    """Setup message repository mock with standard responses"""
    if messages is None:
        messages = [create_mock_message()]
    
    # Mock: Generic component isolation for controlled unit testing
    message_repo = Mock()
    # Mock: Async component isolation for testing without real async operations
    message_repo.count_by_thread = AsyncMock(return_value=message_count)
    # Mock: Async component isolation for testing without real async operations
    message_repo.find_by_thread = AsyncMock(return_value=messages)
    return message_repo

def setup_llm_manager_mock(response: str = "Generated Title") -> Mock:
    """Setup LLM manager mock"""
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager = Mock()
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager.ask_llm = AsyncMock(return_value=response)
    return llm_manager

def setup_repos_with_patches(
    thread_repo: Mock,
    message_repo: Mock,
    llm_manager: Mock = None
) -> list:
    """Setup repository patches for tests"""
    patches = [
        # Mock: Component isolation for testing without external dependencies
        patch('app.routes.utils.thread_helpers.ThreadRepository', return_value=thread_repo),
        # Mock: Component isolation for testing without external dependencies
        patch('app.routes.utils.thread_helpers.MessageRepository', return_value=message_repo)
    ]
    if llm_manager:
        # Mock: Component isolation for testing without external dependencies
        patches.append(patch('app.routes.utils.thread_helpers.LLMManager', return_value=llm_manager))
    return patches

def assert_thread_response(result, expected_id: str, expected_count: int = 0):
    """Assert thread response has expected values"""
    assert result.id == expected_id
    assert result.message_count == expected_count

def assert_http_exception(exc_info, status_code: int, detail: str):
    """Assert HTTPException has expected values"""
    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail

def assert_repo_calls(thread_repo: Mock, message_repo: Mock, db: Mock, user_id: str, thread_id: str):
    """Assert repository methods were called correctly"""
    thread_repo.find_by_user.assert_called_once_with(db, user_id)
    message_repo.count_by_thread.assert_called_once_with(db, thread_id)

def create_multiple_threads(count: int, prefix: str = "thread_") -> List[Mock]:
    """Create multiple mock threads for pagination tests"""
    threads = []
    for i in range(count):
        # Mock: Component isolation for controlled unit testing
        thread = Mock(
            id=f"{prefix}{i}",
            object="thread",
            created_at=123456789+i,
            metadata_={"title": f"Thread {i}"}
        )
        threads.append(thread)
    return threads

def create_empty_metadata_thread() -> Mock:
    """Create thread with None metadata for testing"""
    # Mock: Component isolation for controlled unit testing
    thread = Mock(id="thread_1", object="thread", created_at=123456789, metadata_=None)
    return thread

def create_special_metadata_dict(user_id: str = "test_user_123") -> dict:
    """Create special dict that returns user_id once then becomes None"""
    class SpecialDict(dict):
        def __init__(self):
            super().__init__({"user_id": user_id})
            self.call_count = 0
            
        def get(self, key, default=None):
            self.call_count += 1
            if self.call_count == 1 and key == "user_id":
                return user_id
            return super().get(key, default)
    
    return SpecialDict()

def setup_thread_with_special_metadata(user_id: str = "test_user_123") -> Mock:
    """Setup thread that changes metadata during test"""
    # Mock: Generic component isolation for controlled unit testing
    mock_thread = Mock()
    mock_thread.id = "thread_abc123"
    mock_thread.object = "thread"
    mock_thread.created_at = 1234567890
    mock_thread.metadata_ = create_special_metadata_dict(user_id)
    return mock_thread

def create_thread_update_scenario(mock_time: Mock, return_value: int = 1234567900) -> None:
    """Setup time mock for update scenarios"""
    mock_time.return_value = return_value

def create_uuid_scenario(mock_uuid: Mock, hex_value: str = "abcdef1234567890") -> None:
    """Setup UUID mock for creation scenarios"""
    # Mock: Generic component isolation for controlled unit testing
    mock_uuid_obj = Mock()
    mock_uuid_obj.hex = hex_value
    mock_uuid.return_value = mock_uuid_obj

def setup_ws_manager_mock() -> Mock:
    """Setup WebSocket manager mock"""
    # Mock: Generic component isolation for controlled unit testing
    mock_ws = Mock()
    # Mock: Generic component isolation for controlled unit testing
    mock_ws.send_to_user = AsyncMock()
    return mock_ws

def assert_ws_notification(mock_ws: Mock, user_id: str, thread_id: str, new_title: str):
    """Assert WebSocket notification was sent correctly"""
    mock_ws.send_to_user.assert_called_once()
    ws_call_args = mock_ws.send_to_user.call_args
    assert ws_call_args[0][0] == user_id
    assert ws_call_args[0][1]["type"] == "thread_renamed"
    assert ws_call_args[0][1]["thread_id"] == thread_id
    assert ws_call_args[0][1]["new_title"] == new_title

def assert_thread_creation_call(thread_repo: Mock, db: Mock, user_id: str, title: str = None):
    """Assert thread creation was called with correct parameters"""
    thread_repo.create.assert_called_once()
    call_args = thread_repo.create.call_args
    assert call_args[0][0] == db
    assert "thread_" in call_args[1]["id"]
    assert call_args[1]["object"] == "thread"
    assert call_args[1]["metadata_"]["user_id"] == user_id
    if title:
        assert call_args[1]["metadata_"]["title"] == title
    assert call_args[1]["metadata_"]["status"] == "active"

def assert_thread_messages_response(result: dict, thread_id: str, message_count: int, limit: int = 50, offset: int = 0):
    """Assert thread messages response structure"""
    assert result["thread_id"] == thread_id
    assert len(result["messages"]) == message_count
    assert result["total"] == message_count
    assert result["limit"] == limit
    assert result["offset"] == offset

def clean_llm_title(raw_title: str, max_length: int = 50) -> str:
    """Clean and truncate LLM-generated title"""
    cleaned = raw_title.strip().strip('"\'')
    return cleaned[:max_length] if len(cleaned) > max_length else cleaned

def create_access_denied_thread(user_id: str = "another_user") -> Mock:
    """Create thread owned by different user for access tests"""
    thread = create_mock_thread()
    thread.metadata_["user_id"] = user_id
    return thread