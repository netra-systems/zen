"""Thread database repository test helper functions.

This module provides helper functions for thread test operations
on database repositories. All functions are  <= 8 lines.
COMPLIANCE: 450-line max file, 25-line max functions
"""

from datetime import datetime, timedelta
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
    base_attrs = _get_thread_base_attrs(kwargs, counter)
    time_attrs = _get_thread_time_attrs(kwargs)
    return AsyncMock(**{**base_attrs, **time_attrs})

def _setup_thread_crud_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads):
    """Setup CRUD operation mocks for threads."""
    _setup_thread_update_mock(mock_repo)
    _setup_thread_delete_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads)
    _setup_thread_soft_delete_mock(mock_repo, created_threads, soft_deleted_threads)
    _setup_thread_get_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads)

def _setup_thread_update_mock(mock_repo):
    """Setup thread update mock."""
    update_func = _create_thread_update_func()
    mock_repo.update.side_effect = update_func

def _setup_thread_delete_mocks(mock_repo, created_threads, soft_deleted_threads, deleted_threads):
    """Setup delete operation mocks."""
    delete_func = _create_thread_delete_func(created_threads, soft_deleted_threads, deleted_threads)
    mock_repo.delete.side_effect = delete_func

def _setup_thread_soft_delete_mock(mock_repo, created_threads, soft_deleted_threads):
    """Setup soft delete operation mock."""
    soft_delete_func = _create_thread_soft_delete_func(created_threads, soft_deleted_threads)
    mock_repo.soft_delete.side_effect = soft_delete_func

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
    
    get_paginated_func = _create_paginated_threads_func()
    mock_repo.get_paginated.side_effect = get_paginated_func
    
    get_active_func = _create_active_threads_func(created_threads)
    mock_repo.get_active.side_effect = get_active_func
    
    archive_func = _create_archive_thread_func()
    mock_repo.archive.side_effect = archive_func
    
    async def get_many_threads(thread_ids):
        return [created_threads.get(tid) for tid in thread_ids if tid in created_threads]
    mock_repo.get_many.side_effect = get_many_threads

def _get_thread_base_attrs(kwargs, counter):
    """Get base thread attributes."""
    return {
        'id': kwargs.get('id', f"thread_{counter}"),
        'user_id': kwargs.get('user_id'),
        'title': kwargs.get('title'),
        'is_archived': False
    }

def _get_thread_time_attrs(kwargs):
    """Get thread time-related attributes."""
    now = datetime.now()
    return {
        'created_at': now,
        'updated_at': now,
        'archived_at': None,
        'deleted_at': None,
        'last_activity': kwargs.get('last_activity', now)
    }

def _create_thread_update_func():
    """Create thread update function."""
    async def update_thread(id, updates=None, **kwargs):
        title = updates.get('title', 'Updated Title') if updates else 'Updated Title'
        return AsyncMock(
            id=id, title=title,
            updated_at=datetime.now() + timedelta(seconds=1),
            created_at=datetime.now() - timedelta(days=1)
        )
    return update_thread

def _create_thread_delete_func(created_threads, soft_deleted_threads, deleted_threads):
    """Create thread delete function."""
    async def delete_thread(thread_id):
        _remove_from_collections(thread_id, created_threads, soft_deleted_threads)
        deleted_threads.add(thread_id)
        return True
    return delete_thread

def _remove_from_collections(thread_id, created_threads, soft_deleted_threads):
    """Remove thread from created and soft deleted collections."""
    if thread_id in created_threads:
        del created_threads[thread_id]
    if thread_id in soft_deleted_threads:
        del soft_deleted_threads[thread_id]

def _create_thread_soft_delete_func(created_threads, soft_deleted_threads):
    """Create thread soft delete function."""
    async def soft_delete_thread(thread_id):
        if thread_id in created_threads:
            _move_to_soft_deleted(thread_id, created_threads, soft_deleted_threads)
        else:
            _create_soft_deleted_thread(thread_id, soft_deleted_threads)
        return None
    return soft_delete_thread

def _move_to_soft_deleted(thread_id, created_threads, soft_deleted_threads):
    """Move thread from created to soft deleted."""
    thread = created_threads[thread_id]
    thread.deleted_at = datetime.now()
    soft_deleted_threads[thread_id] = thread
    del created_threads[thread_id]

def _create_soft_deleted_thread(thread_id, soft_deleted_threads):
    """Create new soft deleted thread entry."""
    soft_deleted_threads[thread_id] = AsyncMock(
        id=thread_id,
        deleted_at=datetime.now()
    )

def _create_paginated_threads_func():
    """Create paginated threads function."""
    async def get_paginated_threads(page, page_size):
        item_count = min(page_size, 25 - (page-1)*page_size)
        items = [AsyncMock(id=f"thread_{i}") for i in range(item_count)]
        return AsyncMock(items=items, total=25, pages=3)
    return get_paginated_threads

def _create_active_threads_func(created_threads):
    """Create active threads function."""
    async def get_active_threads(user_id, since):
        active_threads = []
        for thread in created_threads.values():
            if _is_user_thread_active(thread, user_id, since):
                active_threads.append(thread)
        return active_threads
    return get_active_threads

def _is_user_thread_active(thread, user_id, since):
    """Check if thread is active for user since given time."""
    user_match = hasattr(thread, 'user_id') and thread.user_id == user_id
    time_match = hasattr(thread, 'last_activity') and thread.last_activity >= since
    return user_match and time_match

def _create_archive_thread_func():
    """Create archive thread function."""
    async def archive_thread(id):
        return AsyncMock(
            id=id,
            is_archived=True,
            archived_at=datetime.now()
        )
    return archive_thread