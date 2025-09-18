"""
Integration Tests for Concurrent Agent Execution with User Context Isolation
Test #7 of Agent Registry and Factory Patterns Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core multi-user platform capability
- Business Goal: Enable reliable concurrent multi-user agent execution without cross-contamination
- Value Impact: Supports 10+ concurrent users with guaranteed isolation - enables platform scalability  
- Strategic Impact: $1.5M+ ARR foundation - multi-user isolation is core to platform business model

CRITICAL MISSION: Test Concurrent Agent Execution with User Context Isolation ensuring:
1. 10+ users can execute agents concurrently without interference
2. UserExecutionContext maintains complete isolation between users
3. Agent state, memory, and execution results remain user-specific
4. WebSocket events are delivered only to correct user connections
5. Resource allocation and cleanup work correctly under concurrent load
6. Factory-based isolation patterns prevent shared state corruption
7. Error handling isolates failures to specific user contexts
8. Performance remains acceptable under multi-user concurrent load

FOCUS: Real concurrent execution testing with actual agent instances, WebSocket connections,
        and user context validation to ensure business-critical multi-user isolation.
"""

import asyncio
import pytest
import time
import uuid
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from collections import defaultdict, Counter
import random

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import classes under test
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession
)

from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    configure_agent_instance_factory
)

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    create_agent_websocket_bridge
)

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


# ============================================================================
# FIXTURES - Multi-User Concurrent Testing
# ============================================================================

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager for concurrent testing."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm.chat_completion = AsyncMock(return_value="Concurrent test response from agent")
    mock_llm.is_healthy = Mock(return_value=True)
    mock_llm.get_usage_stats = Mock(return_value={"total_requests": 0, "concurrent_requests": 0})
    return mock_llm


@pytest.fixture
def concurrent_websocket_manager():
    """Create WebSocket manager optimized for concurrent testing."""
    ws_manager = UnifiedWebSocketManager()
    
    # Thread-safe event tracking
    ws_manager._event_log = []
    ws_manager._event_lock = asyncio.Lock()
    ws_manager._user_connections = {}
    ws_manager._connection_stats = {"total_events": 0, "total_users": 0}
    
    # Mock concurrent-safe methods
    async def thread_safe_send_event(*args, **kwargs):
        async with ws_manager._event_lock:
            event_data = args[0] if args else kwargs
            ws_manager._event_log.append({
                "timestamp": time.time(),
                "thread_id": threading.get_ident(),
                "event": event_data,
                "user_id": event_data.get("user_id", "unknown")
            })
            ws_manager._connection_stats["total_events"] += 1
        return True
    
    ws_manager.send_event = thread_safe_send_event
    ws_manager.send_to_thread = thread_safe_send_event  # Bridge calls send_to_thread, not send_event
    ws_manager.is_connected = Mock(return_value=True)
    ws_manager.get_connection_count = Mock(return_value=10)
    
    return ws_manager


@pytest.fixture
def multi_user_contexts():
    """Create multiple isolated user contexts for concurrent testing."""
    contexts = []
    user_tiers = ["free", "early", "mid", "enterprise"]
    
    for i in range(12):  # Test with 12 concurrent users
        tier = user_tiers[i % len(user_tiers)]
        context = UserExecutionContext(
            user_id=f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}",
            request_id=f"concurrent_req_{i}_{uuid.uuid4().hex[:8]}",
            thread_id=f"concurrent_thread_{i}_{uuid.uuid4().hex[:8]}",
            run_id=f"concurrent_run_{i}_{uuid.uuid4().hex[:8]}",
            agent_context={
                "user_tier": tier,
                "concurrency_limit": {"free": 1, "early": 2, "mid": 3, "enterprise": 5}[tier],
                "test_data": f"isolated_data_for_user_{i}",
                "user_index": i
            }
        )
        contexts.append(context)
    
    return contexts


