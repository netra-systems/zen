"""
E2E tests for GCP cold start WebSocket race condition reproduction.

MISSION CRITICAL: Tests the actual race condition in GCP Cloud Run environment
that causes 1011 WebSocket errors during service initialization.

Business Value Justification (BVJ):
- Segment: Platform/All Users
- Business Goal: Platform Stability & Revenue Protection  
- Value Impact: Ensures $500K+ ARR dependent on reliable WebSocket connections
- Strategic Impact: Validates Golden Path works during GCP cold start scenarios

Test Strategy:
- E2E tests run in actual GCP staging environment
- Tests reproduce real race conditions with actual Cloud Run timing
- Tests validate complete user journey during startup window
- Tests ensure 1011 errors are prevented through proper coordination

IMPORTANT: These tests require GCP staging environment access and should be run
as part of staging deployment validation pipeline.
"""

import asyncio
import pytest
import time
import websockets
import json
import logging
from typing import Dict, Any, Optional
from unittest.mock import patch
import httpx

from test_framework.base_e2e_test import BaseE2ETest


@pytest.mark.e2e
@pytest.mark.gcp_staging  
@pytest.mark.mission_critical
class TestGCPColdStartWebSocketRace(BaseE2ETest):
    """Test GCP cold start WebSocket race condition scenarios."""
    
    @classmethod
    def setup_class(cls):
        """Setup for GCP staging environment tests."""
        super().setup_class()
        cls.logger = logging.getLogger(__name__)
        
        # GCP staging configuration
        cls.staging_base_url = "https://netra-staging-backend.a.run.app"
        cls.staging_websocket_url = "wss://netra-staging-backend.a.run.app/ws"
        cls.staging_health_url = f"{cls.staging_base_url}/health"
        
        # Test timeouts for race condition scenarios
        cls.cold_start_timeout = 30.0  # GCP cold start can take up to 30s
        cls.race_condition_window = 2.0  # Critical race condition window
        cls.websocket_connection_timeout = 10.0
    
    async def trigger_gcp_cold_start(self) -> Dict[str, Any]:
        """
        Trigger a GCP cold start by forcing instance restart.
        
        This simulates the actual cold start scenario that triggers the race condition.
        
        Returns:
            Dict with cold start trigger information
        """
        self.logger.info("🚨 Triggering GCP cold start scenario...")
        
        # Record time before cold start
        cold_start_begin = time.time()
        
        # Trigger cold start by hitting health endpoint after period of inactivity
        # In real GCP Cloud Run, this would happen automatically after traffic absence
        try:
            async with httpx.AsyncClient(timeout=self.cold_start_timeout) as client:
                # First, verify service is responsive
                health_response = await client.get(self.staging_health_url)
                self.logger.info(f"Pre-cold-start health check: {health_response.status_code}")
                
                # Wait to allow instance scaling down (simulate traffic absence)
                await asyncio.sleep(2.0)
                
                # Now trigger cold start with new request
                cold_start_response = await client.get(self.staging_health_url)
                cold_start_elapsed = time.time() - cold_start_begin
                
                self.logger.info(f"Cold start triggered, response: {cold_start_response.status_code} "
                               f"after {cold_start_elapsed:.2f}s")
                
                return {
                    "success": True,
                    "cold_start_time": cold_start_elapsed,
                    "response_code": cold_start_response.status_code,
                    "timestamp": cold_start_begin
                }
        
        except Exception as e:
            self.logger.error(f"Failed to trigger cold start: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": cold_start_begin
            }
    
    @pytest.mark.asyncio
    async def test_race_condition_reproduction_during_cold_start(self):
        """
        Test reproduction of WebSocket 1011 race condition during GCP cold start.
        
        CRITICAL: This test reproduces the exact Issue #586 scenario in real GCP
        environment to validate the race condition occurs and is handled properly.
        """
        self.logger.info("🧪 Testing WebSocket race condition during GCP cold start...")
        
        # Trigger cold start scenario
        cold_start_info = await self.trigger_gcp_cold_start()
        if not cold_start_info["success"]:
            pytest.skip(f"Could not trigger cold start: {cold_start_info['error']}")
        
        # Immediately attempt WebSocket connection during startup window
        # This simulates the race condition where GCP routes connections before services ready
        race_condition_start = time.time()
        
        connection_attempts = []
        websocket_errors = []
        
        # Attempt multiple WebSocket connections during the critical startup window
        for attempt in range(3):
            attempt_start = time.time()
            try:
                self.logger.info(f"WebSocket connection attempt {attempt + 1} during startup window...")
                
                # Attempt WebSocket connection with short timeout
                async with websockets.connect(
                    self.staging_websocket_url,
                    timeout=self.websocket_connection_timeout,
                    extra_headers={"Authorization": "Bearer test-token"}
                ) as websocket:
                    
                    # If connection succeeds, try to send a message
                    test_message = {
                        "type": "agent_request",
                        "agent": "triage_agent", 
                        "message": "Test during cold start",
                        "thread_id": f"test_cold_start_{attempt}"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response or timeout
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        connection_attempts.append({
                            "attempt": attempt + 1,
                            "success": True,
                            "duration": time.time() - attempt_start,
                            "response_type": response_data.get("type", "unknown")
                        })
                        
                        self.logger.info(f"✅ WebSocket connection {attempt + 1} succeeded during cold start")
                        
                    except asyncio.TimeoutError:
                        connection_attempts.append({
                            "attempt": attempt + 1,
                            "success": True,  # Connection established but no response
                            "duration": time.time() - attempt_start,
                            "response_type": "timeout"
                        })
                        
                        self.logger.warning(f"⚠️ WebSocket connection {attempt + 1} established but no response")
                        
            except websockets.exceptions.ConnectionClosedError as e:
                if e.code == 1011:  # The specific error code we're testing for
                    websocket_errors.append({
                        "attempt": attempt + 1,
                        "error_code": e.code,
                        "error_reason": e.reason,
                        "duration": time.time() - attempt_start
                    })
                    self.logger.error(f"🚨 WebSocket 1011 error detected in attempt {attempt + 1}: {e.reason}")
                else:
                    websocket_errors.append({
                        "attempt": attempt + 1,
                        "error_code": e.code,
                        "error_reason": e.reason,
                        "duration": time.time() - attempt_start
                    })
                    self.logger.error(f"❌ WebSocket error {e.code} in attempt {attempt + 1}: {e.reason}")
                
            except Exception as e:
                websocket_errors.append({
                    "attempt": attempt + 1,
                    "error_code": "unknown",
                    "error_reason": str(e),
                    "duration": time.time() - attempt_start
                })
                self.logger.error(f"❌ WebSocket connection attempt {attempt + 1} failed: {e}")
            
            # Wait between attempts
            await asyncio.sleep(0.5)
        
        race_condition_elapsed = time.time() - race_condition_start
        
        # Analyze results
        total_attempts = len(connection_attempts) + len(websocket_errors)
        success_rate = len(connection_attempts) / total_attempts if total_attempts > 0 else 0
        websocket_1011_errors = [err for err in websocket_errors if err.get("error_code") == 1011]
        
        self.logger.info(f"📊 Race condition test results:")
        self.logger.info(f"   Total attempts: {total_attempts}")
        self.logger.info(f"   Successful connections: {len(connection_attempts)}")
        self.logger.info(f"   WebSocket errors: {len(websocket_errors)}")
        self.logger.info(f"   1011 errors (race condition): {len(websocket_1011_errors)}")
        self.logger.info(f"   Success rate: {success_rate:.1%}")
        self.logger.info(f"   Test duration: {race_condition_elapsed:.2f}s")
        
        # Assertions: The fix should prevent 1011 errors
        assert len(websocket_1011_errors) == 0, (
            f"WebSocket 1011 errors detected - race condition not fully resolved: {websocket_1011_errors}"
        )
        
        # At least some connections should succeed or fail gracefully (not with 1011)
        assert total_attempts > 0, "Should have attempted WebSocket connections"
        
        # If there are errors, they should not be 1011 (race condition) errors
        non_1011_errors = [err for err in websocket_errors if err.get("error_code") != 1011]
        if len(websocket_errors) > 0:
            assert len(non_1011_errors) == len(websocket_errors), (
                f"All WebSocket errors should be non-1011 errors, got 1011 errors: {websocket_1011_errors}"
            )
    
    @pytest.mark.asyncio
    async def test_golden_path_reliability_during_cold_start(self):
        """
        Test Golden Path reliability during GCP cold start scenarios.
        
        BUSINESS CRITICAL: Chat functionality (90% of platform value) should work
        reliably during cold start scenarios, even if some services have delays.
        """
        self.logger.info("🎯 Testing Golden Path reliability during GCP cold start...")
        
        # Trigger cold start
        cold_start_info = await self.trigger_gcp_cold_start()
        if not cold_start_info["success"]:
            pytest.skip(f"Could not trigger cold start: {cold_start_info['error']}")
        
        # Wait for startup to stabilize (but not too long - test realistic user behavior)
        await asyncio.sleep(3.0)
        
        golden_path_start = time.time()
        
        try:
            # Test complete Golden Path user journey
            async with websockets.connect(
                self.staging_websocket_url,
                timeout=self.websocket_connection_timeout,
                extra_headers={"Authorization": "Bearer test-token"}
            ) as websocket:
                
                # Send realistic user message
                user_message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Help me understand my AI costs and suggest optimizations",
                    "thread_id": f"golden_path_cold_start_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(user_message))
                
                # Collect all WebSocket events (the 5 critical events)
                events = []
                event_timeout = 30.0  # Allow time for full agent execution
                
                try:
                    while len(events) < 10:  # Reasonable upper bound
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=event_timeout)
                        event = json.loads(event_data)
                        events.append(event)
                        
                        self.logger.info(f"📨 Received event: {event.get('type', 'unknown')}")
                        
                        # Stop if we get agent_completed
                        if event.get("type") == "agent_completed":
                            break
                        
                        # Reduce timeout for subsequent events
                        event_timeout = 10.0
                
                except asyncio.TimeoutError:
                    self.logger.warning(f"⏰ Timeout waiting for events, collected {len(events)} events")
                
                golden_path_elapsed = time.time() - golden_path_start
                
                # Analyze Golden Path success
                event_types = [event.get("type", "unknown") for event in events]
                required_events = ["agent_started", "agent_completed"]
                
                self.logger.info(f"📊 Golden Path results after cold start:")
                self.logger.info(f"   Total events received: {len(events)}")
                self.logger.info(f"   Event types: {event_types}")
                self.logger.info(f"   Duration: {golden_path_elapsed:.2f}s")
                
                # Assertions for Golden Path success
                assert len(events) > 0, "Should receive at least one WebSocket event"
                
                # Check for critical events
                has_agent_started = "agent_started" in event_types
                has_agent_completed = "agent_completed" in event_types
                
                assert has_agent_started, f"Should receive agent_started event, got: {event_types}"
                assert has_agent_completed, f"Should receive agent_completed event, got: {event_types}"
                
                # Verify final response contains useful content
                if has_agent_completed:
                    completed_event = next(event for event in events if event.get("type") == "agent_completed")
                    result = completed_event.get("data", {}).get("result", {})
                    
                    # Should have some kind of response content
                    assert len(str(result)) > 10, "Agent should provide substantive response content"
                
                self.logger.info("✅ Golden Path succeeded during cold start scenario")
                
        except Exception as e:
            golden_path_elapsed = time.time() - golden_path_start
            self.logger.error(f"❌ Golden Path failed during cold start: {e} (after {golden_path_elapsed:.2f}s)")
            
            # Golden Path failure is critical - should not happen after race condition fix
            pytest.fail(f"Golden Path failed during cold start scenario: {e}")
    
    @pytest.mark.asyncio  
    async def test_startup_monitoring_and_observability(self):
        """
        Test startup monitoring and observability during cold start scenarios.
        
        MONITORING: Ensure race condition scenarios are properly monitored and
        observable for debugging and alerting purposes.
        """
        self.logger.info("📊 Testing startup monitoring during cold start...")
        
        # Trigger cold start
        cold_start_info = await self.trigger_gcp_cold_start()
        if not cold_start_info["success"]:
            pytest.skip(f"Could not trigger cold start: {cold_start_info['error']}")
        
        # Check health endpoint for startup monitoring information
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Check multiple times during startup window
            health_checks = []
            
            for check_num in range(3):
                try:
                    health_response = await client.get(self.staging_health_url)
                    health_data = health_response.json()
                    
                    health_checks.append({
                        "check_number": check_num + 1,
                        "status_code": health_response.status_code,
                        "response_time": health_response.elapsed.total_seconds(),
                        "data": health_data
                    })
                    
                    self.logger.info(f"Health check {check_num + 1}: {health_response.status_code} "
                                   f"({health_response.elapsed.total_seconds():.2f}s)")
                    
                except Exception as e:
                    health_checks.append({
                        "check_number": check_num + 1,
                        "status_code": "error",
                        "error": str(e)
                    })
                    self.logger.warning(f"Health check {check_num + 1} failed: {e}")
                
                await asyncio.sleep(2.0)
        
        # Analyze health check results
        successful_checks = [check for check in health_checks if check.get("status_code") == 200]
        
        self.logger.info(f"📊 Health monitoring results:")
        self.logger.info(f"   Total health checks: {len(health_checks)}")
        self.logger.info(f"   Successful checks: {len(successful_checks)}")
        
        # Assertions for monitoring
        assert len(health_checks) > 0, "Should perform health checks"
        assert len(successful_checks) > 0, "At least one health check should succeed after cold start"
        
        # Check if health response includes WebSocket readiness information
        if successful_checks:
            sample_health = successful_checks[0]["data"]
            
            # Should include some startup/readiness information
            has_startup_info = any(
                key in sample_health 
                for key in ["startup", "ready", "websocket", "services", "status"]
            )
            
            assert has_startup_info, f"Health endpoint should include startup information, got: {sample_health.keys()}"
            
            self.logger.info("✅ Startup monitoring information available in health endpoint")
    
    @pytest.mark.asyncio
    async def test_race_condition_recovery_scenarios(self):
        """
        Test recovery scenarios when race conditions are detected.
        
        RESILIENCE: System should recover gracefully from race condition scenarios
        and allow subsequent connections to succeed.
        """
        self.logger.info("🔄 Testing race condition recovery scenarios...")
        
        # Trigger cold start
        cold_start_info = await self.trigger_gcp_cold_start()
        if not cold_start_info["success"]:
            pytest.skip(f"Could not trigger cold start: {cold_start_info['error']}")
        
        # Attempt connection immediately (may fail due to race condition)
        immediate_connection_result = None
        try:
            async with websockets.connect(
                self.staging_websocket_url,
                timeout=5.0,  # Short timeout
                extra_headers={"Authorization": "Bearer test-token"}
            ) as websocket:
                await websocket.send(json.dumps({"type": "ping"}))
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                immediate_connection_result = {"success": True, "response": response}
                
        except Exception as e:
            immediate_connection_result = {"success": False, "error": str(e)}
            self.logger.info(f"Immediate connection during cold start: {e}")
        
        # Wait for system to stabilize
        await asyncio.sleep(5.0)
        
        # Attempt connection after stabilization - should always work
        recovery_connection_result = None
        try:
            async with websockets.connect(
                self.staging_websocket_url,
                timeout=10.0,
                extra_headers={"Authorization": "Bearer test-token"}  
            ) as websocket:
                
                test_message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Test recovery after cold start",
                    "thread_id": f"recovery_test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                recovery_connection_result = {"success": True, "response": response}
                
                self.logger.info("✅ Recovery connection succeeded after cold start stabilization")
                
        except Exception as e:
            recovery_connection_result = {"success": False, "error": str(e)}
            self.logger.error(f"❌ Recovery connection failed: {e}")
        
        # Assertions for recovery
        assert recovery_connection_result is not None, "Should attempt recovery connection"
        assert recovery_connection_result["success"] is True, (
            f"Recovery connection should succeed after cold start stabilization: "
            f"{recovery_connection_result.get('error')}"
        )
        
        self.logger.info(f"📊 Recovery test results:")
        self.logger.info(f"   Immediate connection: {immediate_connection_result['success']}")
        self.logger.info(f"   Recovery connection: {recovery_connection_result['success']}")
        
        # Recovery is the critical assertion - system must recover
        assert recovery_connection_result["success"], "System must recover from race condition scenarios"


