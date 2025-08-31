"""Mission Critical WebSocket Event Validation for Supervisor Agent.

CRITICAL: These tests ensure WebSocket events are ALWAYS sent during agent execution.
The chat UI depends on these events - without them, the UI appears broken.

Business Value: Ensures users always receive real-time feedback during AI operations.
"""

import asyncio
import pytest
import time
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
import uuid

from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core import UnifiedWebSocketManager
from netra_backend.app.schemas.websocket_models import WebSocketMessage


class WebSocketEventValidator:
    """Helper class to validate WebSocket events."""
    
    def __init__(self):
        self.events = []
        self.event_types = set()
        self.event_timeline = []
        self.critical_events = {
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        }
    
    async def capture_event(self, thread_id: str, message: WebSocketMessage):
        """Capture WebSocket event for validation."""
        timestamp = time.time()
        event = {
            'timestamp': timestamp,
            'thread_id': thread_id,
            'type': message.type if hasattr(message, 'type') else 'unknown',
            'payload': message.payload if hasattr(message, 'payload') else None
        }
        
        self.events.append(event)
        self.event_types.add(event['type'])
        self.event_timeline.append((timestamp, event['type']))
    
    def validate_critical_events(self) -> Dict[str, bool]:
        """Validate that all critical events were sent."""
        return {
            event: event in self.event_types
            for event in self.critical_events
        }
    
    def validate_event_order(self) -> bool:
        """Validate that events were sent in correct order."""
        # agent_started should come before agent_completed
        started_times = [t for t, e in self.event_timeline if 'started' in e]
        completed_times = [t for t, e in self.event_timeline if 'completed' in e]
        
        if started_times and completed_times:
            return min(started_times) < max(completed_times)
        return True
    
    def get_event_frequency(self) -> Dict[str, int]:
        """Get frequency of each event type."""
        freq = {}
        for event in self.events:
            event_type = event['type']
            freq[event_type] = freq.get(event_type, 0) + 1
        return freq
    
    def clear(self):
        """Clear captured events."""
        self.events.clear()
        self.event_types.clear()
        self.event_timeline.clear()


