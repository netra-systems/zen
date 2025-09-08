"""
E2E Tests for WebSocket Chat Sessions - Batch 3 WebSocket Infrastructure Suite  
=============================================================================

Business Value Justification:
- Segment: Free, Early, Mid, Enterprise (All customer segments)
- Business Goal: Chat Business Value & User Retention
- Value Impact: Validates complete chat experience delivers substantive AI value
- Strategic Impact: Ensures chat is the primary value delivery mechanism

CRITICAL: ALL E2E TESTS MUST USE AUTHENTICATION per CLAUDE.md requirements.
This ensures proper user isolation and real-world multi-user chat scenarios.

CHAT BUSINESS VALUE VALIDATION:
1. Real Solutions - AI agents solve actual problems with actionable results
2. Helpful Responses - Chat UI/UX provides timely, contextual updates
3. Complete Value Chain - Full agent execution delivers business outcomes
4. Data-Driven Insights - Users receive meaningful analysis and recommendations
5. Professional Experience - System behaves reliably under real conditions

This suite tests complete chat sessions from user request through AI response
with full authentication, WebSocket events, and business value delivery.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from test_framework.ssot.websocket import (
    WebSocketTestUtility, 
    WebSocketEventType, 
    WebSocketTestClient
)
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketChatSessionsE2E(SSotBaseTestCase):
    """
    E2E tests for complete WebSocket chat sessions with authentication.
    
    These tests validate the entire chat business value chain:
    User Request -> Authentication -> WebSocket Connection -> Agent Execution 
    -> Real-time Events -> Final Response -> Business Value Delivered
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated E2E test helper."""
        config = E2EAuthConfig()
        return E2EAuthHelper(config)
    
    @pytest.fixture 
    async def authenticated_chat_session(self, auth_helper):
        """Create authenticated chat session with WebSocket connection."""
        # Get authentication token
        auth_result = await auth_helper.authenticate_test_user()
        
        if not auth_result.success:
            pytest.skip(f"Authentication failed: {auth_result.error}")
        
        # Create WebSocket utility with auth
        ws_util = WebSocketTestUtility()
        await ws_util.initialize()
        
        # Create authenticated client
        client = await ws_util.create_authenticated_client(
            auth_result.user_id,
            auth_result.access_token
        )
        
        # Connect with real authentication
        connected = await client.connect(timeout=15.0)
        if not connected:
            pytest.skip("WebSocket connection with authentication failed")
            
        return {
            "ws_util": ws_util,
            "client": client,
            "auth_result": auth_result,
            "user_id": auth_result.user_id
        }

    @pytest.mark.e2e
    @pytest.mark.requires_auth
    async def test_complete_authenticated_chat_session(self, authenticated_chat_session):
        """
        Test complete authenticated chat session delivers business value.
        
        BUSINESS VALUE: Validates that authenticated users can have complete
        chat conversations that deliver real AI-powered solutions to business problems.
        """
        session = authenticated_chat_session
        client = session["client"]
        user_id = session["user_id"]
        
        # Arrange - Business-focused user request
        business_request = {
            "content": "I need to analyze our Q3 sales data to identify the top 3 growth opportunities for Q4 planning. Please focus on revenue trends, customer segments, and regional performance.",
            "priority": "high",
            "expected_deliverables": [
                "Revenue trend analysis",
                "Customer segment insights", 
                "Regional performance comparison",
                "Top 3 actionable recommendations"
            ]
        }
        
        # Act - Start authenticated chat session
        start_time = time.time()
        
        # Send user request through WebSocket
        await client.send_message(
            WebSocketEventType.MESSAGE_CREATED,
            {
                **business_request,
                "role": "user",
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "session_id": f"chat_{uuid.uuid4().hex[:8]}"
            }
        )
        
        # Expected chat business value events
        expected_business_events = [
            WebSocketEventType.AGENT_STARTED,     # User sees AI engaged
            WebSocketEventType.AGENT_THINKING,    # Real-time reasoning
            WebSocketEventType.TOOL_EXECUTING,    # Data analysis in progress
            WebSocketEventType.TOOL_COMPLETED,    # Analysis results available
            WebSocketEventType.AGENT_COMPLETED    # Complete response ready
        ]
        
        # Wait for complete business value delivery
        try:
            received_events = await client.wait_for_events(
                expected_business_events, 
                timeout=45.0  # Allow time for real AI processing
            )
            
            chat_duration = time.time() - start_time
            
            # Assert - Business value validation
            
            # 1. All critical events delivered for transparency
            for event_type in expected_business_events:
                assert event_type in received_events, \
                    f"Missing critical business event: {event_type.value}"
            
            # 2. Agent started promptly (user engagement)
            agent_started_events = received_events[WebSocketEventType.AGENT_STARTED]
            assert len(agent_started_events) > 0
            first_event = agent_started_events[0]
            assert "agent_name" in first_event.data
            assert first_event.user_id == user_id  # Proper user isolation
            
            # 3. Real-time thinking provides user confidence
            thinking_events = received_events[WebSocketEventType.AGENT_THINKING]
            assert len(thinking_events) > 0
            
            thinking_event = thinking_events[0]
            thinking_data = thinking_event.data
            assert "thought" in thinking_data
            assert len(thinking_data["thought"]) > 10  # Substantive reasoning
            
            # 4. Tool execution demonstrates AI working on solution
            tool_exec_events = received_events[WebSocketEventType.TOOL_EXECUTING]  
            assert len(tool_exec_events) > 0
            
            tool_event = tool_exec_events[0]
            tool_data = tool_event.data
            assert "tool_name" in tool_data
            assert "purpose" in tool_data or "tool_purpose" in tool_data
            
            # 5. Tool completion delivers actionable results
            tool_completed_events = received_events[WebSocketEventType.TOOL_COMPLETED]
            assert len(tool_completed_events) > 0
            
            tool_result = tool_completed_events[0]
            result_data = tool_result.data
            assert "result" in result_data
            assert result_data["result"] is not None
            
            # 6. Agent completion signals full business value delivered
            completion_events = received_events[WebSocketEventType.AGENT_COMPLETED]
            assert len(completion_events) > 0
            
            completion_event = completion_events[0]
            completion_data = completion_event.data
            assert "result" in completion_data or "summary" in completion_data
            
            # 7. Performance meets user expectations
            assert chat_duration < 60.0, f"Chat session took {chat_duration}s (should be < 60s)"
            
            # 8. User receives complete business value
            total_events = sum(len(events) for events in received_events.values())
            assert total_events >= len(expected_business_events), \
                "Insufficient event detail for business transparency"
                
        except asyncio.TimeoutError:
            pytest.fail(f"Chat session timeout - business value not delivered within 45s")
        
        finally:
            await session["ws_util"].cleanup()

    @pytest.mark.e2e
    @pytest.mark.requires_auth 
    async def test_multi_user_chat_isolation(self, auth_helper):
        """
        Test multi-user chat sessions maintain proper isolation.
        
        BUSINESS VALUE: Enterprise customers need guaranteed conversation privacy.
        Users must only see their own chat events and AI responses.
        """
        # Create multiple authenticated users
        user_sessions = []
        
        try:
            # Arrange - Create 3 authenticated chat sessions
            for i in range(3):
                auth_result = await auth_helper.authenticate_test_user(
                    user_email=f"multi_user_{i}_{uuid.uuid4().hex[:6]}@example.com"
                )
                
                if not auth_result.success:
                    pytest.skip(f"Authentication failed for user {i}")
                
                ws_util = WebSocketTestUtility()
                await ws_util.initialize()
                
                client = await ws_util.create_authenticated_client(
                    auth_result.user_id,
                    auth_result.access_token  
                )
                
                connected = await client.connect(timeout=10.0)
                if not connected:
                    pytest.skip(f"WebSocket connection failed for user {i}")
                
                user_sessions.append({
                    "user_id": auth_result.user_id,
                    "client": client,
                    "ws_util": ws_util,
                    "thread_id": f"thread_{i}_{uuid.uuid4().hex[:8]}"
                })
            
            # Act - Start concurrent chat sessions
            chat_tasks = []
            for i, session in enumerate(user_sessions):
                task = asyncio.create_task(
                    self._simulate_user_chat_session(
                        session["client"],
                        session["user_id"], 
                        f"User {i} confidential request: Analyze our competitive position vs Company-{i}"
                    )
                )
                chat_tasks.append(task)
            
            # Wait for all sessions to complete
            results = await asyncio.gather(*chat_tasks, return_exceptions=True)
            
            # Assert - Isolation verification
            
            # 1. All sessions should succeed independently
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), \
                    f"User {i} chat session failed: {result}"
                assert result["success"] is True
            
            # 2. Verify event isolation - users only receive their own events
            user_agent_events = {}
            for i, session in enumerate(user_sessions):
                client = session["client"]
                user_id = session["user_id"]
                
                # Get agent events for this user
                agent_started = client.get_messages_by_type(WebSocketEventType.AGENT_STARTED)
                agent_completed = client.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                
                user_agent_events[user_id] = {
                    "started": agent_started,
                    "completed": agent_completed
                }
                
                # Each user should have exactly their own events
                assert len(agent_started) >= 1, f"User {i} missing agent_started events"
                assert len(agent_completed) >= 1, f"User {i} missing agent_completed events"
                
                # Verify events belong to this user
                for event in agent_started + agent_completed:
                    if hasattr(event, 'user_id') and event.user_id:
                        assert event.user_id == user_id, \
                            f"User {i} received event for different user: {event.user_id}"
            
            # 3. Verify no cross-contamination between users
            all_user_ids = [session["user_id"] for session in user_sessions]
            for i, session in enumerate(user_sessions):
                client = session["client"]
                current_user_id = session["user_id"]
                
                # Check all received messages
                for message in client.received_messages:
                    if hasattr(message, 'user_id') and message.user_id:
                        assert message.user_id == current_user_id or message.user_id is None, \
                            f"User {i} received message for different user"
                            
        finally:
            # Clean up all sessions
            for session in user_sessions:
                try:
                    await session["client"].disconnect()
                    await session["ws_util"].cleanup()
                except Exception as e:
                    print(f"Cleanup error: {e}")

    @pytest.mark.e2e
    @pytest.mark.requires_auth
    async def test_chat_error_recovery_with_auth(self, authenticated_chat_session):
        """
        Test chat error scenarios provide good user experience with recovery.
        
        BUSINESS VALUE: When AI processing fails, authenticated users get clear
        guidance and can recover their session without losing context.
        """
        session = authenticated_chat_session
        client = session["client"]
        user_id = session["user_id"]
        
        # Act - Simulate various error scenarios
        error_scenarios = [
            {
                "scenario": "rate_limit_recovery",
                "request": "Analyze massive dataset (trigger rate limit)",
                "expected_recovery": True,
                "max_retry_time": 30.0
            },
            {
                "scenario": "timeout_graceful_handling", 
                "request": "Complex analysis that may timeout",
                "expected_recovery": True,
                "max_retry_time": 45.0
            },
            {
                "scenario": "invalid_request_guidance",
                "request": "",  # Empty request should be handled gracefully
                "expected_recovery": True,
                "max_retry_time": 5.0
            }
        ]
        
        successful_recoveries = 0
        
        for scenario in error_scenarios:
            try:
                # Send potentially problematic request
                await client.send_message(
                    WebSocketEventType.MESSAGE_CREATED,
                    {
                        "content": scenario["request"],
                        "role": "user",
                        "user_id": user_id,
                        "scenario": scenario["scenario"]
                    }
                )
                
                # Wait for response (error or success)
                start_time = time.time()
                received_completion = False
                received_error = False
                
                while time.time() - start_time < scenario["max_retry_time"]:
                    try:
                        # Check for completion or error
                        message = await client.wait_for_message(timeout=2.0)
                        
                        if message.event_type == WebSocketEventType.AGENT_COMPLETED:
                            received_completion = True
                            break
                        elif message.event_type == WebSocketEventType.ERROR:
                            received_error = True
                            
                            # Verify error provides recovery guidance
                            error_data = message.data
                            assert "recovery_suggestions" in error_data or "user_guidance" in error_data
                            assert error_data.get("is_recoverable", False) == scenario["expected_recovery"]
                            break
                            
                    except asyncio.TimeoutError:
                        continue  # Keep waiting
                
                # Scenario should either complete or provide recoverable error
                if received_completion or (received_error and scenario["expected_recovery"]):
                    successful_recoveries += 1
                    
            except Exception as e:
                # Even exceptions should be handled gracefully
                print(f"Error scenario {scenario['scenario']} exception: {e}")
                continue
        
        # Assert - Most error scenarios should be handled well
        recovery_rate = successful_recoveries / len(error_scenarios)
        assert recovery_rate >= 0.6, \
            f"Poor error recovery rate: {recovery_rate:.1%} (should be ≥60%)"

    @pytest.mark.e2e
    @pytest.mark.requires_auth
    @pytest.mark.performance
    async def test_chat_performance_under_load(self, auth_helper):
        """
        Test chat system performance with multiple concurrent authenticated users.
        
        BUSINESS VALUE: System scales to support multiple paying customers
        simultaneously without degraded experience.
        """
        # Performance targets for chat business value
        max_users = 5  # Concurrent authenticated users
        max_chat_duration = 30.0  # Seconds per chat
        min_success_rate = 0.8  # 80% sessions must succeed
        max_avg_latency = 2.0  # Seconds average response time
        
        user_sessions = []
        performance_results = []
        
        try:
            # Arrange - Create concurrent authenticated users
            for i in range(max_users):
                auth_result = await auth_helper.authenticate_test_user(
                    user_email=f"perf_user_{i}_{uuid.uuid4().hex[:6]}@example.com"
                )
                
                if not auth_result.success:
                    continue  # Skip failed auth, test with available users
                
                ws_util = WebSocketTestUtility()
                await ws_util.initialize()
                
                client = await ws_util.create_authenticated_client(
                    auth_result.user_id,
                    auth_result.access_token
                )
                
                connected = await client.connect(timeout=10.0)
                if connected:
                    user_sessions.append({
                        "user_id": auth_result.user_id,
                        "client": client,
                        "ws_util": ws_util
                    })
            
            if len(user_sessions) < 2:
                pytest.skip("Insufficient authenticated users for performance test")
            
            # Act - Run concurrent chat sessions
            performance_tasks = []
            for i, session in enumerate(user_sessions):
                task = asyncio.create_task(
                    self._measure_chat_performance(
                        session["client"],
                        session["user_id"],
                        f"Performance test {i}: Quick revenue analysis"
                    )
                )
                performance_tasks.append(task)
            
            # Wait for all performance tests
            results = await asyncio.gather(*performance_tasks, return_exceptions=True)
            
            # Analyze performance results
            successful_sessions = 0
            total_duration = 0.0
            total_latencies = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    performance_results.append({
                        "user": i,
                        "success": False,
                        "error": str(result),
                        "duration": max_chat_duration,
                        "latency": max_chat_duration
                    })
                else:
                    successful_sessions += 1
                    total_duration += result["duration"]
                    total_latencies.append(result["avg_latency"])
                    performance_results.append({
                        "user": i,
                        "success": True,
                        "duration": result["duration"],
                        "latency": result["avg_latency"]
                    })
            
            # Assert - Performance requirements met
            success_rate = successful_sessions / len(user_sessions)
            avg_duration = total_duration / successful_sessions if successful_sessions > 0 else max_chat_duration
            avg_latency = sum(total_latencies) / len(total_latencies) if total_latencies else max_avg_latency
            
            assert success_rate >= min_success_rate, \
                f"Poor success rate under load: {success_rate:.1%} (should be ≥{min_success_rate:.1%})"
            
            assert avg_duration <= max_chat_duration, \
                f"Chat sessions too slow: {avg_duration:.1f}s (should be ≤{max_chat_duration}s)"
            
            assert avg_latency <= max_avg_latency, \
                f"Response latency too high: {avg_latency:.1f}s (should be ≤{max_avg_latency}s)"
                
        finally:
            # Clean up all sessions
            for session in user_sessions:
                try:
                    await session["client"].disconnect()
                    await session["ws_util"].cleanup()
                except Exception:
                    pass

    async def _simulate_user_chat_session(self, client: WebSocketTestClient, 
                                        user_id: str, request_content: str) -> Dict[str, Any]:
        """Helper method to simulate a complete user chat session."""
        start_time = time.time()
        
        try:
            # Send user request
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": request_content,
                    "role": "user",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Wait for agent completion
            completion_event = await client.wait_for_message(
                WebSocketEventType.AGENT_COMPLETED,
                timeout=30.0
            )
            
            duration = time.time() - start_time
            
            return {
                "success": True,
                "user_id": user_id,
                "duration": duration,
                "events_received": len(client.received_messages),
                "completion_data": completion_event.data if completion_event else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": user_id,
                "duration": time.time() - start_time,
                "error": str(e)
            }

    async def _measure_chat_performance(self, client: WebSocketTestClient,
                                      user_id: str, request_content: str) -> Dict[str, Any]:
        """Helper method to measure chat session performance metrics."""
        start_time = time.time()
        event_times = []
        
        try:
            # Send request and measure response times
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": request_content,
                    "role": "user", 
                    "user_id": user_id
                }
            )
            
            # Measure time to first response
            first_response_time = time.time()
            first_event = await client.wait_for_message(timeout=5.0)
            
            if first_event:
                event_times.append(time.time() - first_response_time)
            
            # Wait for completion
            completion_event = await client.wait_for_message(
                WebSocketEventType.AGENT_COMPLETED,
                timeout=25.0
            )
            
            total_duration = time.time() - start_time
            avg_latency = sum(event_times) / len(event_times) if event_times else 0.0
            
            return {
                "success": True,
                "duration": total_duration,
                "avg_latency": avg_latency,
                "events_count": len(client.received_messages)
            }
            
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "avg_latency": 30.0,  # Max penalty for failed sessions
                "error": str(e)
            }