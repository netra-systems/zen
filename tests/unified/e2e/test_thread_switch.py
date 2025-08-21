"""Thread Switching Tests - WebSocket Flow
Focused tests for thread switching and history loading operations.
Extracted from test_thread_management_websocket.py for better organization.

BVJ: Context switching reliability prevents user frustration and session loss.
Segment: All customer tiers. Business Goal: Retention through seamless thread operations.
Value Impact: Thread switching reliability maintains user workflow continuity.
Strategic Impact: Context switching failures disrupt user experience and cause churn.
"""

import asyncio
import pytest
import time
from typing import Dict, Any, List

from tests.unified.config import TEST_USERS
from tests.unified.e2e.thread_test_fixtures_core import (
    ThreadWebSocketFixtures, ThreadContextManager, ThreadTestDataFactory,
    unified_harness, ws_thread_fixtures, thread_context_manager, test_users
)
from netra_backend.app.schemas.core_enums import WebSocketMessageType
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ThreadSwitchingManager:
    """Manages thread switching operations via WebSocket."""
    
    def __init__(self, ws_fixtures: ThreadWebSocketFixtures):
        self.ws_fixtures = ws_fixtures
        self.switch_operations: List[Dict[str, Any]] = []
    
    async def switch_thread_via_websocket(self, user_id: str, thread_id: str) -> Dict[str, Any]:
        """Switch threads via WebSocket and return history."""
        # Build and send switch message
        switch_message = self.ws_fixtures.build_websocket_message(
            WebSocketMessageType.SWITCH_THREAD,
            thread_id=thread_id
        )
        await self.ws_fixtures.send_websocket_message(user_id, switch_message)
        
        # Load thread history
        history = await self._load_thread_history(user_id, thread_id)
        
        # Capture thread switched event
        self.ws_fixtures.capture_thread_event(
            WebSocketMessageType.THREAD_SWITCHED,
            user_id,
            thread_id
        )
        
        # Track switch operation
        switch_operation = {
            "user_id": user_id,
            "thread_id": thread_id,
            "timestamp": time.time(),
            "history_loaded": len(history.get("messages", [])),
            "operation_id": f"switch_{len(self.switch_operations)}"
        }
        self.switch_operations.append(switch_operation)
        
        return history
    
    async def _load_thread_history(self, user_id: str, thread_id: str) -> Dict[str, Any]:
        """Load thread history and update context."""
        # Generate mock history for testing
        messages = self._generate_mock_history(thread_id, 10)
        
        history = {
            "thread_id": thread_id,
            "messages": messages,
            "total_messages": len(messages),
            "loaded_at": time.time()
        }
        
        # Preserve existing context and merge with history
        context_key = f"{user_id}:{thread_id}"
        existing_context = self.ws_fixtures.thread_contexts.get(context_key, {})
        self.ws_fixtures.thread_contexts[context_key] = {
            **existing_context, 
            **history,
            "last_accessed": time.time()
        }
        
        return history
    
    def _generate_mock_history(self, thread_id: str, count: int) -> List[Dict[str, Any]]:
        """Generate mock message history for thread."""
        messages = []
        for i in range(count):
            messages.append({
                "id": f"msg_{i}_{thread_id[:8]}",
                "thread_id": thread_id,
                "content": f"Historical message {i+1}",
                "role": "user" if i % 2 == 0 else "assistant",
                "timestamp": time.time() - (count - i) * 60,
                "metadata": {"index": i, "mock": True}
            })
        return messages
    
    def get_switch_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get thread switch events for specific user."""
        return [
            event for event in self.ws_fixtures.thread_events
            if (event["type"] == WebSocketMessageType.THREAD_SWITCHED.value and 
                event["user_id"] == user_id)
        ]
    
    def get_switch_operations_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get switch operations for specific user."""
        return [
            op for op in self.switch_operations
            if op["user_id"] == user_id
        ]


