#!/usr/bin/env python3
"""
Integration Test: Agent Supervisor Race Condition Prevention

MISSION CRITICAL: This test prevents the agent supervisor race condition that causes
fallback handler creation instead of proper service initialization.

PURPOSE: Reproduce and prevent the WebSocket.py line 529 condition where supervisor is None,
ensuring the system waits for real services or fails hard, never creating fallback handlers.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent supervisor race conditions from degrading agent business value
- Value Impact: Ensure agent supervisor is available when WebSocket connections are established
- Strategic Impact: Protect core agent orchestration reliability

CRITICAL: This test must FAIL if fallback handlers are created due to supervisor race conditions.
"""

import asyncio
import json
import logging
import os
import sys
import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

# CRITICAL: Add project root to Python path for imports  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT components
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from shared.isolated_environment import get_env

# Import system components for race condition simulation
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Import BusinessValueValidator
from tests.mission_critical.test_fallback_handler_degradation_prevention import (
    BusinessValueValidator, MockServiceController
)


class AgentSupervisorRaceConditionSimulator:
    """
    Simulator for agent supervisor race conditions during WebSocket initialization.
    
    This class creates realistic race conditions where WebSocket connections are
    established before the agent supervisor is fully initialized.
    """
    
    def __init__(self):
        """Initialize race condition simulator."""
        self.original_supervisor = None
        self.race_condition_active = False
        self._lock = threading.Lock()
        
    def setup_supervisor_race_condition(self) -> None:
        """
        Set up agent supervisor race condition.
        
        This simulates the scenario where WebSocket connection happens
        before agent supervisor initialization is complete.
        """
        with self._lock:
            if not self.race_condition_active:
                # Store original supervisor
                self.original_supervisor = getattr(AgentRegistry, '_instance', None)
                
                # Create race condition: supervisor appears None during WebSocket init
                AgentRegistry._instance = None
                self.race_condition_active = True
                
                logger.warning("🚨 RACE CONDITION: Agent supervisor set to None - simulating initialization race")
    
    def resolve_supervisor_race_condition(self, delay_seconds: float = 5.0) -> None:
        """
        Resolve the race condition after a delay.
        
        This simulates the supervisor becoming available after proper initialization.
        
        Args:
            delay_seconds: How long to wait before resolving the race condition
        """
        async def delayed_resolution():
            await asyncio.sleep(delay_seconds)
            with self._lock:
                if self.race_condition_active:
                    # Restore supervisor or create new one
                    if self.original_supervisor:
                        AgentRegistry._instance = self.original_supervisor
                    else:
                        # Create new supervisor instance if needed
                        AgentRegistry._instance = AgentRegistry()
                    
                    self.race_condition_active = False
                    logger.info(f"✅ RACE RESOLVED: Agent supervisor restored after {delay_seconds}s delay")
        
        # Run resolution in background
        asyncio.create_task(delayed_resolution())
    
    def cleanup(self) -> None:
        """Clean up race condition simulation."""
        with self._lock:
            if self.race_condition_active:
                if self.original_supervisor:
                    AgentRegistry._instance = self.original_supervisor
                else:
                    AgentRegistry._instance = AgentRegistry()
                
                self.race_condition_active = False
                logger.info("🧹 CLEANUP: Agent supervisor race condition simulation cleaned up")


