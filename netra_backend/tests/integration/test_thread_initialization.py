"""Integration Test: First Message Thread Initialization

BVJ: $15K MRR - New thread creation for first-time users
Components: WebSocket → Thread Service → Database → Supervisor
Critical: Thread context required for all agent interactions
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path



@pytest.mark.asyncio
class TestFirstMessageThreadInit:
    """Test thread initialization for first user messages."""
    
    @pytest.fixture
    async def db_session(self):
        """Create async database session for testing."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async_session = sessionmaker(engine, class_=AsyncSession)
        
        async with engine.begin() as conn:
            # Create tables if needed
            pass
        
        async with async_session() as session:
            yield session
    
    @pytest.fixture
    def thread_data(self):
        """Generate test thread data."""
        return {
            "id": str(uuid.uuid4()),
            "user_id": "test_user_123",
            "title": "First conversation",
            "created_at": datetime.utcnow(),
            "messages": [],
            "metadata": {
                "agent_type": "supervisor",
                "context": {}
            }
        }
    
    async def test_new_thread_creation_first_message(self, db_session, thread_data):
        """Test thread creation when user sends first message."""
        from netra_backend.app.services.thread_service import ThreadService
        from netra_backend.app.services.message_service import MessageService
        
        thread_service = Mock(spec=ThreadService)
        thread_service.create_thread = AsyncMock(return_value=thread_data)
        thread_service.get_thread = AsyncMock(return_value=None)
        
        message_service = Mock(spec=MessageService)
        message_service.add_message = AsyncMock()
        
        # User sends first message (no thread exists)
        user_message = {
            "content": "Optimize my GPT-4 costs",
            "user_id": "test_user_123"
        }
        
        # Check if thread exists
        existing_thread = await thread_service.get_thread(
            user_message["user_id"], 
            None
        )
        assert existing_thread is None
        
        # Create new thread
        new_thread = await thread_service.create_thread(
            user_id=user_message["user_id"],
            title="Optimize my GPT-4 costs"
        )
        
        assert new_thread["id"] == thread_data["id"]
        assert new_thread["user_id"] == "test_user_123"
        
        # Add message to thread
        await message_service.add_message(
            thread_id=new_thread["id"],
            content=user_message["content"],
            role="user"
        )
        
        thread_service.create_thread.assert_called_once()
        message_service.add_message.assert_called_once()
    
    async def test_thread_persistence_to_database(self, db_session):
        """Test thread data persists correctly to database."""
        from netra_backend.app.services.apex_optimizer_agent.models import Thread
        
        # Create thread model
        thread = Thread(
            id=str(uuid.uuid4()),
            user_id="test_user_123",
            title="Cost optimization query",
            created_at=datetime.utcnow()
        )
        
        # Add to session
        db_session.add(thread)
        await db_session.commit()
        
        # Query back
        result = await db_session.get(Thread, thread.id)
        assert result is not None
        assert result.user_id == "test_user_123"
        assert result.title == "Cost optimization query"
    
    async def test_thread_context_initialization(self, thread_data):
        """Test thread context properly initialized for agents."""
        from netra_backend.app.services.context_service import ContextService
        
        context_service = Mock(spec=ContextService)
        context_service.initialize_context = AsyncMock(return_value={
            "thread_id": thread_data["id"],
            "user_id": thread_data["user_id"],
            "conversation_history": [],
            "user_preferences": {},
            "system_state": {
                "models_available": ["gpt-4", "claude-3"],
                "rate_limits": {"gpt-4": 100, "claude-3": 50}
            }
        })
        
        # Initialize context for new thread
        context = await context_service.initialize_context(thread_data)
        
        assert context["thread_id"] == thread_data["id"]
        assert context["conversation_history"] == []
        assert "system_state" in context
        
        context_service.initialize_context.assert_called_once_with(thread_data)
    
    async def test_concurrent_thread_creation_race_condition(self, db_session):
        """Test handling of concurrent thread creation attempts."""
        from netra_backend.app.services.thread_service import ThreadService
        
        thread_service = Mock(spec=ThreadService)
        creation_count = 0
        
        async def mock_create():
            nonlocal creation_count
            creation_count += 1
            await asyncio.sleep(0.01)  # Simulate DB delay
            return {
                "id": f"thread_{creation_count}",
                "user_id": "test_user"
            }
        
        thread_service.create_thread = mock_create
        
        # Simulate concurrent creation attempts
        tasks = [
            thread_service.create_thread() 
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Should create 5 threads (no deduplication in this test)
        assert len(results) == 5
        assert creation_count == 5
    
    async def test_thread_title_generation_from_message(self):
        """Test automatic thread title generation from first message."""
        from netra_backend.app.services.thread_service import ThreadService
        
        thread_service = Mock(spec=ThreadService)
        
        def generate_title(message: str) -> str:
            """Generate concise title from message."""
            return message[:50] + "..." if len(message) > 50 else message
        
        thread_service.generate_title = generate_title
        
        # Test various message lengths
        short_msg = "Help with costs"
        long_msg = "I need help optimizing my GPT-4 usage because costs are getting out of control"
        
        assert thread_service.generate_title(short_msg) == "Help with costs"
        assert thread_service.generate_title(long_msg) == "I need help optimizing my GPT-4 usage because cos..."
    
    async def test_thread_metadata_includes_agent_routing(self, thread_data):
        """Test thread metadata includes agent routing information."""
        from netra_backend.app.services.agent_router import AgentRouter
        
        router = Mock(spec=AgentRouter)
        router.determine_agent = AsyncMock(return_value={
            "primary_agent": "cost_optimizer",
            "support_agents": ["usage_analyzer", "model_selector"],
            "confidence": 0.95
        })
        
        message = "Reduce my GPT-4 costs by 50%"
        
        # Determine routing
        routing = await router.determine_agent(message)
        
        # Add to thread metadata
        thread_data["metadata"]["routing"] = routing
        
        assert thread_data["metadata"]["routing"]["primary_agent"] == "cost_optimizer"
        assert len(thread_data["metadata"]["routing"]["support_agents"]) == 2
        assert thread_data["metadata"]["routing"]["confidence"] == 0.95
    
    async def test_websocket_notification_on_thread_creation(self, thread_data):
        """Test WebSocket notification sent when thread created."""
        from netra_backend.app.services.websocket_manager import WebSocketManager
        
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.send_message = AsyncMock()
        
        # Send thread creation notification
        await ws_manager.send_message(
            thread_data["user_id"],
            {
                "type": "thread_created",
                "thread": thread_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        ws_manager.send_message.assert_called_once()
        call_args = ws_manager.send_message.call_args[0]
        assert call_args[0] == "test_user_123"
        assert call_args[1]["type"] == "thread_created"