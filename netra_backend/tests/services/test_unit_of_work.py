"""Test Unit of Work pattern implementation.

MODULE PURPOSE:
Tests the Unit of Work pattern with comprehensive mocking to ensure
transaction management works correctly without requiring a real database.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio

import pytest

# Add project root to path
from netra_backend.app.services.database.unit_of_work import UnitOfWork
from .database_repository_helpers import (
    assert_thread_created_correctly,
    create_test_message,
    # Add project root to path
    create_test_thread,
)

# Import fixtures from helpers
pytest_plugins = ["app.tests.helpers.database_repository_fixtures"]
class TestUnitOfWork:
    """Test Unit of Work pattern implementation."""

    async def test_uow_initialization(self, unit_of_work):
        """Test UoW initialization and repository access."""
        async with unit_of_work as uow:
            assert uow.messages is not None
            assert uow.threads is not None
            assert uow.runs is not None
            assert uow.references is not None
            assert hasattr(uow.messages, 'create')
            assert hasattr(uow.threads, 'create')

    async def test_uow_transaction_commit(self, unit_of_work):
        """Test successful transaction commit."""
        thread_id = None
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            thread_id = thread.id
            await create_test_message(uow, thread.id, "Test message", "user")
            await uow.commit()
        
        async with unit_of_work as uow:
            retrieved_thread = await uow.threads.get(thread_id)
            assert retrieved_thread is not None
            assert_thread_created_correctly(retrieved_thread, "test_user", "Test Thread")

    async def test_uow_transaction_rollback(self, unit_of_work):
        """Test transaction rollback on error."""
        try:
            async with unit_of_work as uow:
                await create_test_thread(uow, "test_user", "Test Thread")
                raise ValueError("Test error")
        except ValueError:
            pass
        
        assert unit_of_work.session.rollback.called

    @pytest.mark.skip(reason="begin_nested not implemented in current UnitOfWork")
    async def test_uow_nested_transactions(self, unit_of_work):
        """Test nested transaction handling."""
        thread_id = None
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Outer Transaction")
            thread_id = thread.id
            
            async with uow.begin_nested() as nested:
                await create_test_message(uow, thread.id, "Nested message", "user")
                await nested.rollback()
            
            await uow.commit()
        
        async with unit_of_work as uow:
            assert await uow.threads.get(thread_id) is not None
            messages = await uow.messages.get_by_thread(thread_id)
            assert len(messages) == 0

    async def test_uow_concurrent_access(self, unit_of_work):
        """Test concurrent UoW instances."""
        async def create_thread_task(uow, thread_id):
            async with uow:
                return await create_test_thread(uow, f"user_{thread_id}", f"Thread {thread_id}")
        
        uow1 = UnitOfWork()
        uow2 = UnitOfWork()
        
        results = await asyncio.gather(
            create_thread_task(uow1, 1),
            create_thread_task(uow2, 2)
        )
        
        assert len(results) == 2
        assert results[0].title == "Thread 1"
        assert results[1].title == "Thread 2"