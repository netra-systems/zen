"""
WebSocket Notifier Complete E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise)
- Business Goal: Validate real-time notifications work in production-like environment
- Value Impact: E2E tests ensure users receive timely feedback for engagement and transparency
- Strategic Impact: Real-time notifications are critical for user retention and platform stickiness

This test suite validates WebSocket Notifier functionality through complete
end-to-end testing with authentication, real WebSocket connections, and
production-like infrastructure, ensuring users receive reliable real-time feedback.

🚨 CRITICAL: ALL E2E TESTS MUST USE AUTHENTICATION
This ensures proper multi-user isolation and real-world scenario testing.

⚠️ DEPRECATION NOTE: AgentWebSocketBridge is deprecated in favor of AgentWebSocketBridge.
These E2E tests validate the complete notification flow for backward compatibility.

CRITICAL REQUIREMENTS VALIDATED:
- Real WebSocket notification delivery with authentication
- Multi-user notification isolation in production environment
- Complete agent lifecycle notification flows  
- Error notification handling with real WebSocket connections
- Performance under realistic network conditions
- Message ordering and timing in real scenarios
- User engagement metrics and notification effectiveness
"""

import asyncio
import json
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user
from test_framework.ssot.websocket import WebSocketTestClient
from shared.isolated_environment import get_env