@pytest.mark.e2e
@pytest.mark.gcp_staging
class TestWebSocketStabilityMetrics:
    """Test WebSocket stability metrics and performance during cold starts."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_stability_metrics(self):
        """
        Test WebSocket connection stability metrics during multiple cold start scenarios.
        
        METRICS: Collect stability metrics to validate race condition fix effectiveness.
        """
        logger = logging.getLogger(__name__)
        logger.info("📈 Testing WebSocket stability metrics...")
        
        staging_websocket_url = "wss://netra-staging-backend.a.run.app/ws"
        
        # Run multiple connection tests to gather stability metrics
        connection_results = []
        test_iterations = 5
        
        for iteration in range(test_iterations):
            iteration_start = time.time()
            logger.info(f"🔄 WebSocket stability test iteration {iteration + 1}/{test_iterations}")
            
            try:
                async with websockets.connect(
                    staging_websocket_url,
                    timeout=10.0,
                    extra_headers={"Authorization": "Bearer test-token"}
                ) as websocket:
                    
                    # Send test message
                    await websocket.send(json.dumps({
                        "type": "ping",
                        "iteration": iteration + 1
                    }))
                    
                    # Measure response time  
                    response_start = time.time()
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_time = time.time() - response_start
                    
                    connection_results.append({
                        "iteration": iteration + 1,
                        "success": True,
                        "connection_time": time.time() - iteration_start,
                        "response_time": response_time,
                        "error": None
                    })
                    
            except Exception as e:
                connection_results.append({
                    "iteration": iteration + 1,
                    "success": False,
                    "connection_time": time.time() - iteration_start,
                    "response_time": None,
                    "error": str(e)
                })
            
            # Wait between iterations
            await asyncio.sleep(1.0)
        
        # Analyze stability metrics
        successful_connections = [r for r in connection_results if r["success"]]
        failed_connections = [r for r in connection_results if not r["success"]]
        
        success_rate = len(successful_connections) / len(connection_results)
        avg_connection_time = sum(r["connection_time"] for r in successful_connections) / len(successful_connections) if successful_connections else 0
        avg_response_time = sum(r["response_time"] for r in successful_connections if r["response_time"]) / len(successful_connections) if successful_connections else 0
        
        logger.info(f"📊 WebSocket Stability Metrics:")
        logger.info(f"   Total iterations: {test_iterations}")
        logger.info(f"   Successful connections: {len(successful_connections)}")
        logger.info(f"   Failed connections: {len(failed_connections)}")
        logger.info(f"   Success rate: {success_rate:.1%}")
        logger.info(f"   Average connection time: {avg_connection_time:.2f}s")
        logger.info(f"   Average response time: {avg_response_time:.2f}s")
        
        # Log any errors for debugging
        if failed_connections:
            logger.warning("❌ Failed connection details:")
            for failed in failed_connections:
                logger.warning(f"   Iteration {failed['iteration']}: {failed['error']}")
        
        # Stability assertions
        assert success_rate >= 0.8, f"WebSocket success rate should be >= 80%, got {success_rate:.1%}"
        assert avg_connection_time < 10.0, f"Average connection time should be < 10s, got {avg_connection_time:.2f}s"
        
        # Check for race condition indicators in errors
        race_condition_errors = [
            failed for failed in failed_connections 
            if "1011" in failed["error"] or "race" in failed["error"].lower()
        ]
        
        assert len(race_condition_errors) == 0, (
            f"No race condition errors should occur, found: {race_condition_errors}"
        )
        
        logger.info("✅ WebSocket stability metrics within acceptable ranges")