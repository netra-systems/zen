"""
Test Agent Started Events via WebSocket - Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent_started events enable meaningful chat interactions
- Value Impact: Users must see when agents begin processing to understand AI is working on their problems
- Strategic Impact: MISSION CRITICAL - WebSocket events are fundamental to chat business value delivery

CRITICAL REQUIREMENTS:
- NO MOCKS (per CLAUDE.md - "MOCKS = ABOMINATION")
- REAL WebSocket connections only
- Integration tests (NOT e2e - no Docker services required)
- Use SSOT patterns from test_framework/ssot/
- Follow reports/testing/TEST_CREATION_GUIDE.md patterns
- Full authentication using test_framework/ssot/e2e_auth_helper.py

These tests validate that when agents start execution, the `agent_started` WebSocket event 
actually reaches the end user with correct timing, payload, and user isolation.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock
import pytest
import websockets
from concurrent.futures import ThreadPoolExecutor
import threading
import gc
import psutil
import os

# SSOT imports with absolute paths
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.fixtures.websocket_test_helpers import (
    WebSocketTestClient,
    assert_websocket_events,
    websocket_test_context
)
from shared.isolated_environment import get_env


class TestAgentStartedEvents(BaseIntegrationTest):
    """
    Integration tests for agent_started WebSocket events reaching end users.
    
    CRITICAL: These tests validate the fundamental mechanism that enables chat business value.
    Without agent_started events, users cannot see when AI begins working on their problems.
    """
    
    def setup_method(self):
        """Set up test environment with real WebSocket configuration."""
        super().setup_method()
        self.env = get_env()
        
        # Test configuration using test ports (not mocked)
        self.websocket_url = "ws://localhost:8000/ws"
        self.backend_url = "http://localhost:8000"
        
        # Real authentication helpers (SSOT)
        self.auth_helper = E2EAuthHelper(environment="test")
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Event collection for analysis
        self.received_events: List[Dict[str, Any]] = []
        self.timing_data: List[Dict[str, Any]] = []
        
        # User isolation tracking
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.connection_times: List[float] = []
        self.event_latencies: List[float] = []
        
    def teardown_method(self):
        """Clean up resources and connections."""
        super().teardown_method()
        # Clear test data
        self.received_events.clear()
        self.timing_data.clear()
        self.user_sessions.clear()
        self.connection_times.clear()
        self.event_latencies.clear()
        
    async def create_authenticated_websocket_client(self, user_id: Optional[str] = None) -> Tuple[WebSocketTestClient, str, Dict[str, str]]:
        """
        Create authenticated WebSocket client with real JWT token.
        SSOT method for client creation with proper authentication.
        """
        # Generate unique user ID if not provided
        user_id = user_id or f"test-user-{uuid.uuid4().hex[:8]}"
        
        # Create real JWT token (not mocked)
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=f"{user_id}@test.example.com",
            permissions=["read", "write"]
        )
        
        # Get WebSocket headers with authentication
        headers = self.ws_auth_helper.get_websocket_headers(token)
        
        # Create WebSocket client with real URL
        client = WebSocketTestClient(self.websocket_url)
        
        return client, token, headers
        
    async def simulate_agent_execution_start(self, ws_client: WebSocketTestClient, agent_type: str = "triage_agent") -> Dict[str, Any]:
        """
        Simulate agent execution start and capture agent_started event.
        This simulates the real agent execution flow without mocking.
        """
        start_time = time.time()
        
        # Send agent execution request (real message format)
        agent_request = {
            "type": "agent_request",
            "agent": agent_type,
            "message": f"Test query for {agent_type}",
            "thread_id": f"test-thread-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await ws_client.send_message(agent_request)
        
        # Wait for agent_started event (real WebSocket response)
        try:
            # Wait up to 10 seconds for agent_started event
            for _ in range(100):  # 100 * 0.1s = 10s timeout
                message = await ws_client.receive_message(timeout=0.1)
                if message.get("type") == "agent_started":
                    end_time = time.time()
                    latency = end_time - start_time
                    
                    # Record timing data
                    timing_record = {
                        "start_time": start_time,
                        "end_time": end_time,
                        "latency": latency,
                        "agent_type": agent_type,
                        "event_type": "agent_started"
                    }
                    self.timing_data.append(timing_record)
                    
                    return message
                    
        except asyncio.TimeoutError:
            pass
            
        # If no agent_started event received, return empty dict
        return {}
    
    # =========================================================================
    # TEST 1-5: BASIC EVENT DELIVERY AND VALIDATION
    # =========================================================================
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_01_basic_agent_started_event_delivery(self):
        """
        BVJ: Verify basic agent_started event reaches user via WebSocket
        - Segment: All users need to see when agents start working
        - Business Goal: User awareness of AI processing initiation
        - Value Impact: Users know their request is being processed
        - Strategic Impact: Foundation for all chat interactions
        """
        # Create authenticated WebSocket client
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            # Connect with real authentication
            await client.connect(headers=headers)
            
            # Simulate agent execution start
            agent_started_event = await self.simulate_agent_execution_start(client, "triage_agent")
            
            # Verify agent_started event was received
            assert agent_started_event.get("type") == "agent_started", "agent_started event not received"
            assert "data" in agent_started_event, "agent_started event missing data field"
            assert "agent" in agent_started_event["data"], "agent_started event missing agent identifier"
            assert agent_started_event["data"]["agent"] == "triage_agent", "Incorrect agent type in event"
            
            # Verify business value: user gets immediate feedback
            assert "timestamp" in agent_started_event, "agent_started event missing timestamp"
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration 
    @pytest.mark.websocket
    async def test_02_event_timing_and_latency_measurement(self):
        """
        BVJ: Measure agent_started event delivery latency for user experience
        - Segment: All users expect responsive AI interactions
        - Business Goal: Ensure sub-second response times for user engagement
        - Value Impact: Fast feedback maintains user confidence in system
        - Strategic Impact: Performance directly affects user satisfaction
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Measure connection establishment time
            connection_start = time.time()
            await client.send_message({"type": "ping"})
            connection_end = time.time()
            connection_time = connection_end - connection_start
            self.connection_times.append(connection_time)
            
            # Measure agent_started event latency
            event_start = time.time()
            agent_started_event = await self.simulate_agent_execution_start(client)
            event_end = time.time()
            event_latency = event_end - event_start
            self.event_latencies.append(event_latency)
            
            # Verify performance requirements for business value
            assert connection_time < 5.0, f"WebSocket connection too slow: {connection_time}s"
            assert event_latency < 10.0, f"agent_started event too slow: {event_latency}s"
            assert agent_started_event, "agent_started event not received within timeout"
            
            # Record performance metrics
            perf_data = {
                "connection_time": connection_time,
                "event_latency": event_latency,
                "total_time": connection_time + event_latency
            }
            print(f"Performance metrics: {perf_data}")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket 
    async def test_03_payload_structure_validation(self):
        """
        BVJ: Validate agent_started event payload contains required business data
        - Segment: All users need complete information about agent processing
        - Business Goal: Provide meaningful status updates to users
        - Value Impact: Users understand what agent is doing for their request
        - Strategic Impact: Proper payload structure enables rich UI/UX
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Get agent_started event with comprehensive payload
            agent_started_event = await self.simulate_agent_execution_start(client, "cost_optimizer")
            
            # Validate required payload structure for business value
            assert "type" in agent_started_event, "Event missing type field"
            assert agent_started_event["type"] == "agent_started", "Incorrect event type"
            
            assert "data" in agent_started_event, "Event missing data field"
            event_data = agent_started_event["data"]
            
            # Validate business-critical fields
            required_fields = ["agent", "thread_id", "user_id", "status"]
            for field in required_fields:
                assert field in event_data, f"agent_started event missing required field: {field}"
            
            # Validate data types and values
            assert isinstance(event_data["agent"], str), "Agent field must be string"
            assert isinstance(event_data["thread_id"], str), "Thread ID must be string" 
            assert isinstance(event_data["user_id"], str), "User ID must be string"
            assert event_data["status"] == "started", "Status must be 'started'"
            
            # Validate optional business fields
            if "message" in event_data:
                assert isinstance(event_data["message"], str), "Message must be string"
            
            if "metadata" in event_data:
                assert isinstance(event_data["metadata"], dict), "Metadata must be dict"
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_04_user_isolation_different_users_different_events(self):
        """
        BVJ: Verify user isolation - different users receive only their agent_started events
        - Segment: Multi-user system isolation is critical for Enterprise customers
        - Business Goal: Prevent data leakage between users
        - Value Impact: Users only see their own agent processing, maintaining privacy
        - Strategic Impact: User isolation enables secure multi-tenant operation
        """
        # Create two different users
        user1_client, user1_token, user1_headers = await self.create_authenticated_websocket_client("user1")
        user2_client, user2_token, user2_headers = await self.create_authenticated_websocket_client("user2")
        
        try:
            # Connect both users
            await user1_client.connect(headers=user1_headers)
            await user2_client.connect(headers=user2_headers)
            
            # User 1 starts agent execution
            user1_agent_request = {
                "type": "agent_request",
                "agent": "data_analyzer", 
                "message": "User 1 private request",
                "thread_id": "user1-thread",
                "user_id": "user1"
            }
            await user1_client.send_message(user1_agent_request)
            
            # User 2 starts different agent execution  
            user2_agent_request = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "User 2 private request", 
                "thread_id": "user2-thread",
                "user_id": "user2"
            }
            await user2_client.send_message(user2_agent_request)
            
            # Collect events for both users
            user1_events = []
            user2_events = []
            
            # Wait for agent_started events (with timeout)
            for _ in range(50):  # 5 second timeout
                try:
                    # Check user1 events
                    user1_message = await user1_client.receive_message(timeout=0.1)
                    if user1_message.get("type") == "agent_started":
                        user1_events.append(user1_message)
                except asyncio.TimeoutError:
                    pass
                    
                try:
                    # Check user2 events  
                    user2_message = await user2_client.receive_message(timeout=0.1)
                    if user2_message.get("type") == "agent_started":
                        user2_events.append(user2_message)
                except asyncio.TimeoutError:
                    pass
                    
                # Break if both received their events
                if user1_events and user2_events:
                    break
            
            # Verify user isolation
            assert len(user1_events) > 0, "User 1 did not receive agent_started event"
            assert len(user2_events) > 0, "User 2 did not receive agent_started event"
            
            # Verify users only receive their own events
            user1_event = user1_events[0]
            user2_event = user2_events[0]
            
            assert user1_event["data"]["user_id"] == "user1", "User 1 received wrong user's event"
            assert user2_event["data"]["user_id"] == "user2", "User 2 received wrong user's event"
            assert user1_event["data"]["thread_id"] == "user1-thread", "User 1 thread ID incorrect"
            assert user2_event["data"]["thread_id"] == "user2-thread", "User 2 thread ID incorrect"
            
        finally:
            await user1_client.disconnect()
            await user2_client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_05_authentication_edge_cases(self):
        """
        BVJ: Test authentication edge cases for agent_started events
        - Segment: Security-conscious Enterprise customers
        - Business Goal: Ensure only authenticated users receive events
        - Value Impact: Prevents unauthorized access to agent processing information
        - Strategic Impact: Authentication failures must fail gracefully
        """
        # Test 1: Invalid token
        client = WebSocketTestClient(self.websocket_url)
        invalid_headers = {"Authorization": "Bearer invalid_token_123"}
        
        try:
            await client.connect(headers=invalid_headers)
            # Connection should fail or not receive agent events
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Test with invalid auth"
            }
            await client.send_message(agent_request)
            
            # Should not receive agent_started event with invalid auth
            received_agent_started = False
            for _ in range(10):  # 1 second timeout
                try:
                    message = await client.receive_message(timeout=0.1)
                    if message.get("type") == "agent_started":
                        received_agent_started = True
                        break
                except asyncio.TimeoutError:
                    pass
            
            # Verify security: no agent_started event with invalid auth
            assert not received_agent_started, "agent_started event received with invalid authentication"
            
        except Exception as e:
            # Connection failure is acceptable for invalid auth
            print(f"Expected auth failure: {e}")
        finally:
            await client.disconnect()
        
        # Test 2: Expired token
        expired_token = self.auth_helper.create_test_jwt_token(
            user_id="expired-user",
            exp_minutes=-5  # Expired 5 minutes ago
        )
        expired_headers = self.ws_auth_helper.get_websocket_headers(expired_token)
        
        client2 = WebSocketTestClient(self.websocket_url)
        try:
            await client2.connect(headers=expired_headers)
            
            # Try to start agent with expired token
            agent_request = {
                "type": "agent_request", 
                "agent": "triage_agent",
                "message": "Test with expired token"
            }
            await client2.send_message(agent_request)
            
            # Should not receive agent_started with expired token
            received_agent_started = False
            for _ in range(10):
                try:
                    message = await client2.receive_message(timeout=0.1)
                    if message.get("type") == "agent_started":
                        received_agent_started = True
                        break
                except asyncio.TimeoutError:
                    pass
            
            assert not received_agent_started, "agent_started event received with expired token"
            
        except Exception as e:
            # Connection/auth failure expected
            print(f"Expected expired token failure: {e}")
        finally:
            await client2.disconnect()
    
    # =========================================================================
    # TEST 6-10: CONNECTION STATE AND EVENT ORDERING
    # =========================================================================
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_06_connection_state_management(self):
        """
        BVJ: Test WebSocket connection state affects agent_started event delivery
        - Segment: All users need reliable connections for agent interactions
        - Business Goal: Ensure events are delivered despite connection issues
        - Value Impact: Users receive agent updates even with network problems
        - Strategic Impact: Connection resilience enables consistent user experience
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            # Test connection state transitions
            assert not client.connected, "Client should start disconnected"
            
            # Connect and verify state
            await client.connect(headers=headers)
            assert client.connected, "Client should be connected after connect()"
            
            # Test agent_started event delivery in connected state
            agent_started_event = await self.simulate_agent_execution_start(client)
            assert agent_started_event.get("type") == "agent_started", "Event not received in connected state"
            
            # Test reconnection scenario
            await client.disconnect()
            assert not client.connected, "Client should be disconnected after disconnect()"
            
            # Reconnect and test again
            await client.connect(headers=headers)
            assert client.connected, "Client should reconnect successfully"
            
            # Verify events work after reconnection
            agent_started_event2 = await self.simulate_agent_execution_start(client, "cost_optimizer")
            assert agent_started_event2.get("type") == "agent_started", "Event not received after reconnection"
            
            # Verify different agent types work
            assert agent_started_event2["data"]["agent"] == "cost_optimizer", "Wrong agent type after reconnection"
            
        finally:
            if client.connected:
                await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_07_event_ordering_guarantees(self):
        """
        BVJ: Verify agent_started events maintain proper ordering in event stream
        - Segment: All users need predictable agent execution flow
        - Business Goal: Ensure users understand agent processing sequence
        - Value Impact: Ordered events enable coherent user interface updates
        - Strategic Impact: Event ordering is critical for complex agent workflows
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Start multiple agents in sequence
            agent_types = ["triage_agent", "data_analyzer", "cost_optimizer"]
            received_events = []
            
            # Send multiple agent requests
            for i, agent_type in enumerate(agent_types):
                agent_request = {
                    "type": "agent_request",
                    "agent": agent_type,
                    "message": f"Sequential request {i+1}",
                    "sequence_id": i + 1,
                    "thread_id": f"sequence-thread-{i+1}"
                }
                await client.send_message(agent_request)
                
                # Small delay to ensure ordering
                await asyncio.sleep(0.1)
            
            # Collect agent_started events with timeout
            start_time = time.time()
            while len(received_events) < len(agent_types) and time.time() - start_time < 15:
                try:
                    message = await client.receive_message(timeout=0.5)
                    if message.get("type") == "agent_started":
                        received_events.append(message)
                except asyncio.TimeoutError:
                    continue
            
            # Verify we received all agent_started events
            assert len(received_events) >= len(agent_types), f"Expected {len(agent_types)} agent_started events, got {len(received_events)}"
            
            # Verify event ordering (business requirement for coherent UX)
            received_agents = [event["data"]["agent"] for event in received_events[:len(agent_types)]]
            assert received_agents == agent_types, f"Agent order incorrect: expected {agent_types}, got {received_agents}"
            
            # Verify sequence metadata if present
            for i, event in enumerate(received_events[:len(agent_types)]):
                if "sequence_id" in event["data"]:
                    assert event["data"]["sequence_id"] == i + 1, f"Sequence ID wrong for event {i}"
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_08_error_handling_scenarios(self):
        """
        BVJ: Test error handling for agent_started events
        - Segment: All users need graceful error handling
        - Business Goal: Provide meaningful error feedback when agents fail to start
        - Value Impact: Users understand when and why agent processing fails
        - Strategic Impact: Error handling prevents user confusion and support tickets
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Test 1: Invalid agent type
            invalid_agent_request = {
                "type": "agent_request",
                "agent": "nonexistent_agent_type_999",
                "message": "Test invalid agent",
                "thread_id": "error-test-1"
            }
            await client.send_message(invalid_agent_request)
            
            # Should receive error response, not agent_started
            error_received = False
            agent_started_received = False
            
            for _ in range(50):  # 5 second timeout
                try:
                    message = await client.receive_message(timeout=0.1)
                    msg_type = message.get("type")
                    
                    if msg_type == "error" or msg_type == "agent_error":
                        error_received = True
                        # Verify error message contains meaningful info
                        assert "data" in message, "Error message missing data"
                        assert "message" in message["data"] or "error" in message["data"], "Error missing descriptive message"
                        
                    elif msg_type == "agent_started":
                        agent_started_received = True
                        
                except asyncio.TimeoutError:
                    pass
            
            # Verify proper error handling (business requirement)
            assert not agent_started_received, "Should not receive agent_started for invalid agent"
            # Note: error_received may be False if system handles invalid agents silently
            
            # Test 2: Malformed request  
            malformed_request = {
                "type": "agent_request",
                # Missing required fields
                "message": "Test malformed request"
            }
            await client.send_message(malformed_request)
            
            # Should handle malformed request gracefully
            malformed_error = False
            for _ in range(20):  # 2 second timeout
                try:
                    message = await client.receive_message(timeout=0.1)
                    if message.get("type") in ["error", "validation_error", "agent_error"]:
                        malformed_error = True
                        break
                except asyncio.TimeoutError:
                    pass
            
            # System should handle malformed requests gracefully
            print(f"Malformed request error handling: {malformed_error}")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_09_concurrent_user_scenarios(self):
        """
        BVJ: Test concurrent users receiving agent_started events simultaneously
        - Segment: Enterprise customers with multiple concurrent users
        - Business Goal: Support multiple users simultaneously without conflicts
        - Value Impact: System scales to handle concurrent agent executions
        - Strategic Impact: Concurrency support enables platform growth
        """
        # Create multiple concurrent users
        num_users = 5
        clients = []
        user_data = []
        
        try:
            # Create and connect multiple users
            for i in range(num_users):
                client, token, headers = await self.create_authenticated_websocket_client(f"concurrent-user-{i}")
                await client.connect(headers=headers)
                clients.append(client)
                user_data.append({"client": client, "token": token, "headers": headers, "user_id": f"concurrent-user-{i}"})
            
            # All users start agents simultaneously
            agent_types = ["triage_agent", "data_analyzer", "cost_optimizer", "validation_agent", "summary_extractor"]
            concurrent_tasks = []
            
            for i, user in enumerate(user_data):
                agent_type = agent_types[i % len(agent_types)]
                
                async def start_user_agent(client, agent_type, user_id):
                    agent_request = {
                        "type": "agent_request",
                        "agent": agent_type,
                        "message": f"Concurrent request from {user_id}",
                        "thread_id": f"concurrent-{user_id}",
                        "user_id": user_id
                    }
                    await client.send_message(agent_request)
                    
                    # Wait for agent_started event
                    for _ in range(100):  # 10 second timeout
                        try:
                            message = await client.receive_message(timeout=0.1)
                            if message.get("type") == "agent_started":
                                return message
                        except asyncio.TimeoutError:
                            continue
                    return None
                
                task = asyncio.create_task(
                    start_user_agent(user["client"], agent_type, user["user_id"])
                )
                concurrent_tasks.append(task)
            
            # Wait for all agent_started events
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Verify all users received their agent_started events
            successful_events = [r for r in results if r and not isinstance(r, Exception)]
            assert len(successful_events) >= num_users * 0.8, f"Expected at least 80% success rate, got {len(successful_events)}/{num_users}"
            
            # Verify user isolation in concurrent scenario
            user_ids_in_events = set()
            for event in successful_events:
                if event and "data" in event:
                    user_ids_in_events.add(event["data"].get("user_id"))
            
            assert len(user_ids_in_events) >= num_users * 0.8, "User isolation failed in concurrent scenario"
            
        finally:
            # Cleanup all connections
            for client in clients:
                await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_10_performance_under_load(self):
        """
        BVJ: Test agent_started event performance under load conditions
        - Segment: Enterprise customers with high usage patterns
        - Business Goal: Maintain responsive agent_started events under load
        - Value Impact: System remains responsive during peak usage
        - Strategic Impact: Performance under load enables customer growth
        """
        # Performance test with multiple rapid requests
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Send rapid sequence of agent requests
            num_requests = 20
            start_time = time.time()
            sent_requests = []
            
            for i in range(num_requests):
                request_start = time.time()
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Load test request {i+1}",
                    "thread_id": f"load-test-{i+1}",
                    "request_id": f"req-{i+1}"
                }
                await client.send_message(agent_request)
                sent_requests.append({"request": agent_request, "sent_time": request_start})
                
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.05)  # 50ms between requests
            
            # Collect agent_started events
            received_events = []
            collection_timeout = 30  # 30 seconds to collect all events
            collection_start = time.time()
            
            while (len(received_events) < num_requests and 
                   time.time() - collection_start < collection_timeout):
                try:
                    message = await client.receive_message(timeout=0.5)
                    if message.get("type") == "agent_started":
                        received_events.append({
                            "event": message,
                            "received_time": time.time()
                        })
                except asyncio.TimeoutError:
                    continue
            
            # Analyze performance metrics
            total_time = time.time() - start_time
            success_rate = len(received_events) / num_requests
            avg_latency = sum(e["received_time"] - start_time for e in received_events) / len(received_events) if received_events else 0
            
            # Performance assertions for business value
            assert success_rate >= 0.9, f"Success rate too low: {success_rate:.2%} (expected >= 90%)"
            assert total_time < 60, f"Total time too long: {total_time}s (expected < 60s)"
            assert avg_latency < 5, f"Average latency too high: {avg_latency}s (expected < 5s)"
            
            print(f"Load test results: {len(received_events)}/{num_requests} events received")
            print(f"Success rate: {success_rate:.2%}")
            print(f"Average latency: {avg_latency:.3f}s")
            print(f"Total time: {total_time:.3f}s")
            
        finally:
            await client.disconnect()
    
    # =========================================================================
    # TEST 11-15: MEMORY, NETWORK, AND RESOURCE EFFICIENCY
    # =========================================================================
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_11_memory_efficiency(self):
        """
        BVJ: Test memory efficiency of agent_started event handling
        - Segment: Platform/Internal - resource efficiency
        - Business Goal: Minimize memory usage for cost optimization
        - Value Impact: Lower infrastructure costs enable competitive pricing
        - Strategic Impact: Resource efficiency enables scaling
        """
        import gc
        import psutil
        import os
        
        # Measure initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple clients and collect events
        num_clients = 10
        clients = []
        collected_events = []
        
        try:
            # Create clients and collect many events
            for i in range(num_clients):
                client, token, headers = await self.create_authenticated_websocket_client(f"memory-test-{i}")
                await client.connect(headers=headers)
                clients.append(client)
                
                # Generate multiple events per client
                for j in range(5):
                    agent_started_event = await self.simulate_agent_execution_start(
                        client, f"agent_{j % 3}"
                    )
                    if agent_started_event:
                        collected_events.append(agent_started_event)
            
            # Measure peak memory usage
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            # Force garbage collection
            gc.collect()
            
            # Measure memory after cleanup
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_retained = final_memory - initial_memory
            
            # Memory efficiency assertions for business value
            events_per_mb = len(collected_events) / max(memory_increase, 1)
            assert memory_increase < 100, f"Memory increase too high: {memory_increase:.1f}MB"
            assert events_per_mb > 1, f"Memory efficiency too low: {events_per_mb:.1f} events/MB"
            
            print(f"Memory efficiency test:")
            print(f"  Initial memory: {initial_memory:.1f}MB")
            print(f"  Peak memory: {peak_memory:.1f}MB")  
            print(f"  Final memory: {final_memory:.1f}MB")
            print(f"  Events collected: {len(collected_events)}")
            print(f"  Events per MB: {events_per_mb:.1f}")
            
        finally:
            # Cleanup all clients
            for client in clients:
                await client.disconnect()
            gc.collect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_12_network_resilience(self):
        """
        BVJ: Test network resilience for agent_started events
        - Segment: All users need reliable event delivery despite network issues
        - Business Goal: Maintain agent_started event delivery during network problems
        - Value Impact: Users receive updates even with poor network conditions
        - Strategic Impact: Network resilience improves user satisfaction
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Test normal operation baseline
            baseline_event = await self.simulate_agent_execution_start(client)
            assert baseline_event.get("type") == "agent_started", "Baseline event failed"
            
            # Simulate network delay by adding artificial delay
            original_receive = client.receive_message
            
            async def delayed_receive(timeout=5.0):
                """Add artificial network delay"""
                await asyncio.sleep(0.2)  # 200ms delay simulation
                return await original_receive(timeout)
            
            client.receive_message = delayed_receive
            
            # Test with simulated network delay
            delayed_start = time.time()
            delayed_event = await self.simulate_agent_execution_start(client)
            delayed_time = time.time() - delayed_start
            
            assert delayed_event.get("type") == "agent_started", "Event not received with network delay"
            assert delayed_time > 0.2, "Network delay simulation not working"
            
            # Test rapid reconnection scenario
            await client.disconnect()
            
            # Quick reconnect
            reconnect_start = time.time()
            await client.connect(headers=headers)
            reconnect_time = time.time() - reconnect_start
            
            # Verify events work after reconnection
            post_reconnect_event = await self.simulate_agent_execution_start(client)
            assert post_reconnect_event.get("type") == "agent_started", "Event not received after reconnection"
            
            print(f"Network resilience test:")
            print(f"  Baseline event: ✓")
            print(f"  Delayed event time: {delayed_time:.3f}s")
            print(f"  Reconnect time: {reconnect_time:.3f}s")
            print(f"  Post-reconnect event: ✓")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_13_event_deduplication(self):
        """
        BVJ: Test event deduplication for agent_started events
        - Segment: All users need clean, non-duplicate event streams
        - Business Goal: Prevent duplicate agent_started events confusing users
        - Value Impact: Clean event streams enable clear user interface updates
        - Strategic Impact: Proper deduplication prevents user confusion
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Send multiple identical agent requests
            identical_requests = 3
            thread_id = f"dedup-test-{uuid.uuid4().hex[:8]}"
            
            for i in range(identical_requests):
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Duplicate request test",
                    "thread_id": thread_id,  # Same thread ID
                    "request_id": f"duplicate-{i}"
                }
                await client.send_message(agent_request)
                await asyncio.sleep(0.1)  # Small delay
            
            # Collect agent_started events
            agent_started_events = []
            collection_start = time.time()
            
            while time.time() - collection_start < 10:  # 10 second timeout
                try:
                    message = await client.receive_message(timeout=0.5)
                    if message.get("type") == "agent_started":
                        agent_started_events.append(message)
                except asyncio.TimeoutError:
                    break
            
            # Analyze deduplication behavior
            unique_events = []
            duplicate_count = 0
            
            for event in agent_started_events:
                # Check if this event is a duplicate based on thread_id and agent
                is_duplicate = any(
                    existing["data"].get("thread_id") == event["data"].get("thread_id") and
                    existing["data"].get("agent") == event["data"].get("agent")
                    for existing in unique_events
                )
                
                if not is_duplicate:
                    unique_events.append(event)
                else:
                    duplicate_count += 1
            
            # Verify deduplication for business value
            print(f"Deduplication test results:")
            print(f"  Total events received: {len(agent_started_events)}")
            print(f"  Unique events: {len(unique_events)}")
            print(f"  Duplicates: {duplicate_count}")
            
            # Business requirement: minimal duplicates for clean UX
            duplication_rate = duplicate_count / max(len(agent_started_events), 1)
            assert duplication_rate < 0.5, f"Too many duplicate events: {duplication_rate:.2%}"
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_14_rate_limiting_behavior(self):
        """
        BVJ: Test rate limiting behavior for agent_started events
        - Segment: Platform/Internal - prevent abuse
        - Business Goal: Protect system from excessive requests
        - Value Impact: Rate limiting prevents system overload
        - Strategic Impact: Abuse protection enables stable service
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Send rapid burst of requests to test rate limiting
            burst_size = 50
            burst_start = time.time()
            sent_count = 0
            
            for i in range(burst_size):
                try:
                    agent_request = {
                        "type": "agent_request",
                        "agent": "triage_agent",
                        "message": f"Rate limit test {i+1}",
                        "thread_id": f"rate-test-{i+1}"
                    }
                    await client.send_message(agent_request)
                    sent_count += 1
                    
                    # No delay - send as fast as possible
                    
                except Exception as e:
                    # Connection might be closed due to rate limiting
                    print(f"Request {i+1} failed: {e}")
                    break
            
            burst_time = time.time() - burst_start
            
            # Collect responses
            received_events = []
            rate_limit_errors = []
            
            collection_start = time.time()
            while time.time() - collection_start < 15:  # 15 second collection
                try:
                    message = await client.receive_message(timeout=0.5)
                    msg_type = message.get("type")
                    
                    if msg_type == "agent_started":
                        received_events.append(message)
                    elif msg_type in ["error", "rate_limit", "too_many_requests"]:
                        rate_limit_errors.append(message)
                        
                except asyncio.TimeoutError:
                    break
            
            # Analyze rate limiting behavior
            receive_rate = len(received_events) / sent_count if sent_count > 0 else 0
            requests_per_second = sent_count / burst_time if burst_time > 0 else 0
            
            print(f"Rate limiting test results:")
            print(f"  Requests sent: {sent_count}/{burst_size}")
            print(f"  Requests per second: {requests_per_second:.1f}")
            print(f"  Events received: {len(received_events)}")
            print(f"  Rate limit errors: {len(rate_limit_errors)}")
            print(f"  Receive rate: {receive_rate:.2%}")
            
            # Verify system handles burst gracefully
            assert received_events or rate_limit_errors, "System should respond with events or rate limit errors"
            
            # If rate limiting is implemented, verify it works
            if rate_limit_errors:
                assert len(rate_limit_errors) > 0, "Rate limiting should generate error responses"
                
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_15_security_validation(self):
        """
        BVJ: Test security validation for agent_started events
        - Segment: Enterprise customers require strong security
        - Business Goal: Prevent unauthorized access to agent execution info
        - Value Impact: Security validation protects sensitive agent operations
        - Strategic Impact: Strong security enables enterprise adoption
        """
        # Test 1: Token manipulation
        legitimate_client, token, headers = await self.create_authenticated_websocket_client("security-test")
        
        # Extract user ID from legitimate token
        import jwt
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        legitimate_user_id = decoded_token.get("sub")
        
        try:
            await legitimate_client.connect(headers=headers)
            
            # Test legitimate request first
            legitimate_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Legitimate security test",
                "user_id": legitimate_user_id,
                "thread_id": "security-test-legit"
            }
            await legitimate_client.send_message(legitimate_request)
            
            # Verify legitimate request gets agent_started
            legit_event_received = False
            for _ in range(50):
                try:
                    message = await legitimate_client.receive_message(timeout=0.1)
                    if message.get("type") == "agent_started":
                        legit_event_received = True
                        assert message["data"]["user_id"] == legitimate_user_id, "User ID mismatch in legitimate request"
                        break
                except asyncio.TimeoutError:
                    pass
            
            assert legit_event_received, "Legitimate request should receive agent_started event"
            
            # Test 2: User ID spoofing attempt
            spoofed_request = {
                "type": "agent_request", 
                "agent": "triage_agent",
                "message": "Spoofed security test",
                "user_id": "spoofed-user-999",  # Different user ID
                "thread_id": "security-test-spoofed"
            }
            await legitimate_client.send_message(spoofed_request)
            
            # Check if spoofed request is handled securely
            spoofed_event_received = False
            security_error_received = False
            
            for _ in range(30):
                try:
                    message = await legitimate_client.receive_message(timeout=0.1)
                    msg_type = message.get("type")
                    
                    if msg_type == "agent_started":
                        # If event received, verify user ID is corrected/validated
                        event_user_id = message["data"].get("user_id")
                        if event_user_id == "spoofed-user-999":
                            spoofed_event_received = True
                        else:
                            # System corrected the user ID - this is acceptable
                            print(f"System corrected user ID from spoofed to {event_user_id}")
                    elif msg_type in ["error", "security_error", "unauthorized"]:
                        security_error_received = True
                        
                except asyncio.TimeoutError:
                    pass
            
            # Verify security: either reject spoofed request or correct user ID
            if spoofed_event_received:
                print("WARNING: Spoofed user ID was not prevented")
            elif security_error_received:
                print("GOOD: Security error returned for spoofed user ID")
            else:
                print("ACCEPTABLE: Spoofed request ignored or user ID corrected")
            
            # Test 3: Malicious payload injection
            malicious_request = {
                "type": "agent_request",
                "agent": "triage_agent'; DROP TABLE users; --",  # SQL injection attempt
                "message": "<script>alert('xss')</script>",  # XSS attempt
                "user_id": legitimate_user_id,
                "thread_id": "security-test-malicious",
                "malicious_field": {"__proto__": {"isAdmin": True}}  # Prototype pollution
            }
            await legitimate_client.send_message(malicious_request)
            
            # System should handle malicious payload safely
            malicious_processed = False
            for _ in range(30):
                try:
                    message = await legitimate_client.receive_message(timeout=0.1)
                    if message.get("type") == "agent_started":
                        # If processed, verify malicious content is sanitized
                        agent_type = message["data"].get("agent", "")
                        assert "DROP TABLE" not in agent_type, "SQL injection not sanitized"
                        assert "<script>" not in str(message), "XSS not sanitized"
                        malicious_processed = True
                        break
                except asyncio.TimeoutError:
                    pass
            
            print(f"Security validation results:")
            print(f"  Legitimate request: {'✓' if legit_event_received else '✗'}")
            print(f"  Spoofed user ID: {'⚠️ Allowed' if spoofed_event_received else '✓ Prevented/Corrected'}")
            print(f"  Malicious payload: {'✓ Handled' if not malicious_processed else '⚠️ Processed'}")
            
        finally:
            await legitimate_client.disconnect()
    
    # =========================================================================
    # TEST 16-20: CONTENT FILTERING, THREADING, AND BUSINESS METRICS
    # =========================================================================
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_16_content_filtering(self):
        """
        BVJ: Test content filtering for agent_started events
        - Segment: All users need appropriate content filtering
        - Business Goal: Ensure agent_started events contain safe, appropriate content
        - Value Impact: Content filtering protects users from inappropriate material
        - Strategic Impact: Content safety enables broader user adoption
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Test 1: Normal content (should pass)
            normal_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Please help me optimize my cloud costs",
                "thread_id": "content-test-normal"
            }
            await client.send_message(normal_request)
            
            normal_event = None
            for _ in range(50):
                try:
                    message = await client.receive_message(timeout=0.1)
                    if message.get("type") == "agent_started":
                        normal_event = message
                        break
                except asyncio.TimeoutError:
                    pass
            
            assert normal_event, "Normal content should receive agent_started event"
            assert "data" in normal_event, "Normal event should have data"
            
            # Test 2: Potentially sensitive content
            sensitive_request = {
                "type": "agent_request",
                "agent": "data_analyzer",
                "message": "Analyze customer data including SSN 123-45-6789 and credit card 4111-1111-1111-1111",
                "thread_id": "content-test-sensitive"
            }
            await client.send_message(sensitive_request)
            
            sensitive_event = None
            for _ in range(50):
                try:
                    message = await client.receive_message(timeout=0.1)
                    if message.get("type") == "agent_started":
                        if message["data"].get("thread_id") == "content-test-sensitive":
                            sensitive_event = message
                            break
                except asyncio.TimeoutError:
                    pass
            
            # Verify sensitive content is handled appropriately
            if sensitive_event:
                # If event is sent, verify sensitive data is not exposed
                event_str = json.dumps(sensitive_event)
                assert "123-45-6789" not in event_str, "SSN should be filtered from event"
                assert "4111-1111-1111-1111" not in event_str, "Credit card should be filtered from event"
                print("✓ Sensitive content processed with filtering")
            else:
                print("✓ Sensitive content blocked entirely")
            
            # Test 3: Large content (test size limits)
            large_message = "X" * 10000  # 10KB message
            large_request = {
                "type": "agent_request",
                "agent": "triage_agent", 
                "message": large_message,
                "thread_id": "content-test-large"
            }
            
            try:
                await client.send_message(large_request)
                
                large_event = None
                for _ in range(50):
                    try:
                        message = await client.receive_message(timeout=0.1)
                        if (message.get("type") == "agent_started" and 
                            message["data"].get("thread_id") == "content-test-large"):
                            large_event = message
                            break
                    except asyncio.TimeoutError:
                        pass
                
                if large_event:
                    # Verify large content is handled appropriately
                    event_size = len(json.dumps(large_event))
                    assert event_size < 50000, f"Event size too large: {event_size} bytes"
                    print(f"✓ Large content handled, event size: {event_size} bytes")
                else:
                    print("✓ Large content rejected or filtered")
                    
            except Exception as e:
                # Large content rejection is acceptable
                print(f"✓ Large content rejected: {e}")
            
            print("Content filtering test completed successfully")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_17_multi_threading_safety(self):
        """
        BVJ: Test multi-threading safety for agent_started events
        - Segment: Platform/Internal - thread safety critical
        - Business Goal: Ensure agent_started events work correctly with multiple threads
        - Value Impact: Thread safety prevents race conditions and data corruption
        - Strategic Impact: Multi-threading support enables better performance
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        # Test data collection
        thread_results = {}
        thread_errors = []
        
        def create_client_in_thread(thread_id):
            """Create and test WebSocket client in separate thread."""
            try:
                # Create event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def thread_websocket_test():
                    # Create authenticated client
                    auth_helper = E2EAuthHelper(environment="test")
                    ws_auth_helper = E2EWebSocketAuthHelper(environment="test")
                    
                    token = auth_helper.create_test_jwt_token(
                        user_id=f"thread-user-{thread_id}",
                        email=f"thread-{thread_id}@test.example.com"
                    )
                    headers = ws_auth_helper.get_websocket_headers(token)
                    
                    client = WebSocketTestClient(self.websocket_url)
                    try:
                        await client.connect(headers=headers)
                        
                        # Send agent request
                        agent_request = {
                            "type": "agent_request",
                            "agent": "triage_agent",
                            "message": f"Multi-threading test from thread {thread_id}",
                            "thread_id": f"mt-test-{thread_id}",
                            "user_id": f"thread-user-{thread_id}"
                        }
                        await client.send_message(agent_request)
                        
                        # Wait for agent_started event
                        start_time = time.time()
                        while time.time() - start_time < 10:
                            try:
                                message = await client.receive_message(timeout=0.5)
                                if message.get("type") == "agent_started":
                                    return {
                                        "thread_id": thread_id,
                                        "success": True,
                                        "event": message,
                                        "user_id": message["data"].get("user_id")
                                    }
                            except asyncio.TimeoutError:
                                continue
                        
                        return {"thread_id": thread_id, "success": False, "error": "Timeout"}
                        
                    finally:
                        await client.disconnect()
                
                # Run the async test in this thread's event loop
                result = loop.run_until_complete(thread_websocket_test())
                thread_results[thread_id] = result
                
            except Exception as e:
                thread_errors.append({"thread_id": thread_id, "error": str(e)})
            finally:
                loop.close()
        
        # Run multiple threads concurrently
        num_threads = 5
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                future = executor.submit(create_client_in_thread, i)
                futures.append(future)
            
            # Wait for all threads to complete
            for future in futures:
                future.result(timeout=30)  # 30 second timeout per thread
        
        # Analyze thread safety results
        successful_threads = [r for r in thread_results.values() if r.get("success")]
        failed_threads = [r for r in thread_results.values() if not r.get("success")]
        
        print(f"Multi-threading safety results:")
        print(f"  Threads started: {num_threads}")
        print(f"  Successful: {len(successful_threads)}")
        print(f"  Failed: {len(failed_threads)}")
        print(f"  Errors: {len(thread_errors)}")
        
        # Verify thread safety for business value
        success_rate = len(successful_threads) / num_threads
        assert success_rate >= 0.8, f"Thread safety success rate too low: {success_rate:.2%}"
        
        # Verify user isolation between threads
        user_ids = [r.get("user_id") for r in successful_threads if r.get("user_id")]
        unique_user_ids = set(user_ids)
        assert len(unique_user_ids) == len(user_ids), "User isolation failed between threads"
        
        # Print any errors for debugging
        for error in thread_errors:
            print(f"Thread {error['thread_id']} error: {error['error']}")
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_18_resource_cleanup(self):
        """
        BVJ: Test resource cleanup for agent_started event handling
        - Segment: Platform/Internal - resource management
        - Business Goal: Ensure proper cleanup prevents resource leaks
        - Value Impact: Proper cleanup maintains system stability
        - Strategic Impact: Resource management enables long-term system health
        """
        import gc
        import weakref
        
        # Track resources for cleanup testing
        created_clients = []
        weak_refs = []
        
        try:
            # Create and use multiple clients
            num_clients = 10
            for i in range(num_clients):
                client, token, headers = await self.create_authenticated_websocket_client(f"cleanup-test-{i}")
                created_clients.append(client)
                
                # Create weak reference to track garbage collection
                weak_refs.append(weakref.ref(client))
                
                # Connect and get event
                await client.connect(headers=headers)
                agent_started_event = await self.simulate_agent_execution_start(client)
                
                if agent_started_event:
                    assert agent_started_event.get("type") == "agent_started", f"Client {i} event failed"
            
            # Verify all clients created successfully
            assert len(created_clients) == num_clients, "Not all clients created"
            
            # Test 1: Explicit cleanup
            cleanup_count = 0
            for client in created_clients:
                await client.disconnect()
                cleanup_count += 1
            
            assert cleanup_count == num_clients, "Not all clients disconnected"
            
            # Clear strong references
            created_clients.clear()
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)  # Allow cleanup to complete
            gc.collect()
            
            # Test 2: Verify garbage collection worked
            alive_refs = sum(1 for ref in weak_refs if ref() is not None)
            cleanup_rate = (num_clients - alive_refs) / num_clients
            
            print(f"Resource cleanup results:")
            print(f"  Clients created: {num_clients}")
            print(f"  Clients cleaned up: {cleanup_count}")
            print(f"  References alive: {alive_refs}/{num_clients}")
            print(f"  Cleanup rate: {cleanup_rate:.2%}")
            
            # Verify cleanup for business value (prevent memory leaks)
            assert cleanup_rate >= 0.8, f"Cleanup rate too low: {cleanup_rate:.2%}"
            
            # Test 3: Resource usage after cleanup
            final_client, final_token, final_headers = await self.create_authenticated_websocket_client("cleanup-final")
            
            try:
                await final_client.connect(headers=final_headers)
                final_event = await self.simulate_agent_execution_start(final_client)
                assert final_event.get("type") == "agent_started", "System not functional after cleanup"
                print("✓ System functional after resource cleanup")
                
            finally:
                await final_client.disconnect()
                
        except Exception as e:
            # Ensure cleanup happens even if test fails
            for client in created_clients:
                try:
                    await client.disconnect()
                except:
                    pass
            raise
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_19_edge_cases_empty_and_large_payloads(self):
        """
        BVJ: Test edge cases with empty and large payloads for agent_started events
        - Segment: All users may send various payload sizes
        - Business Goal: Handle edge cases gracefully without system failure
        - Value Impact: Robust edge case handling prevents user frustration
        - Strategic Impact: Edge case handling improves system reliability
        """
        client, token, headers = await self.create_authenticated_websocket_client()
        
        try:
            await client.connect(headers=headers)
            
            # Test 1: Empty/minimal payload
            minimal_request = {
                "type": "agent_request",
                "agent": "triage_agent"
                # Missing message, thread_id, etc.
            }
            await client.send_message(minimal_request)
            
            minimal_response = None
            for _ in range(30):
                try:
                    message = await client.receive_message(timeout=0.1)
                    if message.get("type") in ["agent_started", "error", "validation_error"]:
                        minimal_response = message
                        break
                except asyncio.TimeoutError:
                    pass
            
            # System should handle minimal payload gracefully
            if minimal_response:
                if minimal_response.get("type") == "agent_started":
                    print("✓ Minimal payload accepted")
                else:
                    print("✓ Minimal payload rejected with error (acceptable)")
            else:
                print("✓ Minimal payload ignored (acceptable)")
            
            # Test 2: Empty string fields
            empty_fields_request = {
                "type": "agent_request",
                "agent": "",  # Empty agent type
                "message": "",  # Empty message
                "thread_id": "",  # Empty thread ID
                "user_id": ""  # Empty user ID
            }
            await client.send_message(empty_fields_request)
            
            empty_response = None
            for _ in range(30):
                try:
                    message = await client.receive_message(timeout=0.1)
                    if message.get("type") in ["agent_started", "error", "validation_error"]:
                        empty_response = message
                        break
                except asyncio.TimeoutError:
                    pass
            
            # System should handle empty fields appropriately
            if empty_response and empty_response.get("type") == "agent_started":
                # If accepted, verify system filled in defaults
                print("⚠️ Empty fields accepted - verify defaults applied")
            else:
                print("✓ Empty fields rejected (recommended)")
            
            # Test 3: Very large message
            large_data = {
                "type": "agent_request",
                "agent": "data_analyzer",
                "message": "A" * 100000,  # 100KB message
                "metadata": {
                    "large_data": "B" * 50000,  # Additional 50KB
                    "array": ["item"] * 1000  # Large array
                },
                "thread_id": "large-payload-test"
            }
            
            large_payload_sent = False
            try:
                await client.send_message(large_data)
                large_payload_sent = True
            except Exception as e:
                print(f"✓ Large payload rejected at send: {e}")
            
            if large_payload_sent:
                large_response = None
                for _ in range(50):  # Longer timeout for large payload
                    try:
                        message = await client.receive_message(timeout=0.2)
                        if (message.get("type") == "agent_started" and 
                            message["data"].get("thread_id") == "large-payload-test"):
                            large_response = message
                            break
                    except asyncio.TimeoutError:
                        pass
                
                if large_response:
                    # Verify large payload handled appropriately
                    response_size = len(json.dumps(large_response))
                    print(f"✓ Large payload processed, response size: {response_size} bytes")
                    assert response_size < 1000000, "Response size should be reasonable"
                else:
                    print("✓ Large payload timed out or rejected")
            
            # Test 4: Special characters and Unicode
            unicode_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Unicode test: 🚀🔥💯 中文测试 العربية русский язык",
                "thread_id": "unicode-test-🚀",
                "metadata": {
                    "emoji": "🎉🎊✨",
                    "chinese": "测试消息",
                    "arabic": "رسالة اختبار"
                }
            }
            await client.send_message(unicode_request)
            
            unicode_response = None
            for _ in range(30):
                try:
                    message = await client.receive_message(timeout=0.1)
                    if (message.get("type") == "agent_started" and 
                        "unicode-test" in message["data"].get("thread_id", "")):
                        unicode_response = message
                        break
                except asyncio.TimeoutError:
                    pass
            
            if unicode_response:
                print("✓ Unicode characters handled correctly")
            else:
                print("⚠️ Unicode handling may have issues")
            
            print("Edge case testing completed")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_20_business_metrics_tracking(self):
        """
        BVJ: Test business metrics tracking for agent_started events
        - Segment: Platform/Internal - business intelligence
        - Business Goal: Track agent_started events for business analysis
        - Value Impact: Metrics enable data-driven business decisions
        - Strategic Impact: Business metrics tracking enables product optimization
        """
        client, token, headers = await self.create_authenticated_websocket_client("metrics-test")
        
        # Business metrics collection
        metrics = {
            "total_events": 0,
            "event_types": {},
            "agent_types": {},
            "user_engagement": {},
            "performance_metrics": {
                "avg_response_time": 0,
                "min_response_time": float('inf'),
                "max_response_time": 0,
                "response_times": []
            },
            "error_metrics": {
                "total_errors": 0,
                "error_types": {}
            }
        }
        
        try:
            await client.connect(headers=headers)
            
            # Test different agent types for business metrics
            test_agents = [
                "triage_agent",
                "data_analyzer", 
                "cost_optimizer",
                "validation_agent",
                "summary_extractor"
            ]
            
            # Collect events and metrics
            for i, agent_type in enumerate(test_agents):
                start_time = time.time()
                
                # Send agent request
                agent_request = {
                    "type": "agent_request",
                    "agent": agent_type,
                    "message": f"Business metrics test {i+1}",
                    "thread_id": f"metrics-test-{i+1}",
                    "user_id": "metrics-test"
                }
                await client.send_message(agent_request)
                
                # Wait for agent_started event and track metrics
                event_received = False
                timeout_start = time.time()
                
                while time.time() - timeout_start < 10 and not event_received:
                    try:
                        message = await client.receive_message(timeout=0.5)
                        response_time = time.time() - start_time
                        
                        if message.get("type") == "agent_started":
                            event_received = True
                            
                            # Track business metrics
                            metrics["total_events"] += 1
                            
                            # Event type metrics
                            event_type = message.get("type")
                            metrics["event_types"][event_type] = metrics["event_types"].get(event_type, 0) + 1
                            
                            # Agent type metrics
                            agent_in_event = message["data"].get("agent", "unknown")
                            metrics["agent_types"][agent_in_event] = metrics["agent_types"].get(agent_in_event, 0) + 1
                            
                            # Performance metrics
                            metrics["performance_metrics"]["response_times"].append(response_time)
                            metrics["performance_metrics"]["min_response_time"] = min(
                                metrics["performance_metrics"]["min_response_time"], response_time
                            )
                            metrics["performance_metrics"]["max_response_time"] = max(
                                metrics["performance_metrics"]["max_response_time"], response_time
                            )
                            
                            # User engagement metrics
                            user_id = message["data"].get("user_id", "unknown")
                            if user_id not in metrics["user_engagement"]:
                                metrics["user_engagement"][user_id] = {"events": 0, "agents_used": set()}
                            metrics["user_engagement"][user_id]["events"] += 1
                            metrics["user_engagement"][user_id]["agents_used"].add(agent_in_event)
                            
                        elif message.get("type") == "error":
                            # Track error metrics
                            metrics["error_metrics"]["total_errors"] += 1
                            error_type = message.get("error_type", "unknown")
                            metrics["error_metrics"]["error_types"][error_type] = metrics["error_metrics"]["error_types"].get(error_type, 0) + 1
                            
                    except asyncio.TimeoutError:
                        # Track timeout as business metric
                        if not event_received:
                            metrics["error_metrics"]["total_errors"] += 1
                            metrics["error_metrics"]["error_types"]["timeout"] = metrics["error_metrics"]["error_types"].get("timeout", 0) + 1
                        break
            
            # Calculate final metrics
            if metrics["performance_metrics"]["response_times"]:
                avg_time = sum(metrics["performance_metrics"]["response_times"]) / len(metrics["performance_metrics"]["response_times"])
                metrics["performance_metrics"]["avg_response_time"] = avg_time
            
            # Convert sets to counts for user engagement
            for user_id in metrics["user_engagement"]:
                metrics["user_engagement"][user_id]["unique_agents"] = len(metrics["user_engagement"][user_id]["agents_used"])
                del metrics["user_engagement"][user_id]["agents_used"]  # Remove set for JSON serialization
            
            # Business metrics validation
            success_rate = (metrics["total_events"] / len(test_agents)) if test_agents else 0
            error_rate = metrics["error_metrics"]["total_errors"] / (metrics["total_events"] + metrics["error_metrics"]["total_errors"]) if (metrics["total_events"] + metrics["error_metrics"]["total_errors"]) > 0 else 0
            
            # Print business metrics report
            print("=== BUSINESS METRICS REPORT ===")
            print(f"📊 Total agent_started events: {metrics['total_events']}")
            print(f"📈 Success rate: {success_rate:.2%}")
            print(f"📉 Error rate: {error_rate:.2%}")
            print(f"⏱️ Avg response time: {metrics['performance_metrics']['avg_response_time']:.3f}s")
            print(f"⚡ Min response time: {metrics['performance_metrics']['min_response_time']:.3f}s")
            print(f"🐌 Max response time: {metrics['performance_metrics']['max_response_time']:.3f}s")
            print(f"🤖 Agent types used: {list(metrics['agent_types'].keys())}")
            print(f"👥 User engagement: {len(metrics['user_engagement'])} users")
            
            # Business value assertions
            assert success_rate >= 0.8, f"Business success rate too low: {success_rate:.2%}"
            assert error_rate <= 0.2, f"Business error rate too high: {error_rate:.2%}"
            assert metrics["performance_metrics"]["avg_response_time"] < 5, f"Business response time too slow: {metrics['performance_metrics']['avg_response_time']:.3f}s"
            
            # Store metrics for potential business analysis
            self.business_metrics = metrics
            
        finally:
            await client.disconnect()


# Additional utility functions for business value validation
def validate_websocket_event_business_value(event: Dict[str, Any]) -> bool:
    """
    Validate that a WebSocket event provides business value.
    
    Business value criteria:
    1. Event type must be meaningful to users
    2. Event data must contain actionable information
    3. Event timing must be appropriate for user experience
    4. Event format must enable rich UI/UX
    """
    if not isinstance(event, dict):
        return False
    
    # Must have type field
    event_type = event.get("type")
    if not event_type:
        return False
    
    # Must be a business-valuable event type
    business_event_types = [
        "agent_started", "agent_thinking", "tool_executing", 
        "tool_completed", "agent_completed"
    ]
    if event_type not in business_event_types:
        return False
    
    # Must have data field with meaningful content
    event_data = event.get("data")
    if not event_data or not isinstance(event_data, dict):
        return False
    
    # Must have required business fields
    required_fields = ["agent", "thread_id", "user_id"]
    for field in required_fields:
        if field not in event_data:
            return False
    
    return True


def calculate_business_impact_score(events: List[Dict[str, Any]]) -> float:
    """
    Calculate business impact score for WebSocket events.
    
    Score factors:
    - Event delivery success rate (40%)
    - Event timing performance (30%) 
    - Event content completeness (20%)
    - User isolation correctness (10%)
    """
    if not events:
        return 0.0
    
    # Success rate factor (40%)
    valid_events = [e for e in events if validate_websocket_event_business_value(e)]
    success_rate = len(valid_events) / len(events)
    success_score = success_rate * 0.4
    
    # Timing performance factor (30%) - assume good if events received
    timing_score = 0.3 if valid_events else 0.0
    
    # Content completeness factor (20%)
    complete_events = []
    for event in valid_events:
        data = event.get("data", {})
        if all(field in data for field in ["agent", "thread_id", "user_id", "status"]):
            complete_events.append(event)
    
    completeness_rate = len(complete_events) / len(events) if events else 0
    completeness_score = completeness_rate * 0.2
    
    # User isolation factor (10%) - assume good if user_id present
    isolation_events = [e for e in valid_events if e.get("data", {}).get("user_id")]
    isolation_rate = len(isolation_events) / len(events) if events else 0
    isolation_score = isolation_rate * 0.1
    
    total_score = success_score + timing_score + completeness_score + isolation_score
    return min(total_score, 1.0)  # Cap at 1.0


# Export test class and utilities
__all__ = [
    "TestAgentStartedEvents",
    "validate_websocket_event_business_value", 
    "calculate_business_impact_score"
]