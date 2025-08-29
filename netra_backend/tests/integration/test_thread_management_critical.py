#!/usr/bin/env python3
"""
Critical Thread Management Integration Tests
Tests the core thread lifecycle management functionality that is essential for the system.
"""
import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.db.postgres_session import get_async_db
from netra_backend.app.db.database_manager import DatabaseManager
from tests.e2e.harness_complete import get_test_database_url
from test_framework.test_utils import cleanup_test_data


# Test Environment Setup
@pytest.fixture(scope="module")
def test_env():
    """Test environment configuration."""
    env = IsolatedEnvironment("netra_backend")
    return env


@pytest.fixture
async def thread_service(test_env):
    """Thread service instance for testing."""
    service = ThreadService()
    yield service
    # Cleanup any test data
    await cleanup_test_data()


@pytest.fixture
async def db_manager():
    """Database manager for direct database operations."""
    db_url = get_test_database_url()
    manager = DatabaseManager(db_url)
    await manager.initialize()
    yield manager
    await manager.close()


class TestThreadLifecycle:
    """Test the complete thread lifecycle operations."""
    
    @pytest.mark.asyncio
    async def test_create_thread_basic(self, thread_service: ThreadService):
        """Test basic thread creation functionality."""
        user_id = "test_user_123"
        title = "Test Thread"
        
        # Create a new thread
        thread = await thread_service.create_thread(
            user_id=user_id,
            title=title,
            metadata={"source": "test", "priority": "high"}
        )
        
        # Verify thread properties
        assert thread is not None
        assert thread.user_id == user_id
        assert thread.title == title
        assert thread.status == "active"
        assert thread.created_at is not None
        assert thread.id is not None
        
        # Verify metadata is stored correctly
        assert "source" in thread.metadata
        assert thread.metadata["source"] == "test"
    
    @pytest.mark.asyncio
    async def test_thread_retrieval_by_id(self, thread_service: ThreadService):
        """Test retrieving a thread by its ID."""
        # Create a thread first
        user_id = "test_user_456"
        thread = await thread_service.create_thread(
            user_id=user_id,
            title="Retrievable Thread"
        )
        
        # Retrieve the thread by ID
        retrieved_thread = await thread_service.get_thread(thread.id)
        
        assert retrieved_thread is not None
        assert retrieved_thread.id == thread.id
        assert retrieved_thread.title == thread.title
        assert retrieved_thread.user_id == user_id
    
    @pytest.mark.asyncio
    async def test_list_user_threads(self, thread_service: ThreadService):
        """Test listing threads for a specific user."""
        user_id = "test_user_789"
        
        # Create multiple threads for the user
        thread_titles = ["Thread 1", "Thread 2", "Thread 3"]
        created_threads = []
        
        for title in thread_titles:
            thread = await thread_service.create_thread(
                user_id=user_id,
                title=title
            )
            created_threads.append(thread)
        
        # List threads for the user
        user_threads = await thread_service.list_user_threads(
            user_id=user_id,
            limit=10
        )
        
        assert len(user_threads) >= 3
        
        # Verify all created threads are in the list
        thread_ids = {t.id for t in user_threads}
        for created_thread in created_threads:
            assert created_thread.id in thread_ids
    
    @pytest.mark.asyncio 
    async def test_update_thread_status(self, thread_service: ThreadService):
        """Test updating thread status."""
        # Create a thread
        user_id = "test_user_status"
        thread = await thread_service.create_thread(
            user_id=user_id,
            title="Status Update Thread"
        )
        
        original_status = thread.status
        new_status = "archived"
        
        # Update the thread status
        updated_thread = await thread_service.update_thread_status(
            thread_id=thread.id,
            status=new_status
        )
        
        assert updated_thread is not None
        assert updated_thread.status == new_status
        assert updated_thread.id == thread.id
        
        # Verify the change persisted
        retrieved_thread = await thread_service.get_thread(thread.id)
        assert retrieved_thread.status == new_status
    
    @pytest.mark.asyncio
    async def test_thread_message_count_tracking(self, thread_service: ThreadService):
        """Test that thread message count is properly tracked."""
        # Create a thread
        user_id = "test_user_messages"
        thread = await thread_service.create_thread(
            user_id=user_id,
            title="Message Count Thread"
        )
        
        # Initially should have 0 messages
        assert thread.message_count == 0
        
        # Add some messages (simulate message service interaction)
        await thread_service.increment_message_count(thread.id)
        await thread_service.increment_message_count(thread.id)
        await thread_service.increment_message_count(thread.id)
        
        # Verify message count is updated
        updated_thread = await thread_service.get_thread(thread.id)
        assert updated_thread.message_count == 3
    
    @pytest.mark.asyncio
    async def test_delete_thread(self, thread_service: ThreadService):
        """Test thread deletion functionality."""
        # Create a thread
        user_id = "test_user_delete"
        thread = await thread_service.create_thread(
            user_id=user_id,
            title="Thread to Delete"
        )
        
        thread_id = thread.id
        
        # Delete the thread
        success = await thread_service.delete_thread(thread_id)
        assert success is True
        
        # Verify thread no longer exists
        deleted_thread = await thread_service.get_thread(thread_id)
        assert deleted_thread is None


