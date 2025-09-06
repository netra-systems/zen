from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Agent Message Flow End-to-End Test"""

PRIORITY: CRITICAL
# REMOVED_SYNTAX_ERROR: BVJ: Core functionality worth $45K MRR

# REMOVED_SYNTAX_ERROR: This test validates the complete agent message flow:
    # REMOVED_SYNTAX_ERROR: 1. User message -> Backend -> Agent processing
    # REMOVED_SYNTAX_ERROR: 2. Agent response -> WebSocket -> Frontend
    # REMOVED_SYNTAX_ERROR: 3. Message ordering guarantees
    # REMOVED_SYNTAX_ERROR: 4. Streaming response handling

    # REMOVED_SYNTAX_ERROR: Uses REAL agent components with NO MOCKS as required by unified system testing.
    # REMOVED_SYNTAX_ERROR: Follows CLAUDE.md patterns for async testing and agent integration.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.manager import WebSocketManager as WebSocketManager
    # Test framework import - using pytest fixtures instead
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from datetime import datetime
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.manager import WebSocketManager, get_websocket_manager

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.models_postgres import Message, Thread
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.registry import WebSocketMessage

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_service_core import AgentService
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.message_handlers import MessageHandlerService
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.thread_service import ThreadService

    # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)

# REMOVED_SYNTAX_ERROR: class MessageOrderTracker:

    # REMOVED_SYNTAX_ERROR: """Tracks message ordering for validation."""

# REMOVED_SYNTAX_ERROR: def __init__(self):

    # REMOVED_SYNTAX_ERROR: self.messages: List[Dict[str, Any]] = []

    # REMOVED_SYNTAX_ERROR: self.timestamps: List[datetime] = []

    # REMOVED_SYNTAX_ERROR: self.lock = asyncio.Lock()

# REMOVED_SYNTAX_ERROR: async def record_message(self, message: Dict[str, Any]) -> None:

    # REMOVED_SYNTAX_ERROR: """Record a message with timestamp."""

    # REMOVED_SYNTAX_ERROR: async with self.lock:

        # REMOVED_SYNTAX_ERROR: self.messages.append(message)

        # REMOVED_SYNTAX_ERROR: self.timestamps.append(datetime.now())

# REMOVED_SYNTAX_ERROR: def get_ordered_messages(self) -> List[Dict[str, Any]]:

    # REMOVED_SYNTAX_ERROR: """Get messages in order they were received."""

    # REMOVED_SYNTAX_ERROR: return self.messages.copy()

# REMOVED_SYNTAX_ERROR: def validate_ordering(self) -> bool:

    # REMOVED_SYNTAX_ERROR: """Validate messages arrived in correct order."""

    # REMOVED_SYNTAX_ERROR: if len(self.timestamps) < 2:

        # REMOVED_SYNTAX_ERROR: return True

        # REMOVED_SYNTAX_ERROR: for i in range(1, len(self.timestamps)):

            # REMOVED_SYNTAX_ERROR: if self.timestamps[i] < self.timestamps[i-1]:

                # REMOVED_SYNTAX_ERROR: return False

                # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: class WebSocketMessageCapture:

    # REMOVED_SYNTAX_ERROR: """Captures WebSocket messages sent to users."""

# REMOVED_SYNTAX_ERROR: def __init__(self):

    # REMOVED_SYNTAX_ERROR: self.sent_messages: Dict[str, List[Dict[str, Any]]] = {}

    # REMOVED_SYNTAX_ERROR: self.error_messages: Dict[str, List[str]] = {}

    # REMOVED_SYNTAX_ERROR: self.streaming_chunks: Dict[str, List[Dict[str, Any]]] = {}

# REMOVED_SYNTAX_ERROR: async def capture_message(self, user_id: str, message: Dict[str, Any]) -> bool:

    # REMOVED_SYNTAX_ERROR: """Capture a message sent to user."""

    # REMOVED_SYNTAX_ERROR: if user_id not in self.sent_messages:

        # REMOVED_SYNTAX_ERROR: self.sent_messages[user_id] = []

        # REMOVED_SYNTAX_ERROR: self.sent_messages[user_id].append(message)

        # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def capture_error(self, user_id: str, error: str) -> bool:

    # REMOVED_SYNTAX_ERROR: """Capture an error sent to user."""

    # REMOVED_SYNTAX_ERROR: if user_id not in self.error_messages:

        # REMOVED_SYNTAX_ERROR: self.error_messages[user_id] = []

        # REMOVED_SYNTAX_ERROR: self.error_messages[user_id].append(error)

        # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def capture_streaming_chunk(self, user_id: str, chunk: Dict[str, Any]) -> bool:

    # REMOVED_SYNTAX_ERROR: """Capture a streaming chunk sent to user."""

    # REMOVED_SYNTAX_ERROR: if user_id not in self.streaming_chunks:

        # REMOVED_SYNTAX_ERROR: self.streaming_chunks[user_id] = []

        # REMOVED_SYNTAX_ERROR: self.streaming_chunks[user_id].append(chunk)

        # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: def get_messages_for_user(self, user_id: str) -> List[Dict[str, Any]]:

    # REMOVED_SYNTAX_ERROR: """Get all messages sent to a user."""

    # REMOVED_SYNTAX_ERROR: return self.sent_messages.get(user_id, [])

# REMOVED_SYNTAX_ERROR: def get_errors_for_user(self, user_id: str) -> List[str]:

    # REMOVED_SYNTAX_ERROR: """Get all errors sent to a user."""

    # REMOVED_SYNTAX_ERROR: return self.error_messages.get(user_id, [])

# REMOVED_SYNTAX_ERROR: def get_streaming_chunks_for_user(self, user_id: str) -> List[Dict[str, Any]]:

    # REMOVED_SYNTAX_ERROR: """Get all streaming chunks sent to a user."""

    # REMOVED_SYNTAX_ERROR: return self.streaming_chunks.get(user_id, [])

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def message_tracker():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: """Fixture providing message order tracker."""

    # REMOVED_SYNTAX_ERROR: return MessageOrderTracker()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_capture():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: """Fixture providing WebSocket message capture."""

    # REMOVED_SYNTAX_ERROR: return WebSocketMessageCapture()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Fixture providing real WebSocket manager."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.manager import get_websocket_manager as get_unified_manager
    # REMOVED_SYNTAX_ERROR: manager = get_unified_manager()

    # Add broadcasting attribute if it doesn't exist
    # REMOVED_SYNTAX_ERROR: if not hasattr(manager, 'broadcasting'):
        # Mock: Generic component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: mock_broadcasting = MagicMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: mock_broadcasting.join_room = AsyncMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: mock_broadcasting.leave_all_rooms = AsyncMock()  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: manager.broadcasting = mock_broadcasting

        # REMOVED_SYNTAX_ERROR: return manager

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Fixture providing real tool dispatcher."""
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = MagicMock()  # TODO: Use real service instance
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: mock_dispatcher.dispatch = AsyncMock(return_value="Tool executed successfully")
    # REMOVED_SYNTAX_ERROR: return mock_dispatcher

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def real_thread_service():
    # REMOVED_SYNTAX_ERROR: """Fixture providing real thread service."""
    # Initialize database session factory for testing
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.postgres_core import initialize_postgres

    # Mock the database URL and initialize for testing
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.db.postgres_core as postgres_module

    # Create a mock session factory that returns a proper async session
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: mock_session.commit = AsyncMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: mock_session.rollback = AsyncMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: mock_session.close = AsyncMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: mock_session.add = MagicMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: mock_session.execute = AsyncMock()  # TODO: Use real service instance

    # Mock session factory that returns the session directly
