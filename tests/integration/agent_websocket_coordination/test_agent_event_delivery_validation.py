"""
Test Agent Event Delivery Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure all 5 critical WebSocket events are delivered for complete user visibility
- Value Impact: Validates the core 90% business value of chat - real-time agent progress visibility
- Strategic Impact: Mission critical test ensuring users can see AI operations in real-time

This test validates that all 5 critical WebSocket events (agent_started, agent_thinking,
tool_executing, tool_completed, agent_completed) are properly delivered during agent execution.
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
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


class EventDeliveryTracker:
    """Tracks WebSocket event delivery for validation."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_counts: Dict[str, int] = {}
        self.first_event_time: Optional[float] = None
        self.last_event_time: Optional[float] = None
    
    async def track_event(self, event_type: str, *args, **kwargs) -> bool:
        """Track an event delivery."""
        current_time = time.time()
        
        if self.first_event_time is None:
            self.first_event_time = current_time
        self.last_event_time = current_time
        
        self.events.append({
            'type': event_type,
            'timestamp': current_time,
            'args': args,
            'kwargs': kwargs,
            'sequence': len(self.events) + 1
        })
        
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        return True
    
    def get_missing_critical_events(self) -> Set[str]:
        """Get any missing critical events."""
        critical_events = {
            'agent_started', 'agent_thinking', 'tool_executing', 
            'tool_completed', 'agent_completed'
        }
        delivered_events = set(self.event_counts.keys())
        return critical_events - delivered_events
    
    def get_event_sequence(self) -> List[str]:
        """Get the sequence of event types."""
        return [event['type'] for event in self.events]
    
    def get_execution_duration(self) -> float:
        """Get total execution duration."""
        if self.first_event_time and self.last_event_time:
            return self.last_event_time - self.first_event_time
        return 0.0


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


