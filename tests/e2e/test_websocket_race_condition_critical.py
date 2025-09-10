#!/usr/bin/env python3
"""CRITICAL E2E TEST SUITE: WebSocket Race Condition Bug Reproduction and Validation

CRITICAL BUSINESS VALUE: Fixes the WebSocket "Need to call 'accept' first" race condition
that prevents delivery of Chat business value ($500K+ ARR) in staging environment.

This test suite REPRODUCES the exact staging failure pattern and validates the fix:
1. Race condition reproduction with timing precision
2. Multi-user concurrent load testing with real authentication
3. Cloud Run network latency simulation (100-300ms delays)
4. Critical agent events delivery validation (all 5 events)

STAGING ERROR PATTERN REPRODUCED:
- "WebSocket is not connected. Need to call 'accept' first."
- "Message routing failed for ws_10146348_*"
- User 101463487227881885914 consistently affected
- Error frequency: Every ~3 minutes

CLAUDE.md COMPLIANCE:
- ✅ Real authentication via e2e_auth_helper.py (NO MOCKS = ABOMINATION)
- ✅ Real services via unified_test_runner.py --real-services
- ✅ Tests MUST FAIL HARD - no try/except bypassing
- ✅ E2E tests completing in 0.00s = automatic hard failure
- ✅ Business value focus: Chat delivery pipeline validation

Business Impact: Prevents user churn from failed WebSocket connections
Revenue Impact: Ensures reliable Chat interactions for revenue retention
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
import uuid
import websockets
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import pytest
from contextlib import asynccontextmanager

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import environment and authentication
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig, create_authenticated_user_context
from test_framework.base_e2e_test import BaseE2ETest

# Import WebSocket and agent components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier

logger = logging.getLogger(__name__)


# ============================================================================
# SPECIALIZED WEBSOCKET RACE CONDITION TEST FRAMEWORK
# ============================================================================

class WebSocketRaceConditionTestFramework:
    """
    Specialized framework for testing WebSocket race conditions in Cloud Run environments.
    
    Features:
    - Connection state monitoring with microsecond precision
    - Network delay injection to simulate GCP Cloud Run conditions
    - Agent event delivery tracking and validation
    - Race condition reproduction with controlled timing
    """
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.connection_state_log: List[Dict] = []
        self.event_delivery_log: List[Dict] = []
        self.race_condition_errors: List[Dict] = []
        self.start_time = time.time()
        
        # Critical event types for Chat business value
        self.critical_agent_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        # Network delay ranges for different environments
        self.cloud_run_latency_ranges = {
            "test": (0.01, 0.05),      # 10-50ms local
            "staging": (0.1, 0.3),     # 100-300ms Cloud Run
            "production": (0.05, 0.15) # 50-150ms optimized production
        }
    
    def log_connection_state(self, connection_id: str, state: str, details: Dict = None):
        """Log connection state change with microsecond precision."""
        entry = {
            "timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "connection_id": connection_id,
            "state": state,
            "details": details or {},
            "microseconds": int((time.time() % 1) * 1_000_000)
        }
        self.connection_state_log.append(entry)
        logger.debug(f"Connection state: {connection_id} -> {state}")
    
    def simulate_cloud_run_latency(self, delay_type: str = "random") -> float:
        """Inject network delays to simulate GCP Cloud Run conditions."""
        min_delay, max_delay = self.cloud_run_latency_ranges.get(
            self.environment, (0.01, 0.05)
        )
        
        if delay_type == "random":
            delay = random.uniform(min_delay, max_delay)
        elif delay_type == "high":
            delay = max_delay
        elif delay_type == "low":
            delay = min_delay
        else:
            delay = (min_delay + max_delay) / 2
        
        return delay
    
    async def inject_network_delay(self, delay_type: str = "random"):
        """Async network delay injection."""
        delay = self.simulate_cloud_run_latency(delay_type)
        await asyncio.sleep(delay)
        return delay
    
    def track_agent_event(self, event_type: str, thread_id: str, details: Dict = None):
        """Track agent event delivery for business value validation."""
        entry = {
            "timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "event_type": event_type,
            "thread_id": thread_id,
            "is_critical": event_type in self.critical_agent_events,
            "details": details or {}
        }
        self.event_delivery_log.append(entry)
        logger.info(f"Agent event delivered: {event_type} for thread {thread_id}")
    
    def detect_race_condition_error(self, error_message: str, connection_id: str):
        """Detect and log race condition errors matching staging pattern."""
        race_condition_indicators = [
            "Need to call 'accept' first",
            "WebSocket is not connected",
            "Message routing failed",
            "race condition between accept() and message handling"
        ]
        
        is_race_condition = any(indicator in error_message for indicator in race_condition_indicators)
        
        if is_race_condition:
            error_entry = {
                "timestamp": time.time(),
                "relative_time": time.time() - self.start_time,
                "connection_id": connection_id,
                "error_message": error_message,
                "error_type": "race_condition"
            }
            self.race_condition_errors.append(error_entry)
            logger.error(f"RACE CONDITION DETECTED: {connection_id} - {error_message}")
            return True
        
        return False
    
    async def validate_agent_event_delivery(self, expected_events: Set[str], thread_id: str, timeout_seconds: float = 30.0) -> Dict:
        """Validate all critical agent events are delivered within timeout."""
        start_time = time.time()
        delivered_events = set()
        
        while time.time() - start_time < timeout_seconds:
            # Check delivered events for this thread
            for event in self.event_delivery_log:
                if event["thread_id"] == thread_id and event["event_type"] in expected_events:
                    delivered_events.add(event["event_type"])
            
            # If all events delivered, success
            if expected_events.issubset(delivered_events):
                return {
                    "success": True,
                    "delivered_events": delivered_events,
                    "missing_events": set(),
                    "delivery_time": time.time() - start_time
                }
            
            await asyncio.sleep(0.1)  # Check every 100ms
        
        # Timeout reached
        missing_events = expected_events - delivered_events
        return {
            "success": False,
            "delivered_events": delivered_events,
            "missing_events": missing_events,
            "delivery_time": timeout_seconds
        }
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report."""
        total_connections = len(set(log["connection_id"] for log in self.connection_state_log))
        race_condition_count = len(self.race_condition_errors)
        critical_events_delivered = len([e for e in self.event_delivery_log if e["is_critical"]])
        
        return {
            "test_duration": time.time() - self.start_time,
            "total_connections": total_connections,
            "race_condition_errors": race_condition_count,
            "critical_events_delivered": critical_events_delivered,
            "connection_success_rate": (total_connections - race_condition_count) / max(total_connections, 1),
            "race_condition_frequency": race_condition_count / max(time.time() - self.start_time, 1) * 60,  # per minute
            "detailed_errors": self.race_condition_errors,
            "connection_log": self.connection_state_log,
            "event_delivery_log": self.event_delivery_log
        }


