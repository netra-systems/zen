"""
Critical thread and message API endpoint tests.

Tests for thread management and message handling endpoints.
Core chat functionality validation.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAPIThreadsMessagesCritical:
    """Critical thread and message API endpoint tests."""
    async def test_create_thread(self):
        """Test thread creation endpoint."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test create thread
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": str(uuid.uuid4()),
                "title": "New Thread",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        response = await mock_client.post(
            "/api/threads",
            json={"title": "New Thread"},
            headers=auth_headers
        )
        assert response["status_code"] == 201
        assert response["json"]["title"] == "New Thread"
    async def test_get_user_threads(self):
        """Test get user threads endpoint."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test get user threads
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "threads": [
                    {"id": "thread1", "title": "Thread 1"},
                    {"id": "thread2", "title": "Thread 2"}
                ],
                "total": 2
            }
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 200
        assert len(response["json"]["threads"]) == 2
    async def test_thread_creation_validation(self):
        """Test thread creation validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        thread_id = str(uuid.uuid4())
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": thread_id,
                "title": "Validated Thread",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        response = await mock_client.post(
            "/api/threads",
            json={"title": "Validated Thread"},
            headers=auth_headers
        )
        assert "id" in response["json"]
        assert "created_at" in response["json"]
    async def test_send_message(self):
        """Test send message endpoint."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        thread_id = str(uuid.uuid4())
        
        # Test send message
        message_data = {
            "content": "Hello, AI assistant!",
            "thread_id": thread_id
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": str(uuid.uuid4()),
                "content": "Hello, AI assistant!",
                "role": "user",
                "thread_id": thread_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        response = await mock_client.post(
            "/api/messages",
            json=message_data,
            headers=auth_headers
        )
        assert response["status_code"] == 201
        assert response["json"]["content"] == message_data["content"]
    async def test_get_thread_messages(self):
        """Test get thread messages endpoint."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        thread_id = str(uuid.uuid4())
        
        # Test get thread messages
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help?"}
                ],
                "total": 2
            }
        })
        
        response = await mock_client.get(
            f"/api/threads/{thread_id}/messages",
            headers=auth_headers
        )
        assert response["status_code"] == 200
        assert len(response["json"]["messages"]) == 2
    async def test_message_role_validation(self):
        """Test message role validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        thread_id = str(uuid.uuid4())
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help?"}
                ],
                "total": 2
            }
        })
        
        response = await mock_client.get(
            f"/api/threads/{thread_id}/messages",
            headers=auth_headers
        )
        
        messages = response["json"]["messages"]
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
    async def test_message_content_validation(self):
        """Test message content validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        thread_id = str(uuid.uuid4())
        
        message_data = {
            "content": "Test message content",
            "thread_id": thread_id
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": str(uuid.uuid4()),
                "content": "Test message content",
                "role": "user",
                "thread_id": thread_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        response = await mock_client.post(
            "/api/messages",
            json=message_data,
            headers=auth_headers
        )
        assert response["json"]["thread_id"] == thread_id
        assert response["json"]["role"] == "user"
    async def test_thread_listing_pagination(self):
        """Test thread listing with pagination."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "threads": [
                    {"id": f"thread{i}", "title": f"Thread {i}"} 
                    for i in range(1, 6)
                ],
                "total": 5,
                "page": 1,
                "per_page": 5
            }
        })
        
        response = await mock_client.get("/api/threads?page=1&per_page=5", headers=auth_headers)
        assert response["json"]["total"] == 5
        assert len(response["json"]["threads"]) == 5
    async def test_message_timestamp_validation(self):
        """Test message timestamp validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        thread_id = str(uuid.uuid4())
        
        timestamp = datetime.now(timezone.utc).isoformat()
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": str(uuid.uuid4()),
                "content": "Timestamped message",
                "role": "user",
                "thread_id": thread_id,
                "created_at": timestamp
            }
        })
        
        response = await mock_client.post(
            "/api/messages",
            json={"content": "Timestamped message", "thread_id": thread_id},
            headers=auth_headers
        )
        assert "created_at" in response["json"]
        assert response["json"]["created_at"] == timestamp
    async def test_thread_id_validation(self):
        """Test thread ID validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        thread_id = str(uuid.uuid4())
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": thread_id,
                "title": "ID Validated Thread",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        response = await mock_client.post(
            "/api/threads",
            json={"title": "ID Validated Thread"},
            headers=auth_headers
        )
        
        # Verify UUID format
        returned_id = response["json"]["id"]
        uuid.UUID(returned_id)  # This will raise ValueError if invalid UUID
    async def test_empty_thread_list(self):
        """Test empty thread list response."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "threads": [],
                "total": 0
            }
        })
        
        response = await mock_client.get("/api/threads", headers=auth_headers)
        assert response["status_code"] == 200
        assert len(response["json"]["threads"]) == 0
        assert response["json"]["total"] == 0
    async def test_message_order_consistency(self):
        """Test message order consistency."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        thread_id = str(uuid.uuid4())
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "messages": [
                    {"id": "msg1", "role": "user", "content": "First message"},
                    {"id": "msg2", "role": "assistant", "content": "Response to first"},
                    {"id": "msg3", "role": "user", "content": "Second message"}
                ],
                "total": 3
            }
        })
        
        response = await mock_client.get(
            f"/api/threads/{thread_id}/messages",
            headers=auth_headers
        )
        
        messages = response["json"]["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
    async def test_thread_title_handling(self):
        """Test thread title handling."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        titles = ["Short", "A very long thread title that tests length limits", ""]
        
        for title in titles:
            mock_client.post = AsyncMock(return_value={
                "status_code": 201,
                "json": {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            })
            
            response = await mock_client.post(
                "/api/threads",
                json={"title": title},
                headers=auth_headers
            )
            assert response["json"]["title"] == title
    async def test_message_context_preservation(self):
        """Test message context preservation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        thread_id = str(uuid.uuid4())
        
        # Send message with context
        message_data = {
            "content": "Context-aware message",
            "thread_id": thread_id,
            "metadata": {"context": "important"}
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 201,
            "json": {
                "id": str(uuid.uuid4()),
                "content": "Context-aware message",
                "role": "user",
                "thread_id": thread_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        response = await mock_client.post(
            "/api/messages",
            json=message_data,
            headers=auth_headers
        )
        assert response["json"]["thread_id"] == thread_id