class TestAgentEventDeliveryValidation(SSotAsyncTestCase):
    """Test Agent Event Delivery Validation."""
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    @pytest.mark.mission_critical
    async def test_all_five_critical_events_delivered(self):
        """Test that all 5 critical WebSocket events are delivered during agent execution.
        
        BVJ: Mission critical validation that ensures users receive complete real-time
        visibility into agent operations, delivering the core 90% chat business value.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="critical_user_001",
            thread_id="critical_thread_001",
            run_id="critical_run_001",
            request_id="critical_req_001"
        )
        
        # Create event delivery tracker
        tracker = EventDeliveryTracker()
        
        # Create mock WebSocket emitter with comprehensive tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('agent_completed', *a, **k))
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
            user_id="critical_user_001",
            thread_id="critical_thread_001",
            run_id="critical_run_001", 
            request_id="critical_req_001",
            agent_name="cost_optimizer",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Simulate complete agent execution lifecycle
        # 1. Agent started
        await engine._send_user_agent_started(context)
        
        # 2. Agent thinking (multiple thinking steps)
        await engine._send_user_agent_thinking(context, "Analyzing cost optimization opportunities...", 1)
        await engine._send_user_agent_thinking(context, "Identifying cost reduction patterns...", 2)
        
        # 3. Tool execution
        tool_dispatcher = engine.get_tool_dispatcher()
        await tool_dispatcher.execute_tool("cost_analyzer", {"period": "last_30_days"})
        await tool_dispatcher.execute_tool("savings_calculator", {"baseline": "current_usage"})
        
        # 4. Agent completed
        result = AgentExecutionResult(
            success=True,
            agent_name="cost_optimizer",
            execution_time=3.2,
            state=None,
            metadata={"savings_identified": "$15000", "recommendations": 5}
        )
        await engine._send_user_agent_completed(context, result)
        
        # CRITICAL VALIDATION: All 5 events must be delivered
        missing_events = tracker.get_missing_critical_events()
        assert len(missing_events) == 0, f"CRITICAL: Missing essential events: {missing_events}"
        
        # Verify minimum event counts
        assert tracker.event_counts['agent_started'] >= 1, "Must have at least 1 agent_started event"
        assert tracker.event_counts['agent_thinking'] >= 1, "Must have at least 1 agent_thinking event"
        assert tracker.event_counts['tool_executing'] >= 1, "Must have at least 1 tool_executing event"
        assert tracker.event_counts['tool_completed'] >= 1, "Must have at least 1 tool_completed event"
        assert tracker.event_counts['agent_completed'] >= 1, "Must have at least 1 agent_completed event"
        
        # Verify event ordering (agent_started first, agent_completed last)
        event_sequence = tracker.get_event_sequence()
        assert event_sequence[0] == 'agent_started', "First event must be agent_started"
        assert event_sequence[-1] == 'agent_completed', "Last event must be agent_completed"
        
        # Verify execution duration is reasonable
        duration = tracker.get_execution_duration()
        assert 0 < duration < 10, f"Execution duration should be reasonable: {duration}s"
        
        # Verify total event count
        total_events = len(tracker.events)
        assert total_events >= 5, f"Should have at least 5 events (one of each type), got {total_events}"
        
        # Cleanup
        await engine.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_event_delivery_with_multiple_tools(self):
        """Test event delivery when agent uses multiple tools.
        
        BVJ: Validates that complex agent workflows with multiple tool executions
        deliver all events correctly, ensuring users see complete operation progress.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="multi_tool_user",
            thread_id="multi_tool_thread", 
            run_id="multi_tool_run",
            request_id="multi_tool_req"
        )
        
        # Create event delivery tracker
        tracker = EventDeliveryTracker()
        
        # Create mock WebSocket emitter
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: tracker.track_event('agent_completed', *a, **k))
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
            user_id="multi_tool_user",
            thread_id="multi_tool_thread",
            run_id="multi_tool_run",
            request_id="multi_tool_req",
            agent_name="data_analyzer",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Simulate agent execution with multiple tools
        await engine._send_user_agent_started(context)
        await engine._send_user_agent_thinking(context, "Starting comprehensive data analysis...")
        
        # Execute 5 different tools to test comprehensive event delivery
        tool_dispatcher = engine.get_tool_dispatcher()
        tools = [
            "data_loader",
            "data_cleaner", 
            "pattern_analyzer",
            "trend_detector",
            "report_generator"
        ]
        
        for i, tool in enumerate(tools, 1):
            await engine._send_user_agent_thinking(context, f"Executing {tool}...", i + 1)
            await tool_dispatcher.execute_tool(tool, {"step": i, "data": f"analysis_step_{i}"})
        
        # Complete execution
        result = AgentExecutionResult(
            success=True,
            agent_name="data_analyzer",
            execution_time=5.8,
            state=None
        )
        await engine._send_user_agent_completed(context, result)
        
        # Verify all critical events delivered
        missing_events = tracker.get_missing_critical_events()
        assert len(missing_events) == 0, f"Missing critical events: {missing_events}"
        
        # Verify expected event counts
        assert tracker.event_counts['agent_started'] == 1, "Should have exactly 1 agent_started"
        assert tracker.event_counts['agent_thinking'] >= 6, "Should have at least 6 agent_thinking events"
        assert tracker.event_counts['tool_executing'] == 5, "Should have exactly 5 tool_executing events"
        assert tracker.event_counts['tool_completed'] == 5, "Should have exactly 5 tool_completed events"
        assert tracker.event_counts['agent_completed'] == 1, "Should have exactly 1 agent_completed"
        
        # Verify tool event pairing
        tool_executing_count = tracker.event_counts['tool_executing']
        tool_completed_count = tracker.event_counts['tool_completed']
        assert tool_executing_count == tool_completed_count, "Tool executing/completed events should be paired"
        
        # Verify event sequence logic
        event_sequence = tracker.get_event_sequence()
        
        # Check that tool events are properly paired
        tool_pairs_correct = True
        executing_indices = [i for i, event_type in enumerate(event_sequence) if event_type == 'tool_executing']
        completed_indices = [i for i, event_type in enumerate(event_sequence) if event_type == 'tool_completed']
        
        # Each tool_executing should be followed by tool_completed before next tool_executing
        for i in range(len(executing_indices)):
            if i < len(completed_indices):
                if executing_indices[i] >= completed_indices[i]:
                    tool_pairs_correct = False
                    break
        
        assert tool_pairs_correct, "Tool executing events should be followed by completed events"
        
        # Cleanup
        await engine.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_event_delivery_failure_recovery(self):
        """Test event delivery behavior when some events fail.
        
        BVJ: Validates system resilience when WebSocket delivery fails,
        ensuring user experience degrades gracefully without system crashes.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="failure_test_user",
            thread_id="failure_test_thread",
            run_id="failure_test_run",
            request_id="failure_test_req"
        )
        
        # Create event delivery tracker with failure simulation
        tracker = EventDeliveryTracker()
        failure_count = {'count': 0}
        
        async def failing_event_tracker(event_type: str, *args, **kwargs) -> bool:
            failure_count['count'] += 1
            # Simulate intermittent failures (fail every 3rd event)
            if failure_count['count'] % 3 == 0:
                # Still track for validation but indicate failure
                await tracker.track_event(f"{event_type}_failed", *args, **kwargs)
                return False  # Indicate delivery failure
            else:
                await tracker.track_event(event_type, *args, **kwargs)
                return True
        
        # Create mock WebSocket emitter with failure simulation
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: failing_event_tracker('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: failing_event_tracker('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: failing_event_tracker('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: failing_event_tracker('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: failing_event_tracker('agent_completed', *a, **k))
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
            user_id="failure_test_user",
            thread_id="failure_test_thread",
            run_id="failure_test_run",
            request_id="failure_test_req",
            agent_name="resilience_test_agent",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Execute full agent lifecycle (should not crash despite failures)
        await engine._send_user_agent_started(context)
        
        # Multiple thinking events to trigger failures
        for i in range(5):
            await engine._send_user_agent_thinking(context, f"Thinking step {i+1}...", i+1)
        
        # Tool execution
        tool_dispatcher = engine.get_tool_dispatcher()
        await tool_dispatcher.execute_tool("resilience_tool", {"test": "failure_recovery"})
        
        # Complete execution
        result = AgentExecutionResult(
            success=True,
            agent_name="resilience_test_agent", 
            execution_time=2.1,
            state=None
        )
        await engine._send_user_agent_completed(context, result)
        
        # Verify system resilience
        total_events = len(tracker.events)
        assert total_events > 0, "Should have attempted to deliver events despite failures"
        
        # Count successful vs failed events
        successful_events = [e for e in tracker.events if not e['type'].endswith('_failed')]
        failed_events = [e for e in tracker.events if e['type'].endswith('_failed')]
        
        assert len(successful_events) > 0, "Some events should have succeeded"
        assert len(failed_events) > 0, "Some events should have failed (as designed)"
        
        # Verify that execution completed despite failures
        completed_events = [e for e in tracker.events if 'agent_completed' in e['type']]
        assert len(completed_events) >= 1, "Agent execution should complete despite WebSocket failures"
        
        # Verify engine remains functional
        assert engine.is_active(), "Engine should remain active despite WebSocket failures"
        
        # Test that subsequent operations still work
        engine.set_agent_state("resilience_test_agent", "completed")
        assert engine.get_agent_state("resilience_test_agent") == "completed", "Engine functionality should remain intact"
        
        # Cleanup
        await engine.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_event_delivery_timing_validation(self):
        """Test that WebSocket events are delivered within acceptable time limits.
        
        BVJ: Validates that real-time events are actually delivered in real-time,
        ensuring users get immediate feedback for responsive chat experience.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="timing_test_user",
            thread_id="timing_test_thread",
            run_id="timing_test_run",
            request_id="timing_test_req"
        )
        
        # Create timing-aware event tracker
        tracker = EventDeliveryTracker()
        event_delays = []
        
        async def timing_event_tracker(event_type: str, *args, **kwargs) -> bool:
            call_time = time.time()
            await tracker.track_event(event_type, *args, **kwargs)
            
            # Add small delay to simulate network latency
            await asyncio.sleep(0.001)
            
            delivery_time = time.time()
            delay = delivery_time - call_time
            event_delays.append({
                'event_type': event_type,
                'delay_ms': delay * 1000,
                'call_time': call_time,
                'delivery_time': delivery_time
            })
            return True
        
        # Create mock WebSocket emitter with timing tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: timing_event_tracker('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: timing_event_tracker('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: timing_event_tracker('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: timing_event_tracker('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: timing_event_tracker('agent_completed', *a, **k))
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
            user_id="timing_test_user",
            thread_id="timing_test_thread", 
            run_id="timing_test_run",
            request_id="timing_test_req",
            agent_name="timing_test_agent",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Execute agent lifecycle while measuring timing
        start_time = time.time()
        
        await engine._send_user_agent_started(context)
        await engine._send_user_agent_thinking(context, "Processing request with timing validation...")
        
        tool_dispatcher = engine.get_tool_dispatcher()
        await tool_dispatcher.execute_tool("timing_test_tool", {"measure": "latency"})
        
        result = AgentExecutionResult(
            success=True,
            agent_name="timing_test_agent",
            execution_time=1.0,
            state=None
        )
        await engine._send_user_agent_completed(context, result)
        
        end_time = time.time()
        total_execution_time = end_time - start_time
        
        # Validate timing constraints
        assert len(event_delays) >= 5, "Should have timing data for all critical events"
        
        # Verify individual event delivery times are reasonable (< 10ms for mock)
        max_acceptable_delay_ms = 10.0
        for delay_info in event_delays:
            assert delay_info['delay_ms'] < max_acceptable_delay_ms, \
                f"Event {delay_info['event_type']} took {delay_info['delay_ms']:.2f}ms, " \
                f"exceeds {max_acceptable_delay_ms}ms limit"
        
        # Verify total execution time is reasonable
        assert total_execution_time < 1.0, f"Total execution took {total_execution_time:.3f}s, should be < 1s for mock"
        
        # Verify event delivery order matches call order
        call_times = [delay_info['call_time'] for delay_info in event_delays]
        delivery_times = [delay_info['delivery_time'] for delay_info in event_delays]
        
        assert call_times == sorted(call_times), "Event call times should be in order"
        assert delivery_times == sorted(delivery_times), "Event delivery times should be in order"
        
        # Verify no significant gaps between events (all events < 100ms apart)
        max_gap_ms = 100.0
        for i in range(1, len(call_times)):
            gap_ms = (call_times[i] - call_times[i-1]) * 1000
            assert gap_ms < max_gap_ms, f"Gap between events {i-1} and {i} is {gap_ms:.2f}ms, exceeds {max_gap_ms}ms"
        
        # Cleanup
        await engine.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_event_delivery_content_validation(self):
        """Test that WebSocket events contain correct and complete content.
        
        BVJ: Validates that WebSocket events carry meaningful data for users,
        ensuring chat interface can display relevant agent progress information.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="content_test_user",
            thread_id="content_test_thread",
            run_id="content_test_run", 
            request_id="content_test_req"
        )
        
        # Create content-aware event tracker
        tracker = EventDeliveryTracker()
        event_content = {}
        
        async def content_event_tracker(event_type: str, *args, **kwargs) -> bool:
            await tracker.track_event(event_type, *args, **kwargs)
            
            # Store content for validation
            event_content[event_type] = {
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            }
            return True
        
        # Create mock WebSocket emitter with content tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: content_event_tracker('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: content_event_tracker('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: content_event_tracker('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: content_event_tracker('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: content_event_tracker('agent_completed', *a, **k))
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
            user_id="content_test_user",
            thread_id="content_test_thread",
            run_id="content_test_run",
            request_id="content_test_req",
            agent_name="content_validation_agent",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            metadata={"test_mode": True, "validation": "content"}
        )
        
        # Execute agent with rich content
        await engine._send_user_agent_started(context)
        
        await engine._send_user_agent_thinking(
            context, 
            "Analyzing complex data patterns for optimization opportunities", 
            step_number=1
        )
        
        # Tool execution with specific parameters
        tool_dispatcher = engine.get_tool_dispatcher()
        await tool_dispatcher.execute_tool("advanced_analyzer", {
            "analysis_type": "comprehensive",
            "data_sources": ["database", "logs", "metrics"],
            "output_format": "detailed_report"
        })
        
        # Complete with detailed result
        result = AgentExecutionResult(
            success=True,
            agent_name="content_validation_agent",
            execution_time=4.7,
            state=None,
            metadata={
                "insights_generated": 12,
                "recommendations": ["optimize_queries", "scale_resources", "implement_caching"],
                "potential_savings": "$25000/month",
                "confidence_score": 0.87
            }
        )
        await engine._send_user_agent_completed(context, result)
        
        # Validate event content
        assert len(event_content) >= 5, "Should have content for all critical events"
        
        # Validate agent_started content
        if 'agent_started' in event_content:
            started_content = event_content['agent_started']
            assert len(started_content['args']) > 0, "agent_started should have agent name argument"
            # Should include context information
            if 'context' in started_content['kwargs']:
                context_data = started_content['kwargs']['context']
                assert 'user_id' in context_data, "Should include user_id in context"
                assert context_data['user_id'] == "content_test_user", "Should have correct user_id"
        
        # Validate agent_thinking content
        if 'agent_thinking' in event_content:
            thinking_content = event_content['agent_thinking']
            assert len(thinking_content['args']) >= 2, "agent_thinking should have agent name and reasoning"
            # Reasoning should be meaningful
            reasoning = thinking_content['args'][1] if len(thinking_content['args']) > 1 else ""
            assert len(reasoning) > 10, "Reasoning should be descriptive"
            assert "optimization" in reasoning.lower(), "Should contain relevant business content"
        
        # Validate tool events content
        if 'tool_executing' in event_content:
            tool_exec_content = event_content['tool_executing']
            assert len(tool_exec_content['args']) > 0, "tool_executing should have tool name"
            tool_name = tool_exec_content['args'][0]
            assert tool_name == "advanced_analyzer", "Should have correct tool name"
        
        if 'tool_completed' in event_content:
            tool_comp_content = event_content['tool_completed']
            assert len(tool_comp_content['args']) >= 2, "tool_completed should have tool name and result"
            # Result should contain meaningful data
            if len(tool_comp_content['args']) > 1:
                tool_result = tool_comp_content['args'][1]
                assert isinstance(tool_result, dict), "Tool result should be structured data"
                if 'result' in tool_result:
                    assert 'success' in tool_result['result'], "Should indicate tool execution success"
        
        # Validate agent_completed content  
        if 'agent_completed' in event_content:
            completed_content = event_content['agent_completed']
            assert len(completed_content['args']) >= 2, "agent_completed should have agent name and result"
            
            if 'result' in completed_content['kwargs']:
                result_data = completed_content['kwargs']['result']
                assert 'success' in result_data, "Result should indicate success status"
                assert 'duration_ms' in result_data, "Result should include timing information"
                assert result_data['success'] is True, "Result should indicate successful execution"
                assert result_data['duration_ms'] > 0, "Duration should be positive"
        
        # Verify all events have timestamps
        for event_type, content in event_content.items():
            assert 'timestamp' in content, f"Event {event_type} should have timestamp"
            assert isinstance(content['timestamp'], (int, float)), f"Event {event_type} timestamp should be numeric"
        
        # Cleanup
        await engine.cleanup()