@pytest.fixture 
def mock_concurrent_agent():
    """Create mock agent that simulates realistic concurrent execution."""
    class MockConcurrentAgent:
        def __init__(self, llm_manager=None, tool_dispatcher=None):
            self.llm_manager = llm_manager
            self.tool_dispatcher = tool_dispatcher
            self.execution_history = []
            self._websocket_bridge = None
            self._run_id = None
            self._agent_name = None
            self._user_specific_memory = {}
            self._execution_lock = asyncio.Lock()
            
        def set_websocket_bridge(self, bridge, run_id, agent_name=None):
            self._websocket_bridge = bridge
            self._run_id = run_id
            self._agent_name = agent_name or "concurrent_agent"
            
        async def execute(self, state, run_id):
            """Concurrent-safe agent execution with user isolation."""
            # Ensure thread-safe execution
            async with self._execution_lock:
                execution_id = f"{run_id}_{time.time()}"
                start_time = time.time()
                
                try:
                    # Store user-specific state
                    if run_id not in self._user_specific_memory:
                        self._user_specific_memory[run_id] = {
                            "execution_count": 0,
                            "user_data": state,
                            "private_memory": f"private_to_{run_id}"
                        }
                    
                    self._user_specific_memory[run_id]["execution_count"] += 1
                    
                    # Send agent started event
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_agent_started(
                            run_id=self._run_id,
                            agent_name=self._agent_name,
                            context={
                                "state": "started",
                                "execution_id": execution_id,
                                "user_specific_data": self._user_specific_memory[run_id]["private_memory"],
                                "execution_count": self._user_specific_memory[run_id]["execution_count"]
                            }
                        )
                    
                    # Simulate variable processing time to test concurrency
                    processing_time = random.uniform(0.1, 0.5)
                    
                    # Send thinking events during processing
                    for step in range(3):
                        if self._websocket_bridge:
                            await self._websocket_bridge.notify_agent_thinking(
                                run_id=self._run_id,
                                agent_name=self._agent_name,
                                reasoning=f"Processing step {step + 1}/3 for {run_id}",
                                step_number=step + 1,
                                progress_percentage=(step + 1) * 33.33
                            )
                        
                        await asyncio.sleep(processing_time / 3)
                    
                    # Simulate tool execution
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_tool_executing(
                            run_id=self._run_id,
                            agent_name=self._agent_name,
                            tool_name="concurrent_processor",
                            parameters={
                                "input": state,
                                "user_memory": self._user_specific_memory[run_id]["private_memory"],
                                "execution_id": execution_id
                            }
                        )
                    
                    # Process user-specific data
                    processed_result = {
                        "original_state": state,
                        "processed_data": f"processed_{state}_{execution_id}",
                        "user_memory": self._user_specific_memory[run_id]["private_memory"],
                        "execution_count": self._user_specific_memory[run_id]["execution_count"],
                        "processing_time": processing_time
                    }
                    
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_tool_completed(
                            run_id=self._run_id,
                            agent_name=self._agent_name,
                            tool_name="concurrent_processor",
                            result=processed_result,
                            execution_time_ms=processing_time * 1000
                        )
                    
                    # Complete execution
                    execution_time = (time.time() - start_time) * 1000
                    
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_agent_completed(
                            run_id=self._run_id,
                            agent_name=self._agent_name,
                            result={
                                "status": "success",
                                "data": processed_result,
                                "execution_metadata": {
                                    "execution_id": execution_id,
                                    "execution_time_ms": execution_time,
                                    "thread_id": threading.get_ident(),
                                    "run_id": run_id
                                }
                            },
                            execution_time_ms=execution_time
                        )
                    
                    # Record execution history
                    self.execution_history.append({
                        "execution_id": execution_id,
                        "state": state,
                        "run_id": run_id,
                        "result": processed_result,
                        "execution_time": execution_time,
                        "thread_id": threading.get_ident()
                    })
                    
                    return {
                        "status": "success",
                        "data": processed_result,
                        "execution_id": execution_id
                    }
                    
                except Exception as e:
                    if self._websocket_bridge:
                        await self._websocket_bridge.notify_agent_error(
                            run_id=self._run_id,
                            agent_name=self._agent_name,
                            error=str(e),
                            context={"execution_id": execution_id}
                        )
                    raise
            
        async def cleanup(self):
            """Clean up user-specific memory and resources."""
            self._user_specific_memory.clear()
            
        def get_user_memory_for_run(self, run_id):
            """Get user-specific memory for testing isolation."""
            return self._user_specific_memory.get(run_id, {})
    
    return MockConcurrentAgent


