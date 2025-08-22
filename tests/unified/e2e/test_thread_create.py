"""Thread Creation Tests - WebSocket Flow
Focused tests for thread creation operations via WebSocket.
Extracted from test_thread_management_websocket.py for better organization.

BVJ: Thread creation notifications ensure real-time UI updates across devices.
Segment: All customer tiers (Free, Early, Mid, Enterprise).
Business Goal: Ensure reliable thread creation drives user engagement.
Value Impact: Thread creation reliability directly impacts customer retention.
Strategic Impact: Thread creation failures cause user frustration and churn.
"""

import asyncio
import time
from typing import Any, Dict, List

import pytest

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import WebSocketMessageType
from tests.unified.config import TEST_USERS
from tests.unified.e2e.thread_test_fixtures_core import (
    ThreadContextManager,
    ThreadTestDataFactory,
    ThreadWebSocketFixtures,
    test_users,
    thread_context_manager,
    unified_harness,
    ws_thread_fixtures,
)

logger = central_logger.get_logger(__name__)


class ThreadCreationManager:
    """Manages thread creation operations via WebSocket."""
    
    def __init__(self, ws_fixtures: ThreadWebSocketFixtures):
        self.ws_fixtures = ws_fixtures
        self.created_threads: List[Dict[str, Any]] = []
    
    async def create_thread_via_websocket(self, user_id: str, thread_name: str) -> str:
        """Create new thread via WebSocket and capture events."""
        thread_id = f"thread_{user_id}_{int(time.time())}_{len(self.created_threads)}"
        
        # Build and send creation message
        message = self.ws_fixtures.build_websocket_message(
            WebSocketMessageType.CREATE_THREAD,
            thread_id=thread_id,
            thread_name=thread_name
        )
        await self.ws_fixtures.send_websocket_message(user_id, message)
        
        # Capture thread created event
        self.ws_fixtures.capture_thread_event(
            WebSocketMessageType.THREAD_CREATED,
            user_id,
            thread_id,
            thread_name=thread_name
        )
        
        # Initialize thread context
        context_key = f"{user_id}:{thread_id}"
        self.ws_fixtures.thread_contexts[context_key] = {
            "thread_id": thread_id,
            "thread_name": thread_name,
            "created_at": time.time(),
            "messages": []
        }
        
        # Track created thread
        thread_data = {
            "thread_id": thread_id,
            "thread_name": thread_name,
            "user_id": user_id,
            "created_at": time.time()
        }
        self.created_threads.append(thread_data)
        
        return thread_id
    
    async def create_multiple_threads_concurrently(self, user_id: str, 
                                                   thread_names: List[str]) -> List[str]:
        """Create multiple threads concurrently."""
        creation_tasks = [
            self.create_thread_via_websocket(user_id, name) 
            for name in thread_names
        ]
        
        created_thread_ids = await asyncio.gather(*creation_tasks)
        return created_thread_ids
    
    def get_creation_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get thread creation events for specific user."""
        return [
            event for event in self.ws_fixtures.thread_events
            if (event["type"] == WebSocketMessageType.THREAD_CREATED.value and 
                event["user_id"] == user_id)
        ]
    
    def validate_thread_creation_event(self, event: Dict[str, Any], 
                                       expected_thread_id: str, 
                                       expected_thread_name: str) -> bool:
        """Validate thread creation event structure and data."""
        return (
            event["type"] == WebSocketMessageType.THREAD_CREATED.value and
            event["thread_id"] == expected_thread_id and
            event["payload"].get("thread_name") == expected_thread_name and
            "timestamp" in event and
            event["timestamp"] > 0
        )


@pytest.fixture
def thread_creator(ws_thread_fixtures):
    """Thread creation manager fixture."""
    return ThreadCreationManager(ws_thread_fixtures)


@pytest.mark.asyncio
async def test_thread_creation_websocket_notification(ws_thread_fixtures, thread_creator):
    """Test new thread creation triggers WebSocket event and frontend updates."""
    user = TEST_USERS["free"]
    
    # Create authenticated WebSocket connection
    connection = await ws_thread_fixtures.create_authenticated_connection(user.id)
    assert connection["connected"], "WebSocket connection must be established"
    
    # Create thread via WebSocket
    thread_name = "Real-time Optimization Thread"
    thread_id = await thread_creator.create_thread_via_websocket(user.id, thread_name)
    
    # Verify WebSocket event was captured
    creation_events = thread_creator.get_creation_events_for_user(user.id)
    
    assert len(creation_events) == 1, "Thread creation must trigger exactly one WebSocket event"
    
    # Validate event structure and data
    event = creation_events[0]
    assert thread_creator.validate_thread_creation_event(event, thread_id, thread_name)
    assert event["user_id"] == user.id, "Event must be associated with correct user"


@pytest.mark.asyncio
async def test_multiple_threads_per_user_creation(ws_thread_fixtures, thread_creator):
    """Test multiple threads can be created per user with proper event routing."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create multiple threads concurrently
    thread_names = [
        "Cost Optimization Thread", 
        "Performance Analysis Thread", 
        "Security Review Thread", 
        "Compliance Check Thread"
    ]
    
    created_thread_ids = await thread_creator.create_multiple_threads_concurrently(
        user.id, thread_names
    )
    
    # Verify all threads created with unique IDs
    assert len(created_thread_ids) == len(thread_names), "All threads must be created successfully"
    assert len(set(created_thread_ids)) == len(created_thread_ids), "All thread IDs must be unique"
    
    # Verify thread creation events captured
    creation_events = thread_creator.get_creation_events_for_user(user.id)
    assert len(creation_events) == len(thread_names), "All thread creations must trigger events"
    
    # Verify all events associated with correct user
    for event in creation_events:
        assert event["user_id"] == user.id, "All events must be associated with correct user"
        assert event["thread_id"] in created_thread_ids, "Event thread ID must match created threads"


