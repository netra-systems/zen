"""
E2E GCP Staging WebSocket Race Condition Tests for GitHub Issue #111

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Protect $120K+ MRR by ensuring WebSocket stability
- Value Impact: Prevent 20% concurrent load failures causing chat outages
- Strategic Impact: Eliminate 1011 errors that break core chat functionality

CRITICAL: These tests reproduce the exact race conditions causing failures in GCP staging.
They MUST fail initially to prove they capture the actual race condition issues.
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
import aiohttp
import websockets

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.base_e2e_test import BaseE2ETest

logger = logging.getLogger(__name__)


class TestWebSocketRaceConditionsStaging(BaseE2ETest):
    """
    E2E tests that reproduce WebSocket race conditions in GCP staging environment.
    
    CRITICAL: These tests are designed to FAIL initially to prove they reproduce
    the race conditions causing backend 1011 errors and 20% concurrent load failures.
    """

    @pytest.fixture(autouse=True)
    async def setup_staging_auth(self):
        """Set up staging authentication for all tests."""
        self.auth_helper = E2EWebSocketAuthHelper(environment="staging")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    @pytest.mark.mission_critical
    async def test_concurrent_connection_storm_triggers_1011_errors(self):
        """
        Test concurrent connection storms to reproduce backend 1011 errors.
        
        EXPECTED RESULT: Should FAIL with 1011 errors to prove race condition reproduction.
        This test simulates the exact scenario causing failures in staging.
        """
        # Create multiple authenticated users for concurrent connections
        user_contexts = []
        for i in range(10):  # 10 concurrent users to trigger race conditions
            user_email = f"race_test_user_{i}_{int(time.time())}@example.com"
            context = await create_authenticated_user_context(
                user_email=user_email,
                environment="staging",
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        # Track connection failures and timing
        connection_results = []
        start_time = time.time()
        
        async def attempt_websocket_connection(user_context, user_index):
            """Attempt WebSocket connection and track results."""
            try:
                # Get staging token for this user
                token = await self.websocket_auth_helper.get_staging_token_async(
                    email=user_context.agent_context['user_email']
                )
                
                # Create WebSocket connection with staging-specific timeout
                connection_start = time.time()
                websocket, connection_info = await self.auth_helper.create_websocket_connection(
                    token=token,
                    timeout=15.0,  # GCP Cloud Run limit
                    max_retries=1   # Quick failure to capture race conditions
                )
                connection_duration = time.time() - connection_start
                
                # Send test message to verify connection works
                test_message = {
                    "type": "ping",
                    "user_id": str(user_context.user_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_id": f"race_test_{user_index}"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response with short timeout to catch timing issues
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    success = True
                    error = None
                except asyncio.TimeoutError:
                    success = False
                    error = "Response timeout - possible race condition"
                    response_data = None
                
                await websocket.close()
                
                return {
                    "user_index": user_index,
                    "success": success,
                    "connection_duration": connection_duration,
                    "error": error,
                    "response_received": response_data is not None,
                    "connection_info": connection_info
                }
                
            except Exception as e:
                connection_duration = time.time() - connection_start
                return {
                    "user_index": user_index,
                    "success": False,
                    "connection_duration": connection_duration,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "response_received": False,
                    "connection_info": None
                }
        
        # Execute concurrent connections to trigger race conditions
        connection_tasks = [
            attempt_websocket_connection(context, i) 
            for i, context in enumerate(user_contexts)
        ]
        
        # Run all connections simultaneously to maximize race condition probability
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Analyze results to detect race conditions
        successful_connections = sum(1 for r in connection_results if isinstance(r, dict) and r.get("success", False))
        failed_connections = len(connection_results) - successful_connections
        failure_rate = failed_connections / len(connection_results)
        
        # Detect specific race condition patterns
        race_condition_indicators = {
            "1011_errors": sum(1 for r in connection_results if isinstance(r, dict) and "1011" in str(r.get("error", ""))),
            "accept_errors": sum(1 for r in connection_results if isinstance(r, dict) and "accept" in str(r.get("error", "")).lower()),
            "timeout_errors": sum(1 for r in connection_results if isinstance(r, dict) and "timeout" in str(r.get("error", "")).lower()),
            "connection_refused": sum(1 for r in connection_results if isinstance(r, dict) and "refused" in str(r.get("error", "")).lower()),
            "timing_failures": sum(1 for r in connection_results if isinstance(r, dict) and r.get("connection_duration", 0) > 10.0)
        }
        
        # Log detailed results for analysis
        print(f"\n SEARCH:  RACE CONDITION TEST RESULTS:")
        print(f" CHART:  Total connections attempted: {len(connection_results)}")
        print(f" PASS:  Successful connections: {successful_connections}")
        print(f" FAIL:  Failed connections: {failed_connections}")
        print(f"[U+1F4C8] Failure rate: {failure_rate:.1%}")
        print(f"[U+23F1][U+FE0F]  Total test duration: {total_duration:.2f}s")
        print(f"\n ALERT:  Race Condition Indicators:")
        for indicator, count in race_condition_indicators.items():
            if count > 0:
                print(f"   {indicator}: {count} occurrences")
        
        # Log individual connection results for debugging
        print(f"\n[U+1F4CB] Individual Connection Results:")
        for i, result in enumerate(connection_results):
            if isinstance(result, dict):
                status = " PASS:  SUCCESS" if result.get("success") else " FAIL:  FAILED"
                duration = result.get("connection_duration", 0)
                error = result.get("error", "None")
                print(f"   User {i}: {status} ({duration:.2f}s) - {error}")
        
        # CRITICAL: This test is designed to FAIL to prove race condition reproduction
        # If we're seeing the expected race condition patterns, the test "succeeds" at reproducing them
        race_conditions_detected = any(count > 0 for count in race_condition_indicators.values())
        
        if race_conditions_detected:
            # Log that we successfully reproduced the race conditions
            print(f"\n PASS:  RACE CONDITIONS SUCCESSFULLY REPRODUCED:")
            print(f"   This test proves the WebSocket race conditions exist in staging")
            print(f"   Failure patterns match those reported in GitHub Issue #111")
            
            # Create detailed failure analysis
            failure_analysis = {
                "race_conditions_detected": True,
                "failure_rate": failure_rate,
                "race_condition_indicators": race_condition_indicators,
                "total_duration": total_duration,
                "connection_results": connection_results,
                "test_timestamp": datetime.now(timezone.utc).isoformat(),
                "github_issue": "#111",
                "expected_outcome": "FAILURE_TO_REPRODUCE_RACE_CONDITIONS"
            }
            
            # This assertion should FAIL to indicate race conditions were found
            assert False, (
                f" ALERT:  RACE CONDITIONS DETECTED IN STAGING (Expected for Issue #111):\n"
                f"Failure Rate: {failure_rate:.1%} (Target: <5%)\n"
                f"1011 Errors: {race_condition_indicators['1011_errors']}\n"
                f"Accept Errors: {race_condition_indicators['accept_errors']}\n"
                f"Timeout Errors: {race_condition_indicators['timeout_errors']}\n"
                f"This proves the race conditions exist and need fixing."
            )
        else:
            # If no race conditions detected, that's unexpected
            print(f"\n WARNING: [U+FE0F]  NO RACE CONDITIONS DETECTED:")
            print(f"   This may indicate the race conditions have been fixed")
            print(f"   Or this test needs refinement to trigger them")
            
            # This would be surprising given the reported issues
            pytest.fail(
                f"No race conditions detected. Expected 1011 errors and timing failures. "
                f"Either race conditions are fixed or test needs refinement."
            )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_gcp_cloud_run_startup_timing_edge_cases(self):
        """
        Test GCP Cloud Run startup timing edge cases that cause race conditions.
        
        EXPECTED RESULT: Should detect timing gaps between network handshake and app readiness.
        """
        # Create authenticated user for timing tests
        user_context = await create_authenticated_user_context(
            user_email=f"timing_test_{int(time.time())}@example.com",
            environment="staging",
            websocket_enabled=True
        )
        
        # Get staging token
        token = await self.websocket_auth_helper.get_staging_token_async(
            email=user_context.agent_context['user_email']
        )
        
        # Test rapid connection attempts to catch startup timing gaps
        timing_results = []
        
        for attempt in range(5):
            try:
                # Measure different phases of connection
                phase_times = {}
                
                # Phase 1: Network handshake timing
                network_start = time.time()
                websocket, connection_info = await self.auth_helper.create_websocket_connection(
                    token=token,
                    timeout=20.0,  # Longer timeout to measure timing
                    max_retries=0   # No retries to get raw timing
                )
                phase_times['network_handshake'] = time.time() - network_start
                
                # Phase 2: First message timing (tests app readiness)
                app_readiness_start = time.time()
                test_message = {
                    "type": "connection_test",
                    "phase": "app_readiness",
                    "attempt": attempt,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response to confirm app is ready
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    phase_times['app_response'] = time.time() - app_readiness_start
                    app_ready = True
                except asyncio.TimeoutError:
                    phase_times['app_response'] = time.time() - app_readiness_start
                    app_ready = False
                
                await websocket.close()
                
                timing_results.append({
                    "attempt": attempt,
                    "success": app_ready,
                    "network_handshake_time": phase_times['network_handshake'],
                    "app_response_time": phase_times['app_response'],
                    "total_time": phase_times['network_handshake'] + phase_times['app_response'],
                    "timing_gap": phase_times['app_response'] - phase_times['network_handshake'],
                    "connection_info": connection_info
                })
                
            except Exception as e:
                timing_results.append({
                    "attempt": attempt,
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
            
            # Small delay between attempts
            await asyncio.sleep(1.0)
        
        # Analyze timing patterns for race conditions
        successful_attempts = [r for r in timing_results if r.get("success", False)]
        avg_network_time = sum(r.get("network_handshake_time", 0) for r in successful_attempts) / len(successful_attempts) if successful_attempts else 0
        avg_app_time = sum(r.get("app_response_time", 0) for r in successful_attempts) / len(successful_attempts) if successful_attempts else 0
        
        timing_gaps = [r.get("timing_gap", 0) for r in successful_attempts if r.get("timing_gap", 0) > 0]
        max_timing_gap = max(timing_gaps) if timing_gaps else 0
        
        print(f"\n[U+23F1][U+FE0F]  GCP CLOUD RUN TIMING ANALYSIS:")
        print(f" CHART:  Successful attempts: {len(successful_attempts)}/{len(timing_results)}")
        print(f"[U+1F310] Average network handshake time: {avg_network_time:.2f}s")
        print(f"[U+1F4F1] Average app response time: {avg_app_time:.2f}s")
        print(f" LIGHTNING:  Maximum timing gap: {max_timing_gap:.2f}s")
        
        # Print individual timing results
        print(f"\n[U+1F4CB] Individual Timing Results:")
        for result in timing_results:
            if result.get("success"):
                net_time = result.get("network_handshake_time", 0)
                app_time = result.get("app_response_time", 0)
                gap = result.get("timing_gap", 0)
                print(f"   Attempt {result['attempt']}: Network={net_time:.2f}s, App={app_time:.2f}s, Gap={gap:.2f}s")
            else:
                print(f"   Attempt {result['attempt']}: FAILED - {result.get('error', 'Unknown error')}")
        
        # Check for timing issues that indicate race conditions
        timing_issues_detected = (
            max_timing_gap > 5.0 or  # Large gap between network and app readiness
            avg_app_time > 10.0 or   # Slow app response indicates startup issues
            len(successful_attempts) < len(timing_results)  # Some attempts failed
        )
        
        if timing_issues_detected:
            print(f"\n ALERT:  TIMING ISSUES DETECTED:")
            print(f"   Large timing gaps suggest GCP Cloud Run startup race conditions")
            print(f"   These gaps can cause 'accept' errors when network is ready but app isn't")
            
            # This indicates the race condition exists
            assert False, (
                f"GCP Cloud Run timing race conditions detected:\n"
                f"Max timing gap: {max_timing_gap:.2f}s (should be <1s)\n"
                f"Average app response: {avg_app_time:.2f}s (should be <5s)\n"
                f"Failed attempts: {len(timing_results) - len(successful_attempts)}\n"
                f"This proves startup timing race conditions exist."
            )
        else:
            print(f"\n PASS:  NO TIMING ISSUES DETECTED:")
            print(f"   GCP Cloud Run startup timing appears stable")
            print(f"   Race conditions may have been resolved")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_service_initialization_race_conditions(self):
        """
        Test service initialization race conditions that cause WebSocket failures.
        
        EXPECTED RESULT: Should detect initialization gaps causing service readiness failures.
        """
        # Create authenticated user for service initialization tests
        user_context = await create_authenticated_user_context(
            user_email=f"service_init_test_{int(time.time())}@example.com",
            environment="staging",
            websocket_enabled=True
        )
        
        # Get staging token
        token = await self.websocket_auth_helper.get_staging_token_async(
            email=user_context.agent_context['user_email']
        )
        
        # Test service readiness validation during connection
        service_readiness_results = []
        
        for attempt in range(3):
            try:
                # Create connection with detailed timing
                connection_start = time.time()
                
                # Get WebSocket headers with E2E detection
                headers = self.auth_helper.get_websocket_headers(token)
                
                # Attempt connection with service readiness monitoring
                websocket = await websockets.connect(
                    self.auth_helper.config.websocket_url,
                    extra_headers=headers,
                    open_timeout=15.0,
                    ping_interval=None,  # Disable during testing
                    ping_timeout=None
                )
                
                connection_time = time.time() - connection_start
                
                # Test service readiness by sending service-specific messages
                readiness_tests = [
                    {"type": "service_health_check", "service": "websocket"},
                    {"type": "auth_validation_test", "token_validation": True},
                    {"type": "message_routing_test", "routing_check": True}
                ]
                
                service_responses = []
                for test_msg in readiness_tests:
                    test_msg.update({
                        "attempt": attempt,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": str(user_context.user_id)
                    })
                    
                    try:
                        # Send test message
                        send_start = time.time()
                        await websocket.send(json.dumps(test_msg))
                        send_time = time.time() - send_start
                        
                        # Wait for response
                        response_start = time.time()
                        response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                        response_time = time.time() - response_start
                        
                        response_data = json.loads(response)
                        service_responses.append({
                            "test_type": test_msg["type"],
                            "success": True,
                            "send_time": send_time,
                            "response_time": response_time,
                            "total_time": send_time + response_time,
                            "response_data": response_data
                        })
                        
                    except asyncio.TimeoutError:
                        service_responses.append({
                            "test_type": test_msg["type"],
                            "success": False,
                            "error": "Response timeout - service may not be ready",
                            "send_time": send_time if 'send_time' in locals() else 0,
                            "response_time": 8.0  # Timeout duration
                        })
                    except Exception as e:
                        service_responses.append({
                            "test_type": test_msg["type"],
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__
                        })
                
                await websocket.close()
                
                service_readiness_results.append({
                    "attempt": attempt,
                    "connection_success": True,
                    "connection_time": connection_time,
                    "service_responses": service_responses,
                    "total_response_time": sum(r.get("response_time", 0) for r in service_responses),
                    "successful_services": sum(1 for r in service_responses if r.get("success", False)),
                    "failed_services": sum(1 for r in service_responses if not r.get("success", False))
                })
                
            except Exception as e:
                connection_time = time.time() - connection_start
                service_readiness_results.append({
                    "attempt": attempt,
                    "connection_success": False,
                    "connection_time": connection_time,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "service_responses": [],
                    "successful_services": 0,
                    "failed_services": 3  # All tests failed due to connection failure
                })
            
            # Delay between attempts
            await asyncio.sleep(2.0)
        
        # Analyze service initialization race conditions
        successful_connections = sum(1 for r in service_readiness_results if r.get("connection_success", False))
        total_service_failures = sum(r.get("failed_services", 0) for r in service_readiness_results)
        avg_connection_time = sum(r.get("connection_time", 0) for r in service_readiness_results) / len(service_readiness_results)
        
        print(f"\n[U+1F527] SERVICE INITIALIZATION ANALYSIS:")
        print(f" CHART:  Successful connections: {successful_connections}/{len(service_readiness_results)}")
        print(f" LIGHTNING:  Average connection time: {avg_connection_time:.2f}s")
        print(f" FAIL:  Total service failures: {total_service_failures}")
        
        # Print detailed service readiness results
        print(f"\n[U+1F4CB] Service Readiness Results:")
        for result in service_readiness_results:
            attempt = result["attempt"]
            if result.get("connection_success"):
                successful = result.get("successful_services", 0)
                failed = result.get("failed_services", 0)
                conn_time = result.get("connection_time", 0)
                print(f"   Attempt {attempt}: Connected in {conn_time:.2f}s, Services: {successful} PASS: /{failed} FAIL: ")
                
                for response in result.get("service_responses", []):
                    test_type = response.get("test_type", "unknown")
                    success = " PASS: " if response.get("success") else " FAIL: "
                    resp_time = response.get("response_time", 0)
                    error = response.get("error", "")
                    print(f"      {test_type}: {success} ({resp_time:.2f}s) {error}")
            else:
                error = result.get("error", "Unknown error")
                print(f"   Attempt {attempt}: CONNECTION FAILED - {error}")
        
        # Check for service initialization race conditions
        service_race_conditions = (
            total_service_failures > 0 or        # Any service failures indicate race conditions
            avg_connection_time > 10.0 or        # Slow connections suggest initialization issues
            successful_connections < len(service_readiness_results)  # Connection failures
        )
        
        if service_race_conditions:
            print(f"\n ALERT:  SERVICE INITIALIZATION RACE CONDITIONS DETECTED:")
            print(f"   Service failures suggest initialization timing issues")
            print(f"   These can cause WebSocket functionality to fail even when connected")
            
            # This indicates race conditions in service initialization
            assert False, (
                f"Service initialization race conditions detected:\n"
                f"Service failures: {total_service_failures} (should be 0)\n"
                f"Connection success rate: {successful_connections}/{len(service_readiness_results)}\n"
                f"Average connection time: {avg_connection_time:.2f}s (should be <5s)\n"
                f"This proves service initialization race conditions exist."
            )
        else:
            print(f"\n PASS:  SERVICE INITIALIZATION APPEARS STABLE:")
            print(f"   All services responded properly during connection tests")
            print(f"   Race conditions may have been resolved")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_heartbeat_timeout_systematic_failures(self):
        """
        Test systematic heartbeat timeouts that occur every 2 minutes in staging.
        
        EXPECTED RESULT: Should detect heartbeat timing misalignment with GCP infrastructure.
        """
        # Create authenticated user for heartbeat testing
        user_context = await create_authenticated_user_context(
            user_email=f"heartbeat_test_{int(time.time())}@example.com",
            environment="staging",
            websocket_enabled=True
        )
        
        # Get staging token
        token = await self.websocket_auth_helper.get_staging_token_async(
            email=user_context.agent_context['user_email']
        )
        
        # Create long-running connection to test heartbeat behavior
        print(f"\n[U+1F493] TESTING HEARTBEAT BEHAVIOR (2 minute duration):")
        print(f"   Monitoring for systematic heartbeat failures every ~2 minutes")
        
        try:
            # Create connection with heartbeat monitoring
            websocket = await websockets.connect(
                self.auth_helper.config.websocket_url,
                extra_headers=self.auth_helper.get_websocket_headers(token),
                open_timeout=15.0,
                ping_interval=30,  # 30-second ping interval
                ping_timeout=10,   # 10-second ping timeout
                close_timeout=5
            )
            
            connection_start = time.time()
            heartbeat_events = []
            last_ping_time = connection_start
            
            # Monitor connection for 2.5 minutes to catch heartbeat patterns
            test_duration = 150  # 2.5 minutes to catch 2-minute pattern
            end_time = connection_start + test_duration
            
            print(f"   Connection established, monitoring for {test_duration}s...")
            
            while time.time() < end_time:
                try:
                    # Send periodic test messages to keep connection active
                    current_time = time.time()
                    if current_time - last_ping_time >= 30:  # Every 30 seconds
                        test_message = {
                            "type": "heartbeat_test",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "elapsed_time": current_time - connection_start,
                            "ping_number": len(heartbeat_events) + 1
                        }
                        
                        ping_start = time.time()
                        await websocket.send(json.dumps(test_message))
                        
                        # Wait for response to measure round-trip time
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            ping_duration = time.time() - ping_start
                            
                            heartbeat_events.append({
                                "ping_number": len(heartbeat_events) + 1,
                                "timestamp": current_time,
                                "elapsed_time": current_time - connection_start,
                                "ping_duration": ping_duration,
                                "success": True,
                                "response_received": True
                            })
                            
                            print(f"   Ping {len(heartbeat_events)}:  PASS:  ({ping_duration:.2f}s) at {current_time - connection_start:.0f}s")
                            
                        except asyncio.TimeoutError:
                            ping_duration = time.time() - ping_start
                            heartbeat_events.append({
                                "ping_number": len(heartbeat_events) + 1,
                                "timestamp": current_time,
                                "elapsed_time": current_time - connection_start,
                                "ping_duration": ping_duration,
                                "success": False,
                                "error": "Response timeout",
                                "response_received": False
                            })
                            
                            print(f"   Ping {len(heartbeat_events)}:  FAIL:  TIMEOUT at {current_time - connection_start:.0f}s")
                        
                        last_ping_time = current_time
                    
                    # Small sleep to prevent busy loop
                    await asyncio.sleep(1.0)
                    
                except websockets.exceptions.ConnectionClosed:
                    print(f"    FAIL:  Connection closed unexpectedly at {time.time() - connection_start:.0f}s")
                    break
                except Exception as e:
                    print(f"    FAIL:  Connection error at {time.time() - connection_start:.0f}s: {e}")
                    break
            
            # Close connection
            try:
                await websocket.close()
            except:
                pass  # Connection may already be closed
            
            total_test_time = time.time() - connection_start
            
        except Exception as e:
            print(f"    FAIL:  Failed to establish heartbeat test connection: {e}")
            heartbeat_events = []
            total_test_time = 0
        
        # Analyze heartbeat patterns for systematic failures
        successful_pings = sum(1 for event in heartbeat_events if event.get("success", False))
        failed_pings = len(heartbeat_events) - successful_pings
        failure_rate = failed_pings / len(heartbeat_events) if heartbeat_events else 1.0
        
        # Check for 2-minute pattern in failures
        failure_times = [event["elapsed_time"] for event in heartbeat_events if not event.get("success", False)]
        two_minute_failures = sum(1 for t in failure_times if 110 <= t <= 130)  # Around 2 minutes ( +/- 10s)
        
        print(f"\n[U+1F493] HEARTBEAT ANALYSIS RESULTS:")
        print(f" CHART:  Total pings attempted: {len(heartbeat_events)}")
        print(f" PASS:  Successful pings: {successful_pings}")
        print(f" FAIL:  Failed pings: {failed_pings}")
        print(f"[U+1F4C8] Failure rate: {failure_rate:.1%}")
        print(f"[U+23F1][U+FE0F]  Total test duration: {total_test_time:.1f}s")
        print(f" TARGET:  Failures around 2-minute mark: {two_minute_failures}")
        
        if failure_times:
            print(f"\n[U+1F4CB] Failure Timing Pattern:")
            for i, fail_time in enumerate(failure_times):
                print(f"   Failure {i+1}: {fail_time:.0f}s")
        
        # Check for systematic heartbeat issues
        heartbeat_issues_detected = (
            failure_rate > 0.2 or          # More than 20% failure rate
            two_minute_failures > 0 or     # Failures specifically around 2-minute mark
            total_test_time < test_duration - 10  # Connection died early
        )
        
        if heartbeat_issues_detected:
            print(f"\n ALERT:  SYSTEMATIC HEARTBEAT FAILURES DETECTED:")
            print(f"   Heartbeat failures indicate GCP infrastructure timing misalignment")
            print(f"   2-minute pattern matches reported systematic failures")
            
            # This indicates heartbeat race conditions
            assert False, (
                f"Systematic heartbeat failures detected:\n"
                f"Failure rate: {failure_rate:.1%} (should be <5%)\n"
                f"2-minute pattern failures: {two_minute_failures} (should be 0)\n"
                f"Test duration: {total_test_time:.1f}s (target: {test_duration}s)\n"
                f"This proves heartbeat timing race conditions exist."
            )
        else:
            print(f"\n PASS:  HEARTBEAT BEHAVIOR APPEARS STABLE:")
            print(f"   No systematic failures detected")
            print(f"   Heartbeat race conditions may have been resolved")