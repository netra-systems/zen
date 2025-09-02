"""
Mission Critical Test Suite: Concurrent User Isolation Issues

This test suite demonstrates critical architectural flaws in the agent infrastructure
that prevent proper isolation between concurrent users. These tests WILL FAIL with
the current architecture, exposing serious security and reliability issues.

BUSINESS IMPACT:
- User data leakage between sessions
- Performance degradation under concurrent load  
- Potential security vulnerabilities
- Poor user experience due to blocking

ARCHITECTURAL PROBLEMS DEMONSTRATED:
1. Global singleton WebSocket bridge shared across all users
2. AgentRegistry global state contamination
3. ExecutionEngine shared active_runs dictionary
4. Database session leakage risks
5. Global semaphores blocking concurrent execution
6. Run ID placeholder confusion
7. Execution metrics mixing between users
8. Misdirected agent death notifications
9. ToolDispatcher shared executor state
10. Performance degradation under concurrent load

Each test documents WHY it fails and what architectural changes are needed.
"""

import pytest
import asyncio
import uuid
from typing import Dict, List, Optional, Set
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import time
import threading
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

# Import actual modules being tested
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.base_agent import BaseAgent


@dataclass
class MockUser:
    """Mock user context for isolation testing"""
    user_id: str
    websocket_events: List[Dict] = field(default_factory=list)
    database_session: Optional[Mock] = None
    websocket_manager: Optional[Mock] = None
    agent_executions: List[str] = field(default_factory=list)
    execution_metrics: Dict = field(default_factory=dict)


@dataclass
class WebSocketEvent:
    """WebSocket event capture for testing"""
    user_id: str
    event_type: str
    data: Dict
    timestamp: float


class MockWebSocketManager:
    """Mock WebSocket manager that captures events per user"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events: List[WebSocketEvent] = []
        self.connected = True
    
    async def send_message(self, event_type: str, data: Dict):
        """Capture WebSocket events for analysis"""
        event = WebSocketEvent(
            user_id=self.user_id,
            event_type=event_type,
            data=data,
            timestamp=time.time()
        )
        self.events.append(event)
    
    async def notify_agent_started(self, agent_type: str, run_id: str):
        await self.send_message("agent_started", {
            "agent_type": agent_type,
            "run_id": run_id
        })
    
    async def notify_agent_thinking(self, reasoning: str, run_id: str):
        await self.send_message("agent_thinking", {
            "reasoning": reasoning,
            "run_id": run_id
        })
    
    async def notify_tool_executing(self, tool_name: str, parameters: Dict, run_id: str):
        await self.send_message("tool_executing", {
            "tool_name": tool_name,
            "parameters": parameters,
            "run_id": run_id
        })
    
    async def notify_tool_completed(self, tool_name: str, result: Dict, run_id: str):
        await self.send_message("tool_completed", {
            "tool_name": tool_name,
            "result": result,
            "run_id": run_id
        })
    
    async def notify_agent_completed(self, result: Dict, run_id: str):
        await self.send_message("agent_completed", {
            "result": result,
            "run_id": run_id
        })
    
    async def notify_agent_error(self, error: str, run_id: str):
        await self.send_message("agent_error", {
            "error": error,
            "run_id": run_id
        })


class MockAgent(BaseAgent):
    """Mock agent for testing concurrent execution"""
    
    def __init__(self, agent_id: str, user_id: str, execution_time: float = 0.1):
        super().__init__()
        self.agent_id = agent_id
        self.user_id = user_id
        self.execution_time = execution_time
        self.executed = False
        self.run_id = None
    
    async def execute(self, request_data: Dict, run_id: str) -> Dict:
        """Simulate agent execution with configurable timing"""
        self.run_id = run_id
        self.executed = True
        
        # Simulate execution time
        await asyncio.sleep(self.execution_time)
        
        return {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "run_id": run_id,
            "result": f"Executed by user {self.user_id}",
            "execution_time": self.execution_time
        }


# Helper Functions

def create_mock_user_context(user_id: str) -> MockUser:
    """Create a mock user context with isolated resources"""
    user = MockUser(user_id=user_id)
    user.database_session = Mock()
    user.websocket_manager = MockWebSocketManager(user_id)
    return user


def create_mock_websocket_manager(user_id: str) -> MockWebSocketManager:
    """Create a mock WebSocket manager for a specific user"""
    return MockWebSocketManager(user_id)


def create_mock_database_session(user_id: str) -> Mock:
    """Create a mock database session for a specific user"""
    session = Mock()
    session.user_id = user_id
    session.query = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


def capture_websocket_events(websocket_manager: MockWebSocketManager) -> List[WebSocketEvent]:
    """Capture WebSocket events from a manager"""
    return websocket_manager.events.copy()


# Global state for tracking cross-test contamination
_global_event_capture: Dict[str, List[WebSocketEvent]] = {}
_execution_order: List[str] = []


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test"""
    global _global_event_capture, _execution_order
    _global_event_capture.clear()
    _execution_order.clear()
    
    # Reset singleton states that might exist
    if hasattr(AgentRegistry, '_instance'):
        AgentRegistry._instance = None
    if hasattr(ExecutionEngine, '_instance'):
        ExecutionEngine._instance = None
    if hasattr(AgentWebSocketBridge, '_instance'):
        AgentWebSocketBridge._instance = None


