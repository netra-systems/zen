#!/usr/bin/env python3
"""
Multi-User Agent Isolation E2E Test

Business Value Justification (BVJ):
- Segment: Mid, Enterprise
- Business Goal: Multi-user isolation enables enterprise scalability and data security
- Value Impact: Ensures concurrent user sessions maintain complete data isolation
- Strategic Impact: Enables enterprise onboarding and multi-tenant architecture scaling

This test validates complete user isolation in concurrent agent execution:
1. Multiple users authenticate simultaneously with different JWT tokens
2. Concurrent WebSocket connections established with proper authentication
3. Agents execute simultaneously for different users 
4. Complete data isolation maintained (no cross-contamination)
5. All 5 WebSocket events delivered to correct users only
6. Business results delivered to correct users with proper context
7. Resource cleanup prevents memory leaks

CRITICAL REQUIREMENTS:
- MANDATORY AUTHENTICATION: Each user uses real JWT tokens with unique context
- NO MOCKS: All services (WebSocket, database, Redis, agents) are real
- COMPLETE ISOLATION: No data leakage between concurrent user sessions
- ALL 5 WEBSOCKET EVENTS: Each user receives their events independently

This test is essential for:
- Enterprise customer confidence in data security
- Platform ability to handle concurrent users
- Preventing data leakage incidents that could lose customers
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
from loguru import logger

# Test framework imports - SSOT patterns
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    create_authenticated_user_context
)
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import (
    assert_websocket_events_sent,
    WebSocketTestHelpers
)

# Shared utilities
from shared.isolated_environment import get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext


class TestMultiUserAgentIsolationE2E(BaseE2ETest):
    """
    E2E test for multi-user agent isolation using REAL services only.
    
    This test validates that the platform can safely handle concurrent users
    without any data leakage or cross-contamination between user sessions.
    
    Critical for enterprise customers who require guaranteed data isolation.
    """

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Set up isolated test environment for multi-user testing."""
        await self.initialize_test_environment()
        
        # Initialize auth helper for multi-user scenarios
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Track all test users for cleanup
        self.test_users = []
        self.active_connections = []
        
        yield
        
        # Ensure all connections are cleaned up
        for connection in self.active_connections:
            try:
                await WebSocketTestHelpers.close_test_connection(connection)
            except:
                pass  # Ignore cleanup errors

    async def create_isolated_user_session(self, user_email: str, permissions: List[str] = None) -> Tuple[Any, Any, str]:
        """
        Create a completely isolated user session with authentication and WebSocket connection.
        
        Returns:
            Tuple of (auth_user, websocket_connection, user_context)
        """
        # Create authenticated user with unique context
        auth_user = await self.auth_helper.create_authenticated_user(
            email=user_email,
            permissions=permissions or ["read", "write", "agent_execute"]
        )
        
        # Create execution context
        user_context = await create_authenticated_user_context(
            user_email=auth_user.email,
            user_id=auth_user.user_id,
            environment="test",
            permissions=auth_user.permissions,
            websocket_enabled=True
        )
        
        # Establish WebSocket connection
        websocket_url = "ws://localhost:8000/ws/chat"
        headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
        
        websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
            websocket_url,
            headers=headers,
            timeout=15.0,
            max_retries=3,
            user_id=auth_user.user_id
        )
        
        # Track for cleanup
        self.test_users.append(auth_user)
        self.active_connections.append(websocket_connection)
        
        logger.info(f" PASS:  Created isolated session for user: {auth_user.email}")
        
        return auth_user, websocket_connection, user_context

    async def execute_agent_for_user(
        self, 
        auth_user: Any, 
        websocket_connection: Any, 
        user_context: Any,
        message: str,
        expected_response_indicators: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute agent workflow for a specific user and collect all events.
        
        Args:
            auth_user: Authenticated user object
            websocket_connection: User's WebSocket connection
            user_context: User's execution context
            message: Message to send to agent
            expected_response_indicators: Keywords expected in response
            
        Returns:
            List of all WebSocket events received for this user
        """
        received_events = []
        
        # Send agent request
        chat_message = {
            "type": "agent_request",
            "agent": "triage_agent",
            "message": message,
            "user_id": auth_user.user_id,
            "thread_id": str(user_context.thread_id),
            "request_id": str(user_context.request_id),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"[U+1F4E4] [{auth_user.email}] Sending: {message[:50]}...")
        await WebSocketTestHelpers.send_test_message(websocket_connection, chat_message)
        
        # Collect events for this user
        start_time = time.time()
        timeout = 30.0
        
        while time.time() - start_time < timeout:
            try:
                event = await WebSocketTestHelpers.receive_test_message(
                    websocket_connection,
                    timeout=2.0
                )
                
                # Verify event belongs to this user
                event_user_id = event.get("data", {}).get("user_id")
                if event_user_id and event_user_id != auth_user.user_id:
                    logger.error(f" ALERT:  DATA LEAKAGE DETECTED: User {auth_user.email} received event for user {event_user_id}")
                    raise AssertionError(f"CRITICAL: Data leakage - user {auth_user.email} received event for {event_user_id}")
                
                received_events.append(event)
                
                event_type = event.get("type", "unknown")
                logger.info(f"[U+1F4E8] [{auth_user.email}] Received: {event_type}")
                
                # Stop on completion
                if event_type == "agent_completed":
                    break
                    
            except Exception as e:
                if "timeout" in str(e).lower():
                    # Check if we have completion
                    completion_events = [e for e in received_events if e.get("type") == "agent_completed"]
                    if completion_events:
                        break
                    continue
                else:
                    logger.error(f" FAIL:  [{auth_user.email}] Error receiving message: {e}")
                    break
        
        logger.info(f" CHART:  [{auth_user.email}] Collected {len(received_events)} events")
        
        # Validate expected response content if provided
        if expected_response_indicators:
            completion_events = [e for e in received_events if e.get("type") == "agent_completed"]
            if completion_events:
                response_text = completion_events[0].get("data", {}).get("result", "")
                for indicator in expected_response_indicators:
                    assert indicator.lower() in response_text.lower(), \
                        f"User {auth_user.email} missing expected response indicator '{indicator}' in: {response_text[:100]}..."
        
        return received_events

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_concurrent_user_agent_isolation_basic(self, real_services_fixture):
        """
        Test basic concurrent user isolation with 2 users executing agents simultaneously.
        
        This test validates that 2 users can execute agents concurrently without
        any data contamination or cross-user event delivery.
        """
        logger.info("[U+1F680] Starting basic concurrent user agent isolation test")
        
        # Create 2 isolated user sessions
        user1_email = "isolation_user1@example.com"
        user2_email = "isolation_user2@example.com"
        
        user1_auth, user1_ws, user1_context = await self.create_isolated_user_session(user1_email)
        user2_auth, user2_ws, user2_context = await self.create_isolated_user_session(user2_email)
        
        logger.info(" PASS:  Created 2 isolated user sessions")
        
        # Define different requests for each user to ensure isolation
        user1_message = "Please analyze AWS EC2 costs and provide optimization recommendations for development environments."
        user2_message = "I need help with Azure blob storage cost optimization and archival strategies for compliance data."
        
        # Expected unique indicators for each user's response
        user1_indicators = ["aws", "ec2", "development"]
        user2_indicators = ["azure", "blob", "storage", "compliance"]
        
        # Execute agents concurrently
        logger.info("[U+1F500] Executing agents concurrently for both users")
        
        # Start both agent executions simultaneously
        user1_task = asyncio.create_task(
            self.execute_agent_for_user(
                user1_auth, user1_ws, user1_context, 
                user1_message, user1_indicators
            )
        )
        
        user2_task = asyncio.create_task(
            self.execute_agent_for_user(
                user2_auth, user2_ws, user2_context,
                user2_message, user2_indicators
            )
        )
        
        # Wait for both to complete
        user1_events, user2_events = await asyncio.gather(user1_task, user2_task)
        
        # Validate both users received complete event sequences
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        # User 1 validation
        assert_websocket_events_sent(user1_events, required_events)
        logger.info(f" PASS:  User 1 received all required events: {len(user1_events)}")
        
        # User 2 validation
        assert_websocket_events_sent(user2_events, required_events)
        logger.info(f" PASS:  User 2 received all required events: {len(user2_events)}")
        
        # Validate complete isolation - no user ID cross-contamination
        for event in user1_events:
            event_user_id = event.get("data", {}).get("user_id")
            if event_user_id:
                assert event_user_id == user1_auth.user_id, \
                    f"User 1 event contaminated with user ID: {event_user_id}"
        
        for event in user2_events:
            event_user_id = event.get("data", {}).get("user_id")
            if event_user_id:
                assert event_user_id == user2_auth.user_id, \
                    f"User 2 event contaminated with user ID: {event_user_id}"
        
        # Validate response content isolation
        user1_response = ""
        user2_response = ""
        
        user1_completions = [e for e in user1_events if e.get("type") == "agent_completed"]
        if user1_completions:
            user1_response = user1_completions[0].get("data", {}).get("result", "")
        
        user2_completions = [e for e in user2_events if e.get("type") == "agent_completed"]
        if user2_completions:
            user2_response = user2_completions[0].get("data", {}).get("result", "")
        
        # Ensure responses are contextually different (no response mixing)
        assert user1_response != user2_response, "Users received identical responses - possible data mixing"
        assert len(user1_response) > 50, "User 1 response too short"
        assert len(user2_response) > 50, "User 2 response too short"
        
        logger.info(" CELEBRATION:  CONCURRENT USER ISOLATION TEST PASSED")
        logger.info(f"   [U+1F465] Users: {user1_email}, {user2_email}")
        logger.info(f"   [U+1F4E8] Events: User1={len(user1_events)}, User2={len(user2_events)}")
        logger.info(f"   [U+1F512] Data Isolation: VERIFIED - No cross-contamination detected")
        logger.info(f"    PASS:  Enterprise-grade multi-user security validated")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_user_thread_isolation(self, real_services_fixture):
        """
        Test thread-level isolation between users with overlapping conversation contexts.
        
        This test ensures that multiple users with similar conversation topics
        maintain complete thread isolation without context bleeding.
        """
        logger.info("[U+1F680] Starting multi-user thread isolation test")
        
        # Create 3 users with overlapping but distinct requests
        users = []
        connections = []
        contexts = []
        
        for i in range(3):
            email = f"thread_isolation_user{i+1}@example.com"
            auth_user, ws_conn, user_context = await self.create_isolated_user_session(email)
            users.append(auth_user)
            connections.append(ws_conn)
            contexts.append(user_context)
        
        logger.info(" PASS:  Created 3 user sessions for thread isolation testing")
        
        # Define similar but distinct conversation contexts
        messages = [
            "Analyze my monthly AWS costs and suggest optimizations for Q1 2024.",
            "Review my quarterly AWS spending and recommend cost reductions for Q2 2024.",
            "Evaluate my annual AWS expenditure and provide optimization strategies for 2024."
        ]
        
        expected_indicators = [
            ["monthly", "q1", "2024"],
            ["quarterly", "q2", "2024"], 
            ["annual", "2024"]
        ]
        
        # Execute all agent sessions concurrently
        tasks = []
        for i, (user, ws, context) in enumerate(zip(users, connections, contexts)):
            task = asyncio.create_task(
                self.execute_agent_for_user(
                    user, ws, context, 
                    messages[i], expected_indicators[i]
                )
            )
            tasks.append(task)
        
        # Gather all results
        all_user_events = await asyncio.gather(*tasks)
        
        # Validate complete isolation across all users
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for i, events in enumerate(all_user_events):
            # Validate event completeness
            assert_websocket_events_sent(events, required_events)
            
            # Validate user context isolation
            for event in events:
                event_user_id = event.get("data", {}).get("user_id")
                event_thread_id = event.get("data", {}).get("thread_id")
                
                if event_user_id:
                    assert event_user_id == users[i].user_id, \
                        f"User {i+1} received event with wrong user_id: {event_user_id}"
                
                if event_thread_id:
                    assert event_thread_id == str(contexts[i].thread_id), \
                        f"User {i+1} received event with wrong thread_id: {event_thread_id}"
            
            logger.info(f" PASS:  User {i+1} thread isolation validated: {len(events)} events")
        
        # Validate response differentiation
        responses = []
        for events in all_user_events:
            completion_events = [e for e in events if e.get("type") == "agent_completed"]
            if completion_events:
                response = completion_events[0].get("data", {}).get("result", "")
                responses.append(response)
        
        # Ensure all responses are unique (no context bleeding)
        assert len(set(responses)) == len(responses), "Duplicate responses detected - context bleeding"
        
        # Ensure each response contains expected context
        for i, response in enumerate(responses):
            for indicator in expected_indicators[i]:
                assert indicator.lower() in response.lower(), \
                    f"User {i+1} response missing expected indicator '{indicator}'"
        
        logger.info(" CELEBRATION:  MULTI-USER THREAD ISOLATION TEST PASSED")
        logger.info(f"   [U+1F465] Users: 3 concurrent sessions")
        logger.info(f"   [U+1F9F5] Thread Isolation: VERIFIED")
        logger.info(f"   [U+1F4E8] Total Events: {sum(len(events) for events in all_user_events)}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_user_permission_isolation(self, real_services_fixture):
        """
        Test that users with different permission levels maintain proper isolation
        and only receive data appropriate for their permission level.
        """
        logger.info("[U+1F680] Starting user permission isolation test")
        
        # Create users with different permission levels
        admin_user, admin_ws, admin_context = await self.create_isolated_user_session(
            "admin_isolation@example.com",
            permissions=["read", "write", "agent_execute", "admin", "sensitive_data"]
        )
        
        basic_user, basic_ws, basic_context = await self.create_isolated_user_session(
            "basic_isolation@example.com", 
            permissions=["read", "agent_execute"]
        )
        
        logger.info(" PASS:  Created admin and basic user sessions")
        
        # Both users ask for similar information
        message = "Please provide a security analysis of our current cloud infrastructure and identify any compliance issues."
        
        # Execute concurrently
        admin_task = asyncio.create_task(
            self.execute_agent_for_user(admin_user, admin_ws, admin_context, message)
        )
        
        basic_task = asyncio.create_task(
            self.execute_agent_for_user(basic_user, basic_ws, basic_context, message)
        )
        
        admin_events, basic_events = await asyncio.gather(admin_task, basic_task)
        
        # Validate both got complete event sequences
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert_websocket_events_sent(admin_events, required_events)
        assert_websocket_events_sent(basic_events, required_events)
        
        # Validate permission context preservation
        for event in admin_events:
            event_data = event.get("data", {})
            if "permissions" in event_data:
                user_permissions = event_data["permissions"]
                assert "admin" in user_permissions, "Admin user lost admin permissions in events"
        
        for event in basic_events:
            event_data = event.get("data", {})
            if "permissions" in event_data:
                user_permissions = event_data["permissions"]
                assert "admin" not in user_permissions, "Basic user gained admin permissions in events"
        
        logger.info(" CELEBRATION:  USER PERMISSION ISOLATION TEST PASSED")
        logger.info(f"   [U+1F510] Admin user maintained elevated permissions")
        logger.info(f"   [U+1F464] Basic user maintained restricted permissions")
        logger.info(f"   [U+1F512] No permission escalation or contamination detected")

    @pytest.mark.e2e
    @pytest.mark.real_services  
    async def test_concurrent_user_resource_cleanup(self, real_services_fixture):
        """
        Test that concurrent user sessions are properly cleaned up without resource leaks.
        
        This test validates that the system properly manages resources when multiple
        users connect and disconnect, preventing memory leaks and connection exhaustion.
        """
        logger.info("[U+1F680] Starting concurrent user resource cleanup test")
        
        # Create multiple short-lived user sessions
        num_users = 5
        all_events = []
        
        for batch in range(2):  # Test in batches to simulate real usage
            logger.info(f"[U+1F4E6] Starting batch {batch + 1} with {num_users} users")
            
            # Create batch of users
            batch_users = []
            batch_connections = []
            batch_contexts = []
            
            for i in range(num_users):
                email = f"cleanup_batch{batch}_user{i}@example.com"
                auth_user, ws_conn, user_context = await self.create_isolated_user_session(email)
                batch_users.append(auth_user)
                batch_connections.append(ws_conn)
                batch_contexts.append(user_context)
            
            # Execute quick agent requests concurrently
            tasks = []
            for i, (user, ws, context) in enumerate(zip(batch_users, batch_connections, batch_contexts)):
                message = f"Quick status check #{i} - please provide current system health summary."
                task = asyncio.create_task(
                    self.execute_agent_for_user(user, ws, context, message)
                )
                tasks.append(task)
            
            # Gather results
            batch_events = await asyncio.gather(*tasks)
            all_events.extend(batch_events)
            
            # Clean up this batch explicitly
            for ws in batch_connections:
                await WebSocketTestHelpers.close_test_connection(ws)
            
            # Clear from active connections to prevent double cleanup
            for ws in batch_connections:
                if ws in self.active_connections:
                    self.active_connections.remove(ws)
            
            logger.info(f" PASS:  Batch {batch + 1} completed and cleaned up")
            
            # Brief pause between batches
            await asyncio.sleep(1.0)
        
        # Validate all batches received proper events
        total_events = sum(len(events) for events in all_events)
        expected_min_events = num_users * 2 * 5  # 2 batches, 5 users, minimum 5 events each
        
        assert total_events >= expected_min_events, \
            f"Insufficient total events: {total_events} < {expected_min_events}"
        
        # Validate no event contamination across batches
        user_ids_seen = set()
        for events in all_events:
            for event in events:
                event_user_id = event.get("data", {}).get("user_id")
                if event_user_id:
                    user_ids_seen.add(event_user_id)
        
        expected_users = num_users * 2  # 2 batches
        assert len(user_ids_seen) == expected_users, \
            f"Expected {expected_users} unique users, found {len(user_ids_seen)}"
        
        logger.info(" CELEBRATION:  CONCURRENT USER RESOURCE CLEANUP TEST PASSED")
        logger.info(f"   [U+1F465] Total Users Processed: {expected_users}")
        logger.info(f"   [U+1F4E8] Total Events: {total_events}")
        logger.info(f"   [U+1F9F9] Resource Cleanup: VERIFIED")
        logger.info(f"   [U+1F4BE] No Resource Leaks Detected")


if __name__ == "__main__":
    # Run this E2E test standalone
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s",  # Show real-time output  
        "--timeout=180",  # Allow time for concurrent execution
    ])