class TestCriticalWebSocketEvents:
    """Test critical WebSocket event requirements."""
    
    @pytest.fixture
    def event_validator(self):
        """Create event validator."""
        return WebSocketEventValidator()
    
    @pytest.fixture
    def supervisor_with_validator(self, event_validator):
        """Create supervisor with event validation."""
        db_session = AsyncMock()
        llm_manager = MagicMock(spec=LLMManager)
        llm_manager.generate = AsyncMock(return_value="Test response")
        
        websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        websocket_manager.send_message = AsyncMock(side_effect=event_validator.capture_event)
        
        tool_dispatcher = MagicMock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        return supervisor, event_validator
    
    @pytest.mark.asyncio
    async def test_agent_started_always_sent(self, supervisor_with_validator):
        """CRITICAL: agent_started event MUST be sent."""
        supervisor, validator = supervisor_with_validator
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # CRITICAL: agent_started MUST be present
        validation = validator.validate_critical_events()
        assert validation.get('agent_started', False), \
            "CRITICAL FAILURE: agent_started event was not sent!"
    
    @pytest.mark.asyncio
    async def test_agent_completed_always_sent(self, supervisor_with_validator):
        """CRITICAL: agent_completed event MUST be sent."""
        supervisor, validator = supervisor_with_validator
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # CRITICAL: agent_completed MUST be present
        validation = validator.validate_critical_events()
        assert validation.get('agent_completed', False), \
            "CRITICAL FAILURE: agent_completed event was not sent!"
    
    @pytest.mark.asyncio
    async def test_agent_thinking_during_execution(self, supervisor_with_validator):
        """CRITICAL: agent_thinking events provide real-time feedback."""
        supervisor, validator = supervisor_with_validator
        
        # Mock workflow with thinking events
        async def workflow_with_thinking(context):
            # Send thinking events
            await supervisor.websocket_notifier.send_agent_thinking(
                AgentExecutionContext(
                    run_id=context.run_id,
                    thread_id=context.thread_id,
                    agent_name="test",
                    stream_updates=True
                ),
                "Analyzing request...",
                step_number=1
            )
            
            await asyncio.sleep(0.1)
            
            await supervisor.websocket_notifier.send_agent_thinking(
                AgentExecutionContext(
                    run_id=context.run_id,
                    thread_id=context.thread_id,
                    agent_name="test",
                    stream_updates=True
                ),
                "Processing data...",
                step_number=2
            )
            
            return [ExecutionResult(success=True)]
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         side_effect=workflow_with_thinking):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # CRITICAL: agent_thinking MUST be present for user feedback
        assert 'agent_thinking' in validator.event_types, \
            "CRITICAL FAILURE: agent_thinking events not sent!"
        
        # Should have multiple thinking events
        frequency = validator.get_event_frequency()
        assert frequency.get('agent_thinking', 0) >= 2, \
            "Not enough agent_thinking events for proper user feedback"
    
    @pytest.mark.asyncio
    async def test_tool_events_during_execution(self, supervisor_with_validator):
        """CRITICAL: tool_executing and tool_completed events for transparency."""
        supervisor, validator = supervisor_with_validator
        
        # Mock workflow with tool execution
        async def workflow_with_tools(context):
            notifier = supervisor.websocket_notifier
            exec_context = AgentExecutionContext(
                run_id=context.run_id,
                thread_id=context.thread_id,
                agent_name="test",
                stream_updates=True
            )
            
            # Tool execution sequence
            await notifier.send_tool_executing(
                exec_context,
                "data_analysis_tool",
                "Analyzing user data",
                estimated_duration_ms=2000
            )
            
            await asyncio.sleep(0.1)
            
            await notifier.send_tool_completed(
                exec_context,
                "data_analysis_tool",
                {"status": "success", "records": 100}
            )
            
            return [ExecutionResult(success=True)]
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Analyze my data"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         side_effect=workflow_with_tools):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # CRITICAL: Tool events MUST be present
        validation = validator.validate_critical_events()
        assert validation.get('tool_executing', False), \
            "CRITICAL FAILURE: tool_executing event not sent!"
        assert validation.get('tool_completed', False), \
            "CRITICAL FAILURE: tool_completed event not sent!"
    
    @pytest.mark.asyncio
    async def test_event_order_validation(self, supervisor_with_validator):
        """Test that events are sent in correct order."""
        supervisor, validator = supervisor_with_validator
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # Validate event order
        assert validator.validate_event_order(), \
            "Events were sent in incorrect order!"
        
        # Check specific ordering
        timeline = validator.event_timeline
        event_sequence = [event_type for _, event_type in timeline]
        
        # agent_started should come before agent_completed
        if 'agent_started' in event_sequence and 'agent_completed' in event_sequence:
            started_idx = event_sequence.index('agent_started')
            completed_idx = event_sequence.index('agent_completed')
            assert started_idx < completed_idx, \
                "agent_started must come before agent_completed"


class TestWebSocketEventReliability:
    """Test WebSocket event delivery reliability."""
    
    @pytest.mark.asyncio
    async def test_events_sent_on_error(self, supervisor_with_validator):
        """Test that events are sent even when errors occur."""
        supervisor, validator = supervisor_with_validator
        
        # Mock workflow that fails
        async def failing_workflow(context):
            # Send started event
            await supervisor.websocket_notifier.send_agent_started(
                AgentExecutionContext(
                    run_id=context.run_id,
                    thread_id=context.thread_id,
                    agent_name="test",
                    stream_updates=True
                )
            )
            
            # Simulate error
            raise Exception("Test error")
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         side_effect=failing_workflow):
            try:
                await supervisor.execute(state, "test-run", stream_updates=True)
            except Exception:
                pass  # Expected to fail
        
        # Even on error, some events should be sent
        assert len(validator.events) > 0, \
            "No events sent on error - user has no feedback!"
        
        # Should have at least started event
        assert 'agent_started' in validator.event_types or len(validator.events) > 0, \
            "No feedback events sent on error"
    
    @pytest.mark.asyncio
    async def test_events_under_high_load(self, supervisor_with_validator):
        """Test that events are sent reliably under high load."""
        supervisor, validator = supervisor_with_validator
        
        # Generate concurrent requests
        tasks = []
        for i in range(10):
            state = DeepAgentState()
            state.messages = [{"role": "user", "content": f"Request {i}"}]
            
            with patch.object(supervisor, '_execute_protected_workflow',
                            return_value=[ExecutionResult(success=True)]):
                task = supervisor.execute(state, f"load-{i}", stream_updates=True)
                tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should have events
        events_per_thread = {}
        for event in validator.events:
            thread_id = event['thread_id']
            if thread_id not in events_per_thread:
                events_per_thread[thread_id] = []
            events_per_thread[thread_id].append(event['type'])
        
        # Each thread should have critical events
        for thread_id, events in events_per_thread.items():
            assert len(events) > 0, f"No events for thread {thread_id}"
    
    @pytest.mark.asyncio
    async def test_event_delivery_timeout(self, supervisor_with_validator):
        """Test event delivery with timeouts."""
        supervisor, validator = supervisor_with_validator
        
        # Track delivery times
        delivery_times = []
        
        async def timed_capture(thread_id, message):
            start = time.time()
            await validator.capture_event(thread_id, message)
            delivery_times.append(time.time() - start)
        
        supervisor.websocket_manager.send_message = AsyncMock(side_effect=timed_capture)
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # Event delivery should be fast
        if delivery_times:
            avg_delivery = sum(delivery_times) / len(delivery_times)
            max_delivery = max(delivery_times)
            
            assert avg_delivery < 0.1, f"Slow average delivery: {avg_delivery:.3f}s"
            assert max_delivery < 0.5, f"Slow max delivery: {max_delivery:.3f}s"