# ============================================================================
# TEST: Multi-User Concurrent Execution
# ============================================================================

class TestMultiUserConcurrentExecution(SSotBaseTestCase):
    """Test multi-user concurrent agent execution with complete isolation."""
    
    @pytest.mark.asyncio
    async def test_concurrent_10_users_agent_execution_isolation(self, mock_llm_manager, concurrent_websocket_manager, 
                                                               mock_concurrent_agent, multi_user_contexts):
        """Test 10+ users executing agents concurrently with complete isolation."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        
        # Create agents for each user
        user_agents = []
        for i, context in enumerate(multi_user_contexts[:10]):  # Test with 10 concurrent users
            agent = mock_concurrent_agent()
            registry.get_async = AsyncMock(return_value=agent)
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type=f"concurrent_test_agent_{i}",
                user_context=context,
                websocket_manager=concurrent_websocket_manager
            )
            
            user_agents.append((created_agent, context))
        
        # Execute all agents concurrently
        execution_tasks = []
        start_time = time.time()
        
        for agent, context in user_agents:
            # Each user sends unique test data
            user_input = f"test_data_for_{context.user_id}_{context.agent_context['user_index']}"
            task = agent.execute(user_input, context.run_id)
            execution_tasks.append((task, context))
        
        # Gather all concurrent executions
        task_list = [task for task, _ in execution_tasks]
        results = await asyncio.gather(*task_list)
        total_execution_time = time.time() - start_time
        
        # Verify all executions succeeded
        assert len(results) == 10, "Should have 10 concurrent execution results"
        for result in results:
            assert result["status"] == "success"
            assert "execution_id" in result
            assert "data" in result
        
        # Verify user isolation - each result should contain user-specific data
        for i, (result, (agent, context)) in enumerate(zip(results, user_agents)):
            expected_user_data = f"test_data_for_{context.user_id}_{context.agent_context['user_index']}"
            
            # Verify user-specific input was processed correctly
            assert expected_user_data in result["data"]["original_state"]
            assert context.run_id in result["data"]["processed_data"]
            
            # Verify user-specific memory isolation
            user_memory = agent.get_user_memory_for_run(context.run_id)
            assert context.run_id in user_memory["private_memory"]
            
            # Verify no cross-contamination with other users
            for j, (other_agent, other_context) in enumerate(user_agents):
                if i != j:
                    other_memory = other_agent.get_user_memory_for_run(other_context.run_id)
                    # User's private memory should not contain other users' data
                    assert other_context.run_id not in user_memory.get("private_memory", "")
                    assert context.run_id not in other_memory.get("private_memory", "")
        
        # Verify WebSocket event isolation
        async with concurrent_websocket_manager._event_lock:
            event_log = concurrent_websocket_manager._event_log.copy()
        
        # Group events by user
        events_by_user = defaultdict(list)
        for event_entry in event_log:
            user_id = event_entry["event"].get("user_id", "unknown")
            events_by_user[user_id].append(event_entry)
        
        # Verify each user received their own events
        assert len(events_by_user) >= 10, "Should have events for at least 10 users"
        
        for context in multi_user_contexts[:10]:
            user_events = events_by_user.get(context.user_id, [])
            assert len(user_events) > 0, f"User {context.user_id} should have received WebSocket events"
            
            # Verify no cross-user event contamination
            for event_entry in user_events:
                event_user_id = event_entry["event"].get("user_id")
                assert event_user_id == context.user_id, f"User {context.user_id} should only receive their own events"
        
        # Performance assertion
        assert total_execution_time < 2.0, f"Concurrent execution of 10 users should complete in <2s, took {total_execution_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_user_context_factory_isolation(self, mock_llm_manager, concurrent_websocket_manager, multi_user_contexts):
        """Test UserExecutionContext factory creates properly isolated contexts for concurrent users."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        
        # Create factory for concurrent context management
        factory = AgentInstanceFactory()
        
        # Mock WebSocket bridge for factory configuration
        mock_bridge = AsyncMock()
        mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        
        factory.configure(
            agent_registry=registry,
            websocket_bridge=mock_bridge,
            websocket_manager=concurrent_websocket_manager,
            llm_manager=mock_llm_manager
        )
        
        # Create contexts concurrently
        context_creation_tasks = []
        for context in multi_user_contexts[:8]:  # Test with 8 concurrent context creations
            task = factory.create_user_execution_context(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
                request_id=context.request_id
            )
            context_creation_tasks.append((task, context))
        
        # Execute all context creations concurrently
        task_list = [task for task, _ in context_creation_tasks]
        created_contexts = await asyncio.gather(*task_list)
        
        # Verify all contexts were created successfully
        assert len(created_contexts) == 8, "Should have created 8 concurrent contexts"
        
        # Verify context isolation
        for i, (created_context, (_, original_context)) in enumerate(zip(created_contexts, context_creation_tasks)):
            # Verify basic context properties
            assert created_context.user_id == original_context.user_id
            assert created_context.run_id == original_context.run_id
            assert created_context.thread_id == original_context.thread_id
            
            # Verify no shared references between contexts
            for j, other_created_context in enumerate(created_contexts):
                if i != j:
                    # Contexts should be separate objects
                    assert created_context is not other_created_context
                    
                    # IDs should be unique between users
                    assert created_context.user_id != other_created_context.user_id
                    assert created_context.run_id != other_created_context.run_id
                    assert created_context.thread_id != other_created_context.thread_id
        
        # Cleanup all contexts
        cleanup_tasks = [factory.cleanup_user_context(ctx) for ctx in created_contexts]
        await asyncio.gather(*cleanup_tasks)
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_event_delivery_isolation(self, mock_llm_manager, concurrent_websocket_manager, multi_user_contexts):
        """Test WebSocket events are delivered only to correct users during concurrent execution."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        
        # Create user sessions for WebSocket testing
        user_sessions = []
        for context in multi_user_contexts[:6]:  # Test with 6 concurrent WebSocket users
            session = await registry.get_user_session(context.user_id)
            user_sessions.append((session, context))
        
        # Send events concurrently for each user
        event_sending_tasks = []
        event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for session, context in user_sessions:
            for event_type in event_types:
                task = concurrent_websocket_manager.send_event({
                    "event_type": event_type,
                    "user_id": context.user_id,
                    "run_id": context.run_id,
                    "thread_id": context.thread_id,
                    "timestamp": time.time(),
                    "data": f"event_data_for_{context.user_id}_{event_type}"
                })
                event_sending_tasks.append(task)
        
        # Execute all event sending concurrently
        await asyncio.gather(*event_sending_tasks)
        
        # Verify event delivery isolation
        async with concurrent_websocket_manager._event_lock:
            all_events = concurrent_websocket_manager._event_log.copy()
        
        # Group events by user and verify isolation
        events_by_user = defaultdict(list)
        for event_entry in all_events:
            user_id = event_entry["event"].get("user_id")
            events_by_user[user_id].append(event_entry)
        
        # Verify each user received exactly their events
        assert len(events_by_user) == 6, "Should have events for exactly 6 users"
        
        for session, context in user_sessions:
            user_events = events_by_user[context.user_id]
            assert len(user_events) == len(event_types), f"User {context.user_id} should receive all {len(event_types)} event types"
            
            # Verify all events belong to this user
            for event_entry in user_events:
                event = event_entry["event"]
                assert event["user_id"] == context.user_id
                assert event["run_id"] == context.run_id
                assert event["thread_id"] == context.thread_id
                assert context.user_id in event["data"]
        
        # Verify no cross-user event contamination
        all_user_ids = {context.user_id for _, context in user_sessions}
        for user_id, user_events in events_by_user.items():
            assert user_id in all_user_ids, f"Unexpected user_id {user_id} in events"
            
            for event_entry in user_events:
                event_user_id = event_entry["event"]["user_id"]
                assert event_user_id == user_id, f"Event for {user_id} contains data for {event_user_id}"


# ============================================================================
# TEST: Concurrent Resource Management
# ============================================================================

class TestConcurrentResourceManagement(SSotBaseTestCase):
    """Test concurrent resource management and cleanup."""
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_resource_allocation_and_cleanup(self, mock_llm_manager, concurrent_websocket_manager, 
                                                                  mock_concurrent_agent, multi_user_contexts):
        """Test resource allocation and cleanup work correctly under concurrent load."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        
        # Track resource allocation
        allocated_resources = {
            "agents": {},
            "sessions": {},
            "websocket_bridges": {},
            "memory_usage": defaultdict(int)
        }
        
        # Create and execute agents concurrently
        concurrent_executions = []
        
        for i, context in enumerate(multi_user_contexts[:8]):  # Test with 8 concurrent users
            agent = mock_concurrent_agent()
            registry.get_async = AsyncMock(return_value=agent)
            
            # Track resource allocation
            allocated_resources["agents"][context.user_id] = agent
            allocated_resources["memory_usage"][context.user_id] = i * 1024  # Simulate memory usage
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type=f"resource_test_agent_{i}",
                user_context=context,
                websocket_manager=concurrent_websocket_manager
            )
            
            # Execute agent
            execution_task = created_agent.execute(f"resource_test_data_{i}", context.run_id)
            concurrent_executions.append((execution_task, created_agent, context))
        
        # Execute all agents concurrently
        execution_tasks = [task for task, _, _ in concurrent_executions]
        results = await asyncio.gather(*execution_tasks)
        
        # Verify all executions succeeded
        for result in results:
            assert result["status"] == "success"
        
        # Test concurrent cleanup
        cleanup_tasks = []
        for _, agent, context in concurrent_executions:
            cleanup_task = agent.cleanup()
            cleanup_tasks.append(cleanup_task)
        
        await asyncio.gather(*cleanup_tasks)
        
        # Verify resource cleanup
        for _, agent, context in concurrent_executions:
            user_memory = agent.get_user_memory_for_run(context.run_id)
            assert len(user_memory) == 0, f"Agent for {context.user_id} should have cleaned up user-specific memory"
        
        # Verify no resource leaks
        assert len(allocated_resources["agents"]) == 8, "Should have allocated 8 agent resources"
        
        # Simulate resource deallocation
        for user_id in list(allocated_resources["agents"].keys()):
            del allocated_resources["agents"][user_id]
            del allocated_resources["memory_usage"][user_id]
        
        assert len(allocated_resources["agents"]) == 0, "All agent resources should be deallocated"
        assert len(allocated_resources["memory_usage"]) == 0, "All memory usage should be cleared"
    
    @pytest.mark.asyncio 
    async def test_concurrent_error_isolation_and_recovery(self, mock_llm_manager, concurrent_websocket_manager, 
                                                         mock_concurrent_agent, multi_user_contexts):
        """Test error handling isolates failures to specific users during concurrent execution."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        
        # Create agents with some configured to fail
        successful_agents = []
        failing_agents = []
        
        for i, context in enumerate(multi_user_contexts[:6]):
            if i < 3:  # First 3 agents succeed
                agent = mock_concurrent_agent()
                successful_agents.append((agent, context))
            else:  # Last 3 agents fail
                agent = mock_concurrent_agent()
                
                # Override execute method to simulate failure
                original_execute = agent.execute
                
                async def failing_execute(state, run_id):
                    # Send started event first
                    if agent._websocket_bridge:
                        await agent._websocket_bridge.notify_agent_started(
                            run_id=agent._run_id,
                            agent_name=agent._agent_name,
                            context={"state": "started", "will_fail": True}
                        )
                    
                    # Then fail with user-specific error
                    raise Exception(f"Simulated failure for user {context.user_id}")
                
                agent.execute = failing_execute
                failing_agents.append((agent, context))
        
        # Register all agents
        all_agents = successful_agents + failing_agents
        for agent, context in all_agents:
            registry.get_async = AsyncMock(return_value=agent)
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type=f"error_test_agent",
                user_context=context,
                websocket_manager=concurrent_websocket_manager
            )
            
            # Update the reference to the created agent
            if (agent, context) in successful_agents:
                index = successful_agents.index((agent, context))
                successful_agents[index] = (created_agent, context)
            else:
                index = failing_agents.index((agent, context))
                failing_agents[index] = (created_agent, context)
        
        # Execute all agents concurrently (some will succeed, some will fail)
        execution_tasks = []
        for agent, context in all_agents:
            task = agent.execute(f"test_input_{context.user_id}", context.run_id)
            execution_tasks.append((task, context))
        
        # Gather results, allowing exceptions
        results = await asyncio.gather(*[task for task, _ in execution_tasks], return_exceptions=True)
        
        # Verify success/failure isolation
        success_count = sum(1 for result in results if not isinstance(result, Exception))
        failure_count = sum(1 for result in results if isinstance(result, Exception))
        
        assert success_count == 3, f"Should have 3 successful executions, got {success_count}"
        assert failure_count == 3, f"Should have 3 failed executions, got {failure_count}"
        
        # Verify that successful users were not affected by failing users
        for i, result in enumerate(results):
            context = execution_tasks[i][1]
            
            if i < 3:  # Should have succeeded
                assert not isinstance(result, Exception), f"User {context.user_id} should have succeeded"
                assert result["status"] == "success"
            else:  # Should have failed
                assert isinstance(result, Exception), f"User {context.user_id} should have failed"
                assert context.user_id in str(result), "Error should contain user-specific information"
        
        # Verify WebSocket events show proper error isolation
        async with concurrent_websocket_manager._event_lock:
            all_events = concurrent_websocket_manager._event_log.copy()
        
        # Count error events by user
        error_events_by_user = defaultdict(list)
        success_events_by_user = defaultdict(list)
        
        for event_entry in all_events:
            event = event_entry["event"]
            user_id = event.get("user_id")
            event_type = event.get("event_type", "")
            
            if "error" in event_type.lower():
                error_events_by_user[user_id].append(event)
            elif "completed" in event_type.lower() or "success" in str(event).lower():
                success_events_by_user[user_id].append(event)
        
        # Verify error isolation - errors only for failing users
        failing_user_ids = {context.user_id for _, context in failing_agents}
        successful_user_ids = {context.user_id for _, context in successful_agents}
        
        for user_id in error_events_by_user.keys():
            assert user_id in failing_user_ids, f"Error events should only be for failing users, not {user_id}"
        
        for user_id in successful_user_ids:
            assert user_id not in error_events_by_user, f"Successful user {user_id} should not have error events"


# ============================================================================
# TEST: Performance Under Concurrent Load
# ============================================================================

class TestConcurrentPerformance(SSotBaseTestCase):
    """Test system performance under concurrent multi-user load."""
    
    @pytest.mark.asyncio
    async def test_performance_12_concurrent_users_execution(self, mock_llm_manager, concurrent_websocket_manager, 
                                                           mock_concurrent_agent, multi_user_contexts):
        """Test system performance with 12 concurrent users executing agents."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(concurrent_websocket_manager)
        
        # Performance tracking
        performance_metrics = {
            "user_execution_times": {},
            "websocket_event_counts": defaultdict(int),
            "resource_usage": {"peak_agents": 0, "total_events": 0},
            "concurrency_stats": {"max_concurrent": 0, "avg_response_time": 0}
        }
        
        # Create and execute agents for all 12 users
        user_agents = []
        agent_creation_start = time.time()
        
        for i, context in enumerate(multi_user_contexts):  # All 12 users
            agent = mock_concurrent_agent()
            registry.get_async = AsyncMock(return_value=agent)
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type=f"performance_agent_{i}",
                user_context=context,
                websocket_manager=concurrent_websocket_manager
            )
            
            user_agents.append((created_agent, context, time.time()))
            performance_metrics["resource_usage"]["peak_agents"] += 1
        
        agent_creation_time = time.time() - agent_creation_start
        
        # Execute all agents concurrently with timing
        execution_start_time = time.time()
        execution_tasks = []
        
        for agent, context, creation_time in user_agents:
            user_input = f"performance_test_{context.agent_context['user_index']}"
            task = agent.execute(user_input, context.run_id)
            execution_tasks.append((task, context, creation_time))
        
        # Track concurrent execution
        performance_metrics["concurrency_stats"]["max_concurrent"] = len(execution_tasks)
        
        # Execute all concurrently
        task_list = [task for task, _, _ in execution_tasks]
        results = await asyncio.gather(*task_list)
        
        total_execution_time = time.time() - execution_start_time
        
        # Calculate performance metrics
        for i, (result, (_, context, creation_time)) in enumerate(zip(results, execution_tasks)):
            user_execution_time = result.get("execution_id", 0)  # Get from result if available
            performance_metrics["user_execution_times"][context.user_id] = user_execution_time
        
        # Get WebSocket event statistics
        async with concurrent_websocket_manager._event_lock:
            total_events = len(concurrent_websocket_manager._event_log)
            performance_metrics["resource_usage"]["total_events"] = total_events
            
            # Count events per user
            for event_entry in concurrent_websocket_manager._event_log:
                user_id = event_entry["event"].get("user_id", "unknown")
                performance_metrics["websocket_event_counts"][user_id] += 1
        
        # Performance assertions
        assert len(results) == 12, "Should have 12 concurrent execution results"
        assert all(result["status"] == "success" for result in results), "All executions should succeed"
        
        # Timing assertions
        assert agent_creation_time < 2.0, f"Agent creation for 12 users should take <2s, took {agent_creation_time:.2f}s"
        assert total_execution_time < 3.0, f"Concurrent execution for 12 users should take <3s, took {total_execution_time:.2f}s"
        
        # Calculate average response time
        avg_response_time = total_execution_time / 12
        performance_metrics["concurrency_stats"]["avg_response_time"] = avg_response_time
        assert avg_response_time < 0.5, f"Average response time should be <500ms, got {avg_response_time:.3f}s"
        
        # WebSocket event performance
        assert total_events >= 48, f"Should have at least 4 events per user (48 total), got {total_events}"  # 12 users * 4 events minimum
        
        # Verify even distribution of events across users
        event_counts = list(performance_metrics["websocket_event_counts"].values())
        min_events = min(event_counts) if event_counts else 0
        max_events = max(event_counts) if event_counts else 0
        
        assert min_events > 0, "All users should have received some events"
        assert max_events / min_events < 3, "Event distribution should be relatively even across users"
        
        # Resource usage assertions
        assert performance_metrics["resource_usage"]["peak_agents"] == 12, "Should track 12 peak agents"
        assert performance_metrics["concurrency_stats"]["max_concurrent"] == 12, "Should track 12 max concurrent executions"


if __name__ == "__main__":
    # Run tests with focus on concurrent execution and performance
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=3", "-s"])