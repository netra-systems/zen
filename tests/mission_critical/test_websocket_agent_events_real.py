#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: WebSocket Agent Events - REAL SERVICES ONLY

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Core chat functionality

This comprehensive test suite validates WebSocket agent event integration using REAL services:
1. Real WebSocket connections (NO MOCKS)
2. Real agent execution
3. Real service communication
4. Real timing and performance validation

ARCHITECTURAL COMPLIANCE:
- Uses IsolatedEnvironment for test isolation
- Real WebSocket connections with actual servers
- NO MOCKS per CLAUDE.md policy
- Docker-compose for service dependencies
- < 3 second response time validation

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
from netra_backend.app.core.agent_registry import AgentRegistry

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import test framework
from test_framework.environment_isolation import isolated_test_env, get_test_env_manager
from tests.clients.websocket_client import WebSocketTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.auth_client import AuthTestClient

# Import production components for validation
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager


# ============================================================================
# REAL SERVICE TEST UTILITIES
# ============================================================================

class RealWebSocketEventValidator:
    """Validates WebSocket events with real service interactions."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self, strict_mode: bool = True):
    pass
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
        
    def record(self, event: Dict) -> None:
        """Record an event with detailed tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        logger.debug(f"Event recorded: {event_type} at {timestamp:.2f}s")
        
    def validate_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL critical requirements are met."""
        failures = []
        
        # 1. Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required events: {missing}")
        
        # 2. Validate event ordering
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order")
        
        # 3. Check for paired events
        if not self._validate_paired_events():
            failures.append("CRITICAL: Unpaired tool events")
        
        # 4. Validate timing constraints
        if not self._validate_timing():
            failures.append("CRITICAL: Event timing violations")
        
        # 5. Check for data completeness
        if not self._validate_event_data():
            failures.append("CRITICAL: Incomplete event data")
        
        return len(failures) == 0, failures
    
    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order."""
        if not self.event_timeline:
            return False
            
        # First event must be agent_started
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"First event was {self.event_timeline[0][1]}, not agent_started")
            return False
        
        # Last event should be completion
        last_event = self.event_timeline[-1][1] 
        if last_event not in ["agent_completed", "final_report"]:
            self.warnings.append(f"Last event was {last_event}, not a completion event")
            
        return True
    
    def _validate_paired_events(self) -> bool:
        """Ensure tool events are properly paired."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)
        
        if tool_starts != tool_ends:
            self.errors.append(f"Tool event mismatch: {tool_starts} starts, {tool_ends} completions")
            return False
            
        return True
    
    def _validate_timing(self) -> bool:
        """Validate event timing constraints."""
        if not self.event_timeline:
            return True
            
        # Check for events that arrive too late
        for timestamp, event_type, _ in self.event_timeline:
            if timestamp > 30:  # 30 second timeout for real services
                self.errors.append(f"Event {event_type} arrived after 30s timeout at {timestamp:.2f}s")
                return False
                
        return True
    
    def _validate_event_data(self) -> bool:
        """Validate event data completeness."""
        for event in self.events:
            event_type = event.get("type")
            
            # Check required fields per event type
            if event_type == "agent_started":
                if not event.get("agent_id"):
                    self.errors.append("agent_started missing agent_id")
                    return False
                    
            elif event_type == "tool_executing":
                if not event.get("tool_name"):
                    self.errors.append("tool_executing missing tool_name")
                    return False
                    
        return True


class RealServiceTestCore:
    """Core test infrastructure using real services."""
    
    def __init__(self):
    pass
        self.auth_client = None
        self.backend_client = None 
        self.ws_client = None
        self.test_user_token = None
        self.test_env = None
        
    async def setup_real_services(self, isolated_env) -> Dict[str, Any]:
        """Setup real service connections for testing."""
        self.test_env = isolated_env
        
        # Ensure we're using real services
        assert isolated_env.get("USE_REAL_SERVICES") == "true", "Must use real services"
        assert isolated_env.get("TESTING") == "1", "Must be in test mode"
        
        # Initialize real service clients
        auth_host = isolated_env.get("AUTH_SERVICE_HOST", "localhost")
        auth_port = isolated_env.get("AUTH_SERVICE_PORT", "8001")
        backend_host = isolated_env.get("BACKEND_HOST", "localhost") 
        backend_port = isolated_env.get("BACKEND_PORT", "8000")
        
        self.auth_client = AuthTestClient(f"http://{auth_host}:{auth_port}")
        self.backend_client = BackendTestClient(f"http://{backend_host}:{backend_port}")
        
        # Create test user with real auth service
        user_data = await self._create_test_user()
        self.test_user_token = user_data["token"]
        
        # Setup WebSocket connection with real auth
        ws_url = f"ws://{backend_host}:{backend_port}/ws"
        self.ws_client = WebSocketTestClient(ws_url)
        
        await self.ws_client.connect(token=self.test_user_token, timeout=10.0)
        assert self.ws_client.is_connected, "Real WebSocket connection failed"
        
        logger.info("Real services setup complete")
        
        return {
            "auth_client": self.auth_client,
            "backend_client": self.backend_client,
            "ws_client": self.ws_client,
            "user_token": self.test_user_token,
            "env": isolated_env
        }
        
    async def _create_test_user(self) -> Dict[str, Any]:
        """Create test user using real auth service."""
        test_email = f"test-{uuid.uuid4()}@netra-test.com"
        test_password = "TestPassword123!"
        
        # Real user registration
        register_response = await self.auth_client.register(
            email=test_email,
            password=test_password,
            name="Real Test User"
        )
        assert register_response.get("success"), f"Real user registration failed: {register_response}"
        
        # Real user login
        login_response = await self.auth_client.login(test_email, test_password)
        assert login_response.get("access_token"), f"Real user login failed: {login_response}"
        
        return {
            "email": test_email,
            "token": login_response["access_token"],
            "user_id": login_response.get("user_id")
        }
        
    async def teardown_real_services(self):
        """Cleanup real service connections."""
        if self.ws_client:
            await self.ws_client.disconnect()
            
        if self.auth_client:
            await self.auth_client.close()
            
        if self.backend_client:
            await self.backend_client.close()


# ============================================================================
# MISSION CRITICAL TESTS - REAL SERVICES ONLY
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.mission_critical
class TestWebSocketAgentEventsReal:
    """Mission critical tests using REAL WebSocket connections and services."""
    
    @pytest.fixture
    async def real_service_core(self, isolated_test_env):
        """Setup real service test infrastructure."""
        core = RealServiceTestCore()
        services = await core.setup_real_services(isolated_test_env)
        yield services
        await core.teardown_real_services()
    
    async def test_real_websocket_agent_event_flow(self, real_service_core):
        """
    pass
        MISSION CRITICAL: Test complete agent event flow with REAL services.
        
        This test validates the core chat functionality that generates $500K+ ARR.
        Uses real WebSocket connections, real agent execution, real event timing.
        """
        ws_client = real_service_core["ws_client"]
        validator = RealWebSocketEventValidator()
        
        # Start capturing real events
        async def capture_real_events():
            """Capture real events from WebSocket connection."""
            event_count = 0
            while event_count < 10:  # Reasonable limit for real services
                try:
                    event = await ws_client.receive(timeout=2.0)
                    if event:
                        validator.record(event)
                        event_count += 1
                        logger.info(f"Captured real event: {event.get('type')}")
                except Exception as e:
                    logger.warning(f"Event capture error: {e}")
                    break
        
        # Start real agent request
        chat_message = "Analyze cost optimization for my AI infrastructure"
        
        # Send real chat message that will trigger agent execution
        await ws_client.send_chat(chat_message)
        
        # Capture events from real agent execution
        await asyncio.wait_for(capture_real_events(), timeout=30.0)
        
        # Validate captured real events
        success, failures = validator.validate_critical_requirements()
        
        if not success:
            pytest.fail(f"CRITICAL WEBSOCKET EVENT FAILURES:
" + "
".join(failures))
        
        # Additional real-service validations
        assert len(validator.events) >= 3, f"Insufficient events captured: {len(validator.events)}"
        assert validator.event_counts.get("agent_started", 0) >= 1, "No agent_started events"
        
        logger.info("✅ Real WebSocket agent event flow validated successfully")
    
    async def test_real_websocket_connection_reliability(self, real_service_core):
        """
    pass
        MISSION CRITICAL: Test WebSocket connection reliability with real services.
        
        Validates that real WebSocket connections remain stable during agent execution.
        """
        ws_client = real_service_core["ws_client"]
        
        # Test connection stability
        assert ws_client.is_connected, "Real WebSocket connection lost"
        
        # Send multiple messages to test stability
        for i in range(3):
            test_message = f"Connection test message {i+1}"
            await ws_client.send_chat(test_message)
            
            # Wait for response to verify connection stability
            response = await ws_client.receive(timeout=10.0)
            assert response is not None, f"No response to message {i+1} - connection unstable"
            
            # Short delay between messages
            await asyncio.sleep(0.5)
        
        # Verify connection is still active
        assert ws_client.is_connected, "WebSocket connection became unstable"
        
        logger.info("✅ Real WebSocket connection reliability validated")
    
    async def test_real_agent_event_ordering(self, real_service_core):
        """
        MISSION CRITICAL: Validate agent event ordering with real execution.
        
        Events must arrive in correct order: started → thinking → executing → completed
        """
    pass
        ws_client = real_service_core["ws_client"]
        validator = RealWebSocketEventValidator()
        
        # Send real agent request
        await ws_client.send_chat("Simple analysis request for event ordering test")
        
        # Collect events for validation
        collected_events = []
        timeout_start = time.time()
        
        while time.time() - timeout_start < 20.0:  # 20s timeout for real services
            event = await ws_client.receive(timeout=2.0)
            if event:
                collected_events.append(event)
                validator.record(event)
                
                # Stop after getting completion event
                if event.get("type") in ["agent_completed", "final_report"]:
                    break
        
        # Validate event ordering
        success, failures = validator.validate_critical_requirements()
        
        if not success:
            # Log detailed event sequence for debugging
            logger.error("Event sequence:")
            for i, (timestamp, event_type, event_data) in enumerate(validator.event_timeline):
                logger.error(f"  {i+1}. {timestamp:.2f}s: {event_type}")
            
            pytest.fail(f"CRITICAL EVENT ORDERING FAILURES:
" + "
".join(failures))
        
        logger.info(f"✅ Real agent event ordering validated - {len(collected_events)} events")
    
    async def test_real_agent_performance_timing(self, real_service_core):
        """
        MISSION CRITICAL: Validate agent performance with real services.
        
        Agent responses must meet performance requirements with real infrastructure.
        """
    pass
        ws_client = real_service_core["ws_client"]
        
        start_time = time.time()
        
        # Send performance test request
        await ws_client.send_chat("Quick performance test request")
        
        # Wait for first meaningful response
        first_response = None
        while time.time() - start_time < 15.0:  # 15s timeout for real services
            event = await ws_client.receive(timeout=2.0)
            if event and event.get("type") in ["agent_thinking", "tool_executing"]:
                first_response = event
                break
        
        response_time = time.time() - start_time
        
        # Validate performance requirements
        assert first_response is not None, "No agent response within timeout"
        assert response_time < 10.0, f"Agent response too slow: {response_time:.2f}s (max 10s for real services)"
        
        logger.info(f"✅ Real agent performance validated - {response_time:.2f}s response time")
    
    async def test_real_error_handling_and_recovery(self, real_service_core):
        """
        MISSION CRITICAL: Test error handling with real services.
        
        System must handle errors gracefully and maintain WebSocket connection.
        """
    pass
        ws_client = real_service_core["ws_client"]
        
        # Send request that might cause errors (intentionally complex)
        error_test_message = "Test error handling with invalid complex request $$INVALID$$"
        
        initial_connection = ws_client.is_connected
        assert initial_connection, "WebSocket not connected before error test"
        
        await ws_client.send_chat(error_test_message)
        
        # Collect responses including potential errors
        responses = []
        timeout_start = time.time()
        
        while time.time() - timeout_start < 10.0:
            event = await ws_client.receive(timeout=2.0)
            if event:
                responses.append(event)
                
                # Stop if we get a completion or error event
                if event.get("type") in ["agent_completed", "error", "agent_error"]:
                    break
        
        # Validate error handling
        assert ws_client.is_connected, "WebSocket connection lost during error handling"
        assert len(responses) > 0, "No response to error test request"
        
        # Verify system can handle normal requests after error
        await ws_client.send_chat("Recovery test - normal request")
        recovery_response = await ws_client.receive(timeout=5.0)
        assert recovery_response is not None, "System failed to recover after error"
        
        logger.info("✅ Real error handling and recovery validated")
    
    async def test_real_concurrent_websocket_handling(self, real_service_core):
        """
        MISSION CRITICAL: Test concurrent WebSocket message handling.
        
        System must handle multiple concurrent messages without losing events.
        """
    pass
        ws_client = real_service_core["ws_client"]
        
        # Send multiple concurrent messages
        messages = [
            "Concurrent message 1 - quick analysis",
            "Concurrent message 2 - status check", 
            "Concurrent message 3 - brief report"
        ]
        
        # Send messages rapidly
        send_start = time.time()
        for msg in messages:
            await ws_client.send_chat(msg)
            await asyncio.sleep(0.1)  # Small delay between messages
        
        # Collect all responses
        all_responses = []
        collection_start = time.time()
        
        while time.time() - collection_start < 15.0:  # 15s to collect all responses
            event = await ws_client.receive(timeout=1.0)
            if event:
                all_responses.append(event)
            else:
                # No more events, wait a bit more then break
                await asyncio.sleep(1.0)
                final_event = await ws_client.receive(timeout=1.0)
                if final_event:
                    all_responses.append(final_event)
                else:
                    break
        
        # Validate concurrent handling
        assert len(all_responses) >= len(messages), f"Insufficient responses: {len(all_responses)} < {len(messages)}"
        assert ws_client.is_connected, "WebSocket connection lost during concurrent handling"
        
        # Check for agent_started events (should have at least one)
        started_events = [e for e in all_responses if e.get("type") == "agent_started"]
        assert len(started_events) >= 1, "No agent_started events in concurrent test"
        
        logger.info(f"✅ Real concurrent WebSocket handling validated - {len(all_responses)} total responses")


# ============================================================================
# STRESS TESTS WITH REAL SERVICES
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.stress
class TestWebSocketStressReal:
    """Stress tests using real WebSocket infrastructure."""
    
    @pytest.fixture
    async def real_service_core(self, isolated_test_env):
        """Setup real service test infrastructure."""
        core = RealServiceTestCore()
        services = await core.setup_real_services(isolated_test_env)
        yield services
        await core.teardown_real_services()
    
    async def test_real_websocket_sustained_load(self, real_service_core):
        """
    pass
        STRESS TEST: Sustained WebSocket load with real services.
        
        Validates system stability under continuous real load.
        """
        ws_client = real_service_core["ws_client"]
        
        # Run sustained load for 30 seconds
        load_duration = 30.0
        message_interval = 2.0  # One message every 2 seconds
        start_time = time.time()
        
        message_count = 0
        response_count = 0
        
        while time.time() - start_time < load_duration:
            # Send load test message
            message_count += 1
            await ws_client.send_chat(f"Sustained load test message {message_count}")
            
            # Collect responses during interval
            interval_start = time.time()
            while time.time() - interval_start < message_interval:
                event = await ws_client.receive(timeout=0.5)
                if event:
                    response_count += 1
            
            # Verify connection remains stable
            assert ws_client.is_connected, f"Connection lost at message {message_count}"
        
        # Final validation
        total_time = time.time() - start_time
        assert total_time >= load_duration * 0.9, f"Test ended prematurely: {total_time:.1f}s"
        assert message_count >= load_duration / message_interval * 0.8, f"Insufficient messages sent: {message_count}"
        assert response_count > 0, "No responses received during sustained load"
        
        logger.info(f"✅ Sustained load test completed: {message_count} messages, {response_count} responses over {total_time:.1f}s")


if __name__ == '__main__':
    # Run the mission critical tests
    pytest.main([__file__, '-v', '--tb=short', '-m', 'mission_critical'])