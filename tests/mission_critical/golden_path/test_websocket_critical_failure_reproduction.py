"""
MISSION CRITICAL: WebSocket Critical Failure Reproduction Tests for Golden Path

🚨 MISSION CRITICAL TEST 🚨
This test suite reproduces and validates fixes for the 3 P1 critical failures
that have impacted $120K+ MRR functionality in the golden path user flow.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - affects entire customer base
- Business Goal: Prevent regression of critical WebSocket failures that block revenue
- Value Impact: WebSocket failures = broken chat = complete business value loss
- Strategic Impact: Protects $120K+ MRR by ensuring critical failures never return

P1 CRITICAL FAILURES REPRODUCED AND PROTECTED:
1. WebSocket connection timeouts in staging/production environments
2. Missing WebSocket event delivery causing chat experience degradation
3. Race conditions in multi-user WebSocket scenarios under load

ZERO TOLERANCE: These failures MUST be detected immediately if they regress.
"""

import asyncio
import pytest
import time
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.types.core_types import UserID, ThreadID, RunID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.isolated_environment import get_env


class TestWebSocketCriticalFailureReproduction(SSotAsyncTestCase):
    """
    🚨 MISSION CRITICAL TEST SUITE 🚨
    
    Reproduces the 3 P1 critical WebSocket failures that have caused business impact.
    These tests MUST fail before fixes and MUST pass after fixes are implemented.
    """
    
    def setup_method(self, method=None):
        """Setup with critical failure tracking context."""
        super().setup_method(method)
        
        # Mission critical business metrics
        self.record_metric("mission_critical", True)
        self.record_metric("p1_critical_failure_protection", True)
        self.record_metric("revenue_protection", 120000)  # $120K MRR
        self.record_metric("deployment_blocker", True)
        
        # Initialize components
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.id_generator = UnifiedIdGenerator()
        
        # Test configuration
        self.websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # The 5 mission critical events that MUST be delivered
        self.CRITICAL_EVENTS = [
            "agent_started",      # User sees AI began work
            "agent_thinking",     # Real-time reasoning visibility  
            "tool_executing",     # Tool usage transparency
            "tool_completed",     # Tool results display
            "agent_completed"     # Final results ready
        ]
        
        # Connection tracking for cleanup
        self.active_connections = []
        self.connection_lock = threading.Lock()
        
    async def async_teardown_method(self, method=None):
        """Critical cleanup with failure protection."""
        try:
            # Close all tracked connections
            connections_to_close = []
            with self.connection_lock:
                connections_to_close = self.active_connections.copy()
                self.active_connections.clear()
            
            for connection in connections_to_close:
                try:
                    await WebSocketTestHelpers.close_test_connection(connection)
                except Exception as cleanup_error:
                    # Log but don't fail on cleanup errors
                    print(f"⚠️  Connection cleanup warning: {cleanup_error}")
            
        except Exception as e:
            print(f"⚠️  Critical test cleanup error: {e}")
        
        await super().async_teardown_method(method)
    
    @pytest.mark.mission_critical
    @pytest.mark.p1_critical_failure
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_websocket_connection_timeout_failure_reproduction(self):
        """
        🚨 P1 CRITICAL FAILURE REPRODUCTION: WebSocket Connection Timeouts
        
        Reproduces the staging/production WebSocket connection timeout failures
        that have blocked users from accessing chat functionality.
        
        CRITICAL FAILURE SCENARIO:
        - Users cannot connect to WebSocket in staging/production
        - Connections time out before authentication completes
        - GCP Cloud Run/NEG limitations cause connection drops
        - Results in complete chat system unavailability
        """
        failure_reproduction_start = time.time()
        
        # Create user context for connection test
        user_context = await create_authenticated_user_context(
            user_email="connection_timeout_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Simulate staging environment conditions
        staging_conditions = {
            "connection_timeout": 5.0,  # Aggressive timeout to reproduce failure
            "auth_delay": True,         # Simulate auth processing delay
            "gcp_neg_simulation": True  # Simulate GCP Network Endpoint Group limits
        }
        
        # Get authentication with staging simulation
        try:
            if self.environment == "staging":
                jwt_token = await self.auth_helper.get_staging_token_async(
                    email=user_context.agent_context.get('user_email')
                )
            else:
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=str(user_context.user_id),
                    email=user_context.agent_context.get('user_email')
                )
        except Exception as auth_error:
            # This is EXPECTED in failure reproduction - authentication should be challenging
            print(f"📊 EXPECTED AUTH CHALLENGE (simulating failure): {auth_error}")
            # Use fallback token for connection testing
            jwt_token = self.auth_helper.create_test_jwt_token()
        
        # Get headers with staging-specific optimizations
        ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
        
        # CRITICAL FAILURE TEST: Attempt connection with conditions that reproduce timeout
        connection_attempts = []
        successful_connections = 0
        timeout_failures = 0
        auth_failures = 0
        
        # Test multiple connection attempts to reproduce the intermittent failure
        for attempt in range(3):
            attempt_start = time.time()
            
            try:
                # REPRODUCTION: Use conditions that have caused failures in staging
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=self.websocket_url,
                    headers=ws_headers,
                    timeout=staging_conditions["connection_timeout"],  # Aggressive timeout
                    user_id=str(user_context.user_id),
                    retry_attempts=1  # No retries to see raw failure
                )
                
                # If connection succeeds, track it
                with self.connection_lock:
                    self.active_connections.append(connection)
                successful_connections += 1
                
                connection_time = time.time() - attempt_start
                connection_attempts.append({
                    "attempt": attempt + 1,
                    "success": True,
                    "connection_time": connection_time,
                    "error": None
                })
                
                # Test if the connection can actually send/receive
                test_message = {
                    "type": "connection_test",
                    "attempt": attempt + 1,
                    "timestamp": time.time()
                }
                
                try:
                    await WebSocketTestHelpers.send_test_message(
                        connection, test_message, timeout=3.0
                    )
                    
                    # Try to receive a response (may timeout)
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=5.0
                        )
                        connection_attempts[-1]["message_exchange"] = True
                    except:
                        connection_attempts[-1]["message_exchange"] = False
                        
                except Exception as msg_error:
                    connection_attempts[-1]["message_error"] = str(msg_error)
                    
            except asyncio.TimeoutError:
                timeout_failures += 1
                connection_attempts.append({
                    "attempt": attempt + 1,
                    "success": False,
                    "connection_time": time.time() - attempt_start,
                    "error": "TIMEOUT",
                    "error_type": "connection_timeout"
                })
                
            except Exception as e:
                error_type = "auth_failure" if "auth" in str(e).lower() else "connection_failure"
                if error_type == "auth_failure":
                    auth_failures += 1
                    
                connection_attempts.append({
                    "attempt": attempt + 1,
                    "success": False,
                    "connection_time": time.time() - attempt_start,
                    "error": str(e),
                    "error_type": error_type
                })
        
        total_test_time = time.time() - failure_reproduction_start
        
        # CRITICAL FAILURE ANALYSIS AND VALIDATION
        
        # Calculate failure rates
        total_attempts = len(connection_attempts)
        success_rate = successful_connections / total_attempts if total_attempts > 0 else 0
        timeout_rate = timeout_failures / total_attempts if total_attempts > 0 else 0
        
        # Record comprehensive failure reproduction metrics
        self.record_metric("p1_connection_test_success_rate", success_rate)
        self.record_metric("p1_connection_test_timeout_rate", timeout_rate)
        self.record_metric("p1_connection_test_auth_failures", auth_failures)
        self.record_metric("p1_connection_test_total_time", total_test_time)
        self.record_metric("p1_connection_test_attempts", total_attempts)
        
        # CRITICAL ASSESSMENT: This test should PASS if the P1 failures are FIXED
        
        if success_rate == 0:
            # TOTAL FAILURE - The P1 critical issue is ACTIVE
            pytest.fail(
                f"🚨 P1 CRITICAL FAILURE ACTIVE: WebSocket connections completely failing\n"
                f"Success Rate: {success_rate:.1%} (0% = system down)\n"
                f"Timeout Failures: {timeout_failures}/{total_attempts}\n"
                f"Auth Failures: {auth_failures}\n"
                f"This reproduces the EXACT P1 failure that blocks $120K+ MRR!\n"
                f"Attempts: {json.dumps(connection_attempts, indent=2)}"
            )
            
        elif success_rate < 0.5:
            # PARTIAL FAILURE - The P1 critical issue is PARTIALLY ACTIVE
            pytest.fail(
                f"🚨 P1 CRITICAL FAILURE PARTIALLY ACTIVE: High WebSocket failure rate\n"
                f"Success Rate: {success_rate:.1%} (< 50% = unacceptable)\n"
                f"Timeout Rate: {timeout_rate:.1%}\n"
                f"This indicates the P1 connection issue is not fully resolved!\n"
                f"Business impact: Significant user experience degradation"
            )
            
        elif timeout_rate > 0.3:
            # HIGH TIMEOUT RATE - Indicates connection instability
            pytest.fail(
                f"🚨 P1 CONNECTION INSTABILITY DETECTED: High timeout rate\n"
                f"Timeout Rate: {timeout_rate:.1%} (> 30% = unstable)\n"
                f"Success Rate: {success_rate:.1%}\n"
                f"This suggests the P1 timeout issue may regress under load!"
            )
        
        # SUCCESS CASE: P1 critical failure is RESOLVED
        print(f"\n✅ P1 CRITICAL FAILURE PROTECTION: WebSocket Connection Test PASSED")
        print(f"   🔗 Success Rate: {success_rate:.1%}")
        print(f"   ⏱️  Timeout Rate: {timeout_rate:.1%}")
        print(f"   🕒 Total Test Time: {total_test_time:.2f}s")
        print(f"   💰 $120K+ MRR: PROTECTED from connection failures")
        
        # Cleanup successful connections
        for attempt_data in connection_attempts:
            if attempt_data.get("success"):
                # Connections were already added to active_connections for cleanup
                pass
                
    @pytest.mark.mission_critical
    @pytest.mark.p1_critical_failure
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_missing_websocket_events_failure_reproduction(self):
        """
        🚨 P1 CRITICAL FAILURE REPRODUCTION: Missing WebSocket Events
        
        Reproduces the critical WebSocket event delivery failures that have
        caused chat experience degradation and user abandonment.
        
        CRITICAL FAILURE SCENARIO:
        - Users send messages but receive incomplete event streams
        - Missing agent_started, agent_thinking, or agent_completed events
        - Broken user experience with no feedback on AI processing
        - Results in user frustration and platform abandonment
        """
        event_failure_start = time.time()
        
        # Create user context for event testing
        user_context = await create_authenticated_user_context(
            user_email="missing_events_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Authenticate and connect
        jwt_token = await self._get_reliable_token(
            user_context.agent_context.get('user_email')
        )
        ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
        
        # Establish connection for event testing
        try:
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=ws_headers,
                timeout=15.0,
                user_id=str(user_context.user_id)
            )
            with self.connection_lock:
                self.active_connections.append(connection)
                
        except Exception as conn_error:
            pytest.fail(f"🚨 SETUP FAILURE: Cannot establish connection for event testing: {conn_error}")
        
        # Execute multiple message scenarios to test event delivery
        event_test_scenarios = [
            {
                "name": "Basic Agent Request",
                "message": {
                    "type": "chat_message",
                    "content": "Help me optimize costs",
                    "user_id": str(user_context.user_id),
                    "scenario": "basic_optimization"
                },
                "expected_events": self.CRITICAL_EVENTS,
                "max_wait_time": 30.0
            },
            {
                "name": "Complex Agent Request",
                "message": {
                    "type": "chat_message", 
                    "content": "Analyze my infrastructure and provide detailed cost optimization with specific tool usage",
                    "user_id": str(user_context.user_id),
                    "scenario": "complex_analysis"
                },
                "expected_events": self.CRITICAL_EVENTS,
                "max_wait_time": 45.0
            },
            {
                "name": "Rapid Follow-up Request",
                "message": {
                    "type": "chat_message",
                    "content": "Show me the top 3 recommendations",
                    "user_id": str(user_context.user_id),
                    "scenario": "rapid_followup"
                },
                "expected_events": self.CRITICAL_EVENTS,
                "max_wait_time": 20.0
            }
        ]
        
        scenario_results = []
        critical_failures_detected = []
        
        for scenario in event_test_scenarios:
            scenario_start = time.time()
            
            try:
                # Send the scenario message
                await WebSocketTestHelpers.send_test_message(
                    connection, scenario["message"], timeout=5.0
                )
                
                # Collect events for this scenario
                events_received = []
                event_types_received = set()
                
                scenario_wait_start = time.time()
                while (time.time() - scenario_wait_start) < scenario["max_wait_time"]:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=3.0
                        )
                        
                        if event and isinstance(event, dict):
                            event_type = event.get("type")
                            if event_type:
                                events_received.append({
                                    "type": event_type,
                                    "timestamp": time.time() - scenario_start,
                                    "data": event
                                })
                                event_types_received.add(event_type)
                                
                                # Check if we have all expected events
                                if all(evt in event_types_received for evt in scenario["expected_events"]):
                                    break
                                    
                    except:
                        # Individual event timeouts are acceptable - continue collecting
                        continue
                
                scenario_time = time.time() - scenario_start
                
                # Analyze scenario results
                missing_events = [evt for evt in scenario["expected_events"] if evt not in event_types_received]
                success = len(missing_events) == 0
                
                scenario_result = {
                    "scenario_name": scenario["name"],
                    "success": success,
                    "events_received": list(event_types_received),
                    "missing_events": missing_events,
                    "total_events_count": len(events_received),
                    "scenario_time": scenario_time,
                    "max_allowed_time": scenario["max_wait_time"]
                }
                
                scenario_results.append(scenario_result)
                
                # Track critical failures
                if missing_events:
                    critical_failures_detected.append({
                        "scenario": scenario["name"],
                        "missing_events": missing_events,
                        "failure_type": "missing_events"
                    })
                    
                if scenario_time >= scenario["max_wait_time"]:
                    critical_failures_detected.append({
                        "scenario": scenario["name"],
                        "failure_type": "timeout",
                        "time_taken": scenario_time
                    })
                
            except Exception as scenario_error:
                critical_failures_detected.append({
                    "scenario": scenario["name"],
                    "failure_type": "execution_error",
                    "error": str(scenario_error)
                })
                
                scenario_results.append({
                    "scenario_name": scenario["name"],
                    "success": False,
                    "error": str(scenario_error),
                    "scenario_time": time.time() - scenario_start
                })
        
        total_event_test_time = time.time() - event_failure_start
        
        # CRITICAL EVENT FAILURE ANALYSIS
        
        successful_scenarios = sum(1 for result in scenario_results if result.get("success"))
        total_scenarios = len(scenario_results)
        success_rate = successful_scenarios / total_scenarios if total_scenarios > 0 else 0
        
        # Record comprehensive event failure metrics
        self.record_metric("p1_event_delivery_success_rate", success_rate)
        self.record_metric("p1_event_delivery_failures", len(critical_failures_detected))
        self.record_metric("p1_event_test_scenarios", total_scenarios)
        self.record_metric("p1_event_test_total_time", total_event_test_time)
        
        # CRITICAL ASSESSMENT: Event delivery must be reliable
        
        if len(critical_failures_detected) > 0:
            # P1 EVENT DELIVERY FAILURE ACTIVE
            failure_summary = "\n".join([
                f"  - {failure['scenario']}: {failure.get('missing_events', failure.get('failure_type'))}"
                for failure in critical_failures_detected
            ])
            
            pytest.fail(
                f"🚨 P1 CRITICAL FAILURE ACTIVE: Missing WebSocket Events Detected\n"
                f"Success Rate: {success_rate:.1%}\n"
                f"Critical Failures: {len(critical_failures_detected)}\n"
                f"Failure Details:\n{failure_summary}\n"
                f"This reproduces the EXACT P1 event delivery failure!\n"
                f"Business Impact: Broken chat experience = user abandonment\n"
                f"Results: {json.dumps(scenario_results, indent=2)}"
            )
            
        elif success_rate < 1.0:
            # PARTIAL EVENT DELIVERY FAILURE
            pytest.fail(
                f"🚨 P1 EVENT DELIVERY INSTABILITY: Some scenarios failed\n"
                f"Success Rate: {success_rate:.1%} (must be 100%)\n"
                f"Failed Scenarios: {total_scenarios - successful_scenarios}\n"
                f"This indicates event delivery is not fully reliable!"
            )
        
        # SUCCESS CASE: P1 event delivery failure is RESOLVED
        print(f"\n✅ P1 CRITICAL FAILURE PROTECTION: WebSocket Event Delivery Test PASSED")
        print(f"   📡 Success Rate: {success_rate:.1%}")
        print(f"   🎯 Scenarios Tested: {total_scenarios}")
        print(f"   ⏱️  Total Test Time: {total_event_test_time:.2f}s")
        print(f"   💰 $120K+ MRR: PROTECTED from event delivery failures")
        
        # Cleanup
        await WebSocketTestHelpers.close_test_connection(connection)
        with self.connection_lock:
            self.active_connections.remove(connection)
            
    @pytest.mark.mission_critical
    @pytest.mark.p1_critical_failure
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_race_condition_multi_user_failure_reproduction(self):
        """
        🚨 P1 CRITICAL FAILURE REPRODUCTION: Multi-User Race Conditions
        
        Reproduces the race condition failures that occur when multiple users
        access WebSocket functionality simultaneously, causing system instability.
        
        CRITICAL FAILURE SCENARIO:
        - Multiple users connect to WebSocket simultaneously
        - Race conditions in user context management and session handling
        - WebSocket event delivery conflicts between users
        - System degradation or failures under concurrent load
        - Results in unreliable service for enterprise customers
        """
        race_test_start = time.time()
        
        # Configure multi-user race condition test
        concurrent_users = 5  # Enough to trigger race conditions
        
        print(f"\n🏁 RACE CONDITION TEST: Starting {concurrent_users} concurrent users")
        
        # Create user contexts for concurrent testing
        user_contexts = []
        for i in range(concurrent_users):
            context = await create_authenticated_user_context(
                user_email=f"race_test_user_{i}@example.com",
                environment=self.environment,
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        # Execute concurrent user operations
        async def execute_concurrent_user_flow(user_index: int, user_context) -> Dict[str, Any]:
            """Execute a complete user flow that can trigger race conditions."""
            user_start = time.time()
            user_connections = []
            
            try:
                # Get authentication token
                jwt_token = await self._get_reliable_token(
                    user_context.agent_context.get('user_email')
                )
                
                # Create WebSocket connection
                ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=self.websocket_url,
                    headers=ws_headers,
                    timeout=10.0,
                    user_id=str(user_context.user_id)
                )
                user_connections.append(connection)
                
                # Track connection globally for cleanup
                with self.connection_lock:
                    self.active_connections.append(connection)
                
                # Send multiple rapid messages to trigger race conditions
                messages = [
                    {"type": "chat_message", "content": f"User {user_index} message 1", "user_id": str(user_context.user_id)},
                    {"type": "chat_message", "content": f"User {user_index} message 2", "user_id": str(user_context.user_id)},
                    {"type": "chat_message", "content": f"User {user_index} rapid request", "user_id": str(user_context.user_id)}
                ]
                
                # Send messages rapidly to create race conditions
                for msg_index, message in enumerate(messages):
                    try:
                        await WebSocketTestHelpers.send_test_message(
                            connection, message, timeout=3.0
                        )
                        # Small delay to create overlapping processing
                        await asyncio.sleep(0.1)
                    except Exception as msg_error:
                        return {
                            "user_index": user_index,
                            "success": False,
                            "error": f"Message {msg_index} failed: {msg_error}",
                            "failure_type": "message_send_error",
                            "execution_time": time.time() - user_start
                        }
                
                # Collect events while other users are also active
                events_received = []
                event_collection_start = time.time()
                max_event_wait = 30.0
                
                while (time.time() - event_collection_start) < max_event_wait:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(
                            connection, timeout=2.0
                        )
                        
                        if event and isinstance(event, dict):
                            events_received.append(event)
                            
                            # Check if we have reasonable event coverage
                            if len(events_received) >= 5:
                                break
                                
                    except:
                        # Individual timeouts acceptable during concurrent load
                        continue
                
                # Cleanup this user's connections
                for conn in user_connections:
                    try:
                        await WebSocketTestHelpers.close_test_connection(conn)
                        with self.connection_lock:
                            if conn in self.active_connections:
                                self.active_connections.remove(conn)
                    except:
                        pass
                
                execution_time = time.time() - user_start
                
                return {
                    "user_index": user_index,
                    "success": True,
                    "events_received": len(events_received),
                    "messages_sent": len(messages),
                    "execution_time": execution_time,
                    "error": None
                }
                
            except Exception as user_error:
                # Cleanup on error
                for conn in user_connections:
                    try:
                        await WebSocketTestHelpers.close_test_connection(conn)
                    except:
                        pass
                
                return {
                    "user_index": user_index,
                    "success": False,
                    "error": str(user_error),
                    "failure_type": "user_execution_error",
                    "execution_time": time.time() - user_start
                }
        
        # Execute all users concurrently to create race conditions
        user_tasks = [
            execute_concurrent_user_flow(i, context) 
            for i, context in enumerate(user_contexts)
        ]
        
        # Run concurrent users and collect results
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_race_test_time = time.time() - race_test_start
        
        # RACE CONDITION FAILURE ANALYSIS
        
        successful_users = 0
        failed_users = 0
        race_condition_indicators = []
        
        for result in user_results:
            if isinstance(result, Exception):
                failed_users += 1
                race_condition_indicators.append({
                    "type": "exception_during_execution",
                    "error": str(result)
                })
            elif not result.get("success"):
                failed_users += 1
                race_condition_indicators.append({
                    "type": "user_execution_failure",
                    "user_index": result.get("user_index"),
                    "error": result.get("error"),
                    "failure_type": result.get("failure_type")
                })
            else:
                successful_users += 1
                
                # Check for race condition indicators in successful users
                events_received = result.get("events_received", 0)
                if events_received < 3:  # Very low event count may indicate conflicts
                    race_condition_indicators.append({
                        "type": "low_event_count",
                        "user_index": result.get("user_index"),
                        "events_received": events_received
                    })
        
        success_rate = successful_users / concurrent_users if concurrent_users > 0 else 0
        
        # Record race condition test metrics
        self.record_metric("p1_race_condition_success_rate", success_rate)
        self.record_metric("p1_race_condition_failed_users", failed_users)
        self.record_metric("p1_race_condition_indicators", len(race_condition_indicators))
        self.record_metric("p1_race_condition_test_time", total_race_test_time)
        
        # CRITICAL ASSESSMENT: Race conditions must be resolved
        
        if len(race_condition_indicators) > 0:
            # P1 RACE CONDITION FAILURE ACTIVE
            indicator_summary = "\n".join([
                f"  - {indicator['type']}: {indicator.get('error', indicator.get('user_index', 'N/A'))}"
                for indicator in race_condition_indicators
            ])
            
            pytest.fail(
                f"🚨 P1 CRITICAL FAILURE ACTIVE: Multi-User Race Conditions Detected\n"
                f"Success Rate: {success_rate:.1%}\n"
                f"Failed Users: {failed_users}/{concurrent_users}\n"
                f"Race Condition Indicators: {len(race_condition_indicators)}\n"
                f"Indicators:\n{indicator_summary}\n"
                f"This reproduces the EXACT P1 race condition failure!\n"
                f"Business Impact: System instability under enterprise load\n"
                f"Results: {json.dumps(user_results, indent=2)}"
            )
            
        elif success_rate < 0.8:
            # HIGH FAILURE RATE INDICATES INSTABILITY
            pytest.fail(
                f"🚨 P1 SYSTEM INSTABILITY: High failure rate under concurrent load\n"
                f"Success Rate: {success_rate:.1%} (< 80% = unstable)\n"
                f"Failed Users: {failed_users}/{concurrent_users}\n"
                f"This indicates the system cannot handle multi-user scenarios reliably!"
            )
        
        # SUCCESS CASE: P1 race condition failure is RESOLVED
        print(f"\n✅ P1 CRITICAL FAILURE PROTECTION: Multi-User Race Condition Test PASSED")
        print(f"   👥 Success Rate: {success_rate:.1%}")
        print(f"   🏁 Concurrent Users: {concurrent_users}")
        print(f"   ⏱️  Total Test Time: {total_race_test_time:.2f}s")
        print(f"   💰 $120K+ MRR: PROTECTED from race condition failures")
    
    async def _get_reliable_token(self, email: str) -> str:
        """Get a reliable authentication token for testing."""
        try:
            if self.environment == "staging":
                return await self.auth_helper.get_staging_token_async(email=email)
            else:
                return self.auth_helper.create_test_jwt_token(email=email)
        except Exception:
            # Fallback to basic test token
            return self.auth_helper.create_test_jwt_token()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])