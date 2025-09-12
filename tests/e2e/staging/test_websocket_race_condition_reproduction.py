"""
E2E Tests for WebSocket Race Condition Reproduction in Staging GCP Environment

Business Value Justification (BVJ):
- Segment: Platform/Enterprise  
- Business Goal: Reproduce and validate fix for WebSocket race conditions in real Cloud Run
- Value Impact: Prevent $500K+ ARR loss from user onboarding failures (1011 errors)
- Strategic Impact: Ensure chat functionality reliability in production environment

These E2E tests run against the ACTUAL STAGING GCP ENVIRONMENT with real:
- Cloud Run services (backend, auth) 
- WebSocket connections through load balancer
- Agent execution with real LLM calls
- Complete user authentication flow
- Network latency and cold start conditions

CRITICAL: These tests are designed to INITIALLY FAIL to reproduce the current
race condition causing 1011 WebSocket errors. After implementing the fix,
all tests should pass consistently.

Issue #372: WebSocket handshake race condition causing 1011 errors in Cloud Run
"""

import asyncio
import pytest
import json
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture

# Import staging-specific utilities
from shared.isolated_environment import get_env


@pytest.mark.e2e
@pytest.mark.staging_only
@pytest.mark.websocket_race_conditions
@pytest.mark.real_llm
class TestWebSocketRaceConditionStaging(BaseE2ETest):
    """
    E2E tests to reproduce WebSocket race conditions in actual GCP staging environment.
    
    CRITICAL: These tests initially FAIL to demonstrate current race condition issues
    in the real Cloud Run environment. After implementing proper handshake coordination 
    and timeout fixes, all tests should pass consistently.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up E2E test environment for staging."""
        
        # Verify we're running against staging
        env = get_env()
        environment = env.get("ENVIRONMENT", "").lower()
        
        if environment != "staging":
            pytest.skip(f"Staging-only tests require ENVIRONMENT=staging, got: {environment}")
        
        # Get staging service URLs
        cls.backend_url = env.get("BACKEND_URL", "wss://netra-backend-staging.onrender.com")
        cls.auth_url = env.get("AUTH_URL", "https://netra-auth-staging.onrender.com")
        
        # WebSocket endpoint (note: wss:// for staging, ws:// for local)
        cls.websocket_url = cls.backend_url.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
        
        # Test user credentials for staging
        cls.test_user_email = env.get("TEST_USER_EMAIL", "test+staging@netra.ai")
        cls.test_user_password = env.get("TEST_USER_PASSWORD", "staging_test_password")
    
    async def get_auth_token(self) -> str:
        """Get authentication token for staging environment."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            login_payload = {
                "email": self.test_user_email,
                "password": self.test_user_password
            }
            
            async with session.post(f"{self.auth_url}/login", json=login_payload) as response:
                if response.status != 200:
                    pytest.fail(f"Failed to authenticate with staging: {response.status}")
                
                auth_data = await response.json()
                return auth_data["access_token"]
    
    @pytest.mark.asyncio
    async def test_concurrent_connections_reproduce_1011_errors(self):
        """
        Test concurrent WebSocket connections to reproduce 1011 errors in staging.
        
        EXPECTED TO FAIL INITIALLY: Current race condition causes 1011 errors when
        multiple users try to connect simultaneously, especially during cold starts.
        
        This reproduces the exact issue reported by users during onboarding.
        """
        auth_token = await self.get_auth_token()
        
        connection_results = []
        connection_errors = []
        
        async def attempt_websocket_connection(connection_id: int, delay_ms: int = 0) -> Dict[str, Any]:
            """Attempt WebSocket connection with authentication."""
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)
            
            start_time = time.time()
            connection_result = {
                "connection_id": connection_id,
                "start_time": start_time,
                "success": False,
                "error": None,
                "duration": 0,
                "close_code": None
            }
            
            try:
                # Connect to staging WebSocket with JWT authentication
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Sec-WebSocket-Protocol": f"jwt.{auth_token}"
                }
                
                timeout_seconds = 10  # Staging connections may be slower
                
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    timeout=timeout_seconds
                ) as websocket:
                    
                    connection_result["duration"] = time.time() - start_time
                    
                    # Wait for connection established message
                    try:
                        welcome_message = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=5.0
                        )
                        
                        welcome_data = json.loads(welcome_message)
                        
                        # Verify connection establishment
                        if welcome_data.get("type") == "connection_established":
                            connection_result["success"] = True
                            connection_result["welcome_message"] = welcome_data
                        else:
                            connection_result["error"] = f"Unexpected welcome message: {welcome_data}"
                            
                    except asyncio.TimeoutError:
                        connection_result["error"] = "Timeout waiting for connection established message"
                    except json.JSONDecodeError as e:
                        connection_result["error"] = f"Invalid JSON in welcome message: {e}"
                        
            except websockets.exceptions.ConnectionClosedError as e:
                connection_result["error"] = f"Connection closed during handshake: {e}"
                connection_result["close_code"] = e.code
                connection_result["duration"] = time.time() - start_time
                
                # Track 1011 errors specifically
                if e.code == 1011:
                    connection_errors.append({
                        "type": "1011_error",
                        "connection_id": connection_id,
                        "message": str(e),
                        "duration": connection_result["duration"]
                    })
                    
            except Exception as e:
                connection_result["error"] = f"Connection failed: {e}"
                connection_result["duration"] = time.time() - start_time
            
            connection_results.append(connection_result)
            return connection_result
        
        # Test with 10 concurrent connections to stress test race condition
        connection_tasks = []
        for i in range(10):
            # Stagger connections slightly to simulate real user behavior
            delay = i * 50  # 50ms between connections
            task = attempt_websocket_connection(i, delay_ms=delay)
            connection_tasks.append(task)
        
        # Execute all connections concurrently
        test_start_time = time.time()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        test_duration = time.time() - test_start_time
        
        # Analyze results
        successful_connections = [r for r in connection_results if r["success"]]
        failed_connections = [r for r in connection_results if not r["success"]]
        error_1011_count = len([e for e in connection_errors if e["type"] == "1011_error"])
        
        # CRITICAL: This assertion will FAIL initially due to race condition
        # Current race condition causes 1011 errors during concurrent connections
        assert len(successful_connections) >= 8, (
            f"Race condition detected: Only {len(successful_connections)}/10 connections succeeded. "
            f"Failed connections: {len(failed_connections)}, 1011 errors: {error_1011_count}. "
            f"Test duration: {test_duration:.2f}s. "
            f"Failed connection details: {failed_connections[:3]}. "
            "This reproduces the user-reported issue causing onboarding failures."
        )
        
        # Should have minimal 1011 errors after fix
        assert error_1011_count <= 1, (
            f"Too many 1011 errors: {error_1011_count}/10 connections. "
            f"1011 errors indicate WebSocket handshake race conditions in Cloud Run. "
            f"Error details: {connection_errors}"
        )
    
    @pytest.mark.asyncio
    async def test_cold_start_connection_timing_race_condition(self):
        """
        Test WebSocket connection during Cloud Run cold start reproduces timing issues.
        
        EXPECTED TO FAIL INITIALLY: Cold start timing causes race conditions where
        WebSocket accepts connections before services are fully initialized.
        """
        auth_token = await self.get_auth_token()
        
        # Force cold start by waiting for services to potentially scale down
        # In real staging, services may scale to zero or restart
        await asyncio.sleep(2.0)
        
        cold_start_results = []
        
        async def test_cold_start_connection(attempt_id: int):
            """Test connection during potential cold start."""
            start_time = time.time()
            
            try:
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Sec-WebSocket-Protocol": f"jwt.{auth_token}"
                }
                
                # Shorter timeout to catch cold start issues
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    timeout=15  # Allow time for cold start
                ) as websocket:
                    
                    connection_time = time.time() - start_time
                    
                    # Send immediate message to test if services are ready
                    test_message = {
                        "type": "user_message",
                        "content": "Test message during cold start",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response to verify services are operational
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30)
                        response_data = json.loads(response)
                        
                        total_time = time.time() - start_time
                        
                        cold_start_results.append({
                            "attempt_id": attempt_id,
                            "success": True,
                            "connection_time": connection_time,
                            "total_time": total_time,
                            "response_type": response_data.get("type"),
                            "cold_start_likely": connection_time > 5.0
                        })
                        
                    except asyncio.TimeoutError:
                        cold_start_results.append({
                            "attempt_id": attempt_id,
                            "success": False,
                            "connection_time": connection_time,
                            "error": "Response timeout - services may not be ready",
                            "cold_start_likely": connection_time > 5.0
                        })
                        
            except Exception as e:
                connection_time = time.time() - start_time
                cold_start_results.append({
                    "attempt_id": attempt_id,
                    "success": False,
                    "connection_time": connection_time,
                    "error": str(e),
                    "cold_start_likely": connection_time > 5.0
                })
        
        # Test 3 connections to catch cold start race condition
        tasks = [test_cold_start_connection(i) for i in range(3)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze cold start behavior
        successful = [r for r in cold_start_results if r["success"]]
        failed = [r for r in cold_start_results if not r["success"]]
        cold_start_likely = [r for r in cold_start_results if r.get("cold_start_likely", False)]
        
        # CRITICAL: Should handle cold start conditions gracefully
        assert len(successful) >= 2, (
            f"Cold start race condition: Only {len(successful)}/3 connections succeeded. "
            f"Failed attempts: {failed}. "
            f"Cold start conditions detected: {len(cold_start_likely)} attempts. "
            "Race condition: WebSocket accepts connections before GCP services ready."
        )
        
        # Long connection times may indicate cold start issues
        long_connections = [r for r in cold_start_results if r.get("connection_time", 0) > 10.0]
        assert len(long_connections) <= 1, (
            f"Too many slow connections: {len(long_connections)}/3 took >10s. "
            f"Slow connections: {long_connections}. "
            "May indicate service readiness race condition."
        )
    
    @pytest.mark.asyncio
    async def test_message_handling_before_handshake_complete_causes_1011(self):
        """
        Test that sending messages before handshake completion causes 1011 errors.
        
        EXPECTED TO FAIL INITIALLY: Current implementation may process messages
        before handshake is fully complete, causing 1011 connection closure.
        """
        auth_token = await self.get_auth_token()
        
        handshake_race_results = []
        
        async def test_immediate_message_sending(test_id: int):
            """Test sending message immediately after connection."""
            result = {
                "test_id": test_id,
                "connection_success": False,
                "message_sent": False,
                "response_received": False,
                "error": None,
                "close_code": None
            }
            
            try:
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Sec-WebSocket-Protocol": f"jwt.{auth_token}"
                }
                
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    timeout=10
                ) as websocket:
                    
                    result["connection_success"] = True
                    
                    # Send message IMMEDIATELY without waiting for handshake completion
                    # This should trigger the race condition
                    immediate_message = {
                        "type": "user_message", 
                        "content": "Immediate message to trigger race condition",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(immediate_message))
                    result["message_sent"] = True
                    
                    # Try to receive response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    result["response_received"] = True
                    result["response"] = json.loads(response)
                    
            except websockets.exceptions.ConnectionClosedError as e:
                result["error"] = str(e)
                result["close_code"] = e.code
                
                # Track 1011 errors from race condition
                if e.code == 1011:
                    result["race_condition_detected"] = True
                    
            except Exception as e:
                result["error"] = str(e)
            
            handshake_race_results.append(result)
            return result
        
        # Test 5 attempts to catch race condition
        tasks = [test_immediate_message_sending(i) for i in range(5)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze race condition results
        successful_responses = [r for r in handshake_race_results if r["response_received"]]
        connection_closed_1011 = [r for r in handshake_race_results if r.get("close_code") == 1011]
        race_conditions_detected = [r for r in handshake_race_results if r.get("race_condition_detected", False)]
        
        # CRITICAL: Should handle immediate messages without 1011 errors
        # This will FAIL initially due to race condition
        assert len(connection_closed_1011) <= 1, (
            f"Race condition detected: {len(connection_closed_1011)}/5 connections got 1011 errors. "
            f"1011 errors indicate messages processed before handshake complete. "
            f"Race condition details: {connection_closed_1011}. "
            "This reproduces the exact issue causing user onboarding failures."
        )
        
        # Most connections should succeed after fix
        assert len(successful_responses) >= 3, (
            f"Handshake race condition: Only {len(successful_responses)}/5 connections "
            f"successfully handled immediate messages. "
            f"Failed results: {[r for r in handshake_race_results if not r['response_received']]}"
        )
    
    @pytest.mark.asyncio
    async def test_service_dependency_race_condition_staging(self):
        """
        Test connection when supervisor/thread services not ready causes failures.
        
        EXPECTED TO FAIL INITIALLY: WebSocket may accept connections before
        required services (supervisor, thread) are ready in Cloud Run.
        """
        auth_token = await self.get_auth_token()
        
        dependency_test_results = []
        
        async def test_service_dependency(test_id: int):
            """Test connection and immediate agent request to check service readiness."""
            result = {
                "test_id": test_id,
                "connection_success": False,
                "agent_request_sent": False,
                "agent_response_received": False,
                "service_ready": False,
                "error": None
            }
            
            try:
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Sec-WebSocket-Protocol": f"jwt.{auth_token}"
                }
                
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    timeout=10
                ) as websocket:
                    
                    result["connection_success"] = True
                    
                    # Wait briefly for connection establishment
                    welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
                    welcome_data = json.loads(welcome)
                    
                    if welcome_data.get("type") != "connection_established":
                        result["error"] = f"Unexpected welcome: {welcome_data}"
                        dependency_test_results.append(result)
                        return
                    
                    # Send agent request to test if supervisor service is ready
                    agent_request = {
                        "type": "start_agent",
                        "agent": "triage_agent",
                        "message": "Test service dependency",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(agent_request))
                    result["agent_request_sent"] = True
                    
                    # Wait for agent response or error
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=15)
                        response_data = json.loads(response)
                        result["response"] = response_data
                        
                        # Check if agent execution started (indicates services ready)
                        if response_data.get("type") in ["agent_started", "agent_thinking"]:
                            result["service_ready"] = True
                            result["agent_response_received"] = True
                        elif response_data.get("type") == "error":
                            result["error"] = f"Service error: {response_data}"
                        else:
                            result["agent_response_received"] = True
                            
                    except asyncio.TimeoutError:
                        result["error"] = "Agent request timeout - services may not be ready"
                        
            except Exception as e:
                result["error"] = str(e)
            
            dependency_test_results.append(result)
            return result
        
        # Test 3 connections to check service dependency
        tasks = [test_service_dependency(i) for i in range(3)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze service dependency results
        services_ready = [r for r in dependency_test_results if r["service_ready"]]
        agent_timeouts = [r for r in dependency_test_results if "timeout" in str(r.get("error", "")).lower()]
        connection_failures = [r for r in dependency_test_results if not r["connection_success"]]
        
        # CRITICAL: Services should be ready when connections are accepted
        # This may FAIL if WebSocket accepts connections before services ready
        assert len(services_ready) >= 2, (
            f"Service dependency race condition: Only {len(services_ready)}/3 tests "
            f"found services ready. Agent timeouts: {len(agent_timeouts)}, "
            f"Connection failures: {len(connection_failures)}. "
            f"Error details: {[r['error'] for r in dependency_test_results if r['error']]}. "
            "Race condition: WebSocket accepts connections before supervisor/thread services ready."
        )
        
        # Should have minimal agent timeouts after fix
        assert len(agent_timeouts) <= 1, (
            f"Too many service timeouts: {len(agent_timeouts)}/3 tests timed out. "
            f"Timeout details: {agent_timeouts}. "
            "Agent timeouts indicate services not ready when connections accepted."
        )
    
    @pytest.mark.asyncio
    async def test_user_onboarding_flow_reliability_end_to_end(self):
        """
        Test complete user onboarding flow reliability in staging environment.
        
        EXPECTED TO FAIL INITIALLY: Race conditions cause user onboarding failures
        affecting $500K+ ARR from failed user activation.
        
        This is the ultimate test - simulating real user onboarding experience.
        """
        auth_token = await self.get_auth_token()
        
        onboarding_results = []
        
        async def simulate_user_onboarding(user_id: int):
            """Simulate complete user onboarding experience."""
            onboarding_steps = {
                "authentication": False,
                "websocket_connection": False,
                "welcome_message": False,
                "first_agent_interaction": False,
                "agent_response_quality": False,
                "session_persistence": False
            }
            
            errors = []
            start_time = time.time()
            
            try:
                # Step 1: WebSocket connection with authentication
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Sec-WebSocket-Protocol": f"jwt.{auth_token}"
                }
                
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    timeout=15
                ) as websocket:
                    
                    onboarding_steps["authentication"] = True
                    onboarding_steps["websocket_connection"] = True
                    
                    # Step 2: Receive welcome message
                    try:
                        welcome = await asyncio.wait_for(websocket.recv(), timeout=10)
                        welcome_data = json.loads(welcome)
                        
                        if welcome_data.get("type") == "connection_established":
                            onboarding_steps["welcome_message"] = True
                        else:
                            errors.append(f"Unexpected welcome: {welcome_data}")
                            
                    except asyncio.TimeoutError:
                        errors.append("Welcome message timeout")
                    
                    # Step 3: First agent interaction (critical onboarding moment)
                    if onboarding_steps["welcome_message"]:
                        first_message = {
                            "type": "user_message",
                            "content": "Hello! I'm new to Netra. Can you help me optimize my AI costs?",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await websocket.send(json.dumps(first_message))
                        onboarding_steps["first_agent_interaction"] = True
                        
                        # Step 4: Wait for meaningful agent response
                        agent_events = []
                        response_timeout = 30  # Allow time for agent processing
                        
                        try:
                            while len(agent_events) < 3:  # Expect multiple events
                                event = await asyncio.wait_for(websocket.recv(), timeout=response_timeout)
                                event_data = json.loads(event)
                                agent_events.append(event_data)
                                
                                # Look for completion event
                                if event_data.get("type") == "agent_completed":
                                    break
                                    
                                # Reduce timeout for subsequent events
                                response_timeout = 10
                            
                            # Step 5: Validate response quality
                            completion_events = [e for e in agent_events if e.get("type") == "agent_completed"]
                            if completion_events:
                                completion = completion_events[0]
                                result = completion.get("data", {}).get("result", "")
                                
                                # Check for meaningful response content
                                if (len(result) > 50 and 
                                    any(word in result.lower() for word in ["cost", "optimize", "save", "ai"])):
                                    onboarding_steps["agent_response_quality"] = True
                                else:
                                    errors.append(f"Poor response quality: {result[:100]}...")
                            else:
                                errors.append(f"No completion event in: {[e.get('type') for e in agent_events]}")
                                
                        except asyncio.TimeoutError:
                            errors.append(f"Agent response timeout after {len(agent_events)} events")
                    
                    # Step 6: Session persistence check
                    if onboarding_steps["agent_response_quality"]:
                        followup_message = {
                            "type": "user_message", 
                            "content": "That's helpful! Can you give me specific recommendations?",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await websocket.send(json.dumps(followup_message))
                        
                        try:
                            followup_response = await asyncio.wait_for(websocket.recv(), timeout=20)
                            followup_data = json.loads(followup_response)
                            
                            if followup_data.get("type") in ["agent_started", "agent_thinking"]:
                                onboarding_steps["session_persistence"] = True
                            else:
                                errors.append(f"Poor followup response: {followup_data}")
                                
                        except asyncio.TimeoutError:
                            errors.append("Followup response timeout")
            
            except Exception as e:
                errors.append(f"Connection error: {e}")
            
            total_duration = time.time() - start_time
            
            # Calculate onboarding success score
            completed_steps = sum(1 for step in onboarding_steps.values() if step)
            success_rate = completed_steps / len(onboarding_steps)
            
            result = {
                "user_id": user_id,
                "success_rate": success_rate,
                "completed_steps": completed_steps,
                "total_steps": len(onboarding_steps),
                "onboarding_steps": onboarding_steps,
                "errors": errors,
                "duration": total_duration,
                "onboarding_successful": success_rate >= 0.8  # 80% success threshold
            }
            
            onboarding_results.append(result)
            return result
        
        # Test 3 user onboarding flows
        tasks = [simulate_user_onboarding(i) for i in range(3)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze onboarding success
        successful_onboardings = [r for r in onboarding_results if r["onboarding_successful"]]
        failed_onboardings = [r for r in onboarding_results if not r["onboarding_successful"]]
        
        avg_success_rate = sum(r["success_rate"] for r in onboarding_results) / len(onboarding_results)
        common_errors = {}
        for result in onboarding_results:
            for error in result["errors"]:
                common_errors[error] = common_errors.get(error, 0) + 1
        
        # CRITICAL: User onboarding success rate should be very high (>90%)
        # This will FAIL initially due to race conditions affecting user experience
        assert len(successful_onboardings) >= 3, (
            f"User onboarding reliability failure: Only {len(successful_onboardings)}/3 users "
            f"completed onboarding successfully (avg success rate: {avg_success_rate:.1%}). "
            f"Failed onboardings: {len(failed_onboardings)}. "
            f"Common errors: {common_errors}. "
            f"This directly impacts $500K+ ARR from failed user activation due to WebSocket race conditions."
        )
        
        # Average success rate should be excellent
        assert avg_success_rate >= 0.90, (
            f"Poor onboarding success rate: {avg_success_rate:.1%} < 90%. "
            f"Race conditions in WebSocket handshake are degrading user experience. "
            f"Detailed results: {[{k: v for k, v in r.items() if k != 'errors'} for r in onboarding_results]}"
        )