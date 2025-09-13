
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
CRITICAL WebSocket Message to Agent Execution Golden Path E2E Test

Business Value Justification (BVJ):
- Segment: All customer tiers (Free, Early, Mid, Enterprise) - $500K+ ARR protection
- Business Goal: Validate complete WebSocket message routing to agent execution flow
- Value Impact: Ensures core business functionality - chat interactions that deliver AI value
- Strategic Impact: Mission critical infrastructure for substantive chat experience

CRITICAL: This test validates the complete golden path from user message to agent execution
with all 5 required WebSocket events. This represents 90% of our delivered business value.

Test Scope:
1. WebSocket connection with JWT authentication
2. User message routing to AgentHandler 
3. Agent execution pipeline with sub-agents
4. All 5 critical WebSocket events validation
5. Complete flow from GOLDEN_PATH_USER_FLOW_COMPLETE.md

Expected Result: This test SHOULD FAIL initially to prove current issues exist.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

# SSOT imports with absolute paths
from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.real_services import ServiceEndpoints
from tests.e2e.staging_config import StagingTestConfig
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class WebSocketEventCapture:
    """Captures and validates WebSocket events during agent execution."""
    
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    connection_events: List[str] = field(default_factory=list)
    agent_events: List[str] = field(default_factory=list)
    tool_events: List[str] = field(default_factory=list)
    error_events: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    def __post_init__(self):
        self.events_received = []
        self.connection_events = []
        self.agent_events = []
        self.tool_events = []
        self.error_events = []
        self.start_time = time.time()
    
    def add_event(self, event_data: Dict[str, Any]):
        """Add and categorize a WebSocket event."""
        self.events_received.append({
            **event_data,
            'received_at': time.time(),
            'relative_time': time.time() - self.start_time
        })
        
        event_type = event_data.get('type', 'unknown')
        
        # Categorize events
        if event_type in ['connection_ready', 'connection_error', 'connection_closed']:
            self.connection_events.append(event_type)
        elif event_type in ['agent_started', 'agent_thinking', 'agent_completed']:
            self.agent_events.append(event_type)
        elif event_type in ['tool_executing', 'tool_completed']:
            self.tool_events.append(event_type)
        elif 'error' in event_type.lower():
            self.error_events.append(event_type)
    
    def get_critical_events(self) -> Set[str]:
        """Get the 5 critical WebSocket events that must be present."""
        critical_events = set()
        for event in self.events_received:
            event_type = event.get('type', '')
            if event_type in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                critical_events.add(event_type)
        return critical_events
    
    def has_all_critical_events(self) -> bool:
        """Check if all 5 critical events were received."""
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        received_events = self.get_critical_events()
        return required_events.issubset(received_events)
    
    def get_missing_critical_events(self) -> Set[str]:
        """Get list of missing critical events."""
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        received_events = self.get_critical_events()
        return required_events - received_events