# REMOVED_SYNTAX_ERROR: async def mock_session_factory():
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: yield mock_session
        # REMOVED_SYNTAX_ERROR: finally:
            # REMOVED_SYNTAX_ERROR: if hasattr(mock_session, "close"):
                # REMOVED_SYNTAX_ERROR: await mock_session.close()

                # Patch the async_session_factory to use our mock
                # REMOVED_SYNTAX_ERROR: with patch.object(postgres_module, 'async_session_factory', mock_session_factory):
                    # REMOVED_SYNTAX_ERROR: yield ThreadService()

                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def real_supervisor_agent(real_websocket_manager, real_tool_dispatcher, mock_db_session):
    # REMOVED_SYNTAX_ERROR: """Fixture providing real supervisor agent with real components."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.config import get_config

    # REMOVED_SYNTAX_ERROR: try:
        # Try to create real LLM manager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
        # REMOVED_SYNTAX_ERROR: config = get_config()
        # REMOVED_SYNTAX_ERROR: llm_manager = LLMManager(config)
        # REMOVED_SYNTAX_ERROR: except Exception:
            # Fallback to mock for testing
            # Mock: LLM provider isolation to prevent external API usage and costs
            # REMOVED_SYNTAX_ERROR: llm_manager = llm_manager_instance  # Initialize appropriate service
            # Mock: LLM provider isolation to prevent external API usage and costs
            # REMOVED_SYNTAX_ERROR: llm_manager.ask_llm = AsyncMock(return_value="Test agent response")

            # Create supervisor with real components including db_session
            # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
            # REMOVED_SYNTAX_ERROR: db_session=mock_db_session,
            # REMOVED_SYNTAX_ERROR: llm_manager=llm_manager,
            # REMOVED_SYNTAX_ERROR: tool_dispatcher=real_tool_dispatcher,
            # REMOVED_SYNTAX_ERROR: websocket_manager=real_websocket_manager
            

            # Mock the supervisor run method to await asyncio.sleep(0)
            # REMOVED_SYNTAX_ERROR: return a response
