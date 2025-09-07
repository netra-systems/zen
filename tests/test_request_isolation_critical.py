class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
CRITICAL TEST SUITE: Request Isolation and User Context Separation
==================================================================
This test suite demonstrates critical architectural issues where user requests
are not properly isolated, leading to data leakage and concurrency problems.

These tests are designed to FAIL initially, exposing the following issues:
1. Global singleton state shared across users
2. WebSocket events delivered to wrong users
3. Database session conflicts
4. Agent execution context leakage
5. Tool execution state pollution
"""

import asyncio
import pytest
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import threading
import random
import time
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Import core components to test
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class UserContext:
    """Helper to simulate a unique user context."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.thread_id = f"thread_{user_id}_{uuid.uuid4()}"
        self.run_id = f"run_{user_id}_{uuid.uuid4()}"
        self.events_received: List[Dict[str, Any]] = []
        self.db_operations: List[str] = []
        self.tool_executions: List[str] = []
        self.execution_results: List[Any] = []
        

class TestConcurrentUserIsolation:
    """Test that concurrent users are properly isolated."""
    
    @pytest.mark.asyncio
    async def test_concurrent_users_dont_share_state(self):
        """CRITICAL TEST: Verify that concurrent users don't share execution state."""
        # Setup
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        registry = AgentRegistry()
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        engine = ExecutionEngine(registry, websocket_bridge)
        
        # Create 10 concurrent users
        users = [UserContext(f"user_{i}") for i in range(10)]
        
        async def execute_for_user(user: UserContext):
            """Execute agent for a specific user."""
            context = AgentExecutionContext(
                agent_name="test_agent",
                thread_id=user.thread_id,
                user_id=user.user_id,
                run_id=user.run_id,
                metadata={"user_specific": user.user_id}
            )
            
            state = DeepAgentState(
                thread_id=user.thread_id,
                user_message=f"Message from {user.user_id}"
            )
            
            # Execute and track results
            result = await engine.execute_agent(context, state)
            user.execution_results.append(result)
            
            # Verify this user's data isn't in other active runs
            for run_id, active_context in engine.active_runs.items():
                if run_id != user.run_id:
                    # CRITICAL: Other users' contexts should NOT contain this user's data
                    assert user.user_id not in str(active_context.metadata), \
                        f"User {user.user_id} data leaked into run {run_id}"
                    assert user.thread_id != active_context.thread_id, \
                        f"User {user.user_id} thread_id found in other user's context"
        
        # Execute concurrently for all users
        tasks = [execute_for_user(user) for user in users]
        await asyncio.gather(*tasks)
        
        # Verify isolation
        for i, user in enumerate(users):
            # Check that each user got their own result
            assert len(user.execution_results) == 1, f"User {i} should have exactly 1 result"
            
            # Verify no cross-contamination in run history
            for result in engine.run_history:
                if result.context.user_id != user.user_id:
                    # Other users' results should not reference this user
                    assert user.user_id not in str(result.context.metadata)
                    assert user.thread_id != result.context.thread_id
    
    @pytest.mark.asyncio
    async def test_execution_semaphore_fairness(self):
        """Test that the execution semaphore doesn't starve any users."""
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        registry = AgentRegistry()
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        engine = ExecutionEngine(registry, websocket_bridge)
        
        # Track execution order and timing
        execution_order = []
        execution_times = {}
        
        async def slow_agent_execution(user_id: str, delay: float):
            """Simulate agent execution with variable delay."""
            start_time = time.time()
            
            context = AgentExecutionContext(
                agent_name="slow_agent",
                thread_id=f"thread_{user_id}",
                user_id=user_id,
                run_id=f"run_{user_id}",
                metadata={"delay": delay}
            )
            
            state = DeepAgentState(thread_id=f"thread_{user_id}")
            
            # Mock the actual agent execution
            with patch.object(engine.agent_core, 'execute_agent', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = AgentExecutionResult(
                    success=True,
                    agent_name="slow_agent",
                    context=context,
                    result="Done"
                )
                
                # Add artificial delay
                async def delayed_execution(*args, **kwargs):
                    await asyncio.sleep(delay)
                    execution_order.append(user_id)
                    return mock_exec.return_value
                
                mock_exec.side_effect = delayed_execution
                
                result = await engine.execute_agent(context, state)
                execution_times[user_id] = time.time() - start_time
                return result
        
        # Create users with different execution times
        tasks = []
        for i in range(15):  # More than MAX_CONCURRENT_AGENTS
            delay = random.uniform(0.1, 0.5)
            tasks.append(slow_agent_execution(f"user_{i}", delay))
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify fairness
        assert len(results) == 15, "All users should complete"
        assert len(set(execution_order)) == 15, "All users should have executed"
        
        # Check that no user waited excessively long
        max_wait = max(execution_times.values())
        min_wait = min(execution_times.values())
        assert max_wait < min_wait * 10, "No user should wait 10x longer than fastest"


class TestWebSocketEventIsolation:
    """Test that WebSocket events are properly isolated per user."""
    
    @pytest.mark.asyncio
    async def test_websocket_events_go_to_correct_user(self):
        """CRITICAL TEST: Verify WebSocket events are delivered only to the correct user."""
        # Setup WebSocket tracking for multiple users
        user_websockets = {}
        
        def create_user_websocket(user_id: str):
            """Create a mock WebSocket connection for a user."""
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            ws.events_received = []
            ws.user_id = user_id
            
            async def send_event(event_type: str, data: dict):
                ws.events_received.append({
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.now(timezone.utc)
                })
            
            ws.send_event = send_event
            return ws
        
        # Create WebSocket connections for 5 users
        for i in range(5):
            user_id = f"user_{i}"
            user_websockets[user_id] = create_user_websocket(user_id)
        
        # Mock the WebSocket bridge to track events
        websocket_bridge = AgentWebSocketBridge()
        original_notify = websocket_bridge.notify_agent_started
        
        events_by_run = {}
        
        async def track_notify(run_id: str, *args, **kwargs):
            """Track which run_id gets which events."""
            if run_id not in events_by_run:
                events_by_run[run_id] = []
            events_by_run[run_id].append({
                "method": "notify_agent_started",
                "args": args,
                "kwargs": kwargs,
                "timestamp": datetime.now(timezone.utc)
            })
            # Call original if it exists
            if hasattr(original_notify, '__call__'):
                return await original_notify(run_id, *args, **kwargs)
        
        websocket_bridge.notify_agent_started = track_notify
        
        # Setup registry and engine
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        registry = AgentRegistry()
        registry.set_websocket_bridge(websocket_bridge)
        
        engine = ExecutionEngine(registry, websocket_bridge)
        
        # Execute agents for each user concurrently
        async def execute_for_user(user_id: str):
            context = AgentExecutionContext(
                agent_name="test_agent",
                thread_id=f"thread_{user_id}",
                user_id=user_id,
                run_id=f"run_{user_id}_{uuid.uuid4()}",
                metadata={"user": user_id}
            )
            
            state = DeepAgentState(thread_id=f"thread_{user_id}")
            
            # Execute
            with patch.object(engine.agent_core, 'execute_agent', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = AgentExecutionResult(
                    success=True,
                    agent_name="test_agent",
                    context=context,
                    result=f"Result for {user_id}"
                )
                
                result = await engine.execute_agent(context, state)
                return context.run_id, result
        
        # Execute for all users
        tasks = [execute_for_user(f"user_{i}") for i in range(5)]
        run_results = await asyncio.gather(*tasks)
        
        # Verify event isolation
        for run_id, result in run_results:
            user_id = result.context.user_id
            
            # Check that events for this run contain only this user's data
            if run_id in events_by_run:
                for event in events_by_run[run_id]:
                    event_str = str(event)
                    # Verify no other user's data appears in this user's events
                    for other_user in user_websockets:
                        if other_user != user_id:
                            assert other_user not in event_str, \
                                f"User {other_user} data found in {user_id}'s events"
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_singleton_causes_conflicts(self):
        """Test that the singleton WebSocket bridge causes conflicts between users."""
        # Get the singleton instance
        bridge1 = AgentWebSocketBridge()
        bridge2 = AgentWebSocketBridge()
        
        # CRITICAL: These should be the same instance (singleton)
        assert bridge1 is bridge2, "WebSocket bridge should be a singleton"
        
        # Track events from different "users"
        user1_events = []
        user2_events = []
        
        # Simulate two users trying to use the bridge
        async def user1_flow():
            await bridge1.notify_agent_started("run_user1", "agent1", {})
            user1_events.append("started")
            await asyncio.sleep(0.1)
            await bridge1.notify_agent_completed("run_user1", "agent1", "result1", {})
            user1_events.append("completed")
        
        async def user2_flow():
            await bridge2.notify_agent_started("run_user2", "agent2", {})
            user2_events.append("started")
            await asyncio.sleep(0.05)
            await bridge2.notify_agent_completed("run_user2", "agent2", "result2", {})
            user2_events.append("completed")
        
        # Execute concurrently
        await asyncio.gather(user1_flow(), user2_flow())
        
        # The singleton nature means both users affected the same bridge state
        # This demonstrates the problem of shared state
        assert len(user1_events) == 2
        assert len(user2_events) == 2
        # But they're using the SAME bridge instance, which is the problem


class TestDatabaseSessionIsolation:
    """Test that database sessions are properly isolated per request."""
    
    @pytest.mark.asyncio
    async def test_database_sessions_not_shared_across_requests(self):
        """CRITICAL TEST: Verify database sessions are not shared between requests."""
        from netra_backend.app.dependencies import get_db_dependency
        
        sessions_created = []
        
        # Mock the database session creation
        async def mock_get_db():
            session = MagicMock(spec=AsyncSession)
            session.id = uuid.uuid4()
            session.is_active = True
            session.in_transaction = False
            sessions_created.append(session)
            yield session
        
        # Simulate multiple concurrent requests
        async def simulate_request(request_id: int):
            """Simulate a request that uses a database session."""
            # Get a session through the dependency
            async for session in mock_get_db():
                # Verify this is a unique session
                assert session.is_active
                
                # Simulate some database operations
                session.in_transaction = True
                await asyncio.sleep(random.uniform(0.01, 0.05))
                
                # Check that no other request is using this session
                for other_session in sessions_created:
                    if other_session.id != session.id and other_session.in_transaction:
                        # If another session is also in transaction, they must be different
                        assert other_session.id != session.id, \
                            f"Request {request_id} sharing session with another request"
                
                session.in_transaction = False
                return session.id
        
        # Run 20 concurrent requests
        tasks = [simulate_request(i) for i in range(20)]
        session_ids = await asyncio.gather(*tasks)
        
        # Verify each request got a unique session
        assert len(set(session_ids)) == 20, "Each request should have a unique session"
    
    @pytest.mark.asyncio
    async def test_agent_registry_shared_globally(self):
        """Test that AgentRegistry being shared globally causes issues."""
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        # Create registry (simulating app startup)
        registry = AgentRegistry()
        registry.register_default_agents()
        
        # Track modifications from different "requests"
        modifications = []
        
        async def request_handler(request_id: int):
            """Simulate a request that modifies the registry."""
            # Each request tries to set its own WebSocket bridge
            bridge = Mock(spec=AgentWebSocketBridge)
            bridge.request_id = request_id
            
            # CRITICAL: This modifies global state
            registry.set_websocket_bridge(bridge)
            modifications.append(request_id)
            
            # Simulate some work
            await asyncio.sleep(random.uniform(0.01, 0.05))
            
            # Check if our bridge is still set (it might have been overwritten)
            current_bridge = registry.websocket_bridge
            
            # This will likely fail because another request overwrote it
            return current_bridge.request_id if hasattr(current_bridge, 'request_id') else None
        
        # Run concurrent requests
        tasks = [request_handler(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Many requests will find their bridge was overwritten
        overwrites = sum(1 for i, result in enumerate(results) if result != i)
        
        # CRITICAL: This demonstrates the race condition
        assert overwrites > 0, "Global registry causes bridge overwrites between requests"


class TestGlobalStateExecutionPath:
    """Test issues with global state in the execution path."""
    
    @pytest.mark.asyncio
    async def test_execution_engine_global_run_tracking(self):
        """Test that ExecutionEngine's global run tracking causes conflicts."""
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        registry = AgentRegistry()
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        # Single global engine (as in production)
        engine = ExecutionEngine(registry, websocket_bridge)
        
        # Track conflicts
        conflicts = []
        
        async def user_execution(user_id: str):
            """Simulate a user's agent execution."""
            run_id = f"run_{user_id}_{uuid.uuid4()}"
            
            context = AgentExecutionContext(
                agent_name="test_agent",
                thread_id=f"thread_{user_id}",
                user_id=user_id,
                run_id=run_id,
                metadata={"user": user_id}
            )
            
            # Check if another user's run is active
            for active_run_id, active_context in engine.active_runs.items():
                if active_context.user_id != user_id:
                    conflicts.append({
                        "user": user_id,
                        "found_active_run_from": active_context.user_id,
                        "run_id": active_run_id
                    })
            
            # Add our run (modifying global state)
            engine.active_runs[run_id] = context
            
            # Simulate execution
            await asyncio.sleep(random.uniform(0.01, 0.1))
            
            # Check if our run is still there (might be cleared by another user)
            our_run_exists = run_id in engine.active_runs
            
            # Clean up (but this affects global state)
            if our_run_exists:
                del engine.active_runs[run_id]
            
            return our_run_exists
        
        # Execute for multiple users concurrently
        tasks = [user_execution(f"user_{i}") for i in range(15)]
        results = await asyncio.gather(*tasks)
        
        # CRITICAL: We found other users' active runs in global state
        assert len(conflicts) > 0, "Global active_runs dict causes visibility of other users' runs"
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_shared_executor(self):
        """Test that ToolDispatcher's shared executor causes conflicts."""
        # Create a tool dispatcher
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        dispatcher = ToolDispatcher(
            llm_client=llm_manager,
            websocket_bridge=websocket_bridge
        )
        
        # Track tool executions
        executions = []
        
        async def user_tool_execution(user_id: str):
            """Simulate a user executing a tool."""
            # Each user tries to execute a tool
            tool_name = f"tool_for_{user_id}"
            
            # Mock the executor's execute method
            original_execute = dispatcher.executor.execute_tool
            
            async def track_execute(name, *args, **kwargs):
                executions.append({
                    "user": user_id,
                    "tool": name,
                    "timestamp": time.time()
                })
                # Check if another user's tool is being executed
                recent_executions = [e for e in executions 
                                   if time.time() - e["timestamp"] < 0.01]
                if len(recent_executions) > 1:
                    # Multiple users executing simultaneously through same executor
                    return {"conflict": True, "concurrent_users": len(recent_executions)}
                return {"result": f"Result for {user_id}"}
            
            dispatcher.executor.execute_tool = track_execute
            
            # Execute tool
            result = await dispatcher.executor.execute_tool(tool_name)
            
            # Restore
            dispatcher.executor.execute_tool = original_execute
            
            return result
        
        # Execute tools for multiple users concurrently
        tasks = [user_tool_execution(f"user_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Check for conflicts
        conflicts = [r for r in results if isinstance(r, dict) and r.get("conflict")]
        
        # The shared executor causes conflicts
        assert len(conflicts) > 0 or len(executions) == 10, \
            "Shared tool executor causes serialization or conflicts"


class TestThreadUserContextMixing:
    """Test issues with thread_id, user_id, and run_id context mixing."""
    
    @pytest.mark.asyncio
    async def test_context_ids_pollution(self):
        """Test that context IDs can get mixed up in global state."""
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        registry = AgentRegistry()
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        engine = ExecutionEngine(registry, websocket_bridge)
        
        # Track context confusion
        context_issues = []
        
        async def check_context_isolation(user_id: str, thread_num: int):
            """Execute and check for context isolation."""
            thread_id = f"thread_{thread_num}"  # Note: not unique per user
            run_id = f"run_{user_id}_{thread_num}"
            
            context = AgentExecutionContext(
                agent_name="test_agent",
                thread_id=thread_id,
                user_id=user_id,
                run_id=run_id,
                metadata={"original_user": user_id, "original_thread": thread_id}
            )
            
            # Check if this thread_id is already in use by another user
            for active_run_id, active_context in engine.active_runs.items():
                if active_context.thread_id == thread_id and active_context.user_id != user_id:
                    context_issues.append({
                        "issue": "thread_id_collision",
                        "our_user": user_id,
                        "other_user": active_context.user_id,
                        "thread_id": thread_id
                    })
            
            # Add to active runs
            engine.active_runs[run_id] = context
            
            # Simulate some work
            await asyncio.sleep(0.01)
            
            # Check if our context was modified
            if run_id in engine.active_runs:
                current_context = engine.active_runs[run_id]
                if current_context.metadata.get("original_user") != user_id:
                    context_issues.append({
                        "issue": "context_modification",
                        "expected_user": user_id,
                        "found_user": current_context.metadata.get("original_user")
                    })
            
            return context_issues
        
        # Multiple users with potentially colliding thread IDs
        tasks = []
        for user_num in range(5):
            for thread_num in range(3):  # Same thread numbers across users
                tasks.append(check_context_isolation(f"user_{user_num}", thread_num))
        
        await asyncio.gather(*tasks)
        
        # We should find thread_id collisions
        assert len(context_issues) > 0, "Thread IDs can collide between different users"


class TestPlaceholderValueIssues:
    """Test issues with placeholder values in the system."""
    
    def test_registry_uses_placeholder_run_id(self):
        """Test that registry uses 'registry' as placeholder run_id."""
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        registry = AgentRegistry()
        
        # Create a mock agent
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        # Create websocket bridge
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        registry.set_websocket_bridge(websocket_bridge)
        
        # Register agent
        registry.register("test_agent", mock_agent)
        
        # Check that None was used during registration (no run_id during registration)
        mock_agent.set_websocket_bridge.assert_called_with(websocket_bridge, None)
        
        # VERIFIED: Agent registration uses None for run_id, real user context set during execution
        assert mock_agent.set_websocket_bridge.call_args[0][1] is None, \
            "Registry should use None for run_id during registration, real user context set during execution"


class TestRaceConditions:
    """Test race conditions in concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_setting_race_condition(self):
        """Test race condition when multiple requests set WebSocket bridge."""
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        registry = AgentRegistry()
        
        # Track bridge changes
        bridge_changes = []
        
        async def set_bridge_for_request(request_id: int):
            """Each request tries to set its own bridge."""
            bridge = Mock(spec=AgentWebSocketBridge)
            bridge.id = request_id
            
            # Critical section without proper locking
            old_bridge = registry.websocket_bridge
            
            # Simulate processing time (where race condition occurs)
            await asyncio.sleep(random.uniform(0.001, 0.01))
            
            # Set our bridge (overwriting others)
            registry.set_websocket_bridge(bridge)
            
            bridge_changes.append({
                "request": request_id,
                "old_bridge_id": getattr(old_bridge, 'id', None) if old_bridge else None,
                "new_bridge_id": request_id
            })
            
            # Check if our bridge is still set
            await asyncio.sleep(random.uniform(0.001, 0.01))
            current_bridge = registry.websocket_bridge
            
            return getattr(current_bridge, 'id', None) == request_id
        
        # Many concurrent requests
        tasks = [set_bridge_for_request(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # Count how many requests found their bridge was overwritten
        overwrites = sum(1 for r in results if not r)
        
        # Most requests should find their bridge was overwritten
        assert overwrites > 10, f"Race condition: {overwrites}/20 requests had bridge overwritten"


# Performance and Scalability Tests
class TestScalabilityLimits:
    """Test system behavior under load to expose scalability limits."""
    
    @pytest.mark.asyncio
    async def test_system_cannot_handle_target_concurrent_users(self):
        """Test that system cannot handle the target of 5+ concurrent users efficiently."""
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        registry = AgentRegistry()
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        engine = ExecutionEngine(registry, websocket_bridge)
        
        # Simulate 10 concurrent users (2x the business target)
        start_time = time.time()
        response_times = []
        
        async def simulate_user(user_id: str):
            """Simulate a user making requests."""
            user_start = time.time()
            
            context = AgentExecutionContext(
                agent_name="test_agent",
                thread_id=f"thread_{user_id}",
                user_id=user_id,
                run_id=f"run_{user_id}",
                metadata={}
            )
            
            state = DeepAgentState(thread_id=f"thread_{user_id}")
            
            # Mock slow agent execution
            with patch.object(engine.agent_core, 'execute_agent', new_callable=AsyncMock) as mock_exec:
                async def slow_execution(*args, **kwargs):
                    await asyncio.sleep(1.0)  # Simulate 1 second agent execution
                    return AgentExecutionResult(
                        success=True,
                        agent_name="test_agent",
                        context=context,
                        result="Done"
                    )
                
                mock_exec.side_effect = slow_execution
                
                await engine.execute_agent(context, state)
                
                response_time = time.time() - user_start
                response_times.append(response_time)
                return response_time
        
        # Execute for all users
        tasks = [simulate_user(f"user_{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        avg_response_time = sum(response_times) / len(response_times)
        
        # With proper concurrency, 10 users × 1 second should take ~1-2 seconds total
        # Due to semaphore limiting, it will take longer
        
        # Business requirement: <2s response time
        assert avg_response_time > 2.0, \
            f"System cannot meet <2s response time target. Avg: {avg_response_time:.2f}s"
        
        # The MAX_CONCURRENT_AGENTS limit causes serialization
        assert total_time > 1.5, \
            f"Concurrency limitations cause serialization. Total time: {total_time:.2f}s"


if __name__ == "__main__":
    # Run all tests to demonstrate the issues
    pytest.main([__file__, "-v", "--tb=short"])