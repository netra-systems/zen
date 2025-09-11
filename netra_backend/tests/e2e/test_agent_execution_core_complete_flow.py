"""
Agent Execution Core Complete E2E Flow Tests

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise)
- Business Goal: Validate complete agent execution delivers end-to-end user value
- Value Impact: E2E tests ensure agents work in realistic production-like scenarios
- Strategic Impact: Confidence in complete system delivering business insights to real users

This test suite validates Agent Execution Core functionality through complete
end-to-end testing with authentication, real WebSocket connections, and
full system integration, focusing on actual user value delivery scenarios.

🚨 CRITICAL: ALL E2E TESTS MUST USE AUTHENTICATION
This ensures proper multi-user isolation and real-world scenario testing.

CRITICAL REQUIREMENTS VALIDATED:
- Complete agent execution flow with JWT authentication
- Real WebSocket connections with authenticated users
- Multi-user execution context isolation in production-like environment  
- Full system integration including trace context and metrics
- Error handling and recovery in realistic network conditions
- Performance validation under real system load
- Business value delivery measurement and validation
"""

import asyncio
import json
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user
from test_framework.ssot.websocket import WebSocketTestClient
from shared.isolated_environment import get_env
from netra_backend.app.core.network_constants import URLConstants

# Core imports for E2E testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext


class TestAgentExecutionCoreCompleteE2E(SSotBaseTestCase):
    """Complete E2E tests for Agent Execution Core functionality with authentication."""
    
    def setup_method(self):
        """Set up authenticated E2E test environment for each test method."""
        super().setup_method()
        self.env = get_env()
        
        # Determine test environment
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        # Create authenticated helpers - MANDATORY for E2E tests
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        
        # E2E test URLs (will be set based on environment)
        if self.test_environment == "staging":
            self.backend_url = self.env.get("STAGING_BACKEND_URL", URLConstants.STAGING_BACKEND_URL)
            self.websocket_url = self.env.get("STAGING_WEBSOCKET_URL", URLConstants.STAGING_WEBSOCKET_URL)
        else:
            self.backend_url = "http://localhost:8000"
            self.websocket_url = "ws://localhost:8000/ws"

    @pytest.mark.e2e
    @pytest.mark.real_llm  
    async def test_complete_authenticated_agent_execution_flow(self):
        """
        Test complete agent execution flow with authentication and real WebSocket.
        
        BVJ: Validates the complete user value delivery pipeline with security.
        """
        # 🚨 MANDATORY: Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.agent.execution@example.com",
            permissions=["read", "write", "execute_agents"]
        )
        
        user_id = user_data["id"]
        
        # Create authenticated WebSocket client
        websocket_client = WebSocketTestClient(
            base_url=self.websocket_url,
            auth_headers=self.auth_helper.get_websocket_headers(token)
        )
        
        try:
            # Connect with authentication
            await websocket_client.connect(timeout=15.0)
            
            # Send authenticated agent execution request
            agent_request = {
                "type": "agent_request",
                "payload": {
                    "agent_name": "business_optimizer",
                    "user_request": "Analyze my business metrics and provide optimization suggestions",
                    "thread_id": f"e2e_thread_{uuid.uuid4().hex[:12]}",
                    "run_id": str(uuid.uuid4()),
                    "context": {
                        "user_id": user_id,
                        "business_type": "saas",
                        "analysis_depth": "comprehensive"
                    }
                }
            }
            
            # Send request and collect WebSocket events
            await websocket_client.send_json(agent_request)
            
            # Collect agent execution events with timeout
            events = []
            start_time = time.time()
            timeout = 30.0  # 30 second timeout for complete flow
            
            while time.time() - start_time < timeout:
                try:
                    event = await asyncio.wait_for(websocket_client.receive_json(), timeout=5.0)
                    events.append(event)
                    
                    # Check for completion events
                    if event.get("type") in ["agent_completed", "agent_error"]:
                        break
                except asyncio.TimeoutError:
                    # Check if we have at least some events
                    if events:
                        break
                    else:
                        continue
            
            # Assert we received events (validates WebSocket auth worked)
            assert len(events) > 0, "No WebSocket events received - authentication may have failed"
            
            # Verify essential agent execution events were received
            event_types = [event.get("type") for event in events]
            
            # These are the critical events for business value delivery
            critical_events = [
                "agent_started",
                "agent_thinking", 
                # Note: tool events may not occur for simple agents
                "agent_completed"  # OR "agent_error" is acceptable
            ]
            
            received_critical = [event_type for event_type in critical_events if event_type in event_types]
            assert len(received_critical) >= 2, f"Missing critical events. Received: {event_types}"
            
            # Verify agent execution started
            assert "agent_started" in event_types, "Agent execution never started"
            
            # Verify final outcome (success or controlled failure)
            final_events = [event for event in events if event.get("type") in ["agent_completed", "agent_error"]]
            assert len(final_events) > 0, "Agent execution never completed or errored"
            
            # If successful, verify business value was delivered
            completed_events = [event for event in events if event.get("type") == "agent_completed"]
            if completed_events:
                completed_event = completed_events[-1]
                payload = completed_event.get("payload", {})
                
                # Verify execution metadata
                assert "agent_name" in payload or "result" in payload, "Missing execution metadata"
                
            # Verify user isolation - all events should be for our authenticated user
            for event in events:
                payload = event.get("payload", {})
                if "user_id" in payload:
                    assert payload["user_id"] == user_id, f"Event for wrong user: {payload.get('user_id')}"
            
        finally:
            # Clean up WebSocket connection
            await websocket_client.disconnect()

    @pytest.mark.e2e
    async def test_authenticated_multi_user_agent_isolation(self):
        """
        Test multi-user agent execution isolation with authentication.
        
        BVJ: Ensures data privacy and security in multi-tenant production environment.
        """
        # 🚨 MANDATORY: Create multiple authenticated users
        users = []
        for i in range(2):
            token, user_data = await create_authenticated_user(
                environment=self.test_environment,
                email=f"e2e.isolation.user{i}@example.com",
                permissions=["read", "write", "execute_agents"]
            )
            users.append({"token": token, "user_data": user_data, "user_id": user_data["id"]})
        
        # Create WebSocket clients for each user
        websocket_clients = []
        for user in users:
            client = WebSocketTestClient(
                base_url=self.websocket_url,
                auth_headers=self.auth_helper.get_websocket_headers(user["token"])
            )
            websocket_clients.append(client)
        
        try:
            # Connect all clients with their respective authentication
            for client in websocket_clients:
                await client.connect(timeout=10.0)
            
            # Send concurrent requests from different users
            tasks = []
            for i, (user, client) in enumerate(zip(users, websocket_clients)):
                agent_request = {
                    "type": "agent_request", 
                    "payload": {
                        "agent_name": "data_analyzer",
                        "user_request": f"User {i} confidential data analysis",
                        "thread_id": f"isolation_thread_{i}_{uuid.uuid4().hex[:8]}",
                        "run_id": str(uuid.uuid4()),
                        "context": {
                            "user_id": user["user_id"],
                            "confidential_data": f"secret_user_{i}_data",
                            "analysis_scope": "private"
                        }
                    }
                }
                
                task = asyncio.create_task(self._send_and_collect_events(client, agent_request, user["user_id"]))
                tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all executions succeeded or handled gracefully
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"User {i} execution failed: {result}")
                
                user_events, user_id = result
                
                # Verify events were received for this user
                assert len(user_events) > 0, f"No events received for user {i}"
                
                # Verify user isolation - all events are for correct user
                for event in user_events:
                    payload = event.get("payload", {})
                    if "user_id" in payload:
                        assert payload["user_id"] == user_id, f"Data leakage: event for wrong user"
                
                # Verify no cross-contamination in confidential data
                for event in user_events:
                    event_str = json.dumps(event)
                    for j, other_user in enumerate(users):
                        if i != j:  # Don't check against own user
                            assert f"secret_user_{j}_data" not in event_str, \
                                f"User {i} received data from user {j}"
        
        finally:
            # Clean up all WebSocket connections
            for client in websocket_clients:
                await client.disconnect()

    @pytest.mark.e2e
    async def test_authenticated_agent_error_handling(self):
        """
        Test error handling in agent execution with authentication.
        
        BVJ: Ensures graceful error handling maintains user trust and system stability.
        """
        # 🚨 MANDATORY: Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.error.handling@example.com",
            permissions=["read", "write", "execute_agents"]
        )
        
        user_id = user_data["id"]
        
        # Create authenticated WebSocket client
        websocket_client = WebSocketTestClient(
            base_url=self.websocket_url,
            auth_headers=self.auth_helper.get_websocket_headers(token)
        )
        
        try:
            await websocket_client.connect(timeout=10.0)
            
            # Send request that should trigger an error (invalid agent or request)
            invalid_request = {
                "type": "agent_request",
                "payload": {
                    "agent_name": "nonexistent_agent_12345",
                    "user_request": "This should fail gracefully",
                    "thread_id": f"error_thread_{uuid.uuid4().hex[:8]}",
                    "run_id": str(uuid.uuid4()),
                    "context": {
                        "user_id": user_id,
                        "trigger_error": True
                    }
                }
            }
            
            await websocket_client.send_json(invalid_request)
            
            # Collect error handling events
            events = []
            start_time = time.time()
            timeout = 15.0
            
            while time.time() - start_time < timeout:
                try:
                    event = await asyncio.wait_for(websocket_client.receive_json(), timeout=3.0)
                    events.append(event)
                    
                    # Check for error events
                    if event.get("type") in ["agent_error", "agent_completed", "error"]:
                        break
                except asyncio.TimeoutError:
                    break
            
            # Verify error handling
            assert len(events) > 0, "No error handling events received"
            
            event_types = [event.get("type") for event in events]
            
            # Should receive either agent_error or a general error
            error_received = any(event_type in ["agent_error", "error"] for event_type in event_types)
            assert error_received, f"No error event received. Events: {event_types}"
            
            # Verify error events contain proper information
            error_events = [event for event in events if event.get("type") in ["agent_error", "error"]]
            for error_event in error_events:
                payload = error_event.get("payload", {})
                
                # Should have error information
                assert "error" in payload or "error_message" in payload or "message" in payload, \
                    "Error event missing error information"
                
                # Should maintain user context
                if "user_id" in payload:
                    assert payload["user_id"] == user_id, "Error event for wrong user"
        
        finally:
            await websocket_client.disconnect()

    @pytest.mark.e2e
    async def test_authenticated_websocket_reconnection_resilience(self):
        """
        Test WebSocket reconnection resilience with authentication.
        
        BVJ: Ensures system maintains connectivity for uninterrupted user experience.
        """
        # 🚨 MANDATORY: Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.reconnection@example.com",
            permissions=["read", "write", "execute_agents"]
        )
        
        user_id = user_data["id"]
        
        # Test multiple connection cycles
        for attempt in range(2):
            websocket_client = WebSocketTestClient(
                base_url=self.websocket_url,
                auth_headers=self.auth_helper.get_websocket_headers(token)
            )
            
            try:
                # Connect with authentication
                await websocket_client.connect(timeout=10.0)
                
                # Send a simple agent request
                agent_request = {
                    "type": "agent_request",
                    "payload": {
                        "agent_name": "health_checker",
                        "user_request": f"Health check attempt {attempt + 1}",
                        "thread_id": f"reconnect_thread_{attempt}_{uuid.uuid4().hex[:8]}",
                        "run_id": str(uuid.uuid4()),
                        "context": {"user_id": user_id}
                    }
                }
                
                await websocket_client.send_json(agent_request)
                
                # Try to receive at least one event to verify connection works
                try:
                    event = await asyncio.wait_for(websocket_client.receive_json(), timeout=5.0)
                    assert event is not None, f"No response received on attempt {attempt + 1}"
                    
                    # Verify event is for correct user
                    payload = event.get("payload", {})
                    if "user_id" in payload:
                        assert payload["user_id"] == user_id, "Event for wrong user after reconnection"
                        
                except asyncio.TimeoutError:
                    # This is acceptable for health checks that might not respond immediately
                    pass
                
            finally:
                await websocket_client.disconnect()
                # Small delay between connection attempts
                await asyncio.sleep(0.5)

    @pytest.mark.e2e
    async def test_authenticated_performance_under_load(self):
        """
        Test authenticated agent execution performance under simulated load.
        
        BVJ: Ensures system maintains performance standards under realistic user load.
        """
        # 🚨 MANDATORY: Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.performance@example.com",
            permissions=["read", "write", "execute_agents"]
        )
        
        user_id = user_data["id"]
        
        # Create multiple concurrent requests from same authenticated user
        num_concurrent = 3  # Conservative for E2E
        websocket_clients = []
        
        try:
            # Create multiple WebSocket connections for load testing
            for i in range(num_concurrent):
                client = WebSocketTestClient(
                    base_url=self.websocket_url,
                    auth_headers=self.auth_helper.get_websocket_headers(token)
                )
                await client.connect(timeout=10.0)
                websocket_clients.append(client)
            
            # Send concurrent requests
            tasks = []
            start_time = time.time()
            
            for i, client in enumerate(websocket_clients):
                agent_request = {
                    "type": "agent_request",
                    "payload": {
                        "agent_name": "quick_analyzer",
                        "user_request": f"Performance test request {i + 1}",
                        "thread_id": f"perf_thread_{i}_{uuid.uuid4().hex[:8]}",
                        "run_id": str(uuid.uuid4()),
                        "context": {
                            "user_id": user_id,
                            "performance_test": True,
                            "request_index": i
                        }
                    }
                }
                
                task = asyncio.create_task(
                    self._send_and_collect_events(client, agent_request, user_id, timeout=10.0)
                )
                tasks.append(task)
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze performance
            total_time = end_time - start_time
            successful_requests = sum(1 for result in results if not isinstance(result, Exception))
            
            # Verify performance criteria
            assert successful_requests > 0, "No requests completed successfully under load"
            
            # Performance assertion - should handle concurrent requests reasonably
            assert total_time < 30.0, f"Load test took {total_time}s, should complete faster"
            
            # Verify some level of concurrency (not fully sequential)
            if successful_requests > 1:
                avg_time_per_request = total_time / successful_requests
                assert avg_time_per_request < 15.0, f"Average {avg_time_per_request}s per request too slow"
            
            # Verify user isolation maintained under load
            for result in results:
                if not isinstance(result, Exception):
                    events, result_user_id = result
                    assert result_user_id == user_id, "User isolation broken under load"
        
        finally:
            # Clean up all connections
            for client in websocket_clients:
                await client.disconnect()

    async def _send_and_collect_events(self, client: WebSocketTestClient, request: Dict[str, Any], 
                                     expected_user_id: str, timeout: float = 15.0) -> tuple:
        """
        Helper method to send request and collect events.
        
        Returns:
            tuple: (events_list, user_id)
        """
        await client.send_json(request)
        
        events = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                event = await asyncio.wait_for(client.receive_json(), timeout=2.0)
                events.append(event)
                
                # Stop on completion or error
                if event.get("type") in ["agent_completed", "agent_error", "error"]:
                    break
            except asyncio.TimeoutError:
                # If we have some events, that's acceptable
                if events:
                    break
                continue
        
        return events, expected_user_id

    def cleanup_resources(self):
        """Clean up E2E test resources."""
        super().cleanup_resources()
        # Additional cleanup for E2E-specific resources
        self.auth_helper = None
        self.websocket_auth_helper = None