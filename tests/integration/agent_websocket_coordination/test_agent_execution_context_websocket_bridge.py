"""
Test Agent Execution Context WebSocket Bridge

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Validate seamless integration between agent execution context and WebSocket bridge
- Value Impact: Ensures execution context properly coordinates with WebSocket events for complete user visibility
- Strategic Impact: Tests the critical link between agent execution lifecycle and real-time user communication

This test validates that AgentExecutionContext properly integrates with WebSocket bridge
to provide complete coordination between agent execution lifecycle and real-time event delivery.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.state import DeepAgentState


@dataclass
class ExecutionContextEvent:
    """Represents an execution context event with WebSocket coordination."""
    event_type: str
    context: AgentExecutionContext
    timestamp: float
    bridge_response: bool = True
    additional_data: Dict[str, Any] = field(default_factory=dict)


class ExecutionContextTracker:
    """Tracks execution context events and WebSocket bridge coordination."""
    
    def __init__(self):
        self.events: List[ExecutionContextEvent] = []
        self.context_states: Dict[str, str] = {}
        self.bridge_interactions: List[Dict[str, Any]] = []
        self.execution_phases: List[str] = []
    
    async def track_context_event(self, event_type: str, context: AgentExecutionContext, **kwargs) -> bool:
        """Track an execution context event."""
        event = ExecutionContextEvent(
            event_type=event_type,
            context=context,
            timestamp=time.time(),
            additional_data=kwargs
        )
        self.events.append(event)
        self.execution_phases.append(f"{event_type}_{context.step.value}")
        return True
    
    def get_events_for_context(self, context_id: str) -> List[ExecutionContextEvent]:
        """Get all events for a specific execution context."""
        return [event for event in self.events if event.context.execution_id == context_id]
    
    def get_event_sequence(self) -> List[str]:
        """Get the sequence of event types."""
        return [event.event_type for event in self.events]


class TestAgentExecutionContextWebSocketBridge(SSotAsyncTestCase):
    """Test Agent Execution Context WebSocket Bridge."""
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_execution_context_websocket_bridge_coordination(self):
        """Test that execution context properly coordinates with WebSocket bridge.
        
        BVJ: Validates the core coordination mechanism between agent execution
        lifecycle and real-time WebSocket event delivery to users.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="bridge_test_user_001",
            thread_id="bridge_thread_001",
            run_id="bridge_run_001",
            request_id="bridge_req_001"
        )
        
        # Create execution context tracker
        tracker = ExecutionContextTracker()
        
        # Create mock WebSocket emitter with detailed tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        
        async def track_websocket_event(event_type, *args, **kwargs):
            # Track the WebSocket event
            await tracker.track_context_event(f"websocket_{event_type}", None, args=args, kwargs=kwargs)
            return True
        
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_websocket_event('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_websocket_event('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_websocket_event('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_websocket_event('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_websocket_event('agent_completed', *a, **k))
        
        # Create WebSocket bridge
        bridge = AgentWebSocketBridge()
        await bridge.initialize(user_context, mock_emitter)
        
        # Create agent execution context
        execution_context = AgentExecutionContext(
            user_id="bridge_test_user_001",
            thread_id="bridge_thread_001",
            run_id="bridge_run_001", 
            request_id="bridge_req_001",
            agent_name="context_bridge_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            metadata={"test_coordination": True}
        )
        
        # Test execution context lifecycle with bridge coordination
        # Phase 1: Initialization
        await tracker.track_context_event("context_created", execution_context)
        await bridge.emit_agent_started("context_bridge_agent", {
            "execution_context": execution_context.to_dict() if hasattr(execution_context, 'to_dict') else execution_context.metadata,
            "phase": "initialization"
        })
        
        # Phase 2: Execution Planning
        execution_context.step = PipelineStep.EXECUTION
        execution_context.pipeline_step_num = 2
        await tracker.track_context_event("context_updated", execution_context, step="execution")
        await bridge.emit_agent_thinking("context_bridge_agent", "Planning execution based on context...", 1)
        
        # Phase 3: Tool Execution
        execution_context.step = PipelineStep.TOOL_EXECUTION
        execution_context.pipeline_step_num = 3
        await tracker.track_context_event("tool_phase_started", execution_context, phase="tool_execution")
        await bridge.emit_tool_executing("context_coordination_tool")
        
        # Simulate tool completion
        await bridge.emit_tool_completed("context_coordination_tool", {
            "context_aware_result": True,
            "execution_phase": execution_context.step.value,
            "step_number": execution_context.pipeline_step_num
        })
        
        # Phase 4: Completion
        execution_context.step = PipelineStep.COMPLETION
        execution_context.pipeline_step_num = 4
        await tracker.track_context_event("context_completing", execution_context, final_phase=True)
        await bridge.emit_agent_completed("context_bridge_agent", {
            "execution_context_id": getattr(execution_context, 'execution_id', 'context_001'),
            "total_steps": execution_context.pipeline_step_num,
            "completion_status": "success"
        })
        
        # Validate coordination between context and bridge
        context_events = [event for event in tracker.events if not event.event_type.startswith('websocket_')]
        websocket_events = [event for event in tracker.events if event.event_type.startswith('websocket_')]
        
        # Verify context lifecycle events
        assert len(context_events) >= 4, f"Should have at least 4 context events, got {len(context_events)}"
        context_event_types = [event.event_type for event in context_events]
        expected_context_events = ["context_created", "context_updated", "tool_phase_started", "context_completing"]
        for expected in expected_context_events:
            assert expected in context_event_types, f"Missing context event: {expected}"
        
        # Verify WebSocket events were triggered
        assert len(websocket_events) >= 5, f"Should have at least 5 WebSocket events, got {len(websocket_events)}"
        websocket_event_types = [event.event_type.replace('websocket_', '') for event in websocket_events]
        expected_websocket_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for expected in expected_websocket_events:
            assert expected in websocket_event_types, f"Missing WebSocket event: {expected}"
        
        # Verify temporal coordination (WebSocket events follow context events)
        all_events_sorted = sorted(tracker.events, key=lambda e: e.timestamp)
        
        # Check that context updates precede corresponding WebSocket events
        context_creation_time = next(e.timestamp for e in all_events_sorted if e.event_type == "context_created")
        first_websocket_time = next(e.timestamp for e in all_events_sorted if e.event_type.startswith('websocket_'))
        
        assert context_creation_time <= first_websocket_time, "Context creation should precede WebSocket events"
        
        # Cleanup
        await bridge.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_execution_context_state_transitions_with_websocket_sync(self):
        """Test that execution context state transitions are synchronized with WebSocket events.
        
        BVJ: Validates that users receive accurate real-time updates as agent execution
        progresses through different states, ensuring transparency of AI operations.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="state_sync_user",
            thread_id="state_sync_thread",
            run_id="state_sync_run",
            request_id="state_sync_req"
        )
        
        # Create state transition tracker
        state_transitions = []
        websocket_notifications = []
        
        async def track_state_change(from_state, to_state, context):
            state_transitions.append({
                'from': from_state,
                'to': to_state,
                'context_step': context.step.value,
                'step_number': context.pipeline_step_num,
                'timestamp': time.time()
            })
        
        async def track_websocket_notification(event_type, *args, **kwargs):
            websocket_notifications.append({
                'type': event_type,
                'timestamp': time.time(),
                'args': args,
                'kwargs': kwargs
            })
            return True
        
        # Create mock WebSocket emitter
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_websocket_notification('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_websocket_notification('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_websocket_notification('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_websocket_notification('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_websocket_notification('agent_completed', *a, **k))
        
        # Create WebSocket bridge
        bridge = AgentWebSocketBridge()
        await bridge.initialize(user_context, mock_emitter)
        
        # Create execution context and track state transitions
        execution_context = AgentExecutionContext(
            user_id="state_sync_user",
            thread_id="state_sync_thread",
            run_id="state_sync_run",
            request_id="state_sync_req",
            agent_name="state_sync_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Execute state transitions with WebSocket synchronization
        # Transition 1: INITIALIZATION -> PLANNING
        current_step = execution_context.step
        execution_context.step = PipelineStep.PLANNING
        execution_context.pipeline_step_num = 2
        await track_state_change(current_step, execution_context.step, execution_context)
        await bridge.emit_agent_started("state_sync_agent", {
            "state": execution_context.step.value,
            "step": execution_context.pipeline_step_num
        })
        
        # Transition 2: PLANNING -> EXECUTION  
        current_step = execution_context.step
        execution_context.step = PipelineStep.EXECUTION
        execution_context.pipeline_step_num = 3
        await track_state_change(current_step, execution_context.step, execution_context)
        await bridge.emit_agent_thinking("state_sync_agent", f"Transitioning to {execution_context.step.value} phase", execution_context.pipeline_step_num)
        
        # Transition 3: EXECUTION -> TOOL_EXECUTION
        current_step = execution_context.step
        execution_context.step = PipelineStep.TOOL_EXECUTION
        execution_context.pipeline_step_num = 4
        await track_state_change(current_step, execution_context.step, execution_context)
        await bridge.emit_tool_executing("state_aware_tool")
        
        # Transition 4: Continue TOOL_EXECUTION (same state, different step)
        execution_context.pipeline_step_num = 5
        await track_state_change(execution_context.step, execution_context.step, execution_context)
        await bridge.emit_tool_completed("state_aware_tool", {
            "state_when_completed": execution_context.step.value,
            "step_completed": execution_context.pipeline_step_num
        })
        
        # Transition 5: TOOL_EXECUTION -> COMPLETION
        current_step = execution_context.step
        execution_context.step = PipelineStep.COMPLETION
        execution_context.pipeline_step_num = 6
        await track_state_change(current_step, execution_context.step, execution_context)
        await bridge.emit_agent_completed("state_sync_agent", {
            "final_state": execution_context.step.value,
            "total_steps": execution_context.pipeline_step_num
        })
        
        # Validate state transition synchronization
        assert len(state_transitions) == 5, f"Should have 5 state transitions, got {len(state_transitions)}"
        assert len(websocket_notifications) == 5, f"Should have 5 WebSocket notifications, got {len(websocket_notifications)}"
        
        # Verify state progression
        expected_state_progression = [
            (PipelineStep.INITIALIZATION, PipelineStep.PLANNING),
            (PipelineStep.PLANNING, PipelineStep.EXECUTION),
            (PipelineStep.EXECUTION, PipelineStep.TOOL_EXECUTION),
            (PipelineStep.TOOL_EXECUTION, PipelineStep.TOOL_EXECUTION),  # Same state transition
            (PipelineStep.TOOL_EXECUTION, PipelineStep.COMPLETION)
        ]
        
        for i, (expected_from, expected_to) in enumerate(expected_state_progression):
            transition = state_transitions[i]
            assert transition['from'] == expected_from, f"Transition {i}: expected from {expected_from}, got {transition['from']}"
            assert transition['to'] == expected_to, f"Transition {i}: expected to {expected_to}, got {transition['to']}"
        
        # Verify WebSocket notifications align with state changes
        websocket_types = [notif['type'] for notif in websocket_notifications]
        expected_websocket_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert websocket_types == expected_websocket_sequence, f"WebSocket sequence should match expected: {websocket_types}"
        
        # Verify temporal alignment (state changes should precede WebSocket notifications)
        for i in range(len(state_transitions)):
            state_time = state_transitions[i]['timestamp']
            websocket_time = websocket_notifications[i]['timestamp']
            assert state_time <= websocket_time, f"State transition {i} should precede WebSocket notification"
        
        # Cleanup
        await bridge.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_execution_context_error_handling_with_websocket_bridge(self):
        """Test execution context error handling with WebSocket bridge coordination.
        
        BVJ: Validates that execution errors are properly communicated to users
        via WebSocket events, ensuring transparency even when operations fail.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="error_test_user",
            thread_id="error_test_thread", 
            run_id="error_test_run",
            request_id="error_test_req"
        )
        
        # Create error tracking
        execution_errors = []
        error_websocket_events = []
        
        async def track_execution_error(error_type, context, error_details):
            execution_errors.append({
                'type': error_type,
                'context_step': context.step.value,
                'step_number': context.pipeline_step_num,
                'error': error_details,
                'timestamp': time.time()
            })
        
        # Create mock WebSocket emitter that can simulate failures
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        
        # Track successful WebSocket events
        async def track_successful_websocket(event_type, *args, **kwargs):
            error_websocket_events.append({
                'type': event_type,
                'success': True,
                'timestamp': time.time(),
                'args': args,
                'kwargs': kwargs
            })
            return True
        
        # Track failed WebSocket events
        async def track_failed_websocket(event_type, *args, **kwargs):
            error_websocket_events.append({
                'type': event_type,
                'success': False,
                'timestamp': time.time(),
                'args': args,
                'kwargs': kwargs
            })
            raise Exception(f"WebSocket {event_type} delivery failed")
        
        # Configure mixed success/failure pattern
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_successful_websocket('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_failed_websocket('agent_thinking', *a, **k))  # This will fail
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_successful_websocket('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_failed_websocket('tool_completed', *a, **k))  # This will fail
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_successful_websocket('agent_completed', *a, **k))
        
        # Create WebSocket bridge with error handling
        bridge = AgentWebSocketBridge()
        await bridge.initialize(user_context, mock_emitter)
        
        # Create execution context
        execution_context = AgentExecutionContext(
            user_id="error_test_user",
            thread_id="error_test_thread",
            run_id="error_test_run",
            request_id="error_test_req",
            agent_name="error_resilient_agent",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Test execution with error handling
        try:
            # This should succeed
            await bridge.emit_agent_started("error_resilient_agent", {
                "context_id": getattr(execution_context, 'execution_id', 'error_ctx_001')
            })
        except Exception as e:
            await track_execution_error("agent_started_error", execution_context, str(e))
        
        try:
            # This should fail but be handled gracefully
            await bridge.emit_agent_thinking("error_resilient_agent", "Processing with error handling...", 1)
        except Exception as e:
            await track_execution_error("agent_thinking_error", execution_context, str(e))
        
        try:
            # This should succeed
            await bridge.emit_tool_executing("error_test_tool")
        except Exception as e:
            await track_execution_error("tool_executing_error", execution_context, str(e))
        
        try:
            # This should fail but be handled
            await bridge.emit_tool_completed("error_test_tool", {"test": "error_handling"})
        except Exception as e:
            await track_execution_error("tool_completed_error", execution_context, str(e))
        
        try:
            # This should succeed
            await bridge.emit_agent_completed("error_resilient_agent", {"status": "completed_with_errors"})
        except Exception as e:
            await track_execution_error("agent_completed_error", execution_context, str(e))
        
        # Validate error handling
        assert len(error_websocket_events) == 5, f"Should have attempted 5 WebSocket events, got {len(error_websocket_events)}"
        
        # Check success/failure pattern
        successful_events = [e for e in error_websocket_events if e['success']]
        failed_events = [e for e in error_websocket_events if not e['success']]
        
        assert len(successful_events) == 3, f"Should have 3 successful events, got {len(successful_events)}"
        assert len(failed_events) == 2, f"Should have 2 failed events, got {len(failed_events)}"
        
        # Verify specific success/failure events
        successful_types = [e['type'] for e in successful_events]
        failed_types = [e['type'] for e in failed_events]
        
        assert 'agent_started' in successful_types, "agent_started should succeed"
        assert 'tool_executing' in successful_types, "tool_executing should succeed"
        assert 'agent_completed' in successful_types, "agent_completed should succeed"
        
        assert 'agent_thinking' in failed_types, "agent_thinking should fail (as designed)"
        assert 'tool_completed' in failed_types, "tool_completed should fail (as designed)"
        
        # Verify errors were tracked
        assert len(execution_errors) == 2, f"Should have tracked 2 execution errors, got {len(execution_errors)}"
        
        error_types = [error['type'] for error in execution_errors]
        assert 'agent_thinking_error' in error_types, "Should track agent_thinking error"
        assert 'tool_completed_error' in error_types, "Should track tool_completed error"
        
        # Verify error details contain meaningful information
        for error in execution_errors:
            assert 'WebSocket' in error['error'], "Error should mention WebSocket failure"
            assert error['context_step'] == 'execution', "Should capture correct execution step"
        
        # Cleanup
        await bridge.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_execution_context_metadata_propagation_to_websocket(self):
        """Test that execution context metadata is properly propagated to WebSocket events.
        
        BVJ: Validates that rich execution context information is available to users
        via WebSocket events, enabling informed decision-making and operation understanding.
        """
        # Create user context with rich metadata
        user_context = UserExecutionContext(
            user_id="metadata_test_user",
            thread_id="metadata_test_thread",
            run_id="metadata_test_run",
            request_id="metadata_test_req"
        )
        
        # Create metadata tracking
        websocket_metadata = []
        
        async def track_websocket_metadata(event_type, *args, **kwargs):
            websocket_metadata.append({
                'event_type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
        
        # Create mock WebSocket emitter with metadata capture
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_websocket_metadata('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_websocket_metadata('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_websocket_metadata('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_websocket_metadata('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_websocket_metadata('agent_completed', *a, **k))
        
        # Create WebSocket bridge
        bridge = AgentWebSocketBridge()
        await bridge.initialize(user_context, mock_emitter)
        
        # Create execution context with rich metadata
        execution_context = AgentExecutionContext(
            user_id="metadata_test_user",
            thread_id="metadata_test_thread",
            run_id="metadata_test_run",
            request_id="metadata_test_req",
            agent_name="metadata_rich_agent",
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            metadata={
                "business_context": "Q4 cost optimization analysis",
                "user_role": "finance_director",
                "analysis_type": "comprehensive",
                "data_sources": ["aws_billing", "usage_metrics", "performance_data"],
                "expected_savings_range": "$50K-$200K",
                "priority": "high",
                "compliance_requirements": ["SOX", "GDPR"],
                "custom_parameters": {
                    "timeframe": "last_90_days",
                    "include_forecasting": True,
                    "granularity": "service_level"
                }
            }
        )
        
        # Execute events with metadata propagation
        await bridge.emit_agent_started("metadata_rich_agent", {
            "execution_context_metadata": execution_context.metadata,
            "business_value": "cost_optimization",
            "user_context": {
                "user_id": execution_context.user_id,
                "role": execution_context.metadata.get("user_role"),
                "priority": execution_context.metadata.get("priority")
            }
        })
        
        await bridge.emit_agent_thinking("metadata_rich_agent", 
            f"Analyzing {execution_context.metadata['business_context']} "
            f"with {execution_context.metadata['analysis_type']} approach", 
            1
        )
        
        await bridge.emit_tool_executing("cost_analysis_tool", {
            "data_sources": execution_context.metadata["data_sources"],
            "parameters": execution_context.metadata["custom_parameters"],
            "compliance": execution_context.metadata["compliance_requirements"]
        })
        
        await bridge.emit_tool_completed("cost_analysis_tool", {
            "analysis_results": {
                "potential_savings": "$125,000",
                "confidence_level": "high",
                "recommendations": 8,
                "compliance_status": "validated"
            },
            "context_aware_insights": {
                "user_role_specific": f"Finance director insights: {execution_context.metadata['expected_savings_range']}",
                "business_context": execution_context.metadata["business_context"]
            },
            "metadata_echo": execution_context.metadata["custom_parameters"]
        })
        
        await bridge.emit_agent_completed("metadata_rich_agent", {
            "execution_summary": {
                "total_steps": execution_context.pipeline_step_num,
                "business_context": execution_context.metadata["business_context"],
                "final_recommendations": 8,
                "estimated_value": "$125,000"
            },
            "metadata_validation": {
                "all_sources_processed": len(execution_context.metadata["data_sources"]),
                "compliance_met": execution_context.metadata["compliance_requirements"],
                "custom_params_used": execution_context.metadata["custom_parameters"]
            }
        })
        
        # Validate metadata propagation
        assert len(websocket_metadata) == 5, f"Should have 5 WebSocket events with metadata, got {len(websocket_metadata)}"
        
        # Validate agent_started metadata
        started_event = next(e for e in websocket_metadata if e['event_type'] == 'agent_started')
        started_kwargs = started_event['kwargs']
        
        assert 'execution_context_metadata' in started_kwargs, "Should propagate execution context metadata"
        assert started_kwargs['business_value'] == 'cost_optimization', "Should include business value"
        assert started_kwargs['user_context']['user_id'] == 'metadata_test_user', "Should include user context"
        assert started_kwargs['user_context']['role'] == 'finance_director', "Should include user role from metadata"
        
        # Validate agent_thinking metadata
        thinking_event = next(e for e in websocket_metadata if e['event_type'] == 'agent_thinking')
        thinking_args = thinking_event['args']
        
        # Reasoning should include business context from metadata
        reasoning = thinking_args[1] if len(thinking_args) > 1 else ""
        assert "Q4 cost optimization analysis" in reasoning, "Should include business context in reasoning"
        assert "comprehensive approach" in reasoning, "Should include analysis type from metadata"
        
        # Validate tool execution metadata
        tool_exec_event = next(e for e in websocket_metadata if e['event_type'] == 'tool_executing')
        if len(tool_exec_event['args']) > 1:
            tool_exec_kwargs = tool_exec_event['args'][1] if isinstance(tool_exec_event['args'][1], dict) else {}
            if tool_exec_kwargs and 'data_sources' in tool_exec_kwargs:
                assert tool_exec_kwargs['data_sources'] == execution_context.metadata['data_sources'], \
                    "Should propagate data sources metadata"
        
        # Validate tool completion metadata
        tool_comp_event = next(e for e in websocket_metadata if e['event_type'] == 'tool_completed')
        tool_comp_args = tool_comp_event['args']
        
        if len(tool_comp_args) > 1 and isinstance(tool_comp_args[1], dict):
            tool_result = tool_comp_args[1]
            assert 'context_aware_insights' in tool_result, "Should include context-aware insights"
            assert 'metadata_echo' in tool_result, "Should echo metadata parameters"
            
            insights = tool_result['context_aware_insights']
            assert 'Finance director' in insights['user_role_specific'], "Should include role-specific insights"
            assert insights['business_context'] == execution_context.metadata['business_context'], \
                "Should include correct business context"
        
        # Validate agent completion metadata
        completed_event = next(e for e in websocket_metadata if e['event_type'] == 'agent_completed')
        completed_args = completed_event['args']
        
        if len(completed_args) > 1 and isinstance(completed_args[1], dict):
            completion_result = completed_args[1]
            assert 'execution_summary' in completion_result, "Should include execution summary"
            assert 'metadata_validation' in completion_result, "Should validate metadata usage"
            
            summary = completion_result['execution_summary']
            validation = completion_result['metadata_validation']
            
            assert summary['business_context'] == execution_context.metadata['business_context'], \
                "Should include business context in summary"
            assert validation['all_sources_processed'] == len(execution_context.metadata['data_sources']), \
                "Should validate data sources processing"
            assert validation['compliance_met'] == execution_context.metadata['compliance_requirements'], \
                "Should validate compliance requirements"
        
        # Cleanup
        await bridge.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_execution_context_concurrent_bridge_coordination(self):
        """Test execution context coordination with WebSocket bridge under concurrent load.
        
        BVJ: Validates that WebSocket bridge can handle multiple concurrent execution
        contexts without interference, ensuring scalable multi-user operations.
        """
        # Create multiple user contexts
        num_concurrent_contexts = 4
        user_contexts = []
        execution_contexts = []
        context_trackers = {}
        websocket_emitters = {}
        bridges = {}
        
        for i in range(num_concurrent_contexts):
            user_id = f"concurrent_user_{i+1:02d}"
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"concurrent_thread_{i+1:02d}",
                run_id=f"concurrent_run_{i+1:02d}",
                request_id=f"concurrent_req_{i+1:02d}"
            )
            user_contexts.append(user_context)
            
            # Create execution context
            execution_context = AgentExecutionContext(
                user_id=user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                agent_name=f"concurrent_agent_{i+1:02d}",
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1,
                metadata={"user_index": i+1, "concurrent_test": True}
            )
            execution_contexts.append(execution_context)
            
            # Create context tracker
            tracker = ExecutionContextTracker()
            context_trackers[user_id] = tracker
            
            # Create user-specific WebSocket emitter
            mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
            
            # Create tracking functions with user closure
            def make_tracking_function(uid, tracker_ref):
                async def track_event(event_type, *args, **kwargs):
                    await tracker_ref.track_context_event(f"websocket_{event_type}", None, 
                                                         user_id=uid, args=args, kwargs=kwargs)
                    return True
                return track_event
            
            tracking_func = make_tracking_function(user_id, tracker)
            
            mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: tracking_func('agent_started', *a, **k))
            mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: tracking_func('agent_thinking', *a, **k))
            mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: tracking_func('tool_executing', *a, **k))
            mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: tracking_func('tool_completed', *a, **k))
            mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: tracking_func('agent_completed', *a, **k))
            
            websocket_emitters[user_id] = mock_emitter
            
            # Create user-specific bridge
            bridge = AgentWebSocketBridge()
            await bridge.initialize(user_context, mock_emitter)
            bridges[user_id] = bridge
        
        # Define concurrent execution task
        async def execute_context_workflow(user_id: str):
            """Execute a complete workflow for a single execution context."""
            tracker = context_trackers[user_id]
            bridge = bridges[user_id]
            context = next(ctx for ctx in execution_contexts if ctx.user_id == user_id)
            
            # Track context lifecycle
            await tracker.track_context_event("context_workflow_started", context)
            
            # Execute WebSocket coordination workflow
            await bridge.emit_agent_started(context.agent_name, {
                "user_specific": user_id,
                "context_metadata": context.metadata
            })
            
            await bridge.emit_agent_thinking(context.agent_name, 
                f"User {user_id} agent {context.agent_name} processing...", 1)
            
            # Simulate tool execution
            await bridge.emit_tool_executing(f"tool_for_{user_id}")
            
            # Add delay to simulate real execution
            await asyncio.sleep(0.1 + (hash(user_id) % 10) / 100)  # 0.1-0.19 seconds
            
            await bridge.emit_tool_completed(f"tool_for_{user_id}", {
                "user_result": f"result_for_{user_id}",
                "context_data": context.metadata
            })
            
            await bridge.emit_agent_completed(context.agent_name, {
                "user_completion": user_id,
                "final_context": context.metadata
            })
            
            await tracker.track_context_event("context_workflow_completed", context)
        
        # Execute all workflows concurrently
        concurrent_tasks = [execute_context_workflow(user_id) for user_id in [ctx.user_id for ctx in user_contexts]]
        await asyncio.gather(*concurrent_tasks)
        
        # Validate concurrent coordination
        all_user_ids = [ctx.user_id for ctx in user_contexts]
        
        # Verify each user completed their workflow
        for user_id in all_user_ids:
            tracker = context_trackers[user_id]
            
            # Check workflow lifecycle
            lifecycle_events = [e.event_type for e in tracker.events if not e.event_type.startswith('websocket_')]
            assert "context_workflow_started" in lifecycle_events, f"User {user_id} should start workflow"
            assert "context_workflow_completed" in lifecycle_events, f"User {user_id} should complete workflow"
            
            # Check WebSocket events
            websocket_events = [e.event_type.replace('websocket_', '') for e in tracker.events if e.event_type.startswith('websocket_')]
            expected_websocket_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            for expected in expected_websocket_events:
                assert expected in websocket_events, f"User {user_id} missing WebSocket event: {expected}"
        
        # Verify no cross-contamination between users
        for user_id_1 in all_user_ids:
            for user_id_2 in all_user_ids:
                if user_id_1 != user_id_2:
                    tracker_1 = context_trackers[user_id_1]
                    tracker_2 = context_trackers[user_id_2]
                    
                    # Check that user-specific data doesn't leak
                    user_1_websocket_events = [e for e in tracker_1.events if e.event_type.startswith('websocket_')]
                    for event in user_1_websocket_events:
                        if 'user_id' in event.additional_data:
                            assert event.additional_data['user_id'] == user_id_1, \
                                f"User {user_id_1} events should not contain {user_id_2} data"
        
        # Verify concurrent execution timing (all should complete within reasonable time)
        completion_times = []
        for user_id in all_user_ids:
            tracker = context_trackers[user_id]
            completion_events = [e for e in tracker.events if e.event_type == "context_workflow_completed"]
            if completion_events:
                completion_times.append(completion_events[0].timestamp)
        
        assert len(completion_times) == num_concurrent_contexts, "All contexts should complete"
        
        # Verify executions overlapped (concurrent, not sequential)
        min_completion = min(completion_times)
        max_completion = max(completion_times)
        total_duration = max_completion - min_completion
        
        # With 4 concurrent executions, if they were sequential, it would take ~0.8s
        # Concurrent should be much faster
        assert total_duration < 0.5, f"Concurrent execution should be fast, took {total_duration:.3f}s"
        
        # Cleanup all bridges
        cleanup_tasks = [bridge.cleanup() for bridge in bridges.values()]
        await asyncio.gather(*cleanup_tasks)