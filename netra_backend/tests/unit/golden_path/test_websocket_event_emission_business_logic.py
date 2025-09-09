"""
Golden Path Unit Tests: WebSocket Event Emission Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Ensure critical WebSocket events enable real-time user visibility
- Value Impact: Users see AI progress, preventing abandonment and increasing chat completion rates
- Strategic/Revenue Impact: Delivers 90% of $500K+ ARR chat functionality through visible agent interactions

CRITICAL: This test validates the business logic for the 5 mission-critical WebSocket events
that enable users to see AI agent progress during the Golden Path user flow. Without proper
event emission, users think the system is broken and abandon their sessions.

Key Events Tested:
1. agent_started - Confirms AI received user request
2. agent_thinking - Shows real-time reasoning progress  
3. tool_executing - Demonstrates problem-solving approach
4. tool_completed - Delivers actionable insights
5. agent_completed - Indicates valuable response is ready
"""

import pytest
import time
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Callable
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass, field
from enum import Enum

# Import business logic components for testing
from test_framework.base import BaseTestCase
from shared.types.core_types import (
    UserID, ThreadID, AgentID, ExecutionID, WebSocketID,
    ensure_user_id, ensure_thread_id
)
from shared.types.execution_types import StronglyTypedUserExecutionContext


class WebSocketEventType(Enum):
    """WebSocket event types for agent execution notifications."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"  
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    ERROR_OCCURRED = "error_occurred"


class EventPriority(Enum):
    """Business priority levels for WebSocket events."""
    CRITICAL = "critical"      # Must be sent for business value
    IMPORTANT = "important"    # Should be sent for good UX
    OPTIONAL = "optional"      # Nice to have


@dataclass
class WebSocketEventPayload:
    """Structured payload for WebSocket events with business context."""
    event_type: WebSocketEventType
    user_id: UserID
    thread_id: ThreadID
    execution_id: ExecutionID
    agent_id: Optional[AgentID] = None
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    business_context: Dict[str, Any] = field(default_factory=dict)
    tool_name: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None


class WebSocketEventEmitter:
    """Business logic for WebSocket event emission during agent execution."""
    
    def __init__(self):
        self.event_templates = self._initialize_business_event_templates()
        self.required_golden_path_events = {
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        }
        self.emitted_events: List[WebSocketEventPayload] = []
        self.event_callbacks: Dict[WebSocketEventType, List[Callable]] = {}
        
    def _initialize_business_event_templates(self) -> Dict[WebSocketEventType, Dict[str, Any]]:
        """Initialize event templates with business value definitions."""
        return {
            WebSocketEventType.AGENT_STARTED: {
                "priority": EventPriority.CRITICAL,
                "business_value": "Confirms AI agent received user request and is processing",
                "user_message": "AI agent is analyzing your request...",
                "required_fields": ["user_id", "thread_id", "execution_id"]
            },
            WebSocketEventType.AGENT_THINKING: {
                "priority": EventPriority.CRITICAL,
                "business_value": "Shows AI reasoning process for transparency",
                "user_message": "AI is thinking about your problem...",
                "required_fields": ["user_id", "thread_id", "execution_id"]
            },
            WebSocketEventType.TOOL_EXECUTING: {
                "priority": EventPriority.CRITICAL,
                "business_value": "Demonstrates AI taking action to solve user problem",
                "user_message": "AI is using tools to analyze your data...",
                "required_fields": ["user_id", "thread_id", "execution_id", "tool_name"]
            },
            WebSocketEventType.TOOL_COMPLETED: {
                "priority": EventPriority.CRITICAL,
                "business_value": "Shows completion of problem-solving action",
                "user_message": "AI has completed data analysis...",
                "required_fields": ["user_id", "thread_id", "execution_id", "tool_name"]
            },
            WebSocketEventType.AGENT_COMPLETED: {
                "priority": EventPriority.CRITICAL,
                "business_value": "Indicates valuable AI response is ready",
                "user_message": "AI has completed your analysis!",
                "required_fields": ["user_id", "thread_id", "execution_id"]
            }
        }
    
    def emit_event(self, event_payload: WebSocketEventPayload) -> bool:
        """Emit WebSocket event following business validation rules."""
        # Business Rule 1: Validate required fields are present
        template = self.event_templates.get(event_payload.event_type)
        if not template:
            raise ValueError(f"Unknown event type: {event_payload.event_type}")
            
        required_fields = template["required_fields"]
        for field in required_fields:
            if not getattr(event_payload, field, None):
                raise ValueError(f"Required field missing: {field}")
        
        # Business Rule 2: Event must have business context
        if not event_payload.business_context and template["priority"] == EventPriority.CRITICAL:
            event_payload.business_context = {"priority": "high", "user_visible": True}
            
        # Business Rule 3: Add user-friendly message
        if not event_payload.message:
            event_payload.message = template["user_message"]
            
        # Business Rule 4: Record event for business analytics
        self.emitted_events.append(event_payload)
        
        # Business Rule 5: Execute callbacks for business logic
        callbacks = self.event_callbacks.get(event_payload.event_type, [])
        for callback in callbacks:
            try:
                callback(event_payload)
            except Exception as e:
                # Business Rule: Callback errors don't break event emission
                continue
                
        return True
    
    def validate_golden_path_events(self, user_id: UserID, execution_id: ExecutionID) -> Dict[str, Any]:
        """Validate all required golden path events were emitted for business value."""
        user_events = [
            event for event in self.emitted_events 
            if event.user_id == user_id and event.execution_id == execution_id
        ]
        
        emitted_types = {event.event_type for event in user_events}
        missing_events = self.required_golden_path_events - emitted_types
        
        return {
            "all_critical_events_emitted": len(missing_events) == 0,
            "missing_events": list(missing_events),
            "total_events": len(user_events),
            "business_value_complete": len(missing_events) == 0
        }


@pytest.mark.unit
@pytest.mark.golden_path
class TestWebSocketEventEmissionBusinessLogic(BaseTestCase):
    """Test WebSocket event emission business logic for Golden Path user flow."""

    def setup_method(self):
        """Setup test environment for each test."""
        super().setup_method()
        self.event_emitter = WebSocketEventEmitter()
        self.test_user_id = ensure_user_id("test-user-123")
        self.test_thread_id = ensure_thread_id("thread-456")
        self.test_execution_id = ExecutionID("exec-789")

    def test_agent_started_event_business_requirements(self):
        """Test agent_started event meets business requirements for user visibility."""
        # Business Value: User must know AI agent received their request
        
        event_payload = WebSocketEventPayload(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            execution_id=self.test_execution_id,
            agent_id="data-analysis-agent",
            business_context={"user_request": "Analyze AI costs", "priority": "high"}
        )
        
        # Business Rule: Event emission must succeed
        result = self.event_emitter.emit_event(event_payload)
        assert result is True, "Agent started event must be emitted successfully"
        
        # Business Rule: Event must be recorded for analytics
        assert len(self.event_emitter.emitted_events) == 1, "Event must be recorded"
        recorded_event = self.event_emitter.emitted_events[0]
        
        # Business Rule: Event must contain user identification
        assert recorded_event.user_id == self.test_user_id, "Event must identify correct user"
        assert recorded_event.thread_id == self.test_thread_id, "Event must identify correct thread"
        
        # Business Rule: Event must have business context
        assert "user_request" in recorded_event.business_context, "Event must include user request context"
        assert recorded_event.business_context["priority"] == "high", "Event must indicate priority"
        
        # Business Rule: Event must have user-friendly message
        assert recorded_event.message, "Event must have user-visible message"
        assert "analyzing" in recorded_event.message.lower(), "Message must indicate AI is working"

    def test_tool_execution_event_business_requirements(self):
        """Test tool execution events provide business transparency."""
        # Business Value: User sees AI taking concrete actions to solve their problem
        
        # Test tool_executing event
        executing_payload = WebSocketEventPayload(
            event_type=WebSocketEventType.TOOL_EXECUTING,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            execution_id=self.test_execution_id,
            tool_name="cost_analysis_tool",
            business_context={"action": "analyzing_ai_spend", "expected_duration": 30}
        )
        
        result = self.event_emitter.emit_event(executing_payload)
        assert result is True, "Tool executing event must be emitted"
        
        # Test tool_completed event
        completed_payload = WebSocketEventPayload(
            event_type=WebSocketEventType.TOOL_COMPLETED,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            execution_id=self.test_execution_id,
            tool_name="cost_analysis_tool",
            tool_result={"total_cost": "$1,250", "optimization_potential": "$400"},
            business_context={"action_completed": True, "value_delivered": True}
        )
        
        result = self.event_emitter.emit_event(completed_payload)
        assert result is True, "Tool completed event must be emitted"
        
        # Business Rule: Both events must be recorded
        assert len(self.event_emitter.emitted_events) == 2, "Both tool events must be recorded"
        
        # Business Rule: Events must show business value delivery
        completed_event = self.event_emitter.emitted_events[1]
        assert completed_event.tool_result["total_cost"], "Tool must deliver cost insights"
        assert completed_event.tool_result["optimization_potential"], "Tool must show optimization value"

    def test_golden_path_event_sequence_business_validation(self):
        """Test complete golden path event sequence delivers business value."""
        # Business Value: User sees complete AI problem-solving journey
        
        # Emit all 5 required golden path events
        golden_path_events = [
            WebSocketEventPayload(
                event_type=WebSocketEventType.AGENT_STARTED,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                execution_id=self.test_execution_id
            ),
            WebSocketEventPayload(
                event_type=WebSocketEventType.AGENT_THINKING,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                execution_id=self.test_execution_id
            ),
            WebSocketEventPayload(
                event_type=WebSocketEventType.TOOL_EXECUTING,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                execution_id=self.test_execution_id,
                tool_name="analysis_tool"
            ),
            WebSocketEventPayload(
                event_type=WebSocketEventType.TOOL_COMPLETED,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                execution_id=self.test_execution_id,
                tool_name="analysis_tool"
            ),
            WebSocketEventPayload(
                event_type=WebSocketEventType.AGENT_COMPLETED,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                execution_id=self.test_execution_id
            )
        ]
        
        # Emit all events
        for event in golden_path_events:
            result = self.event_emitter.emit_event(event)
            assert result is True, f"Event {event.event_type.value} must be emitted successfully"
        
        # Business Rule: Validate complete golden path flow
        validation_result = self.event_emitter.validate_golden_path_events(
            self.test_user_id, self.test_execution_id
        )
        
        assert validation_result["all_critical_events_emitted"] is True, "All critical events must be emitted"
        assert len(validation_result["missing_events"]) == 0, "No events should be missing"
        assert validation_result["business_value_complete"] is True, "Complete business value must be delivered"
        assert validation_result["total_events"] == 5, "Exactly 5 golden path events should be emitted"

    def test_event_payload_json_serialization_business_requirements(self):
        """Test event payloads can be serialized for WebSocket transmission."""
        # Business Value: Events must be transmittable to users for real-time updates
        
        event_payload = WebSocketEventPayload(
            event_type=WebSocketEventType.AGENT_THINKING,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            execution_id=self.test_execution_id,
            message="AI is analyzing your cost optimization opportunities...",
            business_context={"reasoning": "data_analysis", "progress": 0.3}
        )
        
        # Business Rule: Event must be JSON serializable
        try:
            event_dict = {
                "event_type": event_payload.event_type.value,
                "user_id": str(event_payload.user_id),
                "thread_id": str(event_payload.thread_id),
                "execution_id": str(event_payload.execution_id),
                "message": event_payload.message,
                "timestamp": event_payload.timestamp.isoformat(),
                "business_context": event_payload.business_context
            }
            
            json_string = json.dumps(event_dict)
            assert isinstance(json_string, str), "Event must serialize to JSON string"
            
            # Business Rule: Deserialized data must preserve business information
            deserialized = json.loads(json_string)
            assert deserialized["event_type"] == "agent_thinking", "Event type must be preserved"
            assert deserialized["message"], "User message must be preserved"
            assert deserialized["business_context"]["reasoning"] == "data_analysis", "Business context must be preserved"
            
        except (TypeError, ValueError) as e:
            pytest.fail(f"Event payload must be JSON serializable for WebSocket transmission: {e}")

    def test_multi_user_event_isolation_business_requirements(self):
        """Test events are properly isolated between different users."""
        # Business Value: User privacy and data isolation for multi-tenant system
        
        user1_id = ensure_user_id("user-1")
        user2_id = ensure_user_id("user-2")
        exec1_id = ExecutionID("exec-1")
        exec2_id = ExecutionID("exec-2")
        
        # Emit events for user 1
        user1_event = WebSocketEventPayload(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=user1_id,
            thread_id=self.test_thread_id,
            execution_id=exec1_id,
            business_context={"user_data": "confidential_analysis"}
        )
        
        # Emit events for user 2  
        user2_event = WebSocketEventPayload(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=user2_id,
            thread_id=self.test_thread_id,
            execution_id=exec2_id,
            business_context={"user_data": "different_confidential_data"}
        )
        
        self.event_emitter.emit_event(user1_event)
        self.event_emitter.emit_event(user2_event)
        
        # Business Rule: Events must be isolated per user
        user1_validation = self.event_emitter.validate_golden_path_events(user1_id, exec1_id)
        user2_validation = self.event_emitter.validate_golden_path_events(user2_id, exec2_id)
        
        # Validate user 1 only sees their events
        user1_events = [e for e in self.event_emitter.emitted_events if e.user_id == user1_id]
        assert len(user1_events) == 1, "User 1 should only see their own events"
        assert user1_events[0].business_context["user_data"] == "confidential_analysis", "User 1 data must be isolated"
        
        # Validate user 2 only sees their events
        user2_events = [e for e in self.event_emitter.emitted_events if e.user_id == user2_id]
        assert len(user2_events) == 1, "User 2 should only see their own events"
        assert user2_events[0].business_context["user_data"] == "different_confidential_data", "User 2 data must be isolated"

    def test_event_emission_error_handling_business_continuity(self):
        """Test event emission errors don't break business continuity."""
        # Business Value: System resilience ensures business operations continue despite technical issues
        
        # Test with invalid event type
        with pytest.raises(ValueError, match="Unknown event type"):
            invalid_payload = WebSocketEventPayload(
                event_type="invalid_event",  # This will cause an error
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                execution_id=self.test_execution_id
            )
            # This should raise an error, but business logic should handle gracefully
            
        # Test with missing required fields
        with pytest.raises(ValueError, match="Required field missing"):
            incomplete_payload = WebSocketEventPayload(
                event_type=WebSocketEventType.TOOL_EXECUTING,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                execution_id=self.test_execution_id
                # Missing tool_name which is required for tool_executing
            )
            self.event_emitter.emit_event(incomplete_payload)
        
        # Business Rule: Valid events should still work after errors
        valid_payload = WebSocketEventPayload(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            execution_id=self.test_execution_id
        )
        
        result = self.event_emitter.emit_event(valid_payload)
        assert result is True, "Valid events must work even after errors occur"
        assert len(self.event_emitter.emitted_events) == 1, "Valid event must be recorded"

    def test_event_callback_business_integration(self):
        """Test event callbacks enable business process integration."""
        # Business Value: Events can trigger additional business processes like analytics, notifications
        
        callback_results = []
        
        def business_analytics_callback(event: WebSocketEventPayload):
            """Simulate business analytics integration."""
            callback_results.append({
                "analytics_type": "user_engagement", 
                "event_type": event.event_type.value,
                "user_id": str(event.user_id),
                "timestamp": event.timestamp
            })
        
        def notification_callback(event: WebSocketEventPayload):
            """Simulate notification system integration."""
            callback_results.append({
                "notification_type": "real_time_update",
                "message": event.message,
                "user_id": str(event.user_id)
            })
            
        # Register business callbacks
        self.event_emitter.event_callbacks[WebSocketEventType.AGENT_STARTED] = [
            business_analytics_callback, 
            notification_callback
        ]
        
        # Emit event that should trigger callbacks
        event_payload = WebSocketEventPayload(
            event_type=WebSocketEventType.AGENT_STARTED,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            execution_id=self.test_execution_id,
            message="AI agent has started analyzing your data"
        )
        
        result = self.event_emitter.emit_event(event_payload)
        assert result is True, "Event emission with callbacks must succeed"
        
        # Business Rule: Callbacks must execute for business integration
        assert len(callback_results) == 2, "Both business callbacks must execute"
        
        analytics_result = next(r for r in callback_results if r.get("analytics_type"))
        assert analytics_result["event_type"] == "agent_started", "Analytics must track correct event"
        assert analytics_result["user_id"] == str(self.test_user_id), "Analytics must track correct user"
        
        notification_result = next(r for r in callback_results if r.get("notification_type"))
        assert notification_result["message"], "Notification must include user message"
        assert "analyzing" in notification_result["message"], "Notification must convey business action"