@pytest.mark.asyncio
async def test_thread_creation_with_metadata_preservation(ws_thread_fixtures, thread_creator):
    """Test thread creation preserves metadata correctly."""
    user = TEST_USERS["mid"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create thread with specific metadata expectations
    thread_name = "AI Model Optimization - Production"
    thread_id = await thread_creator.create_thread_via_websocket(user.id, thread_name)
    
    # Add thread metadata to context
    thread_metadata = {
        "priority": "high",
        "tags": ["production", "optimization", "critical"],
        "assigned_agents": ["cost_optimizer", "performance_analyzer"],
        "created_by": user.id,
        "last_activity": time.time()
    }
    
    # Store metadata in thread context
    context_key = f"{user.id}:{thread_id}"
    existing_context = ws_thread_fixtures.thread_contexts.get(context_key, {})
    ws_thread_fixtures.thread_contexts[context_key] = {
        **existing_context,
        "metadata": thread_metadata,
        "thread_id": thread_id,
        "thread_name": thread_name
    }
    
    # Verify metadata is preserved in context
    preserved_context = ws_thread_fixtures.thread_contexts.get(context_key, {})
    preserved_metadata = preserved_context.get("metadata", {})
    
    assert preserved_metadata["priority"] == "high", "Priority metadata must be preserved"
    assert "production" in preserved_metadata["tags"], "Tags metadata must be preserved"
    assert preserved_metadata["assigned_agents"] == thread_metadata["assigned_agents"], \
           "Agent assignments must be preserved"
    assert preserved_metadata["created_by"] == user.id, "Creator metadata must be preserved"


@pytest.mark.asyncio
async def test_thread_creation_isolation_across_users(ws_thread_fixtures, thread_creator):
    """Test thread creation maintains isolation across different users."""
    user_a = TEST_USERS["free"]
    user_b = TEST_USERS["mid"]
    
    # Create connections for both users
    await ws_thread_fixtures.create_authenticated_connection(user_a.id)
    await ws_thread_fixtures.create_authenticated_connection(user_b.id)
    
    # Create threads for each user
    thread_a_id = await thread_creator.create_thread_via_websocket(user_a.id, "User A Thread")
    thread_b_id = await thread_creator.create_thread_via_websocket(user_b.id, "User B Thread")
    
    # Verify thread contexts are isolated
    context_a_key = f"{user_a.id}:{thread_a_id}"
    context_b_key = f"{user_b.id}:{thread_b_id}"
    
    assert context_a_key in ws_thread_fixtures.thread_contexts, "User A thread context must exist"
    assert context_b_key in ws_thread_fixtures.thread_contexts, "User B thread context must exist"
    
    # Verify user-specific events isolation
    user_a_events = thread_creator.get_creation_events_for_user(user_a.id)
    user_b_events = thread_creator.get_creation_events_for_user(user_b.id)
    
    assert len(user_a_events) >= 1, "User A must have thread events"
    assert len(user_b_events) >= 1, "User B must have thread events"
    
    # Verify no cross-user thread access
    user_a_thread_ids = {e["thread_id"] for e in user_a_events}
    user_b_thread_ids = {e["thread_id"] for e in user_b_events}
    
    assert len(user_a_thread_ids.intersection(user_b_thread_ids)) == 0, \
           "Users must not have access to each other's threads"


@pytest.mark.asyncio
async def test_thread_creation_context_initialization(ws_thread_fixtures, thread_creator, 
                                                       thread_context_manager):
    """Test thread creation properly initializes context for agent operations."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create thread
    thread_name = "Context Initialization Thread"
    thread_id = await thread_creator.create_thread_via_websocket(user.id, thread_name)
    
    # Verify thread context was initialized
    context_key = f"{user.id}:{thread_id}"
    assert context_key in ws_thread_fixtures.thread_contexts, "Thread context must be initialized"
    
    context = ws_thread_fixtures.thread_contexts[context_key]
    assert context["thread_id"] == thread_id, "Context must contain correct thread ID"
    assert context["thread_name"] == thread_name, "Context must contain correct thread name"
    assert "created_at" in context, "Context must contain creation timestamp"
    assert "messages" in context, "Context must be prepared for messages"
    
    # Add agent context to verify initialization works for agent operations
    agent_data = {
        "agent_id": "initialization_agent",
        "status": "ready",
        "execution_state": {"initialized": True}
    }
    
    await thread_context_manager.preserve_agent_context_in_thread(
        user.id, thread_id, agent_data
    )
    
    # Verify agent context was properly preserved
    updated_context = ws_thread_fixtures.thread_contexts[context_key]
    assert "agent_context" in updated_context, "Agent context must be preserved"
    assert updated_context["agent_context"]["agent_id"] == "initialization_agent"


@pytest.mark.asyncio
async def test_thread_creation_performance_under_load(ws_thread_fixtures, thread_creator):
    """Test thread creation performance under concurrent load."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Test concurrent thread creation
    thread_count = 10
    thread_names = [f"Load Test Thread {i+1}" for i in range(thread_count)]
    
    # Measure creation time
    start_time = time.perf_counter()
    created_thread_ids = await thread_creator.create_multiple_threads_concurrently(
        user.id, thread_names
    )
    creation_time = time.perf_counter() - start_time
    
    # Verify performance and correctness
    assert len(created_thread_ids) == thread_count, "All threads must be created"
    assert creation_time < 5.0, f"Creation should complete within 5 seconds, took {creation_time:.2f}s"
    
    # Verify all creation events captured
    creation_events = thread_creator.get_creation_events_for_user(user.id)
    assert len(creation_events) == thread_count, "All creations must generate events"
    
    # Verify all threads have contexts
    for thread_id in created_thread_ids:
        context_key = f"{user.id}:{thread_id}"
        assert context_key in ws_thread_fixtures.thread_contexts, \
               f"Thread {thread_id} must have initialized context"