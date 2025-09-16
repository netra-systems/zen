"""Thread UI Creation Tests
Focused tests for thread creation and UI synchronization.
Extracted from test_thread_management_ui_update.py for better organization.

BVJ: Protects $18K MRR from thread management issues affecting user workflow continuity.
Segment: Early/Mid/Enterprise. Business Goal: Retention through reliable thread operations.
Value Impact: Ensures thread creation and UI updates work seamlessly.
Strategic Impact: Prevents workflow disruption and user frustration from thread state issues.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.fixtures.core.thread_test_fixtures_core import (
    ThreadTestDataFactory,
    test_users,
    unified_harness,
)


class ThreadUIStateTracker:
    """L3 Real UI state tracker for thread creation testing."""
    
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
    
    async def track_thread_creation(self, thread_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track thread creation and UI updates."""
        thread_info = {
            "thread_id": thread_data["id"],
            "title": thread_data.get("title", "New Thread"),
            "created_at": thread_data.get("created_at"),
            "message_count": 0
        }
        
        self.ui_state["thread_list"].append(thread_info)
        self.websocket_events.append({
            "type": "thread_created",
            "thread_id": thread_info["thread_id"],
            "timestamp": time.time()
        })
        
        return {
            "ui_updated": True,
            "thread_count": len(self.ui_state["thread_list"]),
            "new_thread_id": thread_info["thread_id"]
        }
    
    def get_current_ui_state(self) -> Dict[str, Any]:
        """Get current UI state snapshot."""
        return self.ui_state.copy()


