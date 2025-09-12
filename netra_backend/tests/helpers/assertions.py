"""Assertion and reference test helper functions.

This module provides assertion helpers and reference test operations
on database repositories. All functions are  <= 8 lines.
COMPLIANCE: 450-line max file, 25-line max functions
"""

from datetime import datetime
from unittest.mock import AsyncMock

# Reference test helpers
async def create_test_reference(uow, message_id, ref_type="document", source="test_source"):
    """Create a test reference with minimal setup."""
    return await uow.references.create({
        "message_id": message_id,
        "type": ref_type,
        "source": source
    })

def setup_reference_mock_behavior(mock_repo):
    """Setup mock behavior for reference repository."""
    reference_counter = [0]
    _setup_reference_create_mock(mock_repo, reference_counter)
    _setup_reference_query_mocks(mock_repo)

def _setup_reference_create_mock(mock_repo, reference_counter):
    """Setup reference creation mock."""
    async def create_reference(data=None, **kwargs):
        if data and isinstance(data, dict):
            kwargs = data
        reference_counter[0] += 1
        return _create_mock_reference(kwargs, reference_counter[0])
    mock_repo.create.side_effect = create_reference

def _create_mock_reference(kwargs, counter):
    """Create a mock reference object."""
    return AsyncMock(
        id=kwargs.get('id', f"ref_{counter}"),
        message_id=kwargs.get('message_id'),
        type=kwargs.get('type'),
        source=kwargs.get('source'),
        content=kwargs.get('content'),
        metadata=kwargs.get('metadata', {})
    )

def _setup_reference_query_mocks(mock_repo):
    """Setup reference query mocks."""
    mock_repo.get_by_message.side_effect = lambda message_id: [
        AsyncMock(id=f"ref_{i}", message_id=message_id) for i in range(3)
    ]
    mock_repo.search.side_effect = lambda query, limit: [
        AsyncMock(content=f"Python programming reference {i}") for i in range(5)
    ]

# Assertion helpers
def assert_thread_created_correctly(thread, user_id, title):
    """Assert thread was created with correct attributes."""
    assert thread.id is not None
    assert thread.user_id == user_id
    assert thread.title == title
    assert thread.created_at is not None

def assert_message_created_correctly(message, thread_id, content, role):
    """Assert message was created with correct attributes."""
    assert message.id is not None
    assert message.thread_id == thread_id
    assert message.content == content
    assert message.role == role

def assert_run_created_correctly(run, thread_id, status, tools):
    """Assert run was created with correct attributes."""
    assert run.id is not None
    assert run.thread_id == thread_id
    assert run.status == status
    assert run.tools == tools

def assert_reference_created_correctly(reference, message_id, ref_type, source):
    """Assert reference was created with correct attributes."""
    assert reference.id is not None
    assert reference.message_id == message_id
    assert reference.type == ref_type
    assert reference.source == source

def assert_pagination_result(page_result, expected_items, expected_total):
    """Assert pagination result has correct structure."""
    assert len(page_result.items) == expected_items
    assert page_result.total == expected_total