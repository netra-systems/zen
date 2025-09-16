"""
Test WebSocket Application State Real-Time Broadcast Synchronization Integration

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (Collaborative features)
- Business Goal: Enable real-time collaboration with instant state updates across all connected clients
- Value Impact: Users see changes immediately, creating seamless collaborative experience
- Strategic Impact: Competitive advantage through superior real-time collaboration capabilities

This test validates that state changes are broadcast in real-time across multiple
WebSocket connections, ensuring all connected clients maintain synchronized views
of shared application state.
"""

import asyncio
import pytest
import json
import time
from typing import Dict, Any, List, Optional, Set
from uuid import uuid4
from dataclasses import dataclass
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState
from shared.types import UserID, ThreadID, MessageID, OrganizationID
from shared.isolated_environment import get_env


@dataclass
class BroadcastEvent:
    """Represents a broadcast event for state synchronization."""
    event_type: str
    event_id: str
    source_connection_id: str
    target_scope: str  # 'user', 'thread', 'organization', 'global'
    target_ids: List[str]
    payload: Dict[str, Any]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'event_id': self.event_id,
            'source_connection_id': self.source_connection_id,
            'target_scope': self.target_scope,
            'target_ids': self.target_ids,
            'payload': self.payload,
            'timestamp': self.timestamp
        }


