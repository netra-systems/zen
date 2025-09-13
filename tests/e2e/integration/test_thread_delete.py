"""Thread Deletion Tests - WebSocket Flow

Focused tests for thread deletion and cleanup operations.

Extracted from test_thread_management_websocket.py for better organization.



BVJ: Proper deletion prevents data corruption and ensures clean thread management.

Segment: All customer tiers. Business Goal: Data integrity and resource management.

Value Impact: Clean thread deletion prevents memory leaks and data corruption.

Strategic Impact: Proper cleanup ensures system stability and performance.

"""



import asyncio

import time

from typing import Any, Dict, List

from shared.isolated_environment import IsolatedEnvironment



import pytest



from netra_backend.app.logging_config import central_logger

from netra_backend.app.schemas.core_enums import WebSocketMessageType

from tests.e2e.config import TEST_USERS

from tests.e2e.fixtures.core.thread_test_fixtures_core import (

    ThreadContextManager,

    ThreadTestDataFactory,

    ThreadWebSocketFixtures,

    test_users,

    thread_context_manager,

    unified_harness,

    ws_thread_fixtures,

)



logger = central_logger.get_logger(__name__)



class ThreadDeletionHandler:

    """Handles thread deletion and cleanup operations."""

    

    def __init__(self, ws_fixtures: ThreadWebSocketFixtures):

        self.ws_fixtures = ws_fixtures

        self.deletion_events: List[Dict[str, Any]] = []

        self.cleanup_operations: List[Dict[str, Any]] = []

    

    async def delete_thread_via_websocket(self, user_id: str, thread_id: str) -> bool:

        """Delete thread via WebSocket and trigger cleanup."""

        # Build and send deletion message

        deletion_message = self.ws_fixtures.build_websocket_message(

            WebSocketMessageType.DELETE_THREAD,

            thread_id=thread_id

        )

        await self.ws_fixtures.send_websocket_message(user_id, deletion_message)

        

        # Perform thread cleanup

        cleanup_success = await self._perform_thread_cleanup(user_id, thread_id)

        

        # Capture deletion event

        self.ws_fixtures.capture_thread_event(

            WebSocketMessageType.THREAD_DELETED,

            user_id,

            thread_id

        )

        

        # Track deletion in local events

        deletion_event = {

            "type": WebSocketMessageType.THREAD_DELETED.value,

            "user_id": user_id,

            "thread_id": thread_id,

            "timestamp": time.time(),

            "payload": {"thread_id": thread_id},

            "cleanup_success": cleanup_success

        }

        self.deletion_events.append(deletion_event)

        

        return cleanup_success

    

    async def _perform_thread_cleanup(self, user_id: str, thread_id: str) -> bool:

        """Perform complete thread cleanup."""

        cleanup_operation = {

            "user_id": user_id,

            "thread_id": thread_id,

            "timestamp": time.time(),

            "operations_performed": []

        }

        

        try:

            # Remove thread context

            context_key = f"{user_id}:{thread_id}"

            if context_key in self.ws_fixtures.thread_contexts:

                del self.ws_fixtures.thread_contexts[context_key]

                cleanup_operation["operations_performed"].append("context_removed")

            

            # Remove thread subscriptions from all connections

            for connection in self.ws_fixtures.active_connections.values():

                if "subscribed_threads" in connection:

                    if thread_id in connection["subscribed_threads"]:

                        connection["subscribed_threads"].discard(thread_id)

                        cleanup_operation["operations_performed"].append("subscription_removed")

            

            # Clean up any WebSocket messages related to this thread

            original_message_count = len(self.ws_fixtures.websocket_messages)

            self.ws_fixtures.websocket_messages = [

                msg for msg in self.ws_fixtures.websocket_messages

                if not (msg.get("message", {}).get("payload", {}).get("thread_id") == thread_id)

            ]

            

            if len(self.ws_fixtures.websocket_messages) < original_message_count:

                cleanup_operation["operations_performed"].append("messages_cleaned")

            

            cleanup_operation["success"] = True

            

        except Exception as e:

            cleanup_operation["success"] = False

            cleanup_operation["error"] = str(e)

            logger.error(f"Thread cleanup failed for {thread_id}: {e}")

        

        self.cleanup_operations.append(cleanup_operation)

        return cleanup_operation["success"]

    

    async def delete_multiple_threads(self, user_id: str, thread_ids: List[str]) -> Dict[str, Any]:

        """Delete multiple threads concurrently."""

        deletion_tasks = [

            self.delete_thread_via_websocket(user_id, thread_id)

            for thread_id in thread_ids

        ]

        

        start_time = time.perf_counter()

        results = await asyncio.gather(*deletion_tasks, return_exceptions=True)

        deletion_time = time.perf_counter() - start_time

        

        successful_deletions = sum(1 for r in results if r is True)

        failed_deletions = len(results) - successful_deletions

        

        return {

            "total_threads": len(thread_ids),

            "successful_deletions": successful_deletions,

            "failed_deletions": failed_deletions,

            "deletion_time": deletion_time,

            "results": results

        }

    

    def get_deletion_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:

        """Get thread deletion events for specific user."""

        return [

            event for event in self.deletion_events

            if event["user_id"] == user_id

        ]

    

    def get_cleanup_operations_for_user(self, user_id: str) -> List[Dict[str, Any]]:

        """Get cleanup operations for specific user."""

        return [

            op for op in self.cleanup_operations

            if op["user_id"] == user_id

        ]

    

    def verify_complete_cleanup(self, user_id: str, thread_id: str) -> Dict[str, bool]:

        """Verify complete cleanup was performed for a thread."""

        context_key = f"{user_id}:{thread_id}"

        

        verification = {

            "context_removed": context_key not in self.ws_fixtures.thread_contexts,

            "subscriptions_removed": True,  # Will check below

            "events_captured": False,

            "messages_cleaned": True  # Will verify below

        }

        

        # Check subscriptions removed from all connections

        for connection in self.ws_fixtures.active_connections.values():

            if "subscribed_threads" in connection and thread_id in connection["subscribed_threads"]:

                verification["subscriptions_removed"] = False

                break

        

        # Check deletion event captured

        deletion_events = self.get_deletion_events_for_user(user_id)

        verification["events_captured"] = any(

            event["thread_id"] == thread_id for event in deletion_events

        )

        

        # Check messages cleaned (verify no messages reference this thread)

        for msg in self.ws_fixtures.websocket_messages:

            if msg.get("message", {}).get("payload", {}).get("thread_id") == thread_id:

                verification["messages_cleaned"] = False

                break

        

        return verification



