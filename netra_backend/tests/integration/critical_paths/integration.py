"""
Integration Test Utilities: Common utilities for integration testing.

This module provides utilities and helpers specifically for integration tests,
including service mocking, data setup, and test orchestration.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Quality Assurance)
- Business Goal: Reduce integration test complexity, improve maintainability  
- Value Impact: Consistent test patterns reduce debugging time by 60%
- Revenue Impact: Faster testing cycles enable more frequent releases
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, AsyncGenerator
from unittest.mock import MagicMock, patch, AsyncMock

from netra_backend.app.core.config import get_settings
from netra_backend.app.schemas.registry import User, Message, Thread, AgentState


class IntegrationTestContext:
    """Context manager for integration test setup and teardown."""
    
    def __init__(self):
        self.patches: List[Any] = []
        self.mocks: Dict[str, MagicMock] = {}
        self.cleanup_functions: List[callable] = []
    
    def __enter__(self):
        """Enter integration test context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit integration test context and cleanup."""
        self.cleanup()
    
    def add_patch(self, target: str, **kwargs) -> MagicMock:
        """Add a patch to the context."""
        patcher = patch(target, **kwargs)
        mock = patcher.start()
        self.patches.append(patcher)
        self.mocks[target] = mock
        return mock
    
    def add_async_patch(self, target: str, **kwargs) -> AsyncMock:
        """Add an async patch to the context."""
        patcher = patch(target, **kwargs)
        mock = AsyncMock()
        patcher.return_value = mock
        patcher.start()
        self.patches.append(patcher)
        self.mocks[target] = mock
        return mock
    
    def add_cleanup(self, cleanup_func: callable) -> None:
        """Add cleanup function to be called on exit."""
        self.cleanup_functions.append(cleanup_func)
    
    def cleanup(self) -> None:
        """Cleanup all patches and run cleanup functions."""
        # Stop all patches
        for patcher in reversed(self.patches):
            try:
                patcher.stop()
            except RuntimeError:
                # Already stopped
                pass
        
        # Run cleanup functions
        for cleanup_func in reversed(self.cleanup_functions):
            try:
                cleanup_func()
            except Exception:
                # Continue cleanup even if one fails
                pass
        
        self.patches.clear()
        self.mocks.clear()
        self.cleanup_functions.clear()
    
    def get_mock(self, target: str) -> Optional[MagicMock]:
        """Get mock by target name."""
        return self.mocks.get(target)


class ServiceMockBuilder:
    """Builder for creating service mocks in integration tests."""
    
    def __init__(self, context: IntegrationTestContext):
        self.context = context
        self._service_mocks: Dict[str, MagicMock] = {}
    
    def mock_user_service(self, users: Optional[List[User]] = None) -> MagicMock:
        """Mock user service with optional user data."""
        users = users or [User(
            id="test_user_123",
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )]
        
        mock_service = self.context.add_patch('netra_backend.app.services.user_service.UserService')
        mock_service.get_user.return_value = users[0] if users else None
        mock_service.get_users.return_value = users
        mock_service.create_user.return_value = users[0] if users else None
        
        self._service_mocks['user_service'] = mock_service
        return mock_service
    
    def mock_thread_service(self, threads: Optional[List[Thread]] = None) -> MagicMock:
        """Mock thread service with optional thread data."""
        threads = threads or [Thread(
            id="test_thread_123",
            user_id="test_user_123", 
            title="Test Thread"
        )]
        
        mock_service = self.context.add_patch('netra_backend.app.services.thread_service.ThreadService')
        mock_service.get_thread.return_value = threads[0] if threads else None
        mock_service.get_threads.return_value = threads
        mock_service.create_thread.return_value = threads[0] if threads else None
        
        self._service_mocks['thread_service'] = mock_service
        return mock_service
    
    def mock_agent_service(self, agent_states: Optional[List[AgentState]] = None) -> MagicMock:
        """Mock agent service with optional agent data."""
        agent_states = agent_states or [AgentState(
            agent_id="test_agent_123",
            status="running",
            thread_id="test_thread_123"
        )]
        
        mock_service = self.context.add_async_patch('netra_backend.app.services.agent_service.AgentService')
        mock_service.start_agent.return_value = agent_states[0] if agent_states else None
        mock_service.get_agent_state.return_value = agent_states[0] if agent_states else None
        mock_service.stop_agent.return_value = True
        
        self._service_mocks['agent_service'] = mock_service
        return mock_service
    
    def mock_websocket_manager(self, connected_users: Optional[List[str]] = None) -> MagicMock:
        """Mock WebSocket manager with optional connection data."""
        connected_users = connected_users or ["test_user_123"]
        
        mock_manager = self.context.add_patch('netra_backend.app.services.websocket_manager.WebSocketManager')
        mock_manager.is_connected.return_value = True
        mock_manager.get_connected_users.return_value = connected_users
        mock_manager.send_message.return_value = True
        mock_manager.broadcast.return_value = {"successful": len(connected_users), "failed": 0}
        
        self._service_mocks['websocket_manager'] = mock_manager
        return mock_manager
    
    def mock_database_session(self) -> MagicMock:
        """Mock database session for database operations."""
        mock_session = MagicMock()
        mock_get_db = self.context.add_patch('netra_backend.app.db.postgres.get_db')
        mock_get_db.return_value = mock_session
        
        self._service_mocks['database_session'] = mock_session
        return mock_session
    
    def get_service_mock(self, service_name: str) -> Optional[MagicMock]:
        """Get service mock by name."""
        return self._service_mocks.get(service_name)


class TestDataBuilder:
    """Builder for creating test data objects."""
    
    @staticmethod
    def create_user(user_id: str = "test_user_123", **kwargs) -> User:
        """Create a test user with default or custom attributes."""
        defaults = {
            "id": user_id,
            "email": f"{user_id}@example.com",
            "full_name": f"Test User {user_id}",
            "is_active": True
        }
        defaults.update(kwargs)
        return User(**defaults)
    
    @staticmethod
    def create_thread(thread_id: str = "test_thread_123", user_id: str = "test_user_123", **kwargs) -> Thread:
        """Create a test thread with default or custom attributes."""
        defaults = {
            "id": thread_id,
            "user_id": user_id,
            "title": f"Test Thread {thread_id}"
        }
        defaults.update(kwargs)
        return Thread(**defaults)
    
    @staticmethod
    def create_message(message_id: str = "test_message_123", thread_id: str = "test_thread_123", **kwargs) -> Message:
        """Create a test message with default or custom attributes."""
        defaults = {
            "id": message_id,
            "thread_id": thread_id,
            "role": "user",
            "content": f"Test message {message_id}"
        }
        defaults.update(kwargs)
        return Message(**defaults)
    
    @staticmethod
    def create_agent_state(agent_id: str = "test_agent_123", thread_id: str = "test_thread_123", **kwargs) -> AgentState:
        """Create a test agent state with default or custom attributes."""
        defaults = {
            "agent_id": agent_id,
            "status": "running",
            "thread_id": thread_id
        }
        defaults.update(kwargs)
        return AgentState(**defaults)
    
    @classmethod
    def create_full_conversation(cls, user_count: int = 1, thread_count: int = 1, message_count: int = 3) -> Dict[str, List]:
        """Create a full conversation with users, threads, and messages."""
        users = [cls.create_user(f"user_{i}") for i in range(user_count)]
        threads = []
        messages = []
        
        for user in users:
            user_threads = [cls.create_thread(f"thread_{user.id}_{i}", user.id) for i in range(thread_count)]
            threads.extend(user_threads)
            
            for thread in user_threads:
                thread_messages = [
                    cls.create_message(f"msg_{thread.id}_{i}", thread.id, 
                                     role="user" if i % 2 == 0 else "assistant",
                                     content=f"Message {i} in {thread.id}")
                    for i in range(message_count)
                ]
                messages.extend(thread_messages)
        
        return {
            "users": users,
            "threads": threads, 
            "messages": messages
        }


@asynccontextmanager
async def integration_test_setup(enable_real_services: bool = False) -> AsyncGenerator[IntegrationTestContext, None]:
    """Async context manager for integration test setup."""
    context = IntegrationTestContext()
    
    try:
        # Setup common mocks unless real services are enabled
        if not enable_real_services:
            service_builder = ServiceMockBuilder(context)
            service_builder.mock_database_session()
            service_builder.mock_user_service()
            service_builder.mock_thread_service()
            service_builder.mock_websocket_manager()
        
        yield context
    finally:
        context.cleanup()


def run_integration_test(test_func, *args, **kwargs):
    """Run an integration test function with proper setup."""
    if asyncio.iscoroutinefunction(test_func):
        return asyncio.run(test_func(*args, **kwargs))
    else:
        return test_func(*args, **kwargs)


class IntegrationTestScenario:
    """Predefined integration test scenarios."""
    
    @staticmethod
    def user_creates_thread_and_sends_message():
        """Scenario: User creates thread and sends message."""
        user = TestDataBuilder.create_user()
        thread = TestDataBuilder.create_thread(user_id=user.id)
        message = TestDataBuilder.create_message(thread_id=thread.id)
        
        return {
            "user": user,
            "thread": thread,
            "message": message,
            "expected_flow": [
                "authenticate_user",
                "create_thread",
                "send_message",
                "notify_via_websocket"
            ]
        }
    
    @staticmethod
    def agent_processes_user_message():
        """Scenario: Agent processes user message and responds."""
        user = TestDataBuilder.create_user()
        thread = TestDataBuilder.create_thread(user_id=user.id)
        user_message = TestDataBuilder.create_message(thread_id=thread.id, role="user")
        agent_state = TestDataBuilder.create_agent_state(thread_id=thread.id)
        
        return {
            "user": user,
            "thread": thread,
            "user_message": user_message,
            "agent_state": agent_state,
            "expected_flow": [
                "receive_user_message",
                "start_agent",
                "process_message",
                "generate_response",
                "send_agent_response",
                "update_agent_state"
            ]
        }
    
    @staticmethod
    def multi_user_thread_collaboration():
        """Scenario: Multiple users collaborating in threads."""
        conversation_data = TestDataBuilder.create_full_conversation(
            user_count=3, thread_count=2, message_count=5
        )
        
        return {
            **conversation_data,
            "expected_flow": [
                "authenticate_multiple_users",
                "create_shared_threads", 
                "exchange_messages",
                "broadcast_updates",
                "maintain_message_order"
            ]
        }


# Export commonly used components
__all__ = [
    "IntegrationTestContext",
    "ServiceMockBuilder", 
    "TestDataBuilder",
    "integration_test_setup",
    "run_integration_test",
    "IntegrationTestScenario"
]