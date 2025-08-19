"""WebSocket Event Propagation Unified Test

CRITICAL P0 TEST - $75K+ MRR Impact
BVJ: ALL tiers | Real-time UX | Missing events cause blank UI → 30% conversion loss

SPEC: websocket_communication.xml - Tests missing events reach frontend UI layers  
EVENTS: agent_thinking, partial_result, tool_executing, final_report
PERFORMANCE: Fast <100ms, Medium <1s, Slow >1s timing validation
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import pytest

pytestmark = pytest.mark.asyncio

from ..config import TEST_CONFIG, TEST_USERS, TEST_ENDPOINTS, TestDataFactory
from ..real_websocket_client import RealWebSocketClient
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EventType(Enum):
    """WebSocket event types to validate"""
    AGENT_THINKING = "agent_thinking"
    PARTIAL_RESULT = "partial_result"
    TOOL_EXECUTING = "tool_executing"
    FINAL_REPORT = "final_report"


@dataclass
class EventValidationResult:
    """Result of event payload validation"""
    event_type: str
    received_at: float
    payload_valid: bool
    timing_valid: bool
    missing_fields: List[str] = field(default_factory=list)


class WebSocketEventValidator:
    """Validates WebSocket event propagation per SPEC/websocket_communication.xml"""
    
    def __init__(self):
        self.events_received: List[Dict[str, Any]] = []
        self.validation_results: List[EventValidationResult] = []
        self.start_time = time.time()
        
        # Expected payload structures per SPEC
        self.required_fields = {
            "agent_thinking": {"thought", "agent_name"},
            "partial_result": {"content", "agent_name", "is_complete"},
            "tool_executing": {"tool_name", "agent_name", "timestamp"},
            "final_report": {"report", "total_duration_ms"}
        }
        
        # UI layer timing requirements
        self.timing_limits = {
            "tool_executing": 0.1,  # Fast layer <100ms
            "agent_thinking": 1.0,  # Medium layer <1s
            "partial_result": 1.0,  # Medium layer <1s
            "final_report": 5.0     # Slow layer <5s
        }
    
    def validate_event(self, event_type: str, payload: Dict[str, Any]) -> EventValidationResult:
        """Validate event payload and timing"""
        received_at = time.time() - self.start_time
        
        # Check required fields
        required = self.required_fields.get(event_type, set())
        missing_fields = [f for f in required if f not in payload]
        
        # Check timing
        timing_limit = self.timing_limits.get(event_type, 5.0)
        timing_valid = received_at <= timing_limit
        
        return EventValidationResult(
            event_type=event_type,
            received_at=received_at,
            payload_valid=len(missing_fields) == 0,
            timing_valid=timing_valid,
            missing_fields=missing_fields
        )
    
    def record_event(self, event: Dict[str, Any]) -> None:
        """Record and validate received event"""
        self.events_received.append({**event, "received_at": time.time() - self.start_time})
        
        event_type = event.get("type", "")
        if event_type in [e.value for e in EventType]:
            payload = event.get("payload", {})
            result = self.validate_event(event_type, payload)
            self.validation_results.append(result)


class EventPropagationTester:
    """Tests WebSocket event propagation to frontend UI layers"""
    
    def __init__(self, websocket_client: RealWebSocketClient):
        self.ws_client = websocket_client
        self.validator = WebSocketEventValidator()
        self.test_run_id = str(uuid.uuid4())
    
    async def trigger_agent_events(self) -> None:
        """Trigger agent execution that generates all required events"""
        test_message = {
            "type": "chat_message",
            "payload": {
                "message": "Test AI optimization analysis with tool usage",
                "thread_id": self.test_run_id,
                "run_id": self.test_run_id
            }
        }
        await self.ws_client.send_message(test_message)
    
    async def listen_for_events(self, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Listen for WebSocket events and validate propagation"""
        events = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                event = await asyncio.wait_for(self.ws_client.receive_message(), timeout=1.0)
                if event:
                    self.validator.record_event(event)
                    events.append(event)
                    
                    # Check if all required events received
                    received_types = {e.get("type") for e in events}
                    required_types = {e.value for e in EventType}
                    if required_types.issubset(received_types):
                        break
                        
            except asyncio.TimeoutError:
                continue
        
        return events
    
    def validate_event_ordering(self, events: List[Dict[str, Any]]) -> List[str]:
        """Validate event ordering requirements"""
        errors = []
        event_times = {e.get("type"): e.get("received_at", 0) 
                      for e in events if e.get("type") in [t.value for t in EventType]}
        
        # final_report should be last
        if "final_report" in event_times:
            final_time = event_times["final_report"]
            for event_type, event_time in event_times.items():
                if event_type != "final_report" and event_time > final_time:
                    errors.append(f"{event_type} received after final_report")
        
        return errors