class TestThreadErrorHandling:
    """Test error handling in thread operations."""
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_thread(self, thread_service: ThreadService):
        """Test retrieving a thread that doesn't exist."""
        nonexistent_id = "thread_123456789"
        
        thread = await thread_service.get_thread(nonexistent_id)
        assert thread is None
    
    @pytest.mark.asyncio
    async def test_create_thread_with_invalid_user(self, thread_service: ThreadService):
        """Test creating a thread with invalid user ID."""
        # Empty user ID should raise an error
        with pytest.raises(ValueError):
            await thread_service.create_thread(
                user_id="",
                title="Invalid User Thread"
            )
        
        # Null user ID should raise an error
        with pytest.raises(ValueError):
            await thread_service.create_thread(
                user_id=None,
                title="Null User Thread"
            )
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_thread_status(self, thread_service: ThreadService):
        """Test updating status of a thread that doesn't exist."""
        nonexistent_id = "thread_nonexistent"
        
        result = await thread_service.update_thread_status(
            thread_id=nonexistent_id,
            status="archived"
        )
        
        assert result is None


class TestThreadConcurrency:
    """Test thread operations under concurrent conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_thread_creation(self, thread_service: ThreadService):
        """Test creating multiple threads concurrently."""
        user_id = "test_user_concurrent"
        num_threads = 5
        
        # Create multiple threads concurrently
        tasks = []
        for i in range(num_threads):
            task = thread_service.create_thread(
                user_id=user_id,
                title=f"Concurrent Thread {i}"
            )
            tasks.append(task)
        
        # Wait for all threads to be created
        created_threads = await asyncio.gather(*tasks)
        
        # Verify all threads were created successfully
        assert len(created_threads) == num_threads
        
        # Verify all threads have unique IDs
        thread_ids = {t.id for t in created_threads}
        assert len(thread_ids) == num_threads
        
        # Verify all threads belong to the same user
        for thread in created_threads:
            assert thread.user_id == user_id
    
    @pytest.mark.asyncio
    async def test_concurrent_message_count_updates(self, thread_service: ThreadService):
        """Test concurrent message count updates on the same thread."""
        # Create a thread
        user_id = "test_user_concurrent_count"
        thread = await thread_service.create_thread(
            user_id=user_id,
            title="Concurrent Count Thread"
        )
        
        num_increments = 10
        
        # Increment message count concurrently
        tasks = []
        for _ in range(num_increments):
            task = thread_service.increment_message_count(thread.id)
            tasks.append(task)
        
        # Wait for all increments to complete
        await asyncio.gather(*tasks)
        
        # Verify final count is correct
        updated_thread = await thread_service.get_thread(thread.id)
        assert updated_thread.message_count == num_increments


class TestThreadDatabaseIntegrity:
    """Test thread operations maintain database integrity."""
    
    @pytest.mark.asyncio
    async def test_thread_persistence_across_service_instances(self, db_manager: DatabaseManager):
        """Test that thread data persists across different service instances."""
        user_id = "test_user_persistence"
        title = "Persistent Thread"
        
        # Create thread with first service instance
        service1 = ThreadService()
        thread = await service1.create_thread(
            user_id=user_id,
            title=title
        )
        
        thread_id = thread.id
        
        # Retrieve thread with second service instance
        service2 = ThreadService()
        retrieved_thread = await service2.get_thread(thread_id)
        
        assert retrieved_thread is not None
        assert retrieved_thread.id == thread_id
        assert retrieved_thread.title == title
        assert retrieved_thread.user_id == user_id
    
    @pytest.mark.asyncio
    async def test_thread_transaction_rollback(self, thread_service: ThreadService, db_manager: DatabaseManager):
        """Test that failed thread operations properly rollback transactions."""
        user_id = "test_user_rollback"
        
        # Mock a database error during thread creation
        with patch.object(db_manager, 'execute', side_effect=Exception("Database error")):
            with pytest.raises(Exception):
                await thread_service.create_thread(
                    user_id=user_id,
                    title="Rollback Test Thread"
                )
        
        # Verify no partial thread data was left in database
        user_threads = await thread_service.list_user_threads(user_id)
        assert len(user_threads) == 0


# Performance Test
class TestThreadPerformance:
    """Test thread operations performance."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bulk_thread_operations_performance(self, thread_service: ThreadService):
        """Test performance of bulk thread operations."""
        user_id = "test_user_performance"
        num_threads = 100
        
        # Measure thread creation time
        start_time = datetime.now()
        
        # Create many threads
        created_threads = []
        for i in range(num_threads):
            thread = await thread_service.create_thread(
                user_id=user_id,
                title=f"Performance Thread {i}"
            )
            created_threads.append(thread)
        
        creation_time = (datetime.now() - start_time).total_seconds()
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert creation_time < 30.0, f"Thread creation took too long: {creation_time}s"
        
        # Measure retrieval time
        start_time = datetime.now()
        
        user_threads = await thread_service.list_user_threads(
            user_id=user_id,
            limit=num_threads
        )
        
        retrieval_time = (datetime.now() - start_time).total_seconds()
        
        assert retrieval_time < 5.0, f"Thread retrieval took too long: {retrieval_time}s"
        assert len(user_threads) == num_threads


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])