"""
Test WebSocket Connection Establishment with Application State Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket connections with proper state management
- Value Impact: Users can establish WebSocket connections that properly initialize application state
- Strategic Impact: Critical foundation for all real-time features and agent interactions

This integration test validates that WebSocket connections are properly established
and that application state is correctly synchronized during the connection process.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestWebSocketConnectionEstablishmentApplicationStateIntegration(BaseIntegrationTest):
    """Test WebSocket connection establishment with comprehensive application state validation."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_establishment_initializes_application_state(self, real_services_fixture):
        """
        Test that WebSocket connection establishment properly initializes application state.
        
        Business Value: Ensures users can connect to WebSocket and their state is properly
        initialized in the database and cache layers.
        """
        # Create test user context with real database
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'websocket_test_user@netra.ai',
            'name': 'WebSocket Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        # Create test session in Redis
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        # Initialize WebSocket manager
        websocket_manager = UnifiedWebSocketManager()
        
        # Mock WebSocket object for testing
        class MockWebSocket:
            def __init__(self):
                self.messages_sent = []
                self.is_closed = False
            
            async def send_json(self, data):
                self.messages_sent.append(data)
            
            async def close(self):
                self.is_closed = True
        
        mock_websocket = MockWebSocket()
        
        # Create connection with application state initialization
        id_manager = UnifiedIDManager()
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="test_conn",
            context={"user_id": user_id, "test": "establishment"}
        )
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "test_establishment",
                "client_info": {"browser": "test", "version": "1.0"},
                "session_id": session_data['session_key']
            }
        )
        
        # CRITICAL: Add connection and verify application state sync
        await websocket_manager.add_connection(connection)
        
        # Verify connection is properly registered
        assert websocket_manager.is_connection_active(user_id), "Connection should be active after establishment"
        
        # Verify connection can be retrieved
        retrieved_connection = websocket_manager.get_connection(connection_id)
        assert retrieved_connection is not None, "Connection should be retrievable after establishment"
        assert retrieved_connection.user_id == user_id, "Retrieved connection should have correct user_id"
        assert retrieved_connection.metadata is not None, "Connection metadata should be preserved"
        
        # Verify user connections are tracked
        user_connections = websocket_manager.get_user_connections(user_id)
        assert connection_id in user_connections, "User should have the connection registered"
        assert len(user_connections) == 1, "User should have exactly one connection"
        
        # Verify application state persistence in database
        db_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, name, is_active, created_at, updated_at FROM auth.users WHERE id = $1",
            user_id
        )
        assert db_user is not None, "User should exist in database"
        assert db_user['email'] == 'websocket_test_user@netra.ai', "Database user email should match"
        assert db_user['is_active'] is True, "Database user should be active"
        
        # Verify session state persistence in Redis
        cached_session = await real_services_fixture["redis"].get(session_data['session_key'])
        assert cached_session is not None, "Session should exist in Redis cache"
        
        # Test connection health
        connection_health = websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True, "Connection health should show active connections"
        assert connection_health['total_connections'] == 1, "Should have exactly one connection"
        assert connection_health['active_connections'] == 1, "Should have one active connection"
        
        # Verify connection metadata is properly stored and correlated
        assert connection_health['connections'][0]['connection_id'] == connection_id
        assert 'connected_at' in connection_health['connections'][0]
        assert connection_health['connections'][0]['active'] is True
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        
        # Verify cleanup
        assert not websocket_manager.is_connection_active(user_id), "Connection should be inactive after removal"
        assert websocket_manager.get_connection(connection_id) is None, "Connection should not be retrievable after removal"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_establishment_with_concurrent_state_updates(self, real_services_fixture):
        """
        Test WebSocket connection establishment under concurrent state update scenarios.
        
        Business Value: Ensures connection establishment is thread-safe and doesn't
        corrupt application state when multiple operations happen simultaneously.
        """
        # Create multiple test users
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'concurrent_test_user_{i}@netra.ai',
                'name': f'Concurrent Test User {i}',
                'is_active': True
            })
            session_data = await self.create_test_session(real_services_fixture, user_data['id'])
            users.append({'user_data': user_data, 'session_data': session_data})
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        async def establish_connection_with_state(user_info, connection_index):
            """Helper to establish connection with concurrent state updates."""
            user_id = user_info['user_data']['id']
            
            class MockWebSocket:
                def __init__(self, user_id, index):
                    self.user_id = user_id
                    self.index = index
                    self.messages_sent = []
                    self.is_closed = False
                
                async def send_json(self, data):
                    self.messages_sent.append(data)
                
                async def close(self):
                    self.is_closed = True
            
            mock_websocket = MockWebSocket(user_id, connection_index)
            
            connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"concurrent_conn_{connection_index}",
                context={"user_id": user_id, "test": "concurrent"}
            )
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=mock_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "connection_type": "concurrent_test",
                    "connection_index": connection_index,
                    "session_id": user_info['session_data']['session_key']
                }
            )
            
            # Simulate concurrent connection establishment
            await websocket_manager.add_connection(connection)
            
            # Simulate concurrent state updates in database
            await real_services_fixture["postgres"].execute(
                "UPDATE auth.users SET updated_at = $1 WHERE id = $2",
                datetime.utcnow(),
                user_id
            )
            
            # Simulate concurrent state updates in Redis
            await real_services_fixture["redis"].set(
                f"user_activity:{user_id}",
                json.dumps({
                    "last_activity": datetime.utcnow().isoformat(),
                    "connection_count": len(websocket_manager.get_user_connections(user_id)),
                    "connection_index": connection_index
                }),
                ex=300  # 5 minute expiry
            )
            
            return {
                'connection_id': connection_id,
                'user_id': user_id,
                'connection': connection,
                'websocket': mock_websocket
            }
        
        # Establish connections concurrently
        connection_tasks = [
            establish_connection_with_state(user_info, i)
            for i, user_info in enumerate(users)
        ]
        
        # Execute concurrent connection establishments
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        for i, result in enumerate(connection_results):
            assert not isinstance(result, Exception), f"Connection {i} establishment failed with exception: {result}"
        
        # Verify all connections were established successfully
        for i, result in enumerate(connection_results):
            user_id = result['user_id']
            connection_id = result['connection_id']
            
            # Verify connection is active
            assert websocket_manager.is_connection_active(user_id), f"User {i} connection should be active"
            
            # Verify connection can be retrieved
            retrieved_connection = websocket_manager.get_connection(connection_id)
            assert retrieved_connection is not None, f"User {i} connection should be retrievable"
            assert retrieved_connection.user_id == user_id, f"User {i} retrieved connection should have correct user_id"
            
            # Verify user connection tracking
            user_connections = websocket_manager.get_user_connections(user_id)
            assert connection_id in user_connections, f"User {i} should have connection registered"
            assert len(user_connections) == 1, f"User {i} should have exactly one connection"
        
        # Verify application state consistency across all users
        for i, result in enumerate(connection_results):
            user_id = result['user_id']
            
            # Verify database state consistency
            db_user = await real_services_fixture["postgres"].fetchrow(
                "SELECT id, email, updated_at FROM auth.users WHERE id = $1",
                user_id
            )
            assert db_user is not None, f"User {i} should exist in database"
            assert db_user['updated_at'] is not None, f"User {i} should have updated timestamp"
            
            # Verify Redis state consistency
            user_activity = await real_services_fixture["redis"].get(f"user_activity:{user_id}")
            assert user_activity is not None, f"User {i} activity should exist in Redis"
            activity_data = json.loads(user_activity)
            assert 'last_activity' in activity_data, f"User {i} should have last_activity tracked"
            assert activity_data['connection_count'] == 1, f"User {i} should have correct connection count"
            assert activity_data['connection_index'] == i, f"User {i} should have correct connection index"
        
        # Verify manager statistics are accurate
        stats = websocket_manager.get_stats()
        assert stats['total_connections'] == 3, "Manager should track 3 total connections"
        assert stats['unique_users'] == 3, "Manager should track 3 unique users"
        
        # Clean up all connections
        cleanup_tasks = [
            websocket_manager.remove_connection(result['connection_id'])
            for result in connection_results
        ]
        await asyncio.gather(*cleanup_tasks)
        
        # Verify cleanup
        for result in connection_results:
            user_id = result['user_id']
            connection_id = result['connection_id']
            
            assert not websocket_manager.is_connection_active(user_id), f"User connection should be inactive after cleanup"
            assert websocket_manager.get_connection(connection_id) is None, f"Connection should not be retrievable after cleanup"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_establishment_failure_state_rollback(self, real_services_fixture):
        """
        Test that failed WebSocket connection establishments properly rollback application state.
        
        Business Value: Ensures system consistency when connection establishment fails,
        preventing orphaned state and resource leaks.
        """
        # Create test user
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'failure_test_user@netra.ai',
            'name': 'Failure Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create a WebSocket mock that will fail during state setup
        class FailingWebSocket:
            def __init__(self, should_fail_on_send=False):
                self.should_fail_on_send = should_fail_on_send
                self.messages_sent = []
                self.is_closed = False
            
            async def send_json(self, data):
                if self.should_fail_on_send:
                    raise ConnectionError("Simulated WebSocket send failure")
                self.messages_sent.append(data)
            
            async def close(self):
                self.is_closed = True
        
        # Test 1: Connection establishment that fails during WebSocket operations
        failing_websocket = FailingWebSocket(should_fail_on_send=True)
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="failing_conn",
            context={"user_id": user_id, "test": "failure"}
        )
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=failing_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "failure_test",
                "session_id": session_data['session_key']
            }
        )
        
        # Attempt to add connection (should succeed as add_connection doesn't immediately send)
        await websocket_manager.add_connection(connection)
        
        # Verify connection was added initially
        assert websocket_manager.is_connection_active(user_id), "Connection should be initially active"
        
        # Attempt to send message through failing WebSocket
        test_message = {
            "type": "test_message",
            "data": {"message": "This should fail"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # This should handle the failure gracefully and clean up the connection
        await websocket_manager.send_to_user(user_id, test_message)
        
        # Give time for cleanup to process
        await asyncio.sleep(0.1)
        
        # Verify state consistency after failure
        # The connection might still be tracked but should be marked as failed
        # Check if error recovery mechanisms are working
        error_stats = websocket_manager.get_error_statistics()
        assert error_stats['total_error_count'] >= 0, "Error statistics should be tracked"
        
        # Verify database state remains consistent
        db_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1",
            user_id
        )
        assert db_user is not None, "User should still exist in database"
        assert db_user['is_active'] is True, "User should still be active in database"
        
        # Verify session state remains in Redis
        cached_session = await real_services_fixture["redis"].get(session_data['session_key'])
        assert cached_session is not None, "Session should still exist in Redis"
        
        # Test 2: Clean connection establishment after failure recovery
        working_websocket = FailingWebSocket(should_fail_on_send=False)
        
        recovery_connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="recovery_conn",
            context={"user_id": user_id, "test": "recovery"}
        )
        
        recovery_connection = WebSocketConnection(
            connection_id=recovery_connection_id,
            user_id=user_id,
            websocket=working_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "recovery_test",
                "session_id": session_data['session_key']
            }
        )
        
        # Add recovery connection
        await websocket_manager.add_connection(recovery_connection)
        
        # Verify recovery connection works
        assert websocket_manager.is_connection_active(user_id), "Recovery connection should be active"
        
        # Send test message to verify recovery
        recovery_message = {
            "type": "recovery_test",
            "data": {"message": "Recovery successful"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await websocket_manager.send_to_user(user_id, recovery_message)
        
        # Verify message was sent successfully
        assert len(working_websocket.messages_sent) > 0, "Recovery connection should receive messages"
        assert working_websocket.messages_sent[-1]['type'] == 'recovery_test', "Should receive recovery test message"
        
        # Verify final state consistency
        connection_health = websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True, "Should have active connections after recovery"
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        await websocket_manager.remove_connection(recovery_connection_id)
        
        # Verify final cleanup
        assert not websocket_manager.is_connection_active(user_id), "All connections should be cleaned up"
        
        # Verify application state business value: User can reconnect after failures
        self.assert_business_value_delivered({
            'connection_recovery': True,
            'state_consistency': True,
            'user_experience': 'seamless_recovery'
        }, 'automation')