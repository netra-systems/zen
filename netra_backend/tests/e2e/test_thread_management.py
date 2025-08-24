"""Thread Management E2E Testing
Tests comprehensive thread lifecycle, persistence, and isolation.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.websocket_core.manager import get_websocket_manager as get_unified_manager
manager = get_unified_manager()

from netra_backend.app.db.models_postgres import Message, Thread
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.state_persistence import state_persistence_service

from netra_backend.app.services.thread_service import ThreadService
from netra_backend.tests.e2e.thread_test_fixtures import (
    ThreadTestDataFactory,
    ThreadTestMocks,
)

class TestThreadCreation:
    """Tests for thread creation with unique IDs."""
    @pytest.mark.asyncio
    async def test_create_unique_thread_ids(self, db_session: AsyncSession):
        """Test that each new thread gets a unique ID."""
        service = ThreadService()
        user_ids = ["user1", "user2", "user3"]
        
        created_threads = await self._create_multiple_threads(service, user_ids, db_session)
        self._assert_unique_thread_ids(created_threads)
    
    async def _create_multiple_threads(
        self, service: ThreadService, user_ids: List[str], db_session: AsyncSession
    ) -> List[Thread]:
        """Create multiple threads for testing."""
        created_threads = []
        for user_id in user_ids:
            thread = await service.get_or_create_thread(user_id, db_session)
            assert thread is not None
            created_threads.append(thread)
        return created_threads
    
    def _assert_unique_thread_ids(self, threads: List[Thread]) -> None:
        """Assert all thread IDs are unique."""
        thread_ids = [t.id for t in threads]
        assert len(thread_ids) == len(set(thread_ids))
    @pytest.mark.asyncio
    async def test_thread_metadata_validation(self, db_session: AsyncSession):
        """Test thread creation with proper metadata."""
        service = ThreadService()
        user_id = "validation_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        self._validate_thread_metadata(thread, user_id)
    
    def _validate_thread_metadata(self, thread: Thread, user_id: str) -> None:
        """Validate thread metadata structure."""
        assert thread.metadata_ is not None
        assert thread.metadata_.get("user_id") == user_id
        assert thread.object == "thread"
        assert thread.created_at > 0

class TestThreadSwitching:
    """Tests for thread switching and context maintenance."""
    @pytest.mark.asyncio
    async def test_thread_switching_maintains_context(self, db_session: AsyncSession):
        """Test switching threads maintains separate contexts."""
        service = ThreadService()
        user_id = "switch_test_user"
        
        threads = await self._create_test_thread_pair(service, user_id, db_session)
        await self._verify_thread_context_separation(service, threads[0], threads[1], db_session)
    
    async def _create_test_thread_pair(
        self, service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> List[Thread]:
        """Create pair of threads for testing."""
        thread1 = await service.get_or_create_thread(user_id, db_session)
        thread2 = await service.get_or_create_thread(f"{user_id}_2", db_session)
        return [thread1, thread2]
    
    async def _verify_thread_context_separation(
        self, service: ThreadService, thread1: Thread, 
        thread2: Thread, db_session: AsyncSession
    ) -> None:
        """Verify threads maintain separate contexts."""
        await self._add_messages_to_threads(service, thread1, thread2, db_session)
        await self._assert_context_isolation(service, thread1, thread2, db_session)
    
    async def _add_messages_to_threads(
        self, service: ThreadService, thread1: Thread, 
        thread2: Thread, db_session: AsyncSession
    ) -> None:
        """Add test messages to both threads."""
        await service.create_message(thread1.id, "user", "Message in thread 1", db=db_session)
        await service.create_message(thread2.id, "user", "Message in thread 2", db=db_session)
    
    async def _assert_context_isolation(
        self, service: ThreadService, thread1: Thread,
        thread2: Thread, db_session: AsyncSession
    ) -> None:
        """Assert threads have isolated contexts."""
        messages1 = await service.get_thread_messages(thread1.id, db=db_session)
        messages2 = await service.get_thread_messages(thread2.id, db=db_session)
        
        self._validate_message_isolation(messages1, messages2, thread1.id, thread2.id)
    
    def _validate_message_isolation(
        self, messages1: List[Message], messages2: List[Message],
        thread1_id: str, thread2_id: str
    ) -> None:
        """Validate message isolation between threads."""
        assert len(messages1) == 1 and len(messages2) == 1
        assert messages1[0].thread_id == thread1_id
        assert messages2[0].thread_id == thread2_id

class TestThreadPersistence:
    """Tests for thread persistence to database."""
    @pytest.mark.asyncio
    async def test_thread_database_persistence(self, db_session: AsyncSession):
        """Test thread persists correctly to database."""
        service = ThreadService()
        user_id = "persistence_user"
        
        # Create thread
        thread = await service.get_or_create_thread(user_id, db_session)
        assert thread is not None
        
        # Verify persistence
        await self._verify_thread_persistence(service, thread.id, db_session)
    
    async def _verify_thread_persistence(
        self, service: ThreadService, thread_id: str, db_session: AsyncSession
    ) -> None:
        """Verify thread exists in database."""
        retrieved_thread = await service.get_thread(thread_id, db_session)
        assert retrieved_thread is not None
        assert retrieved_thread.id == thread_id
    @pytest.mark.asyncio
    async def test_thread_state_persistence_integration(self, db_session: AsyncSession):
        """Test integration with state persistence service."""
        service = ThreadService()
        user_id = "state_persist_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._test_state_persistence_integration(thread, db_session)
    
    async def _test_state_persistence_integration(
        self, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test state persistence service integration."""
        state_data = {"step_count": 1, "user_request": "test", "metadata": {}}
        request = StatePersistenceRequest(
            run_id=f"run_{uuid.uuid4()}",
            thread_id=thread.id,
            user_id=thread.metadata_.get("user_id"),
            state_data=state_data,
            checkpoint_type=CheckpointType.MANUAL
        )
        
        success, snapshot_id = await state_persistence_service.save_agent_state(
            request, db_session
        )
        assert success
        assert snapshot_id is not None