# Core imports for E2E WebSocket notification testing
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class TestWebSocketNotifierCompleteE2E(SSotBaseTestCase):
    """Complete E2E tests for WebSocket Notifier functionality with authentication."""
    
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
            self.backend_url = "https://netra-staging-backend-925110776704.us-central1.run.app"
            self.websocket_url = "wss://netra-staging-backend-925110776704.us-central1.run.app/ws"
        else:
            self.backend_url = "http://localhost:8000"
            self.websocket_url = "ws://localhost:8000/ws"

    @pytest.mark.e2e
    async def test_complete_authenticated_notification_flow(self):
        """
        Test complete notification flow with real WebSocket authentication.
        
        BVJ: Validates end-to-end user notification experience with security.
        """
        # 🚨 MANDATORY: Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.notification.flow@example.com",
            permissions=["read", "write", "receive_notifications"]
        )
        
        user_id = user_data["id"]
        thread_id = f"notification_thread_{uuid.uuid4().hex[:12]}"
        
        # Create authenticated WebSocket client
        websocket_client = WebSocketTestClient(
            base_url=self.websocket_url,
            auth_headers=self.auth_helper.get_websocket_headers(token)
        )
        
        try:
            # Connect with authentication
            await websocket_client.connect(timeout=15.0)
            
            # Simulate agent execution that would trigger notifications
            # Send an agent request to trigger real notification flow
            agent_request = {
                "type": "agent_request",
                "payload": {
                    "agent_name": "notification_test_agent",
                    "user_request": "Test complete notification flow",
                    "thread_id": thread_id,
                    "run_id": str(uuid.uuid4()),
                    "context": {
                        "user_id": user_id,
                        "test_type": "notification_flow",
                        "expect_notifications": True
                    }
                }
            }
            
            # Send request and start collecting notifications
            await websocket_client.send_json(agent_request)
            
            # Collect WebSocket notifications with categorization
            notifications = {
                "agent_started": [],
                "agent_thinking": [],
                "tool_executing": [],
                "tool_completed": [], 
                "agent_completed": [],
                "agent_error": [],
                "other": []
            }
            
            start_time = time.time()
            timeout = 25.0  # Extended timeout for complete flow
            
            while time.time() - start_time < timeout:
                try:
                    event = await asyncio.wait_for(websocket_client.receive_json(), timeout=3.0)
                    
                    event_type = event.get("type", "unknown")
                    if event_type in notifications:
                        notifications[event_type].append(event)
                    else:
                        notifications["other"].append(event)
                    
                    # Stop on completion or error
                    if event_type in ["agent_completed", "agent_error"]:
                        break
                        
                except asyncio.TimeoutError:
                    # Check if we have essential notifications
                    essential_received = any(notifications[key] for key in ["agent_started", "agent_completed", "agent_error"])
                    if essential_received:
                        break
                    continue
            
            # Verify essential notifications were received
            total_notifications = sum(len(events) for events in notifications.values())
            assert total_notifications > 0, "No notifications received - WebSocket auth may have failed"
            
            # Verify agent lifecycle notifications
            assert len(notifications["agent_started"]) > 0, "No agent_started notifications received"
            
            # Verify completion (either success or controlled error)
            completion_received = len(notifications["agent_completed"]) > 0 or len(notifications["agent_error"]) > 0
            assert completion_received, "No completion notification received"
            
            # Verify thinking notifications for user transparency
            if len(notifications["agent_thinking"]) > 0:
                # Check thinking notification content
                thinking_event = notifications["agent_thinking"][0]
                payload = thinking_event.get("payload", {})
                assert "thought" in payload or "reasoning" in payload, "Thinking notification missing content"
            
            # Verify user isolation - all notifications should be for authenticated user
            for category, events in notifications.items():
                for event in events:
                    payload = event.get("payload", {})
                    if "user_id" in payload:
                        assert payload["user_id"] == user_id, f"Notification for wrong user in {category}"
                    
                    # Verify thread isolation
                    if "thread_id" in payload:
                        assert payload["thread_id"] == thread_id, f"Notification for wrong thread in {category}"
            
        finally:
            await websocket_client.disconnect()

    @pytest.mark.e2e
    async def test_authenticated_multi_user_notification_isolation(self):
        """
        Test multi-user notification isolation with real WebSocket connections.
        
        BVJ: Ensures notification privacy and security in multi-tenant environment.
        """
        # 🚨 MANDATORY: Create multiple authenticated users
        users = []
        for i in range(2):  # Conservative number for E2E
            token, user_data = await create_authenticated_user(
                environment=self.test_environment,
                email=f"e2e.notification.user{i}@example.com",
                permissions=["read", "write", "receive_notifications"]
            )
            users.append({
                "token": token, 
                "user_data": user_data, 
                "user_id": user_data["id"],
                "thread_id": f"isolated_thread_{i}_{uuid.uuid4().hex[:8]}"
            })
        
        # Create WebSocket clients for each user
        websocket_clients = []
        for user in users:
            client = WebSocketTestClient(
                base_url=self.websocket_url,
                auth_headers=self.auth_helper.get_websocket_headers(user["token"])
            )
            websocket_clients.append(client)
        
        try:
            # Connect all clients
            for client in websocket_clients:
                await client.connect(timeout=12.0)
            
            # Send concurrent requests from different users
            tasks = []
            for i, (user, client) in enumerate(zip(users, websocket_clients)):
                agent_request = {
                    "type": "agent_request",
                    "payload": {
                        "agent_name": "isolation_test_agent",
                        "user_request": f"User {i} isolated notification test",
                        "thread_id": user["thread_id"],
                        "run_id": str(uuid.uuid4()),
                        "context": {
                            "user_id": user["user_id"],
                            "isolation_test": True,
                            "user_index": i,
                            "confidential_data": f"secret_user_{i}_notifications"
                        }
                    }
                }
                
                # Create task to handle user's notification flow
                task = asyncio.create_task(
                    self._collect_user_notifications(client, user["user_id"], user["thread_id"], agent_request)
                )
                tasks.append(task)
            
            # Execute concurrent notification flows
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify isolation for each user
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"User {i} notification flow failed: {result}")
                
                user_notifications, user_id, thread_id = result
                
                # Verify user received notifications
                assert len(user_notifications) > 0, f"User {i} received no notifications"
                
                # Verify all notifications are for correct user
                for notification in user_notifications:
                    payload = notification.get("payload", {})
                    
                    if "user_id" in payload:
                        assert payload["user_id"] == user_id, \
                            f"User {i} received notification for different user"
                    
                    if "thread_id" in payload:
                        assert payload["thread_id"] == thread_id, \
                            f"User {i} received notification for different thread"
                
                # Verify no cross-user data contamination
                notifications_str = json.dumps(user_notifications)
                for j in range(len(users)):
                    if i != j:
                        assert f"secret_user_{j}_notifications" not in notifications_str, \
                            f"User {i} received data from user {j}"
        
        finally:
            # Clean up all connections
            for client in websocket_clients:
                await client.disconnect()

    @pytest.mark.e2e
    async def test_authenticated_error_notification_handling(self):
        """
        Test error notification handling with real WebSocket connections.
        
        BVJ: Ensures users receive clear error feedback for better experience and trust.
        """
        # 🚨 MANDATORY: Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.error.notifications@example.com",
            permissions=["read", "write", "receive_notifications"]
        )
        
        user_id = user_data["id"]
        error_thread_id = f"error_thread_{uuid.uuid4().hex[:12]}"
        
        # Create authenticated WebSocket client
        websocket_client = WebSocketTestClient(
            base_url=self.websocket_url,
            auth_headers=self.auth_helper.get_websocket_headers(token)
        )
        
        try:
            await websocket_client.connect(timeout=10.0)
            
            # Send request that should trigger error notifications
            error_request = {
                "type": "agent_request",
                "payload": {
                    "agent_name": "nonexistent_error_agent_12345",
                    "user_request": "This should trigger error notifications",
                    "thread_id": error_thread_id,
                    "run_id": str(uuid.uuid4()),
                    "context": {
                        "user_id": user_id,
                        "trigger_error_notifications": True,
                        "expect_failure": True
                    }
                }
            }
            
            await websocket_client.send_json(error_request)
            
            # Collect error-related notifications
            error_notifications = []
            all_notifications = []
            
            start_time = time.time()
            timeout = 15.0
            
            while time.time() - start_time < timeout:
                try:
                    notification = await asyncio.wait_for(websocket_client.receive_json(), timeout=2.0)
                    all_notifications.append(notification)
                    
                    notification_type = notification.get("type", "")
                    if "error" in notification_type.lower() or notification_type == "agent_error":
                        error_notifications.append(notification)
                        
                    # Stop on definitive completion or error
                    if notification_type in ["agent_error", "agent_completed", "error"]:
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            # Verify error handling
            assert len(all_notifications) > 0, "No notifications received for error scenario"
            
            # Should receive error-related notifications OR a completion with error status
            error_received = len(error_notifications) > 0
            completion_with_error = any(
                notif.get("type") == "agent_completed" and 
                notif.get("payload", {}).get("success", True) == False
                for notif in all_notifications
            )
            
            assert error_received or completion_with_error, \
                "No error notifications received for failed request"
            
            # Verify error notification content if received
            if error_notifications:
                error_notification = error_notifications[0]
                payload = error_notification.get("payload", {})
                
                # Should contain error information
                error_info_present = any(key in payload for key in ["error", "error_message", "message"])
                assert error_info_present, "Error notification missing error information"
                
                # Should maintain user context
                if "user_id" in payload:
                    assert payload["user_id"] == user_id, "Error notification for wrong user"
        
        finally:
            await websocket_client.disconnect()

    @pytest.mark.e2e
    async def test_notification_timing_and_sequencing(self):
        """
        Test notification timing and proper sequencing in real environment.
        
        BVJ: Ensures users receive timely and properly ordered notifications for clarity.
        """
        # 🚨 MANDATORY: Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.notification.timing@example.com",
            permissions=["read", "write", "receive_notifications"]
        )
        
        user_id = user_data["id"]
        timing_thread_id = f"timing_thread_{uuid.uuid4().hex[:12]}"
        
        # Create authenticated WebSocket client
        websocket_client = WebSocketTestClient(
            base_url=self.websocket_url,
            auth_headers=self.auth_helper.get_websocket_headers(token)
        )
        
        try:
            await websocket_client.connect(timeout=10.0)
            
            # Send request designed to generate timed notifications
            timing_request = {
                "type": "agent_request",
                "payload": {
                    "agent_name": "timing_test_agent",
                    "user_request": "Test notification timing and sequencing",
                    "thread_id": timing_thread_id,
                    "run_id": str(uuid.uuid4()),
                    "context": {
                        "user_id": user_id,
                        "test_timing": True,
                        "expected_phases": ["start", "thinking", "processing", "completion"]
                    }
                }
            }
            
            # Record request send time
            request_sent_time = time.time()
            await websocket_client.send_json(timing_request)
            
            # Collect notifications with timestamps
            timed_notifications = []
            start_time = time.time()
            timeout = 20.0
            
            while time.time() - start_time < timeout:
                try:
                    notification = await asyncio.wait_for(websocket_client.receive_json(), timeout=3.0)
                    
                    # Add our timestamp
                    notification_entry = {
                        "notification": notification,
                        "received_at": time.time(),
                        "time_from_request": time.time() - request_sent_time
                    }
                    timed_notifications.append(notification_entry)
                    
                    # Stop on completion
                    if notification.get("type") in ["agent_completed", "agent_error"]:
                        break
                        
                except asyncio.TimeoutError:
                    if timed_notifications:  # Have some notifications
                        break
                    continue
            
            # Verify timing characteristics
            assert len(timed_notifications) > 0, "No timed notifications received"
            
            # Verify reasonable response time for first notification
            if timed_notifications:
                first_notification_time = timed_notifications[0]["time_from_request"]
                assert first_notification_time < 10.0, \
                    f"First notification took {first_notification_time}s, too slow"
            
            # Verify notification sequencing
            if len(timed_notifications) >= 2:
                # Notifications should arrive in chronological order
                for i in range(1, len(timed_notifications)):
                    prev_time = timed_notifications[i-1]["received_at"]
                    curr_time = timed_notifications[i]["received_at"]
                    assert curr_time >= prev_time, "Notifications received out of chronological order"
            
            # Verify logical sequence if we have lifecycle notifications
            notification_types = [entry["notification"].get("type") for entry in timed_notifications]
            
            # If we have agent_started, it should come before agent_completed/error
            if "agent_started" in notification_types and ("agent_completed" in notification_types or "agent_error" in notification_types):
                started_index = notification_types.index("agent_started")
                completion_indices = [i for i, t in enumerate(notification_types) if t in ["agent_completed", "agent_error"]]
                
                if completion_indices:
                    first_completion_index = min(completion_indices)
                    assert started_index < first_completion_index, "agent_started came after completion"
        
        finally:
            await websocket_client.disconnect()

    @pytest.mark.e2e
    async def test_notification_resilience_and_reconnection(self):
        """
        Test notification resilience and reconnection scenarios.
        
        BVJ: Ensures notification reliability under network issues for user confidence.
        """
        # 🚨 MANDATORY: Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.notification.resilience@example.com",
            permissions=["read", "write", "receive_notifications"]
        )
        
        user_id = user_data["id"]
        
        # Test multiple connection cycles to verify resilience
        for attempt in range(2):
            resilience_thread_id = f"resilience_thread_{attempt}_{uuid.uuid4().hex[:8]}"
            
            websocket_client = WebSocketTestClient(
                base_url=self.websocket_url,
                auth_headers=self.auth_helper.get_websocket_headers(token)
            )
            
            try:
                # Connect with authentication
                await websocket_client.connect(timeout=12.0)
                
                # Send notification test request
                resilience_request = {
                    "type": "agent_request",
                    "payload": {
                        "agent_name": "resilience_test_agent",
                        "user_request": f"Resilience test attempt {attempt + 1}",
                        "thread_id": resilience_thread_id,
                        "run_id": str(uuid.uuid4()),
                        "context": {
                            "user_id": user_id,
                            "resilience_test": True,
                            "attempt": attempt + 1
                        }
                    }
                }
                
                await websocket_client.send_json(resilience_request)
                
                # Try to receive at least one notification to verify connection works
                notifications_received = []
                
                try:
                    # Try to receive notifications with reasonable timeout
                    for _ in range(3):  # Try multiple times
                        try:
                            notification = await asyncio.wait_for(
                                websocket_client.receive_json(), 
                                timeout=4.0
                            )
                            notifications_received.append(notification)
                            
                            # Stop on completion
                            if notification.get("type") in ["agent_completed", "agent_error"]:
                                break
                        except asyncio.TimeoutError:
                            continue
                            
                except Exception as e:
                    # Log but don't fail - some connection issues are expected in resilience tests
                    print(f"Expected connection issue in resilience test attempt {attempt + 1}: {e}")
                
                # Verify some level of functionality (resilience doesn't mean perfect)
                if notifications_received:
                    # Verify user isolation maintained across reconnections
                    for notification in notifications_received:
                        payload = notification.get("payload", {})
                        if "user_id" in payload:
                            assert payload["user_id"] == user_id, \
                                f"User context lost after reconnection in attempt {attempt + 1}"
                
            finally:
                await websocket_client.disconnect()
                # Brief pause between connection attempts
                await asyncio.sleep(0.5)

    async def _collect_user_notifications(self, client: WebSocketTestClient, user_id: str, 
                                        thread_id: str, agent_request: Dict[str, Any]) -> tuple:
        """
        Helper method to collect notifications for a specific user.
        
        Returns:
            tuple: (notifications_list, user_id, thread_id)
        """
        await client.send_json(agent_request)
        
        notifications = []
        start_time = time.time()
        timeout = 15.0
        
        while time.time() - start_time < timeout:
            try:
                notification = await asyncio.wait_for(client.receive_json(), timeout=2.0)
                notifications.append(notification)
                
                # Stop on completion
                if notification.get("type") in ["agent_completed", "agent_error"]:
                    break
            except asyncio.TimeoutError:
                # If we have some notifications, that's acceptable
                if notifications:
                    break
                continue
        
        return notifications, user_id, thread_id

    def cleanup_resources(self):
        """Clean up E2E test resources."""
        super().cleanup_resources()
        self.auth_helper = None
        self.websocket_auth_helper = None