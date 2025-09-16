"""Thread Context Isolation Tests
Focused tests for thread context isolation and agent state management.
Split from test_thread_state_management.py to meet size requirements.

BVJ: Context isolation prevents agent state corruption across threads.
Segment: Mid/Enterprise. Business Goal: Reliability through isolated contexts.
Value Impact: Context isolation prevents cross-thread data corruption.
Strategic Impact: Proper isolation ensures thread independence and data integrity.
"""

import asyncio
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

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


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_agent_context_maintained_per_thread(ws_thread_fixtures, thread_context_manager):
    """Test agent context is maintained per thread without cross-contamination."""
    user = TEST_USERS["enterprise"]
    
    # Create connection and multiple threads
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create threads with contexts
    thread_1_id = f"isolation_thread_1_{user.id}_{int(time.time())}"
    thread_2_id = f"isolation_thread_2_{user.id}_{int(time.time())}"
    
    # Initialize thread contexts
    for thread_id, name in [(thread_1_id, "Optimization Thread"), (thread_2_id, "Analysis Thread")]:
        context_key = f"{user.id}:{thread_id}"
        ws_thread_fixtures.thread_contexts[context_key] = {
            "thread_id": thread_id,
            "thread_name": name,
            "created_at": time.time(),
            "messages": []
        }
    
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
        user.id, thread_1_id, agent_1_data
    )
    await thread_context_manager.preserve_agent_context_in_thread(
        user.id, thread_2_id, agent_2_data
    )
    
    # Verify context isolation
    isolation_verified = thread_context_manager.validate_context_isolation(
        user.id, thread_1_id, thread_2_id
    )
    
    assert isolation_verified, "Thread contexts must remain isolated from each other"
    
    # Verify agent-specific data preservation
    context_1_key = f"{user.id}:{thread_1_id}"
    context_2_key = f"{user.id}:{thread_2_id}"
    
    context_1 = ws_thread_fixtures.thread_contexts[context_1_key]
    context_2 = ws_thread_fixtures.thread_contexts[context_2_key]
    
    assert context_1["agent_context"]["agent_id"] == "optimizer"
    assert context_2["agent_context"]["agent_id"] == "analyzer"
    assert context_1["agent_context"]["execution_state"]["progress"] == 0.7
    assert context_2["agent_context"]["execution_state"]["progress"] == 0.3


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multiple_thread_state_isolation(ws_thread_fixtures, thread_context_manager):
    """Test state isolation across multiple threads for same user."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create multiple threads with different states
    threads = []
    for i in range(3):
        thread_id = f"multi_isolation_thread_{i}_{user.id}_{int(time.time())}"
        context_key = f"{user.id}:{thread_id}"
        
        # Initialize thread context
        ws_thread_fixtures.thread_contexts[context_key] = {
            "thread_id": thread_id,
            "thread_name": f"Isolation Thread {i+1}",
            "created_at": time.time(),
            "messages": []
        }
        
        # Create unique agent context for each thread
        agent_data = {
            "agent_id": f"agent_{i}",
            "status": "active" if i % 2 == 0 else "standby",
            "execution_state": {
                "thread_specific_data": f"data_for_thread_{i}",
                "phase": f"phase_{i}",
                "step": i * 10
            }
        }
        
        await thread_context_manager.preserve_agent_context_in_thread(
            user.id, thread_id, agent_data
        )
        
        threads.append({
            "thread_id": thread_id,
            "context_key": context_key,
            "agent_data": agent_data
        })
    
    # Verify state isolation - each thread should have unique state
    for i, thread in enumerate(threads):
        context = ws_thread_fixtures.thread_contexts[thread["context_key"]]
        agent_context = context["agent_context"]
        
        # Verify thread-specific data
        assert agent_context["agent_id"] == f"agent_{i}"
        assert agent_context["execution_state"]["thread_specific_data"] == f"data_for_thread_{i}"
        assert agent_context["execution_state"]["phase"] == f"phase_{i}"
        assert agent_context["execution_state"]["step"] == i * 10
        
        # Verify no cross-contamination
        for j, other_thread in enumerate(threads):
            if i != j:
                other_context = ws_thread_fixtures.thread_contexts[other_thread["context_key"]]
                other_agent = other_context["agent_context"]
                
                assert agent_context != other_agent, \
                       f"Thread {i} context must be different from thread {j} context"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_thread_isolation_maintained_across_users(ws_thread_fixtures, thread_context_manager):
    """Test thread isolation is maintained across different users."""
    user_a = TEST_USERS["free"]
    user_b = TEST_USERS["mid"]
    
    # Create connections for both users
    await ws_thread_fixtures.create_authenticated_connection(user_a.id)
    await ws_thread_fixtures.create_authenticated_connection(user_b.id)
    
    # Create threads for each user
    thread_a_id = f"user_a_isolation_{user_a.id}_{int(time.time())}"
    thread_b_id = f"user_b_isolation_{user_b.id}_{int(time.time())}"
    
    # Initialize contexts
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
    
    # Add different agent contexts
    agent_a_data = {
        "agent_id": "user_a_agent",
        "status": "active",
        "execution_state": {"user_specific": "data_a", "priority": "high"}
    }
    
    agent_b_data = {
        "agent_id": "user_b_agent",
        "status": "planning",
        "execution_state": {"user_specific": "data_b", "priority": "medium"}
    }
    
    await thread_context_manager.preserve_agent_context_in_thread(
        user_a.id, thread_a_id, agent_a_data
    )
    await thread_context_manager.preserve_agent_context_in_thread(
        user_b.id, thread_b_id, agent_b_data
    )
    
    # Verify contexts are isolated across users
    assert context_a_key in ws_thread_fixtures.thread_contexts
    assert context_b_key in ws_thread_fixtures.thread_contexts
    
    context_a = ws_thread_fixtures.thread_contexts[context_a_key]
    context_b = ws_thread_fixtures.thread_contexts[context_b_key]
    
    # Verify user-specific agent data
    assert context_a["agent_context"]["agent_id"] == "user_a_agent"
    assert context_b["agent_context"]["agent_id"] == "user_b_agent"
    assert context_a["agent_context"]["execution_state"]["user_specific"] == "data_a"
    assert context_b["agent_context"]["execution_state"]["user_specific"] == "data_b"
    
    # Verify no cross-user access
    assert context_a != context_b
    assert context_a["thread_id"] != context_b["thread_id"]


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_context_isolation_under_concurrent_operations(ws_thread_fixtures, thread_context_manager):
    """Test context isolation maintains integrity under concurrent operations."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create multiple threads
    thread_count = 5
    threads = []
    
    for i in range(thread_count):
        thread_id = f"concurrent_isolation_{i}_{user.id}_{int(time.time())}"
        context_key = f"{user.id}:{thread_id}"
        
        ws_thread_fixtures.thread_contexts[context_key] = {
            "thread_id": thread_id,
            "thread_name": f"Concurrent Thread {i+1}",
            "created_at": time.time(),
            "messages": []
        }
        
        threads.append({"thread_id": thread_id, "context_key": context_key})
    
    # Create concurrent context preservation tasks
    context_tasks = []
    for i, thread in enumerate(threads):
        agent_data = {
            "agent_id": f"concurrent_agent_{i}",
            "status": "executing",
            "execution_state": {
                "concurrent_operation": i,
                "timestamp": time.time() + i,  # Unique timestamp
                "data": f"concurrent_data_{i}"
            }
        }
        
        task = thread_context_manager.preserve_agent_context_in_thread(
            user.id, thread["thread_id"], agent_data
        )
        context_tasks.append((task, i, agent_data))
    
    # Execute concurrent operations
    start_time = time.perf_counter()
    results = await asyncio.gather(*[task for task, _, _ in context_tasks])
    execution_time = time.perf_counter() - start_time
    
    # Verify performance
    assert execution_time < 2.0, f"Concurrent isolation should complete quickly, took {execution_time:.2f}s"
    
    # Verify isolation integrity after concurrent operations
    for i, thread in enumerate(threads):
        context = ws_thread_fixtures.thread_contexts[thread["context_key"]]
        agent_context = context["agent_context"]
        
        # Verify each thread maintained its specific data
        assert agent_context["agent_id"] == f"concurrent_agent_{i}"
        assert agent_context["execution_state"]["concurrent_operation"] == i
        assert agent_context["execution_state"]["data"] == f"concurrent_data_{i}"
        
        # Verify no data corruption from other threads
        for j, other_thread in enumerate(threads):
            if i != j:
                other_context = ws_thread_fixtures.thread_contexts[other_thread["context_key"]]
                other_agent = other_context["agent_context"]
                
                # Ensure no cross-contamination
                assert agent_context["agent_id"] != other_agent["agent_id"]
                assert (agent_context["execution_state"]["concurrent_operation"] != 
                        other_agent["execution_state"]["concurrent_operation"])


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_context_isolation_during_rapid_switches(ws_thread_fixtures, thread_context_manager):
    """Test context isolation during rapid thread switching."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create threads with distinct contexts
    threads = []
    for i in range(3):
        thread_id = f"rapid_switch_{i}_{user.id}_{int(time.time())}"
        context_key = f"{user.id}:{thread_id}"
        
        ws_thread_fixtures.thread_contexts[context_key] = {
            "thread_id": thread_id,
            "thread_name": f"Rapid Switch Thread {i+1}",
            "created_at": time.time(),
            "messages": []
        }
        
        # Add unique agent context
        agent_data = {
            "agent_id": f"rapid_agent_{i}",
            "status": "active",
            "execution_state": {
                "switch_test": True,
                "thread_index": i,
                "unique_data": f"rapid_data_{i}_{time.time()}"
            }
        }
        
        await thread_context_manager.preserve_agent_context_in_thread(
            user.id, thread_id, agent_data
        )
        
        threads.append({"thread_id": thread_id, "context_key": context_key, "agent_data": agent_data})
    
    # Perform rapid switching pattern
    switch_pattern = [0, 1, 2, 1, 0, 2, 0]  # Switch between threads rapidly
    
    for switch_index in switch_pattern:
        thread = threads[switch_index]
        
        # Capture snapshot before switch
        before_snapshot = thread_context_manager.capture_context_snapshot(
            user.id, thread["thread_id"], "before_rapid_switch"
        )
        
        # Simulate rapid context access
        context_key = thread["context_key"]
        if context_key in ws_thread_fixtures.thread_contexts:
            context = ws_thread_fixtures.thread_contexts[context_key]
            context["last_accessed"] = time.time()
            context["access_count"] = context.get("access_count", 0) + 1
        
        # Capture snapshot after switch
        after_snapshot = thread_context_manager.capture_context_snapshot(
            user.id, thread["thread_id"], "after_rapid_switch"
        )
        
        # Verify context preservation during rapid access
        preservation_valid = thread_context_manager.verify_context_preservation(
            before_snapshot, after_snapshot
        )
        assert preservation_valid, f"Context must be preserved during rapid switch to thread {switch_index}"
    
    # Final verification - ensure all contexts remain isolated and intact
    for i, thread in enumerate(threads):
        context = ws_thread_fixtures.thread_contexts[thread["context_key"]]
        agent_context = context["agent_context"]
        
        # Verify original data integrity
        assert agent_context["agent_id"] == f"rapid_agent_{i}"
        assert agent_context["execution_state"]["thread_index"] == i
        assert agent_context["execution_state"]["switch_test"] == True
        
        # Verify rapid access tracking
        assert context.get("access_count", 0) > 0, "Thread should have been accessed during rapid switching"