@pytest.fixture
async def event_tester(real_websocket_client):
    """Create event propagation tester with authenticated WebSocket"""
    return EventPropagationTester(real_websocket_client)


async def test_agent_thinking_event_propagation(event_tester):
    """Test agent_thinking event reaches frontend with correct payload"""
    # BVJ: Medium UI layer | Agent reasoning visibility | $20K+ MRR impact
    await event_tester.trigger_agent_events()
    events = await event_tester.listen_for_events()
    
    thinking_events = [e for e in events if e.get("type") == "agent_thinking"]
    assert len(thinking_events) > 0, "No agent_thinking events received"
    
    for event in thinking_events:
        payload = event.get("payload", {})
        assert "thought" in payload, "Missing 'thought' field"
        assert "agent_name" in payload, "Missing 'agent_name' field"
        assert isinstance(payload["thought"], str) and len(payload["thought"]) > 0


async def test_partial_result_streaming_updates(event_tester):
    """Test partial_result streaming with content accumulation"""
    # BVJ: Medium UI layer | Real-time content updates | $25K+ MRR impact
    await event_tester.trigger_agent_events()
    events = await event_tester.listen_for_events()
    
    partial_events = [e for e in events if e.get("type") == "partial_result"]
    assert len(partial_events) > 0, "No partial_result events received"
    
    accumulated_content = ""
    for event in partial_events:
        payload = event.get("payload", {})
        assert all(f in payload for f in ["content", "agent_name", "is_complete"])
        accumulated_content += payload["content"]
    
    assert len(accumulated_content) > 0, "Content should accumulate"


async def test_tool_executing_notifications(event_tester):
    """Test tool_executing events with tool details and timing"""
    # BVJ: Fast UI layer | Immediate tool feedback | $15K+ MRR impact
    await event_tester.trigger_agent_events()
    events = await event_tester.listen_for_events()
    
    tool_events = [e for e in events if e.get("type") == "tool_executing"]
    assert len(tool_events) > 0, "No tool_executing events received"
    
    for event in tool_events:
        payload = event.get("payload", {})
        assert all(f in payload for f in ["tool_name", "agent_name", "timestamp"])


async def test_final_report_delivery(event_tester):
    """Test final_report with complete results and metrics"""
    # BVJ: Slow UI layer | Complete analysis results | $30K+ MRR impact
    await event_tester.trigger_agent_events()
    events = await event_tester.listen_for_events()
    
    final_events = [e for e in events if e.get("type") == "final_report"]
    assert len(final_events) > 0, "No final_report events received"
    
    for event in final_events:
        payload = event.get("payload", {})
        assert "report" in payload, "Missing 'report' field"
        assert "total_duration_ms" in payload, "Missing 'total_duration_ms' field"
        assert isinstance(payload["total_duration_ms"], (int, float))


async def test_ui_layer_timing_validation(event_tester):
    """Test UI layer timing requirements (Fast/Medium/Slow)"""
    # BVJ: All UI layers | Performance requirements | $20K+ MRR impact
    await event_tester.trigger_agent_events()
    events = await event_tester.listen_for_events()
    
    for result in event_tester.validator.validation_results:
        assert result.timing_valid, f"{result.event_type} timing invalid: {result.received_at}s"


async def test_event_ordering_consistency(event_tester):
    """Test event ordering and payload structure consistency"""
    # BVJ: All UI layers | Event flow consistency | $15K+ MRR impact
    await event_tester.trigger_agent_events()
    events = await event_tester.listen_for_events()
    
    # Validate event ordering
    ordering_errors = event_tester.validate_event_ordering(events)
    assert len(ordering_errors) == 0, f"Event ordering errors: {ordering_errors}"
    
    # Validate payload structures
    for result in event_tester.validator.validation_results:
        assert result.payload_valid, f"Invalid payload for {result.event_type}: missing {result.missing_fields}"
    
    # Log missing event types (soft assertion)
    received_types = {e.get("type") for e in events}
    required_types = {e.value for e in EventType}
    missing_types = required_types - received_types
    if missing_types:
        logger.warning(f"Missing event types: {missing_types}")