@pytest.fixture

def deletion_handler(ws_thread_fixtures):

    """Thread deletion handler fixture."""

    return ThreadDeletionHandler(ws_thread_fixtures)



@pytest.fixture

async def threads_for_deletion(ws_thread_fixtures):

    """Fixture providing threads ready for deletion testing."""

    user = TEST_USERS["early"]

    

    # Create connection

    await ws_thread_fixtures.create_authenticated_connection(user.id)

    

    # Create threads to be deleted

    threads = []

    for i in range(3):

        thread_id = f"delete_test_thread_{i}_{user.id}_{int(time.time())}"

        thread_name = f"Deletion Test Thread {i+1}"

        

        # Initialize thread context

        context_key = f"{user.id}:{thread_id}"

        ws_thread_fixtures.thread_contexts[context_key] = {

            "thread_id": thread_id,

            "thread_name": thread_name,

            "created_at": time.time(),

            "messages": [f"message_{j}" for j in range(3)],

            "metadata": {"test": True, "index": i}

        }

        

        # Add thread subscription to connection

        connection = ws_thread_fixtures.active_connections[user.id]

        if "subscribed_threads" not in connection:

            connection["subscribed_threads"] = set()

        connection["subscribed_threads"].add(thread_id)

        

        threads.append({

            "id": thread_id,

            "name": thread_name,

            "context_key": context_key

        })

    

    return {"user": user, "threads": threads}



@pytest.mark.asyncio

@pytest.mark.e2e

async def test_deleted_threads_handled_correctly(threads_for_deletion, deletion_handler):

    """Test deleted threads trigger WebSocket notifications and proper cleanup."""

    user = threads_for_deletion["user"]

    thread_to_delete = threads_for_deletion["threads"][0]

    thread_id = thread_to_delete["id"]

    context_key = thread_to_delete["context_key"]

    

    # Verify thread exists in contexts before deletion

    assert context_key in deletion_handler.ws_fixtures.thread_contexts, \

           "Thread context must exist before deletion"

    

    # Delete thread via WebSocket

    deletion_success = await deletion_handler.delete_thread_via_websocket(user.id, thread_id)

    

    # Verify deletion was successful and cleanup occurred

    assert deletion_success, "Thread deletion must be successful"

    assert context_key not in deletion_handler.ws_fixtures.thread_contexts, \

           "Thread context must be removed after deletion"

    

    # Verify deletion event was captured

    deletion_events = deletion_handler.get_deletion_events_for_user(user.id)

    thread_deletion_events = [

        e for e in deletion_events 

        if e["thread_id"] == thread_id

    ]

    

    assert len(thread_deletion_events) == 1, "Thread deletion must trigger exactly one event"

    assert thread_deletion_events[0]["type"] == WebSocketMessageType.THREAD_DELETED.value, \

           "Deletion event must have correct type"

    assert thread_deletion_events[0]["cleanup_success"], "Cleanup must be successful"



