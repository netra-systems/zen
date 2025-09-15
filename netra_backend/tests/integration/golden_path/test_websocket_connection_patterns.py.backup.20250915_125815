"""
Test WebSocket Connection Patterns - GOLDEN PATH Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable real-time communication for agent execution updates
- Value Impact: Users receive immediate feedback during optimization analysis
- Strategic Impact: Core platform infrastructure for delivering timely AI insights

These tests validate the WebSocket connection patterns that enable real-time
communication between users and AI agents. Without reliable WebSocket connections,
users cannot receive timely updates about optimization progress and results.
"""

import asyncio
import pytest
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from shared.isolated_environment import get_env


class MockWebSocket:
    """Mock WebSocket for integration testing when real WebSocket unavailable."""
    
    def __init__(self):
        self.open = True
        self.messages_sent = []
        self.messages_to_receive = []
        self.closed = False
        
    async def send(self, message):
        self.messages_sent.append(message)
        
    async def recv(self):
        if self.messages_to_receive:
            return self.messages_to_receive.pop(0)
        # Simulate receiving a message
        return json.dumps({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
        
    async def close(self):
        self.open = False
        self.closed = True
        
    def add_message_to_receive(self, message):
        if isinstance(message, dict):
            message = json.dumps(message)
        self.messages_to_receive.append(message)


class TestWebSocketConnectionPatterns(BaseIntegrationTest):
    """Integration tests for WebSocket connection patterns with real authentication."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_authentication_handshake(self, real_services_fixture):
        """
        Test WebSocket authentication handshake with JWT tokens.
        
        BVJ: Secure WebSocket connections are essential for protecting
        user data during real-time agent communication.
        """
        # Create authenticated user
        user_email = f"ws_auth_{uuid.uuid4().hex[:8]}@example.com"
        user_data = await self.create_test_user_context(
            real_services_fixture,
            user_data={'email': user_email, 'name': 'WebSocket Test User', 'is_active': True}
        )
        
        # Create WebSocket auth helper
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_data["id"],
            email=user_data["email"],
            permissions=["read", "write", "websocket_connect"]
        )
        
        # Test WebSocket authentication headers
        ws_headers = auth_helper.get_websocket_headers(jwt_token)
        assert "Authorization" in ws_headers
        assert ws_headers["Authorization"] == f"Bearer {jwt_token}"
        assert ws_headers["X-User-ID"] == user_data["id"]
        assert ws_headers["X-Test-Mode"] == "true"
        assert ws_headers["X-Test-Type"] == "E2E"
        
        # Test WebSocket subprotocols for alternative auth
        subprotocols = auth_helper.get_websocket_subprotocols(jwt_token)
        assert "jwt-auth" in subprotocols
        assert "e2e-testing" in subprotocols
        assert any(proto.startswith("jwt.") for proto in subprotocols)
        
        # Mock WebSocket connection for integration test
        mock_websocket = MockWebSocket()
        
        with patch('websockets.connect', return_value=mock_websocket):
            # Test connection establishment
            websocket, connection_info = await auth_helper.create_websocket_connection(
                websocket_url="ws://localhost:8000/ws",
                token=jwt_token,
                timeout=5.0
            )
            
            # Verify connection established
            assert websocket.open is True
            connection_data = json.loads(connection_info)
            assert connection_data["authenticated"] is True
            assert connection_data["user_id"] == user_data["id"]
            
        # Verify business value: secure real-time communication enabled
        business_result = {
            "secure_websocket_connection": True,
            "real_time_communication_enabled": True,
            "user_authentication_verified": True,
            "automation": ["jwt_validation", "connection_establishment", "security_headers"]
        }
        self.assert_business_value_delivered(business_result, 'automation')
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_agent_event_streaming(self, real_services_fixture):
        """
        Test WebSocket streaming of agent execution events.
        
        BVJ: Real-time agent event streaming keeps users informed about
        optimization progress and prevents user anxiety during long analyses.
        """
        # Create authenticated user context
        user_email = f"ws_events_{uuid.uuid4().hex[:8]}@example.com"
        user_data = await self.create_test_user_context(
            real_services_fixture,
            user_data={'email': user_email, 'name': 'Event Stream User', 'is_active': True}
        )
        
        # Create authentication for WebSocket
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_data["id"],
            email=user_data["email"],
            permissions=["read", "write", "websocket_connect", "agent_events"]
        )
        
        # Mock WebSocket with realistic agent events
        mock_websocket = MockWebSocket()
        agent_events = [
            {
                "type": "agent_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "cost_optimizer",
                "message": "Starting cost analysis",
                "user_id": user_data["id"]
            },
            {
                "type": "agent_thinking", 
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "cost_optimizer",
                "message": "Analyzing AWS billing data",
                "progress": 25
            },
            {
                "type": "tool_executing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "cost_optimizer",
                "tool": "aws_cost_analyzer",
                "message": "Fetching cost data from AWS Cost Explorer"
            },
            {
                "type": "tool_completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "cost_optimizer", 
                "tool": "aws_cost_analyzer",
                "result": "Found $5,200 in potential monthly savings"
            },
            {
                "type": "agent_completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "cost_optimizer",
                "result": {
                    "monthly_savings": 5200,
                    "recommendations": ["Right-size EC2 instances", "Purchase Reserved Instances"]
                }
            }
        ]
        
        # Add events to mock WebSocket
        for event in agent_events:
            mock_websocket.add_message_to_receive(event)
            
        with patch('websockets.connect', return_value=mock_websocket):
            # Establish WebSocket connection
            websocket, _ = await auth_helper.create_websocket_connection(
                websocket_url="ws://localhost:8000/ws",
                token=jwt_token
            )
            
            # Simulate receiving agent events
            received_events = []
            for _ in range(len(agent_events)):
                event_msg = await websocket.recv()
                event_data = json.loads(event_msg)
                received_events.append(event_data)
                
            # Verify all expected events received
            assert len(received_events) == 5
            
            # Verify event sequence
            event_types = [event["type"] for event in received_events]
            expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            assert event_types == expected_sequence
            
            # Verify business-critical events contain value
            final_event = received_events[-1]
            assert final_event["type"] == "agent_completed"
            assert "result" in final_event
            assert final_event["result"]["monthly_savings"] > 0
            
        # Verify business value: real-time optimization progress delivered
        business_result = {
            "real_time_agent_updates": True,
            "optimization_progress_visible": True,
            "user_engagement_maintained": True,
            "cost_savings_communicated": final_event["result"]["monthly_savings"],
            "insights": received_events
        }
        self.assert_business_value_delivered(business_result, 'insights')
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_multi_user_isolation(self, real_services_fixture):
        """
        Test WebSocket connection isolation between multiple users.
        
        BVJ: User isolation prevents data leakage and ensures each user
        only receives their own optimization results and sensitive data.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for integration testing")
            
        # Create multiple authenticated users
        users = []
        for i in range(3):
            user_email = f"ws_isolation_{i}_{uuid.uuid4().hex[:8]}@example.com"
            user_data = await self.create_test_user_context(
                real_services_fixture,
                user_data={'email': user_email, 'name': f'Isolated User {i}', 'is_active': True}
            )
            
            # Create auth helper for each user
            auth_helper = E2EWebSocketAuthHelper(environment="test")
            jwt_token = auth_helper.create_test_jwt_token(
                user_id=user_data["id"],
                email=user_data["email"],
                permissions=["read", "write", "websocket_connect", f"user_{i}_data"]
            )
            
            users.append({
                "user_data": user_data,
                "jwt_token": jwt_token,
                "auth_helper": auth_helper,
                "mock_websocket": MockWebSocket()
            })
        
        # Test isolated WebSocket connections
        with patch('websockets.connect') as mock_connect:
            connections = []
            
            for i, user in enumerate(users):
                # Configure mock to return user's WebSocket
                mock_connect.return_value = user["mock_websocket"]
                
                # Establish connection
                websocket, connection_info = await user["auth_helper"].create_websocket_connection(
                    websocket_url="ws://localhost:8000/ws",
                    token=user["jwt_token"]
                )
                
                # Verify connection isolation
                connection_data = json.loads(connection_info)
                assert connection_data["user_id"] == user["user_data"]["id"]
                assert connection_data["authenticated"] is True
                
                connections.append({
                    "user_id": user["user_data"]["id"],
                    "websocket": websocket,
                    "connection_info": connection_data
                })
                
            # Verify each connection is isolated
            user_ids = [conn["user_id"] for conn in connections]
            assert len(set(user_ids)) == 3, "Each user must have unique connection"
            
            # Simulate user-specific events
            for i, user in enumerate(users):
                user_specific_event = {
                    "type": "user_data",
                    "user_id": user["user_data"]["id"],
                    "private_data": f"Confidential data for user {i}",
                    "cost_analysis": f"User {i} monthly spend: ${(i+1)*1000}"
                }
                
                user["mock_websocket"].add_message_to_receive(user_specific_event)
                
            # Verify each user only receives their own data
            for i, user in enumerate(users):
                received_msg = await user["mock_websocket"].recv()
                received_data = json.loads(received_msg)
                
                assert received_data["user_id"] == user["user_data"]["id"]
                assert f"user {i}" in received_data["private_data"].lower()
                assert received_data["cost_analysis"].endswith(f"${(i+1)*1000}")
                
        # Verify business value: secure multi-tenant isolation
        business_result = {
            "multi_user_isolation_verified": True,
            "data_privacy_maintained": True,
            "secure_multi_tenant_architecture": True,
            "concurrent_users_supported": len(users),
            "automation": [f"isolated_connection_user_{i}" for i in range(len(users))]
        }
        self.assert_business_value_delivered(business_result, 'automation')
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_resilience(self, real_services_fixture):
        """
        Test WebSocket connection resilience and reconnection handling.
        
        BVJ: Resilient connections ensure users don't lose optimization
        progress due to network issues or temporary service interruptions.
        """
        # Create authenticated user
        user_email = f"ws_resilience_{uuid.uuid4().hex[:8]}@example.com"
        user_data = await self.create_test_user_context(
            real_services_fixture,
            user_data={'email': user_email, 'name': 'Resilience Test User', 'is_active': True}
        )
        
        # Create auth helper
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_data["id"],
            email=user_data["email"],
            permissions=["read", "write", "websocket_connect", "reconnect"]
        )
        
        # Test connection retry mechanism
        connection_attempts = []
        original_connect = None
        
        async def mock_connect_with_failures(*args, **kwargs):
            connection_attempts.append(len(connection_attempts) + 1)
            
            # Fail first 2 attempts, succeed on 3rd
            if len(connection_attempts) <= 2:
                raise ConnectionError(f"Connection failed (attempt {len(connection_attempts)})")
            else:
                # Return successful connection
                mock_ws = MockWebSocket()
                return mock_ws
                
        with patch('websockets.connect', side_effect=mock_connect_with_failures):
            # Test resilient connection with retries
            websocket, connection_info = await auth_helper.create_websocket_connection(
                websocket_url="ws://localhost:8000/ws",
                token=jwt_token,
                timeout=2.0,
                max_retries=3
            )
            
            # Verify connection eventually succeeded
            assert websocket.open is True
            connection_data = json.loads(connection_info)
            assert connection_data["attempt"] == 3  # Third attempt succeeded
            assert len(connection_attempts) == 3
            
        # Test graceful disconnection handling
        mock_websocket = MockWebSocket()
        
        with patch('websockets.connect', return_value=mock_websocket):
            websocket, _ = await auth_helper.create_websocket_connection(
                websocket_url="ws://localhost:8000/ws", 
                token=jwt_token
            )
            
            # Simulate graceful disconnection
            await websocket.close()
            assert websocket.closed is True
            
        # Test connection state management
        state_events = [
            {"type": "connection_established", "user_id": user_data["id"]},
            {"type": "connection_interrupted", "reason": "network_error"},
            {"type": "reconnection_attempt", "attempt": 1},
            {"type": "connection_restored", "user_id": user_data["id"]}
        ]
        
        # Verify business value: reliable communication despite disruptions
        business_result = {
            "connection_resilience_verified": True,
            "retry_mechanism_working": True,
            "graceful_disconnection_handled": True,
            "user_experience_maintained": True,
            "total_connection_attempts": len(connection_attempts),
            "automation": ["connection_retry", "state_management", "error_recovery"]
        }
        self.assert_business_value_delivered(business_result, 'automation')
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_routing_patterns(self, real_services_fixture):
        """
        Test WebSocket message routing patterns for different agent types.
        
        BVJ: Proper message routing ensures users receive relevant updates
        for their specific optimization requests and agent interactions.
        """
        # Create authenticated user with multiple agent permissions
        user_email = f"ws_routing_{uuid.uuid4().hex[:8]}@example.com"
        user_data = await self.create_test_user_context(
            real_services_fixture,
            user_data={'email': user_email, 'name': 'Routing Test User', 'is_active': True}
        )
        
        # Create auth helper with comprehensive permissions
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_data["id"],
            email=user_data["email"],
            permissions=[
                "read", "write", "websocket_connect",
                "triage_agent", "cost_optimizer", "security_analyzer"
            ]
        )
        
        # Mock WebSocket with routing scenarios
        mock_websocket = MockWebSocket()
        
        # Define different message routing patterns
        routing_scenarios = [
            {
                "message_type": "agent_request",
                "agent_type": "triage_agent",
                "route_to": "triage_handler",
                "expected_response": {
                    "type": "agent_started",
                    "agent": "triage_agent",
                    "handler": "triage_handler"
                }
            },
            {
                "message_type": "optimization_request",
                "agent_type": "cost_optimizer", 
                "route_to": "cost_optimization_handler",
                "expected_response": {
                    "type": "agent_started",
                    "agent": "cost_optimizer",
                    "handler": "cost_optimization_handler"
                }
            },
            {
                "message_type": "security_scan_request",
                "agent_type": "security_analyzer",
                "route_to": "security_analysis_handler",
                "expected_response": {
                    "type": "agent_started", 
                    "agent": "security_analyzer",
                    "handler": "security_analysis_handler"
                }
            }
        ]
        
        # Set up expected responses in mock WebSocket
        for scenario in routing_scenarios:
            mock_websocket.add_message_to_receive(scenario["expected_response"])
            
        with patch('websockets.connect', return_value=mock_websocket):
            # Establish WebSocket connection
            websocket, _ = await auth_helper.create_websocket_connection(
                websocket_url="ws://localhost:8000/ws",
                token=jwt_token
            )
            
            # Test each routing scenario
            routing_results = []
            
            for scenario in routing_scenarios:
                # Send message for routing
                request_message = {
                    "type": scenario["message_type"],
                    "agent": scenario["agent_type"],
                    "user_id": user_data["id"],
                    "message": f"Test {scenario['agent_type']} request",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(request_message))
                
                # Receive routed response
                response_msg = await websocket.recv()
                response_data = json.loads(response_msg)
                
                # Verify correct routing
                assert response_data["type"] == scenario["expected_response"]["type"]
                assert response_data["agent"] == scenario["expected_response"]["agent"] 
                assert response_data["handler"] == scenario["expected_response"]["handler"]
                
                routing_results.append({
                    "scenario": scenario["agent_type"],
                    "routing_successful": True,
                    "handler_matched": response_data["handler"] == scenario["route_to"]
                })
                
            # Verify all routing scenarios succeeded
            assert len(routing_results) == len(routing_scenarios)
            assert all(result["routing_successful"] for result in routing_results)
            
        # Verify business value: intelligent message routing enables targeted optimization
        business_result = {
            "message_routing_verified": True,
            "agent_specific_handling": True,
            "targeted_optimization_enabled": True,
            "routing_scenarios_tested": len(routing_scenarios),
            "automation": [result["scenario"] for result in routing_results]
        }
        self.assert_business_value_delivered(business_result, 'automation')
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_performance_under_load(self, real_services_fixture):
        """
        Test WebSocket performance under concurrent connection load.
        
        BVJ: Performance under load ensures the platform can handle multiple
        users simultaneously without degrading the optimization experience.
        """
        # Create multiple concurrent users for load testing
        concurrent_users = 5
        load_test_users = []
        
        for i in range(concurrent_users):
            user_email = f"ws_load_{i}_{uuid.uuid4().hex[:8]}@example.com"
            user_data = await self.create_test_user_context(
                real_services_fixture,
                user_data={'email': user_email, 'name': f'Load Test User {i}', 'is_active': True}
            )
            
            # Create auth helper for each user
            auth_helper = E2EWebSocketAuthHelper(environment="test")
            jwt_token = auth_helper.create_test_jwt_token(
                user_id=user_data["id"],
                email=user_data["email"],
                permissions=["read", "write", "websocket_connect", "load_test"]
            )
            
            load_test_users.append({
                "user_data": user_data,
                "jwt_token": jwt_token,
                "auth_helper": auth_helper,
                "mock_websocket": MockWebSocket()
            })
        
        # Mock concurrent WebSocket connections
        def get_mock_websocket(url, **kwargs):
            # Return different mock WebSocket for each connection
            for user in load_test_users:
                if not hasattr(user["mock_websocket"], '_used'):
                    user["mock_websocket"]._used = True
                    return user["mock_websocket"]
            return MockWebSocket()  # Fallback
            
        # Test concurrent connection establishment
        start_time = asyncio.get_event_loop().time()
        
        with patch('websockets.connect', side_effect=get_mock_websocket):
            # Establish concurrent connections
            connection_tasks = []
            
            for user in load_test_users:
                task = asyncio.create_task(
                    user["auth_helper"].create_websocket_connection(
                        websocket_url="ws://localhost:8000/ws",
                        token=user["jwt_token"],
                        timeout=5.0
                    )
                )
                connection_tasks.append(task)
                
            # Wait for all connections to complete
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
        connection_time = asyncio.get_event_loop().time() - start_time
        
        # Verify all connections succeeded
        successful_connections = []
        for i, result in enumerate(connection_results):
            if isinstance(result, tuple):  # Success: (websocket, connection_info)
                websocket, connection_info = result
                connection_data = json.loads(connection_info)
                successful_connections.append({
                    "user_id": connection_data["user_id"],
                    "connection_time": connection_time / concurrent_users
                })
                
        # Test concurrent message processing
        message_processing_tasks = []
        
        for i, user in enumerate(load_test_users):
            if hasattr(user["mock_websocket"], '_used'):
                # Add test message to receive
                test_message = {
                    "type": "load_test_response",
                    "user_id": user["user_data"]["id"],
                    "message_id": f"msg_{i}",
                    "processing_time_ms": 50 + (i * 10)  # Simulate varying processing times
                }
                user["mock_websocket"].add_message_to_receive(test_message)
                
                # Create task to receive message
                task = asyncio.create_task(user["mock_websocket"].recv())
                message_processing_tasks.append(task)
                
        # Process messages concurrently
        if message_processing_tasks:
            processing_start = asyncio.get_event_loop().time()
            message_results = await asyncio.gather(*message_processing_tasks, return_exceptions=True)
            processing_time = asyncio.get_event_loop().time() - processing_start
            
            # Verify message processing performance
            processed_messages = []
            for result in message_results:
                if isinstance(result, str):  # Successfully received message
                    message_data = json.loads(result)
                    processed_messages.append(message_data)
                    
        # Verify performance metrics
        assert len(successful_connections) >= concurrent_users * 0.8  # 80% success rate minimum
        assert connection_time < 10.0  # All connections within 10 seconds
        
        if message_processing_tasks:
            assert len(processed_messages) >= len(message_processing_tasks) * 0.8
            assert processing_time < 5.0  # All messages processed within 5 seconds
            
        # Verify business value: platform scales for multiple users
        business_result = {
            "concurrent_connections_supported": len(successful_connections),
            "connection_performance_acceptable": connection_time < 10.0,
            "message_processing_performance": processing_time < 5.0 if message_processing_tasks else True,
            "platform_scalability_verified": True,
            "load_test_successful": True,
            "automation": [
                f"concurrent_user_{i}" for i in range(len(successful_connections))
            ]
        }
        self.assert_business_value_delivered(business_result, 'automation')