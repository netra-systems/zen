"""Thread Testing Fixtures and Helpers
Comprehensive fixtures and utilities for thread management testing.
"""

import asyncio
import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Message, Run, Thread
from netra_backend.app.schemas.agent_state import (
    AgentPhase,
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.state_persistence import state_persistence_service
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.fixture
async def websocket_manager():
    """Create WebSocket manager with proper UserExecutionContext for testing."""
    user_context = UserExecutionContext(
        user_id="test-user-123",
        thread_id="test-thread-456",
        run_id="test-run-789",
        request_id="test-request-789"
    )
    return create_websocket_manager(user_context)

class ThreadTestDataFactory:
    """Factory for creating thread test data."""
    
    @staticmethod
    def create_thread_data(user_id: str, **kwargs) -> Dict[str, Any]:
        """Create thread data with defaults."""
        return {
            "id": f"thread_{user_id}",
            "object": "thread",
            "created_at": int(time.time()),
            "metadata_": {"user_id": user_id, **kwargs.get("metadata", {})}
        }
    
    @staticmethod
    def create_message_data(thread_id: str, role: str, content: str, **kwargs) -> Dict[str, Any]:
        """Create message data with defaults."""
        return {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "object": "thread.message",
            "created_at": int(time.time()),
            "thread_id": thread_id,
            "role": role,
            "content": [{"type": "text", "text": {"value": content}}],
            "assistant_id": kwargs.get("assistant_id"),
            "run_id": kwargs.get("run_id"),
            "file_ids": [],
            "metadata_": kwargs.get("metadata", {})
        }
    
    @staticmethod
    def create_run_data(thread_id: str, assistant_id: str, **kwargs) -> Dict[str, Any]:
        """Create run data with defaults."""
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        return {
            "id": UnifiedIDManager.generate_run_id(thread_id),
            "object": "thread.run",
            "created_at": int(time.time()),
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "status": kwargs.get("status", "in_progress"),
            "model": kwargs.get("model", LLMModel.GEMINI_2_5_FLASH.value),
            "instructions": kwargs.get("instructions"),
            "tools": [],
            "file_ids": [],
            "metadata_": kwargs.get("metadata", {})
        }
    
    @staticmethod
    def create_state_data(phase: AgentPhase, **kwargs) -> Dict[str, Any]:
        """Create agent state data."""
        return {
            "step_count": kwargs.get("step_count", 1),
            "user_request": kwargs.get("user_request", "Test request"),
            "metadata": {
                "phase": phase.value,
                "timestamp": time.time(),
                **kwargs.get("metadata", {})
            }
        }

class ThreadTestScenarios:
    """Predefined test scenarios for comprehensive testing."""
    
    @staticmethod
    async def create_basic_conversation_scenario(
        thread_service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Create basic conversation scenario."""
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        
        # User message
        user_msg = await thread_service.create_message(
            thread.id, "user", "Hello, I need help with optimization", db=db_session
        )
        
        # Assistant response
        assistant_msg = await thread_service.create_message(
            thread.id, "assistant", "I'd be happy to help with optimization",
            assistant_id="helper_agent", db=db_session
        )
        
        return {
            "thread": thread,
            "messages": [user_msg, assistant_msg],
            "user_id": user_id
        }
    
    @staticmethod
    async def create_multi_agent_scenario(
        thread_service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Create multi-agent coordination scenario."""
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        
        # Supervisor run
        supervisor_run = await thread_service.create_run(
            thread.id, "supervisor_agent", db=db_session
        )
        
        # Data agent run
        data_run = await thread_service.create_run(
            thread.id, "data_agent", db=db_session
        )
        
        # Messages from different agents
        messages = []
        messages.append(await thread_service.create_message(
            thread.id, "assistant", "Analyzing your request",
            assistant_id="supervisor_agent", run_id=supervisor_run.id, db=db_session
        ))
        
        messages.append(await thread_service.create_message(
            thread.id, "assistant", "Processing data analysis",
            assistant_id="data_agent", run_id=data_run.id, db=db_session
        ))
        
        return {
            "thread": thread,
            "runs": [supervisor_run, data_run],
            "messages": messages,
            "user_id": user_id
        }
    
    @staticmethod
    async def create_interrupted_scenario(
        thread_service: ThreadService, user_id: str, db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Create interrupted workflow scenario."""
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        
        run = await thread_service.create_run(
            thread.id, "processing_agent", db=db_session
        )
        
        # Simulate interruption with state persistence
        state_data = ThreadTestDataFactory.create_state_data(
            AgentPhase.DATA_ANALYSIS,
            step_count=5,
            user_request="Long running analysis"
        )
        
        request = StatePersistenceRequest(
            run_id=run.id,
            thread_id=thread.id,
            user_id=user_id,
            state_data=state_data,
            checkpoint_type=CheckpointType.AUTO,
            is_recovery_point=True
        )
        
        success, snapshot_id = await state_persistence_service.save_agent_state(
            request, db_session
        )
        
        return {
            "thread": thread,
            "run": run,
            "snapshot_id": snapshot_id,
            "state_data": state_data,
            "user_id": user_id
        }

class ThreadTestValidators:
    """Validation utilities for thread testing."""
    
    @staticmethod
    def validate_thread_structure(thread: Thread, user_id: str) -> None:
        """Validate thread structure and metadata."""
        assert thread is not None
        assert thread.id is not None
        assert thread.object == "thread"
        assert thread.created_at > 0
        assert thread.metadata_ is not None
        assert thread.metadata_.get("user_id") == user_id
    
    @staticmethod
    def validate_message_structure(message: Message, thread_id: str) -> None:
        """Validate message structure."""
        assert message is not None
        assert message.id is not None
        assert message.object == "thread.message"
        assert message.thread_id == thread_id
        assert message.role in ["user", "assistant"]
        assert message.content is not None
        assert message.created_at > 0
    
    @staticmethod
    def validate_run_structure(run: Run, thread_id: str) -> None:
        """Validate run structure."""
        assert run is not None
        assert run.id is not None
        assert run.object == "thread.run"
        assert run.thread_id == thread_id
        assert run.assistant_id is not None
        assert run.status in ["in_progress", "completed", "failed"]
        assert run.model is not None
        assert run.created_at > 0
    
    @staticmethod
    def validate_message_chronology(messages: List[Message]) -> None:
        """Validate messages are in chronological order."""
        if len(messages) <= 1:
            return
        
        for i in range(1, len(messages)):
            assert messages[i].created_at >= messages[i-1].created_at
    
    @staticmethod
    def validate_thread_isolation(
        thread1_data: Dict[str, Any], thread2_data: Dict[str, Any]
    ) -> None:
        """Validate isolation between threads."""
        thread1 = thread1_data["thread"]
        thread2 = thread2_data["thread"]
        
        # Verify different thread IDs
        assert thread1.id != thread2.id
        
        # Verify different user IDs if applicable
        user1 = thread1.metadata_.get("user_id")
        user2 = thread2.metadata_.get("user_id")
        if user1 != user2:
            assert user1 != user2
        
        # Verify no shared messages
        messages1 = thread1_data.get("messages", [])
        messages2 = thread2_data.get("messages", [])
        
        thread1_msg_ids = {msg.id for msg in messages1}
        thread2_msg_ids = {msg.id for msg in messages2}
        
        assert thread1_msg_ids.isdisjoint(thread2_msg_ids)

class ThreadTestMocks:
    """Mock objects for thread testing."""
    
    @staticmethod
    def create_mock_thread_service() -> Mock:
        """Create mock thread service."""
        # Mock: Component isolation for controlled unit testing
        service = Mock(spec=ThreadService)
        # Mock: Generic component isolation for controlled unit testing
        service.get_or_create_thread = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.create_message = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.create_run = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.update_run_status = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.get_thread_messages = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.get_thread = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.switch_thread = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.delete_thread = AsyncMock()
        return service
    
    @staticmethod
    def create_mock_websocket_manager() -> Mock:
        """Create mock WebSocket manager."""
        # Mock: Generic component isolation for controlled unit testing
        manager_mock = Mock()
        # Mock: Generic component isolation for controlled unit testing
        manager_mock.send_message = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        manager_mock.broadcast_to_thread = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        manager_mock.connect_user_to_thread = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        manager_mock.disconnect_user_from_thread = AsyncMock()
        return manager_mock
    
    @staticmethod
    def create_mock_state_persistence() -> Mock:
        """Create mock state persistence service."""
        # Mock: Generic component isolation for controlled unit testing
        service = Mock()
        # Mock: Async component isolation for testing without real async operations
        service.save_agent_state = AsyncMock(return_value=(True, "snapshot_123"))
        # Mock: Generic component isolation for controlled unit testing
        service.load_agent_state = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        service.recover_agent_state = AsyncMock(return_value=(True, "recovery_123"))
        return service

class ThreadPerformanceTestUtils:
    """Utilities for thread performance testing."""
    
    @staticmethod
    async def measure_thread_creation_time(
        thread_service: ThreadService, user_ids: List[str], db_session: AsyncSession
    ) -> Dict[str, float]:
        """Measure thread creation performance."""
        results = {}
        
        for user_id in user_ids:
            start_time = time.perf_counter()
            await thread_service.get_or_create_thread(user_id, db_session)
            end_time = time.perf_counter()
            
            results[user_id] = end_time - start_time
        
        return results
    
    @staticmethod
    async def measure_concurrent_operations(
        thread_service: ThreadService, operations: List, concurrency: int
    ) -> Dict[str, Any]:
        """Measure concurrent operation performance."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_operation(operation):
            async with semaphore:
                return await operation()
        
        start_time = time.perf_counter()
        results = await asyncio.gather(
            *[limited_operation(op) for op in operations],
            return_exceptions=True
        )
        end_time = time.perf_counter()
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]
        
        return {
            "total_time": end_time - start_time,
            "successful_count": len(successful_results),
            "error_count": len(errors),
            "throughput": len(successful_results) / (end_time - start_time)
        }
    
    @staticmethod
    def analyze_performance_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics."""
        return {
            "average_time": sum(metrics.values()) / len(metrics) if metrics else 0,
            "max_time": max(metrics.values()) if metrics else 0,
            "min_time": min(metrics.values()) if metrics else 0,
            "operation_count": len(metrics)
        }

# Pytest fixtures for thread testing
@pytest.fixture
def thread_data_factory():
    """Thread test data factory fixture."""
    return ThreadTestDataFactory()

@pytest.fixture
def thread_scenarios():
    """Thread test scenarios fixture."""
    return ThreadTestScenarios()

@pytest.fixture
def thread_validators():
    """Thread validators fixture."""
    return ThreadTestValidators()

@pytest.fixture
def thread_mocks():
    """Thread mocks fixture."""
    return ThreadTestMocks()

@pytest.fixture
def performance_utils():
    """Performance testing utilities fixture."""
    return ThreadPerformanceTestUtils()

@pytest.fixture
async def mock_db_session():
    """Mock database session fixture."""
    # Mock: Database session isolation for transaction testing without real database dependency
    session = AsyncMock(spec=AsyncSession)
    # Mock: Session isolation for controlled testing without external state
    session.begin = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.commit = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.rollback = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.flush = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.refresh = AsyncMock()
    try:
        yield session
    finally:
        if hasattr(session, "close"):
            await session.close()

@pytest.fixture
async def thread_service():
    """Thread service fixture."""
    yield ThreadService()

@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager fixture."""
    manager_mock = ThreadTestMocks.create_mock_websocket_manager()
    
    # Mock: Component isolation for testing without external dependencies
    with patch('app.ws_manager.manager', manager_mock):
        yield manager_mock

@pytest.fixture
def mock_state_persistence():
    """Mock state persistence service fixture."""
    service_mock = ThreadTestMocks.create_mock_state_persistence()
    
    # Mock: Component isolation for testing without external dependencies
    with patch('netra_backend.app.services.state_persistence.state_persistence_service', service_mock):
        yield service_mock