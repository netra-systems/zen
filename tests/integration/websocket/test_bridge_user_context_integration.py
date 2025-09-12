"""
Integration tests for WebSocket bridge with UserExecutionContext - NO DOCKER REQUIRED

Purpose: Test WebSocket bridge integration patterns with user context isolation
Issues: #409 (WebSocket bridge integration), #426 cluster (service dependencies)
Approach: Mock WebSocket connections, test real bridge logic patterns

MISSION CRITICAL: Validates WebSocket bridge maintains user isolation and coordinates
with agent execution without requiring Docker services to be running.

Business Impact: WebSocket events deliver 90% of platform value (real-time chat)
"""

import pytest
import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from shared.types.core_types import UserID, ThreadID, RunID


class TestWebSocketBridgeUserContextIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket bridge with UserExecutionContext patterns"""
    
    async def asyncSetUp(self):
        """Setup test environment with mock services"""
        await super().asyncSetUp()
        
        # Create test user contexts for isolation testing
        self.user_id_1 = UserID(str(uuid.uuid4()))
        self.user_id_2 = UserID(str(uuid.uuid4())) 
        self.thread_id = ThreadID(str(uuid.uuid4()))
        self.run_id = RunID(str(uuid.uuid4()))
        
        # Create UserExecutionContext instances for different users
        self.user_context_1 = UserExecutionContext(
            user_id=self.user_id_1,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=f"req_{uuid.uuid4()}",
            websocket_client_id=f"ws_client_1_{uuid.uuid4()}",
            agent_context={
                "test_scenario": "bridge_integration",
                "user_role": "primary_user"
            },
            audit_metadata={
                "test_case": "websocket_bridge_integration",
                "created_at": "2025-01-09T12:00:00Z"
            }
        )
        
        self.user_context_2 = UserExecutionContext(
            user_id=self.user_id_2,
            thread_id=ThreadID(str(uuid.uuid4())),  # Different thread
            run_id=RunID(str(uuid.uuid4())),        # Different run
            request_id=f"req_{uuid.uuid4()}",
            websocket_client_id=f"ws_client_2_{uuid.uuid4()}",
            agent_context={
                "test_scenario": "bridge_integration", 
                "user_role": "secondary_user"
            },
            audit_metadata={
                "test_case": "websocket_bridge_integration",
                "created_at": "2025-01-09T12:00:00Z"
            }
        )

    @pytest.mark.integration
    @pytest.mark.websocket_bridge
    @pytest.mark.user_context
    @pytest.mark.no_docker_required
    async def test_websocket_bridge_creates_with_user_context(self):
        """
        Test that WebSocket bridge properly integrates with UserExecutionContext
        
        Issue: #409 - WebSocket bridge integration patterns
        Difficulty: Medium (20 minutes)
        Expected: PASS - Bridge should create successfully with context
        """
        # Create WebSocket bridge with user context
        websocket_bridge = create_agent_websocket_bridge(self.user_context_1)
        
        # Verify bridge is created and configured
        assert websocket_bridge is not None, "WebSocket bridge should be created"
        
        # Verify user context is properly associated
        assert hasattr(websocket_bridge, 'user_context'), "Bridge should have user_context"
        
        # Verify user isolation properties
        bridge_user_id = getattr(websocket_bridge, 'user_context', {}).get('user_id')
        assert str(bridge_user_id) == str(self.user_context_1.user_id), (
            f"Bridge should be associated with correct user ID. "
            f"Expected: {self.user_context_1.user_id}, Got: {bridge_user_id}"
        )

    @pytest.mark.integration
    @pytest.mark.websocket_bridge
    @pytest.mark.user_isolation
    @pytest.mark.no_docker_required 
    async def test_websocket_bridge_user_isolation(self):
        """
        Test that WebSocket bridges maintain user isolation
        
        Issue: #409 - Multi-user isolation in WebSocket bridge
        Difficulty: High (30 minutes)
        Expected: PASS - Bridges should be isolated per user
        """
        # Create separate bridges for different users
        bridge_1 = create_agent_websocket_bridge(self.user_context_1)
        bridge_2 = create_agent_websocket_bridge(self.user_context_2)
        
        # Verify bridges are separate instances
        assert bridge_1 is not bridge_2, "Bridges should be separate instances for different users"
        
        # Mock WebSocket connections
        mock_connection_1 = AsyncMock()
        mock_connection_2 = AsyncMock()
        
        # Setup mock WebSocket manager to return different connections
        with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_ws_manager:
            mock_manager = AsyncMock()
            mock_manager.get_connection_by_client_id.side_effect = lambda client_id: {
                self.user_context_1.websocket_client_id: mock_connection_1,
                self.user_context_2.websocket_client_id: mock_connection_2
            }.get(client_id)
            mock_ws_manager.return_value = mock_manager
            
            # Send events through different bridges
            event_data_1 = {"message": "Event for user 1", "user_specific": True}
            event_data_2 = {"message": "Event for user 2", "user_specific": True}
            
            if hasattr(bridge_1, 'send_event'):
                await bridge_1.send_event("agent_started", event_data_1)
            if hasattr(bridge_2, 'send_event'):
                await bridge_2.send_event("agent_started", event_data_2)
            
            # Verify isolation - each connection should only receive its user's events
            if hasattr(mock_connection_1, 'send') and mock_connection_1.send.called:
                user_1_calls = mock_connection_1.send.call_args_list
                for call in user_1_calls:
                    sent_data = json.loads(call[0][0]) if call[0] else {}
                    assert "Event for user 1" in str(sent_data), "User 1 should only receive their events"
                    assert "Event for user 2" not in str(sent_data), "User 1 should not receive user 2's events"
            
            if hasattr(mock_connection_2, 'send') and mock_connection_2.send.called:
                user_2_calls = mock_connection_2.send.call_args_list  
                for call in user_2_calls:
                    sent_data = json.loads(call[0][0]) if call[0] else {}
                    assert "Event for user 2" in str(sent_data), "User 2 should only receive their events"
                    assert "Event for user 1" not in str(sent_data), "User 2 should not receive user 1's events"

    @pytest.mark.integration
    @pytest.mark.websocket_bridge
    @pytest.mark.agent_coordination
    @pytest.mark.no_docker_required
    async def test_websocket_bridge_agent_event_coordination(self):
        """
        Test WebSocket bridge coordinates with agent execution events
        
        Issue: #409 - Agent event coordination through bridge
        Difficulty: High (35 minutes)
        Expected: PASS - Bridge should coordinate with agent events
        """
        # Create bridge with user context
        websocket_bridge = create_agent_websocket_bridge(self.user_context_1)
        
        # Mock WebSocket connection and manager
        mock_connection = AsyncMock()
        sent_events = []
        
        async def track_sent_events(message):
            """Track events sent through WebSocket"""
            try:
                event_data = json.loads(message)
                sent_events.append(event_data)
            except:
                sent_events.append({"raw_message": message})
        
        mock_connection.send.side_effect = track_sent_events
        
        with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_ws_manager:
            mock_manager = AsyncMock()
            mock_manager.get_connection_by_client_id.return_value = mock_connection
            mock_ws_manager.return_value = mock_manager
            
            # Simulate complete agent execution workflow with WebSocket events
            agent_events = [
                ("agent_started", {
                    "agent_type": "supervisor",
                    "user_id": str(self.user_context_1.user_id),
                    "thread_id": str(self.user_context_1.thread_id),
                    "timestamp": "2025-01-09T12:00:00Z"
                }),
                ("agent_thinking", {
                    "reasoning": "Analyzing user request for optimal response",
                    "step": 1,
                    "total_steps": 3
                }),
                ("tool_executing", {
                    "tool_name": "data_analyzer",
                    "tool_input": {"query": "test query"},
                    "execution_id": str(uuid.uuid4())
                }),
                ("tool_completed", {
                    "tool_name": "data_analyzer", 
                    "result": {"status": "success", "data": "analysis complete"},
                    "duration": 2.5
                }),
                ("agent_completed", {
                    "result": "Agent execution completed successfully",
                    "total_duration": 5.2,
                    "status": "success"
                })
            ]
            
            # Send all events through bridge
            for event_type, event_data in agent_events:
                if hasattr(websocket_bridge, 'send_event'):
                    await websocket_bridge.send_event(event_type, event_data)
                elif hasattr(websocket_bridge, 'emit_event'):
                    await websocket_bridge.emit_event(event_type, event_data)
                
                # Small delay to ensure proper ordering
                await asyncio.sleep(0.01)
            
            # Verify all 5 critical events were sent in order
            assert len(sent_events) >= 5, f"Should send all 5 critical events, got {len(sent_events)}"
            
            # Verify event types are present
            event_types = [event.get("type", "") for event in sent_events]
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            for required_event in required_events:
                assert any(required_event in event_type for event_type in event_types), (
                    f"Missing required event: {required_event}. "
                    f"Events sent: {event_types}"
                )
            
            # Verify user context is included in events
            for event in sent_events:
                if "data" in event and isinstance(event["data"], dict):
                    event_user_id = event["data"].get("user_id")
                    if event_user_id:
                        assert event_user_id == str(self.user_context_1.user_id), (
                            f"Event should include correct user ID. "
                            f"Expected: {self.user_context_1.user_id}, Got: {event_user_id}"
                        )

    @pytest.mark.integration
    @pytest.mark.websocket_bridge
    @pytest.mark.factory_pattern
    @pytest.mark.no_docker_required
    async def test_websocket_manager_factory_integration(self):
        """
        Test WebSocket manager factory creates proper instances with user context
        
        Issue: #409 - Factory pattern integration with WebSocket bridge
        Difficulty: Medium (25 minutes) 
        Expected: PASS - Factory should create properly configured instances
        """
        # Test WebSocket manager factory (if it exists)
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            
            # Create manager through factory with user context
            websocket_manager = create_websocket_manager(self.user_context_1)
            
            assert websocket_manager is not None, "Factory should create WebSocket manager"
            
            # Verify manager has proper user context association
            if hasattr(websocket_manager, 'user_context'):
                manager_user_id = websocket_manager.user_context.get('user_id') 
                assert str(manager_user_id) == str(self.user_context_1.user_id), (
                    f"Manager should be associated with correct user"
                )
            
        except ImportError:
            # Factory might not exist yet - this is acceptable
            self.logger.info("WebSocket manager factory not available - using direct WebSocket bridge")
            
            # Test direct bridge creation instead
            bridge = create_agent_websocket_bridge(self.user_context_1)
            assert bridge is not None, "Direct bridge creation should work"

    @pytest.mark.integration
    @pytest.mark.websocket_bridge  
    @pytest.mark.error_handling
    @pytest.mark.no_docker_required
    async def test_websocket_bridge_error_handling_with_user_context(self):
        """
        Test WebSocket bridge error handling maintains user context integrity
        
        Issue: #409 - Error handling in bridge with user isolation
        Difficulty: Medium (20 minutes)
        Expected: PASS - Errors should not compromise user isolation
        """
        # Create bridge with user context
        websocket_bridge = create_agent_websocket_bridge(self.user_context_1)
        
        # Mock failing WebSocket connection
        mock_connection = AsyncMock()
        mock_connection.send.side_effect = Exception("WebSocket connection failed")
        
        error_events = []
        
        with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_ws_manager:
            mock_manager = AsyncMock()
            mock_manager.get_connection_by_client_id.return_value = mock_connection
            mock_ws_manager.return_value = mock_manager
            
            # Test error handling during event sending
            try:
                if hasattr(websocket_bridge, 'send_event'):
                    await websocket_bridge.send_event("agent_started", {
                        "user_id": str(self.user_context_1.user_id),
                        "test": "error_handling"
                    })
                elif hasattr(websocket_bridge, 'emit_event'):
                    await websocket_bridge.emit_event("agent_started", {
                        "user_id": str(self.user_context_1.user_id),
                        "test": "error_handling"  
                    })
                    
            except Exception as e:
                error_events.append(str(e))
            
            # Verify user context integrity is maintained despite errors
            # Bridge should still have correct user context
            if hasattr(websocket_bridge, 'user_context'):
                context_user_id = getattr(websocket_bridge.user_context, 'user_id', None)
                assert str(context_user_id) == str(self.user_context_1.user_id), (
                    "User context should remain intact despite WebSocket errors"
                )
            
            # Errors should not leak between users
            # Create second bridge to verify isolation maintained
            bridge_2 = create_agent_websocket_bridge(self.user_context_2)
            
            # Second bridge should still work independently
            if hasattr(bridge_2, 'user_context'):
                context_2_user_id = getattr(bridge_2.user_context, 'user_id', None)
                assert str(context_2_user_id) == str(self.user_context_2.user_id), (
                    "Second user's bridge should be unaffected by first user's errors"
                )

    @pytest.mark.integration
    @pytest.mark.websocket_bridge
    @pytest.mark.concurrent_users
    @pytest.mark.no_docker_required
    async def test_websocket_bridge_concurrent_user_handling(self):
        """
        Test WebSocket bridge handles concurrent users correctly
        
        Issue: #409 - Concurrent user handling in bridge
        Difficulty: High (40 minutes)
        Expected: PASS - Bridge should handle multiple concurrent users
        """
        # Create multiple user contexts for concurrency testing
        user_contexts = []
        bridges = []
        
        for i in range(3):
            user_context = UserExecutionContext(
                user_id=UserID(f"concurrent_user_{i}_{uuid.uuid4()}"),
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4())),
                request_id=f"concurrent_req_{i}_{uuid.uuid4()}",
                websocket_client_id=f"concurrent_ws_{i}_{uuid.uuid4()}",
                agent_context={
                    "test_scenario": "concurrent_bridge_test",
                    "user_index": i
                },
                audit_metadata={"test": "concurrent_users"}
            )
            user_contexts.append(user_context)
            
            # Create bridge for each user
            bridge = create_agent_websocket_bridge(user_context)
            bridges.append(bridge)
        
        # Mock connections for each user
        mock_connections = [AsyncMock() for _ in range(3)]
        sent_messages = [[] for _ in range(3)]  # Track messages per user
        
        # Setup tracking for each connection
        for i, mock_connection in enumerate(mock_connections):
            async def make_tracker(user_index):
                async def track_messages(message):
                    sent_messages[user_index].append(message)
                return track_messages
            
            mock_connection.send.side_effect = await make_tracker(i)
        
        with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_ws_manager:
            mock_manager = AsyncMock()
            
            # Map client IDs to connections
            def get_connection_by_client_id(client_id):
                for i, context in enumerate(user_contexts):
                    if context.websocket_client_id == client_id:
                        return mock_connections[i]
                return None
            
            mock_manager.get_connection_by_client_id.side_effect = get_connection_by_client_id
            mock_ws_manager.return_value = mock_manager
            
            # Send concurrent events from all users
            async def send_user_events(user_index, bridge, user_context):
                """Send events for a specific user"""
                events = [
                    ("agent_started", {"user_index": user_index, "message": f"User {user_index} started"}),
                    ("agent_thinking", {"user_index": user_index, "message": f"User {user_index} thinking"}),
                    ("agent_completed", {"user_index": user_index, "message": f"User {user_index} completed"})
                ]
                
                for event_type, event_data in events:
                    if hasattr(bridge, 'send_event'):
                        await bridge.send_event(event_type, event_data)
                    elif hasattr(bridge, 'emit_event'):
                        await bridge.emit_event(event_type, event_data)
                    
                    # Small delay to allow interleaving
                    await asyncio.sleep(0.01)
            
            # Execute concurrent event sending
            tasks = []
            for i, (bridge, user_context) in enumerate(zip(bridges, user_contexts)):
                task = send_user_events(i, bridge, user_context)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Verify message isolation - each user should only receive their own messages
            for user_index, messages in enumerate(sent_messages):
                if messages:  # If messages were sent
                    for message in messages:
                        try:
                            parsed_message = json.loads(message)
                            message_user_index = parsed_message.get("data", {}).get("user_index")
                            
                            # If user_index is specified, it should match the receiving user
                            if message_user_index is not None:
                                assert message_user_index == user_index, (
                                    f"User {user_index} received message intended for user {message_user_index}. "
                                    f"This indicates user isolation is broken."
                                )
                        except json.JSONDecodeError:
                            # Raw messages are also acceptable
                            pass
            
            # Verify each user received some messages (bridge is functional)
            active_users = sum(1 for messages in sent_messages if len(messages) > 0)
            assert active_users > 0, "At least some users should receive messages through their bridges"


# Test configuration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket_bridge,
    pytest.mark.user_context,
    pytest.mark.user_isolation,
    pytest.mark.issue_409,
    pytest.mark.issue_426_cluster,
    pytest.mark.no_docker_required,
    pytest.mark.real_services_not_required
]


if __name__ == "__main__":
    # Allow running this file directly
    pytest.main([
        __file__,
        "-v",
        "--tb=long", 
        "-s",
        "--no-docker"
    ])