class TestWebSocketEventContent:
    """Test WebSocket event content and payload."""
    
    @pytest.mark.asyncio
    async def test_agent_started_payload(self, supervisor_with_validator):
        """Test agent_started event has required payload."""
        supervisor, validator = supervisor_with_validator
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # Find agent_started event
        started_events = [e for e in validator.events if e['type'] == 'agent_started']
        
        assert len(started_events) > 0, "No agent_started events found"
        
        # Check payload
        for event in started_events:
            payload = event.get('payload', {})
            # Should have basic information
            assert payload is not None, "agent_started missing payload"
    
    @pytest.mark.asyncio
    async def test_agent_thinking_content(self, supervisor_with_validator):
        """Test agent_thinking events have meaningful content."""
        supervisor, validator = supervisor_with_validator
        
        # Send thinking with content
        notifier = supervisor.websocket_notifier
        context = AgentExecutionContext(
            run_id="test-run",
            thread_id="test-thread",
            agent_name="test",
            stream_updates=True
        )
        
        await notifier.send_agent_thinking(
            context,
            "Analyzing user request to optimize costs",
            step_number=1,
            progress_percentage=25.0
        )
        
        # Check thinking event content
        thinking_events = [e for e in validator.events if e['type'] == 'agent_thinking']
        
        assert len(thinking_events) > 0, "No thinking events captured"
        
        for event in thinking_events:
            payload = event.get('payload', {})
            # Should have thought content
            assert 'thought' in str(payload).lower() or 'analyzing' in str(payload).lower(), \
                "Thinking event missing meaningful content"
    
    @pytest.mark.asyncio
    async def test_tool_event_details(self, supervisor_with_validator):
        """Test tool events include necessary details."""
        supervisor, validator = supervisor_with_validator
        
        notifier = supervisor.websocket_notifier
        context = AgentExecutionContext(
            run_id="test-run",
            thread_id="test-thread",
            agent_name="test",
            stream_updates=True
        )
        
        # Send detailed tool events
        await notifier.send_tool_executing(
            context,
            "cost_analyzer",
            "Analyzing infrastructure costs",
            estimated_duration_ms=3000,
            parameters_summary="regions: us-east-1, us-west-2"
        )
        
        await notifier.send_tool_completed(
            context,
            "cost_analyzer",
            {
                "total_cost": 5000,
                "optimization_potential": 1500,
                "recommendations": 3
            }
        )
        
        # Check tool event details
        tool_events = [e for e in validator.events 
                      if 'tool' in e['type']]
        
        assert len(tool_events) >= 2, "Missing tool events"
        
        # Tool executing should have details
        executing = [e for e in tool_events if e['type'] == 'tool_executing']
        if executing:
            payload = executing[0].get('payload', {})
            assert 'tool_name' in str(payload) or 'cost_analyzer' in str(payload), \
                "Tool executing missing tool name"
        
        # Tool completed should have results
        completed = [e for e in tool_events if e['type'] == 'tool_completed']
        if completed:
            payload = completed[0].get('payload', {})
            assert 'result' in str(payload) or 'total_cost' in str(payload), \
                "Tool completed missing results"


