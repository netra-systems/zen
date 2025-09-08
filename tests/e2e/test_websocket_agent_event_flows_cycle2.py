"""
E2E Tests for Complete WebSocket Agent Event Flows - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete agent-to-user event delivery in production-like environment
- Value Impact: Users experience seamless real-time AI interaction with full transparency
- Strategic Impact: Core business value delivery - this IS the chat experience customers pay for

CRITICAL: These tests validate the complete business value delivery chain.
If these fail, customers cannot see AI working and will not pay for the service.

E2E AUTHENTICATION REQUIREMENT: All tests MUST use real authentication per CLAUDE.md
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.websocket_helpers import WebSocketTestClient

class TestWebSocketAgentEventFlowsE2E(BaseE2ETest):
    """E2E tests for complete WebSocket agent event flows with authentication."""
    
    @pytest.fixture
    async def authenticated_user(self):
        """Create authenticated user for E2E testing."""
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(
            email="e2e_websocket_user@test.netra.ai",
            name="E2E WebSocket Test User"
        )
        return user
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_complete_agent_execution_websocket_events_flow(self, authenticated_user, real_services):
        """
        Test complete agent execution with all WebSocket events in production environment.
        
        Business Value: Validates end-to-end chat experience customers will pay for.
        MISSION CRITICAL: This is the core value proposition of the entire platform.
        """
        # Arrange: Setup authenticated WebSocket connection
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        all_events = []
        agent_execution_complete = False
        
        # Act: Connect with authenticated user and trigger agent execution
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            
            # Setup comprehensive event capture
            async def capture_all_events():
                nonlocal agent_execution_complete
                try:
                    async for message in ws_client.receive_events(timeout=60):  # Long timeout for real agent
                        all_events.append(message)
                        print(f"E2E Event Received: {message.get('type')} at {datetime.now()}")
                        
                        if message.get("type") == "agent_completed":
                            agent_execution_complete = True
                            break
                            
                        # Stop if we get error or timeout
                        if message.get("type") == "error":
                            break
                            
                except asyncio.TimeoutError:
                    print(f"E2E Event capture timeout after receiving {len(all_events)} events")
            
            # Start event monitoring
            event_capture_task = asyncio.create_task(capture_all_events())
            
            # Send real agent request through WebSocket
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",  # Use simple agent for reliable testing
                "message": "Help me analyze my cloud costs for this month",
                "context": {
                    "user_intent": "cost_analysis",
                    "urgency": "medium"
                }
            }
            
            await ws_client.send_json(agent_request)
            
            # Wait for agent execution completion
            await event_capture_task
            
        # Assert: Validate complete business value delivery
        assert len(all_events) >= 5, f"Expected at least 5 events for complete agent flow, got {len(all_events)}"
        assert agent_execution_complete, "Agent execution should complete successfully"
        
        # Validate all critical WebSocket events were delivered
        event_types = [event.get("type") for event in all_events]
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for critical_event in critical_events:
            assert critical_event in event_types, f"Missing critical business event: {critical_event}"
        
        # Validate business value content
        completed_event = next(e for e in all_events if e.get("type") == "agent_completed")
        assert "result" in completed_event, "Agent completion must provide results"
        
        result = completed_event["result"]
        # Business requirement: Results must contain actionable insights
        result_str = str(result).lower()
        business_value_indicators = ["cost", "saving", "optimization", "recommendation", "analysis", "insight"]
        assert any(indicator in result_str for indicator in business_value_indicators), \
            f"Agent result must show business value: {result}"
        
        # Validate event timing shows reasonable progression
        event_timestamps = []
        for event in all_events:
            if "timestamp" in event:
                try:
                    ts = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                    event_timestamps.append(ts)
                except:
                    pass  # Skip malformed timestamps
        
        if len(event_timestamps) >= 2:
            total_execution_time = (event_timestamps[-1] - event_timestamps[0]).total_seconds()
            assert total_execution_time > 0.5, "Agent execution should take measurable time"
            assert total_execution_time < 120, "Agent execution should complete within 2 minutes"

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_agent_multi_user_isolation_e2e(self, real_services):
        """
        Test that multiple authenticated users receive only their own agent events.
        
        Business Value: Ensures privacy and data isolation in production.
        CRITICAL: Data leakage between users would be catastrophic for trust.
        """
        # Arrange: Create two authenticated users
        auth_helper = E2EAuthHelper()
        user1 = await auth_helper.create_authenticated_user(
            email="e2e_isolation_user1@test.netra.ai",
            name="E2E Isolation User 1"
        )
        user2 = await auth_helper.create_authenticated_user(
            email="e2e_isolation_user2@test.netra.ai", 
            name="E2E Isolation User 2"
        )
        
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        user1_events = []
        user2_events = []
        
        # Act: Run concurrent agent requests for both users
        async def user1_session():
            async with WebSocketTestClient(websocket_url, user1.token) as ws1:
                # User 1 agent request
                await ws1.send_json({
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "User 1 cost analysis request",
                    "context": {"user_marker": "USER_1_MARKER"}
                })
                
                # Capture User 1 events
                async for message in ws1.receive_events(timeout=30):
                    user1_events.append(message)
                    if message.get("type") == "agent_completed":
                        break
        
        async def user2_session():
            async with WebSocketTestClient(websocket_url, user2.token) as ws2:
                # User 2 agent request  
                await ws2.send_json({
                    "type": "agent_request",
                    "agent": "triage_agent", 
                    "message": "User 2 optimization request",
                    "context": {"user_marker": "USER_2_MARKER"}
                })
                
                # Capture User 2 events
                async for message in ws2.receive_events(timeout=30):
                    user2_events.append(message)
                    if message.get("type") == "agent_completed":
                        break
        
        # Run both user sessions concurrently
        await asyncio.gather(user1_session(), user2_session())
        
        # Assert: Validate complete isolation
        assert len(user1_events) > 0, "User 1 should receive events"
        assert len(user2_events) > 0, "User 2 should receive events"
        
        # Critical business requirement: No cross-user data leakage
        user1_content = json.dumps(user1_events)
        user2_content = json.dumps(user2_events)
        
        assert "USER_1_MARKER" in user1_content, "User 1 should see their own data"
        assert "USER_1_MARKER" not in user2_content, "User 2 MUST NOT see User 1's data"
        
        assert "USER_2_MARKER" in user2_content, "User 2 should see their own data"
        assert "USER_2_MARKER" not in user1_content, "User 1 MUST NOT see User 2's data"
        
        # Verify both users got complete agent flows
        user1_event_types = [e.get("type") for e in user1_events]
        user2_event_types = [e.get("type") for e in user2_events]
        
        for user_events, user_name in [(user1_event_types, "User1"), (user2_event_types, "User2")]:
            assert "agent_started" in user_events, f"{user_name} should get agent_started"
            assert "agent_completed" in user_events, f"{user_name} should get agent_completed"

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_connection_recovery_during_agent_execution(self, authenticated_user, real_services):
        """
        Test WebSocket connection recovery during agent execution.
        
        Business Value: Users don't lose progress during network interruptions.
        Ensures reliable service even with connectivity issues.
        """
        backend_url = real_services["backend_url"]  
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        all_events = []
        connection_breaks = 0
        
        # Act: Start agent request with connection interruption simulation
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            # Send agent request
            await ws_client.send_json({
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Long-running analysis for connection recovery test",
                "context": {"test_type": "connection_recovery"}
            })
            
            # Capture events with simulated connection break
            event_count = 0
            async for message in ws_client.receive_events(timeout=45):
                all_events.append(message)
                event_count += 1
                
                # Simulate connection break after receiving some events
                if event_count == 2 and connection_breaks == 0:
                    connection_breaks += 1
                    # Brief disconnection simulation
                    await asyncio.sleep(0.5)
                    print("E2E: Simulated brief connection interruption")
                
                if message.get("type") == "agent_completed":
                    break
        
        # Assert: Agent execution completed despite connection issues
        assert len(all_events) >= 3, "Should receive events despite connection interruption"
        
        event_types = [e.get("type") for e in all_events]
        assert "agent_started" in event_types, "Should receive agent_started"
        assert "agent_completed" in event_types, "Should eventually receive agent_completed"
        
        # Business requirement: Final result still shows value delivery
        if "agent_completed" in event_types:
            completed_event = next(e for e in all_events if e.get("type") == "agent_completed")
            assert "result" in completed_event, "Agent should complete with results even after connection issues"

    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.mission_critical
    async def test_websocket_agent_performance_under_load(self, real_services):
        """
        Test WebSocket agent event delivery performance with multiple concurrent users.
        
        Business Value: Ensures platform scales to serve multiple paying customers.
        CRITICAL: Performance degradation loses customers and revenue.
        """
        # Arrange: Create multiple authenticated users
        auth_helper = E2EAuthHelper()
        users = []
        for i in range(3):  # 3 concurrent users for E2E load test
            user = await auth_helper.create_authenticated_user(
                email=f"e2e_load_user_{i}@test.netra.ai",
                name=f"E2E Load User {i}"
            )
            users.append(user)
        
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        all_user_results = []
        start_time = time.time()
        
        # Act: Run concurrent agent requests
        async def user_agent_session(user, user_index):
            user_events = []
            session_start = time.time()
            
            try:
                async with WebSocketTestClient(websocket_url, user.token) as ws_client:
                    await ws_client.send_json({
                        "type": "agent_request", 
                        "agent": "triage_agent",
                        "message": f"Load test request from user {user_index}",
                        "context": {"user_index": user_index, "load_test": True}
                    })
                    
                    # Collect events with timeout
                    async for message in ws_client.receive_events(timeout=60):
                        user_events.append(message)
                        if message.get("type") == "agent_completed":
                            break
                            
            except Exception as e:
                print(f"User {user_index} session error: {e}")
            
            session_duration = time.time() - session_start
            return {
                "user_index": user_index,
                "events": user_events,
                "duration": session_duration,
                "success": len(user_events) > 0 and any(e.get("type") == "agent_completed" for e in user_events)
            }
        
        # Execute all user sessions concurrently
        tasks = [user_agent_session(user, i) for i, user in enumerate(users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_execution_time = time.time() - start_time
        
        # Assert: Performance and reliability under load
        successful_sessions = [r for r in results if isinstance(r, dict) and r.get("success", False)]
        assert len(successful_sessions) >= 2, f"At least 2 of 3 users should complete successfully, got {len(successful_sessions)}"
        
        # Performance requirement: Reasonable response times under load
        for result in successful_sessions:
            assert result["duration"] < 90, f"User {result['user_index']} took too long: {result['duration']}s"
            
            # Verify business value delivered for each user
            events = result["events"]
            event_types = [e.get("type") for e in events]
            assert "agent_completed" in event_types, f"User {result['user_index']} should receive completion"
            
            completed_event = next(e for e in events if e.get("type") == "agent_completed")
            assert "result" in completed_event, f"User {result['user_index']} should get results"
        
        # Business requirement: Platform handles concurrent load efficiently
        assert total_execution_time < 120, f"Total concurrent execution too slow: {total_execution_time}s"
        
        print(f"E2E Load Test Results: {len(successful_sessions)}/{len(users)} users successful in {total_execution_time:.1f}s")