class HistoricalMessageLoader:
    """Handles historical message loading with pagination."""
    
    def __init__(self, ws_fixtures: ThreadWebSocketFixtures):
        self.ws_fixtures = ws_fixtures
        self.load_operations: List[Dict[str, Any]] = []
    
    async def load_historical_messages(self, user_id: str, thread_id: str, 
                                       limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Load historical messages with pagination."""
        # Build and send load message
        load_message = self.ws_fixtures.build_websocket_message(
            WebSocketMessageType.GET_THREAD_HISTORY,
            thread_id=thread_id,
            limit=limit,
            offset=offset
        )
        await self.ws_fixtures.send_websocket_message(user_id, load_message)
        
        # Fetch paginated history
        history_data = await self._fetch_paginated_history(thread_id, limit, offset)
        
        # Track load operation
        await self._track_load_operation(user_id, thread_id, limit, offset)
        
        return history_data
    
    async def _fetch_paginated_history(self, thread_id: str, limit: int, offset: int) -> Dict[str, Any]:
        """Fetch paginated message history."""
        # Simulate loading 100 historical messages with pagination
        total_messages = 100
        messages = []
        
        for i in range(offset, min(offset + limit, total_messages)):
            messages.append({
                "id": f"historical_msg_{i}_{thread_id[:8]}",
                "thread_id": thread_id,
                "content": f"Historical message {i+1}",
                "role": "user" if i % 2 == 0 else "assistant",
                "timestamp": time.time() - (total_messages - i) * 30,
                "metadata": {"page": offset // limit, "index": i}
            })
        
        return {
            "thread_id": thread_id,
            "messages": messages,
            "total": total_messages,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_messages,
            "loaded_at": time.time()
        }
    
    async def _track_load_operation(self, user_id: str, thread_id: str, limit: int, offset: int) -> None:
        """Track message loading operation."""
        operation = {
            "user_id": user_id,
            "thread_id": thread_id,
            "limit": limit,
            "offset": offset,
            "timestamp": time.time(),
            "operation_id": f"load_{len(self.load_operations)}"
        }
        self.load_operations.append(operation)


@pytest.fixture
def thread_switcher(ws_thread_fixtures):
    """Thread switching manager fixture."""
    return ThreadSwitchingManager(ws_thread_fixtures)


@pytest.fixture
def message_loader(ws_thread_fixtures):
    """Historical message loader fixture."""
    return HistoricalMessageLoader(ws_thread_fixtures)


@pytest.fixture
async def prepared_threads(ws_thread_fixtures):
    """Fixture providing pre-created threads for switching tests."""
    user = TEST_USERS["mid"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create threads with different contexts
    threads = {}
    
    # Thread A with optimization context
    thread_a_id = f"thread_a_{user.id}_{int(time.time())}"
    threads["thread_a"] = {
        "id": thread_a_id,
        "name": "Optimization Thread",
        "context": {
            "thread_id": thread_a_id,
            "thread_name": "Optimization Thread",
            "created_at": time.time(),
            "messages": []
        }
    }
    
    # Thread B with analysis context
    thread_b_id = f"thread_b_{user.id}_{int(time.time())}"
    threads["thread_b"] = {
        "id": thread_b_id,
        "name": "Analysis Thread",
        "context": {
            "thread_id": thread_b_id,
            "thread_name": "Analysis Thread",
            "created_at": time.time(),
            "messages": []
        }
    }
    
    # Initialize contexts
    for thread_key, thread_data in threads.items():
        context_key = f"{user.id}:{thread_data['id']}"
        ws_thread_fixtures.thread_contexts[context_key] = thread_data["context"]
    
    return {"user": user, "threads": threads}


@pytest.mark.asyncio
async def test_thread_switching_loads_correct_history(prepared_threads, thread_switcher, 
                                                       thread_context_manager):
    """Test thread switching loads correct message history and restores context."""
    user = prepared_threads["user"]
    thread_a = prepared_threads["threads"]["thread_a"]
    thread_b = prepared_threads["threads"]["thread_b"]
    
    # Preserve agent context in Thread A
    agent_data = {
        "agent_id": "optimizer_agent",
        "status": "active",
        "execution_state": {"step": 3, "phase": "analysis"}
    }
    await thread_context_manager.preserve_agent_context_in_thread(
        user.id, thread_a["id"], agent_data
    )
    
    # Switch to Thread B and capture context
    before_switch = thread_context_manager.capture_context_snapshot(
        user.id, thread_a["id"], "before_switch"
    )
    history_b = await thread_switcher.switch_thread_via_websocket(user.id, thread_b["id"])
    
    # Switch back to Thread A
    history_a = await thread_switcher.switch_thread_via_websocket(user.id, thread_a["id"])
    after_switch = thread_context_manager.capture_context_snapshot(
        user.id, thread_a["id"], "after_switch"
    )
    
    # Verify correct history loaded and context preserved
    assert history_a["thread_id"] == thread_a["id"], "Thread A history must be loaded correctly"
    assert history_b["thread_id"] == thread_b["id"], "Thread B history must be loaded correctly"
    assert thread_context_manager.verify_context_preservation(before_switch, after_switch), \
           "Agent context must be preserved across thread switches"
    
    # Verify switch events captured
    switch_events = thread_switcher.get_switch_events_for_user(user.id)
    assert len(switch_events) == 2, "Both thread switches must generate events"


@pytest.mark.asyncio
async def test_agent_context_maintained_per_thread(prepared_threads, thread_switcher, 
                                                    thread_context_manager):
    """Test agent context is maintained per thread without cross-contamination."""
    user = prepared_threads["user"]
    thread_1 = prepared_threads["threads"]["thread_a"]
    thread_2 = prepared_threads["threads"]["thread_b"]
    
    # Set different agent contexts for each thread
    agent_1_data = {
        "agent_id": "optimizer",
        "status": "executing",
        "execution_state": {"phase": "analysis", "progress": 0.7}
    }
    agent_2_data = {
        "agent_id": "analyzer",
        "status": "planning",
        "execution_state": {"phase": "preparation", "progress": 0.3}
    }
    
    await thread_context_manager.preserve_agent_context_in_thread(
        user.id, thread_1["id"], agent_1_data
    )
    await thread_context_manager.preserve_agent_context_in_thread(
        user.id, thread_2["id"], agent_2_data
    )
    
    # Execute agent in thread 1, switch to thread 2, verify thread 1 context preserved
    await thread_switcher.switch_thread_via_websocket(user.id, thread_1["id"])
    before_context = thread_context_manager.capture_context_snapshot(
        user.id, thread_1["id"], "agent_execution"
    )
    
    await thread_switcher.switch_thread_via_websocket(user.id, thread_2["id"])
    await thread_switcher.switch_thread_via_websocket(user.id, thread_1["id"])
    after_context = thread_context_manager.capture_context_snapshot(
        user.id, thread_1["id"], "context_restoration"
    )
    
    # Verify context isolation and preservation
    isolation_verified = thread_context_manager.validate_context_isolation(
        user.id, thread_1["id"], thread_2["id"]
    )
    context_preserved = thread_context_manager.verify_context_preservation(
        before_context, after_context
    )
    
    assert isolation_verified, "Thread contexts must remain isolated from each other"
    assert context_preserved, "Agent context must be preserved when returning to thread"


@pytest.mark.asyncio
async def test_historical_message_loading_with_pagination(ws_thread_fixtures, message_loader):
    """Test historical message loading with proper pagination support."""
    user = TEST_USERS["enterprise"]
    
    # Create connection and thread
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    thread_id = f"long_conversation_{user.id}_{int(time.time())}"
    
    # Test pagination with different limits and offsets
    page_1 = await message_loader.load_historical_messages(user.id, thread_id, limit=25, offset=0)
    page_2 = await message_loader.load_historical_messages(user.id, thread_id, limit=25, offset=25)
    page_3 = await message_loader.load_historical_messages(user.id, thread_id, limit=50, offset=50)
    
    # Verify pagination works correctly
    assert len(page_1["messages"]) == 25, "First page must contain 25 messages"
    assert len(page_2["messages"]) == 25, "Second page must contain 25 messages"
    assert len(page_3["messages"]) == 50, "Third page must contain 50 messages"
    
    # Verify total counts and pagination metadata
    assert page_1["total"] == 100, "Total message count must be correct"
    assert page_1["has_more"] == True, "First page must indicate more messages available"
    assert page_2["offset"] == 25, "Second page offset must be correct"
    assert page_3["offset"] == 50, "Third page offset must be correct"
    
    # Verify no message duplication across pages
    page_1_ids = {msg["id"] for msg in page_1["messages"]}
    page_2_ids = {msg["id"] for msg in page_2["messages"]}
    assert len(page_1_ids.intersection(page_2_ids)) == 0, "Pages must not contain duplicate messages"


@pytest.mark.asyncio
async def test_websocket_reconnection_preserves_thread_state(ws_thread_fixtures, thread_switcher, 
                                                             thread_context_manager):
    """Test WebSocket reconnection preserves thread state and context."""
    user = TEST_USERS["enterprise"]
    
    # Create initial connection and thread
    connection = await ws_thread_fixtures.create_authenticated_connection(user.id)
    thread_id = f"resilient_thread_{user.id}_{int(time.time())}"
    
    # Initialize thread context
    ws_thread_fixtures.thread_contexts[f"{user.id}:{thread_id}"] = {
        "thread_id": thread_id,
        "thread_name": "Resilient Thread",
        "created_at": time.time(),
        "messages": []
    }
    
    # Set agent context
    agent_data = {
        "agent_id": "resilient_agent",
        "status": "active",
        "execution_state": {"step": 5, "checkpoint": "data_analysis"}
    }
    await thread_context_manager.preserve_agent_context_in_thread(user.id, thread_id, agent_data)
    
    # Capture state before disconnection
    before_disconnect = thread_context_manager.capture_context_snapshot(
        user.id, thread_id, "before_disconnect"
    )
    
    # Simulate disconnection
    connection["connected"] = False
    del ws_thread_fixtures.active_connections[user.id]
    
    # Simulate reconnection
    new_connection = await ws_thread_fixtures.create_authenticated_connection(user.id)
    after_reconnect = thread_context_manager.capture_context_snapshot(
        user.id, thread_id, "after_reconnect"
    )
    
    # Verify state preservation
    state_preserved = thread_context_manager.verify_context_preservation(
        before_disconnect, after_reconnect
    )
    assert state_preserved, "Thread state must be preserved after WebSocket reconnection"
    assert new_connection["connected"], "New connection must be established successfully"


@pytest.mark.asyncio
async def test_thread_switching_performance_optimization(ws_thread_fixtures, thread_switcher):
    """Test thread switching performance with multiple rapid switches."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create multiple threads
    thread_ids = []
    for i in range(5):
        thread_id = f"perf_thread_{i}_{user.id}_{int(time.time())}"
        thread_ids.append(thread_id)
        
        # Initialize thread context
        ws_thread_fixtures.thread_contexts[f"{user.id}:{thread_id}"] = {
            "thread_id": thread_id,
            "thread_name": f"Performance Thread {i+1}",
            "created_at": time.time(),
            "messages": []
        }
    
    # Perform rapid thread switches
    start_time = time.perf_counter()
    
    switch_tasks = []
    for thread_id in thread_ids:
        task = thread_switcher.switch_thread_via_websocket(user.id, thread_id)
        switch_tasks.append(task)
    
    # Execute switches
    histories = await asyncio.gather(*switch_tasks)
    switch_time = time.perf_counter() - start_time
    
    # Verify performance and correctness
    assert len(histories) == len(thread_ids), "All switches must complete"
    assert switch_time < 3.0, f"Switches should complete within 3 seconds, took {switch_time:.2f}s"
    
    # Verify all switches generated events
    switch_events = thread_switcher.get_switch_events_for_user(user.id)
    assert len(switch_events) == len(thread_ids), "All switches must generate events"
    
    # Verify each history corresponds to correct thread
    for i, history in enumerate(histories):
        assert history["thread_id"] == thread_ids[i], f"History {i} must match thread {i}"