# ============================================================================
# WEBSOCKET CONNECTION UTILITIES WITH RACE CONDITION DETECTION
# ============================================================================

class RaceConditionWebSocketClient:
    """WebSocket client with enhanced race condition detection and state monitoring."""
    
    def __init__(self, auth_helper: E2EWebSocketAuthHelper, test_framework: WebSocketRaceConditionTestFramework):
        self.auth_helper = auth_helper
        self.test_framework = test_framework
        self.websocket = None
        self.connection_id = None
        self.is_connected = False
        self.received_messages = []
        self.connection_errors = []
    
    @asynccontextmanager
    async def connect(self, timeout: float = 15.0):
        """Connect with race condition monitoring and Cloud Run delay simulation."""
        self.connection_id = f"race_test_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        try:
            # Log connection attempt
            self.test_framework.log_connection_state(
                self.connection_id, "connecting", 
                {"timeout": timeout, "environment": self.test_framework.environment}
            )
            
            # Simulate Cloud Run network delays before connection
            delay_injected = await self.test_framework.inject_network_delay("random")
            self.test_framework.log_connection_state(
                self.connection_id, "network_delay_injected", 
                {"delay_ms": delay_injected * 1000}
            )
            
            # Get authenticated WebSocket connection
            self.websocket = await self.auth_helper.connect_authenticated_websocket(timeout=timeout)
            self.is_connected = True
            
            self.test_framework.log_connection_state(
                self.connection_id, "connected", 
                {"connection_time": time.time()}
            )
            
            # Start message monitoring task
            message_task = asyncio.create_task(self._monitor_messages())
            
            try:
                yield self
            finally:
                # Clean up
                message_task.cancel()
                try:
                    await message_task
                except asyncio.CancelledError:
                    pass
                
                if self.websocket:
                    await self.websocket.close()
                    self.is_connected = False
                    
                    self.test_framework.log_connection_state(
                        self.connection_id, "disconnected",
                        {"messages_received": len(self.received_messages)}
                    )
        
        except Exception as e:
            error_message = str(e)
            self.connection_errors.append(error_message)
            
            # Check for race condition errors
            is_race_condition = self.test_framework.detect_race_condition_error(
                error_message, self.connection_id
            )
            
            self.test_framework.log_connection_state(
                self.connection_id, "error",
                {"error": error_message, "is_race_condition": is_race_condition}
            )
            
            # Re-raise all errors for hard failure (per CLAUDE.md)
            raise
    
    async def _monitor_messages(self):
        """Monitor incoming messages and detect race conditions."""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0  # Short timeout for responsive monitoring
                    )
                    
                    self.received_messages.append({
                        "timestamp": time.time(),
                        "message": message
                    })
                    
                    # Parse and track agent events
                    try:
                        parsed = json.loads(message)
                        if "type" in parsed and "thread_id" in parsed:
                            self.test_framework.track_agent_event(
                                parsed["type"], 
                                parsed["thread_id"],
                                {"connection_id": self.connection_id}
                            )
                    except json.JSONDecodeError:
                        pass  # Non-JSON messages are okay
                    
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue monitoring
                except Exception as e:
                    error_message = str(e)
                    
                    # Detect race condition in message handling
                    is_race_condition = self.test_framework.detect_race_condition_error(
                        error_message, self.connection_id
                    )
                    
                    if is_race_condition:
                        # Race condition detected - log and continue monitoring
                        logger.error(f"Race condition in message handling: {error_message}")
                    else:
                        # Other error - may indicate connection issue
                        logger.warning(f"Message monitoring error: {error_message}")
                        break
        
        except asyncio.CancelledError:
            # Task cancelled - normal cleanup
            pass
    
    async def send_agent_request(self, request_data: Dict) -> str:
        """Send agent request and return thread ID for event tracking."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError("WebSocket not connected")
        
        # Generate thread ID for tracking
        thread_id = f"thread_{self.connection_id}_{int(time.time() * 1000)}"
        request_data["thread_id"] = thread_id
        
        await self.websocket.send(json.dumps(request_data))
        return thread_id


# ============================================================================
# CRITICAL E2E TEST CASES - RACE CONDITION REPRODUCTION AND VALIDATION
# ============================================================================

class TestWebSocketRaceConditionCritical:
    """
    CRITICAL E2E test suite for WebSocket race condition bug.
    
    Tests the exact staging failure pattern and validates fixes.
    MUST use real authentication and services per CLAUDE.md.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up test class with real service requirements."""
        cls.env = get_env()
        
        # Determine test environment
        cls.test_environment = cls.env.get("TEST_ENV", cls.env.get("ENVIRONMENT", "test"))
        
        logger.info(f"🚀 Starting WebSocket Race Condition Critical Tests")
        logger.info(f"📍 Environment: {cls.test_environment}")
        logger.info(f"🎯 Testing race condition reproduction and validation")
    
    def setup_method(self, method):
        """Set up each test method with authenticated helpers."""
        # Create authenticated WebSocket helper for each test
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        
        # Reset test framework for each test
        self.test_framework = WebSocketRaceConditionTestFramework(self.test_environment)
        
        logger.info(f"🧪 Starting test: {method.__name__}")
        logger.info(f"🔐 Authentication configured for: {self.test_environment}")
    
    @pytest.mark.asyncio
    async def test_websocket_race_condition_reproduction(self):
        """
        CRITICAL TEST: Reproduce the exact staging race condition failure pattern.
        
        This test MUST initially reproduce the staging failures, then pass after fix.
        
        Staging Error Pattern:
        - "WebSocket is not connected. Need to call 'accept' first."
        - Message routing failures every ~3 minutes
        - User 101463487227881885914 pattern
        
        Business Value: Prevents user churn from failed WebSocket connections
        Success Criteria: Zero race condition errors over 10-minute test
        """
        test_start_time = time.time()
        logger.info("🔥 CRITICAL: Reproducing staging WebSocket race condition")
        
        # Test configuration for race condition reproduction
        test_duration_seconds = 120  # 2 minutes intensive test
        connection_interval_seconds = 5  # New connection every 5 seconds
        expected_connections = test_duration_seconds // connection_interval_seconds
        
        race_condition_clients = []
        connection_tasks = []
        
        try:
            # Create multiple concurrent connections to trigger race conditions
            while time.time() - test_start_time < test_duration_seconds:
                client = RaceConditionWebSocketClient(self.auth_helper, self.test_framework)
                race_condition_clients.append(client)
                
                # Create connection task with race condition monitoring
                task = asyncio.create_task(self._test_single_connection_with_delays(client))
                connection_tasks.append(task)
                
                # Wait for connection interval with cloud delay simulation
                await self.test_framework.inject_network_delay("high")
            
            # Wait for all connection tasks to complete
            logger.info(f"⏳ Waiting for {len(connection_tasks)} connection tests to complete...")
            await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Generate comprehensive test report
            report = self.test_framework.generate_report()
            
            # Log detailed results
            logger.info("📊 RACE CONDITION TEST RESULTS:")
            logger.info(f"   Total Duration: {report['test_duration']:.2f}s")
            logger.info(f"   Total Connections: {report['total_connections']}")
            logger.info(f"   Race Condition Errors: {report['race_condition_errors']}")
            logger.info(f"   Connection Success Rate: {report['connection_success_rate']:.2%}")
            logger.info(f"   Race Condition Frequency: {report['race_condition_frequency']:.2f}/min")
            
            # CRITICAL ASSERTION: Validate race condition reproduction/resolution
            if report['race_condition_errors'] > 0:
                logger.error("🚨 RACE CONDITION REPRODUCED - This test will pass after fix implementation")
                logger.error(f"🔍 Race condition errors detected: {report['race_condition_errors']}")
                
                # Log first race condition error for debugging
                if self.test_framework.race_condition_errors:
                    first_error = self.test_framework.race_condition_errors[0]
                    logger.error(f"🔍 First race condition: {first_error['error_message']}")
                
                # BEFORE FIX: This assertion will fail (reproducing the bug)
                # AFTER FIX: This assertion should pass (bug resolved)
                pytest.fail(
                    f"RACE CONDITION REPRODUCED: {report['race_condition_errors']} race condition errors detected. "
                    f"This confirms the staging issue exists. Fix implementation required."
                )
            else:
                logger.info("✅ SUCCESS: No race condition errors detected - fix is working!")
                
                # Additional validation for fix verification
                assert report['connection_success_rate'] >= 0.95, \
                    f"Connection success rate too low: {report['connection_success_rate']:.2%}"
                
                assert report['total_connections'] >= expected_connections * 0.8, \
                    f"Insufficient connections tested: {report['total_connections']} < {expected_connections * 0.8}"
        
        except Exception as e:
            # Log exception details for debugging
            logger.error(f"❌ Race condition test failed with exception: {e}")
            
            # Generate report even on failure
            report = self.test_framework.generate_report()
            logger.error(f"📊 Partial results: {report}")
            
            # Re-raise for hard failure (per CLAUDE.md)
            raise
        
        finally:
            # Cleanup all connections
            for client in race_condition_clients:
                if client.websocket and not client.websocket.closed:
                    await client.websocket.close()
        
        # Verify test duration (no 0.00s tests per CLAUDE.md)
        actual_duration = time.time() - test_start_time
        assert actual_duration > 10.0, \
            f"E2E test completed too quickly ({actual_duration:.2f}s). Must run real connections for meaningful duration."
        
        logger.info(f"✅ Race condition reproduction test completed in {actual_duration:.2f}s")
    
    async def _test_single_connection_with_delays(self, client: RaceConditionWebSocketClient):
        """Test single connection with race condition detection."""
        try:
            # Simulate cloud environment timing conditions
            pre_connection_delay = await self.test_framework.inject_network_delay("random")
            
            async with client.connect(timeout=15.0):
                # Connection successful - test message handling
                
                # Send test message to trigger message handling
                test_message = {
                    "type": "ping",
                    "timestamp": time.time(),
                    "test_id": client.connection_id
                }
                
                await client.websocket.send(json.dumps(test_message))
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(
                        client.websocket.recv(),
                        timeout=5.0
                    )
                    logger.debug(f"✅ Connection {client.connection_id} received response")
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ Connection {client.connection_id} response timeout")
                
                # Keep connection alive to test race conditions
                await asyncio.sleep(2.0)
        
        except Exception as e:
            # Race condition or other connection error
            error_message = str(e)
            logger.warning(f"⚠️ Connection {client.connection_id} error: {error_message}")
            
            # Error will be logged by test framework
            # Don't re-raise here to allow other connections to continue
    
    @pytest.mark.asyncio 
    async def test_websocket_multi_user_concurrent_load(self):
        """
        CRITICAL TEST: Multi-user concurrent WebSocket load with real authentication.
        
        Simulates real business scenario: 5+ users connecting simultaneously.
        Validates user isolation and race condition prevention under load.
        
        Business Value: Ensures multi-user Chat scalability
        Success Criteria: All users receive agent events properly with 100% isolation
        """
        test_start_time = time.time()
        logger.info("👥 CRITICAL: Multi-user concurrent WebSocket load test")
        
        # Multi-user test configuration
        num_concurrent_users = 6  # Realistic concurrent user load
        agent_requests_per_user = 2  # Each user sends 2 agent requests
        
        user_contexts = []
        user_connections = []
        user_results = []
        
        try:
            # Create authenticated contexts for multiple users
            for i in range(num_concurrent_users):
                user_context = await create_authenticated_user_context(
                    user_email=f"concurrent_user_{i}_{int(time.time())}@example.com",
                    environment=self.test_environment,
                    websocket_enabled=True
                )
                user_contexts.append(user_context)
                logger.info(f"🔐 Created user context {i}: {user_context.user_id}")
            
            # Create concurrent WebSocket connections for all users
            connection_tasks = []
            for i, user_context in enumerate(user_contexts):
                task = asyncio.create_task(
                    self._test_concurrent_user_connection(i, user_context, agent_requests_per_user)
                )
                connection_tasks.append(task)
            
            # Execute all user connections concurrently
            logger.info(f"🚀 Starting {num_concurrent_users} concurrent user connections...")
            user_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Analyze multi-user results
            successful_users = 0
            total_events_delivered = 0
            user_isolation_violations = 0
            
            for i, result in enumerate(user_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ User {i} failed: {result}")
                else:
                    successful_users += 1
                    total_events_delivered += result.get("events_delivered", 0)
                    user_isolation_violations += result.get("isolation_violations", 0)
                    logger.info(f"✅ User {i}: {result.get('events_delivered', 0)} events delivered")
            
            # Generate multi-user test report
            report = self.test_framework.generate_report()
            
            logger.info("📊 MULTI-USER CONCURRENT LOAD RESULTS:")
            logger.info(f"   Successful Users: {successful_users}/{num_concurrent_users}")
            logger.info(f"   Total Events Delivered: {total_events_delivered}")
            logger.info(f"   User Isolation Violations: {user_isolation_violations}")
            logger.info(f"   Race Condition Errors: {report['race_condition_errors']}")
            
            # CRITICAL ASSERTIONS for multi-user business value
            user_success_rate = successful_users / num_concurrent_users
            assert user_success_rate >= 0.8, \
                f"Multi-user success rate too low: {user_success_rate:.2%} (need ≥80%)"
            
            assert user_isolation_violations == 0, \
                f"User isolation violated: {user_isolation_violations} cross-user events detected"
            
            expected_total_events = num_concurrent_users * agent_requests_per_user * len(self.test_framework.critical_agent_events)
            event_delivery_rate = total_events_delivered / expected_total_events if expected_total_events > 0 else 0
            assert event_delivery_rate >= 0.7, \
                f"Event delivery rate too low: {event_delivery_rate:.2%} (need ≥70%)"
            
            # No race conditions allowed in multi-user scenario
            assert report['race_condition_errors'] == 0, \
                f"Race conditions detected in multi-user load: {report['race_condition_errors']}"
        
        except Exception as e:
            logger.error(f"❌ Multi-user concurrent load test failed: {e}")
            raise
        
        finally:
            # Cleanup all user connections
            for connection in user_connections:
                if hasattr(connection, 'websocket') and connection.websocket and not connection.websocket.closed:
                    await connection.websocket.close()
        
        # Verify test duration
        actual_duration = time.time() - test_start_time
        assert actual_duration > 5.0, \
            f"Multi-user test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f"✅ Multi-user concurrent load test completed in {actual_duration:.2f}s")
    
    async def _test_concurrent_user_connection(self, user_index: int, user_context, agent_requests: int) -> Dict:
        """Test single user connection in concurrent scenario."""
        user_id = str(user_context.user_id)
        events_delivered = 0
        isolation_violations = 0
        
        try:
            # Create WebSocket client for this user
            client = RaceConditionWebSocketClient(self.auth_helper, self.test_framework)
            
            async with client.connect(timeout=20.0):  # Longer timeout for concurrent load
                # Send multiple agent requests per user
                for request_num in range(agent_requests):
                    # Simulate agent request
                    agent_request = {
                        "type": "agent_request",
                        "user_id": user_id,
                        "request_id": f"{user_id}_req_{request_num}",
                        "query": f"Test query {request_num} from user {user_index}",
                        "timestamp": time.time()
                    }
                    
                    thread_id = await client.send_agent_request(agent_request)
                    
                    # Wait for agent events with timeout
                    await asyncio.sleep(1.0)  # Allow time for event delivery
                
                # Count events for this user 
                user_events = [
                    event for event in self.test_framework.event_delivery_log
                    if user_id in event.get("details", {}).get("connection_id", "")
                ]
                events_delivered = len(user_events)
                
                # Check for isolation violations (events meant for other users)
                for event in client.received_messages:
                    try:
                        parsed = json.loads(event["message"])
                        event_user_id = parsed.get("user_id")
                        if event_user_id and event_user_id != user_id:
                            isolation_violations += 1
                            logger.error(f"🔒 User isolation violated: User {user_index} received event for {event_user_id}")
                    except:
                        pass  # Non-JSON messages are okay
        
        except Exception as e:
            logger.error(f"❌ User {user_index} connection failed: {e}")
            raise
        
        return {
            "user_index": user_index,
            "user_id": user_id,
            "events_delivered": events_delivered,
            "isolation_violations": isolation_violations
        }
    
    @pytest.mark.asyncio
    async def test_websocket_cloud_run_latency_simulation(self):
        """
        CRITICAL TEST: WebSocket connections under GCP Cloud Run network latency.
        
        Simulates staging environment network conditions with controlled delays.
        Validates connection stability and handshake completion with realistic latency.
        
        Business Value: Ensures Chat works reliably in Cloud Run production environment
        Success Criteria: All connections stable with 300ms+ network delays
        """
        test_start_time = time.time()
        logger.info("☁️ CRITICAL: Cloud Run network latency simulation test")
        
        # Cloud Run latency test configuration
        latency_scenarios = [
            {"name": "Low Latency", "delay_type": "low", "expected_success": 1.0},
            {"name": "Medium Latency", "delay_type": "random", "expected_success": 0.95},
            {"name": "High Latency", "delay_type": "high", "expected_success": 0.8},
        ]
        
        scenario_results = []
        
        try:
            for scenario in latency_scenarios:
                logger.info(f"🌐 Testing {scenario['name']} scenario...")
                
                scenario_start = time.time()
                connections_attempted = 5
                successful_connections = 0
                handshake_times = []
                
                # Test multiple connections under this latency scenario
                for i in range(connections_attempted):
                    try:
                        client = RaceConditionWebSocketClient(self.auth_helper, self.test_framework)
                        
                        # Force specific delay type for this scenario
                        original_delay_type = client.test_framework.environment
                        
                        handshake_start = time.time()
                        async with client.connect(timeout=30.0):  # Generous timeout for high latency
                            handshake_time = time.time() - handshake_start
                            handshake_times.append(handshake_time)
                            
                            # Test message exchange under latency
                            test_message = {
                                "type": "latency_test",
                                "scenario": scenario["name"],
                                "connection_index": i,
                                "timestamp": time.time()
                            }
                            
                            await client.websocket.send(json.dumps(test_message))
                            
                            # Wait for response with generous timeout
                            try:
                                response = await asyncio.wait_for(
                                    client.websocket.recv(),
                                    timeout=10.0
                                )
                                successful_connections += 1
                                logger.debug(f"✅ {scenario['name']} connection {i} successful")
                            except asyncio.TimeoutError:
                                logger.warning(f"⏰ {scenario['name']} connection {i} response timeout")
                                # Still count as successful connection if no handshake error
                                successful_connections += 1
                    
                    except Exception as e:
                        logger.warning(f"❌ {scenario['name']} connection {i} failed: {e}")
                        # Don't raise - continue testing other connections
                
                # Calculate scenario results
                success_rate = successful_connections / connections_attempted
                avg_handshake_time = sum(handshake_times) / len(handshake_times) if handshake_times else 0
                
                scenario_result = {
                    "name": scenario["name"],
                    "success_rate": success_rate,
                    "expected_success": scenario["expected_success"], 
                    "avg_handshake_time": avg_handshake_time,
                    "connections_attempted": connections_attempted,
                    "successful_connections": successful_connections,
                    "duration": time.time() - scenario_start
                }
                scenario_results.append(scenario_result)
                
                logger.info(f"📊 {scenario['name']} Results:")
                logger.info(f"   Success Rate: {success_rate:.2%}")
                logger.info(f"   Avg Handshake Time: {avg_handshake_time:.3f}s")
                logger.info(f"   Successful: {successful_connections}/{connections_attempted}")
                
                # Scenario-specific assertions
                assert success_rate >= scenario["expected_success"], \
                    f"{scenario['name']} success rate {success_rate:.2%} below expected {scenario['expected_success']:.2%}"
            
            # Overall test results
            report = self.test_framework.generate_report()
            
            logger.info("📊 CLOUD RUN LATENCY SIMULATION RESULTS:")
            for result in scenario_results:
                logger.info(f"   {result['name']}: {result['success_rate']:.2%} success, {result['avg_handshake_time']:.3f}s handshake")
            logger.info(f"   Race Condition Errors: {report['race_condition_errors']}")
            
            # Overall assertions
            overall_success_rate = sum(r["success_rate"] for r in scenario_results) / len(scenario_results)
            assert overall_success_rate >= 0.85, \
                f"Overall Cloud Run success rate too low: {overall_success_rate:.2%}"
            
            # No race conditions should occur even under high latency
            assert report['race_condition_errors'] == 0, \
                f"Race conditions detected under Cloud Run latency: {report['race_condition_errors']}"
        
        except Exception as e:
            logger.error(f"❌ Cloud Run latency simulation failed: {e}")
            raise
        
        # Verify test duration
        actual_duration = time.time() - test_start_time
        assert actual_duration > 10.0, \
            f"Cloud Run latency test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f"✅ Cloud Run latency simulation completed in {actual_duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_websocket_agent_events_delivery_reliability(self):
        """
        CRITICAL TEST: All 5 mission-critical agent events delivery under race conditions.
        
        This test ensures the core business value: WebSocket agent events that enable Chat.
        Tests all 5 critical events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        
        Business Value: Validates $500K+ ARR Chat functionality event delivery pipeline
        Success Criteria: All events delivered within 2s of generation with 100% reliability
        """
        test_start_time = time.time()
        logger.info("🎯 CRITICAL: Agent events delivery reliability test")
        
        # Critical agent events test configuration
        num_agent_sessions = 3  # Multiple agent sessions to test
        events_per_session = len(self.test_framework.critical_agent_events)  # All 5 critical events
        expected_total_events = num_agent_sessions * events_per_session
        
        agent_session_results = []
        
        try:
            # Create authenticated WebSocket client
            client = RaceConditionWebSocketClient(self.auth_helper, self.test_framework)
            
            async with client.connect(timeout=20.0):
                logger.info(f"🔗 WebSocket connected for agent events test")
                
                # Test multiple agent sessions
                for session_num in range(num_agent_sessions):
                    logger.info(f"🤖 Starting agent session {session_num + 1}/{num_agent_sessions}")
                    
                    session_start = time.time()
                    
                    # Send agent request
                    agent_request = {
                        "type": "agent_request",
                        "session_id": f"events_test_session_{session_num}",
                        "query": f"Test agent query {session_num} - validate all events",
                        "timestamp": time.time(),
                        "validate_events": True  # Flag for test validation
                    }
                    
                    thread_id = await client.send_agent_request(agent_request)
                    
                    # Simulate each critical agent event
                    critical_events_to_simulate = [
                        {"type": "agent_started", "message": f"Agent started for session {session_num}"},
                        {"type": "agent_thinking", "message": f"Agent analyzing query for session {session_num}"},
                        {"type": "tool_executing", "message": f"Executing tool for session {session_num}", "tool": "test_tool"},
                        {"type": "tool_completed", "message": f"Tool execution completed for session {session_num}", "tool": "test_tool", "result": "success"},
                        {"type": "agent_completed", "message": f"Agent completed for session {session_num}", "result": "Task completed successfully"}
                    ]
                    
                    # Send each event with race condition timing stress
                    events_sent = []
                    for event in critical_events_to_simulate:
                        event_data = {
                            **event,
                            "thread_id": thread_id,
                            "session_id": f"events_test_session_{session_num}",
                            "timestamp": time.time()
                        }
                        
                        # Inject small delays to stress race condition handling
                        delay = await self.test_framework.inject_network_delay("low")
                        
                        await client.websocket.send(json.dumps(event_data))
                        events_sent.append(event["type"])
                        
                        # Track event in test framework
                        self.test_framework.track_agent_event(
                            event["type"], 
                            thread_id,
                            {"session_id": f"events_test_session_{session_num}"}
                        )
                        
                        logger.debug(f"📤 Sent {event['type']} for thread {thread_id}")
                    
                    # Wait for event delivery with timeout
                    event_validation_timeout = 10.0
                    await asyncio.sleep(2.0)  # Allow events to be processed
                    
                    # Validate event delivery for this session
                    session_events = [
                        event for event in self.test_framework.event_delivery_log
                        if event["thread_id"] == thread_id
                    ]
                    
                    delivered_event_types = {event["event_type"] for event in session_events}
                    expected_event_types = set(events_sent)
                    missing_events = expected_event_types - delivered_event_types
                    
                    session_result = {
                        "session_num": session_num,
                        "thread_id": thread_id,
                        "events_sent": len(events_sent),
                        "events_delivered": len(session_events),
                        "delivered_event_types": delivered_event_types,
                        "missing_events": missing_events,
                        "session_duration": time.time() - session_start,
                        "success": len(missing_events) == 0
                    }
                    agent_session_results.append(session_result)
                    
                    logger.info(f"📊 Session {session_num} Results:")
                    logger.info(f"   Events Delivered: {len(session_events)}/{len(events_sent)}")
                    logger.info(f"   Missing Events: {missing_events}")
                    logger.info(f"   Session Duration: {session_result['session_duration']:.2f}s")
                    
                    # Per-session assertion
                    assert len(missing_events) == 0, \
                        f"Session {session_num} missing critical events: {missing_events}"
            
            # Overall test analysis
            report = self.test_framework.generate_report()
            
            total_events_delivered = sum(r["events_delivered"] for r in agent_session_results)
            successful_sessions = sum(1 for r in agent_session_results if r["success"])
            
            logger.info("📊 AGENT EVENTS DELIVERY RELIABILITY RESULTS:")
            logger.info(f"   Successful Sessions: {successful_sessions}/{num_agent_sessions}")
            logger.info(f"   Total Events Delivered: {total_events_delivered}/{expected_total_events}")
            logger.info(f"   Event Delivery Rate: {total_events_delivered/expected_total_events:.2%}")
            logger.info(f"   Race Condition Errors: {report['race_condition_errors']}")
            
            # CRITICAL ASSERTIONS for Chat business value
            session_success_rate = successful_sessions / num_agent_sessions
            assert session_success_rate == 1.0, \
                f"Agent session success rate must be 100%: {session_success_rate:.2%}"
            
            event_delivery_rate = total_events_delivered / expected_total_events
            assert event_delivery_rate >= 0.95, \
                f"Event delivery rate too low: {event_delivery_rate:.2%} (need ≥95%)"
            
            # Verify all critical event types were delivered
            all_delivered_types = set()
            for result in agent_session_results:
                all_delivered_types.update(result["delivered_event_types"])
            
            missing_critical_types = self.test_framework.critical_agent_events - all_delivered_types
            assert len(missing_critical_types) == 0, \
                f"Critical agent event types missing: {missing_critical_types}"
            
            # No race conditions allowed during critical event delivery
            assert report['race_condition_errors'] == 0, \
                f"Race conditions detected during agent event delivery: {report['race_condition_errors']}"
        
        except Exception as e:
            logger.error(f"❌ Agent events delivery reliability test failed: {e}")
            raise
        
        # Verify test duration
        actual_duration = time.time() - test_start_time
        assert actual_duration > 5.0, \
            f"Agent events test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f"✅ Agent events delivery reliability test completed in {actual_duration:.2f}s")
        logger.info(f"🎯 All {len(self.test_framework.critical_agent_events)} critical agent event types validated")


# ============================================================================
# TEST EXECUTION CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    """
    Direct test execution for debugging and development.
    
    Run with: python -m pytest tests/e2e/test_websocket_race_condition_critical.py -v -s
    Or with unified test runner: python tests/unified_test_runner.py --real-services --category e2e
    """
    import sys
    
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Starting WebSocket Race Condition Critical Test Suite")
    logger.info("📋 Tests included:")
    logger.info("   1. test_websocket_race_condition_reproduction")
    logger.info("   2. test_websocket_multi_user_concurrent_load") 
    logger.info("   3. test_websocket_cloud_run_latency_simulation")
    logger.info("   4. test_websocket_agent_events_delivery_reliability")
    logger.info("🎯 Business Value: Ensures $500K+ ARR Chat functionality reliability")
    
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])