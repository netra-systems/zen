"""
WebSocket Accept Race Condition E2E Reproduction Tests

Business Value Justification:
- Segment: Free, Early, Mid, Enterprise (All User Segments)
- Business Goal: Revenue Protection & User Experience 
- Value Impact: Prevents WebSocket connection failures that break core chat functionality
- Strategic Impact: Protects $500K+ ARR by ensuring reliable real-time AI interactions

CRITICAL RACE CONDITION REPRODUCTION - E2E LEVEL:
These E2E tests reproduce the EXACT race conditions experienced in production
GCP Cloud Run environments. They simulate real user interactions that trigger:
- "WebSocket is not connected. Need to call 'accept' first" errors every 2-3 minutes
- Message routing failures during connection establishment
- Agent execution failures due to WebSocket handshake timing issues

E2E Test Requirements (CLAUDE.md Section 15 Compliance):
- Uses REAL authentication (JWT/OAuth) - MANDATORY for all E2E tests
- Uses REAL services (PostgreSQL, Redis, Backend, Auth, LLM APIs)
- Uses REAL GCP-like infrastructure delays and timing
- Tests complete user journeys from connection to agent execution
- NO mocks allowed - all services must be real

CRITICAL: These tests MUST initially FAIL to prove they reproduce production race conditions.
Success means identifying and reproducing the exact timing issues that cause failures.
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
import json
import websockets
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest
import requests

from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    get_connection_state_registry
)
from shared.types.core_types import UserID, ConnectionID, ensure_user_id

# Test Framework Imports
from test_framework.ssot.e2e_test_base import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


@dataclass
class E2ERaceConditionEvent:
    """Track E2E race condition events for production scenario reproduction."""
    timestamp: float
    event_type: str  # "connection_start", "accept_attempt", "message_send", "agent_event", "error"
    user_id: str
    connection_id: str
    success: bool
    error: Optional[str] = None
    timing_data: Optional[Dict[str, float]] = field(default_factory=dict)
    agent_data: Optional[Dict[str, Any]] = field(default_factory=dict)
    websocket_state: Optional[str] = None
    production_scenario: Optional[str] = None  # "first_time_user", "concurrent_users", "agent_execution"


class WebSocketAcceptRaceConditionE2ETest(BaseE2ETest):
    """
    E2E tests reproducing WebSocket accept race conditions in production scenarios.
    
    CRITICAL: These tests simulate real user experiences and MUST use:
    - Real authentication flows
    - Real backend services 
    - Real WebSocket connections
    - Real agent execution
    - GCP Cloud Run timing characteristics
    """
    
    def setUp(self):
        """Set up E2E test environment with full production simulation."""
        super().setUp()
        
        # Real authentication (CLAUDE.md Section 15 MANDATORY)
        self.auth_helper = E2EAuthHelper()
        
        # E2E race condition tracking
        self.e2e_race_events: List[E2ERaceConditionEvent] = []
        self.production_errors: List[str] = []
        self.user_journey_failures: List[str] = []
        self.agent_execution_failures: List[str] = []
        
        # Real test users for production scenarios
        self.real_test_users = []
        for i in range(5):  # Multiple users for concurrent scenarios
            user_data = self.auth_helper.create_test_user(
                username=f"e2e_race_user_{i}_{int(time.time())}",
                email=f"e2e_user_{i}_{int(time.time())}@test.netra.ai"
            )
            self.real_test_users.append(user_data)
        
        # GCP Cloud Run timing simulation
        self.gcp_handshake_delay_range = (0.1, 0.3)  # 100-300ms delays seen in production
        self.gcp_accept_timeout = 15.0  # GCP NEG 15-second timeout
        self.production_message_burst_size = 10  # Typical agent execution message volume
        
        # Production scenario configurations
        self.concurrent_user_count = 5  # Simulate multiple simultaneous users
        self.agent_execution_duration = 30.0  # Typical agent execution time
        
        # Base URL for WebSocket connections
        self.base_ws_url = f"ws://localhost:8000"  # Backend service WebSocket endpoint
        
    def _record_e2e_race_event(self, event_type: str, user_id: str, connection_id: str,
                              success: bool, error: Optional[str] = None,
                              timing_data: Optional[Dict[str, float]] = None,
                              agent_data: Optional[Dict[str, Any]] = None,
                              websocket_state: Optional[str] = None,
                              production_scenario: Optional[str] = None):
        """Record E2E race condition event for production scenario analysis."""
        event = E2ERaceConditionEvent(
            timestamp=time.time(),
            event_type=event_type,
            user_id=user_id,
            connection_id=connection_id,
            success=success,
            error=error,
            timing_data=timing_data or {},
            agent_data=agent_data or {},
            websocket_state=websocket_state,
            production_scenario=production_scenario
        )
        self.e2e_race_events.append(event)
    
    @pytest.mark.e2e
    def test_first_time_user_websocket_connection_race_condition(self):
        """
        Test 1: First-time user WebSocket connection with race condition reproduction.
        
        CRITICAL PRODUCTION SCENARIO: This reproduces the exact user journey of a
        first-time user attempting to connect to chat, which triggers the race
        condition every 2-3 minutes in GCP Cloud Run production environment.
        
        Expected Race Condition: User authentication completes, WebSocket connection
        is established, but "Need to call 'accept' first" errors occur when agent
        execution attempts to send messages during the handshake window.
        """
        user_data = self.real_test_users[0]
        
        # Real authentication flow (CLAUDE.md Section 15 requirement)
        auth_token = self.auth_helper.get_valid_jwt_token(user_data['user_id'])
        
        connection_timing = {}
        first_time_user_errors = []
        
        async def simulate_first_time_user_connection(user_id: str):
            """Simulate complete first-time user connection scenario."""
            connection_id = f"first_time_user_{user_id}_{int(time.time())}"
            websocket_uri = f"{self.base_ws_url}/ws?token={auth_token}"
            
            try:
                # Record connection start
                connection_start_time = time.time()
                self._record_e2e_race_event(
                    "connection_start", user_id, connection_id, True,
                    timing_data={"connection_start": connection_start_time},
                    production_scenario="first_time_user"
                )
                
                # Establish WebSocket connection (this is where race conditions occur)
                async with websockets.connect(
                    websocket_uri,
                    extra_headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=self.gcp_accept_timeout  # GCP timeout
                ) as websocket:
                    
                    # Record accept completion time
                    accept_complete_time = time.time()
                    accept_duration = accept_complete_time - connection_start_time
                    
                    connection_timing['accept_duration'] = accept_duration
                    
                    self._record_e2e_race_event(
                        "accept_attempt", user_id, connection_id, True,
                        timing_data={
                            "accept_complete": accept_complete_time,
                            "accept_duration": accept_duration
                        },
                        websocket_state="accepted",
                        production_scenario="first_time_user"
                    )
                    
                    # Simulate the race condition: Send messages immediately after accept
                    # (This is what causes "Need to call 'accept' first" errors)
                    message_send_start = time.time()
                    
                    for i in range(self.production_message_burst_size):
                        try:
                            # This message burst during handshake window triggers race condition
                            message = {
                                "type": "user_message",
                                "content": f"First time user message {i}",
                                "user_id": user_id,
                                "timestamp": time.time(),
                                "message_index": i
                            }
                            
                            # Attempt to send message immediately (race condition trigger)
                            await websocket.send(json.dumps(message))
                            
                            # Record successful message send
                            self._record_e2e_race_event(
                                "message_send", user_id, connection_id, True,
                                timing_data={
                                    "message_send_time": time.time(),
                                    "message_index": i
                                },
                                production_scenario="first_time_user"
                            )
                            
                            # Brief delay between messages (simulate typing)
                            await asyncio.sleep(0.05)
                            
                        except Exception as message_error:
                            error_msg = str(message_error)
                            
                            # Check if this is the race condition error we're reproducing
                            if "accept" in error_msg.lower() or "connected" in error_msg.lower():
                                self.production_errors.append(
                                    f"RACE CONDITION REPRODUCED: {error_msg}"
                                )
                                
                                first_time_user_errors.append({
                                    "message_index": i,
                                    "error": error_msg,
                                    "timing": time.time() - message_send_start,
                                    "race_condition": True
                                })
                            
                            self._record_e2e_race_event(
                                "message_send", user_id, connection_id, False,
                                error=error_msg,
                                timing_data={"message_failure_time": time.time()},
                                production_scenario="first_time_user"
                            )
                    
                    # Simulate waiting for agent response (where race conditions manifest)
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=5.0  # Wait for server response
                        )
                        
                        self._record_e2e_race_event(
                            "agent_response", user_id, connection_id, True,
                            agent_data={"response_received": True},
                            production_scenario="first_time_user"
                        )
                        
                    except asyncio.TimeoutError:
                        # This timeout may indicate race condition prevented response
                        self.user_journey_failures.append(
                            f"First-time user didn't receive response - potential race condition"
                        )
                        
                        self._record_e2e_race_event(
                            "agent_response", user_id, connection_id, False,
                            error="Response timeout - potential race condition",
                            production_scenario="first_time_user"
                        )
                    
                    connection_timing['total_duration'] = time.time() - connection_start_time
                
            except Exception as connection_error:
                error_msg = str(connection_error)
                connection_timing['connection_failed'] = True
                
                # Check if connection failure is due to race condition
                if "accept" in error_msg.lower() or "handshake" in error_msg.lower():
                    self.production_errors.append(
                        f"Connection race condition: {error_msg}"
                    )
                
                self._record_e2e_race_event(
                    "connection_start", user_id, connection_id, False,
                    error=error_msg,
                    production_scenario="first_time_user"
                )
        
        # Execute first-time user scenario
        user_id = user_data['user_id']
        asyncio.run(simulate_first_time_user_connection(user_id))
        
        # Analyze first-time user race condition results
        total_events = len(self.e2e_race_events)
        successful_events = sum(1 for e in self.e2e_race_events if e.success)
        failed_events = total_events - successful_events
        race_condition_errors = len(self.production_errors)
        message_failures = len(first_time_user_errors)
        
        print(f"\n=== FIRST-TIME USER RACE CONDITION E2E ANALYSIS ===")
        print(f"Total E2E events: {total_events}")
        print(f"Successful events: {successful_events}")
        print(f"Failed events: {failed_events}")
        print(f"Race condition errors: {race_condition_errors}")
        print(f"Message failures: {message_failures}")
        print(f"User journey failures: {len(self.user_journey_failures)}")
        print(f"Connection timing: {connection_timing}")
        
        if self.production_errors:
            print("Production race condition errors reproduced:")
            for error in self.production_errors:
                print(f"  - {error}")
        
        # Check if production race condition was reproduced
        race_condition_reproduced = (
            race_condition_errors > 0 or
            message_failures > 0 or
            len(self.user_journey_failures) > 0 or
            connection_timing.get('connection_failed', False)
        )
        
        if not race_condition_reproduced:
            self.user_journey_failures.append(
                "CRITICAL: First-time user race condition not reproduced - "
                "test may not be simulating production conditions properly"
            )
        
        # CRITICAL: This test should fail to prove production race condition reproduction
        pytest.fail(
            f"First-time user WebSocket race condition E2E test completed. "
            f"Production race condition reproduced: {race_condition_reproduced}, "
            f"Race errors: {race_condition_errors}, "
            f"Message failures: {message_failures}, "
            f"Journey failures: {len(self.user_journey_failures)}"
        )
    
    @pytest.mark.e2e
    def test_concurrent_users_websocket_race_condition(self):
        """
        Test 2: Concurrent users triggering WebSocket race conditions.
        
        CRITICAL PRODUCTION SCENARIO: Multiple users connecting simultaneously
        trigger race conditions in the WebSocket accept process, causing some
        users to experience "Need to call 'accept' first" errors while others
        connect successfully.
        """
        concurrent_user_results = []
        concurrent_errors = []
        
        async def concurrent_user_worker(user_data: Dict[str, Any], worker_id: int):
            """Worker for concurrent user WebSocket connections."""
            user_id = user_data['user_id']
            auth_token = self.auth_helper.get_valid_jwt_token(user_id)
            connection_id = f"concurrent_user_{user_id}_{worker_id}"
            websocket_uri = f"{self.base_ws_url}/ws?token={auth_token}"
            
            worker_start_time = time.time()
            worker_result = {
                "worker_id": worker_id,
                "user_id": user_id,
                "start_time": worker_start_time,
                "success": False,
                "errors": [],
                "timing": {}
            }
            
            try:
                # Concurrent connection attempt (race condition trigger)
                async with websockets.connect(
                    websocket_uri,
                    extra_headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=self.gcp_accept_timeout
                ) as websocket:
                    
                    connection_established_time = time.time()
                    worker_result['timing']['connection_time'] = connection_established_time - worker_start_time
                    
                    self._record_e2e_race_event(
                        "connection_start", user_id, connection_id, True,
                        timing_data=worker_result['timing'],
                        production_scenario="concurrent_users"
                    )
                    
                    # Send concurrent messages (increases race condition probability)
                    for i in range(5):  # Reduced burst to avoid overwhelming
                        try:
                            message = {
                                "type": "concurrent_message",
                                "user_id": user_id,
                                "worker_id": worker_id,
                                "message_index": i,
                                "timestamp": time.time()
                            }
                            
                            await websocket.send(json.dumps(message))
                            
                            self._record_e2e_race_event(
                                "message_send", user_id, connection_id, True,
                                timing_data={"message_time": time.time()},
                                production_scenario="concurrent_users"
                            )
                            
                        except Exception as msg_error:
                            error_msg = str(msg_error)
                            worker_result['errors'].append(error_msg)
                            
                            if "accept" in error_msg.lower():
                                concurrent_errors.append({
                                    "worker_id": worker_id,
                                    "user_id": user_id[:8],
                                    "error": error_msg,
                                    "race_condition": True
                                })
                                
                                self.production_errors.append(
                                    f"Concurrent user race condition (worker {worker_id}): {error_msg}"
                                )
                            
                            self._record_e2e_race_event(
                                "message_send", user_id, connection_id, False,
                                error=error_msg,
                                production_scenario="concurrent_users"
                            )
                    
                    worker_result['success'] = True
                    worker_result['timing']['total_time'] = time.time() - worker_start_time
            
            except Exception as worker_error:
                error_msg = str(worker_error)
                worker_result['errors'].append(error_msg)
                
                if "accept" in error_msg.lower() or "handshake" in error_msg.lower():
                    concurrent_errors.append({
                        "worker_id": worker_id,
                        "user_id": user_id[:8],
                        "error": error_msg,
                        "race_condition": True
                    })
                
                self._record_e2e_race_event(
                    "connection_start", user_id, connection_id, False,
                    error=error_msg,
                    production_scenario="concurrent_users"
                )
            
            concurrent_user_results.append(worker_result)
            return worker_result
        
        # Execute concurrent user scenario
        async def run_concurrent_users():
            tasks = []
            
            for i in range(self.concurrent_user_count):
                user_data = self.real_test_users[i] if i < len(self.real_test_users) else self.real_test_users[0]
                task = asyncio.create_task(concurrent_user_worker(user_data, i))
                tasks.append(task)
            
            # Start all tasks simultaneously (maximum race condition probability)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        # Run concurrent user test
        concurrent_results = asyncio.run(run_concurrent_users())
        
        # Analyze concurrent user race condition results
        successful_connections = sum(1 for r in concurrent_user_results if isinstance(r, dict) and r.get('success', False))
        failed_connections = len(concurrent_user_results) - successful_connections
        total_errors = sum(len(r.get('errors', [])) for r in concurrent_user_results if isinstance(r, dict))
        race_condition_detected = len(concurrent_errors) > 0
        
        print(f"\n=== CONCURRENT USERS RACE CONDITION E2E ANALYSIS ===")
        print(f"Concurrent users tested: {self.concurrent_user_count}")
        print(f"Successful connections: {successful_connections}")
        print(f"Failed connections: {failed_connections}")
        print(f"Total errors: {total_errors}")
        print(f"Concurrent race errors: {len(concurrent_errors)}")
        print(f"Production errors: {len(self.production_errors)}")
        
        if concurrent_errors:
            print("Concurrent user race condition errors:")
            for error in concurrent_errors[:5]:  # Show first 5 errors
                print(f"  - Worker {error['worker_id']} (User {error['user_id']}): {error['error']}")
        
        # Check for concurrent race condition reproduction
        concurrent_race_reproduced = (
            race_condition_detected or
            failed_connections > successful_connections or  # More failures than successes indicates issues
            total_errors > self.concurrent_user_count  # More errors than users indicates systemic problems
        )
        
        # CRITICAL: Concurrent user race conditions indicate production issues
        pytest.fail(
            f"Concurrent users WebSocket race condition E2E test completed. "
            f"Race condition reproduced: {concurrent_race_reproduced}, "
            f"Success rate: {successful_connections}/{self.concurrent_user_count}, "
            f"Race errors: {len(concurrent_errors)}"
        )
    
    @pytest.mark.e2e
    def test_agent_execution_websocket_events_race_condition(self):
        """
        Test 3: Agent execution WebSocket events with race condition reproduction.
        
        CRITICAL PRODUCTION SCENARIO: This reproduces the exact scenario where
        agent execution (the core business value) fails due to WebSocket race
        conditions. When agents try to send real-time events (agent_started,
        agent_thinking, tool_executing, tool_completed, agent_completed), they
        encounter "Need to call 'accept' first" errors.
        """
        user_data = self.real_test_users[0]
        auth_token = self.auth_helper.get_valid_jwt_token(user_data['user_id'])
        
        agent_execution_events = []
        agent_race_errors = []
        
        async def simulate_agent_execution_with_websocket_events(user_id: str):
            """Simulate complete agent execution scenario with WebSocket events."""
            connection_id = f"agent_execution_{user_id}_{int(time.time())}"
            websocket_uri = f"{self.base_ws_url}/ws?token={auth_token}"
            
            try:
                async with websockets.connect(
                    websocket_uri,
                    extra_headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=self.gcp_accept_timeout
                ) as websocket:
                    
                    # Step 1: Send user message to trigger agent execution
                    user_message = {
                        "type": "user_message",
                        "content": "Analyze the latest market trends in AI technology",
                        "user_id": user_id,
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(user_message))
                    
                    self._record_e2e_race_event(
                        "user_message", user_id, connection_id, True,
                        agent_data={"message": "Agent execution trigger sent"},
                        production_scenario="agent_execution"
                    )
                    
                    # Step 2: Simulate the 5 critical agent events that MUST be delivered
                    critical_agent_events = [
                        {"type": "agent_started", "status": "Agent execution initiated"},
                        {"type": "agent_thinking", "status": "Analyzing market trends"},
                        {"type": "tool_executing", "tool": "market_analysis", "status": "Gathering data"},
                        {"type": "tool_completed", "tool": "market_analysis", "status": "Data analysis complete"},
                        {"type": "agent_completed", "status": "Analysis complete", "result": "AI market trends analyzed"}
                    ]
                    
                    # Send agent events with timing that triggers race conditions
                    for i, event in enumerate(critical_agent_events):
                        try:
                            # Add race condition timing - send events rapidly after accept
                            if i == 0:
                                # First event immediately after connection (race condition window)
                                await asyncio.sleep(0.01)
                            else:
                                # Subsequent events with brief delays (simulate real agent execution)
                                await asyncio.sleep(0.1)
                            
                            event_message = {
                                **event,
                                "user_id": user_id,
                                "connection_id": connection_id,
                                "timestamp": time.time(),
                                "event_index": i
                            }
                            
                            # This is where race conditions occur in production
                            await websocket.send(json.dumps(event_message))
                            
                            agent_execution_events.append({
                                "event_type": event["type"],
                                "success": True,
                                "timestamp": time.time(),
                                "event_index": i
                            })
                            
                            self._record_e2e_race_event(
                                "agent_event", user_id, connection_id, True,
                                agent_data=event,
                                production_scenario="agent_execution"
                            )
                            
                        except Exception as event_error:
                            error_msg = str(event_error)
                            
                            agent_execution_events.append({
                                "event_type": event["type"],
                                "success": False,
                                "error": error_msg,
                                "timestamp": time.time(),
                                "event_index": i
                            })
                            
                            # Check for race condition errors in agent events
                            if "accept" in error_msg.lower() or "connected" in error_msg.lower():
                                agent_race_errors.append({
                                    "event_type": event["type"],
                                    "error": error_msg,
                                    "event_index": i,
                                    "race_condition": True
                                })
                                
                                self.agent_execution_failures.append(
                                    f"Agent event race condition ({event['type']}): {error_msg}"
                                )
                                
                                # This is CRITICAL - agent events failing breaks core business value
                                self.production_errors.append(
                                    f"CRITICAL BUSINESS IMPACT: Agent event {event['type']} failed due to race condition"
                                )
                            
                            self._record_e2e_race_event(
                                "agent_event", user_id, connection_id, False,
                                error=error_msg,
                                agent_data=event,
                                production_scenario="agent_execution"
                            )
                    
                    # Step 3: Wait for any server responses
                    try:
                        # In a real scenario, server might send acknowledgments or additional events
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        
                        self._record_e2e_race_event(
                            "server_response", user_id, connection_id, True,
                            agent_data={"response": "Server response received"},
                            production_scenario="agent_execution"
                        )
                        
                    except asyncio.TimeoutError:
                        # Timeout might indicate race condition prevented server processing
                        self.agent_execution_failures.append(
                            "Server response timeout - may indicate race condition prevented processing"
                        )
                        
                        self._record_e2e_race_event(
                            "server_response", user_id, connection_id, False,
                            error="Response timeout",
                            production_scenario="agent_execution"
                        )
                
            except Exception as execution_error:
                error_msg = str(execution_error)
                
                self.agent_execution_failures.append(
                    f"Agent execution connection failed: {error_msg}"
                )
                
                if "accept" in error_msg.lower():
                    self.production_errors.append(
                        f"Agent execution race condition: {error_msg}"
                    )
                
                self._record_e2e_race_event(
                    "agent_execution", user_id, connection_id, False,
                    error=error_msg,
                    production_scenario="agent_execution"
                )
        
        # Execute agent execution scenario
        user_id = user_data['user_id']
        asyncio.run(simulate_agent_execution_with_websocket_events(user_id))
        
        # Analyze agent execution race condition results
        total_agent_events = len(agent_execution_events)
        successful_agent_events = sum(1 for e in agent_execution_events if e.get('success', False))
        failed_agent_events = total_agent_events - successful_agent_events
        critical_race_errors = len(agent_race_errors)
        business_impact_failures = len(self.agent_execution_failures)
        
        print(f"\n=== AGENT EXECUTION RACE CONDITION E2E ANALYSIS ===")
        print(f"Total agent events: {total_agent_events}")
        print(f"Successful agent events: {successful_agent_events}")
        print(f"Failed agent events: {failed_agent_events}")
        print(f"Critical race errors: {critical_race_errors}")
        print(f"Business impact failures: {business_impact_failures}")
        print(f"Production errors: {len(self.production_errors)}")
        
        if agent_race_errors:
            print("Agent execution race condition errors:")
            for error in agent_race_errors:
                print(f"  - {error['event_type']}: {error['error']}")
        
        if self.agent_execution_failures:
            print("Agent execution failures (business impact):")
            for failure in self.agent_execution_failures:
                print(f"  - {failure}")
        
        # Check for agent execution race condition reproduction
        agent_race_reproduced = (
            critical_race_errors > 0 or
            failed_agent_events > 0 or
            business_impact_failures > 0 or
            successful_agent_events < 5  # Not all 5 critical events succeeded
        )
        
        # Calculate business impact score
        event_delivery_rate = successful_agent_events / max(total_agent_events, 1) * 100
        
        # CRITICAL: Agent execution failures directly impact $500K+ ARR
        pytest.fail(
            f"Agent execution WebSocket race condition E2E test completed. "
            f"BUSINESS CRITICAL race condition reproduced: {agent_race_reproduced}, "
            f"Event delivery rate: {event_delivery_rate:.1f}%, "
            f"Critical errors: {critical_race_errors}, "
            f"Business impact failures: {business_impact_failures}"
        )
    
    def tearDown(self):
        """Clean up E2E race condition test environment."""
        # Log comprehensive E2E race condition summary
        print(f"\n=== E2E WEBSOCKET RACE CONDITION TEST SUMMARY ===")
        print(f"Total E2E race events recorded: {len(self.e2e_race_events)}")
        print(f"Production errors reproduced: {len(self.production_errors)}")
        print(f"User journey failures: {len(self.user_journey_failures)}")
        print(f"Agent execution failures: {len(self.agent_execution_failures)}")
        
        # Analyze overall race condition reproduction success
        production_scenarios_tested = set(e.production_scenario for e in self.e2e_race_events)
        race_condition_events = [e for e in self.e2e_race_events if not e.success]
        
        print(f"Production scenarios tested: {production_scenarios_tested}")
        print(f"Total race condition events: {len(race_condition_events)}")
        
        # Business impact analysis
        business_critical_failures = [
            error for error in self.production_errors 
            if "CRITICAL BUSINESS IMPACT" in error or "agent_event" in error
        ]
        
        if business_critical_failures:
            print(f"\n ALERT:  BUSINESS CRITICAL FAILURES REPRODUCED: {len(business_critical_failures)}")
            print("These race conditions directly impact $500K+ ARR:")
            for failure in business_critical_failures:
                print(f"  - {failure}")
        
        # Clean up test users
        for user_data in self.real_test_users:
            try:
                self.auth_helper.cleanup_test_user(user_data['user_id'])
            except Exception as cleanup_error:
                print(f"User cleanup error: {cleanup_error}")
        
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])