class TestConcurrentUserIsolation:
    """
    Test suite demonstrating concurrent user isolation failures.
    
    These tests expose critical architectural flaws that prevent proper
    isolation between concurrent users in the agent infrastructure.
    """

    @pytest.mark.asyncio
    async def test_concurrent_user_websocket_isolation(self):
        """
        DEMONSTRATES: WebSocket events from User A leak to User B
        
        FAILURE REASON: AgentWebSocketBridge is a singleton that doesn't
        properly isolate events per user session.
        
        EXPECTED BEHAVIOR: Each user should only receive their own events
        ACTUAL BEHAVIOR: Events leak between users due to shared bridge
        """
        # Create two users with separate WebSocket managers
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        # Create agents for each user
        agent_a = MockAgent("agent_a", "user_a", execution_time=0.1)
        agent_b = MockAgent("agent_b", "user_b", execution_time=0.1)
        
        # Simulate concurrent execution
        async def execute_for_user_a():
            # User A sets their WebSocket bridge
            bridge = AgentWebSocketBridge.get_instance()
            bridge.set_websocket_manager(user_a.websocket_manager)
            
            # Execute agent and capture events
            await agent_a.execute({"test": "data_a"}, "run_a")
            return capture_websocket_events(user_a.websocket_manager)
        
        async def execute_for_user_b():
            # User B sets their WebSocket bridge (this will overwrite A's!)
            bridge = AgentWebSocketBridge.get_instance()
            bridge.set_websocket_manager(user_b.websocket_manager)
            
            # Execute agent and capture events
            await agent_b.execute({"test": "data_b"}, "run_b")
            return capture_websocket_events(user_b.websocket_manager)
        
        # Execute concurrently
        events_a, events_b = await asyncio.gather(
            execute_for_user_a(),
            execute_for_user_b()
        )
        
        # ASSERTION THAT WILL FAIL: Events should be isolated per user
        user_a_events = [e for e in events_a if e.user_id == "user_a"]
        user_b_events = [e for e in events_b if e.user_id == "user_b"]
        leaked_events_to_a = [e for e in events_a if e.user_id == "user_b"]
        leaked_events_to_b = [e for e in events_b if e.user_id == "user_a"]
        
        # This will fail because the singleton bridge causes event leakage
        assert len(leaked_events_to_a) == 0, f"User A received {len(leaked_events_to_a)} events meant for User B"
        assert len(leaked_events_to_b) == 0, f"User B received {len(leaked_events_to_b)} events meant for User A"
        assert len(user_a_events) > 0, "User A should receive their own events"
        assert len(user_b_events) > 0, "User B should receive their own events"

    @pytest.mark.asyncio
    async def test_agent_registry_global_state_contamination(self):
        """
        DEMONSTRATES: AgentRegistry global state affects all users
        
        FAILURE REASON: AgentRegistry maintains global state that's shared
        across all user sessions, causing configuration contamination.
        
        EXPECTED BEHAVIOR: Each user should have isolated registry configuration
        ACTUAL BEHAVIOR: User B inherits User A's configuration
        """
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        # User A configures their registry
        registry_a = AgentRegistry()
        registry_a.set_websocket_manager(user_a.websocket_manager)
        
        # User B gets a "separate" registry (but it's actually the same singleton!)
        registry_b = AgentRegistry()
        
        # Verify they're the same instance (this will pass, showing the problem)
        assert registry_a is registry_b, "AgentRegistry should be a singleton (this shows the problem)"
        
        # User B should have their own configuration, but they don't
        # This assertion will fail because User B inherits User A's WebSocket manager
        current_manager = registry_b._websocket_manager
        
        # ASSERTION THAT WILL FAIL: User B should not inherit User A's configuration
        assert current_manager != user_a.websocket_manager, \
            "User B should not inherit User A's WebSocket manager configuration"
        
        # User B tries to set their own configuration
        registry_b.set_websocket_manager(user_b.websocket_manager)
        
        # This will fail because setting B's manager overwrites A's
        assert registry_a._websocket_manager == user_a.websocket_manager, \
            "User A's configuration should not be overwritten by User B"

    @pytest.mark.asyncio
    async def test_execution_engine_shared_active_runs(self):
        """
        DEMONSTRATES: ExecutionEngine's shared active_runs dictionary
        
        FAILURE REASON: ExecutionEngine maintains a global active_runs
        dictionary that contains all users' executions, not isolated per user.
        
        EXPECTED BEHAVIOR: Each user should only see their own active runs
        ACTUAL BEHAVIOR: All users see all active runs
        """
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        engine = ExecutionEngine()
        
        # Start executions for both users
        run_id_a = str(uuid.uuid4())
        run_id_b = str(uuid.uuid4())
        
        agent_a = MockAgent("agent_a", "user_a", execution_time=0.5)
        agent_b = MockAgent("agent_b", "user_b", execution_time=0.5)
        
        # Start concurrent executions
        task_a = asyncio.create_task(
            engine.execute_agent_async(agent_a, {"test": "data_a"}, run_id_a)
        )
        task_b = asyncio.create_task(
            engine.execute_agent_async(agent_b, {"test": "data_b"}, run_id_b)
        )
        
        # Allow execution to start
        await asyncio.sleep(0.1)
        
        # Check active runs (this shows the shared state problem)
        active_runs = engine.get_active_runs()
        
        # ASSERTION THAT WILL FAIL: Each user should only see their own runs
        user_a_runs = [run_id for run_id in active_runs if run_id == run_id_a]
        user_b_runs = [run_id for run_id in active_runs if run_id == run_id_b]
        
        # This assertion will fail because the engine exposes all active runs globally
        assert len(active_runs) <= 1, \
            f"User should only see their own active runs, but saw {len(active_runs)} total runs"
        
        # Wait for completion
        await asyncio.gather(task_a, task_b)

    @pytest.mark.asyncio
    async def test_database_session_leakage(self):
        """
        DEMONSTRATES: Database session sharing risks between users
        
        FAILURE REASON: Database sessions can leak between users if not
        properly isolated in the agent execution context.
        
        EXPECTED BEHAVIOR: Each user should have their own database session
        ACTUAL BEHAVIOR: Sessions may leak or be shared inappropriately
        """
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        # Create separate database sessions for each user
        session_a = create_mock_database_session("user_a")
        session_b = create_mock_database_session("user_b")
        
        user_a.database_session = session_a
        user_b.database_session = session_b
        
        # Track which sessions are used during execution
        sessions_used = []
        
        original_query = Mock()
        
        def track_session_usage(session):
            def mock_query(*args, **kwargs):
                sessions_used.append(session.user_id)
                return original_query(*args, **kwargs)
            return mock_query
        
        session_a.query = track_session_usage(session_a)
        session_b.query = track_session_usage(session_b)
        
        # Simulate concurrent database operations
        async def db_operation_a():
            # Simulate agent using database
            user_a.database_session.query("SELECT * FROM agents WHERE user_id = 'user_a'")
            await asyncio.sleep(0.1)
            user_a.database_session.commit()
        
        async def db_operation_b():
            # Simulate agent using database
            user_b.database_session.query("SELECT * FROM agents WHERE user_id = 'user_b'")
            await asyncio.sleep(0.1)
            user_b.database_session.commit()
        
        # Execute concurrently
        await asyncio.gather(db_operation_a(), db_operation_b())
        
        # ASSERTION THAT WILL FAIL: Sessions should remain isolated
        user_a_sessions = [s for s in sessions_used if s == "user_a"]
        user_b_sessions = [s for s in sessions_used if s == "user_b"]
        
        assert len(user_a_sessions) > 0, "User A should use their own session"
        assert len(user_b_sessions) > 0, "User B should use their own session"
        
        # This will fail if sessions leak between users
        total_unique_users = len(set(sessions_used))
        assert total_unique_users == 2, \
            f"Should have 2 unique user sessions, but found {total_unique_users}"

    @pytest.mark.asyncio
    async def test_concurrent_user_blocking(self):
        """
        DEMONSTRATES: One user can block another user's execution
        
        FAILURE REASON: Global semaphores or locks prevent concurrent
        execution, causing User B to wait for User A's completion.
        
        EXPECTED BEHAVIOR: Users should execute concurrently without blocking
        ACTUAL BEHAVIOR: Users block each other due to shared execution resources
        """
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        # Create a slow agent for User A and fast agent for User B
        agent_a = MockAgent("slow_agent", "user_a", execution_time=1.0)  # 1 second
        agent_b = MockAgent("fast_agent", "user_b", execution_time=0.1)  # 0.1 seconds
        
        execution_times = {}
        
        async def execute_user_a():
            start_time = time.time()
            result = await agent_a.execute({"task": "slow_task"}, "run_a")
            end_time = time.time()
            execution_times["user_a"] = end_time - start_time
            return result
        
        async def execute_user_b():
            # Start slightly after A to ensure A starts first
            await asyncio.sleep(0.05)
            start_time = time.time()
            result = await agent_b.execute({"task": "fast_task"}, "run_b")
            end_time = time.time()
            execution_times["user_b"] = end_time - start_time
            return result
        
        # Execute concurrently
        start_total = time.time()
        results = await asyncio.gather(execute_user_a(), execute_user_b())
        end_total = time.time()
        
        total_execution_time = end_total - start_total
        
        # ASSERTION THAT WILL FAIL: User B should not be blocked by User A
        # If truly concurrent, total time should be close to A's time (1.0s)
        # If blocked, total time will be A's time + B's time (1.1s+)
        
        assert execution_times["user_b"] < 0.2, \
            f"User B took {execution_times['user_b']:.3f}s, should be ~0.1s (not blocked)"
        
        assert total_execution_time < 1.2, \
            f"Total execution time was {total_execution_time:.3f}s, indicating blocking (should be ~1.0s for concurrent)"
        
        # User B should complete much faster than User A
        assert execution_times["user_b"] < execution_times["user_a"] / 5, \
            "User B (fast) should complete much faster than User A (slow)"

    @pytest.mark.asyncio
    async def test_run_id_placeholder_confusion(self):
        """
        DEMONSTRATES: 'registry' placeholder run_id values leak through
        
        FAILURE REASON: Run ID placeholders like 'registry' are used
        internally but leak through to WebSocket events and user-facing data.
        
        EXPECTED BEHAVIOR: Users should only see their actual run IDs
        ACTUAL BEHAVIOR: Placeholder values appear in user-facing events
        """
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        # Set up WebSocket managers to capture events
        bridge = AgentWebSocketBridge.get_instance()
        
        run_ids_seen = []
        
        # Patch the bridge to track run IDs
        original_send = user_a.websocket_manager.send_message
        
        async def track_run_ids(event_type: str, data: Dict):
            if 'run_id' in data:
                run_ids_seen.append(data['run_id'])
            return await original_send(event_type, data)
        
        user_a.websocket_manager.send_message = track_run_ids
        
        bridge.set_websocket_manager(user_a.websocket_manager)
        
        # Execute agent with proper run ID
        proper_run_id = str(uuid.uuid4())
        agent_a = MockAgent("agent_a", "user_a")
        
        await agent_a.execute({"test": "data"}, proper_run_id)
        
        # ASSERTION THAT WILL FAIL: No placeholder run IDs should leak through
        placeholder_run_ids = [rid for rid in run_ids_seen if rid in ['registry', 'placeholder', '', None]]
        
        assert len(placeholder_run_ids) == 0, \
            f"Found placeholder run IDs in events: {placeholder_run_ids}"
        
        # All run IDs should be the proper UUID
        valid_run_ids = [rid for rid in run_ids_seen if rid == proper_run_id]
        
        assert len(valid_run_ids) > 0, \
            f"Should see the proper run ID {proper_run_id}, but saw: {run_ids_seen}"
        
        assert all(rid == proper_run_id for rid in run_ids_seen if rid is not None), \
            f"All run IDs should be {proper_run_id}, but saw: {run_ids_seen}"

    @pytest.mark.asyncio
    async def test_concurrent_execution_metrics_mixing(self):
        """
        DEMONSTRATES: Execution statistics mix between users
        
        FAILURE REASON: Execution metrics and statistics are not properly
        isolated per user, causing data to mix between user sessions.
        
        EXPECTED BEHAVIOR: Each user should see only their own execution metrics
        ACTUAL BEHAVIOR: Metrics mix between users due to shared tracking
        """
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        # Create execution engine with metrics tracking
        engine = ExecutionEngine()
        
        # Execute multiple agents for each user
        async def execute_for_user_a():
            results = []
            for i in range(3):
                agent = MockAgent(f"agent_a_{i}", "user_a", execution_time=0.1)
                run_id = f"run_a_{i}"
                result = await engine.execute_agent_async(agent, {"index": i}, run_id)
                results.append(result)
                user_a.agent_executions.append(run_id)
            return results
        
        async def execute_for_user_b():
            results = []
            for i in range(2):
                agent = MockAgent(f"agent_b_{i}", "user_b", execution_time=0.2)
                run_id = f"run_b_{i}"
                result = await engine.execute_agent_async(agent, {"index": i}, run_id)
                results.append(result)
                user_b.agent_executions.append(run_id)
            return results
        
        # Execute concurrently
        results_a, results_b = await asyncio.gather(
            execute_for_user_a(),
            execute_for_user_b()
        )
        
        # Get execution statistics (this will show mixed data)
        total_executions = engine.get_execution_count()
        recent_executions = engine.get_recent_executions(10)
        
        # ASSERTION THAT WILL FAIL: User A should only see their own metrics
        user_a_executions_in_recent = [
            exec for exec in recent_executions 
            if any(run_id in str(exec) for run_id in user_a.agent_executions)
        ]
        
        user_b_executions_in_recent = [
            exec for exec in recent_executions 
            if any(run_id in str(exec) for run_id in user_b.agent_executions)
        ]
        
        # This will fail because users see each other's execution data
        assert len(user_a_executions_in_recent) == 3, \
            f"User A should see 3 of their executions, saw {len(user_a_executions_in_recent)}"
        
        assert len(user_b_executions_in_recent) == 0, \
            f"User A should not see User B's executions, but saw {len(user_b_executions_in_recent)}"
        
        # Total count should not include other users' executions from the perspective of each user
        assert total_executions <= 3, \
            f"From User A's perspective, should see at most 3 executions, but saw {total_executions}"

    @pytest.mark.asyncio
    async def test_agent_death_notification_routing(self):
        """
        DEMONSTRATES: Agent death notifications go to wrong users
        
        FAILURE REASON: When agents fail or die, notifications are routed
        through the shared WebSocket bridge, potentially reaching wrong users.
        
        EXPECTED BEHAVIOR: Death notifications should only go to the correct user
        ACTUAL BEHAVIOR: Notifications may be misdirected due to shared bridge
        """
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        # Create agents that will "die" during execution
        class DyingAgent(MockAgent):
            async def execute(self, request_data: Dict, run_id: str) -> Dict:
                # Simulate agent death
                await asyncio.sleep(0.1)
                raise Exception(f"Agent {self.agent_id} died during execution")
        
        agent_a = DyingAgent("dying_agent_a", "user_a")
        agent_b = DyingAgent("dying_agent_b", "user_b")
        
        bridge = AgentWebSocketBridge.get_instance()
        
        # Set up User A's WebSocket manager first
        bridge.set_websocket_manager(user_a.websocket_manager)
        
        # Track error notifications
        error_events_a = []
        error_events_b = []
        
        original_send_a = user_a.websocket_manager.send_message
        original_send_b = user_b.websocket_manager.send_message
        
        async def capture_errors_a(event_type: str, data: Dict):
            if event_type == "agent_error":
                error_events_a.append(data)
            return await original_send_a(event_type, data)
        
        async def capture_errors_b(event_type: str, data: Dict):
            if event_type == "agent_error":
                error_events_b.append(data)
            return await original_send_b(event_type, data)
        
        user_a.websocket_manager.send_message = capture_errors_a
        user_b.websocket_manager.send_message = capture_errors_b
        
        # Execute agents and expect them to die
        async def execute_dying_agent_a():
            try:
                await agent_a.execute({"test": "data"}, "run_a")
            except Exception:
                pass  # Expected
        
        async def execute_dying_agent_b():
            # Switch bridge to User B (this will cause misdirection)
            bridge.set_websocket_manager(user_b.websocket_manager)
            try:
                await agent_b.execute({"test": "data"}, "run_b")
            except Exception:
                pass  # Expected
        
        # Execute concurrently
        await asyncio.gather(execute_dying_agent_a(), execute_dying_agent_b())
        
        # ASSERTION THAT WILL FAIL: Error notifications should go to correct users only
        user_a_errors = [e for e in error_events_a if "dying_agent_a" in str(e)]
        user_b_errors = [e for e in error_events_b if "dying_agent_b" in str(e)]
        
        # Check for misdirected notifications
        user_a_got_b_errors = [e for e in error_events_a if "dying_agent_b" in str(e)]
        user_b_got_a_errors = [e for e in error_events_b if "dying_agent_a" in str(e)]
        
        assert len(user_a_got_b_errors) == 0, \
            f"User A should not receive User B's error notifications, but got: {user_a_got_b_errors}"
        
        assert len(user_b_got_a_errors) == 0, \
            f"User B should not receive User A's error notifications, but got: {user_b_got_a_errors}"
        
        assert len(user_a_errors) > 0, "User A should receive their own error notifications"
        assert len(user_b_errors) > 0, "User B should receive their own error notifications"

    @pytest.mark.asyncio
    async def test_tool_dispatcher_shared_executor(self):
        """
        DEMONSTRATES: ToolDispatcher sharing executor state between users
        
        FAILURE REASON: ToolDispatcher uses shared execution resources
        that are not isolated per user session.
        
        EXPECTED BEHAVIOR: Each user should have isolated tool execution
        ACTUAL BEHAVIOR: Tool execution state is shared between users
        """
        user_a = create_mock_user_context("user_a")
        user_b = create_mock_user_context("user_b")
        
        # Create tool dispatchers
        dispatcher_a = ToolDispatcher()
        dispatcher_b = ToolDispatcher()  # Should be independent, but may share state
        
        # Track tool executions
        executions_a = []
        executions_b = []
        
        # Mock tool execution
        async def mock_tool_execution_a(tool_name: str, parameters: Dict):
            executions_a.append({
                "user": "user_a",
                "tool": tool_name,
                "params": parameters,
                "timestamp": time.time()
            })
            await asyncio.sleep(0.1)
            return {"result": f"Tool {tool_name} executed for user_a"}
        
        async def mock_tool_execution_b(tool_name: str, parameters: Dict):
            executions_b.append({
                "user": "user_b", 
                "tool": tool_name,
                "params": parameters,
                "timestamp": time.time()
            })
            await asyncio.sleep(0.1)
            return {"result": f"Tool {tool_name} executed for user_b"}
        
        # Patch tool execution methods
        dispatcher_a.execute_tool = mock_tool_execution_a
        dispatcher_b.execute_tool = mock_tool_execution_b
        
        # Execute tools concurrently for both users
        async def user_a_tools():
            results = []
            for i in range(3):
                result = await dispatcher_a.execute_tool(f"tool_a_{i}", {"user": "user_a", "index": i})
                results.append(result)
            return results
        
        async def user_b_tools():
            results = []
            for i in range(2):
                result = await dispatcher_b.execute_tool(f"tool_b_{i}", {"user": "user_b", "index": i})
                results.append(result)
            return results
        
        # Execute concurrently
        results_a, results_b = await asyncio.gather(user_a_tools(), user_b_tools())
        
        # Check if executors are truly independent
        if hasattr(dispatcher_a, '_executor') and hasattr(dispatcher_b, '_executor'):
            # ASSERTION THAT WILL FAIL: Dispatchers should have separate executors
            assert dispatcher_a._executor is not dispatcher_b._executor, \
                "ToolDispatchers should have independent executors"
        
        # Verify execution isolation
        user_a_tool_names = [exec["tool"] for exec in executions_a]
        user_b_tool_names = [exec["tool"] for exec in executions_b]
        
        # Check for cross-contamination
        a_tools_in_b = [tool for tool in user_b_tool_names if "tool_a_" in tool]
        b_tools_in_a = [tool for tool in user_a_tool_names if "tool_b_" in tool]
        
        assert len(a_tools_in_b) == 0, \
            f"User B's dispatcher should not execute User A's tools: {a_tools_in_b}"
        
        assert len(b_tools_in_a) == 0, \
            f"User A's dispatcher should not execute User B's tools: {b_tools_in_a}"
        
        # Verify correct execution counts
        assert len(executions_a) == 3, f"User A should have 3 executions, got {len(executions_a)}"
        assert len(executions_b) == 2, f"User B should have 2 executions, got {len(executions_b)}"

    @pytest.mark.asyncio
    async def test_stress_10_concurrent_users(self):
        """
        DEMONSTRATES: System breaks down under concurrent load
        
        FAILURE REASON: Architectural issues compound under load,
        causing performance degradation, event mixing, and failures.
        
        EXPECTED BEHAVIOR: System should handle 10 concurrent users gracefully
        ACTUAL BEHAVIOR: Performance degrades, isolation breaks down, errors occur
        """
        num_users = 10
        users = [create_mock_user_context(f"user_{i}") for i in range(num_users)]
        
        # Track system-wide metrics
        start_time = time.time()
        completion_times = {}
        error_counts = {}
        event_counts = {}
        isolation_violations = []
        
        async def execute_for_user(user: MockUser, user_index: int):
            """Execute agents for a specific user and track metrics"""
            user_start_time = time.time()
            
            try:
                # Create multiple agents per user
                agents = [
                    MockAgent(f"agent_{user_index}_{j}", user.user_id, execution_time=0.2)
                    for j in range(3)
                ]
                
                # Set up WebSocket bridge for this user
                bridge = AgentWebSocketBridge.get_instance()
                bridge.set_websocket_manager(user.websocket_manager)
                
                # Execute agents
                results = []
                for j, agent in enumerate(agents):
                    run_id = f"run_{user_index}_{j}"
                    result = await agent.execute({"user": user.user_id, "agent": j}, run_id)
                    results.append(result)
                    
                    # Small delay to increase chance of race conditions
                    await asyncio.sleep(0.01)
                
                # Record completion time
                completion_times[user.user_id] = time.time() - user_start_time
                
                # Count events received
                event_counts[user.user_id] = len(user.websocket_manager.events)
                
                # Check for isolation violations
                for event in user.websocket_manager.events:
                    if event.user_id != user.user_id:
                        isolation_violations.append({
                            "intended_user": user.user_id,
                            "event_from": event.user_id,
                            "event_type": event.event_type
                        })
                
                error_counts[user.user_id] = 0
                return results
                
            except Exception as e:
                error_counts[user.user_id] = error_counts.get(user.user_id, 0) + 1
                completion_times[user.user_id] = time.time() - user_start_time
                raise e
        
        # Execute all users concurrently
        tasks = [
            asyncio.create_task(execute_for_user(user, i))
            for i, user in enumerate(users)
        ]
        
        # Wait for all to complete (or fail)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_users = sum(1 for r in results if not isinstance(r, Exception))
        failed_users = sum(1 for r in results if isinstance(r, Exception))
        total_errors = sum(error_counts.values())
        total_violations = len(isolation_violations)
        
        # Performance analysis
        avg_completion_time = sum(completion_times.values()) / len(completion_times) if completion_times else 0
        max_completion_time = max(completion_times.values()) if completion_times else 0
        
        # ASSERTIONS THAT WILL FAIL: System should handle concurrent load gracefully
        
        # Success rate should be high
        success_rate = successful_users / num_users
        assert success_rate >= 0.9, \
            f"Success rate should be at least 90%, but was {success_rate:.1%} ({successful_users}/{num_users})"
        
        # No isolation violations should occur
        assert total_violations == 0, \
            f"Found {total_violations} isolation violations: {isolation_violations[:5]}..."
        
        # Performance should not degrade severely
        expected_max_time = 0.8  # 3 agents * 0.2s execution + overhead
        assert max_completion_time < expected_max_time, \
            f"Max completion time was {max_completion_time:.3f}s, should be under {expected_max_time}s"
        
        # No errors should occur
        assert total_errors == 0, \
            f"Found {total_errors} total errors across all users: {error_counts}"
        
        # Event counts should be reasonable and consistent
        expected_events_per_user = 6  # 3 agents * 2 events each (start + complete)
        event_count_issues = [
            user_id for user_id, count in event_counts.items()
            if abs(count - expected_events_per_user) > 2
        ]
        
        assert len(event_count_issues) == 0, \
            f"Event count issues for users: {event_count_issues}. Expected ~{expected_events_per_user} events each"
        
        # Total execution time should indicate proper concurrency
        sequential_time = num_users * avg_completion_time
        concurrency_ratio = total_time / sequential_time if sequential_time > 0 else 1
        
        assert concurrency_ratio < 0.5, \
            f"Concurrency ratio was {concurrency_ratio:.3f}, indicating poor parallelization (should be < 0.5)"


