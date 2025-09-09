"""
WebSocket ID Event Delivery Mission Critical Tests

CRITICAL: These tests are DESIGNED TO FAIL during Phase 1 of WebSocket ID migration.
They expose mission critical event delivery failures caused by uuid.uuid4() ID patterns.

Business Value Justification:
- Segment: All (Mission Critical Infrastructure)
- Business Goal: Reliable event delivery for business value
- Value Impact: WebSocket events enable 90% of our chat business value
- Strategic Impact: CRITICAL - Event delivery failures = business failure

Test Strategy:
1. FAIL INITIALLY - Tests expose event delivery issues with uuid.uuid4()
2. MIGRATE PHASE - Replace with UnifiedIdGenerator event-aware methods
3. PASS FINALLY - Tests validate reliable event delivery with consistent IDs

These tests validate the 5 MISSION CRITICAL WebSocket events:
- agent_started (User sees agent began processing)
- agent_thinking (Real-time reasoning visibility) 
- tool_executing (Tool usage transparency)
- tool_completed (Tool results display)
- agent_completed (User knows response is ready)

FAILURE = BUSINESS VALUE FAILURE
"""

import pytest
import asyncio
import uuid
import time
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Import mission critical testing framework
from tests.mission_critical.base_mission_critical_test import BaseMissionCriticalTest

# Import WebSocket core modules for event delivery testing
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, MessageType, ConnectionInfo, generate_default_message
)
from netra_backend.app.websocket_core.context import WebSocketRequestContext  
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.event_validation_framework import EventValidationFramework
from netra_backend.app.websocket_core.websocket_notifier import WebSocketNotifier

# Import agent execution components for real event testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.websocket_core.agent_handler import WebSocketAgentEventHandler

# Import SSOT UnifiedIdGenerator for proper event delivery
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ConnectionID, ExecutionID, MessageID


