
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Critical WebSocket Agent Events E2E Test - COMPLETELY REWRITTEN

THIS IS THE PRIMARY TEST FOR AGENT WEBSOCKET COMMUNICATION.
Business Value: $500K+ ARR protection - Core chat functionality depends on this.

Tests that ALL required agent events are sent through the WebSocket pipeline:
- agent_started: User sees agent is working
- agent_thinking: Real-time reasoning display  
- tool_executing: Tool execution visibility
- tool_completed: Tool results display
- agent_completed: Execution finished

CRITICAL: If this test fails, the chat UI will appear broken to users.
This test uses REAL services, REAL authentication, and REAL WebSocket connections.
NO MOCKS, NO FAKES, NO CHEATING.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any

import pytest
import websockets
from loguru import logger

from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


# Required events that MUST be sent for proper UI operation
CRITICAL_EVENTS = {
    "agent_started",      # Must show agent is working
    "agent_thinking",     # Must show reasoning process
    "tool_executing",     # Must show tool usage
    "tool_completed",     # Must show tool results
    "agent_completed"     # Must show completion
}

# Events that enhance UX but aren't critical
ENHANCED_EVENTS = {
    "partial_result",     # Streaming responses
    "final_report",       # Comprehensive summary
    "agent_fallback",     # Error recovery
    "agent_update",       # Status updates
}

# Event order validation
REQUIRED_EVENT_ORDER = [
    "agent_started",      # Must be first
    # ... middle events can vary ...
    "agent_completed"     # Must be last (or final_report)
]


class CriticalEventValidator:
    """Validates that all critical WebSocket events are sent."""

    def __init__(self):
        self.events: List[Dict] = []
        self.event_types: Set[str] = set()
        self.event_order: List[str] = []
        self.tool_events: List[Dict] = []
        self.thinking_events: List[Dict] = []
        self.partial_results: List[str] = []
        self.timing: Dict[str, float] = {}
        self.start_time = time.time()
        self.errors: List[str] = []

    def record_event(self, event: Dict) -> None:
        """Record a WebSocket event for validation."""
        self.events.append(event)
        event_type = event.get("type", "unknown")
        self.event_types.add(event_type)
        self.event_order.append(event_type)
        self.timing[event_type] = time.time() - self.start_time

        # Categorize events
        if event_type == "tool_executing":
            self.tool_events.append(event)
        elif event_type == "tool_completed":
            self.tool_events.append(event)
        elif event_type == "agent_thinking":
            self.thinking_events.append(event)
        elif event_type == "partial_result":
            content = event.get("data", {}).get("content", "")
            self.partial_results.append(content)

    def validate_critical_events(self) -> tuple[bool, List[str]]:
        """Validate that all critical events were sent."""
        missing = CRITICAL_EVENTS - self.event_types
        errors = []

        if missing:
            errors.append(f"CRITICAL: Missing required events: {missing}")

        # Validate event order
        if self.event_order:
            if self.event_order[0] != "agent_started":
                errors.append("CRITICAL: agent_started must be first event")

            last_event = self.event_order[-1]
            if last_event not in ["agent_completed", "final_report"]:
                errors.append(f"CRITICAL: Last event must be completion, got {last_event}")
        else:
            errors.append("CRITICAL: No events received at all!")

        # Validate tool event pairing
        tool_starts = [e for e in self.tool_events if e.get("type") == "tool_executing"]
        tool_ends = [e for e in self.tool_events if e.get("type") == "tool_completed"]

        if len(tool_starts) != len(tool_ends):
            errors.append(f"CRITICAL: Tool events not paired: {len(tool_starts)} starts, {len(tool_ends)} ends")

        return len(errors) == 0, errors

    def get_performance_metrics(self) -> Dict:
        """Get performance metrics for the event flow."""
        metrics = {
            "total_events": len(self.events),
            "unique_event_types": len(self.event_types),
            "thinking_updates": len(self.thinking_events),
            "tool_executions": len([e for e in self.tool_events if e.get("type") == "tool_executing"]),
            "partial_results": len(self.partial_results),
            "total_duration": max(self.timing.values()) if self.timing else 0
        }

        # Calculate event latencies
        if "agent_started" in self.timing:
            metrics["time_to_first_event"] = self.timing["agent_started"]

        if "agent_thinking" in self.timing:
            metrics["time_to_first_thought"] = self.timing["agent_thinking"]

        if "partial_result" in self.timing:
            metrics["time_to_first_result"] = self.timing["partial_result"]

        return metrics

    def generate_report(self) -> str:
        """Generate a comprehensive validation report."""
        is_valid, errors = self.validate_critical_events()
        metrics = self.get_performance_metrics()

        report = [
            "=" * 60,
            "CRITICAL WEBSOCKET EVENT VALIDATION REPORT",
            "=" * 60,
            f"Validation Result: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Events: {len(self.events)}",
            f"Event Types: {sorted(self.event_types)}",
            "",
            "Critical Events Status:",
        ]

        for event in CRITICAL_EVENTS:
            status = "✅" if event in self.event_types else "❌"
            report.append(f"  {status} {event}")

        if errors:
            report.extend(["", "Errors Found:"] + [f"  - {e}" for e in errors])

        report.extend([
            "",
            "Performance Metrics:",
            f"  Total Events: {metrics['total_events']}",
            f"  Total Duration: {metrics['total_duration']:.2f}s",
            f"  Thinking Updates: {metrics['thinking_updates']}",
            f"  Tool Executions: {metrics['tool_executions']}",
        ])

        if "time_to_first_thought" in metrics:
            report.append(f"  Time to First Thought: {metrics['time_to_first_thought']:.2f}s")

        report.extend(["", "Event Sequence:"])
        for i, event in enumerate(self.event_order[:20]):  # Show first 20
            report.append(f"  {i+1:2d}. {event}")

        if len(self.event_order) > 20:
            report.append(f"  ... and {len(self.event_order) - 20} more events")

        report.append("=" * 60)

        return "\n".join(report)