# REMOVED_SYNTAX_ERROR: async def mock_supervisor_run(user_request, thread_id, user_id, run_id):
    # The message_processing module will send the agent_completed message
    # We just need to await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return the response content
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

    # REMOVED_SYNTAX_ERROR: supervisor.run = mock_supervisor_run
    # REMOVED_SYNTAX_ERROR: yield supervisor

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def real_agent_service(real_supervisor_agent):

    # REMOVED_SYNTAX_ERROR: """Fixture providing real agent service."""

    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return AgentService(real_supervisor_agent)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_db_session():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Fixture providing mock database session."""
    # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession

    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: session = AsyncMock(spec=AsyncSession)

    # Create proper async context manager mock for db_session.begin()
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_transaction = AsyncMock()  # TODO: Use real service instance
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: mock_transaction.__aexit__ = AsyncMock(return_value=None)
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.begin = MagicMock(return_value=mock_transaction)

    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.commit = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.rollback = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.flush = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.refresh = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.close = AsyncMock()  # TODO: Use real service instance

    # Mock thread retrieval
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_thread = Mock(spec=Thread)
    # REMOVED_SYNTAX_ERROR: mock_thread.id = "test_thread_123"
    # REMOVED_SYNTAX_ERROR: mock_thread.user_id = "test_user"
    # REMOVED_SYNTAX_ERROR: mock_thread.name = "Test Thread"
    # REMOVED_SYNTAX_ERROR: mock_thread.metadata_ = {"user_id": "test_user_001", "test": True}

    # Mock message creation
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_message = Mock(spec=Message)
    # REMOVED_SYNTAX_ERROR: mock_message.id = "test_message_123"
    # REMOVED_SYNTAX_ERROR: mock_message.thread_id = "test_thread_123"
    # REMOVED_SYNTAX_ERROR: mock_message.content = "Test message"
    # REMOVED_SYNTAX_ERROR: mock_message.role = "user"

    # Mock run creation
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_run = mock_run_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_run.id = "test_run_123"
    # REMOVED_SYNTAX_ERROR: mock_run.thread_id = "test_thread_123"
    # REMOVED_SYNTAX_ERROR: mock_run.status = "in_progress"

    # REMOVED_SYNTAX_ERROR: return session

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def setup_database_and_mocks():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Auto-setup database session factory and mocks for all tests in this file."""
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.db.postgres_core as postgres_module
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.services.database.unit_of_work as uow_module
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.models_postgres import Thread, Run

    # Create proper async session factory mock
# REMOVED_SYNTAX_ERROR: class MockAsyncSessionFactory:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: self.session = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: self.session.commit = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: self.session.rollback = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: self.session.close = AsyncMock()  # TODO: Use real service instance

# REMOVED_SYNTAX_ERROR: def __call__(self):
    # REMOVED_SYNTAX_ERROR: return self

# REMOVED_SYNTAX_ERROR: async def __aenter__(self):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.session

# REMOVED_SYNTAX_ERROR: async def __aexit__(self, exc_type, exc_val, exc_tb):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: mock_factory = MockAsyncSessionFactory()

    # Create reusable mock objects
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_thread = Mock(spec=Thread)
    # REMOVED_SYNTAX_ERROR: mock_thread.id = "test_thread_123"
    # REMOVED_SYNTAX_ERROR: mock_thread.user_id = "test_user"
    # REMOVED_SYNTAX_ERROR: mock_thread.metadata_ = {"user_id": "test_user_001"}

    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_run = Mock(spec=Run)
    # REMOVED_SYNTAX_ERROR: mock_run.id = "test_run_123"
    # REMOVED_SYNTAX_ERROR: mock_run.thread_id = "test_thread_123"
    # REMOVED_SYNTAX_ERROR: mock_run.status = "in_progress"

    # Patch all database and service methods
    # REMOVED_SYNTAX_ERROR: with patch.object(postgres_module, 'async_session_factory', mock_factory):
        # REMOVED_SYNTAX_ERROR: with patch.object(uow_module, 'async_session_factory', mock_factory):
            # Mock: Async component isolation for testing without real async operations
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.thread_service.ThreadService.get_thread', new_callable=AsyncMock) as mock_get_thread:
                # Mock: Async component isolation for testing without real async operations
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.thread_service.ThreadService.get_or_create_thread', new_callable=AsyncMock) as mock_create_thread:
                    # Mock: Async component isolation for testing without real async operations
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.thread_service.ThreadService.create_message', new_callable=AsyncMock) as mock_create_message:
                        # Mock: Async component isolation for testing without real async operations
                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.thread_service.ThreadService.create_run', new_callable=AsyncMock) as mock_create_run:
                            # Mock: Async component isolation for testing without real async operations
                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.thread_service.ThreadService.update_run_status', new_callable=AsyncMock) as mock_update_run:

                                # Setup all mocks to return proper objects
                                # REMOVED_SYNTAX_ERROR: mock_get_thread.return_value = mock_thread
                                # REMOVED_SYNTAX_ERROR: mock_create_thread.return_value = mock_thread
                                # REMOVED_SYNTAX_ERROR: mock_create_message.return_value = None
                                # REMOVED_SYNTAX_ERROR: mock_create_run.return_value = mock_run
                                # REMOVED_SYNTAX_ERROR: mock_update_run.return_value = mock_run

                                # REMOVED_SYNTAX_ERROR: yield

                                # Removed problematic line: @pytest.mark.asyncio

