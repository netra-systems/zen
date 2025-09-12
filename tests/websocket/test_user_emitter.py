"""
Real UserWebSocketEmitter Integration Tests - Per-User Event Emission with Complete Isolation

Business Value Justification:
- Segment: Platform/Internal + ALL (Free  ->  Enterprise) 
- Business Goal: User Isolation & Chat Value Delivery
- Value Impact: Ensures WebSocket events reach only intended users, enabling secure multi-user chat
- Strategic Impact: Critical for $500K+ ARR - prevents cross-user event leakage, delivers real AI value

This test suite validates the UserWebSocketEmitter using REAL services with proper authentication.
NO MOCKS - follows CLAUDE.md "CHEATING ON TESTS = ABOMINATION" principle.

Key Features Tested:
1. Per-user event emission with complete isolation 
2. All required WebSocket event types for substantive chat value
3. Real authentication and user context validation
4. Event delivery guarantees and retry mechanisms
5. Business IP protection through event sanitization
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

# CRITICAL: Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import websockets
import httpx
from loguru import logger

# Import real production components - NO MOCKS
from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory, WebSocketFactoryConfig
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor

# Import SSOT authentication helpers
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.isolated_environment_fixtures import isolated_environment_manager
from shared.isolated_environment import get_env

# WebSocket test utilities - REAL SERVICES ONLY
from tests.mission_critical.websocket_real_test_base import (
    require_docker_services,
    RealWebSocketTestBase,
    RealWebSocketTestConfig
)


class TestUserWebSocketEmitterReal(SSotBaseTestCase):
    """
    Real UserWebSocketEmitter tests using live services with authentication.
    
    Business Value: Validates the core WebSocket event system that enables 
    substantive AI chat interactions for all user segments.
    
    Tests are designed to FAIL HARD if anything is wrong - no try/except blocks.
    """
    
    @pytest.fixture(scope="class")
    def docker_services(self):
        """Ensure Docker services are running - REAL SERVICES REQUIRED."""
        return require_docker_services()
    
    @pytest.fixture
    def auth_config(self, isolated_environment_manager):
        """SSOT authentication configuration for real services."""
        env = get_env()
        return E2EAuthConfig(
            auth_service_url=f"http://localhost:{env.get('AUTH_SERVICE_PORT', '8083')}",
            backend_url=f"http://localhost:{env.get('BACKEND_PORT', '8002')}",
            websocket_url=f"ws://localhost:{env.get('BACKEND_PORT', '8002')}/ws",
            test_user_email=f"test_user_{uuid.uuid4().hex[:8]}@netra-test.com",
            test_user_password="secure_test_password_123!",
            timeout=30.0  # Real services need more time
        )
    
    @pytest.fixture
    async def authenticated_user(self, auth_config):
        """Create authenticated user context with real JWT tokens."""
        auth_helper = E2EAuthHelper(auth_config)
        
        # Register user with real auth service
        user_data = await auth_helper.register_test_user()
        assert user_data is not None, "Failed to register test user with real auth service"
        assert "access_token" in user_data, "No JWT token received from real auth service"
        
        # Validate token is real and not expired
        jwt_token = user_data["access_token"]
        user_id = user_data["user"]["id"]
        
        # Create authenticated user execution context
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            request_id=f"test_req_{uuid.uuid4().hex[:8]}",
            jwt_token=jwt_token
        )
        
        yield {"context": context, "auth_data": user_data, "config": auth_config}
    
    @pytest.fixture
    async def real_websocket_infrastructure(self, docker_services, isolated_environment_manager):
        """Set up real WebSocket infrastructure components."""
        # Initialize real components with SSOT environment
        env = get_env()
        
        # Real WebSocket connection pool
        connection_pool = WebSocketConnectionPool(
            max_connections=100,
            cleanup_interval=30
        )
        
        # Real WebSocket event router
        event_router = WebSocketEventRouter(connection_pool)
        
        # Real WebSocket bridge factory with production config
        factory_config = WebSocketFactoryConfig(
            max_events_per_user=1000,
            event_timeout_seconds=10.0,
            heartbeat_interval_seconds=30.0,
            delivery_retries=3,
            enable_event_compression=True
        )
        
        bridge_factory = WebSocketBridgeFactory(factory_config)
        bridge_factory.configure(
            connection_pool=connection_pool,
            agent_registry=None,  # Will be created per-request
            health_monitor=get_websocket_notification_monitor()
        )
        
        yield {
            "connection_pool": connection_pool,
            "event_router": event_router,
            "bridge_factory": bridge_factory,
            "notification_monitor": get_websocket_notification_monitor()
        }
        
        # Cleanup real resources
        await connection_pool.cleanup()
    
    @pytest.fixture
    async def real_websocket_connection(self, authenticated_user, auth_config):
        """Establish real WebSocket connection with authentication."""
        context = authenticated_user["context"]
        jwt_token = authenticated_user["auth_data"]["access_token"]
        
        # Connect to real WebSocket endpoint with authentication
        websocket_url = f"{auth_config.websocket_url}?token={jwt_token}"
        
        websocket = None
        try:
            # Establish real WebSocket connection - this will FAIL HARD if service unavailable
            websocket = await websockets.connect(
                websocket_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            logger.info(f"Real WebSocket connection established for user {context.user_id[:8]}...")
            
            yield websocket
            
        except Exception as e:
            # FAIL HARD - no try/except masking in tests
            raise AssertionError(f"Failed to establish real WebSocket connection: {e}")
        finally:
            if websocket:
                await websocket.close()
    
    @pytest.mark.asyncio
    async def test_user_websocket_emitter_initialization_real(
        self, 
        authenticated_user,
        real_websocket_infrastructure
    ):
        """Test UserWebSocketEmitter initialization with real services and authentication.
        
        Business Value: Validates the foundation of per-user WebSocket communication
        that enables secure multi-user chat interactions.
        """
        context = authenticated_user["context"]
        event_router = real_websocket_infrastructure["event_router"]
        
        # Create real UserWebSocketEmitter with authenticated context
        emitter = UserWebSocketEmitter(
            context=context,
            router=event_router,
            connection_id=f"conn_{uuid.uuid4().hex[:8]}"
        )
        
        # Validate emitter initialization with real authentication data
        assert emitter.user_id == context.user_id, "User ID mismatch in emitter"
        assert emitter.thread_id == context.thread_id, "Thread ID mismatch in emitter" 
        assert emitter.run_id == context.run_id, "Run ID mismatch in emitter"
        assert emitter.request_id == context.request_id, "Request ID mismatch in emitter"
        assert emitter.router is event_router, "Event router not properly set"
        
        # Validate metrics tracking
        stats = emitter.get_stats()
        assert stats["user_id"].endswith("..."), "User ID not properly truncated for security"
        assert stats["events_sent"] == 0, "Initial events sent should be 0"
        assert stats["events_failed"] == 0, "Initial events failed should be 0"
        assert "uptime_seconds" in stats, "Uptime metrics missing"
        assert "success_rate" in stats, "Success rate metrics missing"
        
        logger.info(f" PASS:  UserWebSocketEmitter initialized successfully for authenticated user")
    
    @pytest.mark.asyncio
    async def test_agent_started_event_real_delivery(
        self,
        authenticated_user,
        real_websocket_infrastructure,
        real_websocket_connection
    ):
        """Test agent_started event delivery through real WebSocket connection.
        
        Business Value: Validates the critical agent_started event that informs users
        their AI request is being processed - core to chat user experience.
        """
        context = authenticated_user["context"]
        event_router = real_websocket_infrastructure["event_router"]
        websocket = real_websocket_connection
        
        # Register real WebSocket connection in pool
        connection_pool = real_websocket_infrastructure["connection_pool"]
        connection_id = await connection_pool.add_connection(context.user_id, websocket)
        
        # Create emitter with real WebSocket connection
        emitter = UserWebSocketEmitter(
            context=context,
            router=event_router,
            connection_id=connection_id
        )
        
        # Send agent_started event to real WebSocket
        agent_name = "TestAgent"
        metadata = {"test_mode": True, "priority": "high"}
        
        # This should succeed with real WebSocket - FAIL HARD if not
        success = await emitter.notify_agent_started(agent_name, metadata)
        assert success is True, "Agent started notification failed with real WebSocket"
        
        # Receive event from real WebSocket connection
        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        event_data = json.loads(message)
        
        # Validate event structure and content
        assert event_data["type"] == "agent_started", "Wrong event type received"
        assert event_data["run_id"] == context.run_id, "Run ID mismatch in event"
        assert event_data["thread_id"] == context.thread_id, "Thread ID mismatch in event"
        assert event_data["agent_name"] == agent_name, "Agent name mismatch in event"
        assert event_data["request_id"] == context.request_id, "Request ID missing from event"
        
        # Validate payload content
        payload = event_data["payload"]
        assert payload["status"] == "started", "Wrong status in payload"
        assert payload["metadata"] == metadata, "Metadata not preserved in payload"
        assert agent_name in payload["message"], "Agent name not in user message"
        
        # Validate emitter metrics updated
        stats = emitter.get_stats()
        assert stats["events_sent"] == 1, "Events sent metric not updated"
        assert stats["events_failed"] == 0, "No events should have failed"
        assert stats["success_rate"] == 100.0, "Success rate should be 100%"
        
        logger.info(f" PASS:  Agent started event delivered successfully through real WebSocket")
    
    @pytest.mark.asyncio
    async def test_all_critical_websocket_events_real(
        self,
        authenticated_user,
        real_websocket_infrastructure,
        real_websocket_connection
    ):
        """Test all critical WebSocket events required for substantive chat value.
        
        Business Value: Validates ALL WebSocket events needed for complete AI chat experience.
        This covers the full spectrum of user-visible AI interaction events.
        """
        context = authenticated_user["context"]
        event_router = real_websocket_infrastructure["event_router"]
        websocket = real_websocket_connection
        
        # Register connection and create emitter
        connection_pool = real_websocket_infrastructure["connection_pool"]
        connection_id = await connection_pool.add_connection(context.user_id, websocket)
        
        emitter = UserWebSocketEmitter(
            context=context,
            router=event_router, 
            connection_id=connection_id
        )
        
        agent_name = "ComprehensiveTestAgent"
        
        # Event tracking
        received_events = []
        expected_event_types = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "progress_update",
            "agent_completed"
        ]
        
        # Send all critical WebSocket events in realistic sequence
        logger.info("Sending agent_started event...")
        success = await emitter.notify_agent_started(agent_name, {"task": "comprehensive_test"})
        assert success, "agent_started failed"
        
        logger.info("Sending agent_thinking event...")
        success = await emitter.notify_agent_thinking(agent_name, "Analyzing user request and planning approach", "analysis")
        assert success, "agent_thinking failed"
        
        logger.info("Sending tool_executing event...")
        success = await emitter.notify_tool_executing(agent_name, "SearchTool", {"query": "test search", "limit": 10})
        assert success, "tool_executing failed"
        
        logger.info("Sending tool_completed event...")
        success = await emitter.notify_tool_completed(agent_name, "SearchTool", True, "Found 5 relevant results")
        assert success, "tool_completed failed"
        
        logger.info("Sending progress_update event...")
        success = await emitter.notify_progress_update(agent_name, 75.0, "Processing search results", "30 seconds")
        assert success, "progress_update failed"
        
        logger.info("Sending agent_completed event...")
        success = await emitter.notify_agent_completed(agent_name, {"status": "success", "results": "Comprehensive analysis completed"}, True)
        assert success, "agent_completed failed"
        
        # Receive all events from real WebSocket
        for i, expected_type in enumerate(expected_event_types):
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            event_data = json.loads(message)
            received_events.append(event_data)
            
            # Validate each event
            assert event_data["type"] == expected_type, f"Expected {expected_type}, got {event_data['type']}"
            assert event_data["run_id"] == context.run_id, f"Run ID mismatch in {expected_type}"
            assert event_data["thread_id"] == context.thread_id, f"Thread ID mismatch in {expected_type}"
            assert event_data["agent_name"] == agent_name, f"Agent name mismatch in {expected_type}"
            assert "timestamp" in event_data, f"Timestamp missing in {expected_type}"
            assert "payload" in event_data, f"Payload missing in {expected_type}"
            
            logger.info(f" PASS:  Received and validated {expected_type} event")
        
        # Validate emitter final stats
        final_stats = emitter.get_stats()
        assert final_stats["events_sent"] == len(expected_event_types), "Event count mismatch"
        assert final_stats["events_failed"] == 0, "No events should have failed"
        assert final_stats["success_rate"] == 100.0, "Perfect success rate expected"
        
        logger.info(f" PASS:  All {len(expected_event_types)} critical WebSocket events validated")
    
    @pytest.mark.asyncio
    async def test_event_sanitization_business_ip_protection(
        self,
        authenticated_user,
        real_websocket_infrastructure,
        real_websocket_connection
    ):
        """Test event sanitization prevents business IP leakage in real WebSocket events.
        
        Business Value: Protects Netra's business IP by ensuring sensitive information
        is sanitized before being sent to users through WebSocket events.
        """
        context = authenticated_user["context"]
        event_router = real_websocket_infrastructure["event_router"]
        websocket = real_websocket_connection
        
        # Setup emitter with real connection
        connection_pool = real_websocket_infrastructure["connection_pool"]
        connection_id = await connection_pool.add_connection(context.user_id, websocket)
        
        emitter = UserWebSocketEmitter(
            context=context,
            router=event_router,
            connection_id=connection_id
        )
        
        # Send tool_executing event with sensitive data
        sensitive_tool_input = {
            "query": "user search query",  # Safe
            "api_key": "sk-1234567890abcdef",  # Should be redacted
            "password": "secret123",  # Should be redacted
            "token": "bearer_xyz123",  # Should be redacted
            "large_data": "x" * 500,  # Should be truncated
            "normal_param": "safe_value"  # Should pass through
        }
        
        success = await emitter.notify_tool_executing("TestAgent", "APITool", sensitive_tool_input)
        assert success, "Tool executing notification failed"
        
        # Receive event from real WebSocket
        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        event_data = json.loads(message)
        
        # Validate sanitization occurred
        tool_input = event_data["payload"]["tool_input"]
        
        # Sensitive data should be redacted
        assert tool_input["api_key"] == "[REDACTED]", "API key not redacted"
        assert tool_input["password"] == "[REDACTED]", "Password not redacted"
        assert tool_input["token"] == "[REDACTED]", "Token not redacted"
        
        # Large data should be truncated
        assert len(tool_input["large_data"]) < 500, "Large data not truncated"
        assert tool_input["large_data"].endswith("..."), "Truncation marker missing"
        
        # Safe data should pass through
        assert tool_input["query"] == "user search query", "Safe query data modified"
        assert tool_input["normal_param"] == "safe_value", "Normal param modified"
        
        logger.info(" PASS:  Business IP protection validated through event sanitization")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_isolation_real(
        self,
        docker_services,
        real_websocket_infrastructure,
        auth_config
    ):
        """Test complete user isolation with concurrent real WebSocket connections.
        
        Business Value: Validates that multiple users can use the system simultaneously
        without any cross-user event leakage - critical for multi-user chat.
        """
        auth_helper = E2EAuthHelper(auth_config)
        event_router = real_websocket_infrastructure["event_router"]
        connection_pool = real_websocket_infrastructure["connection_pool"]
        
        # Create multiple authenticated users
        num_users = 3
        users = []
        websockets = []
        emitters = []
        
        try:
            # Setup multiple real authenticated users and WebSocket connections
            for i in range(num_users):
                # Register unique user
                user_data = await auth_helper.register_test_user()
                context = UserExecutionContext(
                    user_id=user_data["user"]["id"],
                    thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                    run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
                    request_id=f"req_{i}_{uuid.uuid4().hex[:8]}",
                    jwt_token=user_data["access_token"]
                )
                
                # Establish real WebSocket connection
                websocket_url = f"{auth_config.websocket_url}?token={user_data['access_token']}"
                websocket = await websockets.connect(websocket_url, ping_interval=20)
                
                # Register connection and create emitter
                connection_id = await connection_pool.add_connection(context.user_id, websocket)
                emitter = UserWebSocketEmitter(
                    context=context,
                    router=event_router,
                    connection_id=connection_id
                )
                
                users.append({"context": context, "auth_data": user_data})
                websockets.append(websocket)
                emitters.append(emitter)
                
                logger.info(f"User {i+1} setup complete: {context.user_id[:8]}...")
            
            # Send unique events to each user simultaneously
            agent_name = "IsolationTestAgent"
            send_tasks = []
            
            for i, emitter in enumerate(emitters):
                task = emitter.notify_agent_started(agent_name, {"user_index": i, "isolation_test": True})
                send_tasks.append(task)
            
            # Send all events concurrently
            send_results = await asyncio.gather(*send_tasks)
            assert all(send_results), "Not all events sent successfully"
            
            # Receive events and validate isolation
            for i, websocket in enumerate(websockets):
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                event_data = json.loads(message)
                
                # Validate this user only received their own event
                expected_user_id = users[i]["context"].user_id
                expected_thread_id = users[i]["context"].thread_id
                expected_user_index = i
                
                assert event_data["type"] == "agent_started", f"Wrong event type for user {i}"
                assert event_data["thread_id"] == expected_thread_id, f"Thread ID mismatch for user {i}"
                assert event_data["payload"]["metadata"]["user_index"] == expected_user_index, f"Wrong user data for user {i}"
                
                logger.info(f" PASS:  User {i+1} received only their own event")
            
            # Validate no additional events received (no cross-user leakage)
            for i, websocket in enumerate(websockets):
                with pytest.raises(asyncio.TimeoutError):
                    # This should timeout - no additional events should be received
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                
                logger.info(f" PASS:  User {i+1} received no additional events - isolation confirmed")
                
        finally:
            # Cleanup all connections
            for websocket in websockets:
                if websocket:
                    await websocket.close()
        
        logger.info(f" PASS:  Complete user isolation validated with {num_users} concurrent users")
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling_real_failure_scenarios(
        self,
        authenticated_user,
        real_websocket_infrastructure
    ):
        """Test WebSocket error handling with real failure scenarios.
        
        Business Value: Validates error handling that prevents system failures
        when WebSocket connections have issues - ensures chat reliability.
        """
        context = authenticated_user["context"]
        event_router = real_websocket_infrastructure["event_router"]
        
        # Create emitter without real WebSocket connection (simulates connection failure)
        emitter = UserWebSocketEmitter(
            context=context,
            router=event_router,
            connection_id="nonexistent_connection"
        )
        
        # Attempt to send event with no connection - should handle gracefully
        success = await emitter.notify_agent_started("TestAgent", {"test": "error_handling"})
        
        # Should return False but not crash
        assert success is False, "Should return False for failed event sending"
        
        # Validate error metrics updated
        stats = emitter.get_stats()
        assert stats["events_sent"] == 0, "No events should have been sent"
        assert stats["events_failed"] == 1, "One event should have failed"
        assert stats["success_rate"] == 0.0, "Success rate should be 0%"
        
        logger.info(" PASS:  Error handling validated - system handles connection failures gracefully")


# Test configuration and setup
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Mark all tests as requiring Docker services
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration, 
    pytest.mark.websocket,
    pytest.mark.real_services  # Custom marker for real service tests
]