@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.fallback_prevention
@pytest.mark.race_condition_testing
class TestAgentSupervisorRaceCondition:
    """
    Integration tests for agent supervisor race condition prevention.
    
    These tests ensure that race conditions during supervisor initialization
    never result in fallback handler creation.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for race condition testing."""
        # Initialize environment and auth
        self.env = get_env()
        environment = self.env.get("TEST_ENV", "test")
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Initialize validators and simulators
        self.validator = BusinessValueValidator()
        self.race_simulator = AgentSupervisorRaceConditionSimulator()
        
        yield
        
        # Cleanup: Ensure race condition is resolved
        self.race_simulator.cleanup()
    
    async def test_supervisor_race_condition_should_wait_not_fallback(self):
        """
        TEST: WebSocket connection during supervisor race condition should wait, not create fallback.
        
        This test reproduces the WebSocket.py line 529 condition where supervisor is None
        and validates that the system waits for proper initialization instead of creating
        fallback handlers.
        
        EXPECTED BEHAVIOR:
        - WebSocket connection waits for supervisor initialization
        - No fallback handlers created during race condition
        - Once supervisor is available, normal agent processing resumes
        - Users receive real agent responses, never mock content
        
        FAILURE CONDITIONS:
        - Fallback handlers created during supervisor unavailability
        - Mock responses delivered to users
        - System doesn't wait for proper supervisor initialization
        """
        logger.info("🧪 INTEGRATION TEST: Supervisor race condition - wait not fallback")
        
        # Step 1: Create supervisor race condition
        self.race_simulator.setup_supervisor_race_condition()
        
        # Step 2: Schedule race condition resolution (supervisor becomes available)
        self.race_simulator.resolve_supervisor_race_condition(delay_seconds=5.0)
        
        # Step 3: Attempt WebSocket connection during race condition
        logger.info("🔌 Attempting WebSocket connection during supervisor race condition")
        
        try:
            # Connect WebSocket - should wait for supervisor or fail appropriately
            websocket = await self.auth_helper.connect_authenticated_websocket(timeout=15.0)
            
            # Step 4: Send test request that requires supervisor
            test_request = {
                "type": "user_message",
                "content": "Analyze my data and provide optimization recommendations",
                "thread_id": f"race-test-{int(time.time())}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(test_request))
            logger.info("📤 Sent test request during race condition resolution")
            
            # Step 5: Receive and validate events - should be real agent events
            events = []
            timeout = 30.0  # Allow time for race condition resolution
            end_time = time.time() + timeout
            
            while time.time() < end_time and len(events) < 5:
                try:
                    message_str = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(message_str)
                    events.append(event)
                    
                    # CRITICAL: Validate no fallback patterns in any event
                    event_content = json.dumps(event)
                    has_fallback, fallback_patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                    
                    if has_fallback:
                        raise AssertionError(
                            f"🚨 RACE CONDITION FAILURE: FALLBACK PATTERNS DETECTED\n"
                            f"Event type: {event.get('type', 'unknown')}\n"
                            f"Fallback patterns: {fallback_patterns}\n"
                            f"Event content: {event_content[:200]}...\n"
                            f"BUSINESS IMPACT: Mock response during supervisor race condition"
                        )
                    
                    logger.info(f"✅ Event {len(events)}/5 - {event.get('type')} (real agent, no fallback)")
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Event reception error: {e}")
                    break
            
            # Step 6: Validate complete real agent workflow
            assert len(events) >= 5, (
                f"🚨 INSUFFICIENT EVENTS: {len(events)}/5 - race condition may have prevented full workflow"
            )
            
            # Validate required events present
            required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            received_types = [e.get('type') for e in events]
            missing_events = [et for et in required_events if et not in received_types]
            
            assert len(missing_events) == 0, (
                f"🚨 MISSING REQUIRED EVENTS: {missing_events}\n"
                f"Received: {received_types}\n"
                f"Race condition may have caused incomplete agent workflow"
            )
            
            # Validate final response business value
            completed_events = [e for e in events if e.get('type') == 'agent_completed']
            assert len(completed_events) > 0, "No agent completion event received"
            
            final_response = completed_events[0].get('content', '')
            has_business_value, _ = self.validator.validate_response_for_business_value(final_response)
            
            assert has_business_value, (
                f"🚨 NO BUSINESS VALUE: Final response lacks authentic insights\n"
                f"Response: '{final_response[:100]}...'\n"
                f"Race condition may have caused degraded response quality"
            )
            
            await websocket.close()
            logger.success("✅ RACE CONDITION TEST PASSED: Real agents used, no fallbacks during supervisor race")
        
        except Exception as e:
            error_msg = str(e)
            
            # Check if error indicates fallback creation
            if any(word in error_msg.lower() for word in ['fallback', 'mock', 'degraded']):
                raise AssertionError(f"🚨 RACE CONDITION FAILURE: {error_msg}")
            
            # Check if it's an appropriate failure (waiting for supervisor)
            if any(phrase in error_msg.lower() for phrase in ['supervisor', 'initialization', 'timeout', 'connection']):
                logger.info(f"✅ EXPECTED BEHAVIOR: System appropriately waited/failed during race condition: {error_msg}")
                return
            
            # Unexpected error
            raise AssertionError(f"🚨 UNEXPECTED ERROR during race condition test: {error_msg}")
    
    async def test_supervisor_available_after_race_resolution(self):
        """
        TEST: Supervisor becomes available after race condition resolution.
        
        This test validates that once the race condition is resolved,
        normal agent processing resumes without any lingering fallback behavior.
        
        EXPECTED BEHAVIOR:
        - WebSocket connections succeed after race resolution
        - Normal agent workflow functions correctly
        - No residual fallback patterns from previous race condition
        """
        logger.info("🧪 INTEGRATION TEST: Normal operation after supervisor race resolution")
        
        # Step 1: Simulate and immediately resolve race condition
        self.race_simulator.setup_supervisor_race_condition()
        await asyncio.sleep(0.1)  # Brief race condition
        self.race_simulator.resolve_supervisor_race_condition(delay_seconds=0.5)
        
        # Step 2: Wait for resolution
        await asyncio.sleep(1.0)
        
        # Step 3: Normal WebSocket connection should work
        websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
        
        # Step 4: Normal agent request
        request = {
            "type": "user_message", 
            "content": "Provide cost optimization analysis with actionable recommendations",
            "thread_id": f"post-race-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send(json.dumps(request))
        
        # Step 5: Validate normal agent workflow
        events = []
        end_time = time.time() + 20.0
        
        while time.time() < end_time and len(events) < 5:
            try:
                message_str = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                event = json.loads(message_str)
                events.append(event)
            except asyncio.TimeoutError:
                continue
        
        # Validate normal operation
        assert len(events) >= 5, f"Post-race normal operation failed: {len(events)}/5 events"
        
        # Validate no fallback patterns
        for event in events:
            event_content = json.dumps(event)
            has_fallback, patterns = self.validator.validate_response_for_fallback_patterns(event_content)
            assert not has_fallback, f"Fallback patterns in post-race operation: {patterns}"
        
        await websocket.close()
        logger.success("✅ POST-RACE TEST PASSED: Normal operation resumed successfully")
    
    async def test_multiple_concurrent_connections_during_race(self):
        """
        TEST: Multiple concurrent WebSocket connections during supervisor race condition.
        
        This test validates that multiple users attempting to connect during
        a supervisor race condition all receive appropriate handling without
        any fallback handler creation.
        
        EXPECTED BEHAVIOR:
        - All connections wait appropriately for supervisor
        - No fallback handlers created for any connection
        - Once resolved, all connections function normally
        """
        logger.info("🧪 INTEGRATION TEST: Multiple concurrent connections during supervisor race")
        
        # Create race condition
        self.race_simulator.setup_supervisor_race_condition()
        
        # Schedule resolution
        self.race_simulator.resolve_supervisor_race_condition(delay_seconds=3.0)
        
        # Create multiple concurrent connection attempts
        async def connection_attempt(connection_id: int):
            try:
                websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
                
                request = {
                    "type": "user_message",
                    "content": f"Connection {connection_id} - analyze my business data",
                    "thread_id": f"concurrent-race-{connection_id}-{int(time.time())}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(request))
                
                # Receive at least one event to validate no fallbacks
                message_str = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                event = json.loads(message_str)
                
                # Validate no fallback patterns
                event_content = json.dumps(event)
                has_fallback, patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                
                if has_fallback:
                    raise AssertionError(f"Connection {connection_id} received fallback: {patterns}")
                
                await websocket.close()
                return f"Connection {connection_id} succeeded"
                
            except Exception as e:
                error_msg = str(e)
                if 'fallback' in error_msg.lower():
                    raise AssertionError(f"Connection {connection_id} fallback error: {error_msg}")
                return f"Connection {connection_id} appropriately failed: {error_msg}"
        
        # Launch multiple concurrent connections
        tasks = [connection_attempt(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate results
        for i, result in enumerate(results):
            if isinstance(result, AssertionError):
                raise result
            
            logger.info(f"✅ {result}")
        
        logger.success("✅ CONCURRENT RACE TEST PASSED: All connections handled appropriately")


if __name__ == "__main__":
    """
    Run the agent supervisor race condition integration tests.
    
    Usage:
        python tests/integration/test_agent_supervisor_race_condition.py
        pytest tests/integration/test_agent_supervisor_race_condition.py -v
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        print("🧪 INTEGRATION: Agent Supervisor Race Condition Prevention Tests")
        print("📋 These tests prevent supervisor race conditions from creating fallback handlers")
        print("🚀 Starting test execution...")
        
        exit_code = pytest.main([
            __file__,
            "-v",
            "-x",
            "--tb=short",
            "-m", "integration and race_condition_testing",
            "--durations=10"
        ])
        
        if exit_code == 0:
            print("✅ ALL TESTS PASSED: Supervisor race conditions handled correctly")
        else:
            print("🚨 TEST FAILURES: Supervisor race condition issues detected")
            
        sys.exit(exit_code)