"""
Test Multi-User Agent Isolation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure complete isolation between concurrent users' agent executions
- Value Impact: Validates multi-tenant capability enabling 10+ concurrent users without cross-contamination
- Strategic Impact: Foundation for scalable SaaS platform serving multiple enterprise customers simultaneously

This test validates that multiple users can execute agents concurrently without any
state leakage, event cross-contamination, or resource conflicts between users.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)


class UserEventTracker:
    """Tracks events for a specific user."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events: List[Dict[str, Any]] = []
        self.event_counts: Dict[str, int] = {}
        self.agent_states: Dict[str, str] = {}
        self.execution_results: Dict[str, Any] = {}
        self.lock = asyncio.Lock()
    
    async def track_event(self, event_type: str, *args, **kwargs) -> bool:
        """Track an event for this user."""
        async with self.lock:
            self.events.append({
                'user_id': self.user_id,
                'type': event_type,
                'timestamp': time.time(),
                'args': args,
                'kwargs': kwargs,
                'sequence': len(self.events) + 1
            })
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        return True
    
    def get_event_types(self) -> Set[str]:
        """Get all event types for this user."""
        return set(self.event_counts.keys())
    
    def has_complete_agent_lifecycle(self) -> bool:
        """Check if user has complete agent lifecycle events."""
        required_events = {'agent_started', 'agent_thinking', 'agent_completed'}
        return required_events.issubset(self.get_event_types())


