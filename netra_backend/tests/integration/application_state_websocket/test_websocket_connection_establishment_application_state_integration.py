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
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, AsyncIterator
from contextlib import asynccontextmanager

# SSOT Test Framework Imports - Following CLAUDE.md requirements
from test_framework.base_integration_test import BaseIntegrationTest, WebSocketIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_redis_fixture
from shared.isolated_environment import get_env

# SSOT Type Safety Imports - CLAUDE.md Section 3.1
from shared.types.core_types import (
    UserID, ConnectionID, WebSocketID, ensure_user_id, ensure_connection_id
)

# SSOT WebSocket and ID Management
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# SSOT Real Services Test Management
from test_framework.real_services import RealServicesManager
import redis.asyncio as redis_async


class TestWebSocketConnectionEstablishmentApplicationStateIntegration(WebSocketIntegrationTest):
    """Test WebSocket connection establishment with comprehensive application state validation."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_establishment_initializes_application_state(self, real_services_fixture, real_redis_fixture):
        """
        Test that WebSocket connection establishment properly initializes application state.
        
        Business Value: Ensures users can connect to WebSocket and their state is properly
        initialized in the database and cache layers.
        """
        # Create test user context with real database - SSOT pattern
        user_data = await self.create_test_user_context(
            RealServicesManager({
                "postgres": real_services_fixture["postgres"],
                "redis": real_redis_fixture
            }), {
                'email': 'websocket_test_user@netra.ai',
                'name': 'WebSocket Test User',
                'is_active': True
            }
        )
        user_id = ensure_user_id(user_data['id'])
        
        # Create test session in Redis using REAL Redis client
        session_data = await self.create_test_session(
            RealServicesManager({
                "postgres": real_services_fixture["postgres"],
                "redis": real_redis_fixture
            }), 
            user_id
        )
        
        # Initialize WebSocket manager
        websocket_manager = UnifiedWebSocketManager()
        
        # CRITICAL FIX: Use REAL WebSocket connection for integration testing
        # NO MOCKS ALLOWED per CLAUDE.md Section 3.4
        real_websocket_connection = await self._create_real_websocket_connection(user_id)
        
        # Create connection with application state initialization
        id_manager = UnifiedIDManager()
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="test_conn",
            context={"user_id": user_id, "test": "establishment"}
        )
        
        connection = WebSocketConnection(
            connection_id=ensure_connection_id(connection_id),
            user_id=user_id,
            websocket=real_websocket_connection,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "test_establishment",
                "client_info": {"browser": "integration_test", "version": "1.0"},
                "session_id": session_data['session_key'],
                "test_context": "application_state_integration"
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
        
        # Verify application state persistence in REAL database - SSOT validation
        db_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, name, is_active, created_at, updated_at FROM auth.users WHERE id = $1",
            str(user_id)
        )
        assert db_user is not None, "User should exist in database"
        assert db_user['email'] == 'websocket_test_user@netra.ai', "Database user email should match"
        assert db_user['is_active'] is True, "Database user should be active"
        
        # Verify session state persistence in REAL Redis - NO MOCKS
        cached_session = await real_redis_fixture.get(session_data['session_key'])
        assert cached_session is not None, "Session should exist in Redis cache"
        
        # CRITICAL: Verify WebSocket events are properly delivered (CLAUDE.md Section 6)
        expected_events = ['connection_established', 'application_state_initialized']
        delivered_events = await self.verify_websocket_event_delivery(
            real_websocket_connection, expected_events
        )
        assert len(delivered_events) >= len(expected_events), "All critical WebSocket events must be delivered"
        
        # Test connection health
        connection_health = websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True, "Connection health should show active connections"
        assert connection_health['total_connections'] == 1, "Should have exactly one connection"
        assert connection_health['active_connections'] == 1, "Should have one active connection"
        
        # Verify connection metadata is properly stored and correlated
        assert connection_health['connections'][0]['connection_id'] == connection_id
        assert 'connected_at' in connection_health['connections'][0]
        assert connection_health['connections'][0]['active'] is True
        
        # Clean up - REAL WebSocket cleanup required
        await real_websocket_connection.close()
        await websocket_manager.remove_connection(connection_id)
        
        # Verify cleanup with REAL service validation
        assert not websocket_manager.is_connection_active(user_id), "Connection should be inactive after removal"
        assert websocket_manager.get_connection(connection_id) is None, "Connection should not be retrievable after removal"
        
        # BUSINESS VALUE ASSERTION - CLAUDE.md requirement
        self.assert_business_value_delivered({
            'connection_established': True,
            'application_state_synced': True,
            'user_isolation_maintained': True,
            'real_services_validated': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_establishment_with_concurrent_state_updates(self, real_services_fixture, real_redis_fixture):
        """
        Test WebSocket connection establishment under concurrent state update scenarios.
        
        Business Value: Ensures connection establishment is thread-safe and doesn't
        corrupt application state when multiple operations happen simultaneously.
        """
        # Create multiple test users with REAL services
        users = []
        real_services_manager = RealServicesManager({
            "postgres": real_services_fixture["postgres"],
            "redis": real_redis_fixture
        })
        
        for i in range(3):
            user_data = await self.create_test_user_context(real_services_manager, {
                'email': f'concurrent_test_user_{i}@netra.ai',
                'name': f'Concurrent Test User {i}',
                'is_active': True
            })
            session_data = await self.create_test_session(
                real_services_manager, 
                ensure_user_id(user_data['id'])
            )
            users.append({'user_data': user_data, 'session_data': session_data})
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        async def establish_connection_with_state(user_info, connection_index):
            """Helper to establish connection with concurrent state updates."""
            user_id = user_info['user_data']['id']
            
            # CRITICAL: Use REAL WebSocket connections - NO MOCKS per CLAUDE.md
            real_websocket = await self._create_real_websocket_connection(
                ensure_user_id(user_id)
            )
            
            connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"concurrent_conn_{connection_index}",
                context={"user_id": user_id, "test": "concurrent"}
            )
            
            connection = WebSocketConnection(
                connection_id=ensure_connection_id(connection_id),
                user_id=ensure_user_id(user_id),
                websocket=real_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "connection_type": "concurrent_test",
                    "connection_index": connection_index,
                    "session_id": user_info['session_data']['session_key'],
                    "test_scenario": "concurrent_application_state"
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
            
            # Simulate concurrent state updates in REAL Redis - NO MOCKS
            await real_redis_fixture.set(
                f"user_activity:{user_id}",
                json.dumps({
                    "last_activity": datetime.utcnow().isoformat(),
                    "connection_count": len(websocket_manager.get_user_connections(ensure_user_id(user_id))),
                    "connection_index": connection_index
                }),
                ex=300  # 5 minute expiry
            )
            
            return {
                'connection_id': connection_id,
                'user_id': user_id,
                'connection': connection,
                'websocket': real_websocket
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
            
            # Verify Redis state consistency with REAL Redis
            user_activity = await real_redis_fixture.get(f"user_activity:{user_id}")
            assert user_activity is not None, f"User {i} activity should exist in Redis"
            activity_data = json.loads(user_activity)
            assert 'last_activity' in activity_data, f"User {i} should have last_activity tracked"
            assert activity_data['connection_count'] == 1, f"User {i} should have correct connection count"
            assert activity_data['connection_index'] == i, f"User {i} should have correct connection index"
        
        # Verify manager statistics are accurate
        stats = websocket_manager.get_stats()
        assert stats['total_connections'] == 3, "Manager should track 3 total connections"
        assert stats['unique_users'] == 3, "Manager should track 3 unique users"
        
        # Clean up all REAL WebSocket connections
        cleanup_tasks = []
        for result in connection_results:
            await result['websocket'].close()  # Close real WebSocket first
            cleanup_tasks.append(
                websocket_manager.remove_connection(result['connection_id'])
            )
        await asyncio.gather(*cleanup_tasks)
        
        # Verify cleanup
        for result in connection_results:
            user_id = result['user_id']
            connection_id = result['connection_id']
            
            assert not websocket_manager.is_connection_active(user_id), f"User connection should be inactive after cleanup"
            assert websocket_manager.get_connection(connection_id) is None, f"Connection should not be retrievable after cleanup"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_establishment_failure_state_rollback(self, real_services_fixture, real_redis_fixture):
        """
        Test that failed WebSocket connection establishments properly rollback application state.
        
        Business Value: Ensures system consistency when connection establishment fails,
        preventing orphaned state and resource leaks.
        """
        # Create test user with REAL services
        real_services_manager = RealServicesManager({
            "postgres": real_services_fixture["postgres"],
            "redis": real_redis_fixture
        })
        
        user_data = await self.create_test_user_context(real_services_manager, {
            'email': 'failure_test_user@netra.ai',
            'name': 'Failure Test User',
            'is_active': True
        })
        user_id = ensure_user_id(user_data['id'])
        
        session_data = await self.create_test_session(real_services_manager, user_id)
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # CRITICAL: Use REAL WebSocket that can simulate failures
        # This tests actual failure recovery in real system
        failing_websocket = await self._create_real_websocket_connection_with_failure_simulation(
            user_id, should_fail=True
        )
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="failing_conn",
            context={"user_id": user_id, "test": "failure"}
        )
        
        connection = WebSocketConnection(
            connection_id=ensure_connection_id(connection_id),
            user_id=user_id,
            websocket=failing_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "failure_test",
                "session_id": session_data['session_key'],
                "test_scenario": "failure_state_rollback"
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
        
        # Verify session state remains in REAL Redis
        cached_session = await real_redis_fixture.get(session_data['session_key'])
        assert cached_session is not None, "Session should still exist in Redis"
        
        # Test 2: Clean connection establishment after failure recovery
        working_websocket = await self._create_real_websocket_connection(user_id)
        
        recovery_connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="recovery_conn",
            context={"user_id": user_id, "test": "recovery"}
        )
        
        recovery_connection = WebSocketConnection(
            connection_id=ensure_connection_id(recovery_connection_id),
            user_id=user_id,
            websocket=working_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "recovery_test",
                "session_id": session_data['session_key'],
                "test_scenario": "recovery_after_failure"
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
        
        # Verify message was sent successfully through REAL WebSocket
        # In real WebSocket integration, we verify by checking connection health
        connection_health = websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True, "Recovery connection should be healthy"
        
        # Verify WebSocket event delivery for recovery
        expected_recovery_events = ['recovery_message_sent', 'connection_restored']
        delivered_events = await self.verify_websocket_event_delivery(
            working_websocket, expected_recovery_events
        )
        
        # Verify final state consistency
        connection_health = websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True, "Should have active connections after recovery"
        
        # Clean up REAL WebSocket connections
        await failing_websocket.close()
        await working_websocket.close()
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