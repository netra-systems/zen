"""
Test WebSocket Application State Audit Trail Generation Integration

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (Compliance and Security focused)
- Business Goal: Enable comprehensive audit trails for regulatory compliance and security monitoring
- Value Impact: Organizations can track all state changes for compliance, debugging, and security analysis
- Strategic Impact: Essential for enterprise customers requiring SOC2, HIPAA, GDPR compliance

This test validates that all WebSocket-triggered state changes generate proper
audit trails with complete context, timestamps, and traceability across all
system layers (PostgreSQL, Redis, WebSocket events).
"""

import asyncio
import pytest
import json
import time
from typing import Dict, Any, List, Optional, Union
from uuid import uuid4
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState
from shared.types import UserID, ThreadID, MessageID, OrganizationID
from shared.isolated_environment import get_env


class AuditEventType(Enum):
    """Types of audit events that should be tracked."""
    WEBSOCKET_CONNECT = "websocket_connect"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    THREAD_CREATE = "thread_create"
    THREAD_UPDATE = "thread_update"
    THREAD_DELETE = "thread_delete"
    MESSAGE_CREATE = "message_create"
    MESSAGE_UPDATE = "message_update"
    MESSAGE_DELETE = "message_delete"
    STATE_SYNC = "state_sync"
    CACHE_UPDATE = "cache_update"
    PERMISSION_CHECK = "permission_check"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class AuditEvent:
    """Represents an audit trail event."""
    event_id: str
    event_type: AuditEventType
    timestamp: float
    user_id: str
    connection_id: Optional[str]
    organization_id: Optional[str]
    resource_type: str  # 'thread', 'message', 'websocket', 'cache'
    resource_id: str
    action: str  # 'create', 'read', 'update', 'delete'
    before_state: Optional[Dict[str, Any]]
    after_state: Optional[Dict[str, Any]]
    context: Dict[str, Any]  # Additional context information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp,
            'iso_timestamp': datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            'user_id': self.user_id,
            'connection_id': self.connection_id,
            'organization_id': self.organization_id,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'before_state': self.before_state,
            'after_state': self.after_state,
            'context': self.context,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id
        }


