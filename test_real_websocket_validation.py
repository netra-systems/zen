#!/usr/bin/env python
"""
Simple validation test for real WebSocket connections - NO MOCKS
Tests that the 5 required WebSocket events work with real connections.

Business Value: Validates that real WebSocket connections can deliver the events
that drive 90% of platform value ($500K+ ARR).
"""

import asyncio
import pytest
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from test_framework.real_websocket_manager import RealWebSocketManager


class TestRealWebSocketValidation:
    """Simple validation tests for real WebSocket connections."""

    @pytest.mark.asyncio
    async def test_real_websocket_manager_can_start_services(self):
        """Test that RealWebSocketManager can start Docker services."""
        manager = RealWebSocketManager()
        
        # Test that we can start services
        success = await manager.ensure_services_ready()
        
        # Clean up
        await manager.cleanup_all_connections()
        
        assert success, "RealWebSocketManager should be able to start Docker services"

    @pytest.mark.asyncio
    async def test_real_websocket_connection_creation(self):
        """Test that we can create real WebSocket connections."""
        async with RealWebSocketManager().real_websocket_session() as manager:
            # Test user connection
            user_id = "test_user_real"
            thread_id = "test_thread_real"
            
            connection_id = await manager.connect_user(
                user_id=user_id,
                thread_id=thread_id
            )
            
            assert connection_id is not None, "Should be able to create real WebSocket connection"
            assert connection_id.startswith("real_conn_"), "Connection ID should indicate real connection"
            
            # Test connection metrics
            metrics = manager.get_connection_metrics()
            assert metrics['successful_connections'] > 0, "Should have successful connections"
            assert metrics['active_connections'] > 0, "Should have active connections"

    @pytest.mark.asyncio 
    async def test_required_websocket_events_interface(self):
        """Test that RealWebSocketManager supports the 5 required events interface."""
        async with RealWebSocketManager().real_websocket_session() as manager:
            user_id = "test_user_events"
            thread_id = "test_thread_events"
            
            # Connect user
            await manager.connect_user(user_id=user_id, thread_id=thread_id)
            
            # Test sending the 5 required events
            required_events = [
                {"type": "agent_started", "user_id": user_id, "thread_id": thread_id},
                {"type": "agent_thinking", "user_id": user_id, "thread_id": thread_id, "reasoning": "Testing"},
                {"type": "tool_executing", "user_id": user_id, "thread_id": thread_id, "tool_name": "test_tool"},
                {"type": "tool_completed", "user_id": user_id, "thread_id": thread_id, "tool_name": "test_tool"},
                {"type": "agent_completed", "user_id": user_id, "thread_id": thread_id, "result": "Test complete"}
            ]
            
            # Send all required events
            for event in required_events:
                success = await manager.send_to_thread(thread_id, event)
                assert success, f"Should be able to send {event['type']} event through real WebSocket"
            
            # Verify events were captured
            captured_events = manager.get_events_for_thread(thread_id)
            assert len(captured_events) == 5, f"Should capture all 5 events, got {len(captured_events)}"
            
            # Verify event types
            captured_types = {event.get('type') for event in captured_events}
            expected_types = {event['type'] for event in required_events}
            assert captured_types == expected_types, f"Should capture all event types: {expected_types}"
            
            # Test compliance score
            compliance_score = manager.get_compliance_score(thread_id)
            assert compliance_score == 1.0, f"Should have 100% compliance, got {compliance_score:.2%}"

    @pytest.mark.asyncio
    async def test_user_isolation_with_real_connections(self):
        """Test that real WebSocket connections maintain user isolation."""
        async with RealWebSocketManager().real_websocket_session() as manager:
            # Create multiple users
            users = [
                {"user_id": "user_1", "thread_id": "thread_1"},
                {"user_id": "user_2", "thread_id": "thread_2"},
                {"user_id": "user_3", "thread_id": "thread_3"}
            ]
            
            # Connect all users
            for user in users:
                await manager.connect_user(user["user_id"], thread_id=user["thread_id"])
            
            # Send events to each user
            for i, user in enumerate(users):
                event = {
                    "type": "agent_started",
                    "user_id": user["user_id"], 
                    "thread_id": user["thread_id"],
                    "message": f"Message for {user['user_id']}"
                }
                success = await manager.send_to_thread(user["thread_id"], event)
                assert success, f"Should send event to {user['user_id']}"
            
            # Verify isolation - each user should only see their own events
            for user in users:
                events = manager.get_events_for_thread(user["thread_id"])
                assert len(events) == 1, f"User {user['user_id']} should see exactly 1 event"
                
                event = events[0]
                assert event.get("user_id") == user["user_id"], "Event should belong to correct user"
                assert event.get("thread_id") == user["thread_id"], "Event should belong to correct thread"
            
            # Verify no cross-contamination
            all_events = manager.captured_events
            for event in all_events:
                event_user_id = event.payload.get("user_id")
                event_thread_id = event.thread_id
                
                # Find the user this event should belong to
                expected_user = None
                for user in users:
                    if user["thread_id"] == event_thread_id:
                        expected_user = user
                        break
                
                assert expected_user is not None, f"Event should belong to a known user"
                assert event_user_id == expected_user["user_id"], "No cross-user contamination"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])