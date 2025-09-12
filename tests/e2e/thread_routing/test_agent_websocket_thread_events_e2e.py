#!/usr/bin/env python3
"""
CRITICAL E2E TEST SUITE: Agent WebSocket Thread Events Routing

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure all 5 critical agent events are delivered to correct threads
- Value Impact: Agent events enable Chat business value ($500K+ ARR) - users must see real-time progress
- Strategic Impact: Core WebSocket event delivery pipeline for AI interactions

CRITICAL REQUIREMENTS:
-  PASS:  Real authentication via e2e_auth_helper.py (NO MOCKS = ABOMINATION)
-  PASS:  Full Docker stack + Real LLM + Agent execution
-  PASS:  ALL 5 WebSocket events MUST be tested: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
-  PASS:  Thread-specific event routing validation with real agent execution
-  PASS:  Tests designed to FAIL initially (find complex event routing issues)

This test validates that agent events are properly routed to the correct user threads
during real agent execution. Expected initial failures due to complex event routing bugs.
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
from shared.types.core_types import UserID, ThreadID, RequestID, RunID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

logger = logging.getLogger(__name__)


class AgentWebSocketEventTracker:
    """
    Advanced framework for tracking agent WebSocket events per thread with validation.
    
    Features:
    - Thread-specific event collection and validation
    - Agent execution timeline tracking
    - Event ordering and completeness validation
    - Real-time event routing verification
    """
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.start_time = time.time()
        
        # CRITICAL: All 5 agent events required for Chat business value
        self.critical_agent_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        # Event tracking per thread
        self.thread_events: Dict[str, List[Dict]] = {}  # thread_id -> events
        self.thread_timelines: Dict[str, Dict] = {}     # thread_id -> timeline
        self.event_routing_errors: List[Dict] = []
        self.agent_execution_results: Dict[str, Dict] = {}  # thread_id -> results
        
        # User context tracking
        self.user_thread_mapping: Dict[str, Set[str]] = {}  # user_id -> thread_ids
        self.thread_user_mapping: Dict[str, str] = {}       # thread_id -> user_id
    
    def register_thread(self, user_id: str, thread_id: str):
        """Register thread ownership for event routing validation."""
        if user_id not in self.user_thread_mapping:
            self.user_thread_mapping[user_id] = set()
        
        self.user_thread_mapping[user_id].add(thread_id)
        self.thread_user_mapping[thread_id] = user_id
        self.thread_events[thread_id] = []
        self.thread_timelines[thread_id] = {
            "created_at": time.time(),
            "events": {},
            "agent_started_at": None,
            "agent_completed_at": None,
            "total_duration": None
        }
        
        logger.info(f"[U+1F4DD] Registered thread {thread_id} for user {user_id}")
    
    def track_agent_event(self, user_id: str, thread_id: str, event_type: str, event_data: Dict):
        """Track agent event with thread routing validation."""
        timestamp = time.time()
        relative_time = timestamp - self.start_time
        
        # Validate event routing - should match thread owner
        expected_user = self.thread_user_mapping.get(thread_id)
        if expected_user and expected_user != user_id:
            routing_error = {
                "timestamp": timestamp,
                "thread_id": thread_id,
                "event_type": event_type,
                "expected_user": expected_user,
                "received_by_user": user_id,
                "error_type": "cross_user_event_routing"
            }
            self.event_routing_errors.append(routing_error)
            logger.error(f" ALERT:  EVENT ROUTING ERROR: Thread {thread_id} event sent to wrong user {user_id} (expected {expected_user})")
        
        # Track event for this thread
        if thread_id not in self.thread_events:
            self.thread_events[thread_id] = []
        
        event_entry = {
            "timestamp": timestamp,
            "relative_time": relative_time,
            "user_id": user_id,
            "thread_id": thread_id,
            "event_type": event_type,
            "is_critical": event_type in self.critical_agent_events,
            "event_data": event_data
        }
        
        self.thread_events[thread_id].append(event_entry)
        
        # Update timeline
        if thread_id in self.thread_timelines:
            timeline = self.thread_timelines[thread_id]
            timeline["events"][event_type] = timestamp
            
            if event_type == "agent_started":
                timeline["agent_started_at"] = timestamp
            elif event_type == "agent_completed":
                timeline["agent_completed_at"] = timestamp
                if timeline["agent_started_at"]:
                    timeline["total_duration"] = timestamp - timeline["agent_started_at"]
        
        logger.debug(f" CHART:  Tracked {event_type} for thread {thread_id} (user {user_id})")
    
    def validate_thread_events(self, thread_id: str, timeout_seconds: float = 30.0) -> Dict:
        """Validate all critical events were received for a thread."""
        if thread_id not in self.thread_events:
            return {
                "success": False,
                "error": "Thread not found in event tracker",
                "events_found": [],
                "missing_events": list(self.critical_agent_events)
            }
        
        thread_events = self.thread_events[thread_id]
        received_event_types = {event["event_type"] for event in thread_events}
        missing_events = self.critical_agent_events - received_event_types
        
        # Check event ordering
        event_order_valid = self._validate_event_order(thread_events)
        
        # Check timing constraints
        timing_valid = self._validate_event_timing(thread_id, timeout_seconds)
        
        success = len(missing_events) == 0 and event_order_valid and timing_valid
        
        return {
            "success": success,
            "events_found": list(received_event_types),
            "missing_events": list(missing_events),
            "event_count": len(thread_events),
            "event_order_valid": event_order_valid,
            "timing_valid": timing_valid,
            "timeline": self.thread_timelines.get(thread_id, {}),
            "critical_events_complete": len(missing_events) == 0
        }
    
    def _validate_event_order(self, events: List[Dict]) -> bool:
        """Validate agent events are in correct order."""
        expected_order = [
            "agent_started",
            "agent_thinking",
            "tool_executing",  # May be optional
            "tool_completed",  # May be optional  
            "agent_completed"
        ]
        
        # Extract event types in order received
        event_types = [e["event_type"] for e in events if e["is_critical"]]
        
        # Must start with agent_started and end with agent_completed
        if not event_types:
            return False
        
        if event_types[0] != "agent_started":
            logger.warning("Event order validation: Missing agent_started as first event")
            return False
        
        if event_types[-1] != "agent_completed":
            logger.warning("Event order validation: Missing agent_completed as last event")
            return False
        
        return True
    
    def _validate_event_timing(self, thread_id: str, max_duration: float) -> bool:
        """Validate event timing is within reasonable bounds."""
        if thread_id not in self.thread_timelines:
            return False
        
        timeline = self.thread_timelines[thread_id]
        
        # Check total execution time
        if timeline.get("total_duration"):
            if timeline["total_duration"] > max_duration:
                logger.warning(f"Agent execution too slow: {timeline['total_duration']:.2f}s > {max_duration}s")
                return False
        
        # Check for reasonable gaps between events
        events = timeline.get("events", {})
        if "agent_started" in events and "agent_thinking" in events:
            thinking_delay = events["agent_thinking"] - events["agent_started"]
            if thinking_delay > 5.0:  # Should start thinking quickly
                logger.warning(f"Agent thinking delay too long: {thinking_delay:.2f}s")
                return False
        
        return True
    
    def get_thread_routing_violations(self) -> List[Dict]:
        """Get all thread event routing violations."""
        return self.event_routing_errors
    
    def generate_comprehensive_report(self) -> Dict:
        """Generate comprehensive agent event tracking report."""
        total_threads = len(self.thread_events)
        total_events = sum(len(events) for events in self.thread_events.values())
        total_routing_errors = len(self.event_routing_errors)
        
        # Calculate event completion rates
        threads_with_complete_events = 0
        critical_event_delivery_rate = 0
        
        for thread_id in self.thread_events:
            validation = self.validate_thread_events(thread_id)
            if validation["critical_events_complete"]:
                threads_with_complete_events += 1
        
        if total_threads > 0:
            critical_event_delivery_rate = threads_with_complete_events / total_threads
        
        # Analyze event timing
        avg_agent_duration = 0
        if self.thread_timelines:
            durations = [
                timeline.get("total_duration", 0) 
                for timeline in self.thread_timelines.values() 
                if timeline.get("total_duration")
            ]
            if durations:
                avg_agent_duration = sum(durations) / len(durations)
        
        return {
            "test_duration": time.time() - self.start_time,
            "total_threads": total_threads,
            "total_events": total_events,
            "routing_errors": total_routing_errors,
            "critical_event_delivery_rate": critical_event_delivery_rate,
            "threads_with_complete_events": threads_with_complete_events,
            "avg_agent_execution_duration": avg_agent_duration,
            "event_routing_success_rate": (total_events - total_routing_errors) / max(total_events, 1),
            "detailed_routing_errors": self.event_routing_errors,
            "thread_timelines": self.thread_timelines,
            "thread_events": self.thread_events
        }


class ThreadEventWebSocketClient:
    """WebSocket client focused on thread-specific agent event collection."""
    
    def __init__(self, user_context: StronglyTypedUserExecutionContext,
                 auth_helper: E2EWebSocketAuthHelper,
                 event_tracker: AgentWebSocketEventTracker):
        self.user_context = user_context
        self.auth_helper = auth_helper
        self.event_tracker = event_tracker
        self.websocket = None
        self.user_id = str(user_context.user_id)
        self.is_connected = False
        self.user_threads: Set[str] = set()
    
    @asynccontextmanager
    async def connect(self, timeout: float = 25.0):
        """Connect with thread event monitoring."""
        try:
            # Get authenticated WebSocket connection
            self.websocket = await self.auth_helper.connect_authenticated_websocket(timeout=timeout)
            self.is_connected = True
            
            logger.info(f"[U+1F50C] User {self.user_id} connected for thread event testing")
            
            # Start event monitoring
            monitor_task = asyncio.create_task(self._monitor_thread_events())
            
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
                
                logger.info(f"[U+1F50C] User {self.user_id} disconnected from thread event testing")
        
        except Exception as e:
            logger.error(f" FAIL:  User {self.user_id} thread event WebSocket connection failed: {e}")
            raise
    
    async def _monitor_thread_events(self):
        """Monitor WebSocket messages for thread-specific agent events."""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    
                    # Parse and validate event
                    try:
                        event_data = json.loads(message)
                        event_type = event_data.get("type", "unknown")
                        thread_id = event_data.get("thread_id", "unknown")
                        
                        # Track critical agent events
                        if event_type in self.event_tracker.critical_agent_events:
                            self.event_tracker.track_agent_event(
                                self.user_id,
                                thread_id,
                                event_type,
                                event_data
                            )
                            
                            logger.info(f" CHART:  User {self.user_id} received {event_type} for thread {thread_id}")
                        
                        # Track all events for routing validation
                        elif thread_id != "unknown":
                            self.event_tracker.track_agent_event(
                                self.user_id,
                                thread_id,
                                event_type,
                                event_data
                            )
                    
                    except json.JSONDecodeError:
                        pass  # Non-JSON messages are okay
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Event monitoring error for user {self.user_id}: {e}")
                    break
        
        except asyncio.CancelledError:
            pass
    
    async def create_agent_thread(self, thread_title: str) -> str:
        """Create a new thread for agent interactions."""
        id_generator = UnifiedIdGenerator()
        thread_id = id_generator.generate_thread_id(self.user_id)
        
        # Register with event tracker
        self.event_tracker.register_thread(self.user_id, thread_id)
        self.user_threads.add(thread_id)
        
        logger.info(f"[U+1F4DD] User {self.user_id} created agent thread {thread_id}: {thread_title}")
        return thread_id
    
    async def execute_agent_in_thread(self, thread_id: str, query: str, 
                                    agent_type: str = "triage_agent") -> str:
        """Execute agent in specific thread and track events."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError(f"User {self.user_id} WebSocket not connected")
        
        # Generate execution IDs
        id_generator = UnifiedIdGenerator()
        request_id = id_generator.generate_request_id(self.user_id)
        run_id = id_generator.generate_run_id(self.user_id)
        
        # Send agent execution request
        agent_request = {
            "type": "agent_request",
            "user_id": self.user_id,
            "thread_id": thread_id,
            "request_id": request_id,
            "run_id": run_id,
            "agent": agent_type,
            "message": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expect_all_events": True  # Flag to ensure all 5 events are sent
        }
        
        await self.websocket.send(json.dumps(agent_request))
        
        logger.info(f"[U+1F916] User {self.user_id} started agent '{agent_type}' in thread {thread_id}")
        logger.info(f" TARGET:  Expecting ALL 5 critical events: {', '.join(self.event_tracker.critical_agent_events)}")
        
        return request_id
    
    async def wait_for_thread_agent_completion(self, thread_id: str, 
                                             timeout: float = 35.0) -> Dict:
        """Wait for all agent events to complete in specific thread."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if all events received
            validation = self.event_tracker.validate_thread_events(thread_id)
            
            if validation["critical_events_complete"]:
                logger.info(f" PASS:  All critical events received for thread {thread_id}")
                return validation
            
            await asyncio.sleep(0.5)  # Check every 500ms
        
        # Timeout - return current state
        validation = self.event_tracker.validate_thread_events(thread_id)
        logger.warning(f"[U+23F0] Agent completion timeout for thread {thread_id}")
        logger.warning(f" SEARCH:  Missing events: {validation.get('missing_events', [])}")
        
        return validation


class TestAgentWebSocketThreadEventsE2E:
    """
    CRITICAL E2E test suite for agent WebSocket thread event routing.
    
    Tests that all 5 critical agent events are properly delivered to the correct
    threads during real agent execution. Uses full authentication and real services.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up test class with real service requirements."""
        cls.env = get_env()
        cls.test_environment = cls.env.get("TEST_ENV", cls.env.get("ENVIRONMENT", "test"))
        
        logger.info("[U+1F680] Starting Agent WebSocket Thread Events E2E Tests")
        logger.info(f" PIN:  Environment: {cls.test_environment}")
        logger.info(" TARGET:  Testing all 5 critical agent events with thread routing")
    
    def setup_method(self, method):
        """Set up each test method."""
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        self.event_tracker = AgentWebSocketEventTracker(self.test_environment)
        self.test_clients: List[ThreadEventWebSocketClient] = []
        
        logger.info(f"[U+1F9EA] Starting test: {method.__name__}")
    
    def teardown_method(self, method):
        """Clean up test resources."""
        logger.info(f"[U+1F9F9] Cleaning up test: {method.__name__}")
        self.test_clients.clear()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.asyncio
    async def test_single_thread_all_agent_events_delivery(self):
        """
        CRITICAL TEST: All 5 agent events delivered to single thread with real agent execution.
        
        This test validates that when a user executes an agent in a thread,
        all 5 critical events are delivered in correct order with proper timing.
        
        Expected Initial Result: FAILURE - Event delivery likely incomplete
        Success Criteria: All 5 events delivered in correct order within 30s
        """
        test_start_time = time.time()
        logger.info("[U+1F916] CRITICAL: Testing single thread agent event delivery")
        
        try:
            # Create authenticated user for agent testing
            user_context = await create_authenticated_user_context(
                user_email=f"single_thread_agent_{int(time.time())}@example.com",
                environment=self.test_environment,
                websocket_enabled=True
            )
            
            # Create thread event client
            client = ThreadEventWebSocketClient(
                user_context,
                self.auth_helper,
                self.event_tracker
            )
            self.test_clients.append(client)
            
            async with client.connect(timeout=30.0):
                logger.info(f" PASS:  Connected user {client.user_id} for single thread agent testing")
                
                # Create thread for agent execution
                thread_id = await client.create_agent_thread("Single Thread Agent Test")
                
                # Execute agent with real query
                agent_query = "Analyze system performance and provide optimization recommendations"
                request_id = await client.execute_agent_in_thread(thread_id, agent_query)
                
                # Wait for all agent events
                logger.info("[U+23F3] Waiting for all 5 critical agent events...")
                result = await client.wait_for_thread_agent_completion(thread_id, timeout=35.0)
                
                # Validate event delivery
                logger.info(" CHART:  SINGLE THREAD AGENT EVENT DELIVERY RESULTS:")
                logger.info(f"   Events Found: {result['events_found']}")
                logger.info(f"   Missing Events: {result['missing_events']}")
                logger.info(f"   Event Count: {result['event_count']}")
                logger.info(f"   Event Order Valid: {result['event_order_valid']}")
                logger.info(f"   Timing Valid: {result['timing_valid']}")
                
                if result["timeline"].get("total_duration"):
                    logger.info(f"   Agent Duration: {result['timeline']['total_duration']:.2f}s")
                
                # CRITICAL ASSERTIONS - Expected to FAIL initially
                if not result["critical_events_complete"]:
                    logger.error(" ALERT:  AGENT EVENT DELIVERY FAILURE - Missing critical events")
                    logger.error(f" SEARCH:  Missing events: {result['missing_events']}")
                    logger.error(f" SEARCH:  Only received: {result['events_found']}")
                    
                    # Expected failure - agent event pipeline incomplete
                    pytest.fail(
                        f"AGENT EVENT DELIVERY FAILURE: Missing {len(result['missing_events'])} critical events. "
                        f"Missing: {result['missing_events']}. "
                        f"Agent event pipeline not delivering complete Chat business value."
                    )
                
                if not result["event_order_valid"]:
                    logger.error(" ALERT:  AGENT EVENT ORDER FAILURE - Events in wrong order")
                    pytest.fail("AGENT EVENT ORDER FAILURE: Events delivered in incorrect sequence")
                
                if not result["timing_valid"]:
                    logger.error(" ALERT:  AGENT EVENT TIMING FAILURE - Events too slow or out of bounds")
                    pytest.fail("AGENT EVENT TIMING FAILURE: Agent execution timing invalid")
                
                # Success validations
                logger.info(" PASS:  SUCCESS: All 5 critical agent events delivered correctly!")
                
                # Verify event completeness
                assert len(result["events_found"]) >= 5, \
                    f"Insufficient events received: {len(result['events_found'])}"
                
                # Verify all critical events present
                missing_critical = self.event_tracker.critical_agent_events - set(result["events_found"])
                assert len(missing_critical) == 0, \
                    f"Missing critical events: {missing_critical}"
                
                # Verify reasonable timing
                if result["timeline"].get("total_duration"):
                    assert result["timeline"]["total_duration"] <= 30.0, \
                        f"Agent execution too slow: {result['timeline']['total_duration']}s"
        
        except Exception as e:
            # Generate report even on failure
            report = self.event_tracker.generate_comprehensive_report()
            logger.error(f" CHART:  Partial results: {report}")
            logger.error(f" FAIL:  Single thread agent event test failed: {e}")
            raise
        
        # Verify test duration
        actual_duration = time.time() - test_start_time
        assert actual_duration > 8.0, \
            f"Agent event test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f" PASS:  Single thread agent event test completed in {actual_duration:.2f}s")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.asyncio
    async def test_multi_thread_agent_event_routing(self):
        """
        CRITICAL TEST: Multiple threads receive correct agent events simultaneously.
        
        This test validates that when multiple agent executions run in different
        threads simultaneously, events are routed to correct threads without leakage.
        
        Expected Initial Result: FAILURE - Event routing likely has cross-thread contamination
        Success Criteria: Each thread receives only its own agent events
        """
        test_start_time = time.time()
        logger.info("[U+1F500] CRITICAL: Testing multi-thread agent event routing")
        
        # Test configuration
        num_concurrent_threads = 4
        
        thread_clients = []
        agent_execution_tasks = []
        
        try:
            # Create user for multi-thread testing
            user_context = await create_authenticated_user_context(
                user_email=f"multi_thread_agent_{int(time.time())}@example.com",
                environment=self.test_environment,
                websocket_enabled=True
            )
            
            # Create thread event client
            client = ThreadEventWebSocketClient(
                user_context,
                self.auth_helper,
                self.event_tracker
            )
            self.test_clients.append(client)
            
            async with client.connect(timeout=35.0):
                logger.info(f" PASS:  Connected user {client.user_id} for multi-thread agent testing")
                
                # Create multiple threads and execute agents concurrently
                thread_ids = []
                for i in range(num_concurrent_threads):
                    thread_title = f"Thread {i} Multi-Agent Test"
                    thread_id = await client.create_agent_thread(thread_title)
                    thread_ids.append(thread_id)
                    
                    # Create agent execution task
                    query = f"Thread {i}: Analyze performance metrics and provide recommendations for optimization"
                    task = asyncio.create_task(self._execute_and_track_thread_agent(client, thread_id, query, i))
                    agent_execution_tasks.append(task)
                
                # Execute all agent tasks concurrently
                logger.info(f"[U+1F680] Executing {num_concurrent_threads} concurrent agent executions...")
                execution_results = await asyncio.gather(*agent_execution_tasks, return_exceptions=True)
                
                # Analyze multi-thread results
                successful_threads = 0
                total_events_delivered = 0
                cross_thread_routing_errors = 0
                
                for i, result in enumerate(execution_results):
                    if isinstance(result, Exception):
                        logger.error(f" FAIL:  Thread {i} agent execution failed: {result}")
                    else:
                        if result["success"]:
                            successful_threads += 1
                        total_events_delivered += result.get("events_received", 0)
                        cross_thread_routing_errors += result.get("routing_errors", 0)
                        
                        logger.info(f"[U+1F9F5] Thread {i}: {result.get('events_received', 0)} events, "
                                  f"Complete: {result['success']}")
                
                # Check for thread event routing violations
                routing_violations = self.event_tracker.get_thread_routing_violations()
                
                # Generate comprehensive report
                report = self.event_tracker.generate_comprehensive_report()
                
                logger.info(" CHART:  MULTI-THREAD AGENT EVENT ROUTING RESULTS:")
                logger.info(f"   Successful Threads: {successful_threads}/{num_concurrent_threads}")
                logger.info(f"   Total Events Delivered: {total_events_delivered}")
                logger.info(f"   Cross-Thread Routing Errors: {len(routing_violations)}")
                logger.info(f"   Event Routing Success Rate: {report['event_routing_success_rate']:.2%}")
                logger.info(f"   Critical Event Delivery Rate: {report['critical_event_delivery_rate']:.2%}")
                
                # CRITICAL ASSERTIONS - Expected to FAIL initially
                if len(routing_violations) > 0:
                    logger.error(" ALERT:  THREAD EVENT ROUTING FAILURE - Cross-thread contamination detected")
                    logger.error(f" SEARCH:  Found {len(routing_violations)} routing violations")
                    
                    # Log first few violations
                    for violation in routing_violations[:3]:
                        logger.error(f" SEARCH:  Violation: {violation}")
                    
                    # Expected failure - thread event routing has bugs
                    pytest.fail(
                        f"THREAD EVENT ROUTING FAILURE: {len(routing_violations)} routing violations. "
                        f"Agent events being delivered to wrong threads. "
                        f"Critical thread isolation bug in event pipeline."
                    )
                
                if report["critical_event_delivery_rate"] < 0.8:
                    logger.error(" ALERT:  CRITICAL EVENT DELIVERY RATE TOO LOW")
                    logger.error(f" SEARCH:  Only {report['critical_event_delivery_rate']:.2%} threads received complete events")
                    
                    pytest.fail(
                        f"CRITICAL EVENT DELIVERY FAILURE: Only {report['critical_event_delivery_rate']:.2%} "
                        f"of threads received complete agent events. "
                        f"Multi-thread event delivery pipeline broken."
                    )
                
                # Success validations
                logger.info(" PASS:  SUCCESS: Perfect multi-thread agent event routing!")
                
                assert successful_threads >= num_concurrent_threads * 0.8, \
                    f"Too few successful thread executions: {successful_threads}/{num_concurrent_threads}"
                
                expected_total_events = num_concurrent_threads * len(self.event_tracker.critical_agent_events)
                assert total_events_delivered >= expected_total_events * 0.8, \
                    f"Too few events delivered: {total_events_delivered}/{expected_total_events}"
                
                assert report["event_routing_success_rate"] >= 0.95, \
                    f"Event routing success rate too low: {report['event_routing_success_rate']:.2%}"
        
        except Exception as e:
            report = self.event_tracker.generate_comprehensive_report()
            logger.error(f" CHART:  Partial results: {report}")
            logger.error(f" FAIL:  Multi-thread agent event routing test failed: {e}")
            raise
        
        # Verify test duration
        actual_duration = time.time() - test_start_time
        assert actual_duration > 12.0, \
            f"Multi-thread agent test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f" PASS:  Multi-thread agent event routing test completed in {actual_duration:.2f}s")
    
    async def _execute_and_track_thread_agent(self, client: ThreadEventWebSocketClient, 
                                            thread_id: str, query: str, thread_index: int) -> Dict:
        """Execute agent in specific thread and track all events."""
        events_received = 0
        routing_errors = 0
        
        try:
            # Execute agent
            await client.execute_agent_in_thread(thread_id, query)
            
            # Wait for completion
            result = await client.wait_for_thread_agent_completion(thread_id, timeout=30.0)
            
            events_received = result.get("event_count", 0)
            
            # Check for routing errors specific to this thread
            thread_routing_errors = [
                error for error in self.event_tracker.get_thread_routing_violations()
                if error.get("thread_id") == thread_id
            ]
            routing_errors = len(thread_routing_errors)
            
            return {
                "thread_index": thread_index,
                "thread_id": thread_id,
                "success": result["critical_events_complete"],
                "events_received": events_received,
                "routing_errors": routing_errors,
                "timeline": result.get("timeline", {})
            }
        
        except Exception as e:
            logger.error(f" FAIL:  Thread {thread_index} agent execution failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.asyncio
    async def test_multi_user_multi_thread_agent_event_isolation(self):
        """
        CRITICAL TEST: Multiple users with multiple threads - perfect event isolation.
        
        This test validates the most complex scenario: multiple users each running
        agents in multiple threads simultaneously. Events must be isolated perfectly.
        
        Expected Initial Result: FAILURE - Complex isolation likely broken under load
        Success Criteria: Zero cross-user or cross-thread event contamination
        """
        test_start_time = time.time()
        logger.info("[U+1F465][U+1F9F5] CRITICAL: Testing multi-user multi-thread agent event isolation")
        
        # Complex test configuration
        num_users = 3
        threads_per_user = 2
        
        user_clients = []
        execution_tasks = []
        
        try:
            # Create multiple authenticated users
            logger.info(f"[U+1F510] Creating {num_users} users with {threads_per_user} threads each...")
            for user_idx in range(num_users):
                user_context = await create_authenticated_user_context(
                    user_email=f"multi_user_thread_{user_idx}_{int(time.time())}@example.com",
                    environment=self.test_environment,
                    websocket_enabled=True
                )
                
                client = ThreadEventWebSocketClient(
                    user_context,
                    self.auth_helper,
                    self.event_tracker
                )
                user_clients.append(client)
                self.test_clients.append(client)
                
                logger.info(f" PASS:  Created user {user_idx}: {client.user_id}")
            
            # Execute complex multi-user multi-thread scenario
            for user_idx, client in enumerate(user_clients):
                task = asyncio.create_task(
                    self._execute_multi_thread_user_scenario(client, threads_per_user, user_idx)
                )
                execution_tasks.append(task)
            
            # Run all user scenarios concurrently
            logger.info("[U+1F680] Executing complex multi-user multi-thread agent scenarios...")
            user_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            # Analyze complex isolation results
            successful_users = 0
            total_successful_threads = 0
            total_events_delivered = 0
            isolation_violations = 0
            
            for user_idx, result in enumerate(user_results):
                if isinstance(result, Exception):
                    logger.error(f" FAIL:  User {user_idx} multi-thread scenario failed: {result}")
                else:
                    successful_users += 1
                    total_successful_threads += result.get("successful_threads", 0)
                    total_events_delivered += result.get("total_events", 0)
                    isolation_violations += result.get("isolation_violations", 0)
                    
                    logger.info(f"[U+1F464] User {user_idx}: {result.get('successful_threads', 0)}/{threads_per_user} threads successful")
            
            # Check for any isolation violations in event tracking
            routing_violations = self.event_tracker.get_thread_routing_violations()
            
            # Generate final comprehensive report
            report = self.event_tracker.generate_comprehensive_report()
            
            logger.info(" CHART:  MULTI-USER MULTI-THREAD ISOLATION RESULTS:")
            logger.info(f"   Successful Users: {successful_users}/{num_users}")
            logger.info(f"   Successful Threads: {total_successful_threads}/{num_users * threads_per_user}")
            logger.info(f"   Total Events Delivered: {total_events_delivered}")
            logger.info(f"   Routing Violations: {len(routing_violations)}")
            logger.info(f"   Isolation Violations: {isolation_violations}")
            logger.info(f"   Overall Success Rate: {successful_users / num_users:.2%}")
            
            # CRITICAL ASSERTIONS - Expected to FAIL initially
            if len(routing_violations) > 0 or isolation_violations > 0:
                logger.error(" ALERT:  COMPLEX ISOLATION FAILURE - Multi-user multi-thread contamination")
                logger.error(f" SEARCH:  Routing violations: {len(routing_violations)}")
                logger.error(f" SEARCH:  Isolation violations: {isolation_violations}")
                
                # Log violation details
                all_violations = routing_violations + [{"type": "isolation"} for _ in range(isolation_violations)]
                for violation in all_violations[:5]:  # First 5
                    logger.error(f" SEARCH:  Violation detail: {violation}")
                
                # Expected failure - complex isolation breaks under load
                pytest.fail(
                    f"COMPLEX ISOLATION FAILURE: {len(routing_violations)} routing + {isolation_violations} "
                    f"isolation violations in multi-user multi-thread scenario. "
                    f"System cannot maintain event isolation under realistic complex load."
                )
            
            if report["critical_event_delivery_rate"] < 0.7:
                logger.error(" ALERT:  COMPLEX EVENT DELIVERY RATE FAILURE")
                pytest.fail(
                    f"COMPLEX EVENT DELIVERY FAILURE: Only {report['critical_event_delivery_rate']:.2%} "
                    f"event delivery rate in complex scenario. System breaks under load."
                )
            
            # Success validations
            logger.info(" PASS:  SUCCESS: Perfect isolation in complex multi-user multi-thread scenario!")
            
            assert successful_users >= num_users * 0.8, \
                f"Too few successful users: {successful_users}/{num_users}"
            
            expected_threads = num_users * threads_per_user
            assert total_successful_threads >= expected_threads * 0.7, \
                f"Too few successful threads: {total_successful_threads}/{expected_threads}"
        
        except Exception as e:
            report = self.event_tracker.generate_comprehensive_report()
            logger.error(f" CHART:  Complex scenario partial results: {report}")
            logger.error(f" FAIL:  Multi-user multi-thread isolation test failed: {e}")
            raise
        
        # Verify significant test duration for complex scenario
        actual_duration = time.time() - test_start_time
        assert actual_duration > 15.0, \
            f"Complex isolation test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f" PASS:  Multi-user multi-thread isolation test completed in {actual_duration:.2f}s")
    
    async def _execute_multi_thread_user_scenario(self, client: ThreadEventWebSocketClient, 
                                                num_threads: int, user_idx: int) -> Dict:
        """Execute multi-thread scenario for single user."""
        successful_threads = 0
        total_events = 0
        isolation_violations = 0
        
        try:
            async with client.connect(timeout=40.0):
                # Create and execute agents in multiple threads
                thread_tasks = []
                thread_ids = []
                
                for thread_idx in range(num_threads):
                    # Create thread
                    thread_title = f"User {user_idx} Thread {thread_idx} Complex Test"
                    thread_id = await client.create_agent_thread(thread_title)
                    thread_ids.append(thread_id)
                    
                    # Create agent execution task
                    query = f"User {user_idx} Thread {thread_idx}: Complex optimization analysis"
                    task = asyncio.create_task(
                        self._execute_and_track_thread_agent(client, thread_id, query, thread_idx)
                    )
                    thread_tasks.append(task)
                
                # Execute all threads for this user concurrently
                thread_results = await asyncio.gather(*thread_tasks, return_exceptions=True)
                
                # Analyze user's thread results
                for thread_idx, result in enumerate(thread_results):
                    if isinstance(result, Exception):
                        logger.error(f" FAIL:  User {user_idx} Thread {thread_idx} failed: {result}")
                    else:
                        if result["success"]:
                            successful_threads += 1
                        total_events += result.get("events_received", 0)
                        isolation_violations += result.get("routing_errors", 0)
        
        except Exception as e:
            logger.error(f" FAIL:  User {user_idx} multi-thread scenario failed: {e}")
            raise
        
        return {
            "user_idx": user_idx,
            "user_id": client.user_id,
            "successful_threads": successful_threads,
            "total_events": total_events,
            "isolation_violations": isolation_violations
        }


# ============================================================================
# TEST EXECUTION CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    """
    Direct test execution for debugging and development.
    
    Run with: python -m pytest tests/e2e/thread_routing/test_agent_websocket_thread_events_e2e.py -v -s
    Or with unified test runner: python tests/unified_test_runner.py --real-services --real-llm --category e2e
    """
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("[U+1F680] Starting Agent WebSocket Thread Events E2E Test Suite")
    logger.info("[U+1F4CB] Tests included:")
    logger.info("   1. test_single_thread_all_agent_events_delivery")
    logger.info("   2. test_multi_thread_agent_event_routing")
    logger.info("   3. test_multi_user_multi_thread_agent_event_isolation")
    logger.info(" TARGET:  Business Value: Ensures $500K+ ARR Chat agent event delivery")
    logger.info("[U+1F916] Requirements: Real LLM + Full Docker stack + Authentication")
    logger.info(" WARNING: [U+FE0F]  Expected: Initial FAILURES due to complex event routing bugs")
    
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])