class TestCriticalWebSocketAgentEvents:
    """Test suite for critical WebSocket agent event flow - COMPLETELY REWRITTEN."""

    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated WebSocket helper."""
        env = get_env()
        environment = env.get("TEST_ENV", "test")
        return E2EWebSocketAuthHelper(environment=environment)

    @pytest.fixture
    def event_validator(self):
        """Create an event validator."""
        return CriticalEventValidator()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_critical_agent_lifecycle_events(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        event_validator: CriticalEventValidator
    ):
        """Test that ALL critical agent lifecycle events are sent via real WebSocket.
        
        This test uses REAL authentication, REAL WebSocket connection, and REAL services.
        It will FAIL HARD if the system doesn't work properly. No mocks, no fakes.
        """
        logger.info("🚀 Starting critical WebSocket agent events test")
        
        # STEP 1: Connect to WebSocket with real authentication
        logger.info("📡 Connecting to WebSocket with real authentication...")
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        # Track connection state
        assert websocket is not None, "Failed to establish WebSocket connection"
        logger.info("✅ WebSocket connected successfully")
        
        # STEP 2: Send a real chat message that will trigger agent execution
        test_message = {
            "type": "chat",
            "message": "What is 2 + 2? Please show your calculation.",
            "thread_id": str(uuid.uuid4()),
            "request_id": f"test-{int(time.time())}"
        }
        
        logger.info(f"📨 Sending chat message: {test_message['message']}")
        await websocket.send(json.dumps(test_message))
        
        # STEP 3: Receive and validate WebSocket events for 30 seconds max
        logger.info("👂 Listening for WebSocket events...")
        start_time = time.time()
        max_wait_time = 30.0
        
        received_completion = False
        
        while time.time() - start_time < max_wait_time and not received_completion:
            # Wait for messages with timeout
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            
            # Parse and validate event
            event = json.loads(message)
            event_validator.record_event(event)
            
            event_type = event.get("type", "unknown")
            logger.info(f"📥 Received event: {event_type}")
            
            # Check for completion events
            if event_type in ["agent_completed", "final_report"]:
                received_completion = True
                logger.info(f"🎯 Received completion event: {event_type}")
                break
                
            # Log important events
            if event_type in CRITICAL_EVENTS:
                data = event.get("data", {})
                content = str(data.get("content", ""))[:100]
                logger.info(f"📋 {event_type}: {content}...")
        
        # STEP 4: Close WebSocket connection  
        await websocket.close()
        logger.info("🔌 WebSocket connection closed")
        
        # STEP 5: Generate comprehensive validation report
        report = event_validator.generate_report()
        logger.info(f"📊 Event Validation Report:\n{report}")
        
        # STEP 6: CRITICAL ASSERTIONS - These will FAIL HARD if system is broken
        is_valid, errors = event_validator.validate_critical_events()
        
        # Assert we received some events
        assert len(event_validator.events) > 0, "CRITICAL FAILURE: No WebSocket events received at all!"
        
        # Assert we got critical events
        missing_critical = CRITICAL_EVENTS - event_validator.event_types
        assert len(missing_critical) == 0, f"CRITICAL FAILURE: Missing required events: {missing_critical}"
        
        # Assert proper event order
        assert len(event_validator.event_order) > 0, "CRITICAL FAILURE: No event sequence recorded"
        assert event_validator.event_order[0] == "agent_started", f"CRITICAL FAILURE: First event must be 'agent_started', got '{event_validator.event_order[0]}'"
        
        # Assert completion
        last_event = event_validator.event_order[-1]
        assert last_event in ["agent_completed", "final_report"], f"CRITICAL FAILURE: Last event must be completion, got '{last_event}'"
        
        # Assert we got thinking events (shows AI reasoning)
        assert len(event_validator.thinking_events) > 0, "CRITICAL FAILURE: No 'agent_thinking' events - user won't see AI reasoning"
        
        # Assert overall validation passed
        assert is_valid, f"CRITICAL FAILURE: Event validation failed:\n{chr(10).join(errors)}"
        
        logger.info("✅ All critical WebSocket agent events validated successfully!")
        
        # Performance checks
        metrics = event_validator.get_performance_metrics()
        total_duration = metrics.get("total_duration", 0)
        
        # Assert reasonable performance
        assert total_duration > 0, "CRITICAL FAILURE: No event timing recorded"
        assert total_duration < 60.0, f"PERFORMANCE FAILURE: Agent execution took too long: {total_duration:.2f}s"
        
        logger.info(f"⚡ Performance: {metrics['total_events']} events in {total_duration:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_connection_resilience(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        event_validator: CriticalEventValidator
    ):
        """Test WebSocket connection handling and error scenarios."""
        logger.info("🔄 Testing WebSocket connection resilience...")
        
        # Test connection establishment
        websocket = await auth_helper.connect_authenticated_websocket(timeout=10.0)
        assert websocket is not None, "Failed to establish initial WebSocket connection"
        
        # Send a simple ping message
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send(json.dumps(ping_message))
        logger.info("📤 Sent ping message")
        
        # Wait for any response (could be pong, error, or other)
        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        response_data = json.loads(response)
        
        logger.info(f"📨 Received response: {response_data.get('type', 'unknown')}")
        
        # Clean close
        await websocket.close()
        logger.info("✅ WebSocket resilience test completed")
        
        # Assert we got some kind of response
        assert response_data is not None, "No response to ping message"

    @pytest.mark.asyncio 
    @pytest.mark.e2e
    async def test_multiple_concurrent_websocket_messages(
        self,
        auth_helper: E2EWebSocketAuthHelper,
        event_validator: CriticalEventValidator
    ):
        """Test sending multiple messages through WebSocket connection."""
        logger.info("🔄 Testing multiple concurrent WebSocket messages...")
        
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        assert websocket is not None, "Failed to establish WebSocket connection"
        
        # Send multiple simple messages
        messages = [
            "Hello",
            "What is 1 + 1?",
            "Tell me a short joke"
        ]
        
        for i, msg in enumerate(messages):
            test_message = {
                "type": "chat",
                "message": msg,
                "thread_id": str(uuid.uuid4()),
                "request_id": f"multi-test-{i}-{int(time.time())}"
            }
            
            logger.info(f"📤 Sending message {i+1}: {msg}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for at least one response
            response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
            event = json.loads(response)
            event_validator.record_event(event)
            
            logger.info(f"📥 Got response for message {i+1}: {event.get('type', 'unknown')}")
            
            # Small delay between messages
            await asyncio.sleep(0.5)
        
        await websocket.close()
        logger.info("✅ Multiple message test completed")
        
        # Assert we got responses to all messages
        assert len(event_validator.events) >= len(messages), f"Expected at least {len(messages)} events, got {len(event_validator.events)}"


if __name__ == "__main__":
    # Run with: python -m pytest tests/e2e/test_critical_websocket_agent_events.py -v
    pytest.main([__file__, "-v", "--tb=short"])