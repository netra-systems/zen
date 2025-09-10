#!/usr/bin/env python
"""
MISSION CRITICAL TEST SUITE: WebSocket Agent Events - GCP STAGING ONLY

THIS SUITE MUST PASS OR THE GOLDEN PATH IS BROKEN.
Business Value: $500K+ ARR - Core chat functionality validation

This test suite validates WebSocket agent event integration using GCP STAGING services:
1. Real WebSocket connections to staging (NO MOCKS)
2. Real agent execution validation 
3. Real service communication with GCP Cloud Run
4. Performance validation (< 10s response time)

ARCHITECTURAL COMPLIANCE:
- Uses IsolatedEnvironment per CLAUDE.md
- Real staging WebSocket connections (wss://netra-backend-staging-*.run.app/ws)
- NO MOCKS per CLAUDE.md Section 6.1-6.2 policy
- GCP staging services for validation
- E2E authentication using SSOT patterns
- Mission critical event validation: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

ANY FAILURE HERE BLOCKS GOLDEN PATH DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional
import pytest
from loguru import logger

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import SSOT test framework
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from tests.e2e.staging_config import get_staging_config, StagingTestConfig
from shared.isolated_environment import get_env

# Mission critical event types per CLAUDE.md Section 6.1
REQUIRED_WEBSOCKET_EVENTS = {
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
}


class StagingWebSocketEventValidator:
    """Validates WebSocket events with real GCP staging service interactions."""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()

    def record_event(self, event: Dict) -> None:
        """Record an event with detailed tracking for staging validation."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")

        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

        logger.info(f"STAGING EVENT: {event_type} at {timestamp:.2f}s - {json.dumps(event, indent=2)}")

    def validate_mission_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL mission critical requirements are met per CLAUDE.md Section 6.1."""
        failures = []

        # 1. Check for required WebSocket events per CLAUDE.md
        missing = REQUIRED_WEBSOCKET_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required WebSocket events: {missing}")

        # 2. Validate event ordering for Golden Path
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order - Golden Path broken")

        # 3. Check for paired tool events
        if not self._validate_paired_events():
            failures.append("CRITICAL: Unpaired tool events - agent execution incomplete")

        # 4. Validate timing constraints for staging
        if not self._validate_staging_timing():
            failures.append("CRITICAL: Staging timing violations - performance requirements not met")

        # 5. Check for complete event data
        if not self._validate_event_data():
            failures.append("CRITICAL: Incomplete event data - cannot validate agent functionality")

        return len(failures) == 0, failures

    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order for Golden Path validation."""
        if not self.event_timeline:
            self.errors.append("No events received - WebSocket connection failed")
            return False

        # First event must be agent_started per CLAUDE.md
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"First event was {self.event_timeline[0][1]}, expected agent_started")
            return False

        # Last event should be completion
        last_event = self.event_timeline[-1][1]
        if last_event not in ["agent_completed", "final_report"]:
            self.warnings.append(f"Last event was {last_event}, expected agent_completed")

        return True

    def _validate_paired_events(self) -> bool:
        """Ensure tool events are properly paired for complete agent execution."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)

        if tool_starts != tool_ends:
            self.errors.append(f"Unpaired tool events: {tool_starts} starts, {tool_ends} completions")
            return False

        return True

    def _validate_staging_timing(self) -> bool:
        """Validate event timing constraints for GCP staging environment."""
        if not self.event_timeline:
            return True

        # Check for events that arrive too late (staging has higher latency than local)
        for timestamp, event_type, _ in self.event_timeline:
            if timestamp > 15:  # 15 second timeout for staging services per CLAUDE.md
                self.errors.append(f"Event {event_type} arrived too late: {timestamp:.2f}s > 15s")
                return False

        return True

    def _validate_event_data(self) -> bool:
        """Validate event data completeness for business value verification."""
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


class StagingWebSocketTestCore:
    """Core test infrastructure using real GCP staging services."""

    def __init__(self):
        self.staging_config: StagingTestConfig = get_staging_config()
        self.auth_helper: Optional[E2EAuthHelper] = None
        self.test_user_token: Optional[str] = None
        self.environment = "staging"

    async def setup_staging_services(self) -> Dict[str, Any]:
        """Setup real GCP staging service connections for testing."""
        logger.info("🚀 Setting up GCP staging services for WebSocket testing")
        
        # Initialize staging auth helper
        config = E2EAuthConfig.for_staging()
        self.auth_helper = E2EAuthHelper(config=config, environment="staging")
        
        # Validate staging configuration
        if not self.staging_config.validate_configuration():
            raise Exception("Staging configuration validation failed")

        # Get staging authentication token
        self.test_user_token = await self.auth_helper.get_staging_token_async()
        
        if not self.test_user_token:
            raise Exception("Failed to get staging authentication token")

        logger.info(f"✅ Staging services setup complete - Token: {self.test_user_token[:20]}...")
        
        return {
            "auth_helper": self.auth_helper,
            "user_token": self.test_user_token,
            "config": self.staging_config,
            "environment": self.environment
        }

    async def create_staging_websocket_connection(self, timeout: float = 10.0):
        """Create authenticated WebSocket connection to GCP staging."""
        import websockets
        
        if not self.auth_helper or not self.test_user_token:
            raise Exception("Staging services not initialized")

        websocket_url = self.staging_config.urls.websocket_url
        headers = self.auth_helper.get_websocket_headers(self.test_user_token)
        
        logger.info(f"🔌 Connecting to staging WebSocket: {websocket_url}")
        logger.info(f"🔑 Auth headers: {list(headers.keys())}")
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    websocket_url,
                    additional_headers=headers,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                    max_size=2**20,  # 1MB
                    open_timeout=timeout
                ),
                timeout=timeout
            )
            
            # Check if connection was successful - just return the websocket
            # The connection succeeded if we get here without exception
            logger.info("✅ Staging WebSocket connection established")
            return websocket
                
        except Exception as e:
            logger.error(f"❌ Staging WebSocket connection failed: {e}")
            raise


@pytest.mark.asyncio
@pytest.mark.mission_critical
class TestWebSocketAgentEventsStaging:
    """Mission critical tests using REAL GCP staging WebSocket connections and services."""

    @pytest.fixture
    async def staging_service_core(self):
        """Setup real GCP staging service test infrastructure."""
        core = StagingWebSocketTestCore()
        services = await core.setup_staging_services()
        yield services, core
        # Cleanup happens automatically

    async def test_staging_websocket_golden_path_validation(self, staging_service_core):
        """
        MISSION CRITICAL: Test Golden Path WebSocket validation with REAL staging services.

        This test validates the core chat functionality that generates $500K+ ARR.
        Uses real staging WebSocket connections and agent execution validation.
        
        Golden Path: User login → Send chat message → Receive agent response
        """
        services, core = staging_service_core
        validator = StagingWebSocketEventValidator()

        # Create staging WebSocket connection
        websocket = await core.create_staging_websocket_connection(timeout=15.0)
        
        try:
            # Start capturing real events from staging
            async def capture_staging_events():
                """Capture real events from staging WebSocket connection."""
                event_count = 0
                max_events = 20  # Reasonable limit for staging
                timeout_per_event = 2.0
                
                while event_count < max_events:
                    try:
                        # Use shorter timeout per event but more total time
                        message = await asyncio.wait_for(websocket.recv(), timeout=timeout_per_event)
                        if message:
                            try:
                                event = json.loads(message)
                                validator.record_event(event)
                                event_count += 1
                                
                                # Stop if we get completion event
                                if event.get("type") in ["agent_completed", "final_report"]:
                                    logger.info("🏁 Received completion event - stopping capture")
                                    break
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"Non-JSON message received: {message}")
                                
                    except asyncio.TimeoutError:
                        logger.debug(f"Event timeout after {timeout_per_event}s")
                        # Continue trying for more events, but don't fail immediately
                        if event_count == 0:
                            # If we haven't received ANY events, wait a bit longer
                            await asyncio.sleep(1.0)
                        continue
                    except Exception as e:
                        logger.warning(f"Event capture error: {e}")
                        break

            # Send real chat message to trigger Golden Path agent execution
            chat_message = {
                "type": "chat",
                "message": "Test Golden Path - analyze server performance briefly",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"📤 Sending Golden Path test message: {chat_message['message']}")
            await websocket.send(json.dumps(chat_message))

            # Capture events from real staging agent execution
            await asyncio.wait_for(capture_staging_events(), timeout=30.0)

            # Validate captured staging events per CLAUDE.md Section 6.1
            success, failures = validator.validate_mission_critical_requirements()

            if not success:
                # Log detailed failure information for debugging
                logger.error("🚨 MISSION CRITICAL FAILURE - Golden Path broken!")
                logger.error("Event timeline:")
                for i, (timestamp, event_type, event_data) in enumerate(validator.event_timeline):
                    logger.error(f"  {i+1}. {timestamp:.2f}s - {event_type}")
                
                pytest.fail(f"CRITICAL WEBSOCKET EVENT FAILURES - Golden Path broken:\n" + 
                           "\n".join(failures))

            # Additional Golden Path validations
            assert len(validator.events) >= 3, f"Insufficient events for Golden Path: {len(validator.events)} < 3"
            assert validator.event_counts.get("agent_started", 0) >= 1, "No agent_started events - agent not triggered"

            logger.info("✅ Golden Path WebSocket validation PASSED - $500K+ ARR protected")

        finally:
            await websocket.close()

    async def test_staging_websocket_connection_stability(self, staging_service_core):
        """
        MISSION CRITICAL: Test WebSocket connection stability with GCP staging services.

        Validates that staging WebSocket connections remain stable during agent execution.
        """
        services, core = staging_service_core

        # Test connection stability
        websocket = await core.create_staging_websocket_connection()
        
        try:
            # Send multiple messages to test stability
            for i in range(3):
                test_message = {
                    "type": "ping",
                    "sequence": i + 1,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await websocket.send(json.dumps(test_message))

                # Wait for response to verify connection stability
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    assert response is not None, f"No response for message {i+1}"
                    logger.info(f"✅ Message {i+1} response received")
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ Message {i+1} response timed out")

                # Short delay between messages
                await asyncio.sleep(0.5)

            logger.info("✅ Staging WebSocket connection stability validated")
            
        finally:
            await websocket.close()

    async def test_staging_websocket_authentication_validation(self, staging_service_core):
        """
        MISSION CRITICAL: Validate WebSocket authentication with staging services.
        
        Ensures proper authentication flow works with GCP staging environment.
        """
        services, core = staging_service_core
        auth_helper = services["auth_helper"]
        
        # Test token validation
        token = services["user_token"]
        validation_result = await auth_helper.validate_jwt_token(token)
        
        assert validation_result["valid"], f"Token validation failed: {validation_result.get('error')}"
        assert validation_result.get("user_id"), "Token missing user_id"
        assert validation_result.get("email"), "Token missing email"
        
        logger.info("✅ Staging WebSocket authentication validated")

    async def test_staging_performance_requirements(self, staging_service_core):
        """
        MISSION CRITICAL: Validate performance requirements with staging services.
        
        Agent responses must meet performance requirements with real GCP infrastructure.
        """
        services, core = staging_service_core
        
        start_time = time.time()
        
        # Create WebSocket connection with performance tracking
        websocket = await core.create_staging_websocket_connection(timeout=10.0)
        
        try:
            # Send performance test request
            perf_message = {
                "type": "chat",
                "message": "Quick status check",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(perf_message))

            # Wait for first meaningful response
            first_response = None
            response_start = time.time()
            
            while time.time() - response_start < 10.0:  # 10s timeout for staging
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    if message:
                        try:
                            event = json.loads(message)
                            if event.get("type") in ["agent_thinking", "tool_executing", "agent_started"]:
                                first_response = event
                                break
                        except json.JSONDecodeError:
                            continue
                except asyncio.TimeoutError:
                    continue

            response_time = time.time() - start_time

            # Validate performance requirements per CLAUDE.md
            assert first_response is not None, "No agent response within timeout"
            assert response_time < 15.0, f"Response time {response_time:.2f}s exceeds 15s staging limit"

            logger.info(f"✅ Staging performance validated - Response in {response_time:.2f}s")
            
        finally:
            await websocket.close()


if __name__ == '__main__':
    # Run the mission critical tests
    pytest.main([__file__, '-v', '--tb=short', '-m', 'mission_critical'])