"""Test base repository functionality.

MODULE PURPOSE:
Tests the base repository layer with comprehensive mocking to ensure
data access patterns work correctly without requiring a real database.
"""

import pytest
import time
from unittest.mock import AsyncMock
from app.tests.helpers.database_repository_helpers import (
    create_test_thread, create_test_threads, assert_thread_created_correctly,
    assert_pagination_result
)


# Import fixtures from helpers
pytest_plugins = ["app.tests.helpers.database_repository_fixtures"]


@pytest.mark.asyncio
class TestBaseRepository:
    """Test base repository functionality."""

    async def test_repository_create(self, unit_of_work):
        """Test creating an entity."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            assert_thread_created_correctly(thread, "test_user", "Test Thread")

    async def test_repository_bulk_create(self, unit_of_work, mock_models):
        """Test bulk entity creation."""
        async with unit_of_work as uow:
            mock_threads = []
            for i in range(10):
                thread = mock_models['Thread'](
                    id=f"thread_{i}",
                    object="thread",
                    created_at=int(time.time()),
                    metadata_={"user_id": f"user_{i}", "title": f"Thread {i}"}
                )
                mock_threads.append(thread)
            
            uow.threads.bulk_create = AsyncMock(return_value=mock_threads)
            
            threads_data = [
                {
                    "object": "thread",
                    "created_at": int(time.time()),
                    "metadata_": {"user_id": f"user_{i}", "title": f"Thread {i}"}
                }
                for i in range(10)
            ]
            
            threads = await uow.threads.bulk_create(threads_data)
            assert len(threads) == 10
            assert all(t.id is not None for t in threads)

    async def test_repository_get_by_id(self, unit_of_work, mock_models):
        """Test getting entity by ID."""
        async with unit_of_work as uow:
            mock_thread = mock_models['Thread'](
                id="thread_test_123",
                user_id="test_user",
                title="Test Thread"
            )
            
            uow.threads.create = AsyncMock(return_value=mock_thread)
            uow.threads.get = AsyncMock(return_value=mock_thread)
            
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            retrieved = await uow.threads.get(thread.id)
            
            assert retrieved is not None
            assert retrieved.id == thread.id
            assert retrieved.title == thread.title

    async def test_repository_get_many(self, unit_of_work, mock_models):
        """Test getting multiple entities."""
        async with unit_of_work as uow:
            mock_threads = []
            thread_ids = []
            for i in range(5):
                thread = mock_models['Thread'](
                    id=f"thread_{i}",
                    user_id="test_user",
                    title=f"Thread {i}"
                )
                mock_threads.append(thread)
                thread_ids.append(thread.id)
            
            uow.threads.create = AsyncMock(side_effect=mock_threads)
            uow.threads.get_many = AsyncMock(return_value=mock_threads[:3])
            
            created_ids = []
            for i in range(5):
                thread = await create_test_thread(uow, "test_user", f"Thread {i}")
                created_ids.append(thread.id)
            
            threads = await uow.threads.get_many(created_ids[:3])
            assert len(threads) == 3
            assert all(t.id in thread_ids[:3] for t in threads)

    async def test_repository_update(self, unit_of_work):
        """Test updating an entity."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Original Title")
            updated = await uow.threads.update(thread.id, {"title": "Updated Title"})
            
            assert updated.title == "Updated Title"
            assert updated.updated_at > thread.created_at

    async def test_repository_delete(self, unit_of_work):
        """Test deleting an entity."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "To Delete")
            deleted = await uow.threads.delete(thread.id)
            assert deleted == True
            
            retrieved = await uow.threads.get(thread.id)
            assert retrieved is None

    async def test_repository_soft_delete(self, unit_of_work):
        """Test soft delete functionality."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Soft Delete Test")
            await uow.threads.soft_delete(thread.id)
            
            retrieved = await uow.threads.get(thread.id)
            assert retrieved is None
            
            retrieved = await uow.threads.get(thread.id, include_deleted=True)
            assert retrieved is not None
            assert retrieved.deleted_at is not None

    async def test_repository_pagination(self, unit_of_work):
        """Test pagination functionality."""
        async with unit_of_work as uow:
            await create_test_threads(uow, count=25, user_id="test_user")
            
            page1 = await uow.threads.get_paginated(page=1, page_size=10)
            page2 = await uow.threads.get_paginated(page=2, page_size=10)
            page3 = await uow.threads.get_paginated(page=3, page_size=10)
            
            assert_pagination_result(page1, 10, 25)
            assert_pagination_result(page2, 10, 25)
            assert_pagination_result(page3, 5, 25)
            assert page1.pages == 3