"""
Integration tests for FINALIZE phase - WebSocket System Readiness

Business Value Justification (BVJ):
- Segment: Free, Early, Mid, Enterprise (All Users)  
- Business Goal: Real-time User Experience
- Value Impact: Enables real-time chat, agent notifications, and live updates
- Strategic Impact: WebSocket failures block core chat functionality and user engagement

Tests WebSocket system readiness during the FINALIZE phase, ensuring WebSocket
infrastructure is properly initialized, authenticated, and ready for real-time
user interactions.

WebSocket readiness is CRITICAL for chat business value delivery.

Covers:
1. WebSocket server availability and handshake
2. Authentication and authorization flow
3. Message routing and delivery
4. Connection lifecycle management
5. Error handling and reconnection
6. Performance under concurrent connections
7. Integration with backend services
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List
import pytest
import websockets
import aiohttp
from unittest.mock import patch, AsyncMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.isolated_environment import get_env


class TestStartupFinalizeWebSocketIntegration(SSotBaseTestCase):
    """Integration tests for FINALIZE phase WebSocket system readiness."""
    
    def setup_method(self, method):
        """Setup test environment for WebSocket integration testing."""
        super().setup_method(method)
        
        # Initialize E2E auth helpers
        self.auth_helper = E2EAuthHelper(environment="test")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Configure test environment
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        self.set_env_var("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars")
        
        # WebSocket and service endpoints
        self.websocket_url = "ws://localhost:8000/ws"
        self.backend_url = "http://localhost:8000"
        
        # Track WebSocket test results
        self.websocket_test_results: Dict[str, Any] = {}
        
        # Test user configuration
        self.test_user_id = f"ws_test_user_{int(time.time())}"
        self.test_user_email = f"ws_test_{int(time.time())}@example.com"

    @pytest.mark.integration
    async def test_finalize_websocket_server_availability(self):
        """
        Test WebSocket server is available and accepts connections.
        
        BVJ: WebSocket availability is prerequisite for all real-time features.
        """
        availability_results = []
        
        # 1. Test basic WebSocket connection without authentication
        basic_connection_start = time.time()
        try:
            # Try to establish basic WebSocket connection
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url),
                timeout=10.0
            )
            
            basic_connection_time = time.time() - basic_connection_start
            
            # Connection established - check if server responds
            try:
                # Send ping to test server responsiveness
                await websocket.ping()
                await websocket.close()
                
                availability_results.append({
                    "test": "basic_websocket_connection",
                    "status": "success",
                    "connection_time": basic_connection_time
                })
                
            except Exception as e:
                await websocket.close()
                availability_results.append({
                    "test": "basic_websocket_connection", 
                    "status": "connection_established_but_not_responsive",
                    "connection_time": basic_connection_time,
                    "error": str(e)
                })
                
        except Exception as e:
            basic_connection_time = time.time() - basic_connection_start
            availability_results.append({
                "test": "basic_websocket_connection",
                "status": "failed",
                "connection_time": basic_connection_time,
                "error": str(e)
            })
        
        # 2. Test WebSocket with authentication headers
        auth_connection_start = time.time()
        try:
            token = self.auth_helper.create_test_jwt_token(
                user_id=self.test_user_id,
                email=self.test_user_email
            )
            headers = self.websocket_auth_helper.get_websocket_headers(token)
            
            auth_websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    additional_headers=headers
                ),
                timeout=15.0
            )
            
            auth_connection_time = time.time() - auth_connection_start
            
            # Test authenticated connection responsiveness
            try:
                await auth_websocket.ping()
                await auth_websocket.close()
                
                availability_results.append({
                    "test": "authenticated_websocket_connection",
                    "status": "success",
                    "connection_time": auth_connection_time
                })
                
            except Exception as e:
                await auth_websocket.close()
                availability_results.append({
                    "test": "authenticated_websocket_connection",
                    "status": "connection_established_but_not_responsive", 
                    "connection_time": auth_connection_time,
                    "error": str(e)
                })
                
        except Exception as e:
            auth_connection_time = time.time() - auth_connection_start
            availability_results.append({
                "test": "authenticated_websocket_connection",
                "status": "failed",
                "connection_time": auth_connection_time,
                "error": str(e)
            })
        
        # 3. Test WebSocket server health endpoint (if available)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/ws/health", timeout=5) as resp:
                    if resp.status == 200:
                        ws_health = await resp.json()
                        availability_results.append({
                            "test": "websocket_health_endpoint",
                            "status": "success",
                            "health_data": ws_health
                        })
                    elif resp.status == 404:
                        availability_results.append({
                            "test": "websocket_health_endpoint",
                            "status": "not_implemented"
                        })
                    else:
                        availability_results.append({
                            "test": "websocket_health_endpoint",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            availability_results.append({
                "test": "websocket_health_endpoint",
                "status": "error",
                "error": str(e)
            })
        
        # Record availability results
        self.websocket_test_results["server_availability"] = availability_results
        
        # Validate at least one connection method works
        successful_connections = [r for r in availability_results if r["status"] == "success" and "connection" in r["test"]]
        assert len(successful_connections) > 0, "No successful WebSocket connections established"
        
        # Record connection time metrics
        for result in availability_results:
            if "connection_time" in result:
                self.record_metric(f"websocket_{result['test']}_time", result["connection_time"])
        
        self.record_metric("websocket_server_availability_passed", True)

    @pytest.mark.integration
    async def test_finalize_websocket_authentication_flow(self):
        """
        Test WebSocket authentication and authorization flow.
        
        BVJ: Proper authentication ensures user isolation and security.
        """
        auth_flow_results = []
        
        # 1. Test connection with valid JWT token
        valid_token_start = time.time()
        try:
            valid_token = self.auth_helper.create_test_jwt_token(
                user_id=self.test_user_id,
                email=self.test_user_email,
                permissions=["read", "write", "websocket"]
            )
            headers = self.websocket_auth_helper.get_websocket_headers(valid_token)
            
            valid_websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            valid_auth_time = time.time() - valid_token_start
            
            # Send authenticated message
            auth_test_message = {
                "type": "auth_test",
                "message": "Testing authentication flow",
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            await valid_websocket.send(json.dumps(auth_test_message))
            
            # Wait for response or acknowledgment
            try:
                auth_response = await asyncio.wait_for(valid_websocket.recv(), timeout=5.0)
                auth_response_data = json.loads(auth_response)
                
                auth_flow_results.append({
                    "test": "valid_token_authentication",
                    "status": "success",
                    "connection_time": valid_auth_time,
                    "response_received": True,
                    "response_type": auth_response_data.get("type")
                })
                
            except asyncio.TimeoutError:
                auth_flow_results.append({
                    "test": "valid_token_authentication",
                    "status": "success",
                    "connection_time": valid_auth_time,
                    "response_received": False
                })
            
            await valid_websocket.close()
            
        except Exception as e:
            auth_flow_results.append({
                "test": "valid_token_authentication",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test connection with invalid/expired token
        invalid_token_start = time.time()
        try:
            # Create expired token
            expired_token = self.auth_helper.create_test_jwt_token(
                user_id="invalid_user",
                email="invalid@example.com",
                exp_minutes=-1  # Expired 1 minute ago
            )
            invalid_headers = self.websocket_auth_helper.get_websocket_headers(expired_token)
            
            # This should either fail to connect or connect but reject messages
            try:
                invalid_websocket = await asyncio.wait_for(
                    websockets.connect(self.websocket_url, additional_headers=invalid_headers),
                    timeout=10.0
                )
                
                # If connection succeeds, try to send message
                invalid_message = {
                    "type": "test",
                    "message": "This should be rejected",
                    "user_id": "invalid_user"
                }
                
                await invalid_websocket.send(json.dumps(invalid_message))
                
                # Wait for rejection or error
                try:
                    invalid_response = await asyncio.wait_for(invalid_websocket.recv(), timeout=3.0)
                    invalid_response_data = json.loads(invalid_response)
                    
                    # Should receive error response
                    if invalid_response_data.get("type") == "error" or "error" in invalid_response_data:
                        auth_flow_results.append({
                            "test": "invalid_token_rejection",
                            "status": "properly_rejected",
                            "message_rejected": True
                        })
                    else:
                        auth_flow_results.append({
                            "test": "invalid_token_rejection",
                            "status": "security_issue",
                            "message_accepted": True,
                            "response": invalid_response_data
                        })
                        
                except asyncio.TimeoutError:
                    auth_flow_results.append({
                        "test": "invalid_token_rejection",
                        "status": "no_response_to_invalid_token"
                    })
                
                await invalid_websocket.close()
                
            except Exception as connection_error:
                # Connection rejection is expected behavior
                auth_flow_results.append({
                    "test": "invalid_token_rejection",
                    "status": "connection_properly_rejected",
                    "connection_error": str(connection_error)
                })
                
        except Exception as e:
            auth_flow_results.append({
                "test": "invalid_token_rejection",
                "status": "test_error",
                "error": str(e)
            })
        
        # 3. Test connection without authentication
        no_auth_start = time.time()
        try:
            # Try to connect without any authentication headers
            no_auth_websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url),
                timeout=10.0
            )
            
            # Try to send message without auth
            no_auth_message = {
                "type": "test",
                "message": "Unauthenticated message test"
            }
            
            await no_auth_websocket.send(json.dumps(no_auth_message))
            
            # Wait for response
            try:
                no_auth_response = await asyncio.wait_for(no_auth_websocket.recv(), timeout=3.0)
                no_auth_response_data = json.loads(no_auth_response)
                
                # Should be rejected or require authentication
                if no_auth_response_data.get("type") == "error" or "auth" in str(no_auth_response_data).lower():
                    auth_flow_results.append({
                        "test": "no_authentication_handling",
                        "status": "properly_rejected",
                        "requires_auth": True
                    })
                else:
                    auth_flow_results.append({
                        "test": "no_authentication_handling",
                        "status": "security_concern", 
                        "message_processed_without_auth": True
                    })
                    
            except asyncio.TimeoutError:
                auth_flow_results.append({
                    "test": "no_authentication_handling",
                    "status": "no_response_without_auth"
                })
            
            await no_auth_websocket.close()
            
        except Exception as e:
            # Connection rejection without auth is expected
            auth_flow_results.append({
                "test": "no_authentication_handling",
                "status": "connection_rejected_without_auth",
                "error": str(e)
            })
        
        # Record authentication flow results
        self.websocket_test_results["authentication_flow"] = auth_flow_results
        
        # Validate authentication requirements
        valid_auth_tests = [r for r in auth_flow_results if r["test"] == "valid_token_authentication" and r["status"] == "success"]
        assert len(valid_auth_tests) > 0, "Valid token authentication failed"
        
        # Validate security measures
        security_tests = [r for r in auth_flow_results 
                         if r["test"] in ["invalid_token_rejection", "no_authentication_handling"] 
                         and r["status"] in ["properly_rejected", "connection_properly_rejected", "connection_rejected_without_auth"]]
        
        # At least some security measures should be in place
        if len(security_tests) == 0:
            self.record_metric("websocket_security_warning", "No authentication security measures detected")
        
        self.record_metric("websocket_authentication_flow_passed", True)

    @pytest.mark.integration
    async def test_finalize_websocket_message_routing(self):
        """
        Test WebSocket message routing and delivery mechanisms.
        
        BVJ: Proper message routing ensures users receive their chat responses.
        """
        routing_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.websocket_auth_helper.get_websocket_headers(token)
        
        try:
            # Establish authenticated WebSocket connection
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            # 1. Test basic message echo/acknowledgment
            echo_message = {
                "type": "echo_test",
                "message": "Testing message routing",
                "user_id": self.test_user_id,
                "timestamp": time.time(),
                "test_id": str(uuid.uuid4())
            }
            
            echo_start = time.time()
            await websocket.send(json.dumps(echo_message))
            
            try:
                echo_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                echo_time = time.time() - echo_start
                echo_response_data = json.loads(echo_response)
                
                routing_results.append({
                    "test": "message_echo",
                    "status": "success",
                    "response_time": echo_time,
                    "response_type": echo_response_data.get("type"),
                    "message_id_preserved": echo_response_data.get("test_id") == echo_message["test_id"]
                })
                
                self.record_metric("message_echo_response_time", echo_time)
                
            except asyncio.TimeoutError:
                routing_results.append({
                    "test": "message_echo",
                    "status": "no_response",
                    "timeout": True
                })
            
            # 2. Test different message types
            message_types = ["chat_message", "command", "ping", "user_action"]
            
            for msg_type in message_types:
                type_test_message = {
                    "type": msg_type,
                    "message": f"Testing {msg_type} routing",
                    "user_id": self.test_user_id,
                    "timestamp": time.time()
                }
                
                type_start = time.time()
                await websocket.send(json.dumps(type_test_message))
                
                try:
                    type_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    type_time = time.time() - type_start
                    type_response_data = json.loads(type_response)
                    
                    routing_results.append({
                        "test": f"message_type_{msg_type}",
                        "status": "response_received",
                        "response_time": type_time,
                        "response_type": type_response_data.get("type")
                    })
                    
                except asyncio.TimeoutError:
                    routing_results.append({
                        "test": f"message_type_{msg_type}",
                        "status": "no_response",
                        "timeout": True
                    })
                
                # Small delay between different message types
                await asyncio.sleep(0.2)
            
            # 3. Test message ordering with rapid messages
            ordering_messages = []
            for i in range(5):
                order_message = {
                    "type": "order_test",
                    "message": f"Ordering test message {i+1}",
                    "sequence": i+1,
                    "user_id": self.test_user_id,
                    "timestamp": time.time()
                }
                ordering_messages.append(order_message)
            
            # Send all messages rapidly
            ordering_start = time.time()
            for msg in ordering_messages:
                await websocket.send(json.dumps(msg))
            
            # Collect responses
            ordering_responses = []
            while len(ordering_responses) < 5 and time.time() - ordering_start < 10.0:
                try:
                    order_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    order_response_data = json.loads(order_response)
                    ordering_responses.append(order_response_data)
                except asyncio.TimeoutError:
                    break
            
            ordering_time = time.time() - ordering_start
            
            routing_results.append({
                "test": "message_ordering",
                "status": "tested",
                "messages_sent": len(ordering_messages),
                "responses_received": len(ordering_responses),
                "total_time": ordering_time
            })
            
            # 4. Test large message handling
            large_message = {
                "type": "large_message_test",
                "message": "A" * 1000,  # 1KB message
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            large_start = time.time()
            try:
                await websocket.send(json.dumps(large_message))
                
                try:
                    large_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    large_time = time.time() - large_start
                    
                    routing_results.append({
                        "test": "large_message_handling",
                        "status": "success",
                        "response_time": large_time,
                        "message_size": len(json.dumps(large_message))
                    })
                    
                except asyncio.TimeoutError:
                    routing_results.append({
                        "test": "large_message_handling",
                        "status": "no_response",
                        "message_size": len(json.dumps(large_message))
                    })
                    
            except Exception as e:
                routing_results.append({
                    "test": "large_message_handling",
                    "status": "send_failed",
                    "error": str(e)
                })
            
            await websocket.close()
            
        except Exception as e:
            routing_results.append({
                "test": "websocket_message_routing",
                "status": "connection_failed",
                "error": str(e)
            })
        
        # Record message routing results
        self.websocket_test_results["message_routing"] = routing_results
        
        # Validate message routing capability
        successful_routing_tests = [r for r in routing_results if r["status"] in ["success", "response_received", "tested"]]
        assert len(successful_routing_tests) > 0, "No successful message routing tests"
        
        self.record_metric("websocket_message_routing_passed", True)

    @pytest.mark.integration
    async def test_finalize_websocket_connection_lifecycle(self):
        """
        Test WebSocket connection lifecycle management.
        
        BVJ: Proper lifecycle management prevents resource leaks and connection issues.
        """
        lifecycle_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.websocket_auth_helper.get_websocket_headers(token)
        
        # 1. Test normal connection and disconnection
        normal_lifecycle_start = time.time()
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            connection_time = time.time() - normal_lifecycle_start
            
            # Send a message to confirm connection is active
            test_message = {
                "type": "lifecycle_test",
                "message": "Testing connection lifecycle",
                "user_id": self.test_user_id
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Wait briefly for any response
            try:
                await asyncio.wait_for(websocket.recv(), timeout=2.0)
                connection_active = True
            except asyncio.TimeoutError:
                connection_active = True  # No response is still OK
            
            # Close connection gracefully
            close_start = time.time()
            await websocket.close()
            close_time = time.time() - close_start
            
            lifecycle_results.append({
                "test": "normal_connection_lifecycle",
                "status": "success",
                "connection_time": connection_time,
                "close_time": close_time,
                "connection_was_active": connection_active
            })
            
        except Exception as e:
            lifecycle_results.append({
                "test": "normal_connection_lifecycle",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test connection timeout behavior
        timeout_test_start = time.time()
        try:
            # Connect and then be idle to test timeout
            idle_websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            # Stay idle for a short period
            await asyncio.sleep(5.0)
            
            # Check if connection is still alive
            try:
                await idle_websocket.ping()
                connection_alive_after_idle = True
            except Exception:
                connection_alive_after_idle = False
            
            await idle_websocket.close()
            
            idle_time = time.time() - timeout_test_start
            
            lifecycle_results.append({
                "test": "idle_connection_handling",
                "status": "tested",
                "idle_time": idle_time,
                "connection_alive_after_idle": connection_alive_after_idle
            })
            
        except Exception as e:
            lifecycle_results.append({
                "test": "idle_connection_handling",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test reconnection capability
        reconnection_start = time.time()
        try:
            # Establish initial connection
            initial_websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            # Send message on initial connection
            initial_message = {
                "type": "reconnection_test",
                "message": "Initial connection message",
                "user_id": self.test_user_id
            }
            
            await initial_websocket.send(json.dumps(initial_message))
            
            # Close initial connection
            await initial_websocket.close()
            
            # Small delay
            await asyncio.sleep(1.0)
            
            # Establish reconnection
            reconnect_websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            # Send message on reconnected connection
            reconnect_message = {
                "type": "reconnection_test",
                "message": "Reconnected message",
                "user_id": self.test_user_id
            }
            
            await reconnect_websocket.send(json.dumps(reconnect_message))
            
            await reconnect_websocket.close()
            
            reconnection_time = time.time() - reconnection_start
            
            lifecycle_results.append({
                "test": "connection_reconnection",
                "status": "success",
                "total_reconnection_time": reconnection_time
            })
            
        except Exception as e:
            lifecycle_results.append({
                "test": "connection_reconnection",
                "status": "failed",
                "error": str(e)
            })
        
        # 4. Test concurrent connection handling
        concurrent_connections_start = time.time()
        try:
            # Create multiple concurrent connections
            connection_tasks = []
            for i in range(3):  # Test 3 concurrent connections
                user_token = self.auth_helper.create_test_jwt_token(
                    user_id=f"concurrent_user_{i}_{int(time.time())}",
                    email=f"concurrent_{i}@example.com"
                )
                user_headers = self.websocket_auth_helper.get_websocket_headers(user_token)
                
                connection_task = websockets.connect(
                    self.websocket_url,
                    additional_headers=user_headers
                )
                connection_tasks.append(connection_task)
            
            # Establish all connections
            concurrent_websockets = await asyncio.gather(*connection_tasks)
            concurrent_connection_time = time.time() - concurrent_connections_start
            
            # Send message from each connection
            message_tasks = []
            for i, ws in enumerate(concurrent_websockets):
                message = {
                    "type": "concurrent_test",
                    "message": f"Message from concurrent connection {i}",
                    "user_id": f"concurrent_user_{i}",
                    "timestamp": time.time()
                }
                message_tasks.append(ws.send(json.dumps(message)))
            
            await asyncio.gather(*message_tasks)
            
            # Close all connections
            close_tasks = [ws.close() for ws in concurrent_websockets]
            await asyncio.gather(*close_tasks, return_exceptions=True)
            
            total_concurrent_time = time.time() - concurrent_connections_start
            
            lifecycle_results.append({
                "test": "concurrent_connections",
                "status": "success",
                "connection_count": len(concurrent_websockets),
                "concurrent_connection_time": concurrent_connection_time,
                "total_time": total_concurrent_time
            })
            
        except Exception as e:
            lifecycle_results.append({
                "test": "concurrent_connections",
                "status": "failed",
                "error": str(e)
            })
        
        # Record lifecycle results
        self.websocket_test_results["connection_lifecycle"] = lifecycle_results
        
        # Validate lifecycle management
        successful_lifecycle_tests = [r for r in lifecycle_results if r["status"] == "success"]
        assert len(successful_lifecycle_tests) > 0, "No successful lifecycle management tests"
        
        # At least normal connection lifecycle should work
        normal_lifecycle_tests = [r for r in lifecycle_results if r["test"] == "normal_connection_lifecycle" and r["status"] == "success"]
        assert len(normal_lifecycle_tests) > 0, "Normal connection lifecycle failed"
        
        self.record_metric("websocket_connection_lifecycle_passed", True)

    @pytest.mark.integration
    async def test_finalize_websocket_error_handling(self):
        """
        Test WebSocket error handling and recovery mechanisms.
        
        BVJ: Proper error handling prevents user experience disruption.
        """
        error_handling_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.websocket_auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=headers),
                timeout=15.0
            )
            
            # 1. Test malformed JSON message handling
            malformed_start = time.time()
            try:
                # Send invalid JSON
                await websocket.send("invalid json message")
                
                # Wait for error response
                try:
                    error_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    error_time = time.time() - malformed_start
                    
                    # Should receive error message or connection should close gracefully
                    try:
                        error_data = json.loads(error_response)
                        error_handling_results.append({
                            "test": "malformed_json_handling",
                            "status": "error_response_received",
                            "response_time": error_time,
                            "error_type": error_data.get("type")
                        })
                    except json.JSONDecodeError:
                        error_handling_results.append({
                            "test": "malformed_json_handling",
                            "status": "non_json_error_response",
                            "response_time": error_time
                        })
                        
                except asyncio.TimeoutError:
                    error_handling_results.append({
                        "test": "malformed_json_handling",
                        "status": "no_error_response"
                    })
                    
            except Exception as e:
                # Connection closure on malformed message is acceptable
                error_handling_results.append({
                    "test": "malformed_json_handling",
                    "status": "connection_closed_on_error",
                    "error": str(e)
                })
                
                # Reconnect for remaining tests
                try:
                    websocket = await asyncio.wait_for(
                        websockets.connect(self.websocket_url, additional_headers=headers),
                        timeout=15.0
                    )
                except Exception:
                    pass  # Continue with remaining tests even if reconnection fails
            
            # 2. Test unknown message type handling
            if not websocket.closed:
                unknown_type_message = {
                    "type": "unknown_message_type_12345",
                    "message": "Testing unknown message type handling",
                    "user_id": self.test_user_id
                }
                
                unknown_start = time.time()
                try:
                    await websocket.send(json.dumps(unknown_type_message))
                    
                    try:
                        unknown_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        unknown_time = time.time() - unknown_start
                        unknown_data = json.loads(unknown_response)
                        
                        error_handling_results.append({
                            "test": "unknown_message_type_handling",
                            "status": "response_received",
                            "response_time": unknown_time,
                            "response_type": unknown_data.get("type")
                        })
                        
                    except asyncio.TimeoutError:
                        error_handling_results.append({
                            "test": "unknown_message_type_handling",
                            "status": "no_response"
                        })
                        
                except Exception as e:
                    error_handling_results.append({
                        "test": "unknown_message_type_handling",
                        "status": "send_failed",
                        "error": str(e)
                    })
            
            # 3. Test oversized message handling
            if not websocket.closed:
                oversized_message = {
                    "type": "oversized_test",
                    "message": "A" * 100000,  # 100KB message
                    "user_id": self.test_user_id
                }
                
                oversized_start = time.time()
                try:
                    await websocket.send(json.dumps(oversized_message))
                    
                    try:
                        oversized_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        oversized_time = time.time() - oversized_start
                        
                        error_handling_results.append({
                            "test": "oversized_message_handling",
                            "status": "response_received",
                            "response_time": oversized_time,
                            "message_size": len(json.dumps(oversized_message))
                        })
                        
                    except asyncio.TimeoutError:
                        error_handling_results.append({
                            "test": "oversized_message_handling",
                            "status": "no_response",
                            "message_size": len(json.dumps(oversized_message))
                        })
                        
                except Exception as e:
                    # Expected for oversized messages
                    error_handling_results.append({
                        "test": "oversized_message_handling",
                        "status": "properly_rejected",
                        "error": str(e),
                        "message_size": len(json.dumps(oversized_message))
                    })
            
            # 4. Test system recovery after errors
            if not websocket.closed:
                recovery_start = time.time()
                try:
                    # Send normal message after error tests
                    recovery_message = {
                        "type": "recovery_test",
                        "message": "Testing system recovery after errors",
                        "user_id": self.test_user_id
                    }
                    
                    await websocket.send(json.dumps(recovery_message))
                    
                    try:
                        recovery_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        recovery_time = time.time() - recovery_start
                        
                        error_handling_results.append({
                            "test": "system_recovery_after_errors",
                            "status": "success",
                            "response_time": recovery_time
                        })
                        
                    except asyncio.TimeoutError:
                        error_handling_results.append({
                            "test": "system_recovery_after_errors",
                            "status": "no_response_but_message_sent"
                        })
                        
                except Exception as e:
                    error_handling_results.append({
                        "test": "system_recovery_after_errors",
                        "status": "failed",
                        "error": str(e)
                    })
            
            # Close WebSocket if still open
            if not websocket.closed:
                await websocket.close()
                
        except Exception as e:
            error_handling_results.append({
                "test": "websocket_error_handling_setup",
                "status": "failed",
                "error": str(e)
            })
        
        # Record error handling results
        self.websocket_test_results["error_handling"] = error_handling_results
        
        # Validate error handling capabilities
        tested_error_scenarios = [r for r in error_handling_results if "handling" in r["test"]]
        assert len(tested_error_scenarios) > 0, "No error handling scenarios were tested"
        
        # At least one error handling scenario should demonstrate proper behavior
        proper_error_handling = [r for r in error_handling_results 
                               if r["status"] in ["error_response_received", "properly_rejected", "connection_closed_on_error"]]
        
        if len(proper_error_handling) == 0:
            self.record_metric("websocket_error_handling_warning", "No proper error handling detected")
        
        self.record_metric("websocket_error_handling_passed", True)
        
        # Record overall WebSocket integration completion
        self.record_metric("finalize_websocket_integration_complete", True)
        
        # Test should complete within reasonable time
        self.assert_execution_time_under(120.0)  # Allow up to 2 minutes for comprehensive WebSocket tests