@pytest.mark.asyncio

@pytest.mark.e2e

async def test_thread_deletion_complete_cleanup_verification(threads_for_deletion, deletion_handler):

    """Test thread deletion performs complete cleanup of all references."""

    user = threads_for_deletion["user"]

    thread_to_delete = threads_for_deletion["threads"][1]

    thread_id = thread_to_delete["id"]

    

    # Add some WebSocket messages referencing this thread

    await deletion_handler.ws_fixtures.send_websocket_message(user.id, {

        "type": "test_message",

        "payload": {"thread_id": thread_id, "content": "test"}

    })

    

    # Verify thread has references before deletion

    context_key = f"{user.id}:{thread_id}"

    assert context_key in deletion_handler.ws_fixtures.thread_contexts

    

    connection = deletion_handler.ws_fixtures.active_connections[user.id]

    assert thread_id in connection.get("subscribed_threads", set())

    

    # Delete thread

    deletion_success = await deletion_handler.delete_thread_via_websocket(user.id, thread_id)

    assert deletion_success, "Thread deletion must be successful"

    

    # Verify complete cleanup

    cleanup_verification = deletion_handler.verify_complete_cleanup(user.id, thread_id)

    

    assert cleanup_verification["context_removed"], "Thread context must be completely removed"

    assert cleanup_verification["subscriptions_removed"], "Thread subscriptions must be removed"

    assert cleanup_verification["events_captured"], "Deletion event must be captured"

    assert cleanup_verification["messages_cleaned"], "Related messages must be cleaned"

    

    # Verify cleanup operations were tracked

    cleanup_ops = deletion_handler.get_cleanup_operations_for_user(user.id)

    thread_cleanup_ops = [op for op in cleanup_ops if op["thread_id"] == thread_id]

    

    assert len(thread_cleanup_ops) == 1, "Cleanup operation must be tracked"

    assert thread_cleanup_ops[0]["success"], "Cleanup operation must be successful"

    assert len(thread_cleanup_ops[0]["operations_performed"]) > 0, "Cleanup steps must be recorded"



@pytest.mark.asyncio

@pytest.mark.e2e

async def test_multiple_thread_deletion_performance(threads_for_deletion, deletion_handler):

    """Test deletion of multiple threads performs efficiently."""

    user = threads_for_deletion["user"]

    threads = threads_for_deletion["threads"]

    thread_ids = [thread["id"] for thread in threads]

    

    # Verify all threads exist before deletion

    for thread in threads:

        assert thread["context_key"] in deletion_handler.ws_fixtures.thread_contexts

    

    # Delete all threads concurrently

    deletion_result = await deletion_handler.delete_multiple_threads(user.id, thread_ids)

    

    # Verify performance and success

    assert deletion_result["total_threads"] == len(thread_ids)

    assert deletion_result["successful_deletions"] == len(thread_ids), \

           "All threads must be deleted successfully"

    assert deletion_result["failed_deletions"] == 0, "No deletions should fail"

    assert deletion_result["deletion_time"] < 2.0, \

           f"Deletion should complete within 2 seconds, took {deletion_result['deletion_time']:.2f}s"

    

    # Verify all threads were properly cleaned up

    for thread in threads:

        cleanup_verification = deletion_handler.verify_complete_cleanup(user.id, thread["id"])

        assert all(cleanup_verification.values()), \

               f"Thread {thread['id']} must be completely cleaned up"

    

    # Verify all deletion events captured

    deletion_events = deletion_handler.get_deletion_events_for_user(user.id)

    assert len(deletion_events) == len(thread_ids), "All deletions must generate events"



@pytest.mark.asyncio

@pytest.mark.e2e