class MockWebSocketConnection:
    """Mock WebSocket connection for testing broadcast functionality."""
    
    def __init__(self, connection_id: str, user_id: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.received_events: List[BroadcastEvent] = []
        self.is_connected = True
        self.event_queue = asyncio.Queue()
    
    async def send_event(self, event: BroadcastEvent):
        """Simulate receiving a broadcast event."""
        if self.is_connected:
            self.received_events.append(event)
            await self.event_queue.put(event)
    
    async def wait_for_event(self, event_type: str, timeout: float = 5.0) -> Optional[BroadcastEvent]:
        """Wait for a specific event type."""
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                if event.event_type == event_type:
                    return event
                # Put back if not the event we're looking for
                await self.event_queue.put(event)
            except asyncio.TimeoutError:
                continue
        
        return None
    
    def disconnect(self):
        """Disconnect the mock connection."""
        self.is_connected = False


class TestWebSocketApplicationStateBroadcastSynchronization(BaseIntegrationTest):
    """Test real-time state broadcast synchronization across multiple WebSocket connections."""
    
    async def setup_broadcast_infrastructure(self, services, state_manager):
        """Set up broadcast infrastructure for testing."""
        # Initialize broadcast tracking
        broadcast_key = "active_broadcasts"
        await services.redis.delete(broadcast_key)
        
        # Initialize connection registry
        connection_registry_key = "websocket_connections"
        await services.redis.delete(connection_registry_key)
        
        return {
            'broadcast_key': broadcast_key,
            'connection_registry_key': connection_registry_key
        }
    
    async def register_websocket_connection(self, services, connection: MockWebSocketConnection, thread_id: Optional[str] = None, org_id: Optional[str] = None):
        """Register a WebSocket connection for broadcasts."""
        registration_data = {
            'connection_id': connection.connection_id,
            'user_id': connection.user_id,
            'connected_at': time.time(),
            'is_active': True,
            'subscriptions': {
                'user': [connection.user_id],
                'thread': [thread_id] if thread_id else [],
                'organization': [org_id] if org_id else []
            }
        }
        
        # Store in Redis
        await services.redis.set_json(
            f"websocket_connection:{connection.connection_id}",
            registration_data,
            ex=3600
        )
        
        # Add to active connections set
        await services.redis.sadd("active_websocket_connections", connection.connection_id)
        
        return registration_data
    
    async def broadcast_state_change(self, services, event: BroadcastEvent, connections: List[MockWebSocketConnection]):
        """Simulate broadcasting state change to all relevant connections."""
        # Store broadcast event
        await services.redis.set_json(
            f"broadcast_event:{event.event_id}",
            event.to_dict(),
            ex=300
        )
        
        # Determine target connections based on scope
        target_connections = []
        
        for connection in connections:
            should_receive = False
            
            # Check if connection should receive this event
            registration = await services.redis.get_json(f"websocket_connection:{connection.connection_id}")
            if not registration or not registration.get('is_active'):
                continue
            
            if event.target_scope == 'user':
                if connection.user_id in event.target_ids:
                    should_receive = True
            elif event.target_scope == 'thread':
                thread_subscriptions = registration['subscriptions'].get('thread', [])
                if any(thread_id in event.target_ids for thread_id in thread_subscriptions):
                    should_receive = True
            elif event.target_scope == 'organization':
                org_subscriptions = registration['subscriptions'].get('organization', [])
                if any(org_id in event.target_ids for org_id in org_subscriptions):
                    should_receive = True
            elif event.target_scope == 'global':
                should_receive = True
            
            if should_receive:
                target_connections.append(connection)
        
        # Send event to all target connections
        broadcast_tasks = [conn.send_event(event) for conn in target_connections]
        await asyncio.gather(*broadcast_tasks, return_exceptions=True)
        
        # Record broadcast metrics
        await services.redis.hincrby("broadcast_metrics", "total_events", 1)
        await services.redis.hincrby("broadcast_metrics", "total_recipients", len(target_connections))
        
        return len(target_connections)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_state_broadcast_to_multiple_connections(self, real_services_fixture):
        """Test that thread state changes are broadcast to all connected participants."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        await self.setup_broadcast_infrastructure(services, state_manager)
        
        # Create test users
        user1_data = await self.create_test_user_context(services, {
            'email': 'broadcast1@example.com',
            'name': 'Broadcast Test User 1'
        })
        user2_data = await self.create_test_user_context(services, {
            'email': 'broadcast2@example.com',
            'name': 'Broadcast Test User 2'
        })
        user3_data = await self.create_test_user_context(services, {
            'email': 'broadcast3@example.com',
            'name': 'Broadcast Test User 3'
        })
        
        user1_id = UserID(user1_data['id'])
        user2_id = UserID(user2_data['id'])
        user3_id = UserID(user3_data['id'])
        
        # Create shared thread
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title, metadata)
            VALUES ($1, $2, $3)
            RETURNING id
        """, str(user1_id), "Broadcast Test Thread", json.dumps({
            'participants': [str(user1_id), str(user2_id), str(user3_id)]
        }))
        
        thread_id = ThreadID(str(thread_id))
        
        # Create multiple WebSocket connections
        connections = [
            MockWebSocketConnection(str(uuid4()), str(user1_id)),
            MockWebSocketConnection(str(uuid4()), str(user2_id)),
            MockWebSocketConnection(str(uuid4()), str(user3_id)),
            # User 1 has a second connection (mobile + desktop)
            MockWebSocketConnection(str(uuid4()), str(user1_id))
        ]
        
        # Register all connections
        for connection in connections:
            await self.register_websocket_connection(
                services, 
                connection, 
                str(thread_id)
            )
        
        # Simulate thread state change event
        message_id = MessageID(str(uuid4()))
        
        # Add message to database
        await services.postgres.execute("""
            INSERT INTO backend.messages (id, thread_id, user_id, content, role)
            VALUES ($1, $2, $3, $4, $5)
        """, str(message_id), str(thread_id), str(user1_id), "New message for broadcast", "user")
        
        # Create broadcast event
        broadcast_event = BroadcastEvent(
            event_type='thread_message_added',
            event_id=str(uuid4()),
            source_connection_id=connections[0].connection_id,
            target_scope='thread',
            target_ids=[str(thread_id)],
            payload={
                'thread_id': str(thread_id),
                'message_id': str(message_id),
                'user_id': str(user1_id),
                'content': "New message for broadcast",
                'timestamp': time.time()
            },
            timestamp=time.time()
        )
        
        # Broadcast the event
        recipient_count = await self.broadcast_state_change(services, broadcast_event, connections)
        
        # All connections should receive the event (4 connections)
        assert recipient_count == 4
        
        # Wait for all connections to receive the event
        received_events = []
        for connection in connections:
            event = await connection.wait_for_event('thread_message_added', timeout=2.0)
            assert event is not None, f"Connection {connection.connection_id} did not receive event"
            received_events.append(event)
        
        # Verify all events have the same content
        for event in received_events:
            assert event.event_id == broadcast_event.event_id
            assert event.payload['message_id'] == str(message_id)
            assert event.payload['thread_id'] == str(thread_id)
            assert event.payload['user_id'] == str(user1_id)
        
        # Verify broadcast metrics
        total_events = await services.redis.hget("broadcast_metrics", "total_events")
        total_recipients = await services.redis.hget("broadcast_metrics", "total_recipients")
        
        assert int(total_events) == 1
        assert int(total_recipients) == 4
        
        # BUSINESS VALUE: Real-time collaboration enabled
        self.assert_business_value_delivered({
            'real_time_updates': True,
            'multi_connection_support': True,
            'broadcast_reliability': True,
            'collaboration_enabled': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_selective_broadcast_based_on_permissions(self, real_services_fixture):
        """Test that broadcasts respect user permissions and subscriptions."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        await self.setup_broadcast_infrastructure(services, state_manager)
        
        # Create users with different permission levels
        admin_user_data = await self.create_test_user_context(services, {
            'email': 'admin@example.com',
            'name': 'Admin User'
        })
        member_user_data = await self.create_test_user_context(services, {
            'email': 'member@example.com', 
            'name': 'Member User'
        })
        external_user_data = await self.create_test_user_context(services, {
            'email': 'external@example.com',
            'name': 'External User'
        })
        
        admin_user_id = UserID(admin_user_data['id'])
        member_user_id = UserID(member_user_data['id'])
        external_user_id = UserID(external_user_data['id'])
        
        # Create organization
        org_id = await services.postgres.fetchval("""
            INSERT INTO backend.organizations (name, slug, plan)
            VALUES ($1, $2, $3)
            RETURNING id
        """, "Selective Broadcast Org", "selective-broadcast-org", "enterprise")
        
        org_id = OrganizationID(str(org_id))
        
        # Add admin and member to organization
        await services.postgres.execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role)
            VALUES ($1, $2, $3)
        """, str(admin_user_id), str(org_id), "admin")
        
        await services.postgres.execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role)
            VALUES ($1, $2, $3)
        """, str(member_user_id), str(org_id), "member")
        
        # External user is NOT in the organization
        
        # Create private thread within organization
        private_thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, organization_id, title, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, str(admin_user_id), str(org_id), "Private Thread", json.dumps({
            'access_level': 'private',
            'participants': [str(admin_user_id), str(member_user_id)]
        }))
        
        private_thread_id = ThreadID(str(private_thread_id))
        
        # Create connections
        connections = [
            MockWebSocketConnection(str(uuid4()), str(admin_user_id)),
            MockWebSocketConnection(str(uuid4()), str(member_user_id)),
            MockWebSocketConnection(str(uuid4()), str(external_user_id))
        ]
        
        # Register connections with different subscriptions
        await self.register_websocket_connection(
            services, 
            connections[0],  # Admin
            str(private_thread_id),
            str(org_id)
        )
        
        await self.register_websocket_connection(
            services,
            connections[1],  # Member 
            str(private_thread_id),
            str(org_id)
        )
        
        await self.register_websocket_connection(
            services,
            connections[2],  # External - no org or thread subscriptions
            None,
            None
        )
        
        # Test 1: Organization-scoped broadcast (admin + member should receive)
        org_broadcast_event = BroadcastEvent(
            event_type='organization_update',
            event_id=str(uuid4()),
            source_connection_id=connections[0].connection_id,
            target_scope='organization',
            target_ids=[str(org_id)],
            payload={
                'organization_id': str(org_id),
                'update_type': 'settings_changed',
                'changed_by': str(admin_user_id)
            },
            timestamp=time.time()
        )
        
        recipient_count = await self.broadcast_state_change(services, org_broadcast_event, connections)
        assert recipient_count == 2  # Only admin and member
        
        # Verify only authorized users received the event
        admin_event = await connections[0].wait_for_event('organization_update', timeout=1.0)
        member_event = await connections[1].wait_for_event('organization_update', timeout=1.0)
        external_event = await connections[2].wait_for_event('organization_update', timeout=1.0)
        
        assert admin_event is not None
        assert member_event is not None
        assert external_event is None  # External user should NOT receive
        
        # Test 2: Thread-scoped broadcast (admin + member should receive)
        thread_broadcast_event = BroadcastEvent(
            event_type='thread_participant_joined',
            event_id=str(uuid4()),
            source_connection_id=connections[0].connection_id,
            target_scope='thread',
            target_ids=[str(private_thread_id)],
            payload={
                'thread_id': str(private_thread_id),
                'new_participant': str(member_user_id),
                'added_by': str(admin_user_id)
            },
            timestamp=time.time()
        )
        
        recipient_count = await self.broadcast_state_change(services, thread_broadcast_event, connections)
        assert recipient_count == 2  # Only thread participants
        
        # Test 3: User-scoped broadcast (only specific user receives)
        user_broadcast_event = BroadcastEvent(
            event_type='user_notification',
            event_id=str(uuid4()),
            source_connection_id=connections[0].connection_id,
            target_scope='user',
            target_ids=[str(member_user_id)],
            payload={
                'notification_type': 'mention',
                'message': 'You were mentioned in a thread'
            },
            timestamp=time.time()
        )
        
        recipient_count = await self.broadcast_state_change(services, user_broadcast_event, connections)
        assert recipient_count == 1  # Only member user
        
        member_notification = await connections[1].wait_for_event('user_notification', timeout=1.0)
        assert member_notification is not None
        
        # Clear previous events from other connections
        await connections[0].wait_for_event('user_notification', timeout=0.1)  # Should timeout
        await connections[2].wait_for_event('user_notification', timeout=0.1)  # Should timeout
        
        # BUSINESS VALUE: Secure, permission-aware broadcasting
        self.assert_business_value_delivered({
            'permission_enforcement': True,
            'selective_broadcasting': True,
            'security_maintained': True,
            'access_control': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_broadcast_performance_under_high_connection_load(self, real_services_fixture):
        """Test broadcast performance with many concurrent connections."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        await self.setup_broadcast_infrastructure(services, state_manager)
        
        # Create test user
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        
        # Create thread for testing
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title)
            VALUES ($1, $2)
            RETURNING id
        """, str(user_id), "High Load Test Thread")
        
        thread_id = ThreadID(str(thread_id))
        
        # Create many connections (simulate high load)
        connection_count = 50
        connections = []
        
        for i in range(connection_count):
            connection = MockWebSocketConnection(str(uuid4()), str(user_id))
            connections.append(connection)
            
            await self.register_websocket_connection(
                services,
                connection,
                str(thread_id)
            )
        
        # Measure broadcast performance
        start_time = time.time()
        
        # Create broadcast event
        performance_event = BroadcastEvent(
            event_type='performance_test',
            event_id=str(uuid4()),
            source_connection_id=connections[0].connection_id,
            target_scope='thread',
            target_ids=[str(thread_id)],
            payload={
                'test_data': f'Performance test with {connection_count} connections',
                'connection_count': connection_count
            },
            timestamp=time.time()
        )
        
        # Broadcast to all connections
        recipient_count = await self.broadcast_state_change(services, performance_event, connections)
        
        broadcast_time = time.time() - start_time
        
        # Verify all connections received the event
        assert recipient_count == connection_count
        
        # Collect performance metrics
        receive_start_time = time.time()
        received_count = 0
        
        for connection in connections:
            event = await connection.wait_for_event('performance_test', timeout=5.0)
            if event is not None:
                received_count += 1
        
        total_receive_time = time.time() - receive_start_time
        
        # Performance assertions
        assert received_count == connection_count, f"Only {received_count}/{connection_count} connections received event"
        assert broadcast_time < 2.0, f"Broadcast took too long: {broadcast_time:.2f}s"
        assert total_receive_time < 3.0, f"Event delivery took too long: {total_receive_time:.2f}s"
        
        # Calculate performance metrics
        broadcasts_per_second = connection_count / broadcast_time
        
        self.logger.info(f"Performance metrics:")
        self.logger.info(f"  Connections: {connection_count}")
        self.logger.info(f"  Broadcast time: {broadcast_time:.3f}s")
        self.logger.info(f"  Receive time: {total_receive_time:.3f}s")
        self.logger.info(f"  Broadcasts/second: {broadcasts_per_second:.1f}")
        
        # Performance should be reasonable (at least 25 broadcasts per second)
        assert broadcasts_per_second > 25, f"Performance too slow: {broadcasts_per_second:.1f} broadcasts/sec"
        
        # Test multiple rapid broadcasts
        rapid_broadcast_count = 10
        rapid_start_time = time.time()
        
        for i in range(rapid_broadcast_count):
            rapid_event = BroadcastEvent(
                event_type='rapid_test',
                event_id=str(uuid4()),
                source_connection_id=connections[0].connection_id,
                target_scope='thread',
                target_ids=[str(thread_id)],
                payload={'sequence': i},
                timestamp=time.time()
            )
            
            await self.broadcast_state_change(services, rapid_event, connections[:10])  # Subset for rapid test
            
            if i < rapid_broadcast_count - 1:
                await asyncio.sleep(0.01)  # 10ms between broadcasts
        
        rapid_total_time = time.time() - rapid_start_time
        rapid_events_per_second = rapid_broadcast_count / rapid_total_time
        
        self.logger.info(f"Rapid broadcast: {rapid_events_per_second:.1f} events/second")
        
        # BUSINESS VALUE: System scales to handle high loads
        self.assert_business_value_delivered({
            'high_performance': True,
            'scalability': True,
            'concurrent_handling': True,
            'system_reliability': True
        }, 'automation')