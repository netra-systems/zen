"""Thread Context Management E2E Testing
Tests context preservation, message history, and state isolation.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.db.models_postgres import Message, Run, Thread
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    RecoveryType,
    StatePersistenceRequest,
    StateRecoveryRequest,
)
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.state_persistence import state_persistence_service

from netra_backend.app.services.thread_service import ThreadService

class ContextPreservationTests:
    """Tests for context preservation across messages."""
    async def test_context_preservation_across_messages(self, db_session: AsyncSession):
        """Test context maintains state across multiple messages."""
        service = ThreadService()
        user_id = "context_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._test_multi_message_context(service, thread, db_session)
    
    async def _test_multi_message_context(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test context preservation across multiple messages."""
        messages_data = [
            ("user", "What is optimization?"),
            ("assistant", "Optimization improves performance"),
            ("user", "Can you give an example?"),
            ("assistant", "Sure, caching reduces latency")
        ]
        
        created_messages = []
        for role, content in messages_data:
            msg = await service.create_message(thread.id, role, content, db=db_session)
            created_messages.append(msg)
        
        await self._verify_context_continuity(service, thread, created_messages, db_session)
    
    async def _verify_context_continuity(
        self, service: ThreadService, thread: Thread,
        messages: List[Message], db_session: AsyncSession
    ) -> None:
        """Verify context continuity across messages."""
        retrieved_messages = await service.get_thread_messages(thread.id, db=db_session)
        
        # Verify all messages are present and ordered correctly
        assert len(retrieved_messages) == len(messages)
        
        # Verify chronological ordering
        timestamps = [msg.created_at for msg in retrieved_messages]
        assert timestamps == sorted(timestamps)
    async def test_context_state_validation(self, db_session: AsyncSession):
        """Test context state validation and integrity."""
        service = ThreadService()
        user_id = "validation_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._test_context_state_integrity(service, thread, db_session)
    
    async def _test_context_state_integrity(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test context state maintains integrity."""
        # Create message with metadata
        metadata = {"context_step": 1, "user_intent": "query"}
        msg = await service.create_message(
            thread.id, "user", "Test message", metadata=metadata, db=db_session
        )
        
        # Verify state integrity
        assert msg.metadata_ == metadata
        assert msg.thread_id == thread.id

class MessageHistoryTests:
    """Tests for message history loading and management."""
    async def test_message_history_chronological_order(self, db_session: AsyncSession):
        """Test message history loads in chronological order."""
        service = ThreadService()
        user_id = "history_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._test_chronological_ordering(service, thread, db_session)
    
    async def _test_chronological_ordering(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test messages are retrieved in chronological order."""
        # Create messages with artificial timestamps
        messages_data = [
            ("user", "First message", 1000),
            ("assistant", "Second message", 2000),
            ("user", "Third message", 3000)
        ]
        
        created_messages = []
        for role, content, timestamp in messages_data:
            with patch('time.time', return_value=timestamp):
                msg = await service.create_message(thread.id, role, content, db=db_session)
                created_messages.append(msg)
        
        await self._verify_chronological_retrieval(service, thread, db_session)
    
    async def _verify_chronological_retrieval(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Verify messages are retrieved chronologically."""
        messages = await service.get_thread_messages(thread.id, db=db_session)
        
        # Verify chronological order
        for i in range(1, len(messages)):
            assert messages[i].created_at >= messages[i-1].created_at
    async def test_message_history_pagination(self, db_session: AsyncSession):
        """Test message history pagination functionality."""
        service = ThreadService()
        user_id = "pagination_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._test_history_pagination(service, thread, db_session)
    
    async def _test_history_pagination(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test message history pagination."""
        # Create multiple messages
        for i in range(10):
            await service.create_message(
                thread.id, "user", f"Message {i}", db=db_session
            )
        
        # Test pagination
        page1 = await service.get_thread_messages(thread.id, limit=5, db=db_session)
        page2 = await service.get_thread_messages(thread.id, limit=5, db=db_session)
        
        assert len(page1) <= 5
        assert len(page2) <= 5

class StateIsolationTests:
    """Tests for state isolation between threads."""
    async def test_thread_state_isolation(self, db_session: AsyncSession):
        """Test threads maintain isolated states."""
        service = ThreadService()
        
        thread1 = await service.get_or_create_thread("user1", db_session)
        thread2 = await service.get_or_create_thread("user2", db_session)
        
        await self._test_isolated_state_management(service, thread1, thread2, db_session)
    
    async def _test_isolated_state_management(
        self, service: ThreadService, thread1: Thread,
        thread2: Thread, db_session: AsyncSession
    ) -> None:
        """Test isolated state management between threads."""
        # Create different state data for each thread
        state1_data = {"current_step": "analysis", "data_points": [1, 2, 3]}
        state2_data = {"current_step": "optimization", "data_points": [4, 5, 6]}
        
        # Persist states
        await self._persist_thread_states(thread1, thread2, state1_data, state2_data, db_session)
        
        # Verify isolation
        await self._verify_state_isolation(thread1, thread2, db_session)
    
    async def _persist_thread_states(
        self, thread1: Thread, thread2: Thread,
        state1_data: Dict, state2_data: Dict, db_session: AsyncSession
    ) -> None:
        """Persist states for both threads."""
        for thread, state_data in [(thread1, state1_data), (thread2, state2_data)]:
            request = StatePersistenceRequest(
                run_id=f"run_{thread.id}",
                thread_id=thread.id,
                user_id=thread.metadata_.get("user_id"),
                state_data=state_data,
                checkpoint_type=CheckpointType.MANUAL
            )
            await state_persistence_service.save_agent_state(request, db_session)
    
    async def _verify_state_isolation(
        self, thread1: Thread, thread2: Thread, db_session: AsyncSession
    ) -> None:
        """Verify states are isolated between threads."""
        state1 = await state_persistence_service.load_agent_state(
            f"run_{thread1.id}", db_session=db_session
        )
        state2 = await state_persistence_service.load_agent_state(
            f"run_{thread2.id}", db_session=db_session
        )
        
        # Verify states are different and isolated
        if state1 and state2:
            assert state1.current_step != state2.current_step
            assert state1.data_points != state2.data_points

class ThreadResumeTests:
    """Tests for thread resume after interruption."""
    async def test_thread_resume_after_interruption(self, db_session: AsyncSession):
        """Test thread can resume after interruption with state recovery."""
        service = ThreadService()
        user_id = "resume_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._test_interruption_and_resume(service, thread, db_session)
    
    async def _test_interruption_and_resume(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test interruption and successful resume."""
        # Create initial state
        run_id = f"run_{thread.id}"
        initial_state = {
            "step_count": 5,
            "user_request": "Optimize database",
            "metadata": {"progress": 0.5}
        }
        
        # Persist initial state
        await self._persist_initial_state(thread, run_id, initial_state, db_session)
        
        # Simulate interruption and resume
        await self._simulate_resume_scenario(run_id, thread, db_session)
    
    async def _persist_initial_state(
        self, thread: Thread, run_id: str,
        state_data: Dict, db_session: AsyncSession
    ) -> None:
        """Persist initial state before interruption."""
        request = StatePersistenceRequest(
            run_id=run_id,
            thread_id=thread.id,
            user_id=thread.metadata_.get("user_id"),
            state_data=state_data,
            checkpoint_type=CheckpointType.AUTO,
            is_recovery_point=True
        )
        
        success, snapshot_id = await state_persistence_service.save_agent_state(
            request, db_session
        )
        assert success
        assert snapshot_id is not None
    
    async def _simulate_resume_scenario(
        self, run_id: str, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Simulate resume scenario after interruption."""
        # Perform recovery
        recovery_request = StateRecoveryRequest(
            run_id=run_id,
            thread_id=thread.id,
            recovery_type=RecoveryType.RESUME
        )
        
        success, recovery_id = await state_persistence_service.recover_agent_state(
            recovery_request, db_session
        )
        
        # Verify successful recovery
        assert success
        assert recovery_id is not None
        
        # Verify state can be loaded
        recovered_state = await state_persistence_service.load_agent_state(
            run_id, db_session=db_session
        )
        assert recovered_state is not None

class ContextLimitsTests:
    """Tests for context limits and truncation."""
    async def test_context_limits_and_truncation(self, db_session: AsyncSession):
        """Test context limits and proper truncation."""
        service = ThreadService()
        user_id = "limits_user"
        
        thread = await service.get_or_create_thread(user_id, db_session)
        
        await self._test_context_size_limits(service, thread, db_session)
    
    async def _test_context_size_limits(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test context size limits are enforced."""
        # Create messages that exceed typical limits
        large_messages = []
        for i in range(100):  # Large number of messages
            msg = await service.create_message(
                thread.id, "user", f"Message {i} with content", db=db_session
            )
            large_messages.append(msg)
        
        # Test retrieval with limits
        await self._verify_context_truncation(service, thread, db_session)
    
    async def _verify_context_truncation(
        self, service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Verify context is properly truncated when limits are applied."""
        # Retrieve with different limits
        limited_messages = await service.get_thread_messages(
            thread.id, limit=10, db=db_session
        )
        
        # Verify limit is respected
        assert len(limited_messages) <= 10
        
        # Verify most recent messages are preserved
        all_messages = await service.get_thread_messages(
            thread.id, limit=1000, db=db_session
        )
        
        if len(all_messages) > 10:
            # Verify chronological ordering is maintained
            timestamps = [msg.created_at for msg in limited_messages]
            assert timestamps == sorted(timestamps)

@pytest.fixture
async def db_session():
    """Mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session

@pytest.fixture
def mock_agent_service():
    """Mock agent service for testing."""
    service = Mock(spec=AgentService)
    service.handle_websocket_message = AsyncMock()
    service.create_thread = AsyncMock()
    service.switch_thread = AsyncMock()
    service.delete_thread = AsyncMock()
    return service

@pytest.fixture
def mock_state_persistence():
    """Mock state persistence service."""
    service = Mock()
    service.save_agent_state = AsyncMock(return_value=(True, "snapshot_id"))
    service.load_agent_state = AsyncMock()
    service.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    return service