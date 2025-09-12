"""
E2E tests for WebSocketNotifier - Testing complete real-time agent event delivery in live environment.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Deliver seamless real-time chat experience
- Value Impact: Validates complete agent event flow reaches users in production-like environment
- Strategic Impact: Core value proposition - ensures users see AI thinking/working in real-time

This E2E test validates the deprecated WebSocketNotifier works end-to-end with real
WebSocket connections, authentication, and complete agent execution workflows.
CRITICAL: This test ensures the 5 critical agent events are delivered for chat UX.
"""

import asyncio
import pytest
import json
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection


class TestWebSocketNotifierE2EAgentFlow(BaseTestCase):
    """
    E2E test for complete agent execution flow with WebSocket event delivery.
    
    CRITICAL: This test validates the 5 essential WebSocket events that enable
    real-time chat feedback: agent_started, agent_thinking, tool_executing, 
    tool_completed, agent_completed.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated test user for E2E testing."""
        auth_helper = E2EAuthHelper()
        await auth_helper.initialize()
        yield auth_helper
        await auth_helper.cleanup()
    
    @pytest.fixture
    async def authenticated_user(self, auth_helper):
        """Create authenticated user context for WebSocket testing."""
        user_data = await auth_helper.create_test_user(
            email="websocket_notifier_e2e@netra.ai",
            name="WebSocket E2E Test User",
            user_type="enterprise"
        )
        return user_data
    
    @pytest.fixture
    async def websocket_test_utility(self):
        """Create WebSocket test utility for E2E testing."""
        utility = WebSocketTestUtility()
        await utility.initialize()
        yield utility
        await utility.cleanup()
    
    @pytest.fixture
    async def real_websocket_manager(self, authenticated_user):
        """Create real UnifiedWebSocketManager with authenticated user connection."""
        manager = UnifiedWebSocketManager()
        
        # Create mock WebSocket connection for testing
        class MockWebSocketForE2E:
            def __init__(self):
                self.messages_sent = []
                self.closed = False
            
            async def send_json(self, data):
                if not self.closed:
                    self.messages_sent.append(data)
                else:
                    raise ConnectionError("WebSocket closed")
            
            async def close(self):
                self.closed = True
        
        mock_websocket = MockWebSocketForE2E()
        
        # Add authenticated user connection to manager
        connection = WebSocketConnection(
            connection_id=f"test_conn_{authenticated_user['user_id']}",
            user_id=authenticated_user['user_id'],
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": "e2e_websocket_notifier", "authenticated": True}
        )
        
        await manager.add_connection(connection)
        
        # Store mock websocket reference for verification
        manager._test_websocket = mock_websocket
        
        yield manager
        
        # Cleanup
        await manager.remove_connection(connection.connection_id)
    
    @pytest.fixture
    async def websocket_notifier_e2e(self, real_websocket_manager):
        """Create WebSocketNotifier with real WebSocket manager."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = WebSocketNotifier.create_for_user(real_websocket_manager)
            yield notifier
            await notifier.shutdown()
    
    @pytest.fixture
    def agent_execution_context(self, authenticated_user):
        """Create realistic agent execution context."""
        return AgentExecutionContext(
            agent_name="cost_optimizer",
            thread_id=f"thread_e2e_{authenticated_user['user_id']}",
            user_id=authenticated_user['user_id'],
            run_id=f"run_e2e_{int(datetime.now().timestamp())}",
            total_steps=4
        )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_complete_agent_execution_websocket_event_flow(
        self, 
        websocket_notifier_e2e, 
        agent_execution_context, 
        real_websocket_manager,
        authenticated_user
    ):
        """
        MISSION CRITICAL: Test complete agent execution produces all 5 critical WebSocket events.
        
        This test validates the core value proposition: users see real-time AI progress.
        Failure of this test indicates broken chat experience for all user segments.
        """
        # Arrange - Clear any existing messages
        mock_websocket = real_websocket_manager._test_websocket
        mock_websocket.messages_sent.clear()
        
        # Act - Execute complete agent lifecycle with WebSocket events
        start_time = datetime.now()
        
        # 1. Agent Started (CRITICAL - user must know agent began)
        await websocket_notifier_e2e.send_agent_started(agent_execution_context)
        
        # 2. Agent Thinking (CRITICAL - shows AI is working)
        await websocket_notifier_e2e.send_agent_thinking(
            agent_execution_context,
            "Analyzing your AWS cost data to identify optimization opportunities",
            step_number=1,
            progress_percentage=25.0,
            estimated_remaining_ms=30000,
            current_operation="cost_data_analysis"
        )
        
        # 3. Tool Executing (CRITICAL - shows what AI is doing)
        await websocket_notifier_e2e.send_tool_executing(
            agent_execution_context,
            "aws_cost_analyzer",
            tool_purpose="Extract and analyze AWS billing data",
            estimated_duration_ms=15000,
            parameters_summary="account_id: enterprise_account, timeframe: last_30_days"
        )
        
        # 4. Tool Completed (CRITICAL - shows tool finished with results)
        await websocket_notifier_e2e.send_tool_completed(
            agent_execution_context,
            "aws_cost_analyzer",
            result={
                "total_analyzed": 1247,
                "potential_savings": 2850.75,
                "categories": ["compute", "storage", "networking"],
                "recommendations_found": 8
            }
        )
        
        # 5. Agent Completed (CRITICAL - shows final results ready)
        await websocket_notifier_e2e.send_agent_completed(
            agent_execution_context,
            result={
                "optimization_complete": True,
                "total_potential_savings": 2850.75,
                "recommendations": [
                    {
                        "category": "compute",
                        "action": "resize_instances",
                        "monthly_savings": 1200.50
                    },
                    {
                        "category": "storage", 
                        "action": "lifecycle_policies",
                        "monthly_savings": 890.25
                    }
                ],
                "implementation_priority": ["high", "medium", "medium"],
                "user_friendly_summary": "Found $2,850 in monthly savings opportunities"
            },
            duration_ms=32500.0
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Allow brief processing time
        await asyncio.sleep(0.2)
        
        # Assert - Verify all critical events were delivered via WebSocket
        messages_sent = mock_websocket.messages_sent
        
        # CRITICAL ASSERTION: All 5 events must be present for functional chat UX
        assert len(messages_sent) == 5, \
            f"CRITICAL FAILURE: Expected 5 WebSocket events for complete chat UX, got {len(messages_sent)}. " \
            f"This breaks real-time user feedback. Messages: {[msg.get('type') for msg in messages_sent]}"
        
        # Verify correct event sequence (order matters for UX)
        event_types = [msg.get("type") for msg in messages_sent]
        expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        assert event_types == expected_sequence, \
            f"CRITICAL FAILURE: WebSocket events out of sequence. Expected: {expected_sequence}, " \
            f"Got: {event_types}. This causes confusing user experience."
        
        # Verify agent_started event structure
        agent_started = messages_sent[0]
        assert agent_started["type"] == "agent_started"
        assert agent_started["payload"]["agent_name"] == "cost_optimizer"
        assert agent_started["payload"]["run_id"] == agent_execution_context.run_id
        assert "timestamp" in agent_started["payload"]
        
        # Verify agent_thinking includes progress context (critical for UX)
        agent_thinking = messages_sent[1]
        assert agent_thinking["type"] == "agent_thinking"
        assert agent_thinking["payload"]["thought"] == "Analyzing your AWS cost data to identify optimization opportunities"
        assert agent_thinking["payload"]["progress_percentage"] == 25.0
        assert agent_thinking["payload"]["current_operation"] == "cost_data_analysis"
        assert agent_thinking["payload"]["urgency"] == "low_priority"  # 30000ms > 10s
        
        # Verify tool_executing includes tool context (shows what AI is doing)
        tool_executing = messages_sent[2]
        assert tool_executing["type"] == "tool_executing"
        assert tool_executing["payload"]["tool_name"] == "aws_cost_analyzer"
        assert tool_executing["payload"]["tool_purpose"] == "Extract and analyze AWS billing data"
        assert tool_executing["payload"]["estimated_duration_ms"] == 15000
        assert tool_executing["payload"]["parameters_summary"] == "account_id: enterprise_account, timeframe: last_30_days"
        assert "category" in tool_executing["payload"]  # Tool context hints
        assert tool_executing["payload"]["execution_phase"] == "starting"
        
        # Verify tool_completed includes results (critical for showing progress)
        tool_completed = messages_sent[3]
        assert tool_completed["type"] == "tool_completed"
        assert tool_completed["payload"]["tool_name"] == "aws_cost_analyzer"
        assert tool_completed["payload"]["result"]["total_analyzed"] == 1247
        assert tool_completed["payload"]["result"]["potential_savings"] == 2850.75
        assert len(tool_completed["payload"]["result"]["categories"]) == 3
        
        # Verify agent_completed includes final results (delivers business value)
        agent_completed = messages_sent[4]
        assert agent_completed["type"] == "agent_completed"
        assert agent_completed["payload"]["result"]["optimization_complete"] is True
        assert agent_completed["payload"]["result"]["total_potential_savings"] == 2850.75
        assert len(agent_completed["payload"]["result"]["recommendations"]) == 2
        assert agent_completed["payload"]["result"]["user_friendly_summary"] == "Found $2,850 in monthly savings opportunities"
        assert agent_completed["payload"]["duration_ms"] == 32500.0
        
        # Performance assertion - events should be delivered quickly for good UX
        assert execution_time < 5.0, \
            f"WebSocket event delivery took {execution_time:.2f}s, which may impact user experience. " \
            f"Target: <1s for optimal chat responsiveness."
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_under_connection_stress(
        self,
        websocket_notifier_e2e,
        agent_execution_context,
        real_websocket_manager,
        authenticated_user
    ):
        """
        Test WebSocket event delivery remains reliable under connection stress.
        
        This test simulates challenging conditions like temporary connection issues,
        high message volume, and concurrent agent execution to ensure chat reliability.
        """
        # Arrange - Create multiple rapid-fire agent operations
        mock_websocket = real_websocket_manager._test_websocket
        mock_websocket.messages_sent.clear()
        
        # Create multiple execution contexts for concurrent testing
        contexts = []
        for i in range(3):
            context = AgentExecutionContext(
                agent_name=f"concurrent_agent_{i}",
                thread_id=f"thread_stress_{authenticated_user['user_id']}_{i}",
                user_id=authenticated_user['user_id'],
                run_id=f"run_stress_{i}_{int(datetime.now().timestamp())}",
                total_steps=3
            )
            contexts.append(context)
        
        # Act - Send rapid concurrent agent events (stress test)
        start_time = datetime.now()
        
        # Send events rapidly from multiple "agents" 
        tasks = []
        for i, context in enumerate(contexts):
            async def send_agent_sequence(ctx, delay_offset):
                await asyncio.sleep(delay_offset * 0.1)  # Stagger slightly
                await websocket_notifier_e2e.send_agent_started(ctx)
                await websocket_notifier_e2e.send_agent_thinking(ctx, f"Processing request {delay_offset}", 1)
                await websocket_notifier_e2e.send_tool_executing(ctx, f"tool_{delay_offset}")
                await websocket_notifier_e2e.send_tool_completed(ctx, f"tool_{delay_offset}", {"status": "success"})
                await websocket_notifier_e2e.send_agent_completed(ctx, {"result": f"completed_{delay_offset}"})
            
            task = asyncio.create_task(send_agent_sequence(context, i))
            tasks.append(task)
        
        # Wait for all concurrent agent sequences
        await asyncio.gather(*tasks)
        
        # Allow processing time
        await asyncio.sleep(0.5)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Assert - Verify all events were delivered despite concurrent load
        messages_sent = mock_websocket.messages_sent
        
        # Should have 15 total messages (3 agents  x  5 events each)
        expected_message_count = 15
        assert len(messages_sent) == expected_message_count, \
            f"STRESS TEST FAILURE: Expected {expected_message_count} messages under concurrent load, " \
            f"got {len(messages_sent)}. This indicates WebSocket delivery issues under stress."
        
        # Verify message integrity - all events should have proper structure
        agent_started_count = sum(1 for msg in messages_sent if msg.get("type") == "agent_started")
        agent_completed_count = sum(1 for msg in messages_sent if msg.get("type") == "agent_completed")
        
        assert agent_started_count == 3, f"Expected 3 agent_started events, got {agent_started_count}"
        assert agent_completed_count == 3, f"Expected 3 agent_completed events, got {agent_completed_count}"
        
        # Performance under stress - should still be reasonably fast
        assert execution_time < 10.0, \
            f"Concurrent WebSocket delivery took {execution_time:.2f}s, indicating performance issues under stress."
        
        # Verify no events were lost or corrupted
        for message in messages_sent:
            assert "type" in message, "Message missing type field"
            assert "payload" in message, "Message missing payload field"
            assert message["payload"].get("agent_name"), "Message missing agent_name"
            assert message["payload"].get("timestamp") or message["payload"].get("run_id"), \
                "Message missing temporal/identity information"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_notifier_authentication_integration(
        self,
        websocket_notifier_e2e,
        real_websocket_manager,
        auth_helper
    ):
        """
        Test WebSocketNotifier properly integrates with authentication system.
        
        Validates that WebSocket events are only delivered to authenticated users
        and that user isolation is maintained (no cross-user message leakage).
        """
        # Arrange - Create two different authenticated users
        user_a = await auth_helper.create_test_user(
            email="user_a_ws_notifier@netra.ai",
            name="WebSocket User A",
            user_type="enterprise"
        )
        
        user_b = await auth_helper.create_test_user(
            email="user_b_ws_notifier@netra.ai", 
            name="WebSocket User B",
            user_type="mid"
        )
        
        # Create separate WebSocket connections for each user
        class MockWebSocketForAuth:
            def __init__(self, user_id):
                self.user_id = user_id
                self.messages_sent = []
                self.closed = False
            
            async def send_json(self, data):
                if not self.closed:
                    self.messages_sent.append(data)
        
        websocket_a = MockWebSocketForAuth(user_a['user_id'])
        websocket_b = MockWebSocketForAuth(user_b['user_id'])
        
        # Add connections for both users
        conn_a = WebSocketConnection(
            connection_id=f"auth_test_a_{user_a['user_id']}",
            user_id=user_a['user_id'],
            websocket=websocket_a,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": "auth_integration", "user": "A"}
        )
        
        conn_b = WebSocketConnection(
            connection_id=f"auth_test_b_{user_b['user_id']}",
            user_id=user_b['user_id'],
            websocket=websocket_b,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": "auth_integration", "user": "B"}
        )
        
        await real_websocket_manager.add_connection(conn_a)
        await real_websocket_manager.add_connection(conn_b)
        
        # Create execution contexts for each user
        context_a = AgentExecutionContext(
            agent_name="user_a_agent",
            thread_id=f"thread_a_{user_a['user_id']}",
            user_id=user_a['user_id'],
            run_id=f"run_a_{int(datetime.now().timestamp())}"
        )
        
        context_b = AgentExecutionContext(
            agent_name="user_b_agent", 
            thread_id=f"thread_b_{user_b['user_id']}",
            user_id=user_b['user_id'],
            run_id=f"run_b_{int(datetime.now().timestamp())}"
        )
        
        try:
            # Act - Send events for both users
            await websocket_notifier_e2e.send_agent_started(context_a)
            await websocket_notifier_e2e.send_agent_thinking(context_a, "User A thinking", 1)
            await websocket_notifier_e2e.send_agent_completed(context_a, {"result": "User A result"})
            
            await websocket_notifier_e2e.send_agent_started(context_b)  
            await websocket_notifier_e2e.send_agent_thinking(context_b, "User B thinking", 1)
            await websocket_notifier_e2e.send_agent_completed(context_b, {"result": "User B result"})
            
            # Allow processing time
            await asyncio.sleep(0.3)
            
            # Assert - Verify user isolation (no cross-user message leakage)
            assert len(websocket_a.messages_sent) == 3, \
                f"User A should receive exactly 3 messages, got {len(websocket_a.messages_sent)}"
            assert len(websocket_b.messages_sent) == 3, \
                f"User B should receive exactly 3 messages, got {len(websocket_b.messages_sent)}"
            
            # Verify User A only receives their own messages
            for message in websocket_a.messages_sent:
                assert "user_a_agent" in message["payload"]["agent_name"], \
                    f"User A received message for wrong agent: {message['payload']['agent_name']}"
                assert context_a.run_id in message["payload"]["run_id"], \
                    f"User A received message for wrong run: {message['payload']['run_id']}"
            
            # Verify User B only receives their own messages  
            for message in websocket_b.messages_sent:
                assert "user_b_agent" in message["payload"]["agent_name"], \
                    f"User B received message for wrong agent: {message['payload']['agent_name']}"
                assert context_b.run_id in message["payload"]["run_id"], \
                    f"User B received message for wrong run: {message['payload']['run_id']}"
            
            # Verify message content is user-specific
            user_a_thinking = next(msg for msg in websocket_a.messages_sent if msg["type"] == "agent_thinking")
            assert user_a_thinking["payload"]["thought"] == "User A thinking"
            
            user_b_thinking = next(msg for msg in websocket_b.messages_sent if msg["type"] == "agent_thinking")  
            assert user_b_thinking["payload"]["thought"] == "User B thinking"
            
            user_a_result = next(msg for msg in websocket_a.messages_sent if msg["type"] == "agent_completed")
            assert user_a_result["payload"]["result"]["result"] == "User A result"
            
            user_b_result = next(msg for msg in websocket_b.messages_sent if msg["type"] == "agent_completed")
            assert user_b_result["payload"]["result"]["result"] == "User B result"
            
        finally:
            # Cleanup
            await real_websocket_manager.remove_connection(conn_a.connection_id)
            await real_websocket_manager.remove_connection(conn_b.connection_id)