"""Message database repository test helper functions.

This module provides helper functions for message test operations
on database repositories. All functions are  <= 8 lines.
COMPLIANCE: 450-line max file, 25-line max functions
"""

from datetime import datetime
from unittest.mock import AsyncMock

# Message test helpers
async def create_test_message(uow, thread_id, content="Test message", role="user"):
    """Create a test message with minimal setup."""
    return await uow.messages.create({
        "thread_id": thread_id,
        "content": content,
        "role": role
    })

async def create_test_messages(uow, thread_id, count=5):
    """Create multiple test messages."""
    messages = []
    for i in range(count):
        message = await create_test_message(uow, thread_id, f"Message {i}")
        messages.append(message)
    return messages

def setup_message_mock_behavior(mock_repo):
    """Setup mock behavior for message repository."""
    message_counter = [0]
    _setup_message_create_mock(mock_repo, message_counter)
    _setup_message_query_mocks(mock_repo)

def _setup_message_create_mock(mock_repo, message_counter):
    """Setup message creation mock."""
    async def create_message(data=None, **kwargs):
        if data and isinstance(data, dict):
            kwargs = data
        message_counter[0] += 1
        return _create_mock_message(kwargs, message_counter[0])
    mock_repo.create.side_effect = create_message

def _create_mock_message(kwargs, counter):
    """Create a mock message object."""
    return AsyncMock(
        id=kwargs.get('id', f"msg_{counter}"),
        thread_id=kwargs.get('thread_id'),
        content=kwargs.get('content'),
        role=kwargs.get('role'),
        created_at=datetime.now()
    )

def _setup_message_query_mocks(mock_repo):
    """Setup message query mocks."""
    mock_repo.get_by_thread.side_effect = lambda thread_id: [
        AsyncMock(id=f"msg_{i}", thread_id=thread_id, content=f"Message {i}") 
        for i in range(5)
    ]
    _setup_message_pagination_mock(mock_repo)
    _setup_message_latest_mock(mock_repo)

def _setup_message_pagination_mock(mock_repo):
    """Setup paginated message retrieval mock."""
    async def get_messages_paginated(thread_id, page, page_size):
        return AsyncMock(
            items=[AsyncMock(id=f"msg_{i}") for i in range(10)],
            total=50
        )
    mock_repo.get_by_thread_paginated.side_effect = get_messages_paginated

def _setup_message_latest_mock(mock_repo):
    """Setup latest messages mock."""
    mock_repo.get_latest.side_effect = lambda thread_id, limit: [
        AsyncMock(content=f"Message {9-i}") for i in range(limit)
    ]