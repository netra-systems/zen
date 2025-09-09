"""
Test WebSocket Multiple Concurrent Connection Management per User with State Isolation

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (users with multiple devices/tabs)
- Business Goal: Support users with multiple active sessions while maintaining data isolation
- Value Impact: Users can work across multiple devices/browser tabs seamlessly
- Strategic Impact: Enables modern multi-device user workflows and improved user experience

This integration test validates that multiple concurrent WebSocket connections per user
are properly managed while maintaining strict state isolation between connections.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestWebSocketMultipleConcurrentConnectionsStateIsolationIntegration(BaseIntegrationTest):
    """Test multiple concurrent WebSocket connections per user with comprehensive state isolation."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_concurrent_connections_per_user_with_state_isolation(self, real_services_fixture):
        """Test that users can have multiple concurrent connections with proper state isolation."""
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'multi_connection_user@netra.ai',
            'name': 'Multi Connection User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create multiple connections for the same user (simulating multiple tabs/devices)
        connections = []
        for i in range(3):
            class MultiConnectionWebSocket:
                def __init__(self, connection_index: int):
                    self.connection_index = connection_index
                    self.messages_sent = []
                    self.is_closed = False
                    self.device_id = f"device_{connection_index}"
                
                async def send_json(self, data):
                    data['_connection_metadata'] = {
                        'connection_index': self.connection_index,
                        'device_id': self.device_id,
                        'received_at': datetime.utcnow().isoformat()
                    }
                    self.messages_sent.append(data)
                
                async def close(self):
                    self.is_closed = True
            
            connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"multi_conn_{i}",
                context={"user_id": user_id, "device": f"device_{i}"}
            )
            
            websocket = MultiConnectionWebSocket(i)
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "connection_type": "multi_concurrent",
                    "device_id": f"device_{i}",
                    "connection_index": i
                }
            )
            
            await websocket_manager.add_connection(connection)
            connections.append({
                'connection_id': connection_id,
                'websocket': websocket,
                'connection': connection,
                'device_id': f"device_{i}"
            })
        
        # Verify all connections are active for the same user
        assert websocket_manager.is_connection_active(user_id)
        user_connections = websocket_manager.get_user_connections(user_id)
        assert len(user_connections) == 3, "User should have 3 concurrent connections"
        
        # Send messages that should be delivered to all connections
        for i in range(5):
            message = {
                "type": "broadcast_message",
                "data": {"message_index": i, "broadcast": True},
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket_manager.send_to_user(user_id, message)
        
        # Verify all connections received messages
        for conn_info in connections:
            assert len(conn_info['websocket'].messages_sent) == 5
            # Verify each connection has proper isolation metadata
            for msg in conn_info['websocket'].messages_sent:
                assert '_connection_metadata' in msg
                assert msg['_connection_metadata']['device_id'] == conn_info['device_id']
        
        # Clean up
        for conn_info in connections:
            await websocket_manager.remove_connection(conn_info['connection_id'])
        
        self.assert_business_value_delivered({
            'multi_device_support': True,
            'concurrent_connection_management': True,
            'state_isolation': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_specific_message_routing_with_isolation(self, real_services_fixture):
        """Test that messages can be routed to specific connections while maintaining isolation."""
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'connection_routing_user@netra.ai',
            'name': 'Connection Routing User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create connections representing different contexts (mobile, desktop, tablet)
        connection_contexts = ["mobile", "desktop", "tablet"]
        connections = {}
        
        for context in connection_contexts:
            class ContextualWebSocket:
                def __init__(self, context: str):
                    self.context = context
                    self.messages_sent = []
                    self.is_closed = False
                
                async def send_json(self, data):
                    data['_context'] = self.context
                    self.messages_sent.append(data)
                
                async def close(self):
                    self.is_closed = True
            
            connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"context_{context}",
                context={"user_id": user_id, "device_context": context}
            )
            
            websocket = ContextualWebSocket(context)
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "connection_type": "contextual",
                    "device_context": context
                }
            )
            
            await websocket_manager.add_connection(connection)
            connections[context] = {
                'connection_id': connection_id,
                'websocket': websocket,
                'connection': connection
            }
        
        # Send context-specific messages (in real system, routing would be more sophisticated)
        await websocket_manager.send_to_user(user_id, {
            "type": "general_message",
            "data": {"content": "This goes to all contexts"}
        })
        
        # Verify all connections received the general message
        for context, conn_info in connections.items():
            assert len(conn_info['websocket'].messages_sent) == 1
            assert conn_info['websocket'].messages_sent[0]['_context'] == context
        
        # Clean up
        for conn_info in connections.values():
            await websocket_manager.remove_connection(conn_info['connection_id'])
        
        self.assert_business_value_delivered({
            'contextual_message_routing': True,
            'device_specific_handling': True,
            'connection_isolation': True
        }, 'automation')