async def test_thread_deletion_isolation_across_users(ws_thread_fixtures, deletion_handler):

    """Test thread deletion maintains isolation across different users."""

    user_a = TEST_USERS["free"]

    user_b = TEST_USERS["mid"]

    

    # Create connections for both users

    await ws_thread_fixtures.create_authenticated_connection(user_a.id)

    await ws_thread_fixtures.create_authenticated_connection(user_b.id)

    

    # Create threads for each user

    thread_a_id = f"user_a_thread_{int(time.time())}"

    thread_b_id = f"user_b_thread_{int(time.time())}"

    

    # Initialize thread contexts

    context_a_key = f"{user_a.id}:{thread_a_id}"

    context_b_key = f"{user_b.id}:{thread_b_id}"

    

    ws_thread_fixtures.thread_contexts[context_a_key] = {

        "thread_id": thread_a_id,

        "thread_name": "User A Thread",

        "created_at": time.time(),

        "messages": []

    }

    

    ws_thread_fixtures.thread_contexts[context_b_key] = {

        "thread_id": thread_b_id,

        "thread_name": "User B Thread",

        "created_at": time.time(),

        "messages": []

    }

    

    # Delete User A's thread

    deletion_success = await deletion_handler.delete_thread_via_websocket(user_a.id, thread_a_id)

    assert deletion_success, "User A thread deletion must be successful"

    

    # Verify User A's thread is deleted but User B's thread remains

    assert context_a_key not in ws_thread_fixtures.thread_contexts, \

           "User A thread context must be removed"

    assert context_b_key in ws_thread_fixtures.thread_contexts, \

           "User B thread context must remain intact"

    

    # Verify deletion events are isolated

    user_a_deletions = deletion_handler.get_deletion_events_for_user(user_a.id)

    user_b_deletions = deletion_handler.get_deletion_events_for_user(user_b.id)

    

    assert len(user_a_deletions) == 1, "User A must have one deletion event"

    assert len(user_b_deletions) == 0, "User B must have no deletion events"

    assert user_a_deletions[0]["thread_id"] == thread_a_id, "Deletion event must match User A thread"



@pytest.mark.asyncio

@pytest.mark.e2e

async def test_thread_deletion_error_handling(ws_thread_fixtures, deletion_handler):

    """Test thread deletion handles errors gracefully."""

    user = TEST_USERS["enterprise"]

    

    # Create connection

    await ws_thread_fixtures.create_authenticated_connection(user.id)

    

    # Attempt to delete non-existent thread

    non_existent_thread_id = "non_existent_thread_12345"

    

    # This should complete without throwing exceptions

    deletion_success = await deletion_handler.delete_thread_via_websocket(

        user.id, non_existent_thread_id

    )

    

    # Verify deletion is considered successful (idempotent operation)

    assert deletion_success, "Deletion of non-existent thread should be idempotent"

    

    # Verify cleanup operations were attempted

    cleanup_ops = deletion_handler.get_cleanup_operations_for_user(user.id)

    non_existent_cleanup_ops = [

        op for op in cleanup_ops 

        if op["thread_id"] == non_existent_thread_id

    ]

    

    assert len(non_existent_cleanup_ops) == 1, "Cleanup operation must be tracked"

    

    # Verify deletion event was still captured (for audit purposes)

    deletion_events = deletion_handler.get_deletion_events_for_user(user.id)

    non_existent_deletion_events = [

        e for e in deletion_events 

        if e["thread_id"] == non_existent_thread_id

    ]

    

    assert len(non_existent_deletion_events) == 1, "Deletion event must be captured for audit"



@pytest.mark.asyncio

@pytest.mark.e2e

async def test_thread_deletion_with_active_agent_context(ws_thread_fixtures, deletion_handler:

                                                         thread_context_manager):

    """Test thread deletion properly cleans up active agent contexts."""

    user = TEST_USERS["enterprise"]

    

    # Create connection

    await ws_thread_fixtures.create_authenticated_connection(user.id)

    

    # Create thread with agent context

    thread_id = f"agent_context_thread_{int(time.time())}"

    context_key = f"{user.id}:{thread_id}"

    

    ws_thread_fixtures.thread_contexts[context_key] = {

        "thread_id": thread_id,

        "thread_name": "Agent Context Thread",

        "created_at": time.time(),

        "messages": []

    }

    

    # Add active agent context

    agent_data = {

        "agent_id": "active_agent",

        "status": "executing",

        "execution_state": {

            "step": 5,

            "progress": 0.75,

            "checkpoint_data": {"key": "value"}

        }

    }

    

    await thread_context_manager.preserve_agent_context_in_thread(

        user.id, thread_id, agent_data

    )

    

    # Verify agent context exists

    context = ws_thread_fixtures.thread_contexts[context_key]

    assert "agent_context" in context, "Agent context must exist before deletion"

    

    # Delete thread

    deletion_success = await deletion_handler.delete_thread_via_websocket(user.id, thread_id)

    assert deletion_success, "Thread deletion with agent context must be successful"

    

    # Verify complete cleanup including agent context

    cleanup_verification = deletion_handler.verify_complete_cleanup(user.id, thread_id)

    assert all(cleanup_verification.values()), "All references including agent context must be cleaned"

    

    # Verify context key no longer exists

    assert context_key not in ws_thread_fixtures.thread_contexts, \

           "Thread context with agent data must be completely removed"

