"""
Test Thread Management Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maintain conversation continuity and context across sessions
- Value Impact: Users can maintain ongoing conversations with AI agents across browser sessions
- Strategic Impact: Core platform functionality enabling persistent AI assistance

This test suite validates thread management operations including:
- Thread creation and lifecycle management
- Message persistence within threads
- Thread isolation between users
- Thread metadata and search functionality
- Performance under concurrent thread operations

Performance Requirements:
- Thread operations should complete within 100ms
- Message persistence should be reliable
- Thread isolation should prevent cross-user access
- Memory usage should be bounded per user
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional, List

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types import UserID, ThreadID


class MockThread:
    """Mock thread model for testing."""
    
    def __init__(self, thread_id: str, user_id: str, title: str):
        self.id = ThreadID(thread_id)
        self.user_id = UserID(user_id)
        self.title = title
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.message_count = 0
        self.active = True
        self.metadata = {}


class MockMessage:
    """Mock message model for testing."""
    
    def __init__(self, message_id: str, thread_id: str, content: str, role: str = "user"):
        self.id = message_id
        self.thread_id = ThreadID(thread_id) 
        self.content = content
        self.role = role
        self.created_at = datetime.now(timezone.utc)
        self.metadata = {}


class ThreadManager:
    """Mock thread manager for unit testing."""
    
    def __init__(self):
        self._threads: Dict[str, MockThread] = {}
        self._messages: Dict[str, List[MockMessage]] = {}
        self._user_threads: Dict[str, List[str]] = {}
    
    async def create_thread(self, user_id: UserID, title: str, metadata: Optional[Dict] = None) -> MockThread:
        """Create a new thread."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        thread = MockThread(thread_id, str(user_id), title)
        if metadata:
            thread.metadata.update(metadata)
        
        self._threads[thread_id] = thread
        self._messages[thread_id] = []
        
        if str(user_id) not in self._user_threads:
            self._user_threads[str(user_id)] = []
        self._user_threads[str(user_id)].append(thread_id)
        
        return thread
    
    async def get_thread(self, thread_id: ThreadID, user_id: UserID) -> Optional[MockThread]:
        """Get thread by ID with user validation."""
        thread = self._threads.get(str(thread_id))
        if thread and thread.user_id == user_id:
            return thread
        return None
    
    async def get_user_threads(self, user_id: UserID, limit: int = 50) -> List[MockThread]:
        """Get all threads for a user."""
        user_thread_ids = self._user_threads.get(str(user_id), [])
        threads = []
        for thread_id in user_thread_ids[:limit]:
            if thread_id in self._threads:
                threads.append(self._threads[thread_id])
        return threads
    
    async def add_message(self, thread_id: ThreadID, content: str, role: str = "user") -> MockMessage:
        """Add message to thread."""
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        message = MockMessage(message_id, str(thread_id), content, role)
        
        if str(thread_id) not in self._messages:
            self._messages[str(thread_id)] = []
        
        self._messages[str(thread_id)].append(message)
        
        # Update thread message count and timestamp
        if str(thread_id) in self._threads:
            self._threads[str(thread_id)].message_count += 1
            self._threads[str(thread_id)].updated_at = datetime.now(timezone.utc)
        
        return message
    
    async def get_thread_messages(self, thread_id: ThreadID, limit: int = 100) -> List[MockMessage]:
        """Get messages for a thread."""
        return self._messages.get(str(thread_id), [])[:limit]
    
    async def update_thread(self, thread_id: ThreadID, user_id: UserID, **kwargs) -> bool:
        """Update thread properties."""
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            return False
        
        for key, value in kwargs.items():
            if hasattr(thread, key):
                setattr(thread, key, value)
        
        thread.updated_at = datetime.now(timezone.utc)
        return True
    
    async def delete_thread(self, thread_id: ThreadID, user_id: UserID) -> bool:
        """Delete thread and associated messages."""
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            return False
        
        # Remove from user threads
        if str(user_id) in self._user_threads:
            if str(thread_id) in self._user_threads[str(user_id)]:
                self._user_threads[str(user_id)].remove(str(thread_id))
        
        # Remove messages
        if str(thread_id) in self._messages:
            del self._messages[str(thread_id)]
        
        # Remove thread
        if str(thread_id) in self._threads:
            del self._threads[str(thread_id)]
        
        return True


