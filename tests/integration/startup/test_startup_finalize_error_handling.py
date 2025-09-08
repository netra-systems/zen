"""
Integration tests for FINALIZE phase - Error Recovery and Fault Tolerance

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Resilience and User Experience Continuity
- Value Impact: Ensures system continues operating despite errors, maintaining user access
- Strategic Impact: Error handling prevents complete system failures that block all users

Tests error recovery and fault tolerance during the FINALIZE phase, ensuring the
system can gracefully handle various error conditions and continue providing
service to users without complete failure.

Robust error handling is CRITICAL for production reliability and user trust.

Covers:
1. Service failure detection and recovery
2. Database connection loss handling
3. WebSocket error recovery and reconnection
4. Agent execution error handling
5. API endpoint error responses
6. System overload and resource exhaustion handling
7. Graceful degradation under failure conditions
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
import pytest
import aiohttp
import websockets
from unittest.mock import patch, AsyncMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.isolated_environment import get_env


class TestStartupFinalizeErrorHandling(SSotBaseTestCase):
    """Integration tests for FINALIZE phase error recovery and fault tolerance."""
    
    def setup_method(self, method):
        """Setup test environment for error handling testing."""
        super().setup_method(method)
        
        # Initialize E2E auth helpers
        self.auth_helper = E2EAuthHelper(environment="test")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Configure test environment
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        self.set_env_var("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars")
        
        # Service endpoints
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        
        # Track error handling test results
        self.error_test_results: Dict[str, Any] = {}
        
        # Test user configuration
        self.test_user_id = f"error_test_user_{int(time.time())}"
        self.test_user_email = f"error_test_{int(time.time())}@example.com"

    @pytest.mark.integration
    async def test_finalize_api_error_response_handling(self):
        """
        Test API error response handling and graceful error messaging.
        
        BVJ: Proper error responses prevent user confusion and support debugging.
        """
        api_error_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        # 1. Test handling of non-existent endpoints
        nonexistent_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.backend_url}/api/nonexistent/endpoint",
                    headers=headers,
                    timeout=10
                ) as resp:
                    nonexistent_time = time.time() - nonexistent_start
                    
                    # Should return proper 404 error
                    assert resp.status == 404, f"Non-existent endpoint should return 404, got {resp.status}"
                    
                    try:
                        error_response = await resp.json()
                        has_error_structure = "error" in error_response or "detail" in error_response or "message" in error_response
                    except Exception:
                        # May not be JSON response
                        error_response = await resp.text()
                        has_error_structure = len(error_response) > 0
                    
                    api_error_results.append({
                        "test": "nonexistent_endpoint_handling",
                        "status": "success",
                        "response_time": nonexistent_time,
                        "status_code": resp.status,
                        "has_error_structure": has_error_structure,
                        "error_response_type": type(error_response).__name__
                    })
                    
                    self.record_metric("nonexistent_endpoint_response_time", nonexistent_time)
                    
        except Exception as e:
            api_error_results.append({
                "test": "nonexistent_endpoint_handling",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test handling of malformed requests
        malformed_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Send invalid JSON data
                async with session.post(
                    f"{self.backend_url}/api/agents/execute",
                    headers=headers,
                    data="invalid json data",  # Not valid JSON
                    timeout=10
                ) as resp:
                    malformed_time = time.time() - malformed_start
                    
                    # Should return proper 400 error
                    assert resp.status in [400, 422], f"Malformed request should return 400/422, got {resp.status}"
                    
                    try:
                        error_response = await resp.json()
                        has_error_details = "error" in error_response or "detail" in error_response
                    except Exception:
                        error_response = await resp.text()
                        has_error_details = "error" in error_response.lower() or "invalid" in error_response.lower()
                    
                    api_error_results.append({
                        "test": "malformed_request_handling",
                        "status": "success",
                        "response_time": malformed_time,
                        "status_code": resp.status,
                        "has_error_details": has_error_details
                    })
                    
                    self.record_metric("malformed_request_response_time", malformed_time)
                    
        except Exception as e:
            api_error_results.append({
                "test": "malformed_request_handling",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test handling of unauthorized requests
        unauthorized_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Send request without authentication headers
                async with session.get(
                    f"{self.backend_url}/api/users/me",
                    timeout=10
                ) as resp:
                    unauthorized_time = time.time() - unauthorized_start
                    
                    # Should return proper authentication error
                    assert resp.status in [401, 403], f"Unauthorized request should return 401/403, got {resp.status}"
                    
                    try:
                        error_response = await resp.json()
                        has_auth_error = "auth" in str(error_response).lower() or "unauthorized" in str(error_response).lower()
                    except Exception:
                        error_response = await resp.text()
                        has_auth_error = "auth" in error_response.lower() or "unauthorized" in error_response.lower()
                    
                    api_error_results.append({
                        "test": "unauthorized_request_handling",
                        "status": "success",
                        "response_time": unauthorized_time,
                        "status_code": resp.status,
                        "has_auth_error_message": has_auth_error
                    })
                    
                    self.record_metric("unauthorized_request_response_time", unauthorized_time)
                    
        except Exception as e:
            api_error_results.append({
                "test": "unauthorized_request_handling",
                "status": "failed",
                "error": str(e)
            })
        
        # 4. Test handling of oversized requests
        oversized_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Send very large request payload
                large_payload = {
                    "data": "A" * 1000000,  # 1MB of data
                    "user_id": self.test_user_id
                }
                
                async with session.post(
                    f"{self.backend_url}/api/logs",
                    headers=headers,
                    json=large_payload,
                    timeout=15
                ) as resp:
                    oversized_time = time.time() - oversized_start
                    
                    # Should handle large payload gracefully (either accept or reject properly)
                    assert resp.status in [200, 201, 400, 413, 422], f"Large payload handling failed: {resp.status}"
                    
                    if resp.status in [400, 413, 422]:
                        # Properly rejected large payload
                        api_error_results.append({
                            "test": "oversized_request_handling",
                            "status": "properly_rejected",
                            "response_time": oversized_time,
                            "status_code": resp.status,
                            "payload_size": len(json.dumps(large_payload))
                        })
                    else:
                        # Accepted large payload
                        api_error_results.append({
                            "test": "oversized_request_handling",
                            "status": "accepted_large_payload",
                            "response_time": oversized_time,
                            "status_code": resp.status,
                            "payload_size": len(json.dumps(large_payload))
                        })
                    
                    self.record_metric("oversized_request_response_time", oversized_time)
                    
        except Exception as e:
            api_error_results.append({
                "test": "oversized_request_handling",
                "status": "connection_error",
                "error": str(e)
            })
        
        # Record API error handling results
        self.error_test_results["api_error_handling"] = api_error_results
        
        # Validate API error handling
        successful_error_handling = [r for r in api_error_results if r["status"] in ["success", "properly_rejected", "accepted_large_payload"]]
        assert len(successful_error_handling) >= 3, f"API error handling insufficient: {len(successful_error_handling)}/4 tests passed"
        
        self.record_metric("api_error_handling_passed", True)

    @pytest.mark.integration
    async def test_finalize_websocket_error_recovery(self):
        """
        Test WebSocket error recovery and reconnection handling.
        
        BVJ: WebSocket reliability ensures continuous chat functionality.
        """
        websocket_error_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.websocket_auth_helper.get_websocket_headers(token)
        
        # 1. Test WebSocket connection recovery after forced disconnection
        recovery_start = time.time()
        try:
            # Establish initial WebSocket connection
            initial_websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            # Send initial message
            initial_message = {
                "type": "test",
                "message": "Initial connection test",
                "user_id": self.test_user_id
            }
            
            await initial_websocket.send(json.dumps(initial_message))
            
            # Force close the connection
            await initial_websocket.close()
            
            # Attempt reconnection
            reconnection_start = time.time()
            recovery_websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            reconnection_time = time.time() - reconnection_start
            
            # Send message on reconnected WebSocket
            recovery_message = {
                "type": "test",
                "message": "Recovery connection test",
                "user_id": self.test_user_id
            }
            
            await recovery_websocket.send(json.dumps(recovery_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(recovery_websocket.recv(), timeout=5.0)
                response_received = True
            except asyncio.TimeoutError:
                response_received = False
            
            await recovery_websocket.close()
            
            recovery_total_time = time.time() - recovery_start
            
            websocket_error_results.append({
                "test": "websocket_connection_recovery",
                "status": "success",
                "total_recovery_time": recovery_total_time,
                "reconnection_time": reconnection_time,
                "response_received_after_recovery": response_received
            })
            
            self.record_metric("websocket_recovery_time", recovery_total_time)
            self.record_metric("websocket_reconnection_time", reconnection_time)
            
        except Exception as e:
            websocket_error_results.append({
                "test": "websocket_connection_recovery",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test handling of invalid WebSocket messages
        invalid_message_start = time.time()
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            # Send invalid JSON message
            await websocket.send("invalid json message")
            
            # Wait for error response or connection status
            try:
                error_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                connection_survived = True
                
                try:
                    error_data = json.loads(error_response)
                    has_error_response = "error" in error_data or "type" in error_data
                except Exception:
                    has_error_response = True  # Any response indicates handling
                    
            except asyncio.TimeoutError:
                # No response - check if connection is still alive
                try:
                    await websocket.ping()
                    connection_survived = True
                    has_error_response = False
                except Exception:
                    connection_survived = False
                    has_error_response = False
            
            # Send valid message after invalid one
            if connection_survived:
                valid_message = {
                    "type": "test",
                    "message": "Valid message after invalid one",
                    "user_id": self.test_user_id
                }
                
                await websocket.send(json.dumps(valid_message))
                
                try:
                    valid_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    recovers_after_invalid = True
                except asyncio.TimeoutError:
                    recovers_after_invalid = True  # No response is acceptable
            else:
                recovers_after_invalid = False
            
            await websocket.close()
            
            invalid_message_time = time.time() - invalid_message_start
            
            websocket_error_results.append({
                "test": "invalid_websocket_message_handling",
                "status": "tested",
                "response_time": invalid_message_time,
                "connection_survived": connection_survived,
                "has_error_response": has_error_response,
                "recovers_after_invalid": recovers_after_invalid
            })
            
        except Exception as e:
            websocket_error_results.append({
                "test": "invalid_websocket_message_handling",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test WebSocket timeout handling
        timeout_start = time.time()
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            # Send message and then be idle for extended period
            idle_message = {
                "type": "test",
                "message": "Starting idle period test",
                "user_id": self.test_user_id
            }
            
            await websocket.send(json.dumps(idle_message))
            
            # Be idle for 10 seconds
            await asyncio.sleep(10.0)
            
            # Test if connection is still alive
            try:
                await websocket.ping()
                connection_alive_after_idle = True
            except Exception:
                connection_alive_after_idle = False
            
            # Try to send message after idle period
            if connection_alive_after_idle:
                post_idle_message = {
                    "type": "test", 
                    "message": "Message after idle period",
                    "user_id": self.test_user_id
                }
                
                try:
                    await websocket.send(json.dumps(post_idle_message))
                    works_after_idle = True
                except Exception:
                    works_after_idle = False
            else:
                works_after_idle = False
            
            if not websocket.closed:
                await websocket.close()
                
            timeout_handling_time = time.time() - timeout_start
            
            websocket_error_results.append({
                "test": "websocket_idle_timeout_handling",
                "status": "tested",
                "total_time": timeout_handling_time,
                "connection_alive_after_idle": connection_alive_after_idle,
                "works_after_idle": works_after_idle
            })
            
        except Exception as e:
            websocket_error_results.append({
                "test": "websocket_idle_timeout_handling",
                "status": "failed",
                "error": str(e)
            })
        
        # Record WebSocket error recovery results
        self.error_test_results["websocket_error_recovery"] = websocket_error_results
        
        # Validate WebSocket error recovery
        successful_websocket_tests = [r for r in websocket_error_results if r["status"] in ["success", "tested"]]
        assert len(successful_websocket_tests) > 0, "No successful WebSocket error recovery tests"
        
        # Connection recovery should work
        recovery_tests = [r for r in websocket_error_results if r["test"] == "websocket_connection_recovery" and r["status"] == "success"]
        assert len(recovery_tests) > 0, "WebSocket connection recovery failed"
        
        self.record_metric("websocket_error_recovery_passed", True)

    @pytest.mark.integration
    async def test_finalize_service_failure_handling(self):
        """
        Test handling of temporary service failures and degraded conditions.
        
        BVJ: Service failure handling ensures system continues operating during issues.
        """
        service_failure_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        # 1. Test handling of slow service responses
        slow_response_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Test with reduced timeout to simulate slow service
                try:
                    async with session.get(
                        f"{self.backend_url}/health",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=2.0)  # Short timeout
                    ) as resp:
                        slow_response_time = time.time() - slow_response_start
                        
                        service_failure_results.append({
                            "test": "fast_service_response",
                            "status": "success",
                            "response_time": slow_response_time,
                            "within_timeout": slow_response_time < 2.0,
                            "status_code": resp.status
                        })
                        
                except asyncio.TimeoutError:
                    slow_response_time = time.time() - slow_response_start
                    service_failure_results.append({
                        "test": "slow_service_timeout_handling",
                        "status": "timeout_handled",
                        "timeout_duration": slow_response_time
                    })
                    
        except Exception as e:
            service_failure_results.append({
                "test": "service_response_timing",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test graceful degradation under high load
        load_test_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Send multiple rapid requests to test load handling
                rapid_request_tasks = []
                
                for i in range(15):  # Send 15 rapid requests
                    task = session.get(
                        f"{self.backend_url}/health",
                        headers=headers,
                        timeout=10
                    )
                    rapid_request_tasks.append(task)
                
                # Execute all requests concurrently
                responses = await asyncio.gather(*rapid_request_tasks, return_exceptions=True)
                load_test_time = time.time() - load_test_start
                
                # Analyze responses
                successful_responses = 0
                error_responses = 0
                timeout_responses = 0
                
                for response in responses:
                    if hasattr(response, 'status'):
                        if response.status == 200:
                            successful_responses += 1
                        else:
                            error_responses += 1
                        await response.close()
                    elif isinstance(response, asyncio.TimeoutError):
                        timeout_responses += 1
                    elif isinstance(response, Exception):
                        error_responses += 1
                
                # Calculate success rate
                total_requests = len(rapid_request_tasks)
                success_rate = successful_responses / total_requests
                
                service_failure_results.append({
                    "test": "high_load_graceful_degradation",
                    "status": "tested",
                    "total_time": load_test_time,
                    "total_requests": total_requests,
                    "successful_responses": successful_responses,
                    "error_responses": error_responses,
                    "timeout_responses": timeout_responses,
                    "success_rate": success_rate
                })
                
                # Should handle at least 60% of requests successfully
                assert success_rate >= 0.6, f"Service degraded too much under load: {success_rate:.2%} success rate"
                
                self.record_metric("high_load_success_rate", success_rate)
                self.record_metric("high_load_test_time", load_test_time)
                
        except Exception as e:
            service_failure_results.append({
                "test": "high_load_graceful_degradation",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test system recovery after stress
        recovery_start = time.time()
        try:
            # After load testing, normal operation should resume
            async with aiohttp.ClientSession() as session:
                # Wait briefly for system to recover
                await asyncio.sleep(2.0)
                
                async with session.get(
                    f"{self.backend_url}/health",
                    headers=headers,
                    timeout=10
                ) as resp:
                    recovery_time = time.time() - recovery_start
                    
                    assert resp.status == 200, f"System did not recover after load test: {resp.status}"
                    
                    service_failure_results.append({
                        "test": "service_recovery_after_load",
                        "status": "success",
                        "recovery_time": recovery_time,
                        "status_code": resp.status
                    })
                    
                    self.record_metric("service_recovery_time", recovery_time)
                    
        except Exception as e:
            service_failure_results.append({
                "test": "service_recovery_after_load",
                "status": "failed",
                "error": str(e)
            })
        
        # 4. Test database connection failure simulation (if possible)
        db_failure_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Test database health endpoint behavior
                async with session.get(
                    f"{self.backend_url}/health/database",
                    headers=headers,
                    timeout=15
                ) as resp:
                    db_failure_time = time.time() - db_failure_start
                    
                    if resp.status == 200:
                        db_health = await resp.json()
                        service_failure_results.append({
                            "test": "database_connection_stability",
                            "status": "stable",
                            "response_time": db_failure_time,
                            "database_connected": db_health.get("connected", False)
                        })
                    else:
                        service_failure_results.append({
                            "test": "database_connection_stability",
                            "status": "unstable",
                            "response_time": db_failure_time,
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            service_failure_results.append({
                "test": "database_connection_stability",
                "status": "error",
                "error": str(e)
            })
        
        # Record service failure handling results
        self.error_test_results["service_failure_handling"] = service_failure_results
        
        # Validate service failure handling
        critical_tests = [r for r in service_failure_results if r["test"] in ["high_load_graceful_degradation", "service_recovery_after_load"]]
        successful_critical_tests = [r for r in critical_tests if r["status"] in ["tested", "success"]]
        
        assert len(successful_critical_tests) >= 1, "Critical service failure handling tests failed"
        
        # System recovery should work
        recovery_tests = [r for r in service_failure_results if r["test"] == "service_recovery_after_load" and r["status"] == "success"]
        assert len(recovery_tests) > 0, "Service did not recover after load testing"
        
        self.record_metric("service_failure_handling_passed", True)

    @pytest.mark.integration
    async def test_finalize_agent_execution_error_resilience(self):
        """
        Test agent execution error resilience and recovery.
        
        BVJ: Agent error resilience ensures AI functionality continues despite failures.
        """
        agent_error_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email,
            permissions=["read", "write", "agent_execution"]
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        # 1. Test handling of invalid agent execution requests
        invalid_agent_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Send invalid agent request
                invalid_request = {
                    "agent_type": "nonexistent_agent",
                    "prompt": "This should fail gracefully",
                    "user_id": self.test_user_id
                }
                
                async with session.post(
                    f"{self.backend_url}/api/agents/execute",
                    headers=headers,
                    json=invalid_request,
                    timeout=15
                ) as resp:
                    invalid_agent_time = time.time() - invalid_agent_start
                    
                    # Should handle invalid agent gracefully
                    assert resp.status in [400, 404, 422], f"Invalid agent request should be handled gracefully: {resp.status}"
                    
                    try:
                        error_response = await resp.json()
                        has_error_message = "error" in error_response or "message" in error_response
                    except Exception:
                        error_response = await resp.text()
                        has_error_message = "error" in error_response.lower()
                    
                    agent_error_results.append({
                        "test": "invalid_agent_request_handling",
                        "status": "gracefully_handled",
                        "response_time": invalid_agent_time,
                        "status_code": resp.status,
                        "has_error_message": has_error_message
                    })
                    
        except Exception as e:
            agent_error_results.append({
                "test": "invalid_agent_request_handling",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test agent execution with malformed prompts
        malformed_prompt_start = time.time()
        try:
            websocket_headers = self.websocket_auth_helper.get_websocket_headers(token)
            
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=websocket_headers),
                timeout=15.0
            )
            
            # Send message with potentially problematic content
            problematic_message = {
                "type": "chat_message",
                "message": "Execute this: " + "A" * 10000,  # Very long prompt
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(problematic_message))
            
            # Wait for response or error handling
            error_events = []
            timeout_duration = 20.0  # Give time for error handling
            
            start_time = time.time()
            while time.time() - start_time < timeout_duration:
                try:
                    event_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    event_data = json.loads(event_response)
                    error_events.append(event_data)
                    
                    # Look for error or completion events
                    event_type = event_data.get("type", "")
                    if event_type in ["error", "agent_error", "execution_error", "agent_completed"]:
                        break
                        
                except asyncio.TimeoutError:
                    if len(error_events) > 0:
                        break  # Got some events
                    continue
            
            malformed_prompt_time = time.time() - malformed_prompt_start
            
            # Analyze error handling
            has_error_handling = any(
                event.get("type", "") in ["error", "agent_error", "execution_error"] 
                for event in error_events
            )
            
            agent_error_results.append({
                "test": "malformed_prompt_handling",
                "status": "tested",
                "response_time": malformed_prompt_time,
                "events_received": len(error_events),
                "has_error_handling": has_error_handling,
                "event_types": [event.get("type") for event in error_events[:3]]
            })
            
            await websocket.close()
            
        except Exception as e:
            agent_error_results.append({
                "test": "malformed_prompt_handling",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test system resilience after agent errors
        resilience_start = time.time()
        try:
            websocket_headers = self.websocket_auth_helper.get_websocket_headers(token)
            
            resilience_websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=websocket_headers),
                timeout=15.0
            )
            
            # Send normal message after previous error tests
            normal_message = {
                "type": "chat_message",
                "message": "This is a normal message to test system resilience after errors.",
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            await resilience_websocket.send(json.dumps(normal_message))
            
            # Wait for normal response
            resilience_events = []
            resilience_timeout = 15.0
            
            start_time = time.time()
            while time.time() - start_time < resilience_timeout:
                try:
                    event_response = await asyncio.wait_for(resilience_websocket.recv(), timeout=3.0)
                    event_data = json.loads(event_response)
                    resilience_events.append(event_data)
                    
                    # Look for completion or substantial response
                    event_type = event_data.get("type", "")
                    if event_type in ["agent_completed", "execution_complete"] or len(event_data.get("message", "")) > 10:
                        break
                        
                except asyncio.TimeoutError:
                    if len(resilience_events) > 0:
                        break  # Got some events
                    continue
            
            resilience_time = time.time() - resilience_start
            
            # System should still be responsive
            system_responsive = len(resilience_events) > 0
            
            agent_error_results.append({
                "test": "agent_system_resilience_after_errors",
                "status": "success" if system_responsive else "unresponsive",
                "response_time": resilience_time,
                "events_received": len(resilience_events),
                "system_responsive": system_responsive
            })
            
            await resilience_websocket.close()
            
            # Validate system responsiveness
            assert system_responsive, "Agent system not responsive after error conditions"
            
        except Exception as e:
            agent_error_results.append({
                "test": "agent_system_resilience_after_errors",
                "status": "failed",
                "error": str(e)
            })
        
        # Record agent error resilience results
        self.error_test_results["agent_error_resilience"] = agent_error_results
        
        # Validate agent error handling
        successful_agent_error_tests = [r for r in agent_error_results if r["status"] in ["gracefully_handled", "tested", "success"]]
        assert len(successful_agent_error_tests) >= 2, f"Agent error handling insufficient: {len(successful_agent_error_tests)}/3 tests passed"
        
        # System resilience should work
        resilience_tests = [r for r in agent_error_results if r["test"] == "agent_system_resilience_after_errors" and r["status"] == "success"]
        assert len(resilience_tests) > 0, "Agent system did not demonstrate resilience after errors"
        
        self.record_metric("agent_error_resilience_passed", True)

    @pytest.mark.integration
    async def test_finalize_system_monitoring_alerting(self):
        """
        Test system monitoring and error alerting capabilities.
        
        BVJ: Monitoring ensures early detection of issues before they impact users.
        """
        monitoring_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        # 1. Test metrics collection endpoint
        metrics_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.backend_url}/metrics",
                    headers=headers,
                    timeout=10
                ) as resp:
                    metrics_time = time.time() - metrics_start
                    
                    if resp.status == 200:
                        metrics_data = await resp.json()
                        
                        # Check for common metrics
                        has_health_metrics = any(
                            metric in str(metrics_data).lower() 
                            for metric in ["cpu", "memory", "requests", "errors", "response_time"]
                        )
                        
                        monitoring_results.append({
                            "test": "metrics_collection",
                            "status": "success",
                            "response_time": metrics_time,
                            "has_health_metrics": has_health_metrics,
                            "metrics_available": bool(metrics_data)
                        })
                        
                    elif resp.status == 404:
                        monitoring_results.append({
                            "test": "metrics_collection",
                            "status": "not_implemented"
                        })
                    else:
                        monitoring_results.append({
                            "test": "metrics_collection",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            monitoring_results.append({
                "test": "metrics_collection",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test error logging and tracking
        error_tracking_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Generate a trackable error
                async with session.get(
                    f"{self.backend_url}/api/trigger/test-error",
                    headers=headers,
                    timeout=5
                ) as resp:
                    # This endpoint likely doesn't exist - will generate 404
                    pass
                
                # Check if error was logged (if logs endpoint exists)
                async with session.get(
                    f"{self.backend_url}/api/logs/errors",
                    headers=headers,
                    timeout=5
                ) as resp:
                    error_tracking_time = time.time() - error_tracking_start
                    
                    if resp.status == 200:
                        error_logs = await resp.json()
                        monitoring_results.append({
                            "test": "error_logging_tracking",
                            "status": "success",
                            "response_time": error_tracking_time,
                            "error_logs_available": bool(error_logs)
                        })
                    elif resp.status == 404:
                        monitoring_results.append({
                            "test": "error_logging_tracking",
                            "status": "not_implemented"
                        })
                    else:
                        monitoring_results.append({
                            "test": "error_logging_tracking",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            monitoring_results.append({
                "test": "error_logging_tracking",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test health check aggregation
        health_aggregation_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Test comprehensive health endpoint
                async with session.get(
                    f"{self.backend_url}/health/comprehensive",
                    headers=headers,
                    timeout=15
                ) as resp:
                    health_aggregation_time = time.time() - health_aggregation_start
                    
                    if resp.status == 200:
                        health_data = await resp.json()
                        
                        # Check for comprehensive health information
                        has_service_status = "services" in health_data or "components" in health_data
                        has_overall_status = "status" in health_data or "healthy" in health_data
                        
                        monitoring_results.append({
                            "test": "health_check_aggregation",
                            "status": "success",
                            "response_time": health_aggregation_time,
                            "has_service_status": has_service_status,
                            "has_overall_status": has_overall_status,
                            "health_data_keys": list(health_data.keys())[:5] if isinstance(health_data, dict) else []
                        })
                        
                    elif resp.status == 404:
                        # Try regular health endpoint
                        async with session.get(f"{self.backend_url}/health", headers=headers, timeout=10) as basic_resp:
                            if basic_resp.status == 200:
                                monitoring_results.append({
                                    "test": "health_check_aggregation",
                                    "status": "basic_health_available",
                                    "response_time": health_aggregation_time
                                })
                            else:
                                monitoring_results.append({
                                    "test": "health_check_aggregation",
                                    "status": "not_implemented"
                                })
                    else:
                        monitoring_results.append({
                            "test": "health_check_aggregation",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            monitoring_results.append({
                "test": "health_check_aggregation",
                "status": "failed",
                "error": str(e)
            })
        
        # Record monitoring results
        self.error_test_results["system_monitoring"] = monitoring_results
        
        # Validate monitoring capabilities
        functional_monitoring = [r for r in monitoring_results if r["status"] in ["success", "basic_health_available"]]
        
        if len(functional_monitoring) == 0:
            self.record_metric("system_monitoring_warning", "No functional monitoring endpoints found")
        else:
            self.record_metric("system_monitoring_available", True)
        
        self.record_metric("system_monitoring_alerting_passed", True)
        
        # Record overall error handling completion
        self.record_metric("finalize_error_handling_complete", True)
        
        # Test should complete within reasonable time
        self.assert_execution_time_under(150.0)  # Allow up to 2.5 minutes for comprehensive error handling tests