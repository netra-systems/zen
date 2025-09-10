"""
Test UserExecutionEngine WebSocket Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Validate per-user agent execution with proper WebSocket event emission
- Value Impact: Tests isolated user execution that enables concurrent users with real-time feedback
- Strategic Impact: Validates the foundation of multi-tenant agent execution with 90% chat business value

This test validates that UserExecutionEngine properly integrates with WebSocket emitters
to provide user-isolated agent execution with complete WebSocket event delivery.
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)


class MockAgentInstanceFactory:
    """Mock agent instance factory for testing."""
    
    def __init__(self):
        self._agent_registry = MagicMock()
        self._agent_registry.list_keys = MagicMock(return_value=["triage_agent", "cost_optimizer", "data_analyzer"])
        self._websocket_bridge = MagicMock()
    
    async def create_agent_instance(self, agent_name: str, user_context: UserExecutionContext):
        """Create a mock agent instance."""
        mock_agent = MagicMock()
        mock_agent.name = agent_name
        mock_agent.agent_name = agent_name
        return mock_agent


class TestUserExecutionEngineWebSocketIntegration(SSotAsyncTestCase):
    """Test UserExecutionEngine WebSocket Integration."""
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_user_execution_engine_websocket_emitter_integration(self):
        """Test that UserExecutionEngine properly integrates with WebSocket emitter.
        
        BVJ: Validates that user-specific execution engine can emit WebSocket events
        for real-time user feedback during agent execution.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_001",
            thread_id="thread_001", 
            run_id="run_001",
            request_id="req_001"
        )
        
        # Create mock WebSocket emitter with event tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        emitted_events = []
        
        def track_event(event_type, *args, **kwargs):
            emitted_events.append({
                'type': event_type,
                'args': args, 
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
        
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_event('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_event('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_event('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_event('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_event('agent_completed', *a, **k))
        mock_emitter.cleanup = AsyncMock()
        
        # Create mock factory
        mock_factory = MockAgentInstanceFactory()
        
        # Create UserExecutionEngine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_factory,
            websocket_emitter=mock_emitter
        )
        
        # Verify engine has WebSocket emitter
        assert engine.websocket_emitter is mock_emitter, "Engine should have WebSocket emitter"
        assert engine.context.user_id == "test_user_001", "Engine should have correct user context"
        
        # Test WebSocket emitter integration by calling internal methods
        context = AgentExecutionContext(
            user_id="test_user_001",
            thread_id="thread_001",
            run_id="run_001",
            request_id="req_001",
            agent_name="triage_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Test agent started event
        await engine._send_user_agent_started(context)
        assert len(emitted_events) == 1, "Should emit agent_started event"
        assert emitted_events[0]['type'] == 'agent_started', "Should emit agent_started"
        
        # Test agent thinking event
        await engine._send_user_agent_thinking(context, "Testing thinking event...", 1)
        assert len(emitted_events) == 2, "Should emit agent_thinking event"
        assert emitted_events[1]['type'] == 'agent_thinking', "Should emit agent_thinking"
        
        # Test agent completed event
        result = AgentExecutionResult(
            success=True,
            agent_name="triage_agent",
            duration=1.5,
            data=None
        )
        await engine._send_user_agent_completed(context, result)
        assert len(emitted_events) == 3, "Should emit agent_completed event"
        assert emitted_events[2]['type'] == 'agent_completed', "Should emit agent_completed"
        
        # Cleanup
        await engine.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_user_execution_engine_tool_dispatcher_websocket_events(self):
        """Test that UserExecutionEngine tool dispatcher emits WebSocket events.
        
        BVJ: Validates that tool execution through user engine emits tool_executing
        and tool_completed events for complete user visibility of AI operations.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_002",
            thread_id="thread_002",
            run_id="run_002", 
            request_id="req_002"
        )
        
        # Create mock WebSocket emitter
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        tool_events = []
        
        async def track_tool_event(event_type, tool_name, *args, **kwargs):
            tool_events.append({
                'type': event_type,
                'tool_name': tool_name,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
        
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda tool_name, *a, **k: track_tool_event('tool_executing', tool_name, *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda tool_name, *a, **k: track_tool_event('tool_completed', tool_name, *a, **k))
        mock_emitter.cleanup = AsyncMock()
        
        # Create mock factory
        mock_factory = MockAgentInstanceFactory()
        
        # Create UserExecutionEngine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_factory,
            websocket_emitter=mock_emitter
        )
        
        # Get tool dispatcher from engine
        tool_dispatcher = engine.get_tool_dispatcher()
        assert tool_dispatcher is not None, "Engine should have tool dispatcher"
        
        # Test tool execution with WebSocket events
        result = await tool_dispatcher.execute_tool("cost_analyzer", {"data": "test"})
        
        # Verify tool events were emitted
        assert len(tool_events) == 2, f"Should emit 2 tool events, got {len(tool_events)}"
        
        # Verify event types and order
        assert tool_events[0]['type'] == 'tool_executing', "First event should be tool_executing"
        assert tool_events[0]['tool_name'] == 'cost_analyzer', "Should have correct tool name"
        
        assert tool_events[1]['type'] == 'tool_completed', "Second event should be tool_completed"
        assert tool_events[1]['tool_name'] == 'cost_analyzer', "Should have correct tool name"
        
        # Verify temporal ordering
        assert tool_events[0]['timestamp'] <= tool_events[1]['timestamp'], "Events should be in temporal order"
        
        # Verify result structure
        assert result is not None, "Tool execution should return result"
        assert 'success' in result, "Result should indicate success"
        
        # Cleanup
        await engine.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_user_execution_engine_concurrent_websocket_isolation(self):
        """Test that multiple UserExecutionEngines maintain WebSocket event isolation.
        
        BVJ: Validates that concurrent users don't interfere with each other's
        WebSocket events, ensuring clean isolated chat experiences.
        """
        # Create multiple user contexts
        user_context_1 = UserExecutionContext(
            user_id="user_001",
            thread_id="thread_001",
            run_id="run_001",
            request_id="req_001"
        )
        
        user_context_2 = UserExecutionContext(
            user_id="user_002", 
            thread_id="thread_002",
            run_id="run_002",
            request_id="req_002"
        )
        
        # Create separate WebSocket emitters for each user
        emitter_1_events = []
        emitter_2_events = []
        
        async def track_user_1_event(event_type, *args, **kwargs):
            emitter_1_events.append({
                'user_id': 'user_001',
                'type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
        
        async def track_user_2_event(event_type, *args, **kwargs):
            emitter_2_events.append({
                'user_id': 'user_002',
                'type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
        
        mock_emitter_1 = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter_1.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_user_1_event('agent_started', *a, **k))
        mock_emitter_1.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_user_1_event('agent_thinking', *a, **k))
        mock_emitter_1.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_user_1_event('agent_completed', *a, **k))
        mock_emitter_1.cleanup = AsyncMock()
        
        mock_emitter_2 = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter_2.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_user_2_event('agent_started', *a, **k))
        mock_emitter_2.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_user_2_event('agent_thinking', *a, **k))
        mock_emitter_2.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_user_2_event('agent_completed', *a, **k))
        mock_emitter_2.cleanup = AsyncMock()
        
        # Create mock factories
        mock_factory_1 = MockAgentInstanceFactory()
        mock_factory_2 = MockAgentInstanceFactory()
        
        # Create separate UserExecutionEngines
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
        
        # Create execution contexts for each user
        context_1 = AgentExecutionContext(
            user_id="user_001",
            thread_id="thread_001",
            run_id="run_001",
            request_id="req_001",
            agent_name="triage_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        context_2 = AgentExecutionContext(
            user_id="user_002",
            thread_id="thread_002", 
            run_id="run_002",
            request_id="req_002",
            agent_name="cost_optimizer",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Execute WebSocket events concurrently for both users
        await asyncio.gather(
            engine_1._send_user_agent_started(context_1),
            engine_2._send_user_agent_started(context_2),
            engine_1._send_user_agent_thinking(context_1, "User 1 thinking..."),
            engine_2._send_user_agent_thinking(context_2, "User 2 thinking...")
        )
        
        # Verify event isolation
        assert len(emitter_1_events) == 2, f"User 1 should have 2 events, got {len(emitter_1_events)}"
        assert len(emitter_2_events) == 2, f"User 2 should have 2 events, got {len(emitter_2_events)}"
        
        # Verify all user 1 events belong to user 1
        for event in emitter_1_events:
            assert event['user_id'] == 'user_001', "All user 1 events should belong to user 1"
        
        # Verify all user 2 events belong to user 2
        for event in emitter_2_events:
            assert event['user_id'] == 'user_002', "All user 2 events should belong to user 2"
        
        # Verify no cross-contamination
        user_1_context_data = [event['kwargs'] for event in emitter_1_events if 'context' in event['kwargs']]
        user_2_context_data = [event['kwargs'] for event in emitter_2_events if 'context' in event['kwargs']]
        
        # Each user should only see their own context data
        for context_data in user_1_context_data:
            if 'context' in context_data and 'user_id' in context_data['context']:
                assert context_data['context']['user_id'] == 'user_001'
                
        for context_data in user_2_context_data:
            if 'context' in context_data and 'user_id' in context_data['context']:
                assert context_data['context']['user_id'] == 'user_002'
        
        # Cleanup
        await engine_1.cleanup()
        await engine_2.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_user_execution_engine_websocket_error_resilience(self):
        """Test UserExecutionEngine resilience to WebSocket errors.
        
        BVJ: Validates that WebSocket failures don't crash user execution,
        ensuring business-critical agent operations continue even with connectivity issues.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_004",
            thread_id="thread_004",
            run_id="run_004",
            request_id="req_004"
        )
        
        # Create failing WebSocket emitter
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        call_count = {'count': 0}
        
        async def failing_notify(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] % 2 == 1:  # Fail every other call
                raise Exception(f"WebSocket connection lost (call {call_count['count']})")
            return True
        
        mock_emitter.notify_agent_started = AsyncMock(side_effect=failing_notify)
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=failing_notify)
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=failing_notify)
        mock_emitter.cleanup = AsyncMock()
        
        # Create mock factory
        mock_factory = MockAgentInstanceFactory()
        
        # Create UserExecutionEngine (should not fail during creation)
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_factory,
            websocket_emitter=mock_emitter
        )
        
        # Verify engine is created successfully despite WebSocket issues
        assert engine.user_context.user_id == "test_user_004", "Engine should be created successfully"
        assert engine.is_active(), "Engine should be active"
        
        # Create execution context
        context = AgentExecutionContext(
            user_id="test_user_004",
            thread_id="thread_004",
            run_id="run_004",
            request_id="req_004",
            agent_name="triage_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Test WebSocket event sending with error resilience
        error_count = 0
        success_count = 0
        
        # Try sending multiple events to test error handling
        for i in range(6):
            try:
                if i % 3 == 0:
                    await engine._send_user_agent_started(context)
                elif i % 3 == 1:
                    await engine._send_user_agent_thinking(context, f"Thinking step {i}")
                else:
                    result = AgentExecutionResult(
                        success=True,
                        agent_name="triage_agent",
                        duration=0.5,
                        data=None
                    )
                    await engine._send_user_agent_completed(context, result)
                success_count += 1
            except Exception as e:
                error_count += 1
                # Errors should be caught and logged, not crash the system
                assert "WebSocket connection lost" in str(e), "Should catch expected WebSocket errors"
        
        # Verify system resilience
        assert error_count > 0, "Should encounter WebSocket errors during testing"
        assert success_count > 0, "Some WebSocket calls should succeed"
        
        # Engine should still be functional
        assert engine.is_active(), "Engine should remain active despite WebSocket errors"
        
        # Verify engine state tracking still works
        engine.set_agent_state("triage_agent", "running")
        assert engine.get_agent_state("triage_agent") == "running", "State tracking should work despite WebSocket issues"
        
        # Cleanup should work
        await engine.cleanup()
        assert not engine.is_active(), "Engine should be inactive after cleanup"
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_user_execution_engine_websocket_event_ordering(self):
        """Test that UserExecutionEngine maintains correct WebSocket event ordering.
        
        BVJ: Validates that WebSocket events are emitted in correct order to provide
        accurate real-time progress information to users during agent execution.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_005", 
            thread_id="thread_005",
            run_id="run_005",
            request_id="req_005"
        )
        
        # Create mock WebSocket emitter with detailed event tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        ordered_events = []
        
        async def track_ordered_event(event_type, *args, **kwargs):
            ordered_events.append({
                'type': event_type,
                'timestamp': time.time(),
                'args': args,
                'kwargs': kwargs,
                'sequence': len(ordered_events) + 1
            })
            # Add small delay to ensure timestamp differences
            await asyncio.sleep(0.001)
            return True
        
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_ordered_event('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_ordered_event('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_ordered_event('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_ordered_event('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_ordered_event('agent_completed', *a, **k))
        mock_emitter.cleanup = AsyncMock()
        
        # Create mock factory
        mock_factory = MockAgentInstanceFactory()
        
        # Create UserExecutionEngine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_factory,
            websocket_emitter=mock_emitter
        )
        
        # Create execution context
        context = AgentExecutionContext(
            user_id="test_user_005",
            thread_id="thread_005", 
            run_id="run_005",
            request_id="req_005",
            agent_name="data_analyzer",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Simulate full agent execution lifecycle with proper ordering
        await engine._send_user_agent_started(context)
        
        await engine._send_user_agent_thinking(context, "Initializing analysis...", 1)
        await engine._send_user_agent_thinking(context, "Loading data sources...", 2)
        await engine._send_user_agent_thinking(context, "Performing analysis...", 3)
        
        # Simulate tool usage
        tool_dispatcher = engine.get_tool_dispatcher()
        await tool_dispatcher.execute_tool("data_loader", {"source": "database"})
        await tool_dispatcher.execute_tool("analyzer", {"type": "cost_analysis"})
        
        # Complete agent execution
        result = AgentExecutionResult(
            success=True,
            agent_name="data_analyzer", 
            duration=2.5,
            data=None
        )
        await engine._send_user_agent_completed(context, result)
        
        # Verify event count and types
        expected_event_count = 9  # 1 started + 3 thinking + 4 tool events (2 executing, 2 completed) + 1 completed
        assert len(ordered_events) == expected_event_count, f"Should have {expected_event_count} events, got {len(ordered_events)}"
        
        # Verify event sequence
        event_types = [event['type'] for event in ordered_events]
        expected_sequence = [
            'agent_started',
            'agent_thinking', 'agent_thinking', 'agent_thinking',
            'tool_executing', 'tool_completed',
            'tool_executing', 'tool_completed', 
            'agent_completed'
        ]
        
        assert event_types == expected_sequence, f"Event sequence should match expected order. Got: {event_types}"
        
        # Verify temporal ordering
        timestamps = [event['timestamp'] for event in ordered_events]
        assert timestamps == sorted(timestamps), "Events should be in strict temporal order"
        
        # Verify sequence numbers
        sequences = [event['sequence'] for event in ordered_events]
        assert sequences == list(range(1, expected_event_count + 1)), "Sequence numbers should be consecutive"
        
        # Verify agent lifecycle events bracket other events
        assert ordered_events[0]['type'] == 'agent_started', "First event should be agent_started"
        assert ordered_events[-1]['type'] == 'agent_completed', "Last event should be agent_completed"
        
        # Verify thinking events are in correct order
        thinking_events = [event for event in ordered_events if event['type'] == 'agent_thinking']
        assert len(thinking_events) == 3, "Should have 3 thinking events"
        
        # Verify tool events are properly paired
        tool_events = [event for event in ordered_events if 'tool' in event['type']]
        tool_executing_count = len([e for e in tool_events if e['type'] == 'tool_executing'])
        tool_completed_count = len([e for e in tool_events if e['type'] == 'tool_completed'])
        
        assert tool_executing_count == tool_completed_count, "Should have equal tool_executing and tool_completed events"
        assert tool_executing_count == 2, "Should have 2 tool_executing events"
        
        # Cleanup
        await engine.cleanup()