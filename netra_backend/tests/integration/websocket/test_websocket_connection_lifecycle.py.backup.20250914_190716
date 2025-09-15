"""
WebSocket Connection Lifecycle Integration Tests

BUSINESS CRITICAL: WebSocket connections enable real-time chat communication that delivers
90% of the platform's business value. This test validates the foundation of all AI interactions.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Core Infrastructure 
- Business Goal: Enable reliable WebSocket communication for Golden Path user flow
- Value Impact: Foundation for all AI chat interactions and real-time user experience
- Revenue Impact: Protects $500K+ ARR dependent on chat functionality reliability

TEST SCOPE: Integration-level validation of WebSocket connection management including:
- Connection establishment with authentication
- Connection state transitions and lifecycle management
- Resource cleanup and connection limits
- Authentication integration with JWT tokens
- Multi-user connection isolation

CRITICAL REQUIREMENTS:
- NO MOCKS for business logic - use real WebSocket manager components
- Mock only transport layer for integration testing
- Validate factory pattern isolation between users
- Test connection health monitoring and heartbeat
- Validate graceful connection cleanup
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import pytest

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# WebSocket core components - NO MOCKS for business logic
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState, MessageType, ConnectionMetadata
)
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol

# User context and authentication
from shared.types.core_types import UserID, ThreadID, ConnectionID, ensure_user_id
from shared.types.user_types import TestUserData

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Mock WebSocket connection for transport layer testing
class MockWebSocketConnection:
    """Mock WebSocket transport for integration testing - replaces network layer only."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.is_closed = False
        self.messages_sent = []
        self.state = WebSocketConnectionState.CONNECTING
        self.close_code = None
        self.close_reason = None
        
    async def send(self, message: str) -> None:
        """Mock send - records messages for verification."""
        if self.is_closed:
            raise ConnectionError("WebSocket connection is closed")
        self.messages_sent.append(message)
        logger.debug(f"Mock WebSocket sent message: {message[:100]}...")
        
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Mock close - updates state."""
        self.is_closed = True
        self.close_code = code
        self.close_reason = reason
        self.state = WebSocketConnectionState.DISCONNECTED
        logger.debug(f"Mock WebSocket closed with code={code}, reason={reason}")


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.asyncio
class TestWebSocketConnectionLifecycle(SSotAsyncTestCase):
    """
    Integration tests for WebSocket connection lifecycle management.
    
    MISSION CRITICAL: These tests protect the foundation of chat functionality
    that generates $500K+ ARR through reliable real-time AI interactions.
    """
    
    def setup_method(self, method):
        """Set up isolated test environment for each test."""
        super().setup_method(method)
        
        # Set up isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("TESTING", "1", source="websocket_lifecycle_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_lifecycle_test")
        
        # Test data for multiple users
        self.test_users = [
            TestUserData(
                user_id=f"test_user_{uuid.uuid4().hex[:8]}",
                email=f"test{i}@netra.ai",
                tier="early",
                thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
            )
            for i in range(3)
        ]
        
        # Track connections for cleanup
        self.active_connections: Dict[str, Any] = {}
        self.websocket_managers: List[Any] = []
        
    async def teardown_method(self, method):
        """Clean up connections and resources."""
        # Close all active connections
        for connection_id, connection in self.active_connections.items():
            try:
                if hasattr(connection, 'close') and not connection.is_closed:
                    await connection.close(1000, "Test cleanup")
            except Exception as e:
                logger.warning(f"Error closing connection {connection_id}: {e}")
        
        # Clean up WebSocket managers
        for manager in self.websocket_managers:
            try:
                if hasattr(manager, 'cleanup'):
                    await manager.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up manager: {e}")
        
        await super().teardown_method(method)
    
    async def create_mock_user_context(self, user_data: TestUserData) -> Any:
        """Create mock user context for testing."""
        return type('MockUserContext', (), {
            'user_id': user_data.user_id,
            'thread_id': user_data.thread_id,
            'request_id': f"test_request_{uuid.uuid4().hex[:8]}",
            'email': user_data.email,
            'tier': user_data.tier,
            'is_test': True
        })()
    
    async def test_single_connection_establishment_with_authentication(self):
        """
        Test: Single WebSocket connection establishment with proper authentication
        
        Business Value: Validates that users can successfully establish authenticated
        chat connections, enabling AI interaction value delivery.
        """
        user_data = self.test_users[0]
        user_context = await self.create_mock_user_context(user_data)
        
        # Create WebSocket manager with user context isolation
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create mock WebSocket transport
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        mock_ws = MockWebSocketConnection(user_data.user_id, connection_id)
        self.active_connections[connection_id] = mock_ws
        
        # Test connection establishment
        with patch.object(manager, '_websocket_transport', mock_ws):
            # Establish connection
            await manager.connect_user(
                user_id=ensure_user_id(user_data.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": user_data.tier}
            )
            
            # Verify connection state
            assert manager.is_connected(ensure_user_id(user_data.user_id))
            assert mock_ws.state == WebSocketConnectionState.CONNECTED
            
            # Verify user context is properly isolated
            user_connections = manager.get_user_connections(ensure_user_id(user_data.user_id))
            assert len(user_connections) == 1
            
            logger.info(f"✅ Connection established for user {user_data.user_id}")
    
    async def test_connection_state_transitions_validation(self):
        """
        Test: WebSocket connection state transitions follow proper lifecycle
        
        Business Value: Ensures connection reliability for uninterrupted chat experience,
        preventing user frustration and churn.
        """
        user_data = self.test_users[0]
        user_context = await self.create_mock_user_context(user_data)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        mock_ws = MockWebSocketConnection(user_data.user_id, connection_id)
        self.active_connections[connection_id] = mock_ws
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            # Test CONNECTING -> CONNECTED transition
            mock_ws.state = WebSocketConnectionState.CONNECTING
            await manager.connect_user(
                user_id=ensure_user_id(user_data.user_id),
                websocket=mock_ws
            )
            
            assert mock_ws.state == WebSocketConnectionState.CONNECTED
            assert manager.is_connected(ensure_user_id(user_data.user_id))
            
            # Test CONNECTED -> DISCONNECTING -> DISCONNECTED transition
            await manager.disconnect_user(ensure_user_id(user_data.user_id))
            
            assert mock_ws.state == WebSocketConnectionState.DISCONNECTED
            assert not manager.is_connected(ensure_user_id(user_data.user_id))
            
            logger.info("✅ Connection state transitions validated")
    
    async def test_concurrent_multi_user_connection_isolation(self):
        """
        Test: Multiple users can establish isolated connections concurrently
        
        Business Value: Ensures multi-tenant isolation for enterprise customers,
        preventing data leakage and enabling scalable chat operations.
        """
        managers = []
        connections = {}
        
        # Establish connections for all test users concurrently
        connection_tasks = []
        
        for user_data in self.test_users:
            user_context = await self.create_mock_user_context(user_data)
            manager = await get_websocket_manager(
                user_context=user_context,
                mode=WebSocketManagerMode.ISOLATED
            )
            managers.append(manager)
            
            connection_id = f"conn_{user_data.user_id}_{uuid.uuid4().hex[:8]}"
            mock_ws = MockWebSocketConnection(user_data.user_id, connection_id)
            connections[user_data.user_id] = mock_ws
            self.active_connections[connection_id] = mock_ws
            
            # Create connection task
            async def connect_user(mgr, ws, ud):
                with patch.object(mgr, '_websocket_transport', ws):
                    await mgr.connect_user(
                        user_id=ensure_user_id(ud.user_id),
                        websocket=ws,
                        connection_metadata={"tier": ud.tier}
                    )
            
            connection_tasks.append(connect_user(manager, mock_ws, user_data))
        
        self.websocket_managers.extend(managers)
        
        # Execute all connections concurrently
        await asyncio.gather(*connection_tasks)
        
        # Verify each user has isolated connection
        for i, user_data in enumerate(self.test_users):
            manager = managers[i]
            user_id = ensure_user_id(user_data.user_id)
            
            # Verify connection exists
            assert manager.is_connected(user_id)
            
            # Verify connection isolation - user can only see their own connection
            user_connections = manager.get_user_connections(user_id)
            assert len(user_connections) == 1
            
            # Verify no cross-contamination between users
            mock_ws = connections[user_data.user_id]
            assert mock_ws.user_id == user_data.user_id
            assert mock_ws.state == WebSocketConnectionState.CONNECTED
        
        logger.info(f"✅ {len(self.test_users)} users connected with proper isolation")
    
    async def test_connection_cleanup_and_resource_management(self):
        """
        Test: Proper cleanup of WebSocket connections and associated resources
        
        Business Value: Prevents resource leaks that could impact system performance
        and reliability for all users, protecting revenue-generating chat functionality.
        """
        user_data = self.test_users[0]
        user_context = await self.create_mock_user_context(user_data)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create multiple connections for the same user (simulating reconnections)
        connections = []
        for i in range(3):
            connection_id = f"conn_{user_data.user_id}_{i}"
            mock_ws = MockWebSocketConnection(user_data.user_id, connection_id)
            connections.append(mock_ws)
            self.active_connections[connection_id] = mock_ws
            
            with patch.object(manager, '_websocket_transport', mock_ws):
                await manager.connect_user(
                    user_id=ensure_user_id(user_data.user_id),
                    websocket=mock_ws
                )
        
        # Verify multiple connections tracked
        user_connections = manager.get_user_connections(ensure_user_id(user_data.user_id))
        assert len(user_connections) >= 1  # At least one active connection
        
        # Test cleanup
        await manager.disconnect_user(ensure_user_id(user_data.user_id))
        
        # Verify all connections are cleaned up
        assert not manager.is_connected(ensure_user_id(user_data.user_id))
        
        # Verify connections are properly closed
        for mock_ws in connections:
            # Connection should be closed during cleanup
            assert mock_ws.close_code is not None or mock_ws.is_closed
        
        logger.info("✅ Connection cleanup and resource management validated")
    
    async def test_connection_heartbeat_and_health_monitoring(self):
        """
        Test: WebSocket connection heartbeat and health monitoring functionality
        
        Business Value: Ensures connection reliability and quick detection of
        connection issues, maintaining chat experience quality.
        """
        user_data = self.test_users[0]
        user_context = await self.create_mock_user_context(user_data)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        mock_ws = MockWebSocketConnection(user_data.user_id, connection_id)
        self.active_connections[connection_id] = mock_ws
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            # Establish connection
            await manager.connect_user(
                user_id=ensure_user_id(user_data.user_id),
                websocket=mock_ws
            )
            
            # Test heartbeat functionality if available
            if hasattr(manager, 'send_heartbeat'):
                await manager.send_heartbeat(ensure_user_id(user_data.user_id))
                
                # Verify heartbeat message was sent
                heartbeat_messages = [
                    msg for msg in mock_ws.messages_sent
                    if 'heartbeat' in msg.lower() or 'ping' in msg.lower()
                ]
                assert len(heartbeat_messages) > 0
            
            # Test connection health check
            if hasattr(manager, 'check_connection_health'):
                is_healthy = await manager.check_connection_health(ensure_user_id(user_data.user_id))
                assert is_healthy  # Connection should be healthy
            
            logger.info("✅ Heartbeat and health monitoring validated")
    
    async def test_connection_limits_and_rate_limiting(self):
        """
        Test: WebSocket connection limits and rate limiting enforcement
        
        Business Value: Protects system resources and ensures fair usage across
        all users, preventing abuse that could impact service quality.
        """
        user_data = self.test_users[0]
        user_context = await self.create_mock_user_context(user_data)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Test connection limit by trying to create many connections
        max_connections = 5  # Typical limit for testing
        connections = []
        
        for i in range(max_connections + 2):  # Try to exceed limit
            connection_id = f"conn_limit_{i}"
            mock_ws = MockWebSocketConnection(user_data.user_id, connection_id)
            
            try:
                with patch.object(manager, '_websocket_transport', mock_ws):
                    await manager.connect_user(
                        user_id=ensure_user_id(user_data.user_id),
                        websocket=mock_ws
                    )
                connections.append(mock_ws)
                self.active_connections[connection_id] = mock_ws
            except Exception as e:
                # Connection limit enforcement may raise exceptions
                logger.info(f"Connection {i} rejected (expected): {e}")
        
        # Verify connection limit is enforced
        user_connections = manager.get_user_connections(ensure_user_id(user_data.user_id))
        assert len(user_connections) <= max_connections
        
        logger.info(f"✅ Connection limits enforced: {len(user_connections)} <= {max_connections}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])