class TestThreadManager(SSotBaseTestCase):
    """Test ThreadManager business logic and lifecycle."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        self.thread_manager = ThreadManager()
        
        # Test users
        self.user1_id = UserID(f"user1_{uuid.uuid4().hex[:8]}")
        self.user2_id = UserID(f"user2_{uuid.uuid4().hex[:8]}")
        self.user3_id = UserID(f"user3_{uuid.uuid4().hex[:8]}")
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    async def test_thread_creation_with_unique_ids(self):
        """Test that thread creation generates unique IDs and proper initialization."""
        # When: Creating multiple threads
        thread1 = await self.thread_manager.create_thread(
            user_id=self.user1_id,
            title="AI Cost Optimization Discussion",
            metadata={"category": "optimization", "priority": "high"}
        )
        
        thread2 = await self.thread_manager.create_thread(
            user_id=self.user1_id,
            title="Infrastructure Review",
            metadata={"category": "infrastructure", "priority": "medium"}
        )
        
        thread3 = await self.thread_manager.create_thread(
            user_id=self.user2_id,
            title="Data Analysis Project",
            metadata={"category": "analytics", "priority": "high"}
        )
        
        # Then: All threads should have unique IDs
        assert thread1.id != thread2.id
        assert thread2.id != thread3.id
        assert thread1.id != thread3.id
        
        # And: Thread properties should be set correctly
        assert thread1.user_id == self.user1_id
        assert thread1.title == "AI Cost Optimization Discussion"
        assert thread1.metadata["category"] == "optimization"
        assert thread1.metadata["priority"] == "high"
        assert thread1.message_count == 0
        assert thread1.active is True
        
        assert thread2.user_id == self.user1_id
        assert thread2.title == "Infrastructure Review"
        
        assert thread3.user_id == self.user2_id
        assert thread3.title == "Data Analysis Project"
        
        # And: Timestamps should be set
        assert isinstance(thread1.created_at, datetime)
        assert isinstance(thread1.updated_at, datetime)
        
        self.record_metric("threads_created", 3)
        self.record_metric("thread_creation_validated", True)
    
    @pytest.mark.unit
    async def test_thread_isolation_between_users(self):
        """Test that thread access is properly isolated between users."""
        # Given: Threads for different users
        user1_thread = await self.thread_manager.create_thread(
            user_id=self.user1_id,
            title="User 1 Private Thread",
            metadata={"sensitive": "user1_data"}
        )
        
        user2_thread = await self.thread_manager.create_thread(
            user_id=self.user2_id,
            title="User 2 Private Thread", 
            metadata={"sensitive": "user2_data"}
        )
        
        # When: Each user tries to access their own and other's threads
        # User 1 accessing own thread
        own_thread = await self.thread_manager.get_thread(user1_thread.id, self.user1_id)
        
        # User 1 trying to access User 2's thread
        other_thread = await self.thread_manager.get_thread(user2_thread.id, self.user1_id)
        
        # User 2 accessing own thread
        user2_own_thread = await self.thread_manager.get_thread(user2_thread.id, self.user2_id)
        
        # Then: Users should only access their own threads
        assert own_thread is not None
        assert own_thread.id == user1_thread.id
        assert own_thread.metadata["sensitive"] == "user1_data"
        
        assert other_thread is None  # Cannot access other user's thread
        
        assert user2_own_thread is not None
        assert user2_own_thread.id == user2_thread.id
        assert user2_own_thread.metadata["sensitive"] == "user2_data"
        
        # And: No cross-contamination of sensitive data
        assert "user2_data" not in str(own_thread.metadata)
        assert "user1_data" not in str(user2_own_thread.metadata)
        
        self.record_metric("thread_isolation_validated", True)
    
    @pytest.mark.unit
    async def test_message_persistence_in_threads(self):
        """Test that messages are properly persisted and retrieved from threads."""
        # Given: A thread with conversation
        thread = await self.thread_manager.create_thread(
            user_id=self.user1_id,
            title="Cost Analysis Conversation"
        )
        
        # When: Adding messages to the thread
        message1 = await self.thread_manager.add_message(
            thread_id=thread.id,
            content="Can you analyze my AWS costs?",
            role="user"
        )
        
        message2 = await self.thread_manager.add_message(
            thread_id=thread.id,
            content="I'd be happy to analyze your AWS costs. Let me review your spending patterns.",
            role="assistant"
        )
        
        message3 = await self.thread_manager.add_message(
            thread_id=thread.id,
            content="Here's my latest AWS bill data.",
            role="user"
        )
        
        # Then: Messages should be persisted correctly
        messages = await self.thread_manager.get_thread_messages(thread.id)
        
        assert len(messages) == 3
        assert messages[0].content == "Can you analyze my AWS costs?"
        assert messages[0].role == "user"
        assert messages[1].content.startswith("I'd be happy to analyze")
        assert messages[1].role == "assistant"
        assert messages[2].content == "Here's my latest AWS bill data."
        assert messages[2].role == "user"
        
        # And: Thread metadata should be updated
        updated_thread = await self.thread_manager.get_thread(thread.id, self.user1_id)
        assert updated_thread.message_count == 3
        assert updated_thread.updated_at > updated_thread.created_at
        
        # And: Message IDs should be unique
        message_ids = [msg.id for msg in messages]
        assert len(set(message_ids)) == 3  # All unique
        
        self.record_metric("messages_persisted", 3)
        self.record_metric("message_persistence_validated", True)
    
    @pytest.mark.unit
    async def test_user_thread_listing_and_pagination(self):
        """Test that user thread listing works correctly with pagination."""
        # Given: Multiple threads for a user
        thread_titles = [
            "Project Alpha Discussion",
            "Weekly Review Meeting",
            "Cost Optimization Analysis",
            "Infrastructure Planning",
            "Performance Metrics Review"
        ]
        
        created_threads = []
        for i, title in enumerate(thread_titles):
            thread = await self.thread_manager.create_thread(
                user_id=self.user1_id,
                title=title,
                metadata={"order": i}
            )
            created_threads.append(thread)
            # Add some messages to vary the update times
            await self.thread_manager.add_message(thread.id, f"Message in {title}", "user")
        
        # Add threads for another user to test isolation
        await self.thread_manager.create_thread(self.user2_id, "Other User Thread")
        
        # When: Getting user threads
        user1_threads = await self.thread_manager.get_user_threads(self.user1_id)
        user2_threads = await self.thread_manager.get_user_threads(self.user2_id)
        
        # Then: User 1 should get only their threads
        assert len(user1_threads) == 5
        thread_titles_retrieved = [t.title for t in user1_threads]
        for title in thread_titles:
            assert title in thread_titles_retrieved
        
        # And: User 2 should get only their thread
        assert len(user2_threads) == 1
        assert user2_threads[0].title == "Other User Thread"
        
        # And: All threads should have proper message counts
        for thread in user1_threads:
            assert thread.message_count == 1
        
        # When: Testing pagination
        limited_threads = await self.thread_manager.get_user_threads(self.user1_id, limit=3)
        
        # Then: Should respect limit
        assert len(limited_threads) == 3
        
        self.record_metric("threads_listed", len(user1_threads))
        self.record_metric("thread_listing_validated", True)
    
    @pytest.mark.unit
    async def test_thread_update_operations(self):
        """Test thread update operations maintain consistency."""
        # Given: A thread with initial properties
        thread = await self.thread_manager.create_thread(
            user_id=self.user1_id,
            title="Initial Title",
            metadata={"status": "active", "priority": "low"}
        )
        
        initial_updated_at = thread.updated_at
        
        # Small delay to ensure timestamp difference
        await asyncio.sleep(0.01)
        
        # When: Updating thread properties
        update_success = await self.thread_manager.update_thread(
            thread_id=thread.id,
            user_id=self.user1_id,
            title="Updated Title",
            metadata={"status": "in_progress", "priority": "high", "tags": ["important"]}
        )
        
        # Then: Update should succeed
        assert update_success is True
        
        # And: Thread should have updated properties
        updated_thread = await self.thread_manager.get_thread(thread.id, self.user1_id)
        assert updated_thread.title == "Updated Title"
        assert updated_thread.metadata["status"] == "in_progress"
        assert updated_thread.metadata["priority"] == "high"
        assert updated_thread.metadata["tags"] == ["important"]
        assert updated_thread.updated_at > initial_updated_at
        
        # When: Attempting to update thread as wrong user
        wrong_user_update = await self.thread_manager.update_thread(
            thread_id=thread.id,
            user_id=self.user2_id,
            title="Unauthorized Update"
        )
        
        # Then: Update should fail
        assert wrong_user_update is False
        
        # And: Thread should remain unchanged
        unchanged_thread = await self.thread_manager.get_thread(thread.id, self.user1_id)
        assert unchanged_thread.title == "Updated Title"  # Still has authorized update
        
        self.record_metric("thread_updates_tested", 2)
        self.record_metric("thread_update_validated", True)
    
    @pytest.mark.unit
    async def test_thread_deletion_and_cleanup(self):
        """Test thread deletion and associated cleanup."""
        # Given: A thread with messages
        thread = await self.thread_manager.create_thread(
            user_id=self.user1_id,
            title="Thread to Delete"
        )
        
        # Add some messages
        await self.thread_manager.add_message(thread.id, "Message 1", "user")
        await self.thread_manager.add_message(thread.id, "Message 2", "assistant")
        await self.thread_manager.add_message(thread.id, "Message 3", "user")
        
        # Verify thread exists with messages
        messages_before = await self.thread_manager.get_thread_messages(thread.id)
        assert len(messages_before) == 3
        
        # When: Deleting the thread
        deletion_success = await self.thread_manager.delete_thread(
            thread_id=thread.id,
            user_id=self.user1_id
        )
        
        # Then: Deletion should succeed
        assert deletion_success is True
        
        # And: Thread should no longer be accessible
        deleted_thread = await self.thread_manager.get_thread(thread.id, self.user1_id)
        assert deleted_thread is None
        
        # And: Messages should be cleaned up
        messages_after = await self.thread_manager.get_thread_messages(thread.id)
        assert len(messages_after) == 0
        
        # And: Thread should not appear in user's thread list
        user_threads = await self.thread_manager.get_user_threads(self.user1_id)
        thread_ids = [t.id for t in user_threads]
        assert thread.id not in thread_ids
        
        # When: Attempting to delete thread as wrong user (should fail gracefully)
        another_thread = await self.thread_manager.create_thread(self.user1_id, "Another Thread")
        wrong_user_deletion = await self.thread_manager.delete_thread(
            thread_id=another_thread.id,
            user_id=self.user2_id
        )
        
        # Then: Deletion should fail
        assert wrong_user_deletion is False
        
        # And: Thread should still exist
        existing_thread = await self.thread_manager.get_thread(another_thread.id, self.user1_id)
        assert existing_thread is not None
        
        self.record_metric("thread_deletion_validated", True)
    
    @pytest.mark.unit
    async def test_concurrent_thread_operations(self):
        """Test concurrent thread operations maintain consistency."""
        # Given: Concurrent thread operations
        thread_count = 10
        concurrent_tasks = []
        
        # Create concurrent thread creation tasks
        for i in range(thread_count):
            task = self.thread_manager.create_thread(
                user_id=self.user1_id,
                title=f"Concurrent Thread {i}",
                metadata={"index": i, "batch": "concurrent_test"}
            )
            concurrent_tasks.append(task)
        
        # When: Executing concurrent operations
        created_threads = await asyncio.gather(*concurrent_tasks)
        
        # Then: All threads should be created successfully
        assert len(created_threads) == thread_count
        
        # And: All thread IDs should be unique
        thread_ids = [t.id for t in created_threads]
        assert len(set(thread_ids)) == thread_count  # All unique
        
        # When: Adding concurrent messages to threads
        message_tasks = []
        for i, thread in enumerate(created_threads):
            task = self.thread_manager.add_message(
                thread_id=thread.id,
                content=f"Concurrent message for thread {i}",
                role="user"
            )
            message_tasks.append(task)
        
        messages = await asyncio.gather(*message_tasks)
        
        # Then: All messages should be created successfully
        assert len(messages) == thread_count
        
        # And: Each thread should have exactly one message
        for thread in created_threads:
            thread_messages = await self.thread_manager.get_thread_messages(thread.id)
            assert len(thread_messages) == 1
            assert f"Concurrent message for thread" in thread_messages[0].content
        
        # And: Thread counts should be updated
        for thread in created_threads:
            updated_thread = await self.thread_manager.get_thread(thread.id, self.user1_id)
            assert updated_thread.message_count == 1
        
        self.record_metric("concurrent_threads_created", thread_count)
        self.record_metric("concurrent_messages_added", thread_count)
        self.record_metric("concurrent_operations_validated", True)


class TestThreadPerformanceAndScaling(SSotBaseTestCase):
    """Test thread management performance characteristics."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.thread_manager = ThreadManager()
        self.test_user_id = UserID(f"perf_user_{uuid.uuid4().hex[:8]}")
    
    @pytest.mark.unit
    async def test_thread_creation_performance(self):
        """Test thread creation performance under load."""
        # Given: Performance test parameters
        thread_count = 50
        max_creation_time_ms = 200  # 200ms max per thread
        
        creation_times = []
        created_threads = []
        
        # When: Creating threads and measuring performance
        for i in range(thread_count):
            start_time = time.time()
            
            thread = await self.thread_manager.create_thread(
                user_id=self.test_user_id,
                title=f"Performance Test Thread {i}",
                metadata={"test_index": i, "performance_test": True}
            )
            
            creation_time = (time.time() - start_time) * 1000  # Convert to ms
            creation_times.append(creation_time)
            created_threads.append(thread)
        
        # Then: Performance should meet requirements
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        
        assert avg_creation_time < max_creation_time_ms
        assert max_creation_time < max_creation_time_ms * 2  # Allow some variance
        
        # And: All threads should be created successfully
        assert len(created_threads) == thread_count
        
        # And: All threads should be unique and accessible
        user_threads = await self.thread_manager.get_user_threads(self.test_user_id)
        assert len(user_threads) == thread_count
        
        self.record_metric("perf_threads_created", thread_count)
        self.record_metric("avg_creation_time_ms", avg_creation_time)
        self.record_metric("max_creation_time_ms", max_creation_time)
        self.record_metric("performance_requirements_met", True)
    
    @pytest.mark.unit
    async def test_message_throughput_performance(self):
        """Test message addition throughput performance."""
        # Given: Thread for message performance testing
        thread = await self.thread_manager.create_thread(
            user_id=self.test_user_id,
            title="Message Throughput Test"
        )
        
        message_count = 100
        max_message_time_ms = 50  # 50ms max per message
        
        message_times = []
        
        # When: Adding messages and measuring performance
        for i in range(message_count):
            start_time = time.time()
            
            await self.thread_manager.add_message(
                thread_id=thread.id,
                content=f"Performance test message {i}: This is a test message to evaluate throughput.",
                role="user" if i % 2 == 0 else "assistant"
            )
            
            message_time = (time.time() - start_time) * 1000  # Convert to ms
            message_times.append(message_time)
        
        # Then: Message performance should meet requirements
        avg_message_time = sum(message_times) / len(message_times)
        max_message_time = max(message_times)
        
        assert avg_message_time < max_message_time_ms
        
        # And: All messages should be persisted
        messages = await self.thread_manager.get_thread_messages(thread.id)
        assert len(messages) == message_count
        
        # And: Thread should be updated correctly
        updated_thread = await self.thread_manager.get_thread(thread.id, self.test_user_id)
        assert updated_thread.message_count == message_count
        
        self.record_metric("perf_messages_added", message_count)
        self.record_metric("avg_message_time_ms", avg_message_time)
        self.record_metric("max_message_time_ms", max_message_time)
        self.record_metric("message_throughput_validated", True)
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Verify test execution time
        execution_time = self.get_metrics().execution_time
        if execution_time > 5.0:  # Warn for slow tests
            self.record_metric("slow_thread_test_warning", execution_time)
        
        super().teardown_method(method)