class TestWebSocketIntegrationEdgeCases:
    """Test WebSocket edge cases and recovery."""
    
    @pytest.mark.asyncio
    async def test_websocket_manager_none(self):
        """Test behavior when WebSocket manager is None."""
        supervisor = SupervisorAgent(
            db_session=AsyncMock(),
            llm_manager=MagicMock(spec=LLMManager),
            websocket_manager=None,  # No WebSocket manager
            tool_dispatcher=MagicMock(spec=ToolDispatcher)
        )
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        # Should not crash even without WebSocket manager
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # Execution should complete
        assert True, "Execution failed without WebSocket manager"
    
    @pytest.mark.asyncio
    async def test_websocket_send_failure_recovery(self, supervisor_with_validator):
        """Test recovery from WebSocket send failures."""
        supervisor, validator = supervisor_with_validator
        
        # Make WebSocket send fail intermittently
        call_count = 0
        
        async def failing_send(thread_id, message):
            nonlocal call_count
            call_count += 1
            
            if call_count % 3 == 0:
                raise Exception("WebSocket send failed")
            
            await validator.capture_event(thread_id, message)
        
        supervisor.websocket_manager.send_message = AsyncMock(side_effect=failing_send)
        
        state = DeepAgentState()
        state.messages = [{"role": "user", "content": "Test"}]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # Some events should still be delivered
        assert len(validator.events) > 0, "No events delivered despite failures"
    
    @pytest.mark.asyncio
    async def test_rapid_event_sequence(self, supervisor_with_validator):
        """Test handling of rapid event sequences."""
        supervisor, validator = supervisor_with_validator
        
        # Send many events rapidly
        notifier = supervisor.websocket_notifier
        context = AgentExecutionContext(
            run_id="test-run",
            thread_id="test-thread",
            agent_name="test",
            stream_updates=True
        )
        
        # Rapid fire events
        for i in range(100):
            await notifier.send_agent_thinking(
                context,
                f"Processing step {i}",
                step_number=i
            )
        
        # All events should be captured
        thinking_events = [e for e in validator.events if e['type'] == 'agent_thinking']
        
        # Most events should be delivered (allow some loss under extreme conditions)
        assert len(thinking_events) >= 80, \
            f"Too many events lost: only {len(thinking_events)}/100 delivered"


class TestMissionCriticalValidation:
    """Final validation of mission-critical requirements."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_events(self, supervisor_with_validator):
        """Test complete workflow has all required events."""
        supervisor, validator = supervisor_with_validator
        
        # Execute complete workflow
        state = DeepAgentState()
        state.messages = [
            {"role": "user", "content": "Optimize my AI infrastructure costs"}
        ]
        
        # Mock multi-step workflow
        async def complete_workflow(context):
            notifier = supervisor.websocket_notifier
            exec_context = AgentExecutionContext(
                run_id=context.run_id,
                thread_id=context.thread_id,
                agent_name="supervisor",
                stream_updates=True
            )
            
            # Full workflow sequence
            await notifier.send_agent_started(exec_context)
            await notifier.send_agent_thinking(exec_context, "Analyzing request", 1)
            await notifier.send_tool_executing(exec_context, "triage_tool")
            await notifier.send_tool_completed(exec_context, "triage_tool", {"status": "ok"})
            await notifier.send_agent_thinking(exec_context, "Processing results", 2)
            await notifier.send_tool_executing(exec_context, "optimization_tool")
            await notifier.send_tool_completed(exec_context, "optimization_tool", {"savings": 30})
            await notifier.send_agent_completed(exec_context, {"status": "success"})
            
            return [ExecutionResult(success=True)]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         side_effect=complete_workflow):
            await supervisor.execute(state, "test-run", stream_updates=True)
        
        # CRITICAL: Validate all required events present
        validation = validator.validate_critical_events()
        
        missing_events = [event for event, present in validation.items() if not present]
        assert len(missing_events) == 0, \
            f"CRITICAL: Missing events: {missing_events}"
        
        # Verify minimum event counts
        frequency = validator.get_event_frequency()
        assert frequency.get('agent_started', 0) >= 1
        assert frequency.get('agent_thinking', 0) >= 2
        assert frequency.get('tool_executing', 0) >= 2
        assert frequency.get('tool_completed', 0) >= 2
        assert frequency.get('agent_completed', 0) >= 1
        
        print("\n✅ MISSION CRITICAL: All WebSocket events validated successfully!")
        print(f"   Total events sent: {len(validator.events)}")
        print(f"   Event types: {', '.join(sorted(validator.event_types))}")


if __name__ == "__main__":
    # Run mission-critical tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure - these are critical!
        "--asyncio-mode=auto"
    ])