class MockAgentInstanceFactory:
    """Mock agent instance factory for testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._agent_registry = MagicMock()
        self._agent_registry.list_keys = MagicMock(return_value=["triage_agent", "cost_optimizer", "data_analyzer"])
        self._websocket_bridge = MagicMock()
    
    async def create_agent_instance(self, agent_name: str, user_context: UserExecutionContext):
        """Create a mock agent instance."""
        mock_agent = MagicMock()
        mock_agent.name = agent_name
        mock_agent.agent_name = agent_name
        mock_agent.user_id = user_context.user_id  # Bind agent to user
        return mock_agent


class TestMultiUserAgentIsolation(SSotAsyncTestCase):
    """Test Multi-User Agent Isolation."""
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    @pytest.mark.mission_critical
    async def test_concurrent_users_complete_isolation(self):
        """Test that multiple users can execute agents concurrently with complete isolation.
        
        BVJ: Mission critical validation that ensures zero cross-contamination between
        concurrent users, enabling secure multi-tenant SaaS operations.
        """
        # Create multiple user contexts
        num_users = 5
        user_contexts = []
        user_trackers = {}
        user_engines = {}
        user_emitters = {}
        
        for i in range(num_users):
            user_id = f"concurrent_user_{i+1:03d}"
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{i+1:03d}",
                run_id=f"run_{i+1:03d}_{int(time.time())}",
                request_id=f"req_{i+1:03d}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(user_context)
            
            # Create user-specific event tracker
            tracker = UserEventTracker(user_id)
            user_trackers[user_id] = tracker
            
            # Create user-specific WebSocket emitter
            mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
            mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, uid=user_id, **k: user_trackers[uid].track_event('agent_started', *a, **k))
            mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, uid=user_id, **k: user_trackers[uid].track_event('agent_thinking', *a, **k))
            mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, uid=user_id, **k: user_trackers[uid].track_event('tool_executing', *a, **k))
            mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, uid=user_id, **k: user_trackers[uid].track_event('tool_completed', *a, **k))
            mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, uid=user_id, **k: user_trackers[uid].track_event('agent_completed', *a, **k))
            mock_emitter.cleanup = AsyncMock()
            user_emitters[user_id] = mock_emitter
            
            # Create user-specific execution engine
            mock_factory = MockAgentInstanceFactory(user_id)
            engine = UserExecutionEngine(
                context=user_context,
                agent_factory=mock_factory,
                websocket_emitter=mock_emitter
            )
            user_engines[user_id] = engine
        
        # Define agent execution task for each user
        async def execute_agent_for_user(user_id: str, agent_name: str, task_data: Dict[str, Any]):
            """Execute agent for a specific user."""
            engine = user_engines[user_id]
            user_context = next(ctx for ctx in user_contexts if ctx.user_id == user_id)
            
            # Create execution context
            context = AgentExecutionContext(
                user_id=user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                agent_name=agent_name,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1,
                metadata=task_data
            )
            
            # Execute full agent lifecycle
            await engine._send_user_agent_started(context)
            
            # Simulate thinking with user-specific content
            await engine._send_user_agent_thinking(
                context, 
                f"User {user_id} executing {agent_name} with {task_data['task_type']}", 
                1
            )
            
            # Tool execution with user-specific parameters
            tool_dispatcher = engine.get_tool_dispatcher()
            await tool_dispatcher.execute_tool(
                f"{agent_name}_tool", 
                {**task_data, "user_id": user_id}
            )
            
            # Complete with user-specific results
            result = AgentExecutionResult(
                success=True,
                agent_name=agent_name,
                execution_time=1.5 + (hash(user_id) % 100) / 100,  # Slight variation per user
                state=None,
                metadata={
                    "user_id": user_id,
                    "task_completed": task_data['task_type'],
                    "agent_used": agent_name,
                    "unique_result": f"result_for_{user_id}"
                }
            )
            await engine._send_user_agent_completed(context, result)
            
            # Store execution result in tracker
            user_trackers[user_id].execution_results[agent_name] = result
        
        # Execute agents concurrently for all users
        concurrent_tasks = []
        for i, user_id in enumerate([ctx.user_id for ctx in user_contexts]):
            agent_name = ["triage_agent", "cost_optimizer", "data_analyzer"][i % 3]
            task_data = {
                "task_type": f"analysis_type_{i+1}",
                "priority": i + 1,
                "user_specific_param": f"param_{user_id}"
            }
            task = execute_agent_for_user(user_id, agent_name, task_data)
            concurrent_tasks.append(task)
        
        # Execute all tasks concurrently
        await asyncio.gather(*concurrent_tasks)
        
        # Validate complete isolation between users
        all_user_ids = set(user_trackers.keys())
        
        # 1. Verify each user has their own events
        for user_id in all_user_ids:
            tracker = user_trackers[user_id]
            assert len(tracker.events) > 0, f"User {user_id} should have events"
            assert tracker.has_complete_agent_lifecycle(), f"User {user_id} should have complete lifecycle"
            
            # Verify all events belong to this user
            for event in tracker.events:
                assert event['user_id'] == user_id, f"Event should belong to {user_id}, got {event['user_id']}"
        
        # 2. Verify no cross-contamination of events
        for user_id_1 in all_user_ids:
            for user_id_2 in all_user_ids:
                if user_id_1 != user_id_2:
                    tracker_1 = user_trackers[user_id_1]
                    tracker_2 = user_trackers[user_id_2]
                    
                    # Check that user 1's events don't appear in user 2's tracker
                    user_1_event_data = [e['kwargs'] for e in tracker_1.events if 'context' in e['kwargs']]
                    user_2_event_data = [e['kwargs'] for e in tracker_2.events if 'context' in e['kwargs']]
                    
                    for event_data in user_1_event_data:
                        if 'context' in event_data and 'user_id' in event_data['context']:
                            assert event_data['context']['user_id'] == user_id_1, \
                                f"User {user_id_1} events should not contain {user_id_2} data"
        
        # 3. Verify execution results isolation
        for user_id in all_user_ids:
            tracker = user_trackers[user_id]
            for agent_name, result in tracker.execution_results.items():
                assert result.metadata['user_id'] == user_id, \
                    f"Execution result should belong to {user_id}"
                assert result.metadata['unique_result'] == f"result_for_{user_id}", \
                    f"Result should be unique to {user_id}"
        
        # 4. Verify engine isolation
        for user_id in all_user_ids:
            engine = user_engines[user_id]
            assert engine.user_context.user_id == user_id, \
                f"Engine should be bound to {user_id}"
            
            # Check that engine state is isolated
            engine_stats = engine.get_user_execution_stats()
            assert engine_stats['user_id'] == user_id, \
                f"Engine stats should belong to {user_id}"
        
        # Cleanup all engines
        cleanup_tasks = [engine.cleanup() for engine in user_engines.values()]
        await asyncio.gather(*cleanup_tasks)
        
        # Verify all engines are inactive after cleanup
        for user_id, engine in user_engines.items():
            assert not engine.is_active(), f"Engine for {user_id} should be inactive after cleanup"
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_user_agent_state_isolation(self):
        """Test that agent states are completely isolated between users.
        
        BVJ: Validates that agent state management doesn't leak between users,
        ensuring each user's agent operations remain private and secure.
        """
        # Create two user contexts with identical agent names to test isolation
        user_context_1 = UserExecutionContext(
            user_id="state_test_user_1",
            thread_id="state_thread_1",
            run_id="state_run_1",
            request_id="state_req_1"
        )
        
        user_context_2 = UserExecutionContext(
            user_id="state_test_user_2", 
            thread_id="state_thread_2",
            run_id="state_run_2",
            request_id="state_req_2"
        )
        
        # Create user-specific event trackers
        tracker_1 = UserEventTracker("state_test_user_1")
        tracker_2 = UserEventTracker("state_test_user_2")
        
        # Create user-specific WebSocket emitters
        mock_emitter_1 = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter_1.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: tracker_1.track_event('agent_started', *a, **k))
        mock_emitter_1.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: tracker_1.track_event('agent_thinking', *a, **k))
        mock_emitter_1.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: tracker_1.track_event('agent_completed', *a, **k))
        mock_emitter_1.cleanup = AsyncMock()
        
        mock_emitter_2 = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter_2.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: tracker_2.track_event('agent_started', *a, **k))
        mock_emitter_2.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: tracker_2.track_event('agent_thinking', *a, **k))
        mock_emitter_2.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: tracker_2.track_event('agent_completed', *a, **k))
        mock_emitter_2.cleanup = AsyncMock()
        
        # Create user-specific engines
        mock_factory_1 = MockAgentInstanceFactory("state_test_user_1")
        mock_factory_2 = MockAgentInstanceFactory("state_test_user_2")
        
        engine_1 = UserExecutionEngine(
            context=user_context_1,
            agent_factory=mock_factory_1,
            websocket_emitter=mock_emitter_1
        )
        
        engine_2 = UserExecutionEngine(
            context=user_context_2,
            agent_factory=mock_factory_2,
            websocket_emitter=mock_emitter_2
        )
        
        # Test agent state isolation with same agent names
        same_agent_name = "data_processor"
        
        # Set different states for same agent name in different engines
        engine_1.set_agent_state(same_agent_name, "user_1_processing")
        engine_2.set_agent_state(same_agent_name, "user_2_analyzing")
        
        # Verify state isolation
        assert engine_1.get_agent_state(same_agent_name) == "user_1_processing", \
            "User 1 should see their own agent state"
        assert engine_2.get_agent_state(same_agent_name) == "user_2_analyzing", \
            "User 2 should see their own agent state"
        
        # Test agent result isolation
        result_1 = {"analysis": "user_1_data", "confidence": 0.85}
        result_2 = {"analysis": "user_2_data", "confidence": 0.92}
        
        engine_1.set_agent_result(same_agent_name, result_1)
        engine_2.set_agent_result(same_agent_name, result_2)
        
        # Verify result isolation
        retrieved_result_1 = engine_1.get_agent_result(same_agent_name)
        retrieved_result_2 = engine_2.get_agent_result(same_agent_name)
        
        assert retrieved_result_1 == result_1, "User 1 should get their own result"
        assert retrieved_result_2 == result_2, "User 2 should get their own result"
        assert retrieved_result_1 != retrieved_result_2, "Results should be different between users"
        
        # Test state history isolation
        engine_1.set_agent_state(same_agent_name, "user_1_completed")
        engine_2.set_agent_state(same_agent_name, "user_2_completed")
        
        history_1 = engine_1.get_agent_state_history(same_agent_name)
        history_2 = engine_2.get_agent_state_history(same_agent_name)
        
        assert "user_1_processing" in history_1, "User 1 history should contain user 1 states"
        assert "user_1_completed" in history_1, "User 1 history should contain user 1 states"
        assert "user_2_analyzing" in history_2, "User 2 history should contain user 2 states"
        assert "user_2_completed" in history_2, "User 2 history should contain user 2 states"
        
        # Verify no cross-contamination in histories
        for state in history_1:
            assert "user_2" not in state, f"User 1 history should not contain user 2 states: {state}"
        for state in history_2:
            assert "user_1" not in state, f"User 2 history should not contain user 1 states: {state}"
        
        # Test execution summary isolation
        summary_1 = engine_1.get_execution_summary()
        summary_2 = engine_2.get_execution_summary()
        
        assert summary_1['user_id'] == "state_test_user_1", "Summary 1 should belong to user 1"
        assert summary_2['user_id'] == "state_test_user_2", "Summary 2 should belong to user 2"
        assert summary_1['engine_id'] != summary_2['engine_id'], "Engine IDs should be different"
        
        # Cleanup
        await engine_1.cleanup()
        await engine_2.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_concurrent_tool_execution_isolation(self):
        """Test that tool executions are isolated between concurrent users.
        
        BVJ: Validates that tool execution doesn't interfere between users,
        ensuring secure and reliable multi-tenant tool usage.
        """
        # Create multiple user contexts
        num_concurrent_users = 3
        user_engines = {}
        user_emitters = {}
        tool_execution_results = {}
        
        for i in range(num_concurrent_users):
            user_id = f"tool_user_{i+1}"
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"tool_thread_{i+1}",
                run_id=f"tool_run_{i+1}",
                request_id=f"tool_req_{i+1}"
            )
            
            # Create user-specific WebSocket emitter
            mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
            mock_emitter.notify_tool_executing = AsyncMock(return_value=True)
            mock_emitter.notify_tool_completed = AsyncMock(return_value=True)
            mock_emitter.cleanup = AsyncMock()
            user_emitters[user_id] = mock_emitter
            
            # Create user-specific engine
            mock_factory = MockAgentInstanceFactory(user_id)
            engine = UserExecutionEngine(
                context=user_context,
                agent_factory=mock_factory,
                websocket_emitter=mock_emitter
            )
            user_engines[user_id] = engine
        
        # Define tool execution task
        async def execute_tools_for_user(user_id: str):
            """Execute tools for a specific user."""
            engine = user_engines[user_id]
            tool_dispatcher = engine.get_tool_dispatcher()
            
            # Execute multiple tools with user-specific parameters
            results = {}
            tools = ["analyzer", "processor", "optimizer"]
            
            for tool_name in tools:
                result = await tool_dispatcher.execute_tool(
                    tool_name,
                    {
                        "user_id": user_id,
                        "data": f"{user_id}_specific_data",
                        "config": f"{user_id}_config"
                    }
                )
                results[tool_name] = result
            
            tool_execution_results[user_id] = results
        
        # Execute tools concurrently for all users
        concurrent_tasks = [
            execute_tools_for_user(user_id) 
            for user_id in user_engines.keys()
        ]
        
        await asyncio.gather(*concurrent_tasks)
        
        # Validate tool execution isolation
        all_user_ids = list(user_engines.keys())
        
        # Verify each user got their own results
        for user_id in all_user_ids:
            assert user_id in tool_execution_results, f"Should have results for {user_id}"
            results = tool_execution_results[user_id]
            
            for tool_name, result in results.items():
                assert result is not None, f"Tool {tool_name} should return result for {user_id}"
                # Verify user-specific data in results
                if isinstance(result, dict) and 'user_id' in result.get('tool_args', {}):
                    assert result['tool_args']['user_id'] == user_id, \
                        f"Tool result should contain correct user_id for {user_id}"
        
        # Verify no cross-contamination between user results
        for user_id_1 in all_user_ids:
            for user_id_2 in all_user_ids:
                if user_id_1 != user_id_2:
                    results_1 = tool_execution_results[user_id_1]
                    results_2 = tool_execution_results[user_id_2]
                    
                    # Results should be different (not identical objects)
                    for tool_name in ["analyzer", "processor", "optimizer"]:
                        result_1 = results_1[tool_name]
                        result_2 = results_2[tool_name]
                        
                        # Results should not be identical objects
                        assert result_1 is not result_2, \
                            f"Tool results should not be shared between {user_id_1} and {user_id_2}"
                        
                        # Results should contain user-specific data
                        if isinstance(result_1, dict) and 'tool_args' in result_1:
                            if 'user_id' in result_1['tool_args']:
                                assert result_1['tool_args']['user_id'] == user_id_1
                        if isinstance(result_2, dict) and 'tool_args' in result_2:
                            if 'user_id' in result_2['tool_args']:
                                assert result_2['tool_args']['user_id'] == user_id_2
        
        # Cleanup all engines
        cleanup_tasks = [engine.cleanup() for engine in user_engines.values()]
        await asyncio.gather(*cleanup_tasks)
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_user_execution_statistics_isolation(self):
        """Test that execution statistics are isolated between users.
        
        BVJ: Validates that performance metrics and statistics don't leak between users,
        ensuring privacy and accurate per-user analytics.
        """
        # Create user contexts with different execution patterns
        user_context_fast = UserExecutionContext(
            user_id="fast_user",
            thread_id="fast_thread",
            run_id="fast_run",
            request_id="fast_req"
        )
        
        user_context_slow = UserExecutionContext(
            user_id="slow_user", 
            thread_id="slow_thread",
            run_id="slow_run",
            request_id="slow_req"
        )
        
        # Create user-specific engines
        mock_emitter_fast = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter_fast.cleanup = AsyncMock()
        
        mock_emitter_slow = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter_slow.cleanup = AsyncMock()
        
        mock_factory_fast = MockAgentInstanceFactory("fast_user")
        mock_factory_slow = MockAgentInstanceFactory("slow_user")
        
        engine_fast = UserExecutionEngine(
            context=user_context_fast,
            agent_factory=mock_factory_fast,
            websocket_emitter=mock_emitter_fast
        )
        
        engine_slow = UserExecutionEngine(
            context=user_context_slow,
            agent_factory=mock_factory_slow,
            websocket_emitter=mock_emitter_slow
        )
        
        # Simulate different execution patterns
        # Fast user: Quick executions
        for i in range(5):
            engine_fast.execution_stats['execution_times'].append(0.1 + i * 0.05)  # 0.1 to 0.3 seconds
            engine_fast.execution_stats['queue_wait_times'].append(0.01)  # Fast queue
            engine_fast.execution_stats['total_executions'] += 1
        
        # Slow user: Slow executions 
        for i in range(3):
            engine_slow.execution_stats['execution_times'].append(2.0 + i * 0.5)  # 2.0 to 3.0 seconds
            engine_slow.execution_stats['queue_wait_times'].append(0.5)  # Slower queue
            engine_slow.execution_stats['total_executions'] += 1
            engine_slow.execution_stats['timeout_executions'] += 1 if i == 2 else 0  # One timeout
        
        # Get statistics for each user
        stats_fast = engine_fast.get_user_execution_stats()
        stats_slow = engine_slow.get_user_execution_stats()
        
        # Verify statistics isolation
        assert stats_fast['user_id'] == "fast_user", "Fast user stats should belong to fast user"
        assert stats_slow['user_id'] == "slow_user", "Slow user stats should belong to slow user"
        
        # Verify different execution patterns are reflected
        assert stats_fast['total_executions'] == 5, "Fast user should have 5 executions"
        assert stats_slow['total_executions'] == 3, "Slow user should have 3 executions"
        
        assert stats_fast['avg_execution_time'] < 0.5, "Fast user should have fast average execution time"
        assert stats_slow['avg_execution_time'] > 1.5, "Slow user should have slow average execution time"
        
        assert stats_fast['timeout_executions'] == 0, "Fast user should have no timeouts"
        assert stats_slow['timeout_executions'] == 1, "Slow user should have 1 timeout"
        
        # Verify engine IDs are unique
        assert stats_fast['engine_id'] != stats_slow['engine_id'], "Engine IDs should be unique"
        
        # Verify correlation IDs are different
        assert stats_fast['user_correlation_id'] != stats_slow['user_correlation_id'], \
            "User correlation IDs should be unique"
        
        # Verify isolation of execution history
        engine_fast.run_history.append(AgentExecutionResult(
            success=True, 
            agent_name="fast_agent", 
            execution_time=0.2,
            state=None
        ))
        
        engine_slow.run_history.append(AgentExecutionResult(
            success=False,
            agent_name="slow_agent",
            execution_time=2.5,
            error="Timeout occurred",
            state=None
        ))
        
        # Verify history isolation
        assert len(engine_fast.run_history) == 1, "Fast user should have 1 history entry"
        assert len(engine_slow.run_history) == 1, "Slow user should have 1 history entry"
        
        fast_result = engine_fast.run_history[0]
        slow_result = engine_slow.run_history[0]
        
        assert fast_result.success is True, "Fast user result should be success"
        assert slow_result.success is False, "Slow user result should be failure"
        assert fast_result.agent_name == "fast_agent", "Fast user should have fast_agent"
        assert slow_result.agent_name == "slow_agent", "Slow user should have slow_agent"
        
        # Cleanup
        await engine_fast.cleanup()
        await engine_slow.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_user_websocket_emitter_isolation(self):
        """Test that WebSocket emitters are completely isolated between users.
        
        BVJ: Validates that WebSocket events are sent only to intended users,
        ensuring privacy and security of real-time communications.
        """
        # Create user contexts
        user_context_alpha = UserExecutionContext(
            user_id="alpha_user",
            thread_id="alpha_thread", 
            run_id="alpha_run",
            request_id="alpha_req"
        )
        
        user_context_beta = UserExecutionContext(
            user_id="beta_user",
            thread_id="beta_thread",
            run_id="beta_run", 
            request_id="beta_req"
        )
        
        # Create isolated event tracking for each user
        alpha_events = []
        beta_events = []
        
        async def track_alpha_event(event_type, *args, **kwargs):
            alpha_events.append({
                'user': 'alpha_user',
                'type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
        
        async def track_beta_event(event_type, *args, **kwargs):
            beta_events.append({
                'user': 'beta_user', 
                'type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
        
        # Create completely separate WebSocket emitters
        mock_emitter_alpha = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter_alpha.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_alpha_event('agent_started', *a, **k))
        mock_emitter_alpha.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_alpha_event('agent_thinking', *a, **k))
        mock_emitter_alpha.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_alpha_event('tool_executing', *a, **k))
        mock_emitter_alpha.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_alpha_event('tool_completed', *a, **k))
        mock_emitter_alpha.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_alpha_event('agent_completed', *a, **k))
        mock_emitter_alpha.cleanup = AsyncMock()
        
        mock_emitter_beta = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter_beta.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_beta_event('agent_started', *a, **k))
        mock_emitter_beta.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_beta_event('agent_thinking', *a, **k))
        mock_emitter_beta.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_beta_event('tool_executing', *a, **k))
        mock_emitter_beta.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_beta_event('tool_completed', *a, **k))
        mock_emitter_beta.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_beta_event('agent_completed', *a, **k))
        mock_emitter_beta.cleanup = AsyncMock()
        
        # Create user-specific engines
        mock_factory_alpha = MockAgentInstanceFactory("alpha_user")
        mock_factory_beta = MockAgentInstanceFactory("beta_user")
        
        engine_alpha = UserExecutionEngine(
            context=user_context_alpha,
            agent_factory=mock_factory_alpha,
            websocket_emitter=mock_emitter_alpha
        )
        
        engine_beta = UserExecutionEngine(
            context=user_context_beta,
            agent_factory=mock_factory_beta,
            websocket_emitter=mock_emitter_beta
        )
        
        # Create execution contexts
        context_alpha = AgentExecutionContext(
            user_id="alpha_user",
            thread_id="alpha_thread",
            run_id="alpha_run",
            request_id="alpha_req",
            agent_name="alpha_agent",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        context_beta = AgentExecutionContext(
            user_id="beta_user",
            thread_id="beta_thread", 
            run_id="beta_run",
            request_id="beta_req",
            agent_name="beta_agent",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Execute WebSocket events concurrently for both users
        async def execute_alpha_events():
            await engine_alpha._send_user_agent_started(context_alpha)
            await engine_alpha._send_user_agent_thinking(context_alpha, "Alpha user thinking...")
            
            tool_dispatcher_alpha = engine_alpha.get_tool_dispatcher()
            await tool_dispatcher_alpha.execute_tool("alpha_tool", {"user": "alpha"})
            
            result_alpha = AgentExecutionResult(
                success=True,
                agent_name="alpha_agent",
                execution_time=1.2,
                state=None
            )
            await engine_alpha._send_user_agent_completed(context_alpha, result_alpha)
        
        async def execute_beta_events():
            await engine_beta._send_user_agent_started(context_beta)
            await engine_beta._send_user_agent_thinking(context_beta, "Beta user thinking...")
            
            tool_dispatcher_beta = engine_beta.get_tool_dispatcher()
            await tool_dispatcher_beta.execute_tool("beta_tool", {"user": "beta"})
            
            result_beta = AgentExecutionResult(
                success=True,
                agent_name="beta_agent", 
                execution_time=1.8,
                state=None
            )
            await engine_beta._send_user_agent_completed(context_beta, result_beta)
        
        # Execute both user workflows concurrently
        await asyncio.gather(execute_alpha_events(), execute_beta_events())
        
        # Verify complete WebSocket isolation
        assert len(alpha_events) > 0, "Alpha user should have WebSocket events"
        assert len(beta_events) > 0, "Beta user should have WebSocket events"
        
        # Verify all alpha events belong to alpha user
        for event in alpha_events:
            assert event['user'] == 'alpha_user', "All alpha events should belong to alpha user"
            # Check event content for alpha-specific data
            if event['args'] and len(event['args']) > 0:
                if isinstance(event['args'][0], str) and 'agent' in event['args'][0]:
                    assert 'alpha' in event['args'][0] or 'alpha_agent' == event['args'][0], \
                        "Alpha events should contain alpha-specific content"
        
        # Verify all beta events belong to beta user
        for event in beta_events:
            assert event['user'] == 'beta_user', "All beta events should belong to beta user"
            # Check event content for beta-specific data
            if event['args'] and len(event['args']) > 0:
                if isinstance(event['args'][0], str) and 'agent' in event['args'][0]:
                    assert 'beta' in event['args'][0] or 'beta_agent' == event['args'][0], \
                        "Beta events should contain beta-specific content"
        
        # Verify no cross-contamination
        alpha_event_types = set(event['type'] for event in alpha_events)
        beta_event_types = set(event['type'] for event in beta_events)
        
        # Both should have complete event sets
        expected_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        assert expected_events.issubset(alpha_event_types), "Alpha should have all event types"
        assert expected_events.issubset(beta_event_types), "Beta should have all event types"
        
        # Verify temporal isolation - events should be interleaved but isolated
        all_events = [(e, 'alpha') for e in alpha_events] + [(e, 'beta') for e in beta_events]
        all_events.sort(key=lambda x: x[0]['timestamp'])
        
        # Check that despite temporal interleaving, each event is correctly attributed
        for event, expected_user in all_events:
            actual_user = event['user']
            assert actual_user == expected_user, \
                f"Event attribution should be correct: expected {expected_user}, got {actual_user}"
        
        # Cleanup
        await engine_alpha.cleanup()
        await engine_beta.cleanup()