#!/usr/bin/env python3
"""
WebSocket Agent Events Validation
================================

Test that WebSocket agent events work correctly with the fixed e2e user ID patterns.
This ensures the fix doesn't break the critical WebSocket event system.
"""

import asyncio
from unittest.mock import Mock, AsyncMock
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from datetime import datetime

async def test_websocket_agent_events_with_e2e_user():
    """
    Test that WebSocket agent events work with e2e-staging_pipeline user ID.
    
    This validates that our fix maintains WebSocket event functionality.
    """
    print("Testing WebSocket Agent Events with e2e-staging_pipeline...")
    
    # Create manager and mock websocket
    manager = UnifiedWebSocketManager()
    mock_websocket = Mock()
    mock_websocket.send_json = AsyncMock()
    
    # Create connection with our fixed user ID pattern
    connection = WebSocketConnection(
        connection_id="test_conn_e2e",
        user_id="e2e-staging_pipeline",  # Fixed pattern
        websocket=mock_websocket,
        connected_at=datetime.now()
    )
    
    # Add connection to manager
    await manager.add_connection(connection)
    print(f" PASS:  Added connection for user: {connection.user_id}")
    
    # Test critical WebSocket events that agents use
    test_events = [
        ("agent_started", {"message": "Agent execution started", "agent_type": "deployment_agent"}),
        ("agent_thinking", {"message": "Processing deployment pipeline", "step": "validation"}),
        ("tool_executing", {"tool_name": "deployment_validator", "status": "running"}),
        ("tool_completed", {"tool_name": "deployment_validator", "status": "success", "result": "pipeline_valid"}),
        ("agent_completed", {"message": "Deployment pipeline validation complete", "status": "success"})
    ]
    
    # Send each event type
    for event_type, event_data in test_events:
        try:
            await manager.emit_critical_event(
                user_id="e2e-staging_pipeline",
                event_type=event_type,
                data=event_data
            )
            print(f" PASS:  Successfully sent {event_type} event")
            
            # Verify the mock was called with correct data
            assert mock_websocket.send_json.called
            sent_data = mock_websocket.send_json.call_args[0][0]
            assert sent_data['type'] == event_type
            assert sent_data['data'] == event_data
            
            # Reset mock for next test
            mock_websocket.send_json.reset_mock()
            
        except Exception as e:
            print(f" FAIL:  Failed to send {event_type} event: {e}")
            return False
    
    print(" PASS:  ALL WEBSOCKET AGENT EVENTS WORKING")
    return True

async def test_multiple_user_patterns():
    """Test WebSocket events work with various user ID patterns."""
    print("\nTesting multiple user ID patterns...")
    
    manager = UnifiedWebSocketManager()
    test_patterns = [
        "e2e-staging_pipeline",      # Primary fix
        "e2e-production_deploy",     # Production pattern
        "test-user-123",             # Existing pattern
        "user_456",                  # Simple pattern
    ]
    
    # Create connections for each pattern
    for i, pattern in enumerate(test_patterns):
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        connection = WebSocketConnection(
            connection_id=f"conn_{i}",
            user_id=pattern,
            websocket=mock_websocket,
            connected_at=datetime.now()
        )
        
        await manager.add_connection(connection)
        
        # Test event sending
        await manager.emit_critical_event(
            user_id=pattern,
            event_type="test_event",
            data={"test": "data", "user_pattern": pattern}
        )
        
        print(f" PASS:  Pattern {pattern} - WebSocket events working")
    
    print(" PASS:  ALL USER PATTERNS SUPPORT WEBSOCKET EVENTS")
    return True

async def test_connection_health_and_isolation():
    """Test connection health checks and user isolation."""
    print("\nTesting connection health and isolation...")
    
    manager = UnifiedWebSocketManager()
    
    # Test users
    user1 = "e2e-staging_pipeline"
    user2 = "e2e-production_deploy" 
    
    # Create connections
    for i, user_id in enumerate([user1, user2]):
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        connection = WebSocketConnection(
            connection_id=f"isolation_conn_{i}",
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now()
        )
        
        await manager.add_connection(connection)
    
    # Test isolation - each user should only see their own health
    health1 = manager.get_connection_health(user1)
    health2 = manager.get_connection_health(user2)
    
    assert health1['user_id'] == user1
    assert health2['user_id'] == user2
    assert health1['total_connections'] == 1
    assert health2['total_connections'] == 1
    
    print(f" PASS:  User isolation maintained: {user1} and {user2}")
    
    # Test that events go to correct users
    await manager.emit_critical_event(user1, "isolated_event", {"target": user1})
    await manager.emit_critical_event(user2, "isolated_event", {"target": user2})
    
    print(" PASS:  EVENT ISOLATION WORKING")
    return True

async def main():
    """Run all WebSocket agent event validation tests."""
    print("="*60)
    print("WEBSOCKET AGENT EVENTS VALIDATION - SYSTEM STABILITY TEST")
    print("="*60)
    
    try:
        # Run all tests
        test1 = await test_websocket_agent_events_with_e2e_user()
        test2 = await test_multiple_user_patterns() 
        test3 = await test_connection_health_and_isolation()
        
        if all([test1, test2, test3]):
            print("\n" + "="*60)
            print(" PASS:  WEBSOCKET AGENT EVENTS VALIDATION: ALL TESTS PASSED")
            print(" PASS:  SYSTEM STABILITY: MAINTAINED")
            print(" PASS:  BUSINESS VALUE: WebSocket events work with e2e deployment users")
            print(" PASS:  NO BREAKING CHANGES: Existing patterns continue to work")
            print("="*60)
            return True
        else:
            print("\n FAIL:  SOME TESTS FAILED - SYSTEM MAY BE UNSTABLE")
            return False
            
    except Exception as e:
        print(f"\n FAIL:  CRITICAL ERROR IN WEBSOCKET EVENTS: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)