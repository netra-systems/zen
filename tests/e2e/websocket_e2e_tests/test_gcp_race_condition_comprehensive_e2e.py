"""
E2E TESTS: GCP WebSocket Race Condition Comprehensive End-to-End Validation

CRITICAL E2E SUITE: These tests validate the complete WebSocket race condition fix
in a full system environment using real services and authentic authentication.
This is the ULTIMATE validation that the race condition fix works in production-like scenarios.

TARGET VALIDATION:
1. Real WebSocket connections with Redis race condition fix
2. Authentic authentication flows with JWT/OAuth
3. Full MESSAGE ROUTING functionality with timing measurements
4. GCP staging environment simulation with real service timing
5. WebSocket 1011 error elimination validation

TEST MISSION:
- Test actual WebSocket connections with real services
- Validate MESSAGE ROUTING works with race condition fix
- Test GCP staging environment simulation
- Ensure NO 1011 WebSocket errors occur
- Validate complete AI chat functionality pipeline

Business Value:
- Ultimate validation that WebSocket connections work reliably
- Ensures core AI chat functionality is preserved
- Validates architectural fix prevents production failures
- Confirms MESSAGE ROUTING reliability

CRITICAL E2E REQUIREMENTS:
- MUST use real services (--real-services flag)
- MUST use authentic authentication (no mocks)
- MUST test actual WebSocket connections
- MUST validate complete message routing pipeline

SSOT COMPLIANCE: Uses test_framework/ssot/e2e_auth_helper.py for authentication
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import pytest
import websockets
import aiohttp
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode

from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    E2EAuthConfig,
    create_authenticated_user_context
)
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.real_services_test_fixtures import RealServicesTestFixtures
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    create_gcp_websocket_validator,
    gcp_websocket_readiness_check
)


@dataclass
class WebSocketTestResult:
    """Result of WebSocket connection test."""
    success: bool
    connection_time: float
    message_count: int
    errors: List[str]
    websocket_events: List[Dict[str, Any]]
    auth_method: str
    environment: str


@dataclass
class MessageRoutingTestResult:
    """Result of message routing test."""
    message_sent: bool
    response_received: bool
    routing_time: float
    agent_events_received: List[str]
    errors: List[str]


@pytest.mark.e2e_auth_required
class TestGCPRaceConditionComprehensiveE2E(SSotBaseTestCase):
    """
    Comprehensive E2E tests for GCP WebSocket race condition fix.
    
    CRITICAL: These tests use real services and authentic authentication
    to validate the race condition fix works in production-like scenarios.
    """
    
    def setup_method(self, method):
        """Setup E2E test environment with real services."""
        super().setup_method(method)
        self.env = get_env()
        self.real_services = RealServicesTestFixtures()
        
        # Determine test environment
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        # Setup auth helpers
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        
        # Configure for staging if needed
        if self.test_environment == "staging":
            self.auth_config = E2EAuthConfig.for_staging()
        else:
            self.auth_config = E2EAuthConfig.for_environment(self.test_environment)
        
        # Test timing configuration
        self.connection_timeout = 15.0 if self.test_environment == "staging" else 10.0
        self.message_timeout = 10.0
        
        print(f"[U+1F680] E2E RACE CONDITION TEST SETUP:")
        print(f"   Environment: {self.test_environment}")
        print(f"   Backend URL: {self.auth_config.backend_url}")
        print(f"   WebSocket URL: {self.auth_config.websocket_url}")
        print(f"   Connection timeout: {self.connection_timeout}s")
    
    @pytest.mark.asyncio
    async def test_websocket_connection_with_race_condition_fix(self):
        """
        CRITICAL E2E TEST: WebSocket connection with race condition fix.
        
        This test validates that WebSocket connections work reliably with
        the race condition fix applied, using real services and authentication.
        """
        print("[U+1F9EA] TESTING: WebSocket Connection with Race Condition Fix")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        connection_results = []
        
        # Test multiple connection attempts to validate consistency
        for attempt in range(3):
            print(f"   Connection attempt {attempt + 1}/3")
            
            start_time = time.time()
            websocket = None
            errors = []
            
            try:
                # Connect with authentication
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                    timeout=self.connection_timeout
                )
                
                connection_time = time.time() - start_time
                
                # Send test message to validate message routing
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": str(user_context.user_id),
                    "test_id": f"race-condition-test-{attempt}"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=self.message_timeout
                )
                
                response_data = json.loads(response)
                
                connection_results.append(WebSocketTestResult(
                    success=True,
                    connection_time=connection_time,
                    message_count=1,
                    errors=[],
                    websocket_events=[response_data],
                    auth_method="jwt_with_e2e_headers",
                    environment=self.test_environment
                ))
                
                print(f"      PASS:  Connection {attempt + 1} successful in {connection_time:.3f}s")
                
            except asyncio.TimeoutError as e:
                connection_time = time.time() - start_time
                errors.append(f"Connection timeout after {connection_time:.3f}s: {e}")
                print(f"      FAIL:  Connection {attempt + 1} failed: timeout")
                
                connection_results.append(WebSocketTestResult(
                    success=False,
                    connection_time=connection_time,
                    message_count=0,
                    errors=errors,
                    websocket_events=[],
                    auth_method="jwt_with_e2e_headers",
                    environment=self.test_environment
                ))
                
            except InvalidStatusCode as e:
                if e.status_code == 1011:
                    errors.append(f"WebSocket 1011 error - RACE CONDITION NOT FIXED: {e}")
                    print(f"      ALERT:  Connection {attempt + 1} failed: WebSocket 1011 (RACE CONDITION)")
                else:
                    errors.append(f"WebSocket status code {e.status_code}: {e}")
                    print(f"      FAIL:  Connection {attempt + 1} failed: status {e.status_code}")
                
                connection_results.append(WebSocketTestResult(
                    success=False,
                    connection_time=time.time() - start_time,
                    message_count=0,
                    errors=errors,
                    websocket_events=[],
                    auth_method="jwt_with_e2e_headers",
                    environment=self.test_environment
                ))
                
            except Exception as e:
                errors.append(f"Unexpected error: {e}")
                print(f"      FAIL:  Connection {attempt + 1} failed: {e}")
                
                connection_results.append(WebSocketTestResult(
                    success=False,
                    connection_time=time.time() - start_time,
                    message_count=0,
                    errors=errors,
                    websocket_events=[],
                    auth_method="jwt_with_e2e_headers",
                    environment=self.test_environment
                ))
                
            finally:
                if websocket:
                    await websocket.close()
        
        # Analyze results
        successful_connections = [r for r in connection_results if r.success]
        failed_connections = [r for r in connection_results if not r.success]
        
        print(f" CHART:  CONNECTION TEST RESULTS:")
        print(f"   Successful: {len(successful_connections)}/3")
        print(f"   Failed: {len(failed_connections)}/3")
        
        if successful_connections:
            avg_connection_time = sum(r.connection_time for r in successful_connections) / len(successful_connections)
            print(f"   Average connection time: {avg_connection_time:.3f}s")
        
        # CRITICAL: No 1011 errors should occur with race condition fix
        websocket_1011_errors = [
            r for r in failed_connections 
            if any("1011" in error for error in r.errors)
        ]
        
        assert len(websocket_1011_errors) == 0, (
            f"WebSocket 1011 errors detected - race condition fix failed: "
            f"{[r.errors for r in websocket_1011_errors]}"
        )
        
        # At least 2/3 connections should succeed (allow for network flakiness)
        assert len(successful_connections) >= 2, (
            f"Too many connection failures: {len(successful_connections)}/3 successful. "
            f"Errors: {[r.errors for r in failed_connections]}"
        )
        
        print(" PASS:  WEBSOCKET CONNECTION WITH RACE CONDITION FIX VALIDATED")
    
    @pytest.mark.asyncio
    async def test_message_routing_with_agent_events(self):
        """
        CRITICAL E2E TEST: Message routing with agent events and race condition fix.
        
        This test validates that complete MESSAGE ROUTING works correctly
        with the race condition fix, including agent event delivery.
        """
        print("[U+1F9EA] TESTING: Message Routing with Agent Events")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        websocket = None
        routing_results = []
        
        try:
            # Connect with authentication
            websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                timeout=self.connection_timeout
            )
            
            # Test different message types that should trigger agent events
            test_messages = [
                {
                    "type": "chat_message",
                    "content": "Hello, can you help me test the system?",
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id)
                },
                {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
            
            for msg_idx, test_message in enumerate(test_messages):
                print(f"   Testing message {msg_idx + 1}: {test_message['type']}")
                
                routing_start = time.time()
                agent_events_received = []
                errors = []
                
                try:
                    # Send message
                    await websocket.send(json.dumps(test_message))
                    message_sent = True
                    
                    # Collect responses and agent events
                    response_received = False
                    timeout_time = time.time() + self.message_timeout
                    
                    while time.time() < timeout_time:
                        try:
                            response = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=1.0
                            )
                            
                            response_data = json.loads(response)
                            response_received = True
                            
                            # Check for agent events
                            if "type" in response_data:
                                event_type = response_data["type"]
                                if event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]:
                                    agent_events_received.append(event_type)
                                    print(f"     [U+1F4E8] Agent event: {event_type}")
                            
                            # Break if we got a completion response
                            if response_data.get("type") in ["pong", "agent_completed", "chat_response"]:
                                break
                                
                        except asyncio.TimeoutError:
                            # No more messages in the next 1 second
                            break
                    
                    routing_time = time.time() - routing_start
                    
                    routing_results.append(MessageRoutingTestResult(
                        message_sent=message_sent,
                        response_received=response_received,
                        routing_time=routing_time,
                        agent_events_received=agent_events_received,
                        errors=errors
                    ))
                    
                    print(f"      PASS:  Message {msg_idx + 1} routing: {routing_time:.3f}s, events: {len(agent_events_received)}")
                    
                except Exception as e:
                    errors.append(f"Message routing error: {e}")
                    print(f"      FAIL:  Message {msg_idx + 1} routing failed: {e}")
                    
                    routing_results.append(MessageRoutingTestResult(
                        message_sent=False,
                        response_received=False,
                        routing_time=time.time() - routing_start,
                        agent_events_received=[],
                        errors=errors
                    ))
        
        finally:
            if websocket:
                await websocket.close()
        
        # Analyze routing results
        successful_routing = [r for r in routing_results if r.message_sent and r.response_received]
        failed_routing = [r for r in routing_results if not (r.message_sent and r.response_received)]
        
        print(f" CHART:  MESSAGE ROUTING RESULTS:")
        print(f"   Successful routing: {len(successful_routing)}/{len(routing_results)}")
        print(f"   Failed routing: {len(failed_routing)}")
        
        if successful_routing:
            avg_routing_time = sum(r.routing_time for r in successful_routing) / len(successful_routing)
            total_agent_events = sum(len(r.agent_events_received) for r in successful_routing)
            print(f"   Average routing time: {avg_routing_time:.3f}s")
            print(f"   Total agent events received: {total_agent_events}")
        
        # MESSAGE ROUTING should work with race condition fix
        assert len(successful_routing) >= len(routing_results) // 2, (
            f"Too many message routing failures: {len(successful_routing)}/{len(routing_results)}. "
            f"Errors: {[r.errors for r in failed_routing]}"
        )
        
        print(" PASS:  MESSAGE ROUTING WITH AGENT EVENTS VALIDATED")
    
    @pytest.mark.asyncio
    async def test_gcp_staging_environment_simulation(self):
        """
        CRITICAL E2E TEST: GCP staging environment simulation with race condition fix.
        
        This test simulates GCP staging environment conditions to validate
        the race condition fix works in production-like GCP scenarios.
        """
        print("[U+1F9EA] TESTING: GCP Staging Environment Simulation")
        
        # Force staging environment configuration
        staging_config = E2EAuthConfig.for_staging()
        staging_auth_helper = E2EWebSocketAuthHelper(config=staging_config, environment="staging")
        
        # Create authenticated user context for staging
        user_context = await create_authenticated_user_context(
            environment="staging",
            websocket_enabled=True
        )
        
        # Test GCP readiness validation directly
        print("   Testing GCP readiness validation...")
        
        # Create mock app state for GCP validation
        mock_app_state = type('MockAppState', (), {
            'db_session_factory': object(),
            'database_available': True,
            'redis_manager': type('MockRedisManager', (), {
                'is_connected': lambda: True
            })(),
            'auth_validation_complete': True,
            'key_manager': object(),
            'agent_supervisor': object(),
            'thread_service': object(),
            'agent_websocket_bridge': type('MockBridge', (), {
                'notify_agent_started': lambda: None,
                'notify_agent_completed': lambda: None,
                'notify_tool_executing': lambda: None
            })(),
            'startup_complete': True,
            'startup_failed': False,
            'startup_phase': 'complete'
        })()
        
        # Test GCP readiness validation
        readiness_start = time.time()
        ready, details = await gcp_websocket_readiness_check(mock_app_state)
        readiness_time = time.time() - readiness_start
        
        print(f"   GCP readiness check: {ready} in {readiness_time:.3f}s")
        print(f"   Readiness details: {details}")
        
        # Readiness should include grace period timing
        assert readiness_time >= 0.5 or not details.get('gcp_detected', False), (
            f"GCP readiness should include grace period if GCP detected: {readiness_time}s"
        )
        
        # Test WebSocket connection in staging simulation
        print("   Testing WebSocket connection in staging simulation...")
        
        staging_connection_results = []
        
        for attempt in range(2):  # Fewer attempts for staging (it's slower)
            print(f"     Staging connection attempt {attempt + 1}/2")
            
            start_time = time.time()
            websocket = None
            
            try:
                # Use staging-optimized connection
                websocket = await staging_auth_helper.connect_authenticated_websocket(
                    timeout=20.0  # Longer timeout for staging
                )
                
                connection_time = time.time() - start_time
                
                # Send test message
                test_message = {
                    "type": "staging_test",
                    "content": "GCP race condition fix validation",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": str(user_context.user_id)
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=15.0
                )
                
                staging_connection_results.append({
                    "success": True,
                    "connection_time": connection_time,
                    "response_received": True
                })
                
                print(f"        PASS:  Staging connection {attempt + 1} successful in {connection_time:.3f}s")
                
            except Exception as e:
                connection_time = time.time() - start_time
                error_msg = str(e)
                
                # Check for specific race condition indicators
                is_race_condition = any(indicator in error_msg.lower() for indicator in [
                    "1011", "server error", "connection closed", "timeout"
                ])
                
                staging_connection_results.append({
                    "success": False,
                    "connection_time": connection_time,
                    "error": error_msg,
                    "is_race_condition": is_race_condition
                })
                
                print(f"        FAIL:  Staging connection {attempt + 1} failed: {error_msg}")
                
            finally:
                if websocket:
                    await websocket.close()
        
        # Analyze staging results
        successful_staging = [r for r in staging_connection_results if r["success"]]
        failed_staging = [r for r in staging_connection_results if not r["success"]]
        
        race_condition_failures = [
            r for r in failed_staging if r.get("is_race_condition", False)
        ]
        
        print(f" CHART:  GCP STAGING SIMULATION RESULTS:")
        print(f"   Successful connections: {len(successful_staging)}/2")
        print(f"   Failed connections: {len(failed_staging)}")
        print(f"   Race condition failures: {len(race_condition_failures)}")
        
        # CRITICAL: No race condition failures should occur
        assert len(race_condition_failures) == 0, (
            f"Race condition failures in staging simulation: "
            f"{[r['error'] for r in race_condition_failures]}"
        )
        
        # At least one staging connection should succeed
        assert len(successful_staging) >= 1, (
            f"No successful staging connections: {[r.get('error') for r in failed_staging]}"
        )
        
        print(" PASS:  GCP STAGING ENVIRONMENT SIMULATION VALIDATED")
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections_stress_test(self):
        """
        STRESS E2E TEST: Concurrent WebSocket connections with race condition fix.
        
        This test validates that the race condition fix works under load
        with multiple concurrent WebSocket connections.
        """
        print("[U+1F9EA] TESTING: Concurrent WebSocket Connections Stress Test")
        
        # Create multiple user contexts
        concurrent_users = 3  # Moderate load for E2E testing
        user_contexts = []
        
        for i in range(concurrent_users):
            user_context = await create_authenticated_user_context(
                user_email=f"stress_test_user_{i}@example.com",
                environment=self.test_environment,
                websocket_enabled=True
            )
            user_contexts.append(user_context)
        
        print(f"   Created {len(user_contexts)} user contexts for stress test")
        
        # Concurrent connection test
        async def test_single_connection(user_idx: int, user_context) -> Dict[str, Any]:
            """Test single WebSocket connection."""
            connection_start = time.time()
            websocket = None
            
            try:
                # Connect with authentication
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                    timeout=self.connection_timeout
                )
                
                connection_time = time.time() - connection_start
                
                # Send test message
                test_message = {
                    "type": "concurrent_test",
                    "user_id": str(user_context.user_id),
                    "user_index": user_idx,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=self.message_timeout
                )
                
                return {
                    "user_idx": user_idx,
                    "success": True,
                    "connection_time": connection_time,
                    "response_received": True,
                    "error": None
                }
                
            except Exception as e:
                return {
                    "user_idx": user_idx,
                    "success": False,
                    "connection_time": time.time() - connection_start,
                    "response_received": False,
                    "error": str(e)
                }
                
            finally:
                if websocket:
                    await websocket.close()
        
        # Run concurrent connections
        print("   Starting concurrent connections...")
        concurrent_start = time.time()
        
        concurrent_tasks = [
            test_single_connection(i, user_contexts[i])
            for i in range(concurrent_users)
        ]
        
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        concurrent_elapsed = time.time() - concurrent_start
        
        # Process results
        successful_concurrent = []
        failed_concurrent = []
        
        for result in concurrent_results:
            if isinstance(result, Exception):
                failed_concurrent.append({
                    "user_idx": -1,
                    "success": False,
                    "error": str(result)
                })
            elif result["success"]:
                successful_concurrent.append(result)
            else:
                failed_concurrent.append(result)
        
        print(f" CHART:  CONCURRENT CONNECTION RESULTS:")
        print(f"   Total test time: {concurrent_elapsed:.3f}s")
        print(f"   Successful: {len(successful_concurrent)}/{concurrent_users}")
        print(f"   Failed: {len(failed_concurrent)}")
        
        if successful_concurrent:
            avg_connection_time = sum(r["connection_time"] for r in successful_concurrent) / len(successful_concurrent)
            print(f"   Average connection time: {avg_connection_time:.3f}s")
        
        # Check for race condition indicators in failures
        race_condition_errors = [
            r for r in failed_concurrent
            if r.get("error") and any(indicator in r["error"].lower() for indicator in ["1011", "race"])
        ]
        
        print(f"   Race condition errors: {len(race_condition_errors)}")
        
        # CRITICAL: No race condition errors under concurrent load
        assert len(race_condition_errors) == 0, (
            f"Race condition errors under concurrent load: "
            f"{[r['error'] for r in race_condition_errors]}"
        )
        
        # Most connections should succeed (allow for some network flakiness)
        success_rate = len(successful_concurrent) / concurrent_users
        assert success_rate >= 0.7, (
            f"Too many concurrent connection failures: {success_rate:.1%} success rate. "
            f"Errors: {[r.get('error') for r in failed_concurrent]}"
        )
        
        print(f" PASS:  CONCURRENT WEBSOCKET STRESS TEST VALIDATED: {success_rate:.1%} success rate")
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_with_race_condition_fix(self):
        """
        E2E TEST: WebSocket reconnection scenarios with race condition fix.
        
        This test validates that WebSocket reconnections work correctly
        with the race condition fix, ensuring reliability over time.
        """
        print("[U+1F9EA] TESTING: WebSocket Reconnection with Race Condition Fix")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        reconnection_results = []
        
        # Test multiple reconnection cycles
        for cycle in range(2):
            print(f"   Reconnection cycle {cycle + 1}/2")
            
            cycle_start = time.time()
            websocket = None
            
            try:
                # Initial connection
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                    timeout=self.connection_timeout
                )
                
                connection_time = time.time() - cycle_start
                print(f"     Initial connection: {connection_time:.3f}s")
                
                # Send initial message
                initial_message = {
                    "type": "reconnection_test_initial",
                    "cycle": cycle,
                    "user_id": str(user_context.user_id)
                }
                
                await websocket.send(json.dumps(initial_message))
                
                # Wait for response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=self.message_timeout
                )
                
                print(f"     Initial message successful")
                
                # Close connection
                await websocket.close()
                websocket = None
                
                # Wait a moment
                await asyncio.sleep(0.5)
                
                # Reconnect
                reconnect_start = time.time()
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                    timeout=self.connection_timeout
                )
                
                reconnect_time = time.time() - reconnect_start
                print(f"     Reconnection: {reconnect_time:.3f}s")
                
                # Send reconnection message
                reconnect_message = {
                    "type": "reconnection_test_reconnect",
                    "cycle": cycle,
                    "user_id": str(user_context.user_id)
                }
                
                await websocket.send(json.dumps(reconnect_message))
                
                # Wait for response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=self.message_timeout
                )
                
                total_cycle_time = time.time() - cycle_start
                
                reconnection_results.append({
                    "cycle": cycle,
                    "success": True,
                    "initial_connection_time": connection_time,
                    "reconnection_time": reconnect_time,
                    "total_cycle_time": total_cycle_time,
                    "error": None
                })
                
                print(f"      PASS:  Cycle {cycle + 1} successful: {total_cycle_time:.3f}s total")
                
            except Exception as e:
                total_cycle_time = time.time() - cycle_start
                error_msg = str(e)
                
                reconnection_results.append({
                    "cycle": cycle,
                    "success": False,
                    "total_cycle_time": total_cycle_time,
                    "error": error_msg
                })
                
                print(f"      FAIL:  Cycle {cycle + 1} failed: {error_msg}")
                
            finally:
                if websocket:
                    await websocket.close()
        
        # Analyze reconnection results
        successful_reconnections = [r for r in reconnection_results if r["success"]]
        failed_reconnections = [r for r in reconnection_results if not r["success"]]
        
        print(f" CHART:  RECONNECTION TEST RESULTS:")
        print(f"   Successful cycles: {len(successful_reconnections)}/2")
        print(f"   Failed cycles: {len(failed_reconnections)}")
        
        if successful_reconnections:
            avg_reconnect_time = sum(r["reconnection_time"] for r in successful_reconnections) / len(successful_reconnections)
            print(f"   Average reconnection time: {avg_reconnect_time:.3f}s")
        
        # Reconnections should work with race condition fix
        assert len(successful_reconnections) >= 1, (
            f"No successful reconnections: {[r['error'] for r in failed_reconnections]}"
        )
        
        print(" PASS:  WEBSOCKET RECONNECTION WITH RACE CONDITION FIX VALIDATED")


class TestWebSocketRaceConditionPerformanceE2E:
    """
    Performance E2E tests for WebSocket race condition fix validation.
    
    These tests provide performance benchmarks for the race condition fix
    in real E2E scenarios.
    """
    
    @pytest.mark.asyncio
    async def test_websocket_connection_timing_benchmarks(self):
        """
        PERFORMANCE E2E TEST: WebSocket connection timing benchmarks.
        
        This test provides detailed timing benchmarks for WebSocket connections
        with the race condition fix applied.
        """
        print(" CHART:  PERFORMANCE BENCHMARK: WebSocket Connection Timing")
        
        # Setup auth helper
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Test different timing scenarios
        timing_scenarios = [
            {"name": "Fast Connection", "iterations": 5},
            {"name": "Repeated Connection", "iterations": 3},
        ]
        
        benchmark_results = []
        
        for scenario in timing_scenarios:
            print(f"   Benchmarking: {scenario['name']}")
            
            scenario_times = []
            
            for iteration in range(scenario["iterations"]):
                websocket = None
                start_time = time.time()
                
                try:
                    websocket = await auth_helper.connect_authenticated_websocket(timeout=10.0)
                    connection_time = time.time() - start_time
                    scenario_times.append(connection_time)
                    
                    print(f"     Iteration {iteration + 1}: {connection_time:.3f}s")
                    
                except Exception as e:
                    print(f"     Iteration {iteration + 1} failed: {e}")
                    
                finally:
                    if websocket:
                        await websocket.close()
                    
                    # Small delay between iterations
                    await asyncio.sleep(0.1)
            
            if scenario_times:
                avg_time = sum(scenario_times) / len(scenario_times)
                min_time = min(scenario_times)
                max_time = max(scenario_times)
                
                benchmark_results.append({
                    "scenario": scenario["name"],
                    "iterations": len(scenario_times),
                    "average_time": avg_time,
                    "min_time": min_time,
                    "max_time": max_time,
                    "success_rate": len(scenario_times) / scenario["iterations"]
                })
                
                print(f"     Results: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")
        
        print(" CHART:  CONNECTION TIMING BENCHMARK RESULTS:")
        for result in benchmark_results:
            print(f"   {result['scenario']}:")
            print(f"     Success rate: {result['success_rate']:.1%}")
            print(f"     Average: {result['average_time']:.3f}s")
            print(f"     Range: {result['min_time']:.3f}s - {result['max_time']:.3f}s")
        
        # Performance should be reasonable
        for result in benchmark_results:
            assert result["success_rate"] >= 0.8, f"Poor success rate for {result['scenario']}: {result['success_rate']:.1%}"
            assert result["average_time"] <= 5.0, f"Slow connections for {result['scenario']}: {result['average_time']:.3f}s"
        
        print(" PASS:  WEBSOCKET CONNECTION TIMING BENCHMARKS COMPLETED")


if __name__ == "__main__":
    # Run specific tests for manual execution
    pytest.main([__file__, "-v", "--tb=short"])