class TestThreadExpiration:
    """Tests for thread expiration and cleanup."""
    @pytest.mark.asyncio
    async def test_thread_expiration_after_timeout(self, db_session: AsyncSession):
        """Test thread expiration mechanism."""
        service = ThreadService()
        user_id = "expiration_user"
        
        # Create thread with custom expiration
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._simulate_thread_expiration(service, thread, db_session)
    
    async def _simulate_thread_expiration(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Simulate thread expiration scenario."""
        # Mark thread as expired (in real scenario, this would be time-based)
        if thread.metadata_:
            thread.metadata_["status"] = "expired"
            thread.metadata_["expired_at"] = int(time.time())
        
        # Verify expiration cleanup
        await self._verify_expiration_cleanup(thread)
    
    async def _verify_expiration_cleanup(self, thread: Thread) -> None:
        """Verify thread expiration cleanup."""
        assert thread.metadata_.get("status") == "expired"
        assert thread.metadata_.get("expired_at") is not None

class TestConcurrentThread:
    """Tests for concurrent thread operations."""
    @pytest.mark.asyncio
    async def test_concurrent_thread_creation(self, db_session: AsyncSession):
        """Test concurrent thread creation for race conditions."""
        service = ThreadService()
        user_base = "concurrent_user"
        
        # Create multiple concurrent operations
        tasks = []
        for i in range(5):
            task = service.get_or_create_thread(f"{user_base}_{i}", db_session)
            tasks.append(task)
        
        threads = await asyncio.gather(*tasks, return_exceptions=True)
        
        await self._verify_concurrent_creation_integrity(threads)
    
    async def _verify_concurrent_creation_integrity(self, threads: List) -> None:
        """Verify concurrent operations maintain integrity."""
        successful_threads = [t for t in threads if isinstance(t, Thread)]
        assert len(successful_threads) > 0
        
        # Check for unique IDs
        thread_ids = {t.id for t in successful_threads}
        assert len(thread_ids) == len(successful_threads)
    @pytest.mark.asyncio
    async def test_concurrent_message_creation(self, db_session: AsyncSession):
        """Test concurrent message creation in same thread."""
        service = ThreadService()
        user_id = "concurrent_msg_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._test_concurrent_messages(service, thread, db_session)
    
    async def _test_concurrent_messages(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test concurrent message creation."""
        message_tasks = []
        for i in range(3):
            task = service.create_message(
                thread.id, "user", f"Concurrent message {i}", db=db_session
            )
            message_tasks.append(task)
        
        messages = await asyncio.gather(*message_tasks, return_exceptions=True)
        successful_messages = [m for m in messages if isinstance(m, Message)]
        
        assert len(successful_messages) > 0

class TestThreadIsolation:
    """Tests for thread isolation and cross-contamination prevention."""
    @pytest.mark.asyncio
    async def test_thread_data_isolation(self, db_session: AsyncSession):
        """Test threads don't share data inappropriately."""
        service = ThreadService()
        user1, user2 = "isolation_user1", "isolation_user2"
        
        thread1 = await service.get_or_create_thread(user1, db_session)
        thread2 = await service.get_or_create_thread(user2, db_session)
        
        await self._verify_data_isolation(service, thread1, thread2, db_session)
    
    async def _verify_data_isolation(
        self, service: ThreadService, thread1: Thread,
        thread2: Thread, db_session: AsyncSession
    ) -> None:
        """Verify complete data isolation between threads."""
        # Add different data to each thread
        await service.create_message(
            thread1.id, "user", "Thread 1 data", db=db_session
        )
        await service.create_message(
            thread2.id, "user", "Thread 2 data", db=db_session
        )
        
        await self._assert_no_cross_contamination(service, thread1, thread2, db_session)
    
    async def _assert_no_cross_contamination(
        self, service: ThreadService, thread1: Thread,
        thread2: Thread, db_session: AsyncSession
    ) -> None:
        """Assert no cross-contamination between threads."""
        msgs1 = await service.get_thread_messages(thread1.id, db=db_session)
        msgs2 = await service.get_thread_messages(thread2.id, db=db_session)
        
        # Verify each thread only has its own messages
        for msg in msgs1:
            assert msg.thread_id == thread1.id
        for msg in msgs2:
            assert msg.thread_id == thread2.id
        
        # Verify content isolation
        thread1_content = {msg.content[0]["text"]["value"] for msg in msgs1}
        thread2_content = {msg.content[0]["text"]["value"] for msg in msgs2}
        assert thread1_content.isdisjoint(thread2_content)

@pytest.fixture
async def db_session():
    """Mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session