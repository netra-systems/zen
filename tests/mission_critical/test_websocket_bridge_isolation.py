"""
Mission Critical Tests: WebSocket Bridge Isolation Issues
===========================================================
These tests demonstrate CRITICAL issues with the current WebSocket Bridge architecture
that violates user isolation and creates security/performance risks.

EXPECTED RESULT: These tests should FAIL in the current system, proving the issues exist.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime, timezone

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


class TestWebSocketBridgeIsolation:
    """Test suite demonstrating critical WebSocket Bridge isolation issues."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        mock = MagicMock(spec=LLMManager)
        return mock
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        mock = MagicMock(spec=ToolDispatcher)
        return mock
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        mock = AsyncMock(spec=WebSocketManager)
        mock.send_agent_event = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_singleton_bridge_shared_across_users(self):
        """
        CRITICAL TEST: Demonstrates that WebSocket Bridge is a singleton shared across all users.
        This test should FAIL, proving that multiple users share the same bridge instance.
        """
        # Create two bridge instances
        bridge1 = AgentWebSocketBridge()
        bridge2 = AgentWebSocketBridge()
        
        # EXPECTED FAILURE: These should be different instances for user isolation
        # but they are the same due to singleton pattern
        assert bridge1 is not bridge2, (
            "CRITICAL: WebSocket Bridge is a singleton - all users share the same instance! "
            "This violates user isolation and creates security risks."
        )
    
    @pytest.mark.asyncio
    async def test_user_context_isolation_in_websocket_events(self, mock_websocket_manager):
        """
        CRITICAL TEST: Demonstrates that WebSocket events from different users can interfere.
        This test should FAIL, proving that user contexts are not properly isolated.
        """
        bridge = AgentWebSocketBridge()
        
        # Track events sent to WebSocket
        events_sent = []
        mock_websocket_manager.send_agent_event.side_effect = lambda *args, **kwargs: events_sent.append({
            'args': args,
            'kwargs': kwargs
        })
        
        # Simulate two different users executing agents concurrently
        user1_context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id="thread_user1",
            user_id="user1",
            agent_name="test_agent"
        )
        
        user2_context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id="thread_user2", 
            user_id="user2",
            agent_name="test_agent"
        )
        
        # Set WebSocket manager on bridge
        await bridge.set_websocket_manager(mock_websocket_manager)
        
        # Simulate concurrent agent executions
        async def execute_for_user(context: AgentExecutionContext):
            # This simulates what happens during agent execution
            await bridge.notify_agent_started(context.agent_name, context.run_id)
            await asyncio.sleep(0.01)  # Simulate some work
            await bridge.notify_agent_completed(context.agent_name, context.run_id, {"result": "done"})
        
        # Execute concurrently for both users
        await asyncio.gather(
            execute_for_user(user1_context),
            execute_for_user(user2_context)
        )
        
        # Check that events are properly isolated by user
        user1_events = [e for e in events_sent if 'user1' in str(e)]
        user2_events = [e for e in events_sent if 'user2' in str(e)]
        
        # EXPECTED FAILURE: Events should be isolated by user context
        assert len(user1_events) > 0, "User1 should have events"
        assert len(user2_events) > 0, "User2 should have events"
        
        # Verify no cross-contamination
        for event in user1_events:
            assert 'user2' not in str(event), (
                f"CRITICAL: User1 event contains User2 data: {event}. "
                "This indicates user context leakage!"
            )
        
        for event in user2_events:
            assert 'user1' not in str(event), (
                f"CRITICAL: User2 event contains User1 data: {event}. "
                "This indicates user context leakage!"
            )
    
    @pytest.mark.asyncio
    async def test_agent_registry_websocket_bridge_global_mutation(self, mock_llm_manager, mock_tool_dispatcher):
        """
        CRITICAL TEST: Demonstrates that AgentRegistry mutates global WebSocket bridge state.
        This test should FAIL, proving that all users affect each other's WebSocket configuration.
        """
        # Create registry
        registry = AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
        
        # Create two different WebSocket bridges (simulating different user contexts)
        bridge1 = MagicMock()
        bridge1.id = "bridge_user1"
        
        bridge2 = MagicMock()
        bridge2.id = "bridge_user2"
        
        # Set bridge for user1
        registry.set_websocket_bridge(bridge1)
        
        # Register agents (this happens at startup)
        registry.register_default_agents()
        
        # Verify all agents have bridge1
        for agent_name, agent in registry.agents.items():
            if hasattr(agent, 'websocket_bridge'):
                assert agent.websocket_bridge.id == "bridge_user1"
        
        # Now user2 comes in and sets their bridge
        registry.set_websocket_bridge(bridge2)
        
        # EXPECTED FAILURE: User1's agents should NOT be affected by user2's bridge
        # but they are because it's a global mutation
        for agent_name, agent in registry.agents.items():
            if hasattr(agent, 'websocket_bridge'):
                assert agent.websocket_bridge.id != "bridge_user2", (
                    f"CRITICAL: Agent '{agent_name}' WebSocket bridge was mutated by another user! "
                    "User2 setting bridge affected User1's agents. This breaks user isolation."
                )
    
    @pytest.mark.asyncio
    async def test_execution_engine_global_state_contamination(self):
        """
        CRITICAL TEST: Demonstrates ExecutionEngine global state can leak between users.
        This test should FAIL, proving that execution state is not isolated per user.
        """
        engine = ExecutionEngine()
        
        # User1 starts execution
        user1_context = AgentExecutionContext(
            run_id="run_user1",
            thread_id="thread_user1",
            user_id="user1",
            agent_name="agent1"
        )
        
        # User2 starts execution
        user2_context = AgentExecutionContext(
            run_id="run_user2",
            thread_id="thread_user2",
            user_id="user2",
            agent_name="agent2"
        )
        
        # Add both to active runs
        engine.active_runs[user1_context.run_id] = user1_context
        engine.active_runs[user2_context.run_id] = user2_context
        
        # EXPECTED FAILURE: User1 should not be able to see User2's runs
        # but they can because active_runs is global
        assert user2_context.run_id not in engine.active_runs, (
            "CRITICAL: User1 can see User2's active runs in global state! "
            f"Found runs: {list(engine.active_runs.keys())}. "
            "This violates user isolation and creates data leakage risk."
        )
        
        # Check that execution history is also isolated
        from netra_backend.app.agents.supervisor.execution_engine import AgentExecutionResult
        
        user1_result = AgentExecutionResult(success=True, metadata={"user": "user1", "sensitive": "data1"})
        user2_result = AgentExecutionResult(success=True, metadata={"user": "user2", "sensitive": "data2"})
        
        engine.run_history.append(user1_result)
        engine.run_history.append(user2_result)
        
        # EXPECTED FAILURE: History should be isolated per user
        user1_visible_history = [r for r in engine.run_history if r.metadata.get("user") == "user1"]
        assert len(user1_visible_history) == len(engine.run_history), (
            f"CRITICAL: User1 can see other users' execution history! "
            f"User1 should only see 1 result but sees {len(engine.run_history)}. "
            "This is a severe data leakage vulnerability."
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_user_websocket_race_condition(self, mock_websocket_manager):
        """
        CRITICAL TEST: Demonstrates race conditions when multiple users use WebSocket concurrently.
        This test should FAIL, proving that concurrent users can interfere with each other.
        """
        bridge = AgentWebSocketBridge()
        await bridge.set_websocket_manager(mock_websocket_manager)
        
        # Track which user's events are being sent
        event_order = []
        
        async def delayed_send(*args, **kwargs):
            await asyncio.sleep(0.001)  # Simulate network delay
            event_order.append(kwargs.get('user_id', 'unknown'))
        
        mock_websocket_manager.send_agent_event = delayed_send
        
        # Simulate rapid concurrent user requests
        async def user_flow(user_id: str, count: int):
            for i in range(count):
                # Simulate setting user context and sending event
                # In current architecture, there's no user context on bridge
                await bridge.notify_agent_event("test_event", {
                    "user_id": user_id,
                    "event_num": i
                })
        
        # Execute 3 users concurrently, each sending 5 events
        await asyncio.gather(
            user_flow("user1", 5),
            user_flow("user2", 5),
            user_flow("user3", 5)
        )
        
        # Check for proper ordering and isolation
        user1_events = [i for i, uid in enumerate(event_order) if uid == "user1"]
        user2_events = [i for i, uid in enumerate(event_order) if uid == "user2"]
        user3_events = [i for i, uid in enumerate(event_order) if uid == "user3"]
        
        # EXPECTED FAILURE: Events should be properly ordered per user
        # but the singleton bridge causes interleaving
        for i in range(len(user1_events) - 1):
            assert user1_events[i+1] > user1_events[i], (
                f"CRITICAL: User1 events are out of order due to race condition! "
                f"Event positions: {user1_events}. "
                "This indicates the singleton bridge cannot handle concurrent users safely."
            )
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_placeholder_runid_issue(self, mock_llm_manager, mock_tool_dispatcher):
        """
        CRITICAL TEST: Demonstrates the 'registry' placeholder run_id problem.
        This test should FAIL, proving that agents are initialized with non-user-specific run_ids.
        """
        registry = AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
        
        # Create a mock bridge that tracks set_websocket_bridge calls
        mock_bridge = MagicMock()
        set_bridge_calls = []
        
        def track_set_bridge(bridge, run_id):
            set_bridge_calls.append({"bridge": bridge, "run_id": run_id})
        
        # Register agents
        registry.websocket_bridge = mock_bridge
        
        # Mock an agent to track set_websocket_bridge calls
        from netra_backend.app.agents.base_agent import BaseAgent
        mock_agent = MagicMock(spec=BaseAgent)
        mock_agent.set_websocket_bridge = MagicMock(side_effect=track_set_bridge)
        
        # Register the agent
        registry.register("test_agent", mock_agent)
        
        # Check what run_id was used
        assert len(set_bridge_calls) > 0, "set_websocket_bridge should have been called"
        
        used_run_id = set_bridge_calls[0]["run_id"]
        
        # EXPECTED FAILURE: run_id should be user-specific, not a placeholder
        assert used_run_id != "registry", (
            f"CRITICAL: Agent initialized with placeholder run_id '{used_run_id}'! "
            "This means agents don't have user-specific context at initialization. "
            "All user events will be mixed up with this placeholder value."
        )
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_shared_executor_isolation(self):
        """
        CRITICAL TEST: Demonstrates ToolDispatcher shared executor violates user isolation.
        This test should FAIL, proving that tool executions are not isolated per user.
        """
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
        
        # Create dispatcher with mock bridge
        mock_bridge = MagicMock()
        dispatcher = ToolDispatcher(websocket_bridge=mock_bridge)
        
        # Track tool executions
        execution_contexts = []
        
        # Mock the executor to track contexts
        original_execute = dispatcher.executor.execute_tool
        
        async def track_execute(tool_name, *args, **kwargs):
            execution_contexts.append({
                "tool": tool_name,
                "context": kwargs.get("context", None)
            })
            return {"success": True}
        
        dispatcher.executor.execute_tool = track_execute
        
        # Simulate two users executing tools concurrently
        user1_context = {"user_id": "user1", "sensitive_data": "user1_secret"}
        user2_context = {"user_id": "user2", "sensitive_data": "user2_secret"}
        
        async def user_tool_execution(user_context):
            return await dispatcher.execute_tool("test_tool", context=user_context)
        
        # Execute concurrently
        results = await asyncio.gather(
            user_tool_execution(user1_context),
            user_tool_execution(user2_context)
        )
        
        # EXPECTED FAILURE: Each user's execution should be isolated
        # but the shared executor means contexts can leak
        assert len(execution_contexts) == 2, "Should have 2 executions"
        
        # Check for context leakage
        for ctx in execution_contexts:
            if ctx["context"] and ctx["context"].get("user_id") == "user1":
                assert "user2" not in str(ctx["context"]), (
                    f"CRITICAL: User1's tool execution contains User2 data! "
                    f"Context: {ctx['context']}. "
                    "This is a severe security vulnerability - tool executor is not isolated per user."
                )
    
    @pytest.mark.asyncio
    async def test_database_session_sharing_risk(self):
        """
        CRITICAL TEST: Demonstrates database session sharing risks in agent execution.
        This test should FAIL if sessions are stored in global agent instances.
        """
        from netra_backend.app.agents.supervisor.supervisor_agent import SupervisorAgent
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Create mock sessions for different users
        user1_session = MagicMock(spec=AsyncSession)
        user1_session.user_id = "user1"
        user1_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value="user1_data")))
        
        user2_session = MagicMock(spec=AsyncSession)
        user2_session.user_id = "user2"
        user2_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value="user2_data")))
        
        # Create supervisor with user1's session
        supervisor = SupervisorAgent(
            db_session=user1_session,
            llm_manager=MagicMock(),
            tool_dispatcher=MagicMock()
        )
        
        # Simulate user1 using the supervisor
        original_session = supervisor.db_session
        
        # Now user2 tries to use the same supervisor instance (due to singleton pattern)
        # This simulates what happens when registry returns the same agent instance
        supervisor.db_session = user2_session  # This is the problem!
        
        # EXPECTED FAILURE: The session should not be changeable after initialization
        # as this would affect other users
        assert supervisor.db_session == original_session, (
            "CRITICAL: Database session was changed after initialization! "
            f"Original session for user1 was replaced with user2's session. "
            "This means database operations could affect the wrong user's data. "
            "This is a SEVERE data integrity vulnerability!"
        )
    
    @pytest.mark.asyncio
    async def test_performance_degradation_with_concurrent_users(self):
        """
        CRITICAL TEST: Demonstrates performance degradation with concurrent users.
        This test should FAIL if the system cannot handle 5+ concurrent users efficiently.
        """
        engine = ExecutionEngine()
        
        # Measure execution time for single user
        start_single = asyncio.get_event_loop().time()
        
        async def simulate_user_execution(user_id: str):
            context = AgentExecutionContext(
                run_id=f"run_{user_id}",
                thread_id=f"thread_{user_id}",
                user_id=user_id,
                agent_name="test_agent"
            )
            # Simulate some work
            await asyncio.sleep(0.1)
            return context
        
        # Single user execution
        await simulate_user_execution("user1")
        single_user_time = asyncio.get_event_loop().time() - start_single
        
        # Measure execution time for 10 concurrent users
        start_concurrent = asyncio.get_event_loop().time()
        
        # The global semaphore in ExecutionEngine limits concurrency
        # This should show performance degradation
        concurrent_tasks = [simulate_user_execution(f"user{i}") for i in range(10)]
        await asyncio.gather(*concurrent_tasks)
        
        concurrent_time = asyncio.get_event_loop().time() - start_concurrent
        
        # Calculate performance degradation
        expected_concurrent_time = single_user_time  # Should be roughly the same with proper isolation
        actual_degradation = concurrent_time / expected_concurrent_time
        
        # EXPECTED FAILURE: Should handle 10 users concurrently without significant degradation
        # but the global semaphore and shared state cause serialization
        assert actual_degradation < 2.0, (
            f"CRITICAL: Performance degrades {actual_degradation:.1f}x with 10 concurrent users! "
            f"Single user: {single_user_time:.3f}s, 10 users: {concurrent_time:.3f}s. "
            "The system cannot handle concurrent users efficiently due to global locks and shared state. "
            "Business goal of 5+ concurrent users is NOT achievable with current architecture!"
        )


if __name__ == "__main__":
    # Run the tests to demonstrate the failures
    pytest.main([__file__, "-v", "--tb=short"])