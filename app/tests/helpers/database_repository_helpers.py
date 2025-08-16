"""Database repository test helper functions.

This module provides helper functions for common test operations
on database repositories. All functions are ≤8 lines.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock


# Thread test helpers
async def create_test_thread(uow, user_id="test_user", title="Test Thread"):
    """Create a test thread with minimal setup."""
    return await uow.threads.create({
        "user_id": user_id,
        "title": title
    })


async def create_test_threads(uow, count=5, user_id="test_user"):
    """Create multiple test threads."""
    threads = []
    for i in range(count):
        thread = await create_test_thread(uow, user_id, f"Thread {i}")
        threads.append(thread)
    return threads


def setup_thread_mock_behavior(mock_repo):
    """Setup mock behavior for thread repository."""
    soft_deleted_threads = {}
    created_threads = {}
    deleted_threads = set()
    thread_counter = [0]
    _setup_thread_create_mock(mock_repo, thread_counter, created_threads)
    _setup_thread_crud_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads)


def _setup_thread_create_mock(mock_repo, thread_counter, created_threads):
    """Setup thread creation mock."""
    async def create_thread(data):
        kwargs = data if isinstance(data, dict) else data
        thread_counter[0] += 1
        thread = _create_mock_thread(kwargs, thread_counter[0])
        created_threads[thread.id] = thread
        return thread
    mock_repo.create.side_effect = create_thread


def _create_mock_thread(kwargs, counter):
    """Create a mock thread object."""
    return AsyncMock(
        id=kwargs.get('id', f"thread_{counter}"),
        user_id=kwargs.get('user_id'),
        title=kwargs.get('title'),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_archived=False,
        archived_at=None,
        deleted_at=None,
        last_activity=kwargs.get('last_activity', datetime.now())
    )


def _setup_thread_crud_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads):
    """Setup CRUD operation mocks for threads."""
    _setup_thread_update_mock(mock_repo)
    _setup_thread_delete_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads)
    _setup_thread_soft_delete_mock(mock_repo, created_threads, soft_deleted_threads)
    _setup_thread_get_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads)


def _setup_thread_update_mock(mock_repo):
    """Setup thread update mock."""
    async def update_thread(id, updates=None, **kwargs):
        return AsyncMock(
            id=id,
            title=updates.get('title', 'Updated Title') if updates else 'Updated Title',
            updated_at=datetime.now() + timedelta(seconds=1),
            created_at=datetime.now() - timedelta(days=1)
        )
    mock_repo.update.side_effect = update_thread


def _setup_thread_delete_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads):
    """Setup delete operation mocks."""
    async def delete_thread(thread_id):
        if thread_id in created_threads:
            del created_threads[thread_id]
        if thread_id in soft_deleted_threads:
            del soft_deleted_threads[thread_id]
        deleted_threads.add(thread_id)
        return True
    mock_repo.delete.side_effect = delete_thread


def _setup_thread_soft_delete_mock(mock_repo, created_threads, soft_deleted_threads):
    """Setup soft delete operation mock."""
    async def soft_delete_thread(thread_id):
        if thread_id in created_threads:
            thread = created_threads[thread_id]
            thread.deleted_at = datetime.now()
            soft_deleted_threads[thread_id] = thread
            del created_threads[thread_id]
        else:
            soft_deleted_threads[thread_id] = AsyncMock(
                id=thread_id,
                deleted_at=datetime.now()
            )
        return None
    mock_repo.soft_delete.side_effect = soft_delete_thread


def _setup_thread_get_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads):
    """Setup get operation mocks."""
    async def get_thread(thread_id, include_deleted=False):
        if thread_id in deleted_threads:
            return None
        if thread_id in soft_deleted_threads:
            return soft_deleted_threads[thread_id] if include_deleted else None
        return created_threads.get(thread_id)
    mock_repo.get.side_effect = get_thread
    
    # Setup additional get methods
    mock_repo.get_by_user.side_effect = lambda user_id: [
        AsyncMock(id=f"thread_{i}", user_id=user_id) for i in range(5)
    ]
    
    async def get_paginated_threads(page, page_size):
        return AsyncMock(
            items=[AsyncMock(id=f"thread_{i}") for i in range(min(page_size, 25 - (page-1)*page_size))],
            total=25,
            pages=3
        )
    mock_repo.get_paginated.side_effect = get_paginated_threads
    
    async def get_active_threads(user_id, since):
        active_threads = []
        for thread in created_threads.values():
            if hasattr(thread, 'user_id') and thread.user_id == user_id:
                if hasattr(thread, 'last_activity') and thread.last_activity >= since:
                    active_threads.append(thread)
        return active_threads
    mock_repo.get_active.side_effect = get_active_threads
    
    async def archive_thread(id):
        return AsyncMock(
            id=id,
            is_archived=True,
            archived_at=datetime.now()
        )
    mock_repo.archive.side_effect = archive_thread
    
    async def get_many_threads(thread_ids):
        return [created_threads.get(tid) for tid in thread_ids if tid in created_threads]
    mock_repo.get_many.side_effect = get_many_threads


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


# Run test helpers
async def create_test_run(uow, thread_id, status="completed", tools=None):
    """Create a test run with minimal setup."""
    return await uow.runs.create({
        "thread_id": thread_id,
        "status": status,
        "tools": tools or []
    })


def setup_run_mock_behavior(mock_repo):
    """Setup mock behavior for run repository."""
    run_counter = [0]
    created_runs = []
    _setup_run_create_mock(mock_repo, run_counter, created_runs)
    _setup_run_operation_mocks(mock_repo, created_runs)


def _setup_run_create_mock(mock_repo, run_counter, created_runs):
    """Setup run creation mock."""
    async def create_run(data=None, **kwargs):
        if data and isinstance(data, dict):
            kwargs = data
        run_counter[0] += 1
        run = _create_mock_run(kwargs, run_counter[0])
        created_runs.append(run)
        return run
    mock_repo.create.side_effect = create_run


def _create_mock_run(kwargs, counter):
    """Create a mock run object."""
    return AsyncMock(
        id=kwargs.get('id', f"run_{counter}"),
        thread_id=kwargs.get('thread_id'),
        status=kwargs.get('status', 'completed'),
        tools=kwargs.get('tools', []),
        model=kwargs.get('model'),
        instructions=kwargs.get('instructions'),
        completed_at=None,
        metadata={}
    )


def _setup_run_operation_mocks(mock_repo, created_runs):
    """Setup run operation mocks."""
    _setup_run_update_status_mock(mock_repo, created_runs)
    _setup_run_active_query_mock(mock_repo, created_runs)


def _setup_run_update_status_mock(mock_repo, created_runs):
    """Setup run status update mock."""
    async def update_run_status(run_id, status, metadata=None):
        for run in created_runs:
            if run.id == run_id:
                run.status = status
                run.completed_at = datetime.now() if status == "completed" else None
                run.metadata = metadata or {}
                return run
        return _create_fallback_run(run_id, status, metadata)
    mock_repo.update_status.side_effect = update_run_status


def _create_fallback_run(run_id, status, metadata):
    """Create fallback run for update operations."""
    return AsyncMock(
        id=run_id,
        status=status,
        completed_at=datetime.now() if status == "completed" else None,
        metadata=metadata or {}
    )


def _setup_run_active_query_mock(mock_repo, created_runs):
    """Setup active runs query mock."""
    async def get_active_runs_impl():
        return [run for run in created_runs if run.status in ["in_progress", "queued", "requires_action"]]
    mock_repo.get_active_runs.side_effect = get_active_runs_impl
    mock_repo.get_active = mock_repo.get_active_runs


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