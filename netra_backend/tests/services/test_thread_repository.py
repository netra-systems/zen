"""Test thread repository specific functionality.

MODULE PURPOSE:
Tests the thread repository layer with comprehensive mocking to ensure
thread-specific data access patterns work correctly.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from datetime import datetime, timedelta

# Add project root to path

from netra_backend.tests.helpers.database_repository_helpers import (

# Add project root to path
    create_test_thread, create_test_threads
)


# Import fixtures from helpers
pytest_plugins = ["app.tests.helpers.database_repository_fixtures"]
class TestThreadRepository:
    """Test thread repository specific functionality."""

    async def test_get_threads_by_user(self, unit_of_work):
        """Test getting threads by user ID."""
        async with unit_of_work as uow:
            user_id = "test_user"
            await create_test_threads(uow, count=5, user_id=user_id)
            
            threads = await uow.threads.get_by_user(user_id)
            
            assert len(threads) == 5
            assert all(t.user_id == user_id for t in threads)

    async def test_get_active_threads(self, unit_of_work):
        """Test getting active threads."""
        async with unit_of_work as uow:
            user_id = "test_user"
            
            active_thread = await uow.threads.create({
                "user_id": user_id,
                "title": "Active Thread",
                "last_activity": datetime.now()
            })
            
            inactive_thread = await uow.threads.create({
                "user_id": user_id,
                "title": "Inactive Thread",
                "last_activity": datetime.now() - timedelta(days=30)
            })
            
            active = await uow.threads.get_active(
                user_id, since=datetime.now() - timedelta(days=7)
            )
            
            assert len(active) == 1
            assert active[0].id == active_thread.id

    async def test_archive_thread(self, unit_of_work):
        """Test thread archival."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "To Archive")
            archived = await uow.threads.archive(thread.id)
            
            assert archived.is_archived == True
            assert archived.archived_at is not None