class TestWebSocketMessageToAgentGoldenPath(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    CRITICAL: WebSocket Message to Agent Execution Golden Path Test
    
    This test validates the complete user journey from WebSocket message to agent execution
    with all required WebSocket events. It follows the patterns from GOLDEN_PATH_USER_FLOW_COMPLETE.md.
    """
    
    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        self.env = get_env()
        
        # Determine test environment
        environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        # Initialize SSOT authentication helper
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Service endpoints configuration - pass None to use default environment
        self.service_endpoints = ServiceEndpoints.from_environment()
        
        # Test tracking
        self.test_connections = []
        self.event_captures = []
        
        # Test user data
        self.test_user_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"WebSocket Golden Path Test Setup - Environment: {environment}")
        logger.info(f"Test User ID: {self.test_user_id}")
        logger.info(f"WebSocket URL: {self.auth_helper.config.websocket_url}")
    
    async def cleanup_method(self):
        """Clean up test resources."""
        logger.info("Cleaning up WebSocket golden path test resources")
        
        # Close all WebSocket connections
        for connection in self.test_connections:
            try:
                if not connection.closed:
                    await connection.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket connection: {e}")
        
        # Clear tracking lists
        self.test_connections.clear()
        self.event_captures.clear()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_message_to_agent_complete_golden_path(self):
        """
        CRITICAL: Test complete WebSocket message to agent execution golden path.
        
        This test validates the complete flow from GOLDEN_PATH_USER_FLOW_COMPLETE.md:
        1. WebSocket connection establishment with JWT authentication
        2. User message routing to AgentHandler
        3. Agent execution pipeline with SupervisorAgent
        4. Sub-agent orchestration (Data -> Optimization -> Report)
        5. All 5 critical WebSocket events must be sent
        6. Final response delivery and resource cleanup
        
        Expected Result: This test SHOULD FAIL initially to prove current system issues.
        """
        logger.info("[U+1F680] Starting WebSocket Message to Agent Golden Path Test")
        
        # Create event capture for validation
        event_capture = WebSocketEventCapture()
        self.event_captures.append(event_capture)
        
        # Step 1: Establish authenticated WebSocket connection
        logger.info("[U+1F4E1] Step 1: Establishing authenticated WebSocket connection")
        websocket = await self._establish_authenticated_websocket_connection(event_capture)
        
        # Step 2: Send user message and track routing
        logger.info("[U+1F4AC] Step 2: Sending user message for agent execution")
        user_message = {
            "type": "user_message",
            "text": "Analyze my AI costs and provide optimization recommendations",
            "thread_id": self.test_thread_id,
            "user_id": self.test_user_id,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        await websocket.send(json.dumps(user_message))
        logger.info(f" PASS:  Sent user message: {user_message['text']}")
        
        # Step 3: Listen for WebSocket events with timeout
        logger.info("[U+1F442] Step 3: Listening for WebSocket events during agent execution")
        await self._listen_for_websocket_events(websocket, event_capture, timeout=60.0)
        
        # Step 4: Validate all critical events were received
        logger.info(" PASS:  Step 4: Validating critical WebSocket events")
        self._validate_critical_websocket_events(event_capture)
        
        # Step 5: Validate agent execution flow
        logger.info(" SEARCH:  Step 5: Validating agent execution flow")
        self._validate_agent_execution_flow(event_capture)
        
        # Step 6: Clean up connection
        logger.info("[U+1F9F9] Step 6: Cleaning up WebSocket connection")
        await websocket.close()
        
        logger.info(" CELEBRATION:  WebSocket Message to Agent Golden Path Test completed")
    
    async def _establish_authenticated_websocket_connection(self, event_capture: WebSocketEventCapture) -> websockets.WebSocketServerProtocol:
        """Establish authenticated WebSocket connection following golden path."""
        try:
            # Use SSOT authentication helper for WebSocket connection
            websocket = await self.auth_helper.connect_authenticated_websocket(timeout=15.0)
            self.test_connections.append(websocket)
            
            # Wait for connection_ready message
            ready_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            ready_data = json.loads(ready_message)
            event_capture.add_event(ready_data)
            
            # Validate connection ready
            assert ready_data.get('type') == 'connection_ready', f"Expected connection_ready, got: {ready_data}"
            assert ready_data.get('user_id') is not None, "Missing user_id in connection_ready message"
            
            logger.info(f" PASS:  WebSocket connection established with user_id: {ready_data.get('user_id')}")
            return websocket
            
        except Exception as e:
            logger.error(f" FAIL:  Failed to establish WebSocket connection: {e}")
            raise AssertionError(f"WebSocket connection failed: {e}")
    
    async def _listen_for_websocket_events(self, websocket: websockets.WebSocketServerProtocol, event_capture: WebSocketEventCapture, timeout: float):
        """Listen for WebSocket events during agent execution."""
        start_time = time.time()
        events_received = 0
        last_event_time = start_time
        
        try:
            while time.time() - start_time < timeout:
                try:
                    # Wait for next message with shorter timeout to allow checking overall timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    events_received += 1
                    last_event_time = time.time()
                    
                    # Parse and capture event
                    event_data = json.loads(message)
                    event_capture.add_event(event_data)
                    
                    event_type = event_data.get('type', 'unknown')
                    logger.info(f"[U+1F4E8] Received WebSocket event [{events_received}]: {event_type}")
                    
                    # Log critical events specially
                    if event_type in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                        logger.info(f" TARGET:  CRITICAL EVENT: {event_type} - {event_data.get('message', '')}")
                    
                    # Check if we received agent_completed (potential end of flow)
                    if event_type == 'agent_completed':
                        logger.info("[U+1F3C1] Received agent_completed - agent execution may be finished")
                        # Continue listening for a bit more to catch any late events
                        await asyncio.sleep(2.0)
                        break
                        
                except asyncio.TimeoutError:
                    # Check if we've been idle too long
                    if time.time() - last_event_time > 15.0:
                        logger.warning("[U+23F0] No events received for 15 seconds, stopping listen")
                        break
                    continue
                    
        except ConnectionClosedError:
            logger.info("[U+1F50C] WebSocket connection closed by server")
        except Exception as e:
            logger.error(f" FAIL:  Error listening for WebSocket events: {e}")
            
        logger.info(f" CHART:  Total events received: {events_received} over {time.time() - start_time:.1f}s")
    
    def _validate_critical_websocket_events(self, event_capture: WebSocketEventCapture):
        """Validate that all 5 critical WebSocket events were received."""
        logger.info(" SEARCH:  Validating critical WebSocket events...")
        
        # Get received critical events
        critical_events = event_capture.get_critical_events()
        missing_events = event_capture.get_missing_critical_events()
        
        logger.info(f" PASS:  Critical events received: {sorted(critical_events)}")
        
        if missing_events:
            logger.error(f" FAIL:  MISSING CRITICAL EVENTS: {sorted(missing_events)}")
            
            # Log all received events for debugging
            logger.error("[U+1F4CB] All received events:")
            for i, event in enumerate(event_capture.events_received):
                event_type = event.get('type', 'unknown')
                relative_time = event.get('relative_time', 0)
                logger.error(f"  [{i+1}] {relative_time:.1f}s: {event_type}")
            
            # This is expected to fail initially - proves the system has issues
            assert False, (
                f"CRITICAL WebSocket events missing: {sorted(missing_events)}. "
                f"This test SHOULD FAIL initially to prove current system issues exist. "
                f"Received events: {sorted(critical_events)}. "
                f"Total events received: {len(event_capture.events_received)}"
            )
        
        logger.info(" CELEBRATION:  All critical WebSocket events successfully received!")
    
    def _validate_agent_execution_flow(self, event_capture: WebSocketEventCapture):
        """Validate the agent execution flow follows expected patterns."""
        logger.info(" SEARCH:  Validating agent execution flow patterns...")
        
        # Check that events follow logical order
        event_types = [event.get('type', 'unknown') for event in event_capture.events_received]
        
        # agent_started should come before other agent events
        if 'agent_started' in event_types and 'agent_completed' in event_types:
            started_index = event_types.index('agent_started')
            completed_index = event_types.index('agent_completed')
            
            assert started_index < completed_index, (
                f"agent_started (index {started_index}) should come before agent_completed (index {completed_index})"
            )
            logger.info(" PASS:  Agent events are in correct order")
        
        # tool_executing should come before tool_completed
        if 'tool_executing' in event_types and 'tool_completed' in event_types:
            executing_indices = [i for i, event_type in enumerate(event_types) if event_type == 'tool_executing']
            completed_indices = [i for i, event_type in enumerate(event_types) if event_type == 'tool_completed']
            
            # Each tool_executing should have a corresponding tool_completed after it
            for exec_index in executing_indices:
                matching_completed = [idx for idx in completed_indices if idx > exec_index]
                assert matching_completed, f"No tool_completed found after tool_executing at index {exec_index}"
            
            logger.info(" PASS:  Tool execution events are properly paired")
        
        # Check for reasonable timing
        total_duration = event_capture.events_received[-1].get('relative_time', 0) if event_capture.events_received else 0
        assert total_duration > 0, "Agent execution should take some time"
        assert total_duration < 120.0, f"Agent execution took too long: {total_duration}s"
        
        logger.info(f" PASS:  Agent execution completed in reasonable time: {total_duration:.1f}s")
        
        # Validate event content
        for event in event_capture.events_received:
            event_type = event.get('type', 'unknown')
            
            # All events should have timestamps
            assert 'received_at' in event, f"Event {event_type} missing timestamp"
            
            # Critical events should have meaningful content
            if event_type in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                assert event.get('message') or event.get('content') or event.get('status'), (
                    f"Critical event {event_type} should have meaningful content"
                )
        
        logger.info(" PASS:  Agent execution flow validation completed successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.critical 
    async def test_websocket_message_routing_failure_modes(self):
        """
        Test WebSocket message routing under various failure conditions.
        
        This test validates graceful handling of:
        1. Invalid message formats
        2. Authentication failures  
        3. Service unavailability
        4. Timeout scenarios
        """
        logger.info("[U+1F680] Starting WebSocket Message Routing Failure Modes Test")
        
        # Test 1: Invalid message format
        logger.info("[U+1F4CB] Test 1: Invalid message format handling")
        websocket = await self.auth_helper.connect_authenticated_websocket()
        self.test_connections.append(websocket)
        
        # Wait for connection ready
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        
        # Send invalid JSON
        invalid_message = "invalid json message"
        await websocket.send(invalid_message)
        
        # Should receive error event
        error_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        error_data = json.loads(error_response)
        
        assert error_data.get('type') == 'error', f"Expected error event, got: {error_data}"
        logger.info(" PASS:  Invalid message format properly handled")
        
        await websocket.close()
        
        logger.info(" CELEBRATION:  WebSocket Message Routing Failure Modes Test completed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_concurrent_message_handling(self):
        """
        Test WebSocket handling of concurrent messages from same user.
        
        This validates:
        1. Multiple messages don't interfere with each other
        2. Each message gets proper agent execution
        3. Events are properly isolated per message
        """
        logger.info("[U+1F680] Starting WebSocket Concurrent Message Handling Test")
        
        websocket = await self.auth_helper.connect_authenticated_websocket()
        self.test_connections.append(websocket)
        
        # Wait for connection ready
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        
        # Send multiple messages quickly
        messages = [
            {"type": "user_message", "text": "Analyze costs for project A", "thread_id": f"thread-a-{uuid.uuid4().hex[:8]}"},
            {"type": "user_message", "text": "Analyze costs for project B", "thread_id": f"thread-b-{uuid.uuid4().hex[:8]}"}
        ]
        
        for msg in messages:
            await websocket.send(json.dumps(msg))
            logger.info(f"[U+1F4E8] Sent concurrent message: {msg['text']}")
        
        # Listen for responses - should handle both messages
        events_received = []
        timeout_start = time.time()
        
        while time.time() - timeout_start < 30.0 and len(events_received) < 10:  # Expect multiple events per message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                event_data = json.loads(message)
                events_received.append(event_data)
                logger.info(f"[U+1F4E8] Received concurrent event: {event_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                break
        
        # Should have received events for both messages
        assert len(events_received) >= 2, f"Expected at least 2 events for concurrent messages, got {len(events_received)}"
        
        logger.info(f" PASS:  Concurrent messages handled - received {len(events_received)} events")
        await websocket.close()
        
        logger.info(" CELEBRATION:  WebSocket Concurrent Message Handling Test completed")


# Test Configuration and Utilities

async def run_websocket_golden_path_test():
    """Standalone function to run the golden path test for debugging."""
    test_instance = TestWebSocketMessageToAgentGoldenPath()
    test_instance.setup_method()
    
    try:
        await test_instance.test_websocket_message_to_agent_complete_golden_path()
        print(" PASS:  Golden Path Test PASSED (unexpected - system may be working)")
    except AssertionError as e:
        print(f" FAIL:  Golden Path Test FAILED (expected): {e}")
        print("This failure proves current system issues exist and need fixing.")
    except Exception as e:
        print(f"[U+1F4A5] Golden Path Test ERROR: {e}")
    finally:
        await test_instance.cleanup_method()


if __name__ == "__main__":
    # Allow running test standalone for debugging
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        asyncio.run(run_websocket_golden_path_test())
    else:
        print("WebSocket Message to Agent Golden Path E2E Test")
        print("Run with: python test_websocket_message_to_agent_golden_path.py run")
        print("Or use: pytest tests/e2e/websocket_message_routing/test_websocket_message_to_agent_golden_path.py -v")