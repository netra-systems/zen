"""Thread UI Messaging Tests
Focused tests for message addition and UI updates.
Extracted from test_thread_management_ui_update.py for better organization.

BVJ: Message handling reliability ensures continuous user engagement and workflow.
Segment: All tiers. Business Goal: User engagement through responsive messaging.
Value Impact: Real-time message updates maintain conversational flow.
Strategic Impact: Message handling failures disrupt core user interaction patterns.
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


class ThreadMessagingUIManager:
    """Manages thread messaging operations with UI state tracking."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.ui_state = {
            "thread_list": [],
            "active_thread": None,
            "message_history": [],
            "pagination_state": {"page": 1, "total_pages": 1},
            "loading_states": {"threads": False, "messages": False}
        }
        self.message_events: List[Dict[str, Any]] = []
        self.ui_updates: List[Dict[str, Any]] = []
    
    def add_thread_to_ui(self, thread_data: Dict[str, Any]) -> None:
        """Add thread to UI thread list."""
        thread_info = {
            "thread_id": thread_data["id"],
            "title": thread_data.get("title", "New Thread"),
            "created_at": thread_data.get("created_at"),
            "message_count": 0
        }
        self.ui_state["thread_list"].append(thread_info)
    
    def set_active_thread(self, thread_id: str) -> bool:
        """Set active thread in UI."""
        active_thread = next(
            (t for t in self.ui_state["thread_list"] if t["thread_id"] == thread_id),
            None
        )
        
        if active_thread:
            self.ui_state["active_thread"] = active_thread
            return True
        return False
    
    async def add_message_to_ui(self, thread_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add message to UI and update thread state."""
        # Add to message history if this is the active thread
        if (self.ui_state["active_thread"] and 
            self.ui_state["active_thread"]["thread_id"] == thread_id):
            self.ui_state["message_history"].append(message_data)
        
        # Update thread message count
        for thread_info in self.ui_state["thread_list"]:
            if thread_info["thread_id"] == thread_id:
                thread_info["message_count"] += 1
                break
        
        # Record message event
        message_event = {
            "type": "message_added",
            "thread_id": thread_id,
            "message_id": message_data["id"],
            "timestamp": time.time()
        }
        self.message_events.append(message_event)
        
        # Record UI update
        ui_update = {
            "operation": "message_add",
            "thread_id": thread_id,
            "message_count": len(self.ui_state["message_history"]),
            "timestamp": time.time()
        }
        self.ui_updates.append(ui_update)
        
        return {
            "ui_updated": True,
            "message_added": True,
            "current_message_count": len(self.ui_state["message_history"])
        }
    
    async def update_message_pagination(self) -> Dict[str, Any]:
        """Update pagination state based on current messages."""
        messages_per_page = 20
        total_messages = len(self.ui_state["message_history"])
        total_pages = max(1, (total_messages + messages_per_page - 1) // messages_per_page)
        
        self.ui_state["pagination_state"] = {
            "page": 1,
            "total_pages": total_pages,
            "total_messages": total_messages,
            "messages_per_page": messages_per_page
        }
        
        return {
            "pagination_updated": True,
            "total_messages": total_messages,
            "total_pages": total_pages
        }
    
    def get_current_ui_state(self) -> Dict[str, Any]:
        """Get current UI state snapshot."""
        return self.ui_state.copy()
    
    def get_message_events(self) -> List[Dict[str, Any]]:
        """Get message events history."""
        return self.message_events.copy()
    
    def get_ui_updates(self) -> List[Dict[str, Any]]:
        """Get UI updates history."""
        return self.ui_updates.copy()


class ThreadMessagingExecutor:
    """Executes thread messaging operations with UI integration."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.ui_manager = ThreadMessagingUIManager(user_id)
        self.created_threads: List[str] = []
    
    async def create_thread_with_ui_update(self, thread_title: str = None) -> Dict[str, Any]:
        """Create thread and update UI state."""
        thread_id = f"thread_{self.user_id}_{int(time.time())}_{len(self.created_threads)}"
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
    
    async def switch_to_thread(self, thread_id: str) -> Dict[str, Any]:
        """Switch to thread for messaging."""
        if thread_id not in self.created_threads:
            return {"operation_successful": False, "error": "Thread not found"}
        
        success = self.ui_manager.set_active_thread(thread_id)
        if not success:
            return {"operation_successful": False, "error": "Failed to set active thread"}
        
        # Reset message history for new thread
        self.ui_manager.ui_state["message_history"] = []
        
        return {
            "operation_successful": True,
            "active_thread_id": thread_id
        }
    
    async def add_message_with_ui_update(self, thread_id: str, content: str, role: str = "user") -> Dict[str, Any]:
        """Add message to thread and update UI."""
        if thread_id not in self.created_threads:
            return {"operation_successful": False, "error": "Thread not found"}
        
        # Mock message creation
        mock_message = MagicMock()
        mock_message.id = f"msg_{int(time.time() * 1000)}_{len(self.ui_manager.message_events)}"
        mock_message.created_at = datetime.now(timezone.utc)
        
        # Create message data
        message_data = {
            "id": mock_message.id,
            "content": content,
            "role": role,
            "created_at": mock_message.created_at.isoformat(),
            "thread_id": thread_id
        }
        
        # Update UI
        ui_result = await self.ui_manager.add_message_to_ui(thread_id, message_data)
        
        # Update pagination
        pagination_result = await self.ui_manager.update_message_pagination()
        
        return {
            "message": mock_message,
            "message_data": message_data,
            "ui_result": ui_result,
            "pagination_result": pagination_result,
            "operation_successful": True
        }
    
    async def add_multiple_messages(self, thread_id: str, message_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add multiple messages to thread."""
        results = []
        
        for config in message_configs:
            content = config.get("content", "Default message")
            role = config.get("role", "user")
            
            result = await self.add_message_with_ui_update(thread_id, content, role)
            results.append(result)
            
            # Small delay to ensure ordering
            await asyncio.sleep(0.001)
        
        return results
    
    def get_thread_message_count(self, thread_id: str) -> int:
        """Get message count for specific thread."""
        for thread_info in self.ui_manager.ui_state["thread_list"]:
            if thread_info["thread_id"] == thread_id:
                return thread_info["message_count"]
        return 0


@pytest.fixture
async def messaging_executor(test_users):
    """Thread messaging executor fixture."""
    user = test_users["mid"]
    return ThreadMessagingExecutor(user.id)


@pytest.fixture
async def prepared_thread_for_messaging(messaging_executor):
    """Fixture providing a thread ready for messaging tests."""
    result = await messaging_executor.create_thread_with_ui_update("Messaging Test Thread")
    thread_id = result["thread_data"]["id"]
    
    # Switch to the thread to make it active
    await messaging_executor.switch_to_thread(thread_id)
    
    return {
        "executor": messaging_executor,
        "thread_id": thread_id,
        "thread_data": result["thread_data"]
    }


@pytest.mark.asyncio
class TestThreadUIMessaging:
    """Thread UI Messaging Test Suite."""
    
    async def test_message_addition_ui_update(self, prepared_thread_for_messaging):
        """Test Case 1: Message addition updates UI and thread counters."""
        executor = prepared_thread_for_messaging["executor"]
        thread_id = prepared_thread_for_messaging["thread_id"]
        
        # Add multiple messages and verify UI updates
        messages = ["First message", "Second message", "Third message"]
        
        for i, content in enumerate(messages):
            result = await executor.add_message_with_ui_update(thread_id, content, "user")
            
            assert result["operation_successful"]
            assert result["ui_result"]["ui_updated"]
            assert result["ui_result"]["message_added"]
            
            # Verify message count in thread list
            message_count = executor.get_thread_message_count(thread_id)
            assert message_count == i + 1
            
            # Verify message in UI history (for active thread)
            ui_state = executor.ui_manager.get_current_ui_state()
            assert len(ui_state["message_history"]) == i + 1
            assert ui_state["message_history"][i]["content"] == content
        
        # Verify final UI state
        final_ui_state = executor.ui_manager.get_current_ui_state()
        assert len(final_ui_state["message_history"]) == len(messages)
        
        # Verify message events tracked
        message_events = executor.ui_manager.get_message_events()
        assert len(message_events) == len(messages)
    
    async def test_message_addition_different_roles(self, prepared_thread_for_messaging):
        """Test Case 2: Messages with different roles handled correctly."""
        executor = prepared_thread_for_messaging["executor"]
        thread_id = prepared_thread_for_messaging["thread_id"]
        
        # Add messages with different roles
        message_configs = [
            {"content": "User question", "role": "user"},
            {"content": "Assistant response", "role": "assistant"},
            {"content": "System message", "role": "system"},
            {"content": "Another user message", "role": "user"}
        ]
        
        results = await executor.add_multiple_messages(thread_id, message_configs)
        
        # Verify all messages added successfully
        assert len(results) == len(message_configs)
        for result in results:
            assert result["operation_successful"]
        
        # Verify message roles in UI
        ui_state = executor.ui_manager.get_current_ui_state()
        assert len(ui_state["message_history"]) == len(message_configs)
        
        for i, config in enumerate(message_configs):
            message = ui_state["message_history"][i]
            assert message["content"] == config["content"]
            assert message["role"] == config["role"]
        
        # Verify message count updated correctly
        message_count = executor.get_thread_message_count(thread_id)
        assert message_count == len(message_configs)
    
    async def test_message_pagination_state_management(self, prepared_thread_for_messaging):
        """Test Case 3: Message pagination state managed correctly."""
        executor = prepared_thread_for_messaging["executor"]
        thread_id = prepared_thread_for_messaging["thread_id"]
        
        # Add many messages to test pagination
        message_count = 25  # More than one page (20 per page)
        message_configs = [
            {"content": f"Message {i+1}", "role": "user" if i % 2 == 0 else "assistant"}
            for i in range(message_count)
        ]
        
        results = await executor.add_multiple_messages(thread_id, message_configs)
        
        # Verify all messages added
        assert len(results) == message_count
        
        # Verify pagination state
        ui_state = executor.ui_manager.get_current_ui_state()
        pagination = ui_state["pagination_state"]
        
        assert pagination["total_messages"] == message_count
        assert pagination["total_pages"] == 2  # 25 messages / 20 per page = 2 pages
        assert pagination["page"] == 1
        assert pagination["messages_per_page"] == 20
        
        # Verify UI updates tracked
        ui_updates = executor.ui_manager.get_ui_updates()
        assert len(ui_updates) == message_count
    
    async def test_concurrent_message_addition(self, prepared_thread_for_messaging):
        """Test Case 4: Concurrent message addition handled correctly."""
        executor = prepared_thread_for_messaging["executor"]
        thread_id = prepared_thread_for_messaging["thread_id"]
        
        # Create concurrent message addition tasks
        message_count = 10
        tasks = [
            executor.add_message_with_ui_update(
                thread_id, f"Concurrent message {i+1}", "user"
            )
            for i in range(message_count)
        ]
        
        # Execute concurrent additions
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        execution_time = time.perf_counter() - start_time
        
        # Verify performance
        assert execution_time < 2.0, f"Concurrent messaging should complete within 2 seconds, took {execution_time:.2f}s"
        
        # Verify all messages added successfully
        assert len(results) == message_count
        for result in results:
            assert result["operation_successful"]
        
        # Verify final UI state consistency
        ui_state = executor.ui_manager.get_current_ui_state()
        assert len(ui_state["message_history"]) == message_count
        
        # Verify thread message count
        final_count = executor.get_thread_message_count(thread_id)
        assert final_count == message_count
        
        # Verify message IDs are unique
        message_ids = [msg["id"] for msg in ui_state["message_history"]]
        assert len(set(message_ids)) == message_count, "All message IDs must be unique"
    
    async def test_message_addition_across_multiple_threads(self, messaging_executor):
        """Test Case 5: Message addition across multiple threads maintains isolation."""
        # Create multiple threads
        threads = []
        for i in range(3):
            result = await messaging_executor.create_thread_with_ui_update(f"Thread {i+1}")
            threads.append(result["thread_data"])
        
        # Add messages to each thread
        for i, thread in enumerate(threads):
            thread_id = thread["id"]
            
            # Switch to thread
            await messaging_executor.switch_to_thread(thread_id)
            
            # Add unique messages
            for j in range(3):
                await messaging_executor.add_message_with_ui_update(
                    thread_id, f"Thread {i+1} Message {j+1}", "user"
                )
        
        # Verify message counts for each thread
        for i, thread in enumerate(threads):
            thread_id = thread["id"]
            message_count = messaging_executor.get_thread_message_count(thread_id)
            assert message_count == 3, f"Thread {i+1} must have 3 messages"
        
        # Verify message isolation - switch to each thread and check history
        for i, thread in enumerate(threads):
            thread_id = thread["id"]
            await messaging_executor.switch_to_thread(thread_id)
            
            ui_state = messaging_executor.ui_manager.get_current_ui_state()
            # Note: message history is reset when switching threads in this implementation
            assert ui_state["active_thread"]["thread_id"] == thread_id
    
    async def test_message_ui_event_ordering(self, prepared_thread_for_messaging):
        """Test Case 6: Message UI events maintain correct ordering."""
        executor = prepared_thread_for_messaging["executor"]
        thread_id = prepared_thread_for_messaging["thread_id"]
        
        # Add messages in sequence with delays to ensure ordering
        messages = ["First", "Second", "Third", "Fourth"]
        
        for message in messages:
            await executor.add_message_with_ui_update(thread_id, message, "user")
            await asyncio.sleep(0.01)  # Small delay to ensure ordering
        
        # Verify message events ordering
        message_events = executor.ui_manager.get_message_events()
        assert len(message_events) == len(messages)
        
        # Verify timestamps are in order
        timestamps = [event["timestamp"] for event in message_events]
        assert timestamps == sorted(timestamps), "Event timestamps must be in order"
        
        # Verify UI updates ordering
        ui_updates = executor.ui_manager.get_ui_updates()
        assert len(ui_updates) == len(messages)
        
        update_timestamps = [update["timestamp"] for update in ui_updates]
        assert update_timestamps == sorted(update_timestamps), "UI update timestamps must be in order"
        
        # Verify message content order in UI
        ui_state = executor.ui_manager.get_current_ui_state()
        for i, expected_content in enumerate(messages):
            assert ui_state["message_history"][i]["content"] == expected_content
    
    async def test_message_addition_error_handling(self, messaging_executor):
        """Test Case 7: Message addition error handling."""
        # Attempt to add message to non-existent thread
        result = await messaging_executor.add_message_with_ui_update(
            "non_existent_thread", "Test message", "user"
        )
        
        assert not result["operation_successful"]
        assert "error" in result
        
        # Verify UI state not corrupted
        ui_state = messaging_executor.ui_manager.get_current_ui_state()
        assert len(ui_state["message_history"]) == 0
        assert len(ui_state["thread_list"]) == 0
        
        # Create valid thread and verify normal operation works
        thread_result = await messaging_executor.create_thread_with_ui_update("Error Recovery Thread")
        assert thread_result["operation_successful"]
        
        thread_id = thread_result["thread_data"]["id"]
        await messaging_executor.switch_to_thread(thread_id)
        
        valid_message = await messaging_executor.add_message_with_ui_update(
            thread_id, "Recovery message", "user"
        )
        assert valid_message["operation_successful"]
    
    async def test_message_addition_ui_performance(self, prepared_thread_for_messaging):
        """Test Case 8: Message addition UI performance under load."""
        executor = prepared_thread_for_messaging["executor"]
        thread_id = prepared_thread_for_messaging["thread_id"]
        
        # Add many messages and measure performance
        message_count = 50
        start_time = time.perf_counter()
        
        tasks = [
            executor.add_message_with_ui_update(
                thread_id, f"Performance message {i+1}", "user"
            )
            for i in range(message_count)
        ]
        
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # Verify performance requirements
        assert total_time < 5.0, f"Message addition should complete within 5 seconds, took {total_time:.2f}s"
        
        # Verify all operations succeeded
        successful_ops = sum(1 for r in results if r["operation_successful"])
        assert successful_ops == message_count, "All message additions must succeed"
        
        # Verify UI consistency after load
        ui_state = executor.ui_manager.get_current_ui_state()
        assert len(ui_state["message_history"]) == message_count
        
        final_count = executor.get_thread_message_count(thread_id)
        assert final_count == message_count
        
        # Verify no UI corruption
        for i, message in enumerate(ui_state["message_history"]):
            assert message["content"] == f"Performance message {i+1}"
            assert message["role"] == "user"
            assert "id" in message
            assert "created_at" in message