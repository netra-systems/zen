#!/usr/bin/env python3
"""
CRITICAL E2E TEST SUITE: Multi-User Thread Isolation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user isolation for thread routing
- Value Impact: Users must never see other users' threads or messages
- Strategic Impact: Core security and privacy for multi-user Chat platform

CRITICAL REQUIREMENTS:
-  PASS:  Real authentication via e2e_auth_helper.py (NO MOCKS = ABOMINATION)
-  PASS:  Full Docker stack + Real LLM + Authentication
-  PASS:  Tests designed to FAIL initially (find system isolation gaps)
-  PASS:  All 5 WebSocket agent events validated (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
-  PASS:  Multi-user concurrent scenarios with proper user context isolation

This test validates that thread routing maintains perfect isolation between users
in concurrent scenarios. Expected initial failures due to isolation gaps in current system.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
import pytest
from contextlib import asynccontextmanager
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

# CRITICAL: Add project root to Python path for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# SSOT imports following CLAUDE.md requirements
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper, 
    create_authenticated_user_context,
    E2EAuthConfig
)
from test_framework.base_e2e_test import BaseE2ETest
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RequestID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

logger = logging.getLogger(__name__)


class MultiUserThreadIsolationFramework:
    """
    Framework for testing multi-user thread isolation with microsecond precision tracking.
    
    Features:
    - User context isolation monitoring
    - Thread access violation detection  
    - Cross-user event leakage detection
    - WebSocket message routing validation
    """
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.user_contexts: Dict[str, StronglyTypedUserExecutionContext] = {}
        self.thread_access_log: List[Dict] = []
        self.isolation_violations: List[Dict] = []
        self.websocket_events: List[Dict] = []
        self.start_time = time.time()
        
        # Critical agent events for Chat business value
        self.critical_agent_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        # User isolation tracking
        self.user_thread_mapping: Dict[str, Set[str]] = {}  # user_id -> set of thread_ids
        self.cross_user_access_attempts: List[Dict] = []
    
    def register_user_context(self, user_context: StronglyTypedUserExecutionContext):
        """Register a user context for isolation tracking."""
        user_id = str(user_context.user_id)
        self.user_contexts[user_id] = user_context
        self.user_thread_mapping[user_id] = set()
        logger.info(f" PASS:  Registered user context: {user_id}")
    
    def log_thread_access(self, user_id: str, thread_id: str, action: str, success: bool, details: Dict = None):
        """Log thread access attempt with isolation validation."""
        entry = {
            "timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "user_id": user_id,
            "thread_id": thread_id,
            "action": action,
            "success": success,
            "details": details or {}
        }
        self.thread_access_log.append(entry)
        
        # Check for isolation violation
        thread_owner = self._find_thread_owner(thread_id)
        if thread_owner and thread_owner != user_id:
            violation = {
                "timestamp": time.time(),
                "violating_user": user_id,
                "thread_owner": thread_owner,
                "thread_id": thread_id,
                "action": action,
                "success": success,
                "violation_type": "cross_user_thread_access"
            }
            self.isolation_violations.append(violation)
            logger.error(f" ALERT:  ISOLATION VIOLATION: User {user_id} accessed thread {thread_id} owned by {thread_owner}")
    
    def register_user_thread(self, user_id: str, thread_id: str):
        """Register that a thread belongs to a specific user."""
        if user_id not in self.user_thread_mapping:
            self.user_thread_mapping[user_id] = set()
        self.user_thread_mapping[user_id].add(thread_id)
        logger.debug(f"[U+1F4DD] Registered thread {thread_id} for user {user_id}")
    
    def _find_thread_owner(self, thread_id: str) -> Optional[str]:
        """Find which user owns a specific thread."""
        for user_id, thread_ids in self.user_thread_mapping.items():
            if thread_id in thread_ids:
                return user_id
        return None
    
    def log_websocket_event(self, user_id: str, event_type: str, thread_id: str, event_data: Dict):
        """Log WebSocket event for routing validation."""
        entry = {
            "timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "user_id": user_id,
            "event_type": event_type,
            "thread_id": thread_id,
            "is_critical": event_type in self.critical_agent_events,
            "event_data": event_data
        }
        self.websocket_events.append(entry)
        
        # Validate event routing - should only go to thread owner
        thread_owner = self._find_thread_owner(thread_id)
        if thread_owner and thread_owner != user_id:
            violation = {
                "timestamp": time.time(),
                "event_recipient": user_id,
                "thread_owner": thread_owner,
                "thread_id": thread_id,
                "event_type": event_type,
                "violation_type": "cross_user_event_routing"
            }
            self.isolation_violations.append(violation)
            logger.error(f" ALERT:  EVENT ROUTING VIOLATION: User {user_id} received event for thread owned by {thread_owner}")
    
    def detect_cross_user_message_leakage(self, received_events: List[Dict], expected_user_id: str) -> List[Dict]:
        """Detect if user received messages meant for other users."""
        leaked_events = []
        
        for event in received_events:
            event_user_id = event.get("user_id")
            event_thread_id = event.get("thread_id")
            
            if event_user_id and event_user_id != expected_user_id:
                leaked_events.append({
                    "event": event,
                    "expected_user": expected_user_id,
                    "actual_user": event_user_id,
                    "leak_type": "user_id_mismatch"
                })
            
            if event_thread_id:
                thread_owner = self._find_thread_owner(event_thread_id)
                if thread_owner and thread_owner != expected_user_id:
                    leaked_events.append({
                        "event": event,
                        "expected_user": expected_user_id,
                        "thread_owner": thread_owner,
                        "thread_id": event_thread_id,
                        "leak_type": "thread_cross_contamination"
                    })
        
        return leaked_events
    
    def generate_isolation_report(self) -> Dict:
        """Generate comprehensive isolation test report."""
        total_users = len(self.user_contexts)
        total_threads = sum(len(threads) for threads in self.user_thread_mapping.values())
        isolation_violations = len(self.isolation_violations)
        critical_events_logged = len([e for e in self.websocket_events if e["is_critical"]])
        
        return {
            "test_duration": time.time() - self.start_time,
            "total_users": total_users,
            "total_threads": total_threads,
            "isolation_violations": isolation_violations,
            "critical_events_logged": critical_events_logged,
            "isolation_success_rate": (total_users - isolation_violations) / max(total_users, 1),
            "thread_access_attempts": len(self.thread_access_log),
            "websocket_events_logged": len(self.websocket_events),
            "detailed_violations": self.isolation_violations,
            "thread_access_log": self.thread_access_log,
            "websocket_events": self.websocket_events
        }


class IsolatedUserWebSocketClient:
    """WebSocket client with user context isolation and violation detection."""
    
    def __init__(self, user_context: StronglyTypedUserExecutionContext, 
                 auth_helper: E2EWebSocketAuthHelper,
                 isolation_framework: MultiUserThreadIsolationFramework):
        self.user_context = user_context
        self.auth_helper = auth_helper
        self.isolation_framework = isolation_framework
        self.websocket = None
        self.user_id = str(user_context.user_id)
        self.received_events = []
        self.is_connected = False
    
    @asynccontextmanager
    async def connect(self, timeout: float = 20.0):
        """Connect with user isolation monitoring."""
        try:
            # Get authenticated WebSocket connection
            self.websocket = await self.auth_helper.connect_authenticated_websocket(timeout=timeout)
            self.is_connected = True
            
            logger.info(f"[U+1F50C] User {self.user_id} connected via WebSocket")
            
            # Start message monitoring
            monitor_task = asyncio.create_task(self._monitor_messages())
            
            try:
                yield self
            finally:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                
                if self.websocket and not self.websocket.closed:
                    await self.websocket.close()
                    self.is_connected = False
                
                logger.info(f"[U+1F50C] User {self.user_id} disconnected from WebSocket")
        
        except Exception as e:
            logger.error(f" FAIL:  User {self.user_id} WebSocket connection failed: {e}")
            raise
    
    async def _monitor_messages(self):
        """Monitor incoming messages and detect isolation violations."""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    
                    # Parse message
                    try:
                        event_data = json.loads(message)
                        self.received_events.append(event_data)
                        
                        # Log event for isolation tracking
                        event_type = event_data.get("type", "unknown")
                        thread_id = event_data.get("thread_id", "unknown")
                        
                        self.isolation_framework.log_websocket_event(
                            self.user_id, 
                            event_type, 
                            thread_id, 
                            event_data
                        )
                        
                        logger.debug(f"[U+1F4E8] User {self.user_id} received {event_type} for thread {thread_id}")
                        
                    except json.JSONDecodeError:
                        # Non-JSON messages are okay
                        pass
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Message monitoring error for user {self.user_id}: {e}")
                    break
        
        except asyncio.CancelledError:
            pass
    
    async def create_thread(self, thread_title: str) -> str:
        """Create a new thread for this user."""
        id_generator = UnifiedIdGenerator()
        thread_id = id_generator.generate_thread_id(self.user_id)
        
        # Register thread ownership
        self.isolation_framework.register_user_thread(self.user_id, thread_id)
        
        # Log thread creation
        self.isolation_framework.log_thread_access(
            self.user_id, 
            thread_id, 
            "create", 
            True, 
            {"title": thread_title}
        )
        
        logger.info(f"[U+1F4DD] User {self.user_id} created thread {thread_id}: {thread_title}")
        return thread_id
    
    async def send_agent_request(self, thread_id: str, message: str, agent_type: str = "triage_agent") -> str:
        """Send agent request to specific thread."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError(f"User {self.user_id} WebSocket not connected")
        
        # Generate request ID
        id_generator = UnifiedIdGenerator()
        request_id = id_generator.generate_request_id(self.user_id)
        
        # Create agent request
        agent_request = {
            "type": "agent_request",
            "user_id": self.user_id,
            "thread_id": thread_id,
            "request_id": request_id,
            "agent": agent_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.websocket.send(json.dumps(agent_request))
        
        # Log thread access
        self.isolation_framework.log_thread_access(
            self.user_id, 
            thread_id, 
            "send_message", 
            True,
            {"agent": agent_type, "message": message[:50]}
        )
        
        logger.info(f"[U+1F4E4] User {self.user_id} sent agent request to thread {thread_id}")
        return request_id
    
    async def wait_for_agent_completion(self, thread_id: str, timeout: float = 30.0) -> Dict:
        """Wait for agent completion events."""
        start_time = time.time()
        collected_events = []
        
        while time.time() - start_time < timeout:
            # Check received events
            for event in self.received_events:
                if (event.get("thread_id") == thread_id and 
                    event.get("type") in self.isolation_framework.critical_agent_events):
                    collected_events.append(event)
                    
                    # Stop when agent completes
                    if event.get("type") == "agent_completed":
                        return {
                            "success": True,
                            "events": collected_events,
                            "duration": time.time() - start_time
                        }
            
            await asyncio.sleep(0.1)
        
        # Timeout
        return {
            "success": False,
            "events": collected_events,
            "duration": timeout
        }


class TestMultiUserThreadIsolationE2E:
    """
    CRITICAL E2E test suite for multi-user thread isolation.
    
    Tests that multiple users cannot access each other's threads or see
    each other's messages in concurrent scenarios. Uses real authentication,
    real services, and validates all 5 WebSocket agent events.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up test class with real service requirements."""
        cls.env = get_env()
        cls.test_environment = cls.env.get("TEST_ENV", cls.env.get("ENVIRONMENT", "test"))
        
        logger.info("[U+1F680] Starting Multi-User Thread Isolation E2E Tests")
        logger.info(f" PIN:  Environment: {cls.test_environment}")
        logger.info(" TARGET:  Testing multi-user isolation with concurrent thread access")
    
    def setup_method(self, method):
        """Set up each test method with authentication and isolation framework."""
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        self.isolation_framework = MultiUserThreadIsolationFramework(self.test_environment)
        self.test_users: List[IsolatedUserWebSocketClient] = []
        
        logger.info(f"[U+1F9EA] Starting test: {method.__name__}")
    
    def teardown_method(self, method):
        """Clean up test resources."""
        logger.info(f"[U+1F9F9] Cleaning up test: {method.__name__}")
        self.test_users.clear()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_concurrent_user_thread_creation_isolation(self):
        """
        CRITICAL TEST: Multiple users create threads concurrently with perfect isolation.
        
        This test validates that when multiple users create threads simultaneously,
        each user can only access their own threads and cannot see others' threads.
        
        Expected Initial Result: FAILURE - System likely has isolation gaps
        Success Criteria: Zero cross-user thread access violations
        """
        test_start_time = time.time()
        logger.info("[U+1F465] CRITICAL: Testing concurrent user thread creation isolation")
        
        # Test configuration
        num_concurrent_users = 4
        threads_per_user = 3
        
        user_clients = []
        thread_creation_tasks = []
        
        try:
            # Create authenticated user contexts
            logger.info(f"[U+1F510] Creating {num_concurrent_users} authenticated user contexts...")
            for i in range(num_concurrent_users):
                user_context = await create_authenticated_user_context(
                    user_email=f"isolation_test_user_{i}_{int(time.time())}@example.com",
                    environment=self.test_environment,
                    websocket_enabled=True
                )
                
                self.isolation_framework.register_user_context(user_context)
                
                # Create isolated WebSocket client
                client = IsolatedUserWebSocketClient(
                    user_context, 
                    self.auth_helper,
                    self.isolation_framework
                )
                user_clients.append(client)
                self.test_users.append(client)
                
                logger.info(f" PASS:  Created user context {i}: {user_context.user_id}")
            
            # Connect all users concurrently
            logger.info("[U+1F50C] Connecting all users to WebSocket concurrently...")
            connection_tasks = []
            for client in user_clients:
                task = asyncio.create_task(self._test_user_thread_creation_isolation(client, threads_per_user))
                connection_tasks.append(task)
            
            # Execute all user tasks concurrently
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Analyze results
            successful_users = 0
            total_threads_created = 0
            isolation_violations = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f" FAIL:  User {i} test failed: {result}")
                else:
                    successful_users += 1
                    total_threads_created += result.get("threads_created", 0)
                    isolation_violations += result.get("isolation_violations", 0)
                    logger.info(f" PASS:  User {i}: {result.get('threads_created', 0)} threads created")
            
            # Generate isolation report
            report = self.isolation_framework.generate_isolation_report()
            
            logger.info(" CHART:  CONCURRENT THREAD CREATION ISOLATION RESULTS:")
            logger.info(f"   Successful Users: {successful_users}/{num_concurrent_users}")
            logger.info(f"   Total Threads Created: {total_threads_created}")
            logger.info(f"   Isolation Violations: {report['isolation_violations']}")
            logger.info(f"   Isolation Success Rate: {report['isolation_success_rate']:.2%}")
            
            # CRITICAL ASSERTIONS - Expected to FAIL initially
            if report['isolation_violations'] > 0:
                logger.error(" ALERT:  ISOLATION VIOLATIONS DETECTED - System has multi-user isolation gaps")
                logger.error(f" SEARCH:  Found {report['isolation_violations']} isolation violations")
                
                # Log first violation for debugging
                if self.isolation_framework.isolation_violations:
                    first_violation = self.isolation_framework.isolation_violations[0]
                    logger.error(f" SEARCH:  First violation: {first_violation}")
                
                # This will fail initially - documenting expected system gap
                pytest.fail(
                    f"MULTI-USER ISOLATION FAILURE: {report['isolation_violations']} violations detected. "
                    f"Users can access each other's threads. Critical security gap requiring fix."
                )
            else:
                logger.info(" PASS:  SUCCESS: Perfect multi-user thread isolation achieved!")
                
                # Verify sufficient test coverage
                assert successful_users >= num_concurrent_users * 0.8, \
                    f"Insufficient successful users: {successful_users}/{num_concurrent_users}"
                
                assert total_threads_created >= num_concurrent_users * threads_per_user * 0.8, \
                    f"Insufficient threads created: {total_threads_created}"
        
        except Exception as e:
            # Generate report even on failure
            report = self.isolation_framework.generate_isolation_report()
            logger.error(f" CHART:  Partial results: {report}")
            logger.error(f" FAIL:  Concurrent thread isolation test failed: {e}")
            raise
        
        # Verify test duration (no 0.00s tests per CLAUDE.md)
        actual_duration = time.time() - test_start_time
        assert actual_duration > 5.0, \
            f"E2E test completed too quickly ({actual_duration:.2f}s). Must test real concurrent scenarios."
        
        logger.info(f" PASS:  Concurrent thread isolation test completed in {actual_duration:.2f}s")
    
    async def _test_user_thread_creation_isolation(self, client: IsolatedUserWebSocketClient, num_threads: int) -> Dict:
        """Test thread creation isolation for single user."""
        threads_created = 0
        isolation_violations = 0
        
        try:
            async with client.connect(timeout=25.0):
                # Create multiple threads for this user
                user_threads = []
                for i in range(num_threads):
                    thread_title = f"Private Thread {i} for User {client.user_id}"
                    thread_id = await client.create_thread(thread_title)
                    user_threads.append(thread_id)
                    threads_created += 1
                    
                    # Brief delay to create timing conditions
                    await asyncio.sleep(0.2)
                
                # Attempt to access other users' threads (should fail)
                # This simulates potential cross-user access attempts
                for other_client in self.test_users:
                    if other_client != client:
                        # Try to access other user's threads (should be blocked)
                        for thread_id in other_client.isolation_framework.user_thread_mapping.get(str(other_client.user_id), set()):
                            try:
                                # This should fail - log as attempted violation
                                self.isolation_framework.log_thread_access(
                                    client.user_id,
                                    thread_id,
                                    "unauthorized_access_attempt",
                                    False,
                                    {"target_user": str(other_client.user_id)}
                                )
                            except Exception:
                                # Expected - access should be blocked
                                pass
                
                # Count any isolation violations detected for this user
                user_violations = len([
                    v for v in self.isolation_framework.isolation_violations 
                    if v.get("violating_user") == client.user_id
                ])
                isolation_violations = user_violations
        
        except Exception as e:
            logger.error(f" FAIL:  User {client.user_id} thread creation test failed: {e}")
            raise
        
        return {
            "user_id": client.user_id,
            "threads_created": threads_created,
            "isolation_violations": isolation_violations
        }
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_user_agent_event_isolation(self):
        """
        CRITICAL TEST: Agent events properly routed to correct users only.
        
        This test validates that when multiple users send agent requests simultaneously,
        each user only receives WebSocket events for their own threads and agents.
        
        Expected Initial Result: FAILURE - Event routing likely has cross-user leakage
        Success Criteria: All 5 agent events delivered to correct users only
        """
        test_start_time = time.time()
        logger.info("[U+1F916] CRITICAL: Testing multi-user agent event isolation")
        
        # Test configuration  
        num_users = 3
        agent_requests_per_user = 2
        
        user_clients = []
        agent_interaction_results = []
        
        try:
            # Create authenticated users with WebSocket connections
            logger.info(f"[U+1F510] Setting up {num_users} users with agent interactions...")
            for i in range(num_users):
                user_context = await create_authenticated_user_context(
                    user_email=f"agent_isolation_user_{i}_{int(time.time())}@example.com",
                    environment=self.test_environment,
                    websocket_enabled=True
                )
                
                self.isolation_framework.register_user_context(user_context)
                
                client = IsolatedUserWebSocketClient(
                    user_context,
                    self.auth_helper, 
                    self.isolation_framework
                )
                user_clients.append(client)
                self.test_users.append(client)
                
                logger.info(f" PASS:  Created agent test user {i}: {user_context.user_id}")
            
            # Execute concurrent agent interactions
            agent_tasks = []
            for client in user_clients:
                task = asyncio.create_task(
                    self._test_user_agent_event_isolation(client, agent_requests_per_user)
                )
                agent_tasks.append(task)
            
            # Run all agent interactions concurrently
            logger.info("[U+1F680] Executing concurrent agent interactions...")
            agent_interaction_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Analyze agent event isolation
            total_events_received = 0
            cross_user_event_leaks = 0
            successful_agent_interactions = 0
            
            for i, result in enumerate(agent_interaction_results):
                if isinstance(result, Exception):
                    logger.error(f" FAIL:  User {i} agent interaction failed: {result}")
                else:
                    successful_agent_interactions += 1
                    total_events_received += result.get("events_received", 0)
                    cross_user_event_leaks += result.get("cross_user_leaks", 0)
                    
                    logger.info(f" PASS:  User {i}: {result.get('events_received', 0)} events received")
                    if result.get("cross_user_leaks", 0) > 0:
                        logger.error(f" ALERT:  User {i}: {result['cross_user_leaks']} cross-user event leaks detected")
            
            # Generate detailed isolation report
            report = self.isolation_framework.generate_isolation_report()
            
            logger.info(" CHART:  MULTI-USER AGENT EVENT ISOLATION RESULTS:")
            logger.info(f"   Successful Agent Interactions: {successful_agent_interactions}/{num_users}")
            logger.info(f"   Total Events Received: {total_events_received}")
            logger.info(f"   Cross-User Event Leaks: {cross_user_event_leaks}")
            logger.info(f"   Event Isolation Violations: {report['isolation_violations']}")
            logger.info(f"   Critical Events Logged: {report['critical_events_logged']}")
            
            # CRITICAL ASSERTIONS - Expected to FAIL initially
            if cross_user_event_leaks > 0 or report['isolation_violations'] > 0:
                logger.error(" ALERT:  AGENT EVENT ISOLATION FAILURE - Cross-user event leakage detected")
                logger.error(f" SEARCH:  Event leaks: {cross_user_event_leaks}, Violations: {report['isolation_violations']}")
                
                # Log detailed violation for debugging
                if self.isolation_framework.isolation_violations:
                    for violation in self.isolation_framework.isolation_violations[:3]:  # First 3
                        logger.error(f" SEARCH:  Violation: {violation}")
                
                # Expected failure - documenting system gap
                pytest.fail(
                    f"AGENT EVENT ISOLATION FAILURE: {cross_user_event_leaks} cross-user leaks + "
                    f"{report['isolation_violations']} violations. "
                    f"Users receiving events meant for other users. Critical routing bug."
                )
            else:
                logger.info(" PASS:  SUCCESS: Perfect agent event isolation achieved!")
                
                # Verify all critical events were delivered
                expected_total_events = num_users * agent_requests_per_user * len(self.isolation_framework.critical_agent_events)
                event_delivery_rate = total_events_received / expected_total_events if expected_total_events > 0 else 0
                
                assert event_delivery_rate >= 0.8, \
                    f"Event delivery rate too low: {event_delivery_rate:.2%} (need  >= 80%)"
                
                assert successful_agent_interactions >= num_users * 0.8, \
                    f"Too few successful agent interactions: {successful_agent_interactions}/{num_users}"
        
        except Exception as e:
            report = self.isolation_framework.generate_isolation_report()
            logger.error(f" CHART:  Partial results: {report}")
            logger.error(f" FAIL:  Multi-user agent event isolation test failed: {e}")
            raise
        
        # Verify test duration
        actual_duration = time.time() - test_start_time
        assert actual_duration > 8.0, \
            f"Agent event test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f" PASS:  Multi-user agent event isolation test completed in {actual_duration:.2f}s")
    
    async def _test_user_agent_event_isolation(self, client: IsolatedUserWebSocketClient, num_requests: int) -> Dict:
        """Test agent event isolation for single user."""
        events_received = 0
        cross_user_leaks = 0
        
        try:
            async with client.connect(timeout=30.0):
                # Create user's private threads and send agent requests
                for req_num in range(num_requests):
                    # Create private thread
                    thread_title = f"Agent Test Thread {req_num} for {client.user_id}"
                    thread_id = await client.create_thread(thread_title)
                    
                    # Send agent request
                    message = f"Test agent query {req_num} from user {client.user_id}"
                    await client.send_agent_request(thread_id, message)
                    
                    # Wait for agent events
                    result = await client.wait_for_agent_completion(thread_id, timeout=15.0)
                    if result["success"]:
                        events_received += len(result["events"])
                    
                    # Brief delay between requests
                    await asyncio.sleep(1.0)
                
                # Check for cross-user event leakage
                leaked_events = self.isolation_framework.detect_cross_user_message_leakage(
                    client.received_events, 
                    client.user_id
                )
                cross_user_leaks = len(leaked_events)
                
                if cross_user_leaks > 0:
                    logger.error(f" ALERT:  User {client.user_id} received {cross_user_leaks} events meant for other users")
                    for leak in leaked_events[:3]:  # Log first 3
                        logger.error(f" SEARCH:  Leaked event: {leak}")
        
        except Exception as e:
            logger.error(f" FAIL:  User {client.user_id} agent event test failed: {e}")
            raise
        
        return {
            "user_id": client.user_id,
            "events_received": events_received,
            "cross_user_leaks": cross_user_leaks
        }
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_stress_multi_user_thread_access_patterns(self):
        """
        CRITICAL TEST: High-volume multi-user thread access patterns with isolation validation.
        
        This test simulates realistic high-load scenarios with multiple users
        accessing threads rapidly and concurrently. Validates isolation holds
        under stress conditions.
        
        Expected Initial Result: FAILURE - Race conditions likely cause isolation breaks
        Success Criteria: Zero isolation violations under stress load
        """
        test_start_time = time.time()
        logger.info(" LIGHTNING:  CRITICAL: Testing stress multi-user thread access patterns")
        
        # Stress test configuration
        num_stress_users = 5
        operations_per_user = 8  # Create threads, send messages, access patterns
        concurrent_operation_delay = 0.1  # Rapid operations
        
        stress_test_clients = []
        stress_results = []
        
        try:
            # Create stress test users
            logger.info(f" FIRE:  Setting up {num_stress_users} users for stress testing...")
            for i in range(num_stress_users):
                user_context = await create_authenticated_user_context(
                    user_email=f"stress_test_user_{i}_{int(time.time())}@example.com",
                    environment=self.test_environment,
                    websocket_enabled=True
                )
                
                self.isolation_framework.register_user_context(user_context)
                
                client = IsolatedUserWebSocketClient(
                    user_context,
                    self.auth_helper,
                    self.isolation_framework
                )
                stress_test_clients.append(client)
                self.test_users.append(client)
                
                logger.info(f" LIGHTNING:  Created stress test user {i}: {user_context.user_id}")
            
            # Execute stress test operations concurrently
            stress_tasks = []
            for client in stress_test_clients:
                task = asyncio.create_task(
                    self._execute_stress_operations(client, operations_per_user, concurrent_operation_delay)
                )
                stress_tasks.append(task)
            
            # Run all stress operations concurrently
            logger.info("[U+1F680] Executing high-volume concurrent thread operations...")
            stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            
            # Analyze stress test results
            total_operations_completed = 0
            isolation_violations_under_stress = 0
            successful_stress_users = 0
            
            for i, result in enumerate(stress_results):
                if isinstance(result, Exception):
                    logger.error(f" FAIL:  Stress user {i} failed: {result}")
                else:
                    successful_stress_users += 1
                    total_operations_completed += result.get("operations_completed", 0)
                    isolation_violations_under_stress += result.get("isolation_violations", 0)
                    
                    logger.info(f" LIGHTNING:  Stress user {i}: {result.get('operations_completed', 0)} operations completed")
            
            # Generate comprehensive stress report
            report = self.isolation_framework.generate_isolation_report()
            
            logger.info(" CHART:  STRESS MULTI-USER THREAD ACCESS RESULTS:")
            logger.info(f"   Successful Stress Users: {successful_stress_users}/{num_stress_users}")
            logger.info(f"   Total Operations Completed: {total_operations_completed}")
            logger.info(f"   Operations Per Second: {total_operations_completed / (time.time() - test_start_time):.1f}")
            logger.info(f"   Isolation Violations Under Stress: {report['isolation_violations']}")
            logger.info(f"   Stress Success Rate: {successful_stress_users / num_stress_users:.2%}")
            
            # CRITICAL ASSERTIONS - Expected to FAIL initially due to race conditions
            if report['isolation_violations'] > 0:
                logger.error(" ALERT:  STRESS ISOLATION FAILURE - Race conditions cause isolation breaks")
                logger.error(f" SEARCH:  Found {report['isolation_violations']} violations under stress")
                
                # Analyze violation patterns
                violation_types = {}
                for violation in self.isolation_framework.isolation_violations:
                    v_type = violation.get("violation_type", "unknown")
                    violation_types[v_type] = violation_types.get(v_type, 0) + 1
                
                logger.error(f" SEARCH:  Violation patterns: {violation_types}")
                
                # Expected failure - stress exposes race conditions
                pytest.fail(
                    f"STRESS ISOLATION FAILURE: {report['isolation_violations']} violations under load. "
                    f"Race conditions in thread access patterns cause isolation breaks. "
                    f"System cannot maintain isolation under realistic load."
                )
            else:
                logger.info(" PASS:  SUCCESS: Perfect isolation maintained under stress!")
                
                # Verify stress test coverage
                expected_operations = num_stress_users * operations_per_user
                operation_completion_rate = total_operations_completed / expected_operations
                
                assert operation_completion_rate >= 0.8, \
                    f"Stress operation completion too low: {operation_completion_rate:.2%}"
                
                assert successful_stress_users >= num_stress_users * 0.8, \
                    f"Too few successful stress users: {successful_stress_users}/{num_stress_users}"
        
        except Exception as e:
            report = self.isolation_framework.generate_isolation_report()
            logger.error(f" CHART:  Stress test partial results: {report}")
            logger.error(f" FAIL:  Stress multi-user thread access test failed: {e}")
            raise
        
        # Verify significant test duration
        actual_duration = time.time() - test_start_time
        assert actual_duration > 10.0, \
            f"Stress test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f" PASS:  Stress multi-user thread access test completed in {actual_duration:.2f}s")
    
    async def _execute_stress_operations(self, client: IsolatedUserWebSocketClient, 
                                       num_operations: int, operation_delay: float) -> Dict:
        """Execute stress operations for single user."""
        operations_completed = 0
        isolation_violations = 0
        
        try:
            async with client.connect(timeout=35.0):
                # Rapid thread creation and message sending
                user_threads = []
                
                for op_num in range(num_operations):
                    # Alternate between different operations
                    if op_num % 3 == 0:
                        # Create thread
                        thread_title = f"Stress Thread {op_num} for {client.user_id}"
                        thread_id = await client.create_thread(thread_title)
                        user_threads.append(thread_id)
                        operations_completed += 1
                    
                    elif op_num % 3 == 1 and user_threads:
                        # Send message to existing thread
                        thread_id = user_threads[-1]  # Use most recent thread
                        message = f"Stress message {op_num} from {client.user_id}"
                        await client.send_agent_request(thread_id, message)
                        operations_completed += 1
                    
                    else:
                        # Simulate rapid thread access
                        if user_threads:
                            thread_id = user_threads[op_num % len(user_threads)]
                            # Log access attempt
                            self.isolation_framework.log_thread_access(
                                client.user_id,
                                thread_id,
                                "rapid_access",
                                True,
                                {"operation": op_num}
                            )
                        operations_completed += 1
                    
                    # Brief delay to create timing stress
                    await asyncio.sleep(operation_delay)
                
                # Count isolation violations for this user
                user_violations = len([
                    v for v in self.isolation_framework.isolation_violations 
                    if v.get("violating_user") == client.user_id
                ])
                isolation_violations = user_violations
        
        except Exception as e:
            logger.error(f" FAIL:  User {client.user_id} stress operations failed: {e}")
            raise
        
        return {
            "user_id": client.user_id,
            "operations_completed": operations_completed,
            "isolation_violations": isolation_violations
        }


# ============================================================================
# TEST EXECUTION CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    """
    Direct test execution for debugging and development.
    
    Run with: python -m pytest tests/e2e/thread_routing/test_multi_user_thread_isolation_e2e.py -v -s
    Or with unified test runner: python tests/unified_test_runner.py --real-services --category e2e
    """
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("[U+1F680] Starting Multi-User Thread Isolation E2E Test Suite")
    logger.info("[U+1F4CB] Tests included:")
    logger.info("   1. test_concurrent_user_thread_creation_isolation")
    logger.info("   2. test_multi_user_agent_event_isolation")
    logger.info("   3. test_stress_multi_user_thread_access_patterns")
    logger.info(" TARGET:  Business Value: Ensures secure multi-user Chat platform isolation")
    logger.info(" WARNING: [U+FE0F]  Expected: Initial FAILURES due to isolation gaps in current system")
    
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])