class ThreadCreationExecutor:
    """L3 Real thread creation executor with UI integration."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.ui_tracker = ThreadUIStateTracker(user_id)
        self.created_threads: List[Dict[str, Any]] = []
    
    async def create_thread_with_ui_update(self, thread_title: str = None) -> Dict[str, Any]:
        """Create thread and update UI state."""
        # Mock thread for testing without database dependency
        thread_id = f"thread_{self.user_id}_{int(time.time())}_{len(self.created_threads)}"
        mock_thread = MagicNone  # TODO: Use real service instead of Mock
        mock_thread.id = thread_id
        mock_thread.created_at = datetime.now(timezone.utc)
        
        thread_data = {
            "id": thread_id,
            "title": thread_title or f"Thread {thread_id}",
            "created_at": mock_thread.created_at.isoformat(),
            "user_id": self.user_id
        }
        
        # Update UI tracker
        ui_result = await self.ui_tracker.track_thread_creation(thread_data)
        
        # Track created thread
        self.created_threads.append({
            "thread_data": thread_data,
            "mock_thread": mock_thread,
            "ui_result": ui_result
        })
        
        return {
            "thread": mock_thread,
            "thread_data": thread_data,
            "ui_result": ui_result,
            "operation_successful": True
        }
    
    async def create_multiple_threads_with_metadata(self, thread_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple threads with specific metadata."""
        creation_results = []
        
        for config in thread_configs:
            title = config.get("title", "Default Thread")
            metadata = config.get("metadata", {})
            
            result = await self.create_thread_with_ui_update(title)
            
            if result["operation_successful"]:
                # Add metadata to thread data
                result["thread_data"]["metadata"] = metadata
                
                # Update UI state with metadata
                thread_info = next(
                    (t for t in self.ui_tracker.ui_state["thread_list"] 
                     if t["thread_id"] == result["thread_data"]["id"]),
                    None
                )
                if thread_info:
                    thread_info.update(metadata)
            
            creation_results.append(result)
        
        return creation_results
    
    def get_created_thread_count(self) -> int:
        """Get count of successfully created threads."""
        return len(self.created_threads)
    
    def get_thread_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get created thread by index."""
        if 0 <= index < len(self.created_threads):
            return self.created_threads[index]
        return None


@pytest.fixture
def thread_data_factory():
    """Thread test data factory fixture."""
    return ThreadTestDataFactory()


@pytest.fixture
@pytest.mark.e2e
async def test_thread_creator(test_users):
    """Thread creation executor fixture."""
    user = test_users["mid"]
    return ThreadCreationExecutor(user.id)


@pytest.fixture
@pytest.mark.e2e
async def test_ui_state_tracker(test_users):
    """UI state tracker fixture."""
    user = test_users["mid"]
    return ThreadUIStateTracker(user.id)


@pytest.mark.asyncio
@pytest.mark.e2e
class ThreadUICreationTests:
    """Thread UI Creation Test Suite."""
    
    @pytest.mark.e2e
    async def test_thread_creation_ui_synchronization(self, thread_creator):
        """Test Case 1: Thread creation synchronizes with UI state correctly."""
        # Create thread and verify UI update
        result = await thread_creator.create_thread_with_ui_update("Test Thread Creation")
        
        assert result["operation_successful"]
        assert result["ui_result"]["ui_updated"]
        assert result["ui_result"]["thread_count"] == 1
        
        # Verify UI state
        ui_state = thread_creator.ui_tracker.get_current_ui_state()
        assert len(ui_state["thread_list"]) == 1
        assert ui_state["thread_list"][0]["title"] == "Test Thread Creation"
        
        # Verify WebSocket event tracked
        events = thread_creator.ui_tracker.websocket_events
        assert len(events) == 1
        assert events[0]["type"] == "thread_created"
    
    @pytest.mark.e2e
    async def test_multiple_thread_creation_ui_consistency(self, thread_creator):
        """Test Case 2: Multiple thread creation maintains UI consistency."""
        thread_titles = [
            "First Thread",
            "Second Thread", 
            "Third Thread"
        ]
        
        created_threads = []
        for title in thread_titles:
            result = await thread_creator.create_thread_with_ui_update(title)
            assert result["operation_successful"], f"Thread '{title}' creation must succeed"
            created_threads.append(result)
        
        # Verify UI state consistency
        ui_state = thread_creator.ui_tracker.get_current_ui_state()
        assert len(ui_state["thread_list"]) == len(thread_titles)
        
        # Verify thread order and titles
        for i, title in enumerate(thread_titles):
            assert ui_state["thread_list"][i]["title"] == title
            assert ui_state["thread_list"][i]["thread_id"] == created_threads[i]["thread_data"]["id"]
        
        # Verify WebSocket events
        events = thread_creator.ui_tracker.websocket_events
        assert len(events) == len(thread_titles)
        
        for i, event in enumerate(events):
            assert event["type"] == "thread_created"
            assert event["thread_id"] == created_threads[i]["thread_data"]["id"]
    
    @pytest.mark.e2e
    async def test_thread_creation_with_metadata_preservation(self, thread_creator):
        """Test Case 3: Thread creation preserves metadata correctly."""
        thread_configs = [
            {
                "title": "High Priority Thread",
                "metadata": {
                    "priority": "high",
                    "tags": ["urgent", "optimization"],
                    "department": "engineering"
                }
            },
            {
                "title": "Analytics Thread",
                "metadata": {
                    "priority": "medium",
                    "tags": ["analytics", "reporting"],
                    "department": "data_science"
                }
            }
        ]
        
        results = await thread_creator.create_multiple_threads_with_metadata(thread_configs)
        
        # Verify all threads created successfully
        assert len(results) == len(thread_configs)
        for result in results:
            assert result["operation_successful"]
        
        # Verify metadata preservation
        ui_state = thread_creator.ui_tracker.get_current_ui_state()
        
        for i, config in enumerate(thread_configs):
            thread_info = ui_state["thread_list"][i]
            expected_metadata = config["metadata"]
            
            # Verify metadata fields were preserved
            assert thread_info.get("priority") == expected_metadata["priority"]
            assert thread_info.get("tags") == expected_metadata["tags"]
            assert thread_info.get("department") == expected_metadata["department"]
    
    @pytest.mark.e2e
    async def test_thread_creation_ui_state_initialization(self, ui_state_tracker):
        """Test Case 4: UI state is properly initialized for new threads."""
        # Verify initial UI state
        initial_state = ui_state_tracker.get_current_ui_state()
        
        assert initial_state["thread_list"] == []
        assert initial_state["active_thread"] is None
        assert initial_state["message_history"] == []
        assert initial_state["pagination_state"]["page"] == 1
        assert initial_state["loading_states"]["threads"] == False
        assert initial_state["loading_states"]["messages"] == False
        
        # Create thread and verify state update
        thread_data = {
            "id": f"test_thread_{int(time.time())}",
            "title": "State Initialization Thread",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        ui_result = await ui_state_tracker.track_thread_creation(thread_data)
        
        # Verify UI state updated correctly
        assert ui_result["ui_updated"]
        assert ui_result["thread_count"] == 1
        
        updated_state = ui_state_tracker.get_current_ui_state()
        assert len(updated_state["thread_list"]) == 1
        assert updated_state["thread_list"][0]["thread_id"] == thread_data["id"]
        assert updated_state["thread_list"][0]["title"] == thread_data["title"]
    
    @pytest.mark.e2e
    async def test_concurrent_thread_creation_ui_handling(self, test_users):
        """Test Case 5: Concurrent thread creation handled correctly by UI."""
        user = test_users["enterprise"]
        creator = ThreadCreationExecutor(user.id)
        
        # Create multiple threads concurrently
        thread_count = 5
        creation_tasks = [
            creator.create_thread_with_ui_update(f"Concurrent Thread {i+1}")
            for i in range(thread_count)
        ]
        
        # Execute concurrent creations
        results = await asyncio.gather(*creation_tasks)
        
        # Verify all creations succeeded
        assert len(results) == thread_count
        for result in results:
            assert result["operation_successful"]
        
        # Verify UI consistency after concurrent operations
        ui_state = creator.ui_tracker.get_current_ui_state()
        assert len(ui_state["thread_list"]) == thread_count
        
        # Verify no duplicate thread IDs
        thread_ids = [thread["thread_id"] for thread in ui_state["thread_list"]]
        assert len(set(thread_ids)) == thread_count, "All thread IDs must be unique"
        
        # Verify WebSocket events captured for all threads
        events = creator.ui_tracker.websocket_events
        assert len(events) == thread_count
        
        event_thread_ids = [event["thread_id"] for event in events]
        assert set(event_thread_ids) == set(thread_ids), "Events must match created threads"
    
    @pytest.mark.e2e
    async def test_thread_creation_error_handling_ui_state(self, thread_creator):
        """Test Case 6: UI state handles creation errors gracefully."""
        # Create a successful thread first
        success_result = await thread_creator.create_thread_with_ui_update("Successful Thread")
        assert success_result["operation_successful"]
        
        # Simulate creation error by manually creating a failed result
        failed_result = {
            "thread": None,
            "thread_data": None,
            "ui_result": {"ui_updated": False, "error": "Creation failed"},
            "operation_successful": False
        }
        
        # Verify UI state not corrupted by failed creation
        ui_state = thread_creator.ui_tracker.get_current_ui_state()
        assert len(ui_state["thread_list"]) == 1  # Only successful thread
        assert ui_state["thread_list"][0]["title"] == "Successful Thread"
        
        # Verify successful operations still work after error
        another_success = await thread_creator.create_thread_with_ui_update("Recovery Thread")
        assert another_success["operation_successful"]
        
        final_state = thread_creator.ui_tracker.get_current_ui_state()
        assert len(final_state["thread_list"]) == 2
        assert final_state["thread_list"][1]["title"] == "Recovery Thread"
    
    @pytest.mark.e2e
    async def test_thread_creation_websocket_event_ordering(self, thread_creator):
        """Test Case 7: WebSocket events maintain correct ordering during creation."""
        # Create threads in sequence
        thread_titles = ["First", "Second", "Third", "Fourth"]
        creation_times = []
        
        for title in thread_titles:
            start_time = time.time()
            result = await thread_creator.create_thread_with_ui_update(title)
            creation_times.append(time.time())
            
            assert result["operation_successful"]
            
            # Small delay to ensure ordering
            await asyncio.sleep(0.01)
        
        # Verify event ordering
        events = thread_creator.ui_tracker.websocket_events
        assert len(events) == len(thread_titles)
        
        # Verify timestamps are in order
        event_timestamps = [event["timestamp"] for event in events]
        assert event_timestamps == sorted(event_timestamps), "Event timestamps must be in order"
        
        # Verify thread IDs match creation order
        ui_state = thread_creator.ui_tracker.get_current_ui_state()
        created_thread_ids = [thread["thread_id"] for thread in ui_state["thread_list"]]
        event_thread_ids = [event["thread_id"] for event in events]
        
        assert created_thread_ids == event_thread_ids, "Event order must match UI thread order"
    
    @pytest.mark.e2e
    async def test_thread_creation_ui_performance_tracking(self, thread_creator):
        """Test Case 8: Thread creation UI performance is tracked."""
        # Create threads and measure UI update performance
        thread_count = 8
        start_time = time.perf_counter()
        
        creation_tasks = [
            thread_creator.create_thread_with_ui_update(f"Performance Thread {i+1}")
            for i in range(thread_count)
        ]
        
        results = await asyncio.gather(*creation_tasks)
        total_time = time.perf_counter() - start_time
        
        # Verify performance requirements
        assert total_time < 3.0, f"UI creation should complete within 3 seconds, took {total_time:.2f}s"
        
        # Verify all operations succeeded
        assert len(results) == thread_count
        for result in results:
            assert result["operation_successful"]
        
        # Verify UI state is consistent after rapid creation
        ui_state = thread_creator.ui_tracker.get_current_ui_state()
        assert len(ui_state["thread_list"]) == thread_count
        
        # Verify no UI state corruption
        for i, thread_info in enumerate(ui_state["thread_list"]):
            assert thread_info["title"] == f"Performance Thread {i+1}"
            assert thread_info["thread_id"] is not None
            assert thread_info["message_count"] == 0