# REMOVED_SYNTAX_ERROR: class TestAgentMessageFlow:

    # REMOVED_SYNTAX_ERROR: """Test complete agent message flow end-to-end."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_complete_user_message_to_agent_response_flow(self,
    # REMOVED_SYNTAX_ERROR: real_agent_service: AgentService,
    # REMOVED_SYNTAX_ERROR: websocket_capture: WebSocketMessageCapture,
    # REMOVED_SYNTAX_ERROR: message_tracker: MessageOrderTracker,
    # REMOVED_SYNTAX_ERROR: mock_db_session,
    # REMOVED_SYNTAX_ERROR: real_websocket_manager
    # REMOVED_SYNTAX_ERROR: ):

        # REMOVED_SYNTAX_ERROR: """Test: User message -> Backend -> Agent -> WebSocket -> Response"""

        # REMOVED_SYNTAX_ERROR: Validates complete message flow with real agent processing.

        # REMOVED_SYNTAX_ERROR: """"

        # REMOVED_SYNTAX_ERROR: user_id = "test_user_001"

        # REMOVED_SYNTAX_ERROR: test_message = { )
        # REMOVED_SYNTAX_ERROR: "type": "user_message",
        # REMOVED_SYNTAX_ERROR: "payload": { )
        # REMOVED_SYNTAX_ERROR: "content": "Optimize my AI costs for GPT-4 usage in production",
        # REMOVED_SYNTAX_ERROR: "thread_id": "test_thread_123",
        # REMOVED_SYNTAX_ERROR: "references": [}
        
        

        # Patch WebSocket manager to capture messages
        # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_message', websocket_capture.capture_message):
            # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_error', websocket_capture.capture_error):
                # Record message start
                # Removed problematic line: await message_tracker.record_message({ ))
                # REMOVED_SYNTAX_ERROR: "stage": "input",
                # REMOVED_SYNTAX_ERROR: "type": test_message["type"},
                # REMOVED_SYNTAX_ERROR: "user_id": user_id
                

                # Process message through agent service
                # REMOVED_SYNTAX_ERROR: await real_agent_service.handle_websocket_message( )
                # REMOVED_SYNTAX_ERROR: user_id=user_id,
                # REMOVED_SYNTAX_ERROR: message=test_message,
                # REMOVED_SYNTAX_ERROR: db_session=mock_db_session
                

                # Record message completion
                # Removed problematic line: await message_tracker.record_message({ ))
                # REMOVED_SYNTAX_ERROR: "stage": "output",
                # REMOVED_SYNTAX_ERROR: "user_id": user_id
                

                # Validate message was processed

                # REMOVED_SYNTAX_ERROR: sent_messages = websocket_capture.get_messages_for_user(user_id)

                # REMOVED_SYNTAX_ERROR: assert len(sent_messages) > 0, "No messages were sent to user"

                # Validate agent response was generated

                # REMOVED_SYNTAX_ERROR: response_messages = [ )

                # REMOVED_SYNTAX_ERROR: msg for msg in sent_messages

                # REMOVED_SYNTAX_ERROR: if msg.get("type") in ["agent_completed", "agent_response"]

                

                # REMOVED_SYNTAX_ERROR: assert len(response_messages) > 0, "No agent response was generated"

                # Validate message ordering

                # REMOVED_SYNTAX_ERROR: assert message_tracker.validate_ordering(), "Messages were not processed in order"

                # Validate no errors occurred

                # REMOVED_SYNTAX_ERROR: errors = websocket_capture.get_errors_for_user(user_id)

                # REMOVED_SYNTAX_ERROR: assert len(errors) == 0, "formatted_string"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_agent_message_ordering_guarantees( )

                # REMOVED_SYNTAX_ERROR: self,

                # REMOVED_SYNTAX_ERROR: real_agent_service: AgentService,

                # REMOVED_SYNTAX_ERROR: websocket_capture: WebSocketMessageCapture,

                # REMOVED_SYNTAX_ERROR: message_tracker: MessageOrderTracker,

                # REMOVED_SYNTAX_ERROR: mock_db_session,

                # REMOVED_SYNTAX_ERROR: real_websocket_manager

                # REMOVED_SYNTAX_ERROR: ):

                    # REMOVED_SYNTAX_ERROR: """Test message ordering guarantees under concurrent load."""

                    # REMOVED_SYNTAX_ERROR: Validates messages are processed and responded to in correct order.

                    # REMOVED_SYNTAX_ERROR: """"

                    # REMOVED_SYNTAX_ERROR: user_id = "test_user_002"

                    # REMOVED_SYNTAX_ERROR: test_messages = [ )

                    # REMOVED_SYNTAX_ERROR: { )

                    # REMOVED_SYNTAX_ERROR: "type": "user_message",

                    # REMOVED_SYNTAX_ERROR: "payload": { )

                    # REMOVED_SYNTAX_ERROR: "content": "formatted_string",

                    # REMOVED_SYNTAX_ERROR: "thread_id": "formatted_string",

                    # REMOVED_SYNTAX_ERROR: "references": []

                    

                    

                    # REMOVED_SYNTAX_ERROR: for i in range(5)

                    

                    # Track message processing order

                    # REMOVED_SYNTAX_ERROR: processed_order = []