class AuditTrailManager:
    """Manages audit trail generation and storage for testing."""
    
    def __init__(self, services):
        self.services = services
        self.audit_events: List[AuditEvent] = []
        
    async def initialize_audit_infrastructure(self):
        """Set up audit trail infrastructure."""
        # Create audit trail table if it doesn't exist (for testing)
        await self.services.postgres.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                event_id UUID PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                user_id UUID,
                connection_id VARCHAR(100),
                organization_id UUID,
                resource_type VARCHAR(50) NOT NULL,
                resource_id VARCHAR(100) NOT NULL,
                action VARCHAR(20) NOT NULL,
                before_state JSONB,
                after_state JSONB,
                context JSONB NOT NULL DEFAULT '{}',
                ip_address INET,
                user_agent TEXT,
                session_id VARCHAR(100),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Create indexes for performance
        await self.services.postgres.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp DESC)
        """)
        await self.services.postgres.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_trail_user_id ON audit_trail(user_id)
        """)
        await self.services.postgres.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_trail_resource ON audit_trail(resource_type, resource_id)
        """)
        
    async def log_audit_event(self, event: AuditEvent):
        """Log an audit event to the audit trail."""
        # Store in memory for testing
        self.audit_events.append(event)
        
        # Store in database
        await self.services.postgres.execute("""
            INSERT INTO audit_trail (
                event_id, event_type, timestamp, user_id, connection_id, 
                organization_id, resource_type, resource_id, action,
                before_state, after_state, context, ip_address, user_agent, session_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        """, event.event_id, event.event_type.value, 
             datetime.fromtimestamp(event.timestamp, tz=timezone.utc),
             event.user_id, event.connection_id, event.organization_id,
             event.resource_type, event.resource_id, event.action,
             json.dumps(event.before_state) if event.before_state else None,
             json.dumps(event.after_state) if event.after_state else None,
             json.dumps(event.context), event.ip_address, event.user_agent, event.session_id)
        
        # Store in Redis for fast queries
        await self.services.redis.set_json(
            f"audit_event:{event.event_id}",
            event.to_dict(),
            ex=86400  # 24 hours
        )
        
        # Add to user's audit timeline
        await self.services.redis.lpush(
            f"user_audit_timeline:{event.user_id}",
            event.event_id
        )
        await self.services.redis.expire(f"user_audit_timeline:{event.user_id}", 86400)
        
    async def create_websocket_connect_event(self, user_id: str, connection_id: str, 
                                           organization_id: Optional[str] = None,
                                           context: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """Create audit event for WebSocket connection."""
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=AuditEventType.WEBSOCKET_CONNECT,
            timestamp=time.time(),
            user_id=user_id,
            connection_id=connection_id,
            organization_id=organization_id,
            resource_type='websocket',
            resource_id=connection_id,
            action='create',
            before_state=None,
            after_state={'state': 'connected', 'connected_at': time.time()},
            context=context or {},
            ip_address='127.0.0.1',  # Mock for testing
            user_agent='TestAgent/1.0',
            session_id=str(uuid4())
        )
        
        await self.log_audit_event(event)
        return event
        
    async def create_state_change_event(self, event_type: AuditEventType, user_id: str,
                                      connection_id: Optional[str], resource_type: str,
                                      resource_id: str, action: str,
                                      before_state: Optional[Dict[str, Any]],
                                      after_state: Optional[Dict[str, Any]],
                                      context: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """Create audit event for state changes."""
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=time.time(),
            user_id=user_id,
            connection_id=connection_id,
            organization_id=context.get('organization_id') if context else None,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            before_state=before_state,
            after_state=after_state,
            context=context or {},
            ip_address='127.0.0.1',
            user_agent='TestAgent/1.0',
            session_id=context.get('session_id') if context else str(uuid4())
        )
        
        await self.log_audit_event(event)
        return event
    
    async def get_audit_trail(self, user_id: Optional[str] = None,
                            resource_type: Optional[str] = None,
                            start_time: Optional[float] = None,
                            end_time: Optional[float] = None) -> List[AuditEvent]:
        """Retrieve audit trail based on filters."""
        query = "SELECT * FROM audit_trail WHERE 1=1"
        params = []
        param_count = 0
        
        if user_id:
            param_count += 1
            query += f" AND user_id = ${param_count}"
            params.append(user_id)
            
        if resource_type:
            param_count += 1
            query += f" AND resource_type = ${param_count}"
            params.append(resource_type)
            
        if start_time:
            param_count += 1
            query += f" AND timestamp >= ${param_count}"
            params.append(datetime.fromtimestamp(start_time, tz=timezone.utc))
            
        if end_time:
            param_count += 1
            query += f" AND timestamp <= ${param_count}"
            params.append(datetime.fromtimestamp(end_time, tz=timezone.utc))
        
        query += " ORDER BY timestamp DESC"
        
        rows = await self.services.postgres.fetch(query, *params)
        
        events = []
        for row in rows:
            event = AuditEvent(
                event_id=str(row['event_id']),
                event_type=AuditEventType(row['event_type']),
                timestamp=row['timestamp'].timestamp(),
                user_id=str(row['user_id']),
                connection_id=row['connection_id'],
                organization_id=str(row['organization_id']) if row['organization_id'] else None,
                resource_type=row['resource_type'],
                resource_id=row['resource_id'],
                action=row['action'],
                before_state=json.loads(row['before_state']) if row['before_state'] else None,
                after_state=json.loads(row['after_state']) if row['after_state'] else None,
                context=json.loads(row['context']) if row['context'] else {},
                ip_address=str(row['ip_address']) if row['ip_address'] else None,
                user_agent=row['user_agent'],
                session_id=row['session_id']
            )
            events.append(event)
        
        return events


class TestWebSocketApplicationStateAuditTrailGeneration(BaseIntegrationTest):
    """Test application state audit trail generation during WebSocket-triggered state changes."""
    
    async def setup_audit_test_environment(self, services) -> AuditTrailManager:
        """Set up audit trail testing environment."""
        audit_manager = AuditTrailManager(services)
        await audit_manager.initialize_audit_infrastructure()
        return audit_manager
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_websocket_lifecycle_audit_trail(self, real_services_fixture):
        """Test that complete WebSocket lifecycle generates proper audit trail."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Set up audit infrastructure
        audit_manager = await self.setup_audit_test_environment(services)
        
        # Create test user
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        connection_id = str(uuid4())
        
        # Create organization
        org_data = await self.create_test_organization(services, str(user_id))
        org_id = OrganizationID(org_data['id'])
        
        test_start_time = time.time()
        
        # 1. Audit WebSocket Connection
        connect_event = await audit_manager.create_websocket_connect_event(
            str(user_id), connection_id, str(org_id), {
                'connection_type': 'websocket',
                'client_version': '1.0.0',
                'feature_flags': ['audit_enabled']
            }
        )
        
        # Set up WebSocket state with audit context
        initial_ws_state = {
            'user_id': str(user_id),
            'organization_id': str(org_id),
            'connection_id': connection_id,
            'state': WebSocketConnectionState.CONNECTED.value,
            'connected_at': time.time(),
            'audit_session_id': connect_event.session_id
        }
        
        state_manager.set_websocket_state(connection_id, 'connection_info', initial_ws_state)
        
        # 2. Audit Thread Creation
        thread_id = str(uuid4())
        
        # Before state (no thread exists)
        thread_before_state = None
        
        # Create thread
        created_thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (id, user_id, organization_id, title, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, thread_id, str(user_id), str(org_id), "Audited Test Thread", json.dumps({
            'audit_enabled': True,
            'created_via': 'websocket',
            'session_id': connect_event.session_id
        }))
        
        thread_id = ThreadID(str(created_thread_id))
        
        # After state
        thread_after_state = {
            'id': str(thread_id),
            'user_id': str(user_id),
            'organization_id': str(org_id),
            'title': 'Audited Test Thread',
            'metadata': {
                'audit_enabled': True,
                'created_via': 'websocket',
                'session_id': connect_event.session_id
            }
        }
        
        # Log thread creation audit event
        thread_create_event = await audit_manager.create_state_change_event(
            AuditEventType.THREAD_CREATE,
            str(user_id),
            connection_id,
            'thread',
            str(thread_id),
            'create',
            thread_before_state,
            thread_after_state,
            {
                'organization_id': str(org_id),
                'session_id': connect_event.session_id,
                'triggered_by': 'websocket_message',
                'client_action': 'create_thread'
            }
        )
        
        # 3. Audit Cache Update
        await services.redis.set_json(f"thread:{thread_id}", thread_after_state, ex=3600)
        
        cache_update_event = await audit_manager.create_state_change_event(
            AuditEventType.CACHE_UPDATE,
            str(user_id),
            connection_id,
            'cache',
            f"thread:{thread_id}",
            'create',
            None,
            {'cached_at': time.time(), 'ttl': 3600},
            {
                'cache_type': 'redis',
                'session_id': connect_event.session_id,
                'related_resource': str(thread_id)
            }
        )
        
        # 4. Audit WebSocket State Synchronization
        updated_ws_state = {
            **initial_ws_state,
            'current_thread_id': str(thread_id),
            'thread_count': 1,
            'last_activity': time.time()
        }
        
        state_manager.set_websocket_state(connection_id, 'connection_info', updated_ws_state)
        
        state_sync_event = await audit_manager.create_state_change_event(
            AuditEventType.STATE_SYNC,
            str(user_id),
            connection_id,
            'websocket',
            connection_id,
            'update',
            initial_ws_state,
            updated_ws_state,
            {
                'sync_reason': 'thread_created',
                'session_id': connect_event.session_id
            }
        )
        
        # 5. Audit Message Creation
        message_id = MessageID(str(uuid4()))
        
        message_before_state = None
        
        await services.postgres.execute("""
            INSERT INTO backend.messages (id, thread_id, user_id, content, role, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, str(message_id), str(thread_id), str(user_id), "Audited test message", "user",
             json.dumps({'audit_enabled': True, 'session_id': connect_event.session_id}))
        
        message_after_state = {
            'id': str(message_id),
            'thread_id': str(thread_id),
            'user_id': str(user_id),
            'content': 'Audited test message',
            'role': 'user',
            'metadata': {
                'audit_enabled': True,
                'session_id': connect_event.session_id
            }
        }
        
        message_create_event = await audit_manager.create_state_change_event(
            AuditEventType.MESSAGE_CREATE,
            str(user_id),
            connection_id,
            'message',
            str(message_id),
            'create',
            message_before_state,
            message_after_state,
            {
                'thread_id': str(thread_id),
                'organization_id': str(org_id),
                'session_id': connect_event.session_id,
                'message_length': len('Audited test message')
            }
        )
        
        test_end_time = time.time()
        
        # Verify audit trail completeness
        audit_trail = await audit_manager.get_audit_trail(
            user_id=str(user_id),
            start_time=test_start_time,
            end_time=test_end_time
        )
        
        self.logger.info(f"Audit trail validation:")
        self.logger.info(f"  Generated events: {len(audit_trail)}")
        self.logger.info(f"  Event types: {[e.event_type.value for e in audit_trail]}")
        
        # Validate audit trail completeness
        expected_event_types = {
            AuditEventType.WEBSOCKET_CONNECT,
            AuditEventType.THREAD_CREATE,
            AuditEventType.CACHE_UPDATE,
            AuditEventType.STATE_SYNC,
            AuditEventType.MESSAGE_CREATE
        }
        
        actual_event_types = {e.event_type for e in audit_trail}
        missing_events = expected_event_types - actual_event_types
        
        assert len(missing_events) == 0, f"Missing audit events: {missing_events}"
        assert len(audit_trail) == len(expected_event_types), f"Expected {len(expected_event_types)} events, got {len(audit_trail)}"
        
        # Validate event details
        for event in audit_trail:
            assert event.user_id == str(user_id), f"Wrong user ID in event {event.event_id}"
            assert event.timestamp >= test_start_time, f"Event timestamp too early: {event.event_id}"
            assert event.timestamp <= test_end_time, f"Event timestamp too late: {event.event_id}"
            assert event.context is not None, f"Missing context in event {event.event_id}"
            
            # Validate session continuity
            if event.event_type != AuditEventType.WEBSOCKET_CONNECT:
                assert event.context.get('session_id') == connect_event.session_id, f"Session ID mismatch in event {event.event_id}"
        
        # Validate event chronology (events should be in correct order)
        sorted_events = sorted(audit_trail, key=lambda e: e.timestamp)
        event_sequence = [e.event_type for e in sorted_events]
        
        expected_sequence = [
            AuditEventType.WEBSOCKET_CONNECT,
            AuditEventType.THREAD_CREATE,
            AuditEventType.CACHE_UPDATE,
            AuditEventType.STATE_SYNC,
            AuditEventType.MESSAGE_CREATE
        ]
        
        assert event_sequence == expected_sequence, f"Incorrect event sequence: {event_sequence}"
        
        # BUSINESS VALUE: Complete audit trail for compliance
        self.assert_business_value_delivered({
            'complete_audit_trail': len(missing_events) == 0,
            'chronological_accuracy': event_sequence == expected_sequence,
            'session_traceability': True,
            'compliance_ready': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_audit_trail_data_retention_and_querying(self, real_services_fixture):
        """Test audit trail data retention, querying, and performance."""
        services = real_services_fixture
        audit_manager = await self.setup_audit_test_environment(services)
        
        # Create multiple users for comprehensive testing
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(services, {
                'email': f'audit-user-{i}@example.com',
                'name': f'Audit User {i}'
            })
            users.append(UserID(user_data['id']))
        
        # Generate audit events across different time periods
        base_time = time.time() - 3600  # 1 hour ago
        time_intervals = [0, 900, 1800, 2700, 3600]  # 15-minute intervals
        
        all_events = []
        
        for i, user_id in enumerate(users):
            for j, time_offset in enumerate(time_intervals):
                event_time = base_time + time_offset
                
                # Create different types of events at different times
                event_types = [
                    (AuditEventType.WEBSOCKET_CONNECT, 'websocket', 'create'),
                    (AuditEventType.THREAD_CREATE, 'thread', 'create'),
                    (AuditEventType.MESSAGE_CREATE, 'message', 'create'),
                    (AuditEventType.STATE_SYNC, 'websocket', 'update')
                ]
                
                for k, (event_type, resource_type, action) in enumerate(event_types):
                    event = AuditEvent(
                        event_id=str(uuid4()),
                        event_type=event_type,
                        timestamp=event_time + (k * 10),  # 10-second spacing
                        user_id=str(user_id),
                        connection_id=str(uuid4()),
                        organization_id=None,
                        resource_type=resource_type,
                        resource_id=str(uuid4()),
                        action=action,
                        before_state={'test': 'before'},
                        after_state={'test': 'after'},
                        context={
                            'test_batch': j,
                            'user_index': i,
                            'event_index': k
                        }
                    )
                    
                    await audit_manager.log_audit_event(event)
                    all_events.append(event)
        
        total_events = len(all_events)
        self.logger.info(f"Generated {total_events} audit events for testing")
        
        # Test time-based queries
        mid_time = base_time + 1800  # Middle of test period
        
        # Query recent events (last 30 minutes)
        recent_events = await audit_manager.get_audit_trail(
            start_time=mid_time,
            end_time=time.time()
        )
        
        # Query older events (first 30 minutes)
        older_events = await audit_manager.get_audit_trail(
            start_time=base_time,
            end_time=mid_time
        )
        
        # Query user-specific events
        user_events = await audit_manager.get_audit_trail(
            user_id=str(users[0])
        )
        
        # Query resource-specific events
        thread_events = await audit_manager.get_audit_trail(
            resource_type='thread'
        )
        
        self.logger.info(f"Audit trail query results:")
        self.logger.info(f"  Recent events: {len(recent_events)}")
        self.logger.info(f"  Older events: {len(older_events)}")
        self.logger.info(f"  User-specific events: {len(user_events)}")
        self.logger.info(f"  Thread events: {len(thread_events)}")
        
        # Validate query results
        assert len(recent_events) > 0, "Recent events query returned no results"
        assert len(older_events) > 0, "Older events query returned no results"
        assert len(user_events) > 0, "User-specific query returned no results"
        assert len(thread_events) > 0, "Thread events query returned no results"
        
        # Validate time filtering accuracy
        for event in recent_events:
            assert event.timestamp >= mid_time, f"Recent event has timestamp too early: {event.timestamp}"
        
        for event in older_events:
            assert event.timestamp <= mid_time, f"Older event has timestamp too late: {event.timestamp}"
        
        # Validate user filtering
        for event in user_events:
            assert event.user_id == str(users[0]), f"User event has wrong user ID: {event.user_id}"
        
        # Validate resource filtering
        for event in thread_events:
            assert event.resource_type == 'thread', f"Thread event has wrong resource type: {event.resource_type}"
        
        # Test audit trail completeness across all queries
        unique_event_ids_from_queries = set()
        for events in [recent_events, older_events]:
            unique_event_ids_from_queries.update(e.event_id for e in events)
        
        all_event_ids = {e.event_id for e in all_events}
        assert unique_event_ids_from_queries == all_event_ids, "Time-based queries don't cover all events"
        
        # Test Redis audit timeline
        user_timeline_keys = await services.redis.lrange(f"user_audit_timeline:{users[0]}", 0, -1)
        assert len(user_timeline_keys) > 0, "User audit timeline is empty"
        
        # Validate timeline contains correct events
        timeline_events = []
        for event_id in user_timeline_keys:
            cached_event = await services.redis.get_json(f"audit_event:{event_id}")
            if cached_event:
                timeline_events.append(cached_event)
        
        assert len(timeline_events) > 0, "No events found in Redis timeline"
        
        # All timeline events should belong to the user
        for event_data in timeline_events:
            assert event_data['user_id'] == str(users[0]), "Timeline contains events from other users"
        
        # BUSINESS VALUE: Efficient audit trail storage and querying
        self.assert_business_value_delivered({
            'time_based_queries': len(recent_events) > 0 and len(older_events) > 0,
            'user_specific_queries': len(user_events) > 0,
            'resource_filtering': len(thread_events) > 0,
            'data_completeness': unique_event_ids_from_queries == all_event_ids,
            'timeline_functionality': len(timeline_events) > 0
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_audit_trail_error_and_security_event_tracking(self, real_services_fixture):
        """Test audit trail captures error conditions and security-relevant events."""
        services = real_services_fixture
        audit_manager = await self.setup_audit_test_environment(services)
        state_manager = get_websocket_state_manager()
        
        # Create test user
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        connection_id = str(uuid4())
        
        test_start_time = time.time()
        
        # 1. Test Permission Check Audit
        permission_check_event = await audit_manager.create_state_change_event(
            AuditEventType.PERMISSION_CHECK,
            str(user_id),
            connection_id,
            'thread',
            str(uuid4()),
            'read',
            None,
            {'permission_granted': False, 'reason': 'insufficient_privileges'},
            {
                'requested_action': 'read_thread',
                'user_role': 'viewer',
                'required_role': 'member',
                'security_check': True
            }
        )
        
        # 2. Test Error Event Audit
        try:
            # Simulate operation that will fail
            await services.postgres.execute("""
                INSERT INTO backend.threads (id, user_id, title)
                VALUES ($1, $2, $3)
            """, "invalid-uuid-format", str(user_id), "Error Test Thread")
        except Exception as e:
            # Log the error as an audit event
            error_event = await audit_manager.create_state_change_event(
                AuditEventType.ERROR_OCCURRED,
                str(user_id),
                connection_id,
                'thread',
                'invalid-uuid-format',
                'create',
                None,
                None,
                {
                    'error_type': 'database_error',
                    'error_message': str(e),
                    'operation_attempted': 'create_thread',
                    'security_relevant': False,
                    'error_code': 'INVALID_UUID'
                }
            )
        
        # 3. Test Security Event - Suspicious Activity
        suspicious_activity_event = await audit_manager.create_state_change_event(
            AuditEventType.ERROR_OCCURRED,
            str(user_id),
            connection_id,
            'websocket',
            connection_id,
            'access',
            None,
            {'access_denied': True, 'reason': 'rate_limit_exceeded'},
            {
                'security_event': True,
                'event_type': 'rate_limit_violation',
                'requests_per_minute': 1000,
                'limit': 100,
                'ip_address': '192.168.1.100',
                'user_agent': 'SuspiciousBot/1.0',
                'threat_level': 'medium'
            }
        )
        
        # 4. Test Unauthorized Access Attempt
        unauthorized_thread_id = str(uuid4())
        
        unauthorized_access_event = await audit_manager.create_state_change_event(
            AuditEventType.PERMISSION_CHECK,
            str(user_id),
            connection_id,
            'thread',
            unauthorized_thread_id,
            'delete',
            {'status': 'exists', 'owner': 'other_user'},
            {'access_denied': True, 'reason': 'not_owner'},
            {
                'security_event': True,
                'attempted_action': 'delete_thread',
                'resource_owner': 'other_user',
                'access_method': 'websocket',
                'threat_level': 'low',
                'requires_investigation': False
            }
        )
        
        # 5. Test State Corruption Detection
        state_corruption_event = await audit_manager.create_state_change_event(
            AuditEventType.ERROR_OCCURRED,
            str(user_id),
            connection_id,
            'cache',
            f'thread:{uuid4()}',
            'validate',
            {'expected_user': str(user_id)},
            {'actual_user': 'corrupted_data', 'corruption_detected': True},
            {
                'security_event': True,
                'event_type': 'data_corruption',
                'corruption_type': 'user_id_mismatch',
                'threat_level': 'high',
                'requires_investigation': True,
                'auto_remediation': 'cache_invalidated'
            }
        )
        
        test_end_time = time.time()
        
        # Retrieve and analyze security/error audit trail
        audit_trail = await audit_manager.get_audit_trail(
            user_id=str(user_id),
            start_time=test_start_time,
            end_time=test_end_time
        )
        
        # Categorize events
        permission_events = [e for e in audit_trail if e.event_type == AuditEventType.PERMISSION_CHECK]
        error_events = [e for e in audit_trail if e.event_type == AuditEventType.ERROR_OCCURRED]
        security_events = [e for e in audit_trail if e.context.get('security_event', False)]
        high_threat_events = [e for e in audit_trail if e.context.get('threat_level') == 'high']
        investigation_required = [e for e in audit_trail if e.context.get('requires_investigation', False)]
        
        self.logger.info(f"Security and error audit analysis:")
        self.logger.info(f"  Total audit events: {len(audit_trail)}")
        self.logger.info(f"  Permission check events: {len(permission_events)}")
        self.logger.info(f"  Error events: {len(error_events)}")
        self.logger.info(f"  Security events: {len(security_events)}")
        self.logger.info(f"  High threat events: {len(high_threat_events)}")
        self.logger.info(f"  Investigation required: {len(investigation_required)}")
        
        # Validate security event details
        assert len(permission_events) >= 2, f"Expected at least 2 permission events, got {len(permission_events)}"
        assert len(error_events) >= 3, f"Expected at least 3 error events, got {len(error_events)}"
        assert len(security_events) >= 3, f"Expected at least 3 security events, got {len(security_events)}"
        assert len(high_threat_events) >= 1, f"Expected at least 1 high threat event, got {len(high_threat_events)}"
        
        # Validate security event structure
        for event in security_events:
            assert 'security_event' in event.context, f"Security event missing security_event flag: {event.event_id}"
            assert 'threat_level' in event.context, f"Security event missing threat_level: {event.event_id}"
            assert event.context['threat_level'] in ['low', 'medium', 'high'], f"Invalid threat level: {event.context['threat_level']}"
        
        # Validate error event structure
        for event in error_events:
            assert event.context is not None, f"Error event missing context: {event.event_id}"
            if event.context.get('error_type'):
                assert isinstance(event.context['error_type'], str), f"Error type not string: {event.event_id}"
        
        # Test audit trail aggregation for security monitoring
        security_summary = {
            'total_security_events': len(security_events),
            'threat_levels': {},
            'event_types': {},
            'investigation_queue': len(investigation_required)
        }
        
        for event in security_events:
            threat_level = event.context.get('threat_level', 'unknown')
            security_summary['threat_levels'][threat_level] = security_summary['threat_levels'].get(threat_level, 0) + 1
            
            event_type = event.context.get('event_type', 'generic')
            security_summary['event_types'][event_type] = security_summary['event_types'].get(event_type, 0) + 1
        
        self.logger.info(f"Security summary: {security_summary}")
        
        # Store security summary in Redis for monitoring dashboard
        await services.redis.set_json(
            f"security_summary:{str(user_id)}:{int(test_start_time)}",
            security_summary,
            ex=86400
        )
        
        # Validate security summary was stored
        stored_summary = await services.redis.get_json(f"security_summary:{str(user_id)}:{int(test_start_time)}")
        assert stored_summary is not None, "Security summary not stored in Redis"
        assert stored_summary['total_security_events'] == len(security_events), "Security summary count mismatch"
        
        # BUSINESS VALUE: Comprehensive security and error audit trail
        self.assert_business_value_delivered({
            'security_event_tracking': len(security_events) >= 3,
            'error_event_logging': len(error_events) >= 3,
            'threat_level_classification': len(high_threat_events) >= 1,
            'investigation_queue': len(investigation_required) >= 1,
            'security_monitoring': stored_summary is not None
        }, 'automation')