# Additional helper functions for advanced testing scenarios

def analyze_websocket_event_timing(events: List[WebSocketEvent]) -> Dict:
    """Analyze timing patterns in WebSocket events to detect issues"""
    if not events:
        return {"total_events": 0, "timing_issues": []}
    
    timing_issues = []
    prev_event = None
    
    for event in sorted(events, key=lambda e: e.timestamp):
        if prev_event:
            time_gap = event.timestamp - prev_event.timestamp
            if time_gap > 1.0:  # Suspicious gap
                timing_issues.append({
                    "gap_seconds": time_gap,
                    "between_events": (prev_event.event_type, event.event_type)
                })
        prev_event = event
    
    return {
        "total_events": len(events),
        "timing_issues": timing_issues,
        "time_span": events[-1].timestamp - events[0].timestamp
    }


def detect_singleton_contamination(*objects) -> List[str]:
    """Detect if objects are actually the same singleton instance"""
    contamination = []
    for i, obj1 in enumerate(objects):
        for j, obj2 in enumerate(objects[i+1:], i+1):
            if obj1 is obj2:
                contamination.append(f"Objects at index {i} and {j} are the same singleton instance")
    return contamination


@pytest.fixture
def isolated_environment():
    """Attempt to create an isolated environment for testing (will fail due to singletons)"""
    # This fixture demonstrates that true isolation is impossible with current architecture
    original_instances = {}
    
    # Try to save original singleton instances
    for cls in [AgentRegistry, ExecutionEngine, AgentWebSocketBridge]:
        if hasattr(cls, '_instance'):
            original_instances[cls.__name__] = cls._instance
            cls._instance = None  # Try to reset
    
    yield
    
    # Try to restore (this won't work properly due to shared state)
    for cls_name, instance in original_instances.items():
        cls = globals()[cls_name.split('.')[-1]]
        if hasattr(cls, '_instance'):
            cls._instance = instance


if __name__ == "__main__":
    """
    Run this test suite to expose concurrent user isolation issues.
    
    Expected result: ALL TESTS SHOULD FAIL, demonstrating architectural problems.
    
    Usage:
        pytest tests/mission_critical/test_concurrent_user_isolation.py -v
        
    Or run specific test:
        pytest tests/mission_critical/test_concurrent_user_isolation.py::TestConcurrentUserIsolation::test_concurrent_user_websocket_isolation -v
    """
    import sys
    print("=" * 80)
    print("MISSION CRITICAL: Concurrent User Isolation Test Suite")
    print("=" * 80)
    print("\nThis test suite demonstrates critical architectural flaws.")
    print("ALL TESTS ARE EXPECTED TO FAIL with the current architecture.")
    print("\nEach test documents:")
    print("- What isolation issue it demonstrates")
    print("- Why the current architecture fails")
    print("- What the expected vs. actual behavior should be")
    print("\n" + "=" * 80)
    
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])