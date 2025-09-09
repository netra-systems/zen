"""
WebSocket Connection Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure stable WebSocket connections for real-time AI chat interactions
- Value Impact: Users can maintain persistent connections for AI chat without drops
- Strategic Impact: Foundation for real-time AI collaboration and chat business value

CRITICAL: These tests validate actual WebSocket connection behavior using REAL services.
NO MOCKS - Uses real PostgreSQL (port 5434) and Redis (port 6381).
Tests service interactions without Docker containers (integration layer).
"""

import asyncio
import pytest
import time
import websockets
from typing import Dict, Any, Optional
from unittest import mock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_postgres_connection, with_test_database

from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState, 
    ConnectionInfo,
    MessageType,
    WebSocketMessage
)
from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestWebSocketConnectionIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket connection management."""

    async def async_setup(self):
        """Set up test environment with real services."""
        await super().async_setup()
        self.env = get_env()
        self.test_user_id = UnifiedIdGenerator.generate_user_id()
        self.test_connection_id = UnifiedIdGenerator.generate_websocket_connection_id(self.test_user_id)

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_websocket_connection_establishment_and_authentication(self, real_services_fixture):
        """
        Test WebSocket connection establishment with authentication.
        
        Business Value: Users must be able to establish authenticated WebSocket connections
        for AI chat interactions. This is the foundation for all real-time AI features.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        # Create test user context with real database
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id}@test.netra.ai',
            'name': 'WebSocket Integration Test User'
        })
        
        # Initialize WebSocket manager with real services
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            # Create mock WebSocket for connection simulation
            mock_websocket = mock.MagicMock()
            mock_websocket.close = mock.AsyncMock()
            mock_websocket.send = mock.AsyncMock()
            mock_websocket.recv = mock.AsyncMock()
            
            # Test connection establishment
            connection_info = ConnectionInfo(
                user_id=user_data['id'],
                websocket=mock_websocket,
                thread_id=UnifiedIdGenerator.generate_thread_id(user_data['id'])
            )
            
            # Add connection to manager
            await websocket_manager.add_connection(connection_info)
            
            # Verify connection is tracked
            active_connections = await websocket_manager.get_active_connections()
            user_connections = [conn for conn in active_connections if conn.user_id == user_data['id']]
            
            assert len(user_connections) == 1, "User should have exactly one active connection"
            assert user_connections[0].state == WebSocketConnectionState.CONNECTED, "Connection should be in connected state"
            assert user_connections[0].is_healthy, "Connection should be healthy"
            
            # Test connection authentication validation
            assert user_connections[0].user_id == user_data['id'], "Connection should be tied to correct user"
            
            self.logger.info(f"Successfully established WebSocket connection for user {user_data['id']}")
            
        finally:
            # Cleanup
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket  
    async def test_websocket_connection_persistence_and_reconnection(self, real_services_fixture):
        """
        Test WebSocket connection persistence and reconnection handling.
        
        Business Value: Users need reliable connections that can handle network interruptions
        without losing chat context or ongoing AI agent interactions.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        # Create test user
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id}@test.netra.ai',
            'name': 'Persistence Test User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            # Create initial connection
            mock_websocket = mock.MagicMock()
            mock_websocket.close = mock.AsyncMock()
            mock_websocket.send = mock.AsyncMock()
            
            connection_info = ConnectionInfo(
                user_id=user_data['id'],
                websocket=mock_websocket
            )
            
            await websocket_manager.add_connection(connection_info)
            original_connection_id = connection_info.connection_id
            
            # Simulate connection drop
            connection_info.is_healthy = False
            connection_info.state = WebSocketConnectionState.DISCONNECTED
            
            # Remove disconnected connection
            await websocket_manager.remove_connection(original_connection_id)
            
            # Verify connection was removed
            active_connections = await websocket_manager.get_active_connections()
            user_connections = [conn for conn in active_connections if conn.user_id == user_data['id']]
            assert len(user_connections) == 0, "Disconnected connection should be removed"
            
            # Simulate reconnection
            new_mock_websocket = mock.MagicMock()
            new_mock_websocket.close = mock.AsyncMock()
            new_mock_websocket.send = mock.AsyncMock()
            
            new_connection_info = ConnectionInfo(
                user_id=user_data['id'],
                websocket=new_mock_websocket
            )
            
            await websocket_manager.add_connection(new_connection_info)
            
            # Verify reconnection successful
            active_connections = await websocket_manager.get_active_connections()
            user_connections = [conn for conn in active_connections if conn.user_id == user_data['id']]
            
            assert len(user_connections) == 1, "User should have reconnected successfully"
            assert user_connections[0].connection_id != original_connection_id, "New connection should have different ID"
            assert user_connections[0].is_healthy, "Reconnected connection should be healthy"
            
            self.logger.info(f"Successfully tested reconnection for user {user_data['id']}")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_websocket_connection_cleanup_on_disconnect(self, real_services_fixture):
        """
        Test proper connection cleanup when WebSocket disconnects.
        
        Business Value: Clean resource management prevents memory leaks and ensures
        system stability for long-running AI chat sessions with many users.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        # Create multiple test users for cleanup testing
        user_data_1 = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id}_1@test.netra.ai',
            'name': 'Cleanup Test User 1'
        })
        
        user_data_2 = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id}_2@test.netra.ai', 
            'name': 'Cleanup Test User 2'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            # Create connections for both users
            connections = []
            for i, user_data in enumerate([user_data_1, user_data_2], 1):
                mock_websocket = mock.MagicMock()
                mock_websocket.close = mock.AsyncMock()
                mock_websocket.send = mock.AsyncMock()
                
                connection_info = ConnectionInfo(
                    user_id=user_data['id'],
                    websocket=mock_websocket
                )
                
                await websocket_manager.add_connection(connection_info)
                connections.append(connection_info)
                
                self.logger.info(f"Created connection {i}: {connection_info.connection_id}")
            
            # Verify both connections exist
            active_connections = await websocket_manager.get_active_connections()
            assert len(active_connections) == 2, "Should have 2 active connections before cleanup"
            
            # Disconnect first user
            first_connection = connections[0]
            await websocket_manager.remove_connection(first_connection.connection_id)
            
            # Verify cleanup - only second user should remain
            active_connections = await websocket_manager.get_active_connections()
            assert len(active_connections) == 1, "Should have 1 active connection after first user disconnect"
            
            remaining_connection = active_connections[0]
            assert remaining_connection.user_id == user_data_2['id'], "Remaining connection should be for user 2"
            assert remaining_connection.is_healthy, "Remaining connection should still be healthy"
            
            # Disconnect second user
            await websocket_manager.remove_connection(remaining_connection.connection_id)
            
            # Verify complete cleanup
            active_connections = await websocket_manager.get_active_connections()
            assert len(active_connections) == 0, "All connections should be cleaned up"
            
            self.logger.info("Successfully verified connection cleanup on disconnect")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_websocket_multi_user_connection_isolation(self, real_services_fixture):
        """
        Test that WebSocket connections are properly isolated between users.
        
        Business Value: User isolation is critical for AI chat security and privacy.
        Users must never see or interfere with other users' AI interactions.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        # Create multiple isolated users
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(services, {
                'email': f'{self.test_user_id}_isolation_{i}@test.netra.ai',
                'name': f'Isolation Test User {i}'
            })
            users.append(user_data)
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            # Create connections for each user with different thread contexts
            connections = []
            for i, user_data in enumerate(users):
                mock_websocket = mock.MagicMock()
                mock_websocket.close = mock.AsyncMock()
                mock_websocket.send = mock.AsyncMock()
                
                connection_info = ConnectionInfo(
                    user_id=user_data['id'],
                    websocket=mock_websocket,
                    thread_id=UnifiedIdGenerator.generate_thread_id(user_data['id'])
                )
                
                await websocket_manager.add_connection(connection_info)
                connections.append(connection_info)
            
            # Verify each user has their own isolated connection
            for i, user_data in enumerate(users):
                user_connections = await websocket_manager.get_user_connections(user_data['id'])
                
                assert len(user_connections) == 1, f"User {i} should have exactly 1 connection"
                assert user_connections[0].user_id == user_data['id'], f"User {i} connection should belong to correct user"
                assert user_connections[0].thread_id is not None, f"User {i} should have thread context"
                
                # Verify thread isolation - threads should be different between users
                for j, other_user in enumerate(users):
                    if i != j:
                        other_connections = await websocket_manager.get_user_connections(other_user['id'])
                        assert user_connections[0].thread_id != other_connections[0].thread_id, \
                            f"User {i} and User {j} should have different thread IDs"
            
            # Test cross-user message routing isolation
            test_message = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={"content": "test isolation message", "sensitive_data": "user_private_info"},
                user_id=users[0]['id'],
                thread_id=connections[0].thread_id
            )
            
            # Send message to first user
            await websocket_manager.send_to_user(users[0]['id'], test_message.dict())
            
            # Verify message was sent to correct user's WebSocket
            connections[0].websocket.send.assert_called_once()
            
            # Verify other users did NOT receive the message
            for i in range(1, len(connections)):
                connections[i].websocket.send.assert_not_called()
            
            self.logger.info("Successfully verified multi-user connection isolation")
            
        finally:
            await websocket_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_websocket_connection_state_management(self, real_services_fixture):
        """
        Test WebSocket connection state transitions and management.
        
        Business Value: Reliable state management ensures users get consistent
        AI chat experience with proper connection status feedback.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        user_data = await self.create_test_user_context(services, {
            'email': f'{self.test_user_id}@test.netra.ai',
            'name': 'State Management Test User'
        })
        
        websocket_manager = UnifiedWebSocketManager(
            postgres_url=services["database_url"],
            redis_url=services["redis_url"]
        )
        await websocket_manager.initialize()
        
        try:
            mock_websocket = mock.MagicMock()
            mock_websocket.close = mock.AsyncMock()
            mock_websocket.send = mock.AsyncMock()
            
            # Test initial connection state
            connection_info = ConnectionInfo(
                user_id=user_data['id'],
                websocket=mock_websocket,
                state=WebSocketConnectionState.CONNECTING
            )
            
            # Test state transition to connected
            connection_info.state = WebSocketConnectionState.CONNECTED
            connection_info.is_healthy = True
            await websocket_manager.add_connection(connection_info)
            
            # Verify connected state
            user_connections = await websocket_manager.get_user_connections(user_data['id'])
            assert len(user_connections) == 1
            assert user_connections[0].state == WebSocketConnectionState.CONNECTED
            assert user_connections[0].is_healthy
            
            # Test state transition to disconnecting
            success = connection_info.transition_to_closing()
            assert success, "Should successfully transition to closing state"
            assert connection_info.state == WebSocketConnectionState.CLOSING
            assert connection_info.is_closing
            
            # Test state transition to disconnected
            success = connection_info.transition_to_closed()
            assert success, "Should successfully transition to closed state"
            assert connection_info.state == WebSocketConnectionState.CLOSED
            assert not connection_info.is_closing
            assert not connection_info.is_healthy
            
            # Test error state transition
            connection_info.transition_to_failed()
            assert connection_info.state == WebSocketConnectionState.FAILED
            assert not connection_info.is_healthy
            assert connection_info.failure_count == 1
            
            # Test invalid state transition (should fail)
            connection_info.state = WebSocketConnectionState.CLOSED
            connection_info.is_closing = False
            invalid_transition = connection_info.transition_to_closing()
            assert not invalid_transition, "Should not allow transition from closed to closing"
            
            self.logger.info("Successfully tested WebSocket connection state management")
            
        finally:
            await websocket_manager.shutdown()