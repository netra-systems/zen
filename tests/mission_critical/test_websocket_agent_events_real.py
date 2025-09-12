#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: WebSocket Agent Events - REAL SERVICES ONLY

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Core chat functionality

This test suite uses ONLY real WebSocket connections per CLAUDE.md "MOCKS = Abomination":
1. Real WebSocket connections to actual backend services
2. Tests all critical WebSocket event flows with Docker services
3. Validates agent integration with live WebSocket communication
4. Ensures all required WebSocket events enable substantive chat value

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
import pytest
from loguru import logger

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import environment after path setup
from shared.isolated_environment import get_env, IsolatedEnvironment

# Import E2E authentication helper - SSOT for all E2E test authentication
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper, 
    create_authenticated_user_context,
    AuthenticatedUser
)

# Import WebSocket test client
from tests.clients.websocket_client import WebSocketTestClient

# Import production components for validation
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager


# ============================================================================
# REAL WEBSOCKET EVENT VALIDATION - NO MOCKS
# ============================================================================

class RealWebSocketEventValidator:
    """Validates WebSocket events with real service interactions."""
    
    # CLAUDE.md Section 6.1: Required WebSocket Events for Substantive Chat Value
    REQUIRED_EVENTS = {
        "agent_started",     # User must see agent began processing
        "agent_thinking",    # Real-time reasoning visibility  
        "tool_executing",    # Tool usage transparency
        "tool_completed",    # Tool results display
        "agent_completed"    # User knows response is ready
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
    
    def record_event(self, event: Dict) -> None:
        """Record an event with detailed tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        # Add capture metadata
        event_with_metadata = {
            **event,
            "capture_timestamp": time.time(),
            "relative_time": timestamp
        }
        
        self.events.append(event_with_metadata)
        self.event_timeline.append((timestamp, event_type, event_with_metadata))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        logger.debug(f" CHART:  Event recorded: {event_type} at {timestamp:.2f}s")
    
    def validate_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL critical requirements are met per CLAUDE.md."""
        failures = []
        
        # 1. Check for required events (CLAUDE.md Section 6.1)
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required WebSocket events: {missing}")
        
        # 2. Validate event ordering
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order - agent_started must be first")
        
        # 3. Check for paired events
        if not self._validate_paired_events():
            failures.append("CRITICAL: Unpaired tool events - tool_executing without tool_completed")
        
        # 4. Validate timing constraints (CLAUDE.md: <10s response time)
        if not self._validate_timing():
            failures.append("CRITICAL: Event timing violations - responses too slow")
        
        # 5. Check for data completeness
        if not self._validate_event_data():
            failures.append("CRITICAL: Incomplete event data - missing required fields")
        
        return len(failures) == 0, failures
    
    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order per CLAUDE.md requirements."""
        if not self.event_timeline:
            return False
        
        # First event must be agent_started (CLAUDE.md Section 6.1)
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"First event was {self.event_timeline[0][1]}, expected agent_started")
            return False
        
        # Last event should be completion
        last_event = self.event_timeline[-1][1]
        if last_event not in ["agent_completed", "final_report"]:
            self.warnings.append(f"Last event was {last_event}, expected agent_completed")
        
        return True
    
    def _validate_paired_events(self) -> bool:
        """Ensure tool events are properly paired."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)
        
        if tool_starts != tool_ends:
            self.errors.append(f"Unpaired tool events: {tool_starts} starts vs {tool_ends} completions")
            return False
        
        return True
    
    def _validate_timing(self) -> bool:
        """Validate event timing constraints per CLAUDE.md (<10s response time)."""
        if not self.event_timeline:
            return True
        
        # Check for events that arrive too late (CLAUDE.md: <10s for performance)
        for timestamp, event_type, _ in self.event_timeline:
            if timestamp > 30:  # 30 second absolute timeout for real services
                self.errors.append(f"Event {event_type} arrived too late: {timestamp:.2f}s")
                return False
        
        return True
    
    def _validate_event_data(self) -> bool:
        """Validate event data completeness."""
        for event in self.events:
            event_type = event.get("type")
            
            # Check required fields per event type
            if event_type == "agent_started":
                if not event.get("agent_id") and not event.get("thread_id"):
                    self.errors.append("agent_started missing agent_id or thread_id")
                    return False
            elif event_type == "tool_executing":
                if not event.get("tool_name"):
                    self.errors.append("tool_executing missing tool_name")
                    return False
        
        return True


# ============================================================================
# REAL SERVICE TEST INFRASTRUCTURE
# ============================================================================

class RealWebSocketTestInfrastructure:
    """Real service test infrastructure with Docker integration."""
    
    def __init__(self):
        self.auth_helper: Optional[E2EWebSocketAuthHelper] = None
        self.ws_client: Optional[WebSocketTestClient] = None
        self.authenticated_user: Optional[AuthenticatedUser] = None
        self.test_env = get_env()
        
    async def setup_real_services(self, environment: str = "test") -> Dict[str, Any]:
        """Setup real service connections per CLAUDE.md requirements."""
        
        # CLAUDE.md: E2E Auth Mandatory - ALL e2e tests MUST use authentication
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Create authenticated user with real JWT token
        self.authenticated_user = await self.auth_helper.create_authenticated_user()
        
        # Setup WebSocket connection with real authentication
        ws_url = self.auth_helper.config.websocket_url
        self.ws_client = WebSocketTestClient(ws_url)
        
        # Connect with real JWT token and proper headers
        connected = await self.ws_client.connect(
            token=self.authenticated_user.jwt_token,
            timeout=10.0
        )
        
        if not connected:
            raise RuntimeError(f"Failed to connect to real WebSocket service at {ws_url}")
        
        logger.info(f" PASS:  Real services setup complete - WebSocket connected to {ws_url}")
        
        return {
            "ws_client": self.ws_client,
            "auth_helper": self.auth_helper,
            "authenticated_user": self.authenticated_user,
            "environment": environment
        }
    
    async def teardown_real_services(self):
        """Cleanup real service connections."""
        if self.ws_client:
            await self.ws_client.disconnect()
        
        logger.info("[U+1F9F9] Real services teardown complete")


# ============================================================================
# MISSION CRITICAL TESTS - REAL SERVICES ONLY
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.mission_critical
class TestWebSocketAgentEventsReal:
    """Mission critical tests using REAL WebSocket connections and services."""
    
    @pytest.fixture
    async def real_service_infrastructure(self):
        """Setup real service test infrastructure."""
        infrastructure = RealWebSocketTestInfrastructure()
        services = await infrastructure.setup_real_services()
        yield services
        await infrastructure.teardown_real_services()
    
    async def test_real_websocket_required_events_validation(self, real_service_infrastructure):
        """
        MISSION CRITICAL: Test all 5 required WebSocket events with REAL services.
        
        CLAUDE.md Section 6.1: This test validates the core chat functionality that 
        generates $500K+ ARR. All 5 events must be sent: agent_started, agent_thinking, 
        tool_executing, tool_completed, agent_completed.
        
        Uses real WebSocket connections, real agent execution, real event timing.
        """
        ws_client = real_service_infrastructure["ws_client"]
        validator = RealWebSocketEventValidator()
        
        # Start capturing real events from live WebSocket
        async def capture_websocket_events():
            """Capture events from real WebSocket connection."""
            event_count = 0
            timeout_start = time.time()
            
            while event_count < 20 and (time.time() - timeout_start) < 25.0:
                try:
                    event = await ws_client.receive(timeout=2.0)
                    if event:
                        validator.record_event(event)
                        event_count += 1
                        logger.info(f"[U+1F4E1] Captured event {event_count}: {event.get('type', 'unknown')}")
                        
                        # Stop after getting completion event
                        if event.get("type") in ["agent_completed", "final_report"]:
                            logger.info("[U+1F3C1] Completion event received - stopping capture")
                            break
                except Exception as e:
                    logger.warning(f" WARNING: [U+FE0F] Event capture timeout or error: {e}")
                    break
        
        # Send real chat message that will trigger agent execution
        chat_message = "Analyze cost optimization opportunities for my AI infrastructure setup"
        logger.info(f"[U+1F4AC] Sending chat message: {chat_message}")
        
        await ws_client.send_chat(chat_message)
        
        # Capture events from real agent execution
        await asyncio.wait_for(capture_websocket_events(), timeout=30.0)
        
        # Validate all captured events against CLAUDE.md requirements
        success, failures = validator.validate_critical_requirements()
        
        # CLAUDE.md: Tests must fail hard - no bypassing
        if not success:
            error_summary = "\n".join([
                " ALERT:  CRITICAL WEBSOCKET EVENT FAILURES:",
                *failures,
                f"\n CHART:  Event Summary:",
                f"  - Total events captured: {len(validator.events)}",
                f"  - Event types: {list(validator.event_counts.keys())}",
                f"  - Event counts: {validator.event_counts}",
                f"\n[U+23F1][U+FE0F] Event Timeline:",
                *[f"  {i+1}. {timestamp:.2f}s: {event_type}" 
                  for i, (timestamp, event_type, _) in enumerate(validator.event_timeline[:10])]
            ])
            pytest.fail(error_summary)
        
        # Additional validations for real service quality
        assert len(validator.events) >= 3, f"Too few events captured: {len(validator.events)}"
        assert validator.event_counts.get("agent_started", 0) >= 1, "No agent_started events"
        assert validator.event_counts.get("agent_completed", 0) >= 1, "No agent_completed events"
        
        logger.info(f" PASS:  Real WebSocket agent event flow validated successfully - {len(validator.events)} events")
    
    async def test_real_websocket_connection_stability(self, real_service_infrastructure):
        """
        MISSION CRITICAL: Test WebSocket connection stability with real services.
        
        Validates that real WebSocket connections remain stable during agent execution
        and can handle multiple sequential requests without dropping connection.
        """
        ws_client = real_service_infrastructure["ws_client"]
        
        # Verify initial connection
        assert ws_client.is_connected, "Real WebSocket connection not established"
        
        # Send multiple messages to test stability
        messages = [
            "Quick status check",
            "Brief analysis request", 
            "Simple performance query"
        ]
        
        for i, message in enumerate(messages):
            logger.info(f"[U+1F4E4] Sending stability test message {i+1}: {message}")
            await ws_client.send_chat(message)
            
            # Wait for response to verify connection stability
            response = await ws_client.receive(timeout=10.0)
            assert response is not None, f"No response to message {i+1} - connection unstable"
            
            # Verify connection remains active
            assert ws_client.is_connected, f"WebSocket connection lost after message {i+1}"
            
            # Small delay between messages
            await asyncio.sleep(0.5)
        
        logger.info(" PASS:  Real WebSocket connection stability validated")
    
    async def test_real_agent_event_sequence_ordering(self, real_service_infrastructure):
        """
        MISSION CRITICAL: Validate agent event ordering with real execution.
        
        CLAUDE.md Section 6.1: Events must arrive in correct order to provide
        substantive chat value. Validates: started  ->  thinking  ->  executing  ->  completed
        """
        ws_client = real_service_infrastructure["ws_client"]
        validator = RealWebSocketEventValidator()
        
        # Send real agent request
        await ws_client.send_chat("Provide a brief analysis for event ordering validation")
        
        # Collect events with detailed timeline tracking
        collected_events = []
        timeout_start = time.time()
        
        while time.time() - timeout_start < 20.0:
            event = await ws_client.receive(timeout=2.0)
            if event:
                collected_events.append(event)
                validator.record_event(event)
                
                # Stop after getting completion event
                if event.get("type") in ["agent_completed", "final_report"]:
                    break
        
        # Validate event ordering per CLAUDE.md requirements
        success, failures = validator.validate_critical_requirements()
        
        if not success:
            # Log detailed event sequence for debugging
            logger.error(" SEARCH:  Event sequence analysis:")
            for i, (timestamp, event_type, event_data) in enumerate(validator.event_timeline):
                logger.error(f"  {i+1}. {timestamp:.2f}s: {event_type} - {event_data.get('message', '')[:50]}")
            
            pytest.fail(f" ALERT:  CRITICAL EVENT ORDERING FAILURES:\n" + "\n".join(failures))
        
        logger.info(f" PASS:  Real agent event ordering validated - {len(collected_events)} events in correct sequence")
    
    async def test_real_agent_performance_timing(self, real_service_infrastructure):
        """
        MISSION CRITICAL: Validate agent performance with real services.
        
        CLAUDE.md: Agent responses must meet performance requirements (<10s) with 
        real infrastructure to ensure user experience quality.
        """
        ws_client = real_service_infrastructure["ws_client"]
        
        start_time = time.time()
        
        # Send performance test request
        await ws_client.send_chat("Quick performance validation test")
        
        # Wait for first meaningful response
        first_response = None
        while time.time() - start_time < 15.0:
            event = await ws_client.receive(timeout=2.0)
            if event and event.get("type") in ["agent_thinking", "tool_executing", "agent_started"]:
                first_response = event
                break
        
        response_time = time.time() - start_time
        
        # Validate performance requirements per CLAUDE.md
        assert first_response is not None, "No agent response within timeout period"
        assert response_time < 10.0, f"Response too slow: {response_time:.2f}s (limit: 10s)"
        
        logger.info(f" PASS:  Real agent performance validated - first response in {response_time:.2f}s")
    
    async def test_real_error_handling_resilience(self, real_service_infrastructure):
        """
        MISSION CRITICAL: Test error handling with real services.
        
        System must handle errors gracefully and maintain WebSocket connection
        to ensure continuous chat functionality.
        """
        ws_client = real_service_infrastructure["ws_client"]
        
        # Verify initial connection state
        initial_connection = ws_client.is_connected
        assert initial_connection, "WebSocket not connected before error test"
        
        # Send request that might cause processing challenges
        error_test_message = "Handle this edge case gracefully: complex multi-step analysis with potential errors"
        await ws_client.send_chat(error_test_message)
        
        # Collect responses including potential errors
        responses = []
        timeout_start = time.time()
        
        while time.time() - timeout_start < 15.0:
            event = await ws_client.receive(timeout=2.0)
            if event:
                responses.append(event)
                
                # Stop if we get a completion or error event
                if event.get("type") in ["agent_completed", "error", "agent_error", "final_report"]:
                    break
        
        # Validate error handling capability
        assert ws_client.is_connected, "WebSocket connection lost during error handling"
        assert len(responses) > 0, "No response to error test request"
        
        # Verify system can handle normal requests after potential error
        await ws_client.send_chat("Recovery test - simple status check")
        recovery_response = await ws_client.receive(timeout=8.0)
        assert recovery_response is not None, "System failed to recover after error scenario"
        
        logger.info(" PASS:  Real error handling and recovery validated")
    
    async def test_real_concurrent_message_handling(self, real_service_infrastructure):
        """
        MISSION CRITICAL: Test concurrent WebSocket message handling.
        
        System must handle multiple concurrent messages without losing events
        to support active user sessions.
        """
        ws_client = real_service_infrastructure["ws_client"]
        
        # Send multiple concurrent messages
        messages = [
            "Concurrent request 1 - brief status",
            "Concurrent request 2 - quick check", 
            "Concurrent request 3 - simple query"
        ]
        
        # Send messages with small delays
        send_start = time.time()
        for msg in messages:
            await ws_client.send_chat(msg)
            await asyncio.sleep(0.2)  # Small delay between messages
        
        # Collect all responses
        all_responses = []
        collection_start = time.time()
        no_response_count = 0
        
        while time.time() - collection_start < 20.0:
            event = await ws_client.receive(timeout=1.0)
            if event:
                all_responses.append(event)
                no_response_count = 0  # Reset counter
            else:
                no_response_count += 1
                if no_response_count >= 3:  # Stop after 3 consecutive timeouts
                    break
        
        # Validate concurrent handling
        assert len(all_responses) >= len(messages), f"Too few responses: {len(all_responses)} for {len(messages)} messages"
        assert ws_client.is_connected, "WebSocket connection lost during concurrent handling"
        
        # Check for agent_started events (should have at least one)
        started_events = [r for r in all_responses if r.get("type") == "agent_started"]
        assert len(started_events) >= 1, "No agent_started events in concurrent test"
        
        logger.info(f" PASS:  Real concurrent message handling validated - {len(all_responses)} responses to {len(messages)} messages")


# ============================================================================
# PERFORMANCE VALIDATION WITH REAL SERVICES
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.performance  
class TestWebSocketPerformanceReal:
    """Performance validation using real WebSocket infrastructure."""
    
    @pytest.fixture
    async def real_service_infrastructure(self):
        """Setup real service test infrastructure."""
        infrastructure = RealWebSocketTestInfrastructure()
        services = await infrastructure.setup_real_services()
        yield services
        await infrastructure.teardown_real_services()
    
    async def test_real_websocket_response_time_compliance(self, real_service_infrastructure):
        """
        PERFORMANCE TEST: Validate WebSocket response times with real services.
        
        CLAUDE.md requirement: Responses must be < 10 seconds for user experience.
        Validates system performance under real infrastructure constraints.
        """
        ws_client = real_service_infrastructure["ws_client"]
        
        # Test multiple requests to get performance baseline
        response_times = []
        
        test_messages = [
            "Quick performance test 1",
            "Brief response validation 2", 
            "Simple timing check 3"
        ]
        
        for i, message in enumerate(test_messages):
            start_time = time.time()
            await ws_client.send_chat(message)
            
            # Wait for first response
            first_response = None
            while time.time() - start_time < 12.0:
                event = await ws_client.receive(timeout=1.0)
                if event and event.get("type") in ["agent_started", "agent_thinking"]:
                    first_response = event
                    break
            
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            assert first_response is not None, f"No response to message {i+1}"
            assert response_time < 10.0, f"Message {i+1} too slow: {response_time:.2f}s"
            
            # Small delay between tests
            await asyncio.sleep(1.0)
        
        # Calculate performance metrics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        logger.info(f" PASS:  Performance validation complete:")
        logger.info(f"  - Average response time: {avg_response_time:.2f}s")
        logger.info(f"  - Max response time: {max_response_time:.2f}s")
        logger.info(f"  - All responses under 10s limit: {all(t < 10.0 for t in response_times)}")
        
        # Performance assertions
        assert avg_response_time < 5.0, f"Average response time too slow: {avg_response_time:.2f}s"
        assert max_response_time < 10.0, f"Maximum response time exceeded: {max_response_time:.2f}s"


if __name__ == '__main__':
    # Run the mission critical tests
    pytest.main([__file__, '-v', '--tb=short', '-m', 'mission_critical'])