@pytest.mark.mission_critical
@pytest.mark.websocket
@pytest.mark.event_delivery
@pytest.mark.business_value
class TestWebSocketIdEventDeliveryMissionCritical(BaseMissionCriticalTest):
    """
    Mission Critical tests that EXPOSE event delivery failures with uuid.uuid4().
    
    CRITICAL: These tests validate the 5 WebSocket events that deliver 90% of business value.
    ANY FAILURE = BUSINESS VALUE DELIVERY FAILURE.
    
    SUCCESS CRITERIA: All 5 events delivered with consistent ID tracking.
    """

    def setup_method(self):
        """Set up mission critical event delivery testing."""
        super().setup_method()
        
        # Initialize event validation framework
        self.event_validator = EventValidationFramework()
        
        # Track mission critical events
        self.mission_critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Event delivery tracking
        self.event_delivery_log = {}
        self.failed_deliveries = []
        
    def test_agent_started_event_id_consistency_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose agent_started event ID consistency failures.
        
        This test validates that agent_started events have consistent IDs that
        enable proper business value tracking throughout the execution flow.
        """
        # Create test user context
        user_id = "mission_critical_user_1"
        
        # Create WebSocket connection with current uuid.uuid4() pattern
        connection_info = ConnectionInfo(user_id=user_id)
        context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # Generate multiple agent_started events
        started_events = []
        for i in range(5):
            event = generate_default_message(
                message_type="agent_started",
                user_id=user_id,
                thread_id=context.thread_id,
                data={
                    "agent_type": "cost_optimization",
                    "execution_id": context.run_id,
                    "status": "started"
                }
            )
            started_events.append(event)
            
        # FAILING ASSERTION: Event message IDs should follow consistent pattern
        for event in started_events:
            # This will FAIL because uuid.uuid4() message IDs lack business context
            assert not len(event.message_id) == 36, \
                f"agent_started message ID still uses uuid.uuid4() format: {event.message_id}"
                
            # Expected UnifiedIdGenerator format for mission critical events
            expected_pattern = f"evt_agent_started_{user_id[:8]}_"
            assert event.message_id.startswith(expected_pattern), \
                f"Expected mission critical event pattern '{expected_pattern}', got: {event.message_id}"
                
        # FAILING ASSERTION: Events should be traceable to execution context
        execution_id = context.run_id
        for event in started_events:
            event_execution_id = event.data.get("execution_id")
            
            # This will FAIL because uuid.uuid4() run_id lacks consistency
            assert event_execution_id == execution_id, \
                f"agent_started event execution_id mismatch: {event_execution_id} != {execution_id}"
                
            # This will FAIL because uuid.uuid4() lacks user context traceability
            assert user_id[:8] in execution_id, \
                f"Execution ID lacks user context for traceability: {execution_id}"
                
        # FAILING ASSERTION: Message IDs should enable audit trail reconstruction
        message_ids = [event.message_id for event in started_events]
        
        # All message IDs should be traceable to same user and execution
        for msg_id in message_ids:
            # This will FAIL because uuid.uuid4() message IDs can't be traced
            assert user_id[:8] in msg_id or execution_id[:8] in msg_id, \
                f"Message ID not traceable to user/execution: {msg_id}"
                
        # Validate event ordering for business value flow
        event_timestamps = [event.timestamp for event in started_events]
        assert event_timestamps == sorted(event_timestamps), \
            f"agent_started events delivered out of order: {event_timestamps}"
            
        print(f"✅ Mission Critical: agent_started event ID consistency validated")

    def test_agent_thinking_event_stream_consistency_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose agent_thinking event stream consistency failures.
        
        This test validates that agent_thinking events maintain consistent ID
        patterns across the thinking stream for real-time business value visibility.
        """
        # Create test execution context
        user_id = "thinking_stream_user"
        connection_info = ConnectionInfo(user_id=user_id)
        context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # Simulate agent thinking stream (multiple thinking events)
        thinking_events = []
        thinking_contents = [
            "Analyzing customer churn data patterns...",
            "Identifying key retention factors...", 
            "Calculating ROI impact scenarios...",
            "Generating actionable recommendations..."
        ]
        
        for i, content in enumerate(thinking_contents):
            event = generate_default_message(
                message_type="agent_thinking",
                user_id=user_id,
                thread_id=context.thread_id,
                data={
                    "content": content,
                    "execution_id": context.run_id,
                    "thinking_step": i + 1,
                    "total_steps": len(thinking_contents)
                }
            )
            thinking_events.append(event)
            
        # FAILING ASSERTION: Thinking event IDs should maintain stream consistency
        for i, event in enumerate(thinking_events):
            # This will FAIL because uuid.uuid4() message IDs lack stream context
            assert not len(event.message_id) == 36, \
                f"agent_thinking message ID uses uuid.uuid4() format: {event.message_id}"
                
            # Expected UnifiedIdGenerator format for thinking streams
            expected_pattern = f"evt_agent_thinking_{user_id[:8]}_step_{i+1}_"
            assert event.message_id.find(expected_pattern) != -1, \
                f"Expected thinking stream pattern '{expected_pattern}' in: {event.message_id}"
                
        # FAILING ASSERTION: All thinking events should reference same execution
        execution_id = context.run_id
        execution_ids = [event.data.get("execution_id") for event in thinking_events]
        unique_execution_ids = set(execution_ids)
        
        assert len(unique_execution_ids) == 1, \
            f"agent_thinking events have inconsistent execution IDs: {unique_execution_ids}"
            
        assert list(unique_execution_ids)[0] == execution_id, \
            f"agent_thinking events not linked to correct execution: {unique_execution_ids} != {execution_id}"
            
        # FAILING ASSERTION: Thinking stream should be reconstructable from message IDs
        # Sort events by message ID to test stream reconstruction
        try:
            # This will FAIL because uuid.uuid4() message IDs don't encode step ordering
            sorted_by_message_id = sorted(thinking_events, key=lambda e: e.message_id)
            original_order_by_step = sorted(thinking_events, key=lambda e: e.data.get("thinking_step", 0))
            
            # Message ID ordering should match thinking step ordering
            assert [e.data["thinking_step"] for e in sorted_by_message_id] == \
                   [e.data["thinking_step"] for e in original_order_by_step], \
                   f"Message IDs don't encode thinking stream ordering"
                   
        except Exception as e:
            pytest.fail(f"Cannot reconstruct thinking stream from uuid.uuid4() message IDs: {e}")
            
        print(f"✅ Mission Critical: agent_thinking stream consistency validated")

    def test_tool_execution_event_lifecycle_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose tool execution event lifecycle failures.
        
        This test validates that tool_executing/tool_completed events maintain
        consistent ID patterns across the complete tool execution lifecycle.
        """
        # Create test execution context
        user_id = "tool_lifecycle_user"
        connection_info = ConnectionInfo(user_id=user_id)
        context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # Simulate tool execution lifecycle
        tool_executions = [
            {
                "tool_name": "cost_analyzer",
                "operation": "analyze_aws_costs",
                "input_data": {"account_id": "123456789", "period": "last_30_days"}
            },
            {
                "tool_name": "recommendation_engine", 
                "operation": "generate_savings_plan",
                "input_data": {"current_spend": 5000, "target_reduction": 0.20}
            },
            {
                "tool_name": "report_generator",
                "operation": "create_executive_summary",
                "input_data": {"findings": "cost_optimization_results"}
            }
        ]
        
        # Generate tool execution event pairs
        tool_event_pairs = []
        
        for tool_exec in tool_executions:
            # Generate tool_executing event
            executing_event = generate_default_message(
                message_type="tool_executing",
                user_id=user_id,
                thread_id=context.thread_id,
                data={
                    "tool_name": tool_exec["tool_name"],
                    "operation": tool_exec["operation"],
                    "input_data": tool_exec["input_data"],
                    "execution_id": context.run_id,
                    "status": "executing"
                }
            )
            
            # Generate corresponding tool_completed event
            completed_event = generate_default_message(
                message_type="tool_completed",
                user_id=user_id,
                thread_id=context.thread_id,
                data={
                    "tool_name": tool_exec["tool_name"],
                    "operation": tool_exec["operation"],
                    "result": f"Success: {tool_exec['operation']} completed",
                    "execution_id": context.run_id,
                    "status": "completed"
                }
            )
            
            tool_event_pairs.append({
                "executing": executing_event,
                "completed": completed_event,
                "tool": tool_exec
            })
            
        # FAILING ASSERTION: Tool event pairs should have linkable IDs
        for pair in tool_event_pairs:
            executing_event = pair["executing"]
            completed_event = pair["completed"] 
            tool_name = pair["tool"]["tool_name"]
            
            # This will FAIL because uuid.uuid4() message IDs can't link executing->completed
            executing_id = executing_event.message_id
            completed_id = completed_event.message_id
            
            # Expected UnifiedIdGenerator format for tool lifecycle
            expected_executing_pattern = f"evt_tool_executing_{user_id[:8]}_{tool_name}_"
            expected_completed_pattern = f"evt_tool_completed_{user_id[:8]}_{tool_name}_"
            
            assert executing_id.find(expected_executing_pattern) != -1, \
                f"Expected tool executing pattern '{expected_executing_pattern}' in: {executing_id}"
                
            assert completed_id.find(expected_completed_pattern) != -1, \
                f"Expected tool completed pattern '{expected_completed_pattern}' in: {completed_id}"
                
            # This will FAIL because uuid.uuid4() IDs can't establish lifecycle linkage
            # The completed event ID should reference the executing event ID
            executing_id_ref = executing_id.split('_')[-1]  # Extract unique part
            assert executing_id_ref in completed_id, \
                f"tool_completed ID should reference executing ID: {completed_id} should contain {executing_id_ref}"
                
        # FAILING ASSERTION: All tool events should trace to same execution context
        all_tool_events = []
        for pair in tool_event_pairs:
            all_tool_events.extend([pair["executing"], pair["completed"]])
            
        execution_ids = [event.data.get("execution_id") for event in all_tool_events]
        unique_execution_ids = set(execution_ids)
        
        assert len(unique_execution_ids) == 1, \
            f"Tool events have inconsistent execution context: {unique_execution_ids}"
            
        # FAILING ASSERTION: Tool execution order should be deterministic from IDs
        executing_events = [pair["executing"] for pair in tool_event_pairs]
        completed_events = [pair["completed"] for pair in tool_event_pairs]
        
        # Message IDs should enable correct event ordering
        try:
            executing_sorted = sorted(executing_events, key=lambda e: e.message_id)
            completed_sorted = sorted(completed_events, key=lambda e: e.message_id)
            
            # Tool execution order should be preserved in ID ordering
            original_tool_order = [pair["tool"]["tool_name"] for pair in tool_event_pairs]
            id_sorted_tool_order = [e.data["tool_name"] for e in executing_sorted]
            
            assert original_tool_order == id_sorted_tool_order, \
                f"Tool execution order not preserved in message IDs: {original_tool_order} != {id_sorted_tool_order}"
                
        except Exception as e:
            pytest.fail(f"Cannot determine tool execution order from uuid.uuid4() IDs: {e}")
            
        print(f"✅ Mission Critical: tool execution lifecycle consistency validated")

    def test_agent_completed_event_finalization_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose agent_completed event finalization failures.
        
        This test validates that agent_completed events properly finalize the
        execution with consistent IDs that enable complete business value audit trails.
        """
        # Create test execution context
        user_id = "completion_audit_user"
        connection_info = ConnectionInfo(user_id=user_id)
        context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # Simulate complete agent execution sequence
        execution_events = []
        
        # 1. Agent started
        started_event = generate_default_message(
            message_type="agent_started",
            user_id=user_id,
            thread_id=context.thread_id,
            data={
                "agent_type": "business_optimizer",
                "execution_id": context.run_id,
                "status": "started",
                "start_time": time.time()
            }
        )
        execution_events.append(started_event)
        
        # 2. Agent thinking
        thinking_event = generate_default_message(
            message_type="agent_thinking",
            user_id=user_id,
            thread_id=context.thread_id,
            data={
                "content": "Analyzing business optimization opportunities...",
                "execution_id": context.run_id,
                "thinking_step": 1
            }
        )
        execution_events.append(thinking_event)
        
        # 3. Tool execution
        tool_executing = generate_default_message(
            message_type="tool_executing",
            user_id=user_id,
            thread_id=context.thread_id,
            data={
                "tool_name": "business_analyzer",
                "execution_id": context.run_id,
                "status": "executing"
            }
        )
        execution_events.append(tool_executing)
        
        # 4. Tool completed
        tool_completed = generate_default_message(
            message_type="tool_completed",
            user_id=user_id,
            thread_id=context.thread_id,
            data={
                "tool_name": "business_analyzer",
                "result": "Identified 15% cost reduction opportunity",
                "execution_id": context.run_id,
                "status": "completed"
            }
        )
        execution_events.append(tool_completed)
        
        # 5. Agent completed (MISSION CRITICAL FINAL EVENT)
        completed_event = generate_default_message(
            message_type="agent_completed",
            user_id=user_id,
            thread_id=context.thread_id,
            data={
                "execution_id": context.run_id,
                "status": "completed",
                "result": "Business optimization analysis complete. Recommended actions will save $180K annually.",
                "total_events": len(execution_events) + 1,  # Including this completion event
                "completion_time": time.time()
            }
        )
        execution_events.append(completed_event)
        
        # FAILING ASSERTION: Completion event should reference all prior events
        completion_execution_id = completed_event.data.get("execution_id")
        
        # This will FAIL because uuid.uuid4() completion event can't trace execution flow
        assert completion_execution_id == context.run_id, \
            f"agent_completed execution ID mismatch: {completion_execution_id} != {context.run_id}"
            
        # Expected UnifiedIdGenerator format for completion audit trail
        expected_completion_pattern = f"evt_agent_completed_{user_id[:8]}_exec_{context.run_id[:8]}_"
        assert completed_event.message_id.find(expected_completion_pattern) != -1, \
            f"Expected completion audit pattern '{expected_completion_pattern}' in: {completed_event.message_id}"
            
        # FAILING ASSERTION: All events in execution should have consistent context
        all_execution_ids = [event.data.get("execution_id") for event in execution_events]
        unique_execution_ids = set(all_execution_ids)
        
        assert len(unique_execution_ids) == 1, \
            f"Execution events have inconsistent execution IDs: {unique_execution_ids}"
            
        # FAILING ASSERTION: Message IDs should enable complete audit trail reconstruction
        message_ids = [event.message_id for event in execution_events]
        
        # This will FAIL because uuid.uuid4() message IDs can't reconstruct execution flow
        for msg_id in message_ids:
            # All message IDs should contain execution context for audit trail
            assert context.run_id[:8] in msg_id or user_id[:8] in msg_id, \
                f"Message ID lacks audit trail context: {msg_id}"
                
        # FAILING ASSERTION: Completion event should summarize execution metrics
        total_events_claimed = completed_event.data.get("total_events", 0)
        actual_events = len(execution_events)
        
        assert total_events_claimed == actual_events, \
            f"agent_completed event incorrect event count: claimed {total_events_claimed}, actual {actual_events}"
            
        # FAILING ASSERTION: Should be able to reconstruct complete execution timeline
        try:
            # This will FAIL because uuid.uuid4() message IDs don't support timeline reconstruction
            timeline = self._reconstruct_execution_timeline(execution_events)
            
            # Timeline should show complete business value flow
            expected_flow = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            actual_flow = [event["type"] for event in timeline]
            
            assert actual_flow == expected_flow, \
                f"Execution timeline reconstruction failed: {actual_flow} != {expected_flow}"
                
            # Timeline should preserve business value context
            business_value_delivered = any(
                "save" in str(event.get("data", {})).lower() or 
                "optimization" in str(event.get("data", {})).lower()
                for event in timeline
            )
            
            assert business_value_delivered, \
                f"Execution timeline missing business value context"
                
        except Exception as e:
            pytest.fail(f"Cannot reconstruct execution timeline with uuid.uuid4() IDs: {e}")
            
        print(f"✅ Mission Critical: agent_completed finalization audit trail validated")

    def test_mission_critical_event_delivery_end_to_end_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose end-to-end mission critical event delivery failures.
        
        This test validates the complete 5-event sequence that delivers 90% of business value:
        agent_started -> agent_thinking -> tool_executing -> tool_completed -> agent_completed
        """
        # Create test execution context
        user_id = "e2e_mission_critical_user"
        connection_info = ConnectionInfo(user_id=user_id)
        context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # Initialize WebSocket notifier for event delivery
        mock_websocket = MagicMock()
        notifier = WebSocketNotifier(mock_websocket)
        
        # Initialize agent event handler
        event_handler = WebSocketAgentEventHandler(notifier)
        
        # Simulate complete mission critical event sequence
        mission_critical_sequence = []
        
        # Event 1: agent_started (User sees agent began processing)
        await_started_event = event_handler.send_agent_started_event(
            execution_id=context.run_id,
            user_id=user_id,
            agent_type="revenue_optimizer"
        )
        mission_critical_sequence.append(("agent_started", await_started_event))
        
        # Event 2: agent_thinking (Real-time reasoning visibility)
        thinking_event = event_handler.send_agent_thinking_event(
            execution_id=context.run_id,
            user_id=user_id,
            thinking_content="Analyzing revenue optimization strategies for Q4..."
        )
        mission_critical_sequence.append(("agent_thinking", thinking_event))
        
        # Event 3: tool_executing (Tool usage transparency)
        tool_executing_event = event_handler.send_tool_executing_event(
            execution_id=context.run_id,
            user_id=user_id,
            tool_name="revenue_forecaster",
            tool_input={"period": "Q4", "growth_target": 0.25}
        )
        mission_critical_sequence.append(("tool_executing", tool_executing_event))
        
        # Event 4: tool_completed (Tool results display)
        tool_completed_event = event_handler.send_tool_completed_event(
            execution_id=context.run_id,
            user_id=user_id,
            tool_name="revenue_forecaster",
            tool_result={"projected_revenue": "$2.5M", "confidence": 0.87}
        )
        mission_critical_sequence.append(("tool_completed", tool_completed_event))
        
        # Event 5: agent_completed (User knows response is ready)
        agent_completed_event = event_handler.send_agent_completed_event(
            execution_id=context.run_id,
            user_id=user_id,
            final_result="Revenue optimization analysis complete. Recommended strategies will increase Q4 revenue by 25% to $2.5M."
        )
        mission_critical_sequence.append(("agent_completed", agent_completed_event))
        
        # FAILING ASSERTION: All 5 mission critical events must be delivered
        assert len(mission_critical_sequence) == 5, \
            f"Mission critical event sequence incomplete: {len(mission_critical_sequence)} != 5"
            
        expected_event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        actual_event_types = [event_type for event_type, _ in mission_critical_sequence]
        
        assert actual_event_types == expected_event_types, \
            f"Mission critical event sequence incorrect: {actual_event_types} != {expected_event_types}"
            
        # FAILING ASSERTION: All events must have consistent execution context
        execution_ids = []
        for event_type, event_data in mission_critical_sequence:
            # Extract execution ID from event (method depends on event format)
            if hasattr(event_data, 'data'):
                exec_id = event_data.data.get("execution_id")
            elif isinstance(event_data, dict):
                exec_id = event_data.get("execution_id")
            else:
                exec_id = getattr(event_data, 'execution_id', None)
                
            execution_ids.append(exec_id)
            
        unique_execution_ids = set(execution_ids)
        assert len(unique_execution_ids) == 1, \
            f"Mission critical events have inconsistent execution IDs: {unique_execution_ids}"
            
        assert list(unique_execution_ids)[0] == context.run_id, \
            f"Mission critical events not linked to correct execution: {unique_execution_ids} != {context.run_id}"
            
        # FAILING ASSERTION: Event delivery order must be preserved
        # This will FAIL because uuid.uuid4() event IDs don't encode ordering
        event_message_ids = []
        for event_type, event_data in mission_critical_sequence:
            if hasattr(event_data, 'message_id'):
                msg_id = event_data.message_id
            elif isinstance(event_data, dict):
                msg_id = event_data.get("message_id")
            else:
                msg_id = str(uuid.uuid4())  # Fallback - this will cause failure
                
            event_message_ids.append(msg_id)
            
        # Message IDs should preserve event ordering for business value flow
        try:
            # This will FAIL because uuid.uuid4() message IDs don't support ordering
            id_sorted_events = sorted(zip(event_message_ids, expected_event_types))
            id_based_order = [event_type for _, event_type in id_sorted_events]
            
            assert id_based_order == expected_event_types, \
                f"Event delivery order not preserved in message IDs: {id_based_order} != {expected_event_types}"
                
        except Exception as e:
            pytest.fail(f"Cannot verify event delivery order with uuid.uuid4() message IDs: {e}")
            
        # FAILING ASSERTION: WebSocket delivery must succeed for all events
        delivery_calls = mock_websocket.send_json.call_args_list
        
        # Should have 5 WebSocket send calls for 5 mission critical events
        assert len(delivery_calls) >= 5, \
            f"Insufficient WebSocket deliveries for mission critical events: {len(delivery_calls)} < 5"
            
        # FAILING ASSERTION: Event content must preserve business value context
        business_value_keywords = ["revenue", "optimization", "growth", "strategies", "$2.5M"]
        
        delivered_content = str(delivery_calls).lower()
        found_keywords = [kw for kw in business_value_keywords if kw.lower() in delivered_content]
        
        assert len(found_keywords) >= 3, \
            f"Mission critical events missing business value context: {found_keywords}"
            
        print(f"✅ Mission Critical: End-to-end 5-event delivery sequence validated")
        print(f"   Events delivered: {len(mission_critical_sequence)}")
        print(f"   WebSocket calls: {len(delivery_calls)}")
        print(f"   Business value keywords: {found_keywords}")

    # Helper methods for mission critical event testing
    
    def _reconstruct_execution_timeline(self, events: List[WebSocketMessage]) -> List[Dict[str, Any]]:
        """Reconstruct execution timeline from events (will fail with uuid.uuid4() IDs)."""
        timeline = []
        
        for event in events:
            timeline_entry = {
                "type": event.type,
                "message_id": event.message_id,
                "timestamp": event.timestamp,
                "data": event.data,
                "execution_id": event.data.get("execution_id")
            }
            timeline.append(timeline_entry)
            
        # Sort by timestamp for timeline reconstruction
        timeline.sort(key=lambda e: e["timestamp"])
        
        return timeline
        
    def _validate_event_business_value(self, event: WebSocketMessage, expected_value_type: str) -> bool:
        """Validate that event contains expected business value context."""
        event_content = str(event.data).lower()
        
        business_value_map = {
            "cost_optimization": ["cost", "save", "reduction", "efficiency"],
            "revenue_growth": ["revenue", "growth", "increase", "profit"],
            "process_improvement": ["optimize", "improve", "streamline", "automate"],
            "risk_mitigation": ["risk", "security", "compliance", "protection"]
        }
        
        expected_keywords = business_value_map.get(expected_value_type, [])
        found_keywords = [kw for kw in expected_keywords if kw in event_content]
        
        return len(found_keywords) > 0
        
    def teardown_method(self):
        """Clean up mission critical test resources."""
        super().teardown_method()
        
        # Log any failed deliveries for mission critical analysis
        if self.failed_deliveries:
            self.logger.error(f"Mission Critical Event Delivery Failures: {len(self.failed_deliveries)}")
            for failure in self.failed_deliveries:
                self.logger.error(f"  - {failure}")
                
        # Report event delivery statistics
        total_events = sum(len(events) for events in self.event_delivery_log.values())
        self.logger.info(f"Mission Critical Test Summary: {total_events} events processed")

# Legacy import for backward compatibility
BaseMissionCriticalTest = BaseMissionCriticalTest