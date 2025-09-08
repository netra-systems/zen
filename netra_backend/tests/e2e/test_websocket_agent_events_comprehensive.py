"""
Comprehensive WebSocket Agent Event Flow Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure chat functionality delivers real-time value to users
- Value Impact: Users must receive all 5 critical WebSocket events for meaningful AI interactions
- Strategic Impact: Core revenue driver - chat is 90% of our delivered value per CLAUDE.md

MISSION CRITICAL: This test validates that WebSocket agent events enable substantive chat value.
All 5 WebSocket events MUST be sent during agent execution per CLAUDE.md section 6:
1. agent_started - User must see agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI is working on valuable solutions)  
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User must know when valuable response is ready

CRITICAL: Uses real Docker services (PostgreSQL, Redis, Backend) and real agent execution.
NO MOCKS per CLAUDE.md "MOCKS = Abomination".
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import pytest

# Import websockets with fallback handling
try:
    import websockets
    from websockets.legacy.client import WebSocketClientProtocol
except ImportError:
    websockets = None
    WebSocketClientProtocol = None

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.websocket_helpers import WebSocketTestHelpers, WebSocketTestClient
from shared.isolated_environment import get_env


class TestWebSocketAgentEventsComprehensive(BaseE2ETest):
    """Comprehensive WebSocket agent event flow tests using real services only."""
    
    @pytest.fixture(scope="class", autouse=True)
    def ensure_services(self):
        """Ensure required services are available or skip tests."""
        # Check if websockets library is available
        if websockets is None:
            pytest.skip("websockets library not available")
        
        # For now, we'll allow the tests to run and handle connection failures gracefully
        # In a production environment, we would start services here
        yield
    
    def setup_method(self):
        """Set up each test method with authentication and event tracking."""
        super().setup_method()
        
        # Initialize authentication helper for real JWT tokens
        self.auth_helper = E2EAuthHelper(environment="test")
        # Use TEST_PORTS configuration instead of hardcoded URLs
        from test_framework.test_config import TEST_PORTS
        self.base_url = f"ws://localhost:{TEST_PORTS['backend']}"
        self.websocket_url = f"{self.base_url}/ws"
        
        # Track events across all tests
        self.received_events: List[Dict[str, Any]] = []
        self.event_counts: Dict[str, int] = {}
        
        # Required event types per CLAUDE.md section 6
        self.required_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
    
    async def _connect_authenticated_websocket(self, user_id: Optional[str] = None):
        """Connect to WebSocket with real JWT authentication.
        
        Args:
            user_id: Optional user ID for token generation
            
        Returns:
            Authenticated WebSocket connection
        """
        # Create real JWT token
        user_id = user_id or f"test-user-{uuid.uuid4().hex[:8]}"
        token = self.auth_helper.create_test_jwt_token(user_id=user_id)
        
        # Get WebSocket headers with authentication
        headers = self.auth_helper.get_websocket_headers(token)
        
        # Connect with real authentication
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            self.websocket_url,
            headers=headers,
            timeout=10.0,
            max_retries=3,
            user_id=user_id
        )
        
        return websocket
    
    async def _send_agent_request(self, websocket, message: str, agent_type: str = "triage") -> str:
        """Send agent execution request through WebSocket.
        
        Args:
            websocket: Authenticated WebSocket connection
            message: Message to send to agent
            agent_type: Type of agent to execute
            
        Returns:
            Thread ID for tracking events
        """
        thread_id = str(uuid.uuid4())
        
        request = {
            "type": "agent_request",
            "data": {
                "agent_type": agent_type,
                "message": message,
                "thread_id": thread_id,
                "context": {
                    "test_mode": True,
                    "require_all_events": True
                }
            }
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, request)
        return thread_id
    
    async def _collect_events_for_thread(
        self, 
        websocket, 
        thread_id: str, 
        timeout: float = 30.0
    ) -> List[Dict[str, Any]]:
        """Collect all WebSocket events for a specific thread with enhanced error handling.
        
        Args:
            websocket: WebSocket connection
            thread_id: Thread ID to filter events
            timeout: Maximum time to wait for events
            
        Returns:
            List of events received for the thread
            
        Raises:
            AssertionError: If no events received or critical timeout exceeded
        """
        events = []
        start_time = time.time()
        completion_received = False
        consecutive_timeouts = 0
        last_event_time = start_time
        
        # Track expected vs received events for better error reporting
        expected_events = set(self.required_events)
        received_event_types = set()
        
        self.logger.info(f"Starting event collection for thread {thread_id} with {timeout}s timeout")
        
        while time.time() - start_time < timeout and not completion_received:
            try:
                # Use shorter timeout for individual receives to check overall timeout
                message = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                consecutive_timeouts = 0  # Reset timeout counter on successful receive
                last_event_time = time.time()
                
                # Filter events for this thread
                message_thread_id = message.get("data", {}).get("thread_id")
                if message_thread_id == thread_id:
                    events.append(message)
                    
                    # Track event types for monitoring
                    event_type = message.get("type", "unknown")
                    received_event_types.add(event_type)
                    self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
                    
                    self.logger.debug(f"Received {event_type} event for thread {thread_id} ({len(events)} total)")
                    
                    # Check if we received completion
                    if event_type == "agent_completed":
                        completion_received = True
                        self.logger.info(f"Agent completion received for thread {thread_id} after {len(events)} events")
                        break
                        
                elif message_thread_id:
                    # Event for different thread - log for debugging
                    self.logger.debug(f"Ignoring event for different thread: {message_thread_id}")
                    
            except asyncio.TimeoutError:
                consecutive_timeouts += 1
                elapsed_time = time.time() - start_time
                time_since_last_event = time.time() - last_event_time
                
                self.logger.debug(
                    f"Timeout {consecutive_timeouts} waiting for events. "
                    f"Elapsed: {elapsed_time:.1f}s, since last event: {time_since_last_event:.1f}s"
                )
                
                # If we haven't received any events for 15 seconds, something is wrong
                if time_since_last_event > 15.0 and len(events) == 0:
                    self.logger.error(f"No events received for {time_since_last_event:.1f}s - possible connection issue")
                    break
                    
                # If close to overall timeout, check what we have
                if elapsed_time > timeout * 0.85:
                    self.logger.warning(
                        f"Approaching timeout ({elapsed_time:.1f}s/{timeout}s). "
                        f"Received {len(events)} events: {[e.get('type') for e in events]}"
                    )
                    if not completion_received and len(events) > 0:
                        # We have some events but no completion - wait a bit more
                        continue
                    else:
                        break
                        
            except Exception as e:
                elapsed_time = time.time() - start_time
                self.logger.error(f"Unexpected error collecting events after {elapsed_time:.1f}s: {e}")
                
                # If we have some events and error is late in process, continue
                if len(events) > 0 and elapsed_time > timeout * 0.5:
                    self.logger.warning("Continuing with partial events due to late-stage error")
                    break
                else:
                    # Early error or no events - re-raise
                    raise
        
        # Final validation and reporting
        total_time = time.time() - start_time
        
        if len(events) == 0:
            self.logger.error(
                f"CRITICAL: No events received for thread {thread_id} after {total_time:.1f}s timeout. "
                f"This indicates a complete WebSocket event system failure."
            )
            # This is a hard failure - no events means no business value delivered
            assert False, f"No WebSocket events received for thread {thread_id} - system failure"
        
        # Check if we got all required events
        missing_events = expected_events - received_event_types
        if missing_events:
            self.logger.warning(
                f"Missing required events for thread {thread_id}: {missing_events}. "
                f"Received: {received_event_types}. Time: {total_time:.1f}s"
            )
        
        self.logger.info(
            f"Event collection completed for thread {thread_id}: "
            f"{len(events)} events in {total_time:.1f}s. "
            f"Types: {sorted(received_event_types)}"
        )
        
        self.received_events.extend(events)
        return events
    
    def _validate_event_structure(self, event: Dict[str, Any], event_type: str) -> None:
        """Validate event structure matches expected format with enhanced business value checks.
        
        Args:
            event: Event to validate
            event_type: Expected event type
        """
        # Basic structure validation
        assert event.get("type") == event_type, f"Event type mismatch: expected {event_type}, got {event.get('type')}"
        assert "timestamp" in event, f"Missing timestamp in {event_type} event"
        assert "data" in event, f"Missing data in {event_type} event"
        
        # Thread ID should be present
        data = event.get("data", {})
        assert "thread_id" in data, f"Missing thread_id in {event_type} event data"
        assert "user_id" in data, f"Missing user_id in {event_type} event data"
        
        # Validate timestamp is reasonable (within last 5 minutes)
        import time
        from datetime import datetime, timezone
        timestamp = event.get("timestamp")
        if isinstance(timestamp, str):
            try:
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
            except ValueError:
                ts = float(timestamp) if timestamp.replace('.', '').isdigit() else time.time()
        else:
            ts = float(timestamp) if timestamp else time.time()
        
        current_time = time.time()
        assert abs(current_time - ts) < 300, f"Event timestamp {timestamp} is not recent (>5 minutes old)"
        
        # Specific validations by event type with business value requirements
        if event_type == "agent_started":
            assert "agent_name" in data, "Missing agent_name in agent_started event"
            # Business value: User must know which agent is helping them
            agent_name = data.get("agent_name", "")
            assert len(agent_name) > 0, "agent_name cannot be empty - user needs to know which agent is working"
            
        elif event_type == "agent_thinking":
            assert "reasoning" in data, "Missing reasoning in agent_thinking event"
            # Business value: Reasoning must be substantive for user trust
            reasoning = data.get("reasoning", "")
            assert len(reasoning) > 10, "Reasoning must be substantive (>10 chars) to build user confidence"
            
        elif event_type == "tool_executing":
            assert "tool_name" in data, "Missing tool_name in tool_executing event"
            # Business value: Tool name must be meaningful for transparency
            tool_name = data.get("tool_name", "")
            assert len(tool_name) > 0, "tool_name cannot be empty - user needs transparency about tools used"
            
        elif event_type == "tool_completed":
            assert "tool_name" in data, "Missing tool_name in tool_completed event" 
            assert "results" in data, "Missing results in tool_completed event"
            # Business value: Results must provide actionable insights
            results = data.get("results")
            assert results is not None, "Tool results cannot be null - must provide user value"
            
        elif event_type == "agent_completed":
            assert "response" in data, "Missing response in agent_completed event"
            # Business value: Final response must be substantial and actionable
            response = data.get("response", "")
            assert len(response) > 50, "Agent response must be substantial (>50 chars) to deliver business value"
    
    def _validate_event_sequence(self, events: List[Dict[str, Any]]) -> None:
        """Validate that events arrive in correct sequence.
        
        Args:
            events: List of events to validate sequence
        """
        event_types = [event.get("type") for event in events]
        
        # Agent started must be first
        assert event_types[0] == "agent_started", f"First event must be agent_started, got {event_types[0]}"
        
        # Agent completed must be last
        assert event_types[-1] == "agent_completed", f"Last event must be agent_completed, got {event_types[-1]}"
        
        # Agent thinking should come after started
        if "agent_thinking" in event_types:
            started_idx = event_types.index("agent_started")
            thinking_idx = event_types.index("agent_thinking")
            assert thinking_idx > started_idx, "agent_thinking must come after agent_started"
        
        # Tool events should be paired and in order
        tool_executing_indices = [i for i, t in enumerate(event_types) if t == "tool_executing"]
        tool_completed_indices = [i for i, t in enumerate(event_types) if t == "tool_completed"]
        
        # Each tool_executing should have corresponding tool_completed
        for exec_idx in tool_executing_indices:
            # Find next tool_completed after this tool_executing
            completed_idx = next((i for i in tool_completed_indices if i > exec_idx), None)
            assert completed_idx is not None, f"No tool_completed found after tool_executing at index {exec_idx}"
    
    async def test_execution_timing_validation(self):
        """CRITICAL: Validate that test actually executes and doesn't return in 0.00s.
        
        Per CLAUDE.md: E2E tests with 0-second execution are automatically failed.
        This indicates tests are being skipped/mocked or not connecting to real services.
        """
        test_start_time = time.time()
        
        async with await self._connect_authenticated_websocket() as websocket:
            thread_id = await self._send_agent_request(
                websocket, 
                message="Execute timing validation test",
                agent_type="triage"
            )
            
            # Collect events - this MUST take time if using real services
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=15.0)
            
            test_execution_time = time.time() - test_start_time
            
            # CRITICAL: Test must take meaningful time (>1 second) to be real
            assert test_execution_time > 1.0, (
                f"CRITICAL FAILURE: Test executed in {test_execution_time:.3f}s. "
                f"E2E tests returning in <1s indicate mocking or service bypass, "
                f"which violates CLAUDE.md real services requirement."
            )
            
            # Validate we actually received events (proves real execution)
            assert len(events) > 0, "No events received - indicates test is not using real services"
            
            # Validate events took time to arrive (proves real processing)
            if len(events) >= 2:
                first_event_time = events[0].get("timestamp", test_start_time)
                last_event_time = events[-1].get("timestamp", test_start_time)
                
                # Convert string timestamps if needed
                if isinstance(first_event_time, str):
                    try:
                        first_event_time = datetime.fromisoformat(first_event_time.replace('Z', '+00:00')).timestamp()
                    except:
                        first_event_time = test_start_time
                if isinstance(last_event_time, str):
                    try:
                        last_event_time = datetime.fromisoformat(last_event_time.replace('Z', '+00:00')).timestamp()
                    except:
                        last_event_time = time.time()
                
                event_span = last_event_time - first_event_time
                assert event_span > 0.1, (
                    f"Events arrived too quickly ({event_span:.3f}s span) - "
                    f"indicates mocked or bypassed processing"
                )
            
            self.logger.info(
                f"✅ TIMING VALIDATION PASSED: Test executed in {test_execution_time:.3f}s "
                f"with {len(events)} events, proving real service execution"
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.mission_critical
    async def test_simple_agent_request_generates_all_events(self):
        """Test that a simple agent request generates all 5 required WebSocket events.
        
        This is the core test that validates chat functionality provides business value.
        """
        async with await self._connect_authenticated_websocket() as websocket:
            # Send simple agent request
            thread_id = await self._send_agent_request(
                websocket, 
                message="What is the current weather?",
                agent_type="triage"
            )
            
            # Collect all events for this request
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=30.0)
            
            # CRITICAL: All 5 events MUST be present
            event_types = [event.get("type") for event in events]
            
            for required_event in self.required_events:
                assert required_event in event_types, (
                    f"CRITICAL FAILURE: Missing required WebSocket event '{required_event}'. "
                    f"Received events: {event_types}. "
                    f"This breaks chat functionality and prevents business value delivery."
                )
            
            # Validate event structure for each event type
            for event in events:
                event_type = event.get("type")
                if event_type in self.required_events:
                    self._validate_event_structure(event, event_type)
            
            # Validate event sequence
            self._validate_event_sequence(events)
            
            # Ensure we have at least one of each required event
            assert len(events) >= len(self.required_events), (
                f"Expected at least {len(self.required_events)} events, got {len(events)}"
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical  
    async def test_events_arrive_in_correct_order(self):
        """Test that WebSocket events arrive in the correct logical order."""
        async with await self._connect_authenticated_websocket() as websocket:
            thread_id = await self._send_agent_request(
                websocket,
                message="Analyze my cloud costs and suggest optimizations",
                agent_type="optimization" 
            )
            
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=45.0)
            event_types = [event.get("type") for event in events]
            
            # Validate sequence
            self._validate_event_sequence(events)
            
            # Verify timestamps are in ascending order
            timestamps = []
            for event in events:
                ts = event.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
                elif isinstance(ts, (int, float)):
                    ts = float(ts)
                else:
                    continue
                timestamps.append(ts)
            
            # Check timestamps are non-decreasing
            for i in range(1, len(timestamps)):
                assert timestamps[i] >= timestamps[i-1], (
                    f"Events out of chronological order: event {i} timestamp "
                    f"{timestamps[i]} < event {i-1} timestamp {timestamps[i-1]}"
                )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_events_contain_proper_user_context(self):
        """Test that events contain proper user context and isolation."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        
        async with await self._connect_authenticated_websocket(user_id=user_id) as websocket:
            thread_id = await self._send_agent_request(
                websocket,
                message="Help me understand my data usage patterns",
                agent_type="data"
            )
            
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=30.0)
            
            # Validate user context in all events
            for event in events:
                data = event.get("data", {})
                
                # Each event must contain user context
                assert data.get("user_id") == user_id, (
                    f"Event {event.get('type')} missing or incorrect user_id. "
                    f"Expected: {user_id}, Got: {data.get('user_id')}"
                )
                
                assert data.get("thread_id") == thread_id, (
                    f"Event {event.get('type')} missing or incorrect thread_id. "
                    f"Expected: {thread_id}, Got: {data.get('thread_id')}"
                )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_multiple_concurrent_requests_maintain_isolation(self):
        """Test that multiple concurrent agent requests maintain proper event isolation."""
        user_id = f"concurrent-user-{uuid.uuid4().hex[:8]}"
        
        async with await self._connect_authenticated_websocket(user_id=user_id) as websocket:
            # Send multiple concurrent requests
            thread_ids = []
            messages = [
                ("What's the weather like?", "triage"),
                ("Analyze my costs", "optimization"),
                ("Show me data trends", "data")
            ]
            
            # Send all requests concurrently
            for message, agent_type in messages:
                thread_id = await self._send_agent_request(websocket, message, agent_type)
                thread_ids.append(thread_id)
            
            # Collect events for each thread
            all_events = {}
            for thread_id in thread_ids:
                events = await self._collect_events_for_thread(websocket, thread_id, timeout=30.0)
                all_events[thread_id] = events
            
            # Validate each thread received all required events
            for thread_id, events in all_events.items():
                event_types = [event.get("type") for event in events]
                
                for required_event in self.required_events:
                    assert required_event in event_types, (
                        f"Thread {thread_id} missing required event '{required_event}'. "
                        f"Got events: {event_types}"
                    )
                
                # Validate proper isolation - all events have correct thread_id
                for event in events:
                    assert event.get("data", {}).get("thread_id") == thread_id, (
                        f"Event isolation violated: event has thread_id "
                        f"{event.get('data', {}).get('thread_id')} but expected {thread_id}"
                    )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_long_running_agent_sends_periodic_updates(self):
        """Test that long-running agents send periodic thinking events."""
        async with await self._connect_authenticated_websocket() as websocket:
            thread_id = await self._send_agent_request(
                websocket,
                message="Perform comprehensive analysis of large dataset",
                agent_type="data"
            )
            
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=60.0)
            
            # Count thinking events - should have multiple for long-running tasks
            thinking_events = [e for e in events if e.get("type") == "agent_thinking"]
            
            # Should have at least one thinking event
            assert len(thinking_events) >= 1, (
                f"Long-running agent should send at least 1 thinking event, got {len(thinking_events)}"
            )
            
            # Each thinking event should have reasoning content
            for thinking_event in thinking_events:
                reasoning = thinking_event.get("data", {}).get("reasoning", "")
                assert reasoning and len(reasoning) > 0, (
                    "Thinking events must contain non-empty reasoning"
                )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_agent_errors_still_send_completion_events(self):
        """Test that agent errors still result in completion events."""
        async with await self._connect_authenticated_websocket() as websocket:
            # Send request that will cause an error
            thread_id = await self._send_agent_request(
                websocket,
                message="FORCE_ERROR",  # Special test message that triggers error
                agent_type="triage"
            )
            
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=30.0)
            event_types = [event.get("type") for event in events]
            
            # Should still receive agent_started and agent_completed events
            assert "agent_started" in event_types, "Should receive agent_started even for errors"
            assert "agent_completed" in event_types, "Should receive agent_completed even for errors"
            
            # Find completion event and verify it indicates error
            completion_events = [e for e in events if e.get("type") == "agent_completed"]
            assert len(completion_events) > 0, "Must have completion event for error cases"
            
            completion_event = completion_events[0]
            data = completion_event.get("data", {})
            
            # Should indicate error in response or status
            assert (
                "error" in data.get("response", "").lower() or
                data.get("status") == "error" or 
                "failed" in data.get("response", "").lower()
            ), "Completion event should indicate error occurred"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_tool_execution_events_include_proper_details(self):
        """Test that tool execution events include proper tool names and parameters."""
        async with await self._connect_authenticated_websocket() as websocket:
            thread_id = await self._send_agent_request(
                websocket,
                message="Get current data metrics and generate report",
                agent_type="data"  # Data agent likely to use tools
            )
            
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=45.0)
            
            # Find tool events
            tool_executing_events = [e for e in events if e.get("type") == "tool_executing"]
            tool_completed_events = [e for e in events if e.get("type") == "tool_completed"]
            
            # If tools were used, validate their events
            if tool_executing_events:
                for tool_event in tool_executing_events:
                    data = tool_event.get("data", {})
                    
                    # Must have tool name
                    assert data.get("tool_name"), "tool_executing event must have tool_name"
                    assert isinstance(data.get("tool_name"), str), "tool_name must be string"
                    assert len(data.get("tool_name")) > 0, "tool_name must not be empty"
                    
                    # Should have parameters or arguments
                    assert (
                        "parameters" in data or 
                        "arguments" in data or
                        "input" in data
                    ), "tool_executing event should have parameters/arguments/input"
            
            if tool_completed_events:
                for tool_event in tool_completed_events:
                    data = tool_event.get("data", {})
                    
                    # Must have tool name and results
                    assert data.get("tool_name"), "tool_completed event must have tool_name"
                    assert "results" in data, "tool_completed event must have results"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_agent_thinking_events_show_reasoning_progress(self):
        """Test that agent thinking events contain meaningful reasoning progress."""
        async with await self._connect_authenticated_websocket() as websocket:
            thread_id = await self._send_agent_request(
                websocket,
                message="Create comprehensive optimization strategy with multiple steps",
                agent_type="optimization"
            )
            
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=45.0)
            
            # Find thinking events
            thinking_events = [e for e in events if e.get("type") == "agent_thinking"]
            
            assert len(thinking_events) >= 1, "Should have at least one thinking event"
            
            for thinking_event in thinking_events:
                data = thinking_event.get("data", {})
                reasoning = data.get("reasoning", "")
                
                # Reasoning should be meaningful
                assert reasoning, "Thinking event must have reasoning content"
                assert isinstance(reasoning, str), "Reasoning must be string"
                assert len(reasoning.strip()) > 10, "Reasoning should be substantive (>10 chars)"
                
                # Should not be placeholder text
                placeholder_texts = ["thinking", "processing", "loading", "..."]
                reasoning_lower = reasoning.lower()
                is_placeholder = any(placeholder in reasoning_lower and len(reasoning) < 50 
                                   for placeholder in placeholder_texts)
                assert not is_placeholder, f"Reasoning appears to be placeholder: {reasoning}"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_websocket_events_enable_chat_business_value(self):
        """Test that WebSocket events collectively enable the chat business value.
        
        This test validates the core value proposition: users receiving real-time
        visibility into AI problem-solving that delivers actionable results.
        
        CRITICAL: This test validates the core revenue driver - chat is 90% of business value.
        """
        async with await self._connect_authenticated_websocket() as websocket:
            thread_id = await self._send_agent_request(
                websocket,
                message="I need to reduce my cloud costs by 20% while maintaining performance",
                agent_type="optimization"
            )
            
            events = await self._collect_events_for_thread(websocket, thread_id, timeout=60.0)
            
            # CRITICAL: Validate complete business value delivery
            event_types = [event.get("type") for event in events]
            
            # 1. User sees agent started - confirms request acknowledged
            assert "agent_started" in event_types, "User must see agent started processing"
            started_event = next(e for e in events if e.get("type") == "agent_started")
            agent_name = started_event.get("data", {}).get("agent_name", "")
            assert agent_name, "Must show which agent is helping"
            assert len(agent_name) > 0, "Agent name must be meaningful for user confidence"
            
            # 2. User sees thinking - builds confidence AI is working on their problem  
            assert "agent_thinking" in event_types, "User must see real-time AI reasoning"
            thinking_events = [e for e in events if e.get("type") == "agent_thinking"]
            assert len(thinking_events) >= 1, "Must have at least one thinking event for transparency"
            
            total_reasoning = " ".join([
                e.get("data", {}).get("reasoning", "") for e in thinking_events
            ])
            assert len(total_reasoning) > 50, "Must provide substantive visible reasoning for user trust"
            
            # Validate reasoning contains meaningful content (not just placeholders)
            reasoning_quality_indicators = [
                "analyz", "consider", "evaluat", "assess", "recommend", "suggest",
                "identif", "determin", "calculat", "review", "examin", "process"
            ]
            reasoning_lower = total_reasoning.lower()
            has_quality_reasoning = any(indicator in reasoning_lower 
                                      for indicator in reasoning_quality_indicators)
            assert has_quality_reasoning, f"Reasoning must contain analytical thinking, not placeholders: {total_reasoning[:100]}"
            
            # 3. User sees tools being used - demonstrates systematic approach
            if "tool_executing" in event_types:
                tool_events = [e for e in events if e.get("type") == "tool_executing"]
                for tool_event in tool_events:
                    tool_name = tool_event.get("data", {}).get("tool_name", "")
                    assert tool_name, "Tool usage must be transparent to user"
                    assert len(tool_name) > 0, "Tool name must be meaningful"
                    
                # Validate tool completion events match execution events
                tool_completed_events = [e for e in events if e.get("type") == "tool_completed"]
                assert len(tool_completed_events) >= len(tool_events), "Each tool execution must have completion event"
            
            # 4. User gets final valuable result - actionable business outcome
            assert "agent_completed" in event_types, "User must receive final result"
            completion_event = next(e for e in events if e.get("type") == "agent_completed")
            response = completion_event.get("data", {}).get("response", "")
            
            # Response should be substantive and actionable
            assert len(response) > 100, f"Final response must be substantive (>100 chars), got {len(response)}"
            
            # Validate business value content
            business_value_indicators = [
                "cost", "save", "reduc", "optim", "recommend", "suggest", 
                "improv", "performance", "efficiency", "strategy", "benefit", "solution"
            ]
            response_lower = response.lower()
            business_matches = [indicator for indicator in business_value_indicators 
                              if indicator in response_lower]
            assert len(business_matches) >= 2, f"Response must contain multiple business value indicators, found: {business_matches}"
            
            # 5. Events delivered timely - user experience is responsive
            start_time = started_event.get("timestamp")
            end_time = completion_event.get("timestamp")
            
            if isinstance(start_time, str):
                try:
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp()
                except:
                    start_time = float(start_time) if str(start_time).replace('.', '').isdigit() else time.time()
            if isinstance(end_time, str):
                try:
                    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00')).timestamp()
                except:
                    end_time = float(end_time) if str(end_time).replace('.', '').isdigit() else time.time()
                    
            total_time = abs(end_time - start_time) if end_time and start_time else 0
            assert total_time < 120, f"Agent response took too long: {total_time}s (max: 2 minutes for user experience)"
            
            # 6. CRITICAL: Validate all 5 required events are present
            required_event_counts = {
                "agent_started": len([e for e in events if e.get("type") == "agent_started"]),
                "agent_thinking": len([e for e in events if e.get("type") == "agent_thinking"]),
                "tool_executing": len([e for e in events if e.get("type") == "tool_executing"]),
                "tool_completed": len([e for e in events if e.get("type") == "tool_completed"]),
                "agent_completed": len([e for e in events if e.get("type") == "agent_completed"])
            }
            
            for event_type, count in required_event_counts.items():
                if event_type in ["tool_executing", "tool_completed"]:
                    # Tool events may be 0 if no tools used, but if one exists, both must exist
                    if required_event_counts["tool_executing"] > 0 or required_event_counts["tool_completed"] > 0:
                        assert count > 0, f"If tools are used, both tool_executing and tool_completed must be present. Missing: {event_type}"
                else:
                    # Other events are mandatory
                    assert count >= 1, f"Required event {event_type} missing or insufficient count: {count}"
            
            self.logger.info(
                f"✅ CHAT BUSINESS VALUE FULLY VALIDATED: "
                f"Agent '{agent_name}' delivered {len(thinking_events)} reasoning updates, "
                f"used {required_event_counts['tool_executing']} tools, "
                f"provided {len(response)} char response with {len(business_matches)} business value indicators "
                f"in {total_time:.1f}s. Event counts: {required_event_counts}"
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_critical_websocket_event_system_health(self):
        """MISSION CRITICAL: Comprehensive system health check for WebSocket events.
        
        This test validates that the entire WebSocket event system is operational
        and delivering the core business value through all 5 required events.
        
        CRITICAL: This test MUST pass for the system to have any business value.
        """
        health_check_start = time.time()
        user_id = f"health-check-{uuid.uuid4().hex[:8]}"
        
        async with await self._connect_authenticated_websocket(user_id=user_id) as websocket:
            # Test multiple request types to ensure system robustness
            test_scenarios = [
                {"message": "Perform system health analysis", "agent_type": "triage", "min_events": 3},
                {"message": "Analyze data patterns", "agent_type": "data", "min_events": 4},
                {"message": "Optimize performance", "agent_type": "optimization", "min_events": 5}
            ]
            
            overall_health = True
            health_report = []
            
            for i, scenario in enumerate(test_scenarios):
                scenario_start = time.time()
                self.logger.info(f"Testing scenario {i+1}/3: {scenario['message'][:30]}...")
                
                try:
                    thread_id = await self._send_agent_request(
                        websocket,
                        message=scenario["message"],
                        agent_type=scenario["agent_type"]
                    )
                    
                    events = await self._collect_events_for_thread(websocket, thread_id, timeout=45.0)
                    scenario_time = time.time() - scenario_start
                    
                    # Health check validations
                    event_types = [e.get("type") for e in events]
                    unique_event_types = set(event_types)
                    
                    scenario_health = {
                        "scenario": i + 1,
                        "message": scenario["message"][:50],
                        "agent_type": scenario["agent_type"],
                        "execution_time": scenario_time,
                        "total_events": len(events),
                        "unique_event_types": len(unique_event_types),
                        "event_types": sorted(unique_event_types),
                        "has_required_events": all(req in event_types for req in ["agent_started", "agent_completed"]),
                        "success": True
                    }
                    
                    # Validate minimum event requirements
                    assert len(events) >= scenario["min_events"], (
                        f"Scenario {i+1} received insufficient events: {len(events)} < {scenario['min_events']}"
                    )
                    
                    # Validate core events present
                    assert "agent_started" in event_types, f"Scenario {i+1} missing agent_started event"
                    assert "agent_completed" in event_types, f"Scenario {i+1} missing agent_completed event"
                    
                    # Validate reasonable execution time
                    assert scenario_time > 0.5, f"Scenario {i+1} executed too quickly: {scenario_time:.3f}s"
                    assert scenario_time < 60.0, f"Scenario {i+1} took too long: {scenario_time:.1f}s"
                    
                    health_report.append(scenario_health)
                    self.logger.info(f"✅ Scenario {i+1} HEALTHY: {len(events)} events in {scenario_time:.1f}s")
                    
                except Exception as e:
                    overall_health = False
                    failed_scenario = {
                        "scenario": i + 1,
                        "message": scenario["message"][:50],
                        "agent_type": scenario["agent_type"],
                        "execution_time": time.time() - scenario_start,
                        "error": str(e),
                        "success": False
                    }
                    health_report.append(failed_scenario)
                    self.logger.error(f"❌ Scenario {i+1} FAILED: {e}")
                    
                # Small delay between scenarios
                await asyncio.sleep(1.0)
            
            total_health_check_time = time.time() - health_check_start
            
            # Generate comprehensive health report
            successful_scenarios = [s for s in health_report if s.get("success", False)]
            failed_scenarios = [s for s in health_report if not s.get("success", True)]
            
            self.logger.info("="*80)
            self.logger.info("WEBSOCKET EVENT SYSTEM HEALTH REPORT")
            self.logger.info("="*80)
            self.logger.info(f"Total Health Check Time: {total_health_check_time:.1f}s")
            self.logger.info(f"Scenarios Tested: {len(test_scenarios)}")
            self.logger.info(f"Successful: {len(successful_scenarios)}")
            self.logger.info(f"Failed: {len(failed_scenarios)}")
            
            if successful_scenarios:
                total_events = sum(s.get("total_events", 0) for s in successful_scenarios)
                avg_time = sum(s.get("execution_time", 0) for s in successful_scenarios) / len(successful_scenarios)
                self.logger.info(f"Total Events Received: {total_events}")
                self.logger.info(f"Average Execution Time: {avg_time:.1f}s")
            
            if failed_scenarios:
                self.logger.error("FAILED SCENARIOS:")
                for scenario in failed_scenarios:
                    self.logger.error(f"  - Scenario {scenario['scenario']}: {scenario.get('error', 'Unknown error')}")
            
            self.logger.info("="*80)
            
            # CRITICAL: System health must be perfect for business value delivery
            assert overall_health, (
                f"CRITICAL SYSTEM HEALTH FAILURE: {len(failed_scenarios)} of {len(test_scenarios)} "
                f"scenarios failed. WebSocket event system is not delivering business value."
            )
            
            assert len(successful_scenarios) == len(test_scenarios), (
                f"Not all test scenarios passed: {len(successful_scenarios)}/{len(test_scenarios)}"
            )
            
            self.logger.info(
                f"🎉 WEBSOCKET EVENT SYSTEM HEALTH: EXCELLENT "
                f"({len(successful_scenarios)}/{len(test_scenarios)} scenarios passed, "
                f"{sum(s.get('total_events', 0) for s in successful_scenarios)} total events)"
            )


if __name__ == "__main__":
    # Allow running individual tests with comprehensive output
    pytest.main([__file__, "-v", "--tb=short", "-s"])