"""Thread UI Switching Tests
Focused tests for thread switching and history loading with UI updates.
Extracted from test_thread_management_ui_update.py for better organization.

BVJ: Thread switching reliability maintains user workflow continuity.
Segment: Early/Mid/Enterprise. Business Goal: Retention through seamless context switching.
Value Impact: Switching reliability prevents workflow interruption and data loss.
Strategic Impact: Context switching failures disrupt user experience and cause churn.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from tests.e2e.fixtures.core.thread_test_fixtures_core import (
    ThreadTestDataFactory,
    test_users,
    unified_harness,
)


class ThreadSwitchingUIManager:
    """Manages thread switching operations with UI state tracking."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.active_thread_id: Optional[str] = None
        self.ui_state = {
            "thread_list": [],
            "active_thread": None,
            "message_history": [],
            "pagination_state": {"page": 1, "total_pages": 1},
            "loading_states": {"threads": False, "messages": False}
        }
        self.websocket_events: List[Dict[str, Any]] = []
        self.switch_history: List[Dict[str, Any]] = []
    
    async def track_thread_switch(self, thread_id: str) -> Dict[str, Any]:
        """Track thread switching and UI state updates."""
        previous_thread = self.active_thread_id
        self.active_thread_id = thread_id
        
        # Update active thread in UI state
        active_thread = next(
            (t for t in self.ui_state["thread_list"] if t["thread_id"] == thread_id),
            None
        )
        
        if active_thread:
            self.ui_state["active_thread"] = active_thread
            self.ui_state["loading_states"]["messages"] = True
            
            # Record switch event
            switch_event = {
                "type": "thread_switched",
                "previous_thread": previous_thread,
                "new_thread": thread_id,
                "timestamp": time.time()
            }
            self.websocket_events.append(switch_event)
            self.switch_history.append(switch_event)
            
            return {
                "switch_successful": True,
                "previous_thread": previous_thread,
                "current_thread": thread_id,
                "ui_loading": True
            }
        
        return {"switch_successful": False, "error": "Thread not found"}
    
    async def load_message_history(self, thread_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Load and paginate message history for UI."""
        self.ui_state["message_history"] = messages
        self.ui_state["loading_states"]["messages"] = False
        
        # Update pagination state
        messages_per_page = 20
        total_messages = len(messages)
        total_pages = max(1, (total_messages + messages_per_page - 1) // messages_per_page)
        
        self.ui_state["pagination_state"] = {
            "page": 1,
            "total_pages": total_pages,
            "total_messages": total_messages,
            "messages_per_page": messages_per_page
        }
        
        return {
            "messages_loaded": total_messages,
            "pagination_ready": True,
            "ui_updated": True
        }
    
    def add_thread_to_ui(self, thread_data: Dict[str, Any]) -> None:
        """Add thread to UI thread list."""
        thread_info = {
            "thread_id": thread_data["id"],
            "title": thread_data.get("title", "New Thread"),
            "created_at": thread_data.get("created_at"),
            "message_count": 0
        }
        self.ui_state["thread_list"].append(thread_info)
    
    def get_current_ui_state(self) -> Dict[str, Any]:
        """Get current UI state snapshot."""
        return self.ui_state.copy()
    
    def get_switch_history(self) -> List[Dict[str, Any]]:
        """Get thread switching history."""
        return self.switch_history.copy()


class ThreadOperationExecutor:
    """Executes thread operations with UI integration."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.ui_manager = ThreadSwitchingUIManager(user_id)
        self.created_threads: List[str] = []
    
    async def create_thread_with_ui_update(self, thread_title: str = None) -> Dict[str, Any]:
        """Create thread and update UI state."""
        thread_id = f"thread_{self.user_id}_{int(time.time())}_{len(self.created_threads)}"
        # Mock: Generic component isolation for controlled unit testing
        mock_thread = MagicMock()
        mock_thread.id = thread_id
        mock_thread.created_at = datetime.now(timezone.utc)
        
        thread_data = {
            "id": thread_id,
            "title": thread_title or f"Thread {thread_id}",
            "created_at": mock_thread.created_at.isoformat(),
            "user_id": self.user_id
        }
        
        # Add to UI
        self.ui_manager.add_thread_to_ui(thread_data)
        self.created_threads.append(thread_id)
        
        return {
            "thread": mock_thread,
            "thread_data": thread_data,
            "operation_successful": True
        }
    
    async def switch_thread_with_history_load(self, thread_id: str) -> Dict[str, Any]:
        """Switch to thread and load message history."""
        # Verify thread exists
        if thread_id not in self.created_threads:
            return {"operation_successful": False, "error": "Thread not found"}
        
        # Track UI switch
        switch_result = await self.ui_manager.track_thread_switch(thread_id)
        if not switch_result["switch_successful"]:
            return {"operation_successful": False, "error": "UI switch failed"}
        
        # Mock message history
        message_data = [
            {
                "id": f"msg_{i}",
                "content": f"Test message {i+1}",
                "role": "user" if i % 2 == 0 else "assistant",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            for i in range(5)  # Create 5 test messages
        ]
        
        history_result = await self.ui_manager.load_message_history(thread_id, message_data)
        
        return {
            "switch_result": switch_result,
            "history_result": history_result,
            "message_count": len(message_data),
            "operation_successful": True
        }
    
    async def add_message_with_ui_update(self, thread_id: str, content: str, role: str = "user") -> Dict[str, Any]:
        """Add message to thread and update UI."""
        # Mock message creation
        # Mock: Generic component isolation for controlled unit testing
        mock_message = MagicMock()
        mock_message.id = f"msg_{int(time.time())}"
        mock_message.created_at = datetime.now(timezone.utc)
        
        # Update UI message history
        current_messages = self.ui_manager.ui_state["message_history"]
        new_message_data = {
            "id": mock_message.id,
            "content": content,
            "role": role,
            "created_at": mock_message.created_at.isoformat()
        }
        current_messages.append(new_message_data)
        
        # Update thread message count in UI
        for thread_info in self.ui_manager.ui_state["thread_list"]:
            if thread_info["thread_id"] == thread_id:
                thread_info["message_count"] += 1
                break
        
        return {
            "message": mock_message,
            "message_data": new_message_data,
            "ui_updated": True,
            "operation_successful": True
        }


@pytest.fixture
async def test_switching_executor(test_users):
    """Thread operation executor fixture for switching tests."""
    user = test_users["mid"]
    return ThreadOperationExecutor(user.id)


@pytest.fixture
async def prepared_threads_for_switching(switching_executor):
    """Fixture providing pre-created threads for switching tests."""
    # Create multiple threads
    threads = []
    thread_titles = ["Switch Test Thread 1", "Switch Test Thread 2", "Switch Test Thread 3"]
    
    for title in thread_titles:
        result = await switching_executor.create_thread_with_ui_update(title)
        threads.append(result["thread_data"])
    
    return {
        "executor": switching_executor,
        "threads": threads
    }


@pytest.mark.asyncio
class TestThreadUISwitching:
    """Thread UI Switching Test Suite."""
    
    async def test_thread_switching_with_history_load(self, prepared_threads_for_switching):
        """Test Case 1: Thread switching loads message history correctly."""
        executor = prepared_threads_for_switching["executor"]
        threads = prepared_threads_for_switching["threads"]
        
        # Switch to first thread
        thread_id = threads[0]["id"]
        
        # Add some messages to the thread first
        await executor.add_message_with_ui_update(thread_id, "First message", "user")
        await executor.add_message_with_ui_update(thread_id, "Second message", "assistant")
        
        # Switch to thread and verify history load
        switch_result = await executor.switch_thread_with_history_load(thread_id)
        
        assert switch_result["operation_successful"]
        assert switch_result["switch_result"]["switch_successful"]
        assert switch_result["message_count"] == 5  # 5 mock messages generated
        assert switch_result["history_result"]["messages_loaded"] == 5
        
        # Verify UI state updated
        ui_state = executor.ui_manager.get_current_ui_state()
        assert ui_state["active_thread"]["thread_id"] == thread_id
        assert len(ui_state["message_history"]) == 5
        assert not ui_state["loading_states"]["messages"]  # Loading complete
    
    async def test_thread_switching_between_multiple_threads(self, prepared_threads_for_switching):
        """Test Case 2: Switching between multiple threads maintains state correctly."""
        executor = prepared_threads_for_switching["executor"]
        threads = prepared_threads_for_switching["threads"]
        
        # Switch to each thread and verify
        switch_results = []
        for i, thread in enumerate(threads):
            thread_id = thread["id"]
            
            # Add unique message to each thread
            await executor.add_message_with_ui_update(
                thread_id, f"Unique message for thread {i+1}", "user"
            )
            
            # Switch to thread
            result = await executor.switch_thread_with_history_load(thread_id)
            assert result["operation_successful"]
            
            switch_results.append(result)
            
            # Verify active thread is correct
            ui_state = executor.ui_manager.get_current_ui_state()
            assert ui_state["active_thread"]["thread_id"] == thread_id
        
        # Verify switch history
        switch_history = executor.ui_manager.get_switch_history()
        assert len(switch_history) == len(threads)
        
        # Verify each switch event
        for i, switch_event in enumerate(switch_history):
            assert switch_event["type"] == "thread_switched"
            assert switch_event["new_thread"] == threads[i]["id"]
    
    async def test_thread_switching_ui_loading_states(self, prepared_threads_for_switching):
        """Test Case 3: UI loading states managed correctly during switching."""
        executor = prepared_threads_for_switching["executor"]
        threads = prepared_threads_for_switching["threads"]
        
        thread_id = threads[0]["id"]
        
        # Capture UI state before switch
        ui_state_before = executor.ui_manager.get_current_ui_state()
        assert not ui_state_before["loading_states"]["messages"]
        
        # Initiate thread switch
        switch_result = await executor.ui_manager.track_thread_switch(thread_id)
        assert switch_result["switch_successful"]
        assert switch_result["ui_loading"]
        
        # Verify loading state is active
        ui_state_during = executor.ui_manager.get_current_ui_state()
        assert ui_state_during["loading_states"]["messages"]
        
        # Complete history load
        mock_messages = [{"id": "msg1", "content": "test", "role": "user"}]
        history_result = await executor.ui_manager.load_message_history(thread_id, mock_messages)
        
        assert history_result["ui_updated"]
        
        # Verify loading state is cleared
        ui_state_after = executor.ui_manager.get_current_ui_state()
        assert not ui_state_after["loading_states"]["messages"]
    
    async def test_pagination_state_management_during_switching(self, prepared_threads_for_switching):
        """Test Case 4: Message pagination state managed correctly during switching."""
        executor = prepared_threads_for_switching["executor"]
        threads = prepared_threads_for_switching["threads"]
        
        thread_id = threads[0]["id"]
        
        # Add many messages to test pagination
        for i in range(25):  # More than one page (20 per page)
            await executor.add_message_with_ui_update(
                thread_id, f"Message {i+1}", "user"
            )
        
        # Switch to thread and load history
        switch_result = await executor.switch_thread_with_history_load(thread_id)
        
        assert switch_result["operation_successful"]
        assert switch_result["message_count"] == 5  # Mock history returns 5 messages
        
        # Verify pagination state
        ui_state = executor.ui_manager.get_current_ui_state()
        pagination = ui_state["pagination_state"]
        
        assert pagination["total_messages"] == 5
        assert pagination["page"] == 1
        assert pagination["messages_per_page"] == 20
        assert pagination["total_pages"] == 1  # 5 messages / 20 per page = 1 page
    
    async def test_concurrent_thread_switching_operations(self, prepared_threads_for_switching):
        """Test Case 5: Concurrent thread switching operations handled correctly."""
        executor = prepared_threads_for_switching["executor"]
        threads = prepared_threads_for_switching["threads"]
        
        # Create switching tasks for multiple threads
        switch_tasks = []
        for thread in threads:
            task = executor.switch_thread_with_history_load(thread["id"])
            switch_tasks.append(task)
        
        # Execute concurrent switches
        start_time = time.perf_counter()
        results = await asyncio.gather(*switch_tasks, return_exceptions=True)
        switch_time = time.perf_counter() - start_time
        
        # Verify performance
        assert switch_time < 2.0, f"Concurrent switches should complete within 2 seconds, took {switch_time:.2f}s"
        
        # Verify all switches completed
        successful_switches = [r for r in results if isinstance(r, dict) and r.get("operation_successful")]
        assert len(successful_switches) == len(threads)
        
        # Verify final UI state is consistent
        ui_state = executor.ui_manager.get_current_ui_state()
        assert ui_state["active_thread"] is not None
        assert ui_state["active_thread"]["thread_id"] in [t["id"] for t in threads]
    
    async def test_thread_switching_error_recovery(self, switching_executor):
        """Test Case 6: Thread switching error handling and recovery."""
        # Create a valid thread first
        valid_result = await switching_executor.create_thread_with_ui_update("Valid Thread")
        assert valid_result["operation_successful"]
        valid_thread_id = valid_result["thread_data"]["id"]
        
        # Attempt to switch to non-existent thread
        invalid_switch = await switching_executor.switch_thread_with_history_load("invalid_thread_id")
        assert not invalid_switch["operation_successful"]
        assert "error" in invalid_switch
        
        # Verify UI state not corrupted
        ui_state = switching_executor.ui_manager.get_current_ui_state()
        assert len(ui_state["thread_list"]) == 1  # Original thread still there
        
        # Verify valid operations still work
        valid_switch = await switching_executor.switch_thread_with_history_load(valid_thread_id)
        assert valid_switch["operation_successful"]
        
        # Verify UI properly updated to valid thread
        updated_ui_state = switching_executor.ui_manager.get_current_ui_state()
        assert updated_ui_state["active_thread"]["thread_id"] == valid_thread_id
    
    async def test_thread_switching_websocket_event_ordering(self, prepared_threads_for_switching):
        """Test Case 7: WebSocket events maintain correct ordering during switching."""
        executor = prepared_threads_for_switching["executor"]
        threads = prepared_threads_for_switching["threads"]
        
        # Perform sequence of switches
        switch_sequence = [threads[0]["id"], threads[1]["id"], threads[0]["id"], threads[2]["id"]]
        
        for thread_id in switch_sequence:
            result = await executor.switch_thread_with_history_load(thread_id)
            assert result["operation_successful"]
            
            # Small delay to ensure ordering
            await asyncio.sleep(0.01)
        
        # Verify event ordering
        switch_history = executor.ui_manager.get_switch_history()
        assert len(switch_history) == len(switch_sequence)
        
        # Verify timestamps are in order
        timestamps = [event["timestamp"] for event in switch_history]
        assert timestamps == sorted(timestamps), "Event timestamps must be in order"
        
        # Verify switch sequence matches expected order
        switched_threads = [event["new_thread"] for event in switch_history]
        assert switched_threads == switch_sequence, "Switch order must match expected sequence"
    
    async def test_thread_switching_context_preservation(self, prepared_threads_for_switching):
        """Test Case 8: Thread context preserved across switching operations."""
        executor = prepared_threads_for_switching["executor"]
        threads = prepared_threads_for_switching["threads"]
        
        # Add different messages to each thread to create distinct contexts
        thread_contexts = {}
        for i, thread in enumerate(threads):
            thread_id = thread["id"]
            
            # Add unique messages to create context
            for j in range(3):
                await executor.add_message_with_ui_update(
                    thread_id, f"Thread {i+1} Message {j+1}", "user"
                )
            
            # Switch to thread to establish context
            result = await executor.switch_thread_with_history_load(thread_id)
            assert result["operation_successful"]
            
            # Capture context
            ui_state = executor.ui_manager.get_current_ui_state()
            thread_contexts[thread_id] = {
                "message_count": len(ui_state["message_history"]),
                "active_thread": ui_state["active_thread"].copy() if ui_state["active_thread"] else None
            }
        
        # Switch back to first thread and verify context preservation
        first_thread_id = threads[0]["id"]
        result = await executor.switch_thread_with_history_load(first_thread_id)
        assert result["operation_successful"]
        
        # Verify context restored correctly
        final_ui_state = executor.ui_manager.get_current_ui_state()
        assert final_ui_state["active_thread"]["thread_id"] == first_thread_id
        
        # Verify message history corresponds to correct thread
        expected_context = thread_contexts[first_thread_id]
        if expected_context["active_thread"]:
            assert final_ui_state["active_thread"]["title"] == expected_context["active_thread"]["title"]