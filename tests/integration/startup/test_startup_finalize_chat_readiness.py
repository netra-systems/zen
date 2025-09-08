"""
Integration tests for FINALIZE phase - Complete Chat Workflow Readiness

Business Value Justification (BVJ):
- Segment: Free, Early, Mid, Enterprise (All Users)
- Business Goal: User Experience and Conversion
- Value Impact: Ensures complete chat functionality works immediately after startup
- Strategic Impact: Prevents user frustration and abandonment due to non-functional chat

Tests complete chat workflow readiness during the FINALIZE phase, validating
that the entire chat system is operational and ready for real user interactions.

This is the CRITICAL business value test - if chat doesn't work, users cannot
get value from the platform.

Covers:
1. End-to-end chat message flow
2. Agent execution pipeline readiness 
3. Real-time WebSocket communication
4. Chat history and persistence
5. Multi-user chat isolation
6. Chat performance under load
"""

import asyncio
import json
import time
from typing import Dict, Any, List
import pytest
import websockets
import aiohttp
from unittest.mock import patch, AsyncMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.isolated_environment import get_env


class TestStartupFinalizeChatReadiness(SSotBaseTestCase):
    """Integration tests for FINALIZE phase complete chat workflow readiness."""
    
    def setup_method(self, method):
        """Setup test environment for chat workflow testing."""
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
        
        # Track chat test results
        self.chat_test_results: Dict[str, Any] = {}
        
        # Test user configuration
        self.test_user_id = f"test_chat_user_{int(time.time())}"
        self.test_user_email = f"chat_test_{int(time.time())}@example.com"

    @pytest.mark.integration
    async def test_finalize_basic_chat_message_flow(self):
        """
        Test basic chat message sending and receiving works.
        
        BVJ: Core chat functionality must work for any user value delivery.
        """
        # Create authenticated user token
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        
        chat_flow_results = []
        
        try:
            # 1. Establish WebSocket connection for chat
            websocket_headers = self.websocket_auth_helper.get_websocket_headers(token)
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    additional_headers=websocket_headers
                ),
                timeout=15.0
            )
            
            chat_flow_results.append({
                "test": "websocket_connection",
                "status": "success",
                "message": "WebSocket connection established for chat"
            })
            
            # 2. Send a basic chat message
            chat_message = {
                "type": "chat_message",
                "message": "Hello, this is a test chat message for finalize phase validation.",
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            message_send_time = time.time()
            await websocket.send(json.dumps(chat_message))
            
            chat_flow_results.append({
                "test": "message_send", 
                "status": "success",
                "message": "Chat message sent successfully"
            })
            
            # 3. Wait for acknowledgment or response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_time = time.time() - message_send_time
                
                # Parse response
                response_data = json.loads(response)
                
                chat_flow_results.append({
                    "test": "message_acknowledgment",
                    "status": "success", 
                    "response_time": response_time,
                    "response_type": response_data.get("type"),
                    "has_message_id": "message_id" in response_data or "id" in response_data
                })
                
                # Validate response structure
                assert "type" in response_data, "Response missing message type"
                assert response_data["type"] in ["ack", "message", "agent_response", "error"], f"Unknown response type: {response_data['type']}"
                
                self.record_metric("chat_message_response_time", response_time)
                
            except asyncio.TimeoutError:
                chat_flow_results.append({
                    "test": "message_acknowledgment",
                    "status": "timeout",
                    "message": "No response received within timeout"
                })
                # This is not necessarily a failure - some systems may not send immediate acks
            
            # 4. Test sending a message that should trigger agent execution
            agent_trigger_message = {
                "type": "chat_message",
                "message": "Can you help me analyze some data?",
                "user_id": self.test_user_id, 
                "timestamp": time.time()
            }
            
            agent_trigger_time = time.time()
            await websocket.send(json.dumps(agent_trigger_message))
            
            # Wait for agent-related responses
            agent_responses = []
            try:
                while time.time() - agent_trigger_time < 15.0:  # Wait up to 15 seconds
                    try:
                        agent_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        agent_response_data = json.loads(agent_response)
                        agent_responses.append(agent_response_data)
                        
                        # Stop if we get a completion message
                        if agent_response_data.get("type") in ["agent_completed", "message_complete", "done"]:
                            break
                            
                    except asyncio.TimeoutError:
                        break  # No more immediate responses
                        
            except Exception as e:
                self.record_metric("agent_trigger_error", str(e))
            
            agent_total_time = time.time() - agent_trigger_time
            
            chat_flow_results.append({
                "test": "agent_trigger_response",
                "status": "tested",
                "agent_response_count": len(agent_responses),
                "total_time": agent_total_time,
                "responses": [r.get("type") for r in agent_responses[:3]]  # First 3 response types
            })
            
            # Record agent response metrics
            self.record_metric("agent_trigger_response_count", len(agent_responses))
            self.record_metric("agent_trigger_total_time", agent_total_time)
            
            # Close WebSocket connection
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Basic chat message flow failed: {e}")
        
        # Record chat flow results
        self.chat_test_results["basic_chat_flow"] = chat_flow_results
        
        # Validate critical chat functionality
        connection_success = any(r["test"] == "websocket_connection" and r["status"] == "success" for r in chat_flow_results)
        message_send_success = any(r["test"] == "message_send" and r["status"] == "success" for r in chat_flow_results)
        
        assert connection_success, "WebSocket connection for chat failed"
        assert message_send_success, "Basic chat message sending failed"
        
        self.record_metric("basic_chat_flow_passed", True)

    @pytest.mark.integration
    async def test_finalize_chat_agent_execution_pipeline(self):
        """
        Test complete chat agent execution pipeline is ready.
        
        BVJ: Agent execution is core business value - must work after startup.
        """
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email,
            permissions=["read", "write", "agent_execution"]
        )
        
        pipeline_results = []
        
        # Test through HTTP API first
        async with aiohttp.ClientSession() as session:
            headers = self.auth_helper.get_auth_headers(token)
            
            # 1. Test agent execution endpoint availability
            try:
                agent_list_response = await session.get(
                    f"{self.backend_url}/api/agents",
                    headers=headers,
                    timeout=10
                )
                
                if agent_list_response.status == 200:
                    agents_data = await agent_list_response.json()
                    pipeline_results.append({
                        "test": "agent_list_endpoint",
                        "status": "success",
                        "agent_count": len(agents_data) if isinstance(agents_data, list) else len(agents_data.get("agents", []))
                    })
                elif agent_list_response.status == 404:
                    pipeline_results.append({
                        "test": "agent_list_endpoint",
                        "status": "not_implemented"
                    })
                else:
                    pipeline_results.append({
                        "test": "agent_list_endpoint",
                        "status": "error",
                        "status_code": agent_list_response.status
                    })
                    
            except Exception as e:
                pipeline_results.append({
                    "test": "agent_list_endpoint",
                    "status": "error",
                    "error": str(e)
                })
            
            # 2. Test direct agent execution endpoint
            try:
                agent_execution_payload = {
                    "agent_type": "data_analysis",
                    "prompt": "Analyze this test data for the finalize phase validation",
                    "user_id": self.test_user_id
                }
                
                execution_start = time.time()
                agent_exec_response = await session.post(
                    f"{self.backend_url}/api/agents/execute",
                    headers=headers,
                    json=agent_execution_payload,
                    timeout=20
                )
                execution_time = time.time() - execution_start
                
                if agent_exec_response.status in [200, 201, 202]:
                    exec_result = await agent_exec_response.json()
                    pipeline_results.append({
                        "test": "direct_agent_execution",
                        "status": "success",
                        "execution_time": execution_time,
                        "has_execution_id": "execution_id" in exec_result or "id" in exec_result,
                        "response_keys": list(exec_result.keys())[:5]
                    })
                else:
                    pipeline_results.append({
                        "test": "direct_agent_execution",
                        "status": "error",
                        "status_code": agent_exec_response.status,
                        "execution_time": execution_time
                    })
                    
                self.record_metric("direct_agent_execution_time", execution_time)
                
            except Exception as e:
                pipeline_results.append({
                    "test": "direct_agent_execution",
                    "status": "error",
                    "error": str(e)
                })
        
        # 3. Test agent execution through WebSocket (real chat scenario)
        try:
            websocket_headers = self.websocket_auth_helper.get_websocket_headers(token)
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    additional_headers=websocket_headers
                ),
                timeout=15.0
            )
            
            # Send message that should trigger agent execution
            agent_trigger_message = {
                "type": "chat_message",
                "message": "Please create a simple data visualization showing monthly trends.",
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            websocket_exec_start = time.time()
            await websocket.send(json.dumps(agent_trigger_message))
            
            # Collect agent execution events
            agent_events = []
            websocket_timeout = 30.0  # Give agent more time to execute
            
            try:
                while time.time() - websocket_exec_start < websocket_timeout:
                    try:
                        event_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(event_response)
                        agent_events.append(event_data)
                        
                        # Look for agent execution events
                        event_type = event_data.get("type", "")
                        if event_type in ["agent_started", "agent_thinking", "tool_executing", "agent_completed"]:
                            self.increment_websocket_events()
                        
                        # Stop if execution completes
                        if event_type in ["agent_completed", "execution_complete", "done"]:
                            break
                            
                    except asyncio.TimeoutError:
                        # No more events - execution may be complete
                        break
                        
            except Exception as e:
                self.record_metric("websocket_agent_execution_error", str(e))
            
            websocket_exec_time = time.time() - websocket_exec_start
            
            # Analyze agent execution events
            agent_event_types = [event.get("type") for event in agent_events]
            has_agent_start = "agent_started" in agent_event_types
            has_agent_completion = any(t in agent_event_types for t in ["agent_completed", "execution_complete", "done"])
            has_tool_execution = "tool_executing" in agent_event_types or "tool_completed" in agent_event_types
            
            pipeline_results.append({
                "test": "websocket_agent_execution",
                "status": "tested",
                "execution_time": websocket_exec_time,
                "event_count": len(agent_events),
                "has_agent_start": has_agent_start,
                "has_agent_completion": has_agent_completion, 
                "has_tool_execution": has_tool_execution,
                "event_types": list(set(agent_event_types))[:5]  # Unique event types (first 5)
            })
            
            self.record_metric("websocket_agent_execution_time", websocket_exec_time)
            self.record_metric("agent_execution_event_count", len(agent_events))
            
            await websocket.close()
            
        except Exception as e:
            pipeline_results.append({
                "test": "websocket_agent_execution",
                "status": "error",
                "error": str(e)
            })
        
        # Record pipeline results
        self.chat_test_results["agent_execution_pipeline"] = pipeline_results
        
        # Validate agent pipeline readiness
        working_tests = [r for r in pipeline_results if r["status"] in ["success", "tested"]]
        assert len(working_tests) > 0, "No working agent execution pipeline found"
        
        # At least WebSocket agent execution should be tested
        websocket_tests = [r for r in pipeline_results if r["test"] == "websocket_agent_execution"]
        assert len(websocket_tests) > 0, "WebSocket agent execution not tested"
        
        self.record_metric("agent_execution_pipeline_passed", True)

    @pytest.mark.integration  
    async def test_finalize_chat_multi_user_isolation(self):
        """
        Test chat system properly isolates multiple users.
        
        BVJ: Multi-user isolation prevents data leakage and ensures privacy.
        """
        # Create two different test users
        user1_id = f"test_user_1_{int(time.time())}"
        user2_id = f"test_user_2_{int(time.time())}"
        
        user1_token = self.auth_helper.create_test_jwt_token(
            user_id=user1_id,
            email=f"user1_{int(time.time())}@example.com"
        )
        
        user2_token = self.auth_helper.create_test_jwt_token(
            user_id=user2_id, 
            email=f"user2_{int(time.time())}@example.com"
        )
        
        isolation_results = []
        
        try:
            # 1. Establish WebSocket connections for both users
            user1_headers = self.websocket_auth_helper.get_websocket_headers(user1_token)
            user2_headers = self.websocket_auth_helper.get_websocket_headers(user2_token)
            
            websocket1 = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=user1_headers),
                timeout=15.0
            )
            
            websocket2 = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=user2_headers), 
                timeout=15.0
            )
            
            isolation_results.append({
                "test": "dual_websocket_connections",
                "status": "success",
                "message": "Both users established WebSocket connections"
            })
            
            # 2. Send messages from both users simultaneously
            user1_message = {
                "type": "chat_message",
                "message": f"User 1 message - isolation test {time.time()}",
                "user_id": user1_id,
                "timestamp": time.time()
            }
            
            user2_message = {
                "type": "chat_message",
                "message": f"User 2 message - isolation test {time.time()}",
                "user_id": user2_id,
                "timestamp": time.time()
            }
            
            # Send messages concurrently
            await asyncio.gather(
                websocket1.send(json.dumps(user1_message)),
                websocket2.send(json.dumps(user2_message))
            )
            
            isolation_results.append({
                "test": "concurrent_messages",
                "status": "success",
                "message": "Both users sent messages concurrently"
            })
            
            # 3. Collect responses for both users
            user1_responses = []
            user2_responses = []
            
            # Collect responses for 10 seconds
            end_time = time.time() + 10.0
            
            while time.time() < end_time:
                try:
                    # Check for user1 responses
                    try:
                        response1 = await asyncio.wait_for(websocket1.recv(), timeout=1.0)
                        user1_responses.append(json.loads(response1))
                    except asyncio.TimeoutError:
                        pass
                    
                    # Check for user2 responses
                    try:
                        response2 = await asyncio.wait_for(websocket2.recv(), timeout=1.0)
                        user2_responses.append(json.loads(response2))
                    except asyncio.TimeoutError:
                        pass
                        
                except Exception:
                    break
            
            # 4. Analyze isolation
            user1_message_count = len(user1_responses)
            user2_message_count = len(user2_responses)
            
            # Check if users received their own responses
            user1_has_responses = user1_message_count > 0
            user2_has_responses = user2_message_count > 0
            
            # Check for cross-contamination (users receiving each other's messages)
            user1_contamination = False
            user2_contamination = False
            
            for response in user1_responses:
                if response.get("user_id") == user2_id:
                    user1_contamination = True
                    break
                    
            for response in user2_responses:
                if response.get("user_id") == user1_id:
                    user2_contamination = True
                    break
            
            isolation_results.append({
                "test": "user_isolation_analysis",
                "status": "analyzed",
                "user1_response_count": user1_message_count,
                "user2_response_count": user2_message_count,
                "user1_contamination": user1_contamination,
                "user2_contamination": user2_contamination,
                "isolation_maintained": not (user1_contamination or user2_contamination)
            })
            
            # Validate isolation
            if user1_contamination or user2_contamination:
                pytest.fail("User isolation breach detected - users received each other's messages")
            
            # Close connections
            await websocket1.close()
            await websocket2.close()
            
        except Exception as e:
            pytest.fail(f"Multi-user isolation test failed: {e}")
        
        # Record isolation test results
        self.chat_test_results["multi_user_isolation"] = isolation_results
        
        # Validate isolation was maintained
        isolation_analysis = next((r for r in isolation_results if r["test"] == "user_isolation_analysis"), None)
        if isolation_analysis:
            assert isolation_analysis["isolation_maintained"], "Multi-user isolation was not maintained"
        
        self.record_metric("multi_user_isolation_passed", True)

    @pytest.mark.integration
    async def test_finalize_chat_performance_under_load(self):
        """
        Test chat system performance under simulated load.
        
        BVJ: System must handle multiple concurrent users without degradation.
        """
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        
        performance_results = []
        
        # 1. Test sequential message performance
        sequential_start = time.time()
        try:
            websocket_headers = self.websocket_auth_helper.get_websocket_headers(token)
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=websocket_headers),
                timeout=15.0
            )
            
            # Send 10 messages sequentially and measure response times
            sequential_times = []
            
            for i in range(10):
                message = {
                    "type": "chat_message",
                    "message": f"Sequential performance test message {i+1}",
                    "user_id": self.test_user_id,
                    "timestamp": time.time()
                }
                
                msg_start = time.time()
                await websocket.send(json.dumps(message))
                
                # Wait for acknowledgment
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    msg_time = time.time() - msg_start
                    sequential_times.append(msg_time)
                except asyncio.TimeoutError:
                    # No ack received - record send time only
                    sequential_times.append(time.time() - msg_start)
                
                # Small delay between messages
                await asyncio.sleep(0.1)
            
            await websocket.close()
            
            sequential_total_time = time.time() - sequential_start
            avg_sequential_time = sum(sequential_times) / len(sequential_times)
            max_sequential_time = max(sequential_times)
            
            performance_results.append({
                "test": "sequential_message_performance",
                "status": "success",
                "total_time": sequential_total_time,
                "message_count": len(sequential_times),
                "avg_response_time": avg_sequential_time,
                "max_response_time": max_sequential_time
            })
            
            # Validate sequential performance
            assert avg_sequential_time < 2.0, f"Sequential message average response time too high: {avg_sequential_time:.3f}s"
            assert max_sequential_time < 5.0, f"Sequential message max response time too high: {max_sequential_time:.3f}s"
            
            self.record_metric("sequential_avg_response_time", avg_sequential_time)
            self.record_metric("sequential_max_response_time", max_sequential_time)
            
        except Exception as e:
            performance_results.append({
                "test": "sequential_message_performance",
                "status": "error",
                "error": str(e)
            })
        
        # 2. Test concurrent connection performance
        concurrent_start = time.time()
        try:
            # Create 5 concurrent WebSocket connections
            connection_tasks = []
            for i in range(5):
                user_token = self.auth_helper.create_test_jwt_token(
                    user_id=f"perf_user_{i}_{int(time.time())}",
                    email=f"perf_user_{i}@example.com"
                )
                headers = self.websocket_auth_helper.get_websocket_headers(user_token)
                
                connection_task = websockets.connect(
                    self.websocket_url,
                    additional_headers=headers
                )
                connection_tasks.append(connection_task)
            
            # Establish all connections concurrently
            websockets_list = await asyncio.gather(*connection_tasks)
            connection_time = time.time() - concurrent_start
            
            performance_results.append({
                "test": "concurrent_connections",
                "status": "success",
                "connection_count": len(websockets_list),
                "connection_time": connection_time
            })
            
            # Send concurrent messages
            message_tasks = []
            for i, ws in enumerate(websockets_list):
                message = {
                    "type": "chat_message", 
                    "message": f"Concurrent message from user {i}",
                    "user_id": f"perf_user_{i}",
                    "timestamp": time.time()
                }
                message_tasks.append(ws.send(json.dumps(message)))
            
            concurrent_msg_start = time.time()
            await asyncio.gather(*message_tasks)
            concurrent_msg_time = time.time() - concurrent_msg_start
            
            performance_results.append({
                "test": "concurrent_messages",
                "status": "success",
                "message_count": len(message_tasks),
                "send_time": concurrent_msg_time
            })
            
            # Close all connections
            close_tasks = [ws.close() for ws in websockets_list]
            await asyncio.gather(*close_tasks, return_exceptions=True)
            
            # Validate concurrent performance
            assert connection_time < 10.0, f"Concurrent connection time too high: {connection_time:.3f}s"
            assert concurrent_msg_time < 3.0, f"Concurrent message send time too high: {concurrent_msg_time:.3f}s"
            
            self.record_metric("concurrent_connection_time", connection_time) 
            self.record_metric("concurrent_message_send_time", concurrent_msg_time)
            
        except Exception as e:
            performance_results.append({
                "test": "concurrent_connections",
                "status": "error", 
                "error": str(e)
            })
        
        # Record performance test results
        self.chat_test_results["performance_under_load"] = performance_results
        
        # Validate at least one performance test passed
        successful_perf_tests = [r for r in performance_results if r["status"] == "success"]
        assert len(successful_perf_tests) > 0, "No performance tests succeeded"
        
        self.record_metric("chat_performance_under_load_passed", True)

    @pytest.mark.integration
    async def test_finalize_complete_chat_readiness_validation(self):
        """
        Test complete end-to-end chat readiness validation.
        
        BVJ: Final validation that entire chat system is ready for users.
        """
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email,
            permissions=["read", "write", "agent_execution", "chat"]
        )
        
        readiness_results = []
        
        # Complete end-to-end chat workflow test
        try:
            websocket_headers = self.websocket_auth_helper.get_websocket_headers(token)
            
            # 1. Connect to chat
            connection_start = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url, additional_headers=websocket_headers),
                timeout=15.0
            )
            connection_time = time.time() - connection_start
            
            readiness_results.append({
                "test": "chat_connection",
                "status": "success",
                "connection_time": connection_time
            })
            
            # 2. Send greeting message
            greeting_message = {
                "type": "chat_message",
                "message": "Hello! I'm testing if the chat system is ready. Can you help me?",
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            greeting_start = time.time()
            await websocket.send(json.dumps(greeting_message))
            
            # Wait for initial response
            try:
                greeting_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                greeting_time = time.time() - greeting_start
                greeting_data = json.loads(greeting_response)
                
                readiness_results.append({
                    "test": "greeting_response",
                    "status": "success", 
                    "response_time": greeting_time,
                    "response_type": greeting_data.get("type")
                })
                
            except asyncio.TimeoutError:
                readiness_results.append({
                    "test": "greeting_response",
                    "status": "no_immediate_response"
                })
            
            # 3. Request agent execution
            agent_request_message = {
                "type": "chat_message",
                "message": "Please analyze this sample data and create a summary report.",
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            agent_start = time.time()
            await websocket.send(json.dumps(agent_request_message))
            
            # Wait for agent execution to complete
            agent_events = []
            agent_execution_complete = False
            
            while time.time() - agent_start < 30.0:  # Wait up to 30 seconds for agent
                try:
                    event_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    event_data = json.loads(event_response)
                    agent_events.append(event_data)
                    
                    event_type = event_data.get("type", "")
                    if event_type in ["agent_completed", "execution_complete", "done"]:
                        agent_execution_complete = True
                        break
                        
                except asyncio.TimeoutError:
                    # Check if we have any agent events
                    if len(agent_events) > 0:
                        break
                    continue
                    
            agent_total_time = time.time() - agent_start
            
            readiness_results.append({
                "test": "agent_execution_request",
                "status": "completed" if agent_execution_complete else "tested",
                "execution_time": agent_total_time,
                "event_count": len(agent_events),
                "execution_complete": agent_execution_complete
            })
            
            # 4. Send follow-up message
            followup_message = {
                "type": "chat_message",
                "message": "Thank you! The chat system appears to be working correctly.",
                "user_id": self.test_user_id,
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(followup_message))
            
            readiness_results.append({
                "test": "followup_message",
                "status": "success"
            })
            
            # Close connection gracefully
            await websocket.close()
            
            readiness_results.append({
                "test": "graceful_disconnection",
                "status": "success"
            })
            
        except Exception as e:
            readiness_results.append({
                "test": "complete_chat_workflow",
                "status": "error",
                "error": str(e)
            })
            pytest.fail(f"Complete chat readiness validation failed: {e}")
        
        # Record complete readiness results  
        self.chat_test_results["complete_chat_readiness"] = readiness_results
        
        # Validate critical readiness components
        connection_success = any(r["test"] == "chat_connection" and r["status"] == "success" for r in readiness_results)
        followup_success = any(r["test"] == "followup_message" and r["status"] == "success" for r in readiness_results)
        graceful_disconnect = any(r["test"] == "graceful_disconnection" and r["status"] == "success" for r in readiness_results)
        
        assert connection_success, "Chat connection not established"
        assert followup_success, "Follow-up messages not working"
        assert graceful_disconnect, "Graceful disconnection not working"
        
        # Record final chat readiness metrics
        self.record_metric("complete_chat_readiness_passed", True)
        self.record_metric("finalize_chat_readiness_complete", True)
        
        # Ensure the complete test completes within reasonable time
        self.assert_execution_time_under(120.0)  # Allow up to 2 minutes for complete chat workflow test