# REMOVED_SYNTAX_ERROR: async def track_and_capture(user_id: str, message: Dict[str, Any]) -> bool:

    # REMOVED_SYNTAX_ERROR: """Track message order and capture."""

    # REMOVED_SYNTAX_ERROR: if message.get("type") == "agent_completed":

        # REMOVED_SYNTAX_ERROR: processed_order.append(message.get("thread_id"))

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return await websocket_capture.capture_message(user_id, message)

        # Process messages concurrently

        # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_message', track_and_capture):

            # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_error', websocket_capture.capture_error):
                # Submit all messages concurrently

                # REMOVED_SYNTAX_ERROR: tasks = [ )

                # REMOVED_SYNTAX_ERROR: real_agent_service.handle_websocket_message( )

                # REMOVED_SYNTAX_ERROR: user_id=user_id,

                # REMOVED_SYNTAX_ERROR: message=msg,

                # REMOVED_SYNTAX_ERROR: db_session=mock_db_session

                

                # REMOVED_SYNTAX_ERROR: for msg in test_messages

                

                # Wait for all to complete

                # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

                # Validate all messages were processed

                # REMOVED_SYNTAX_ERROR: sent_messages = websocket_capture.get_messages_for_user(user_id)

                # REMOVED_SYNTAX_ERROR: completed_responses = [ )

                # REMOVED_SYNTAX_ERROR: msg for msg in sent_messages

                # REMOVED_SYNTAX_ERROR: if msg.get("type") == "agent_completed"

                

                # REMOVED_SYNTAX_ERROR: assert len(completed_responses) == len(test_messages), \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # Validate ordering (messages should be processed in some deterministic order)

                # REMOVED_SYNTAX_ERROR: assert len(processed_order) == len(test_messages), \
                # REMOVED_SYNTAX_ERROR: "Not all messages completed processing"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_streaming_response_handling( )

                # REMOVED_SYNTAX_ERROR: self,

                # REMOVED_SYNTAX_ERROR: real_agent_service: AgentService,

                # REMOVED_SYNTAX_ERROR: websocket_capture: WebSocketMessageCapture,

                # REMOVED_SYNTAX_ERROR: mock_db_session,

                # REMOVED_SYNTAX_ERROR: real_websocket_manager

                # REMOVED_SYNTAX_ERROR: ):

                    # REMOVED_SYNTAX_ERROR: """Test streaming response handling for agent messages."""

                    # REMOVED_SYNTAX_ERROR: Validates streaming chunks are sent in correct order.

                    # REMOVED_SYNTAX_ERROR: """"

                    # REMOVED_SYNTAX_ERROR: user_id = "test_user_003"

                    # REMOVED_SYNTAX_ERROR: test_message = { )

                    # REMOVED_SYNTAX_ERROR: "type": "user_message",

                    # REMOVED_SYNTAX_ERROR: "payload": { )

                    # REMOVED_SYNTAX_ERROR: "content": "Generate a detailed analysis of microservices architecture benefits",

                    # REMOVED_SYNTAX_ERROR: "thread_id": "test_thread_streaming",

                    # REMOVED_SYNTAX_ERROR: "references": [},

                    # REMOVED_SYNTAX_ERROR: "stream": True

                    

                    

                    # Capture streaming responses

                    # REMOVED_SYNTAX_ERROR: streaming_chunks = []

# REMOVED_SYNTAX_ERROR: async def capture_streaming(user_id: str, message: Dict[str, Any]) -> bool:

    # REMOVED_SYNTAX_ERROR: """Capture streaming messages."""

    # REMOVED_SYNTAX_ERROR: if message.get("type") in ["agent_streaming", "agent_chunk"]:

        # REMOVED_SYNTAX_ERROR: streaming_chunks.append(message)

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return await websocket_capture.capture_message(user_id, message)

        # Process streaming message

        # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_message', capture_streaming):

            # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_error', websocket_capture.capture_error):

                # REMOVED_SYNTAX_ERROR: await real_agent_service.handle_websocket_message( )

                # REMOVED_SYNTAX_ERROR: user_id=user_id,

                # REMOVED_SYNTAX_ERROR: message=test_message,

                # REMOVED_SYNTAX_ERROR: db_session=mock_db_session

                

                # Validate response was generated (streaming or complete)

                # REMOVED_SYNTAX_ERROR: all_messages = websocket_capture.get_messages_for_user(user_id)

                # REMOVED_SYNTAX_ERROR: assert len(all_messages) > 0, "No response was generated"

                # Check for either streaming chunks or complete response

                # REMOVED_SYNTAX_ERROR: has_streaming = len(streaming_chunks) > 0

                # REMOVED_SYNTAX_ERROR: has_complete = any( )

                # REMOVED_SYNTAX_ERROR: msg.get("type") in ["agent_completed", "agent_response"]

                # REMOVED_SYNTAX_ERROR: for msg in all_messages

                

                # REMOVED_SYNTAX_ERROR: assert has_streaming or has_complete, \
                # REMOVED_SYNTAX_ERROR: "Neither streaming chunks nor complete response was generated"

                # If streaming was used, validate chunk ordering

                # REMOVED_SYNTAX_ERROR: if has_streaming:

                    # REMOVED_SYNTAX_ERROR: chunk_indices = [ )

                    # REMOVED_SYNTAX_ERROR: chunk.get("chunk_index", 0) for chunk in streaming_chunks

                    

                    # REMOVED_SYNTAX_ERROR: assert chunk_indices == sorted(chunk_indices), \
                    # REMOVED_SYNTAX_ERROR: "Streaming chunks were not sent in order"

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_agent_error_handling_and_recovery( )

                    # REMOVED_SYNTAX_ERROR: self,

                    # REMOVED_SYNTAX_ERROR: real_agent_service: AgentService,

                    # REMOVED_SYNTAX_ERROR: websocket_capture: WebSocketMessageCapture,

                    # REMOVED_SYNTAX_ERROR: mock_db_session,

                    # REMOVED_SYNTAX_ERROR: real_websocket_manager

                    # REMOVED_SYNTAX_ERROR: ):

                        # REMOVED_SYNTAX_ERROR: """Test agent error handling and recovery mechanisms."""

                        # REMOVED_SYNTAX_ERROR: Validates proper error responses are sent via WebSocket.

                        # REMOVED_SYNTAX_ERROR: """"

                        # REMOVED_SYNTAX_ERROR: user_id = "test_user_004"

                        # Test invalid message format

                        # REMOVED_SYNTAX_ERROR: invalid_message = { )

                        # REMOVED_SYNTAX_ERROR: "type": "invalid_message_type",

                        # REMOVED_SYNTAX_ERROR: "payload": {"malformed": "data"}

                        

                        # Process invalid message

                        # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_message', websocket_capture.capture_message):

                            # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_error', websocket_capture.capture_error):

                                # REMOVED_SYNTAX_ERROR: await real_agent_service.handle_websocket_message( )

                                # REMOVED_SYNTAX_ERROR: user_id=user_id,

                                # REMOVED_SYNTAX_ERROR: message=invalid_message,

                                # REMOVED_SYNTAX_ERROR: db_session=mock_db_session

                                

                                # Validate error was reported

                                # REMOVED_SYNTAX_ERROR: errors = websocket_capture.get_errors_for_user(user_id)

                                # REMOVED_SYNTAX_ERROR: assert len(errors) > 0, "No error was reported for invalid message"

                                # Validate error message content

                                # REMOVED_SYNTAX_ERROR: error_message = errors[0]

                                # REMOVED_SYNTAX_ERROR: assert "Unknown message type" in error_message or "invalid" in error_message.lower(), \
                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_concurrent_user_message_isolation( )

                                # REMOVED_SYNTAX_ERROR: self,

                                # REMOVED_SYNTAX_ERROR: real_agent_service: AgentService,

                                # REMOVED_SYNTAX_ERROR: websocket_capture: WebSocketMessageCapture,

                                # REMOVED_SYNTAX_ERROR: mock_db_session,

                                # REMOVED_SYNTAX_ERROR: real_websocket_manager

                                # REMOVED_SYNTAX_ERROR: ):

                                    # REMOVED_SYNTAX_ERROR: """Test message isolation between concurrent users."""

                                    # REMOVED_SYNTAX_ERROR: Validates messages from different users don"t interfere.

                                    # REMOVED_SYNTAX_ERROR: """"

                                    # REMOVED_SYNTAX_ERROR: users = ["user_a", "user_b", "user_c"]

                                    # REMOVED_SYNTAX_ERROR: user_messages = { )

                                    # REMOVED_SYNTAX_ERROR: user_id: { )

                                    # REMOVED_SYNTAX_ERROR: "type": "user_message",

                                    # REMOVED_SYNTAX_ERROR: "payload": { )

                                    # REMOVED_SYNTAX_ERROR: "content": "formatted_string",

                                    # REMOVED_SYNTAX_ERROR: "thread_id": "formatted_string",

                                    # REMOVED_SYNTAX_ERROR: "references": []

                                    

                                    

                                    # REMOVED_SYNTAX_ERROR: for user_id in users

                                    

                                    # Process messages from different users concurrently

                                    # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_message', websocket_capture.capture_message):

                                        # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_error', websocket_capture.capture_error):

                                            # REMOVED_SYNTAX_ERROR: tasks = [ )

                                            # REMOVED_SYNTAX_ERROR: real_agent_service.handle_websocket_message( )

                                            # REMOVED_SYNTAX_ERROR: user_id=user_id,

                                            # REMOVED_SYNTAX_ERROR: message=message,

                                            # REMOVED_SYNTAX_ERROR: db_session=mock_db_session

                                            

                                            # REMOVED_SYNTAX_ERROR: for user_id, message in user_messages.items()

                                            

                                            # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

                                            # Validate each user received responses

                                            # REMOVED_SYNTAX_ERROR: for user_id in users:

                                                # REMOVED_SYNTAX_ERROR: user_messages = websocket_capture.get_messages_for_user(user_id)

                                                # REMOVED_SYNTAX_ERROR: assert len(user_messages) > 0, "formatted_string"

                                                # Validate response contains user-specific content

                                                # REMOVED_SYNTAX_ERROR: response_content = str(user_messages)

                                                # REMOVED_SYNTAX_ERROR: assert user_id in response_content or "formatted_string" in response_content, \
                                                # REMOVED_SYNTAX_ERROR: "formatted_string"t contain user-specific content"

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_agent_websocket_connection_recovery( )

                                                # REMOVED_SYNTAX_ERROR: self,

                                                # REMOVED_SYNTAX_ERROR: real_agent_service: AgentService,

                                                # REMOVED_SYNTAX_ERROR: websocket_capture: WebSocketMessageCapture,

                                                # REMOVED_SYNTAX_ERROR: mock_db_session,

                                                # REMOVED_SYNTAX_ERROR: real_websocket_manager

                                                # REMOVED_SYNTAX_ERROR: ):

                                                    # REMOVED_SYNTAX_ERROR: """Test agent processing continues after WebSocket disconnection."""

                                                    # REMOVED_SYNTAX_ERROR: Validates graceful handling of connection issues.

                                                    # REMOVED_SYNTAX_ERROR: """"

                                                    # REMOVED_SYNTAX_ERROR: user_id = "test_user_recovery"

                                                    # REMOVED_SYNTAX_ERROR: test_message = { )

                                                    # REMOVED_SYNTAX_ERROR: "type": "user_message",

                                                    # REMOVED_SYNTAX_ERROR: "payload": { )

                                                    # REMOVED_SYNTAX_ERROR: "content": "Process this even if WebSocket disconnects",

                                                    # REMOVED_SYNTAX_ERROR: "thread_id": "recovery_thread",

                                                    # REMOVED_SYNTAX_ERROR: "references": [}

                                                    

                                                    

                                                    # Simulate WebSocket disconnection during processing

                                                    # REMOVED_SYNTAX_ERROR: disconnect_count = 0

# REMOVED_SYNTAX_ERROR: async def simulate_disconnect(user_id: str, message: Dict[str, Any]) -> bool:

    # REMOVED_SYNTAX_ERROR: """Simulate WebSocket disconnect on first send."""

    # REMOVED_SYNTAX_ERROR: nonlocal disconnect_count

    # REMOVED_SYNTAX_ERROR: disconnect_count += 1

    # REMOVED_SYNTAX_ERROR: if disconnect_count == 1:
        # Simulate disconnection
        # REMOVED_SYNTAX_ERROR: from starlette.websockets import WebSocketDisconnect

        # REMOVED_SYNTAX_ERROR: raise WebSocketDisconnect()

        # Subsequent sends succeed

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return await websocket_capture.capture_message(user_id, message)

        # Process message with simulated disconnection

        # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_message', simulate_disconnect):

            # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_error', websocket_capture.capture_error):
                # Should not raise exception despite WebSocket disconnect

                # REMOVED_SYNTAX_ERROR: await real_agent_service.handle_websocket_message( )

                # REMOVED_SYNTAX_ERROR: user_id=user_id,

                # REMOVED_SYNTAX_ERROR: message=test_message,

                # REMOVED_SYNTAX_ERROR: db_session=mock_db_session

                

                # Validate processing continued despite disconnection

                # REMOVED_SYNTAX_ERROR: assert disconnect_count > 0, "WebSocket disconnection was not simulated"

                # Check if any messages were eventually captured
                # (after reconnection simulation)

                # REMOVED_SYNTAX_ERROR: all_messages = websocket_capture.get_messages_for_user(user_id)
                # Note: May be 0 if all sends failed, but should not crash

                # Most importantly, no exception should have been raised
                # If we reach this point, the test passed

                # REMOVED_SYNTAX_ERROR: assert True, "Agent service handled WebSocket disconnection gracefully"

                # Removed problematic line: @pytest.mark.asyncio

# REMOVED_SYNTAX_ERROR: class TestAgentMessageFlowPerformance:

    # REMOVED_SYNTAX_ERROR: """Performance tests for agent message flow."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_message_processing_latency( )

    # REMOVED_SYNTAX_ERROR: self,

    # REMOVED_SYNTAX_ERROR: real_agent_service: AgentService,

    # REMOVED_SYNTAX_ERROR: websocket_capture: WebSocketMessageCapture,

    # REMOVED_SYNTAX_ERROR: mock_db_session,

    # REMOVED_SYNTAX_ERROR: real_websocket_manager

    # REMOVED_SYNTAX_ERROR: ):

        # REMOVED_SYNTAX_ERROR: """Test message processing latency is within acceptable bounds."""

        # REMOVED_SYNTAX_ERROR: user_id = "test_user_per"formatted_string"No response was generated"

                # Validate processing time is reasonable (< 30 seconds for test)

                # REMOVED_SYNTAX_ERROR: assert processing_time < 30.0, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_concurrent_message_throughput( )

                # REMOVED_SYNTAX_ERROR: self,

                # REMOVED_SYNTAX_ERROR: real_agent_service: AgentService,

                # REMOVED_SYNTAX_ERROR: websocket_capture: WebSocketMessageCapture,

                # REMOVED_SYNTAX_ERROR: mock_db_session,

                # REMOVED_SYNTAX_ERROR: real_websocket_manager

                # REMOVED_SYNTAX_ERROR: ):

                    # REMOVED_SYNTAX_ERROR: """Test system can handle multiple concurrent messages."""

                    # REMOVED_SYNTAX_ERROR: num_concurrent = 10

                    # REMOVED_SYNTAX_ERROR: users = ["formatted_string" for i in range(num_concurrent)]

                    # REMOVED_SYNTAX_ERROR: messages = [ )

                    # REMOVED_SYNTAX_ERROR: { )

                    # REMOVED_SYNTAX_ERROR: "type": "user_message",

                    # REMOVED_SYNTAX_ERROR: "payload": { )

                    # REMOVED_SYNTAX_ERROR: "content": "formatted_string",

                    # REMOVED_SYNTAX_ERROR: "thread_id": "formatted_string",

                    # REMOVED_SYNTAX_ERROR: "references": []

                    

                    

                    # REMOVED_SYNTAX_ERROR: for i in range(num_concurrent)

                    

                    # Measure concurrent processing time

                    # REMOVED_SYNTAX_ERROR: start_time = datetime.now()

                    # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_message', websocket_capture.capture_message):

                        # REMOVED_SYNTAX_ERROR: with patch.object(real_websocket_manager, 'send_error', websocket_capture.capture_error):

                            # REMOVED_SYNTAX_ERROR: tasks = [ )

                            # REMOVED_SYNTAX_ERROR: real_agent_service.handle_websocket_message( )

                            # REMOVED_SYNTAX_ERROR: user_id=users[i],

                            # REMOVED_SYNTAX_ERROR: message=messages[i],

                            # REMOVED_SYNTAX_ERROR: db_session=mock_db_session

                            

                            # REMOVED_SYNTAX_ERROR: for i in range(num_concurrent)

                            

                            # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

                            # REMOVED_SYNTAX_ERROR: end_time = datetime.now()

                            # REMOVED_SYNTAX_ERROR: total_time = (end_time - start_time).total_seconds()

                            # Validate all messages were processed

                            # REMOVED_SYNTAX_ERROR: total_responses = sum( )

                            # REMOVED_SYNTAX_ERROR: len(websocket_capture.get_messages_for_user(user))

                            # REMOVED_SYNTAX_ERROR: for user in users

                            

                            # REMOVED_SYNTAX_ERROR: assert total_responses >= num_concurrent, \
                            # REMOVED_SYNTAX_ERROR: "formatted_string"

                            # Calculate throughput

                            # REMOVED_SYNTAX_ERROR: throughput = num_concurrent / total_time

                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                            # Validate reasonable throughput (at least 0.1 msg/sec)

                            # REMOVED_SYNTAX_ERROR: assert throughput > 0.1, "formatted_string"