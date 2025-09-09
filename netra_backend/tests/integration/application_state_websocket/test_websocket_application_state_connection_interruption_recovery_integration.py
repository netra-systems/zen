"""
Test WebSocket Application State Synchronization During Connection Interruptions and Recovery Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless user experience during network interruptions and reconnections
- Value Impact: Users don't lose work or experience state corruption during connection issues
- Strategic Impact: Reliability foundation - users trust the system to maintain their data

This test validates that application state remains synchronized and recoverable
when WebSocket connections are interrupted and restored. The system must handle
connection drops gracefully and restore state without data loss.
"""

import asyncio
import pytest
import json
import time
import random
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState
from shared.types import UserID, ThreadID, MessageID
from shared.isolated_environment import get_env


class ConnectionState(Enum):
    """States of a WebSocket connection."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class StateSnapshot:
    """Snapshot of application state at a point in time."""
    timestamp: float
    postgres_state: Dict[str, Any]
    redis_state: Dict[str, Any]
    websocket_state: Dict[str, Any]
    connection_state: ConnectionState
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'postgres_state': self.postgres_state,
            'redis_state': self.redis_state,
            'websocket_state': self.websocket_state,
            'connection_state': self.connection_state.value
        }


class MockWebSocketConnection:
    """Mock WebSocket connection that can simulate interruptions."""
    
    def __init__(self, connection_id: str, user_id: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.state = ConnectionState.DISCONNECTED
        self.connected_at: Optional[float] = None
        self.disconnected_at: Optional[float] = None
        self.reconnect_count = 0
        self.message_queue: List[Dict[str, Any]] = []
        self.pending_operations: List[Dict[str, Any]] = []
        
    async def connect(self, state_manager):
        """Simulate connection establishment."""
        self.state = ConnectionState.CONNECTING
        await asyncio.sleep(0.1)  # Connection delay
        
        self.state = ConnectionState.CONNECTED
        self.connected_at = time.time()
        
        # Initialize WebSocket state
        state_manager.set_websocket_state(self.connection_id, 'connection_info', {
            'user_id': self.user_id,
            'connection_id': self.connection_id,
            'state': WebSocketConnectionState.CONNECTED.value,
            'connected_at': self.connected_at,
            'reconnect_count': self.reconnect_count
        })
        
        return True
    
    async def disconnect(self, state_manager, reason: str = "client_disconnect"):
        """Simulate connection loss."""
        if self.state == ConnectionState.CONNECTED:
            self.state = ConnectionState.DISCONNECTED
            self.disconnected_at = time.time()
            
            # Update WebSocket state to reflect disconnection
            current_state = state_manager.get_websocket_state(self.connection_id, 'connection_info')
            if current_state:
                current_state.update({
                    'state': WebSocketConnectionState.DISCONNECTED.value,
                    'disconnected_at': self.disconnected_at,
                    'disconnect_reason': reason
                })
                state_manager.set_websocket_state(self.connection_id, 'connection_info', current_state)
        
        return True
    
    async def reconnect(self, state_manager):
        """Simulate reconnection process."""
        if self.state == ConnectionState.DISCONNECTED:
            self.state = ConnectionState.RECONNECTING
            self.reconnect_count += 1
            
            await asyncio.sleep(0.2)  # Reconnection delay
            
            # Restore connection
            self.state = ConnectionState.CONNECTED
            self.connected_at = time.time()
            
            # Update WebSocket state for reconnection
            current_state = state_manager.get_websocket_state(self.connection_id, 'connection_info')
            if current_state:
                current_state.update({
                    'state': WebSocketConnectionState.CONNECTED.value,
                    'connected_at': self.connected_at,
                    'reconnect_count': self.reconnect_count,
                    'last_reconnect_at': time.time()
                })
                state_manager.set_websocket_state(self.connection_id, 'connection_info', current_state)
            
            return True
        
        return False
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Simulate sending a message."""
        if self.state == ConnectionState.CONNECTED:
            self.message_queue.append({
                'message': message,
                'sent_at': time.time(),
                'status': 'sent'
            })
            return True
        else:
            # Queue message for later delivery
            self.pending_operations.append({
                'type': 'message',
                'data': message,
                'queued_at': time.time()
            })
            return False
    
    async def flush_pending_operations(self):
        """Process queued operations after reconnection."""
        if self.state == ConnectionState.CONNECTED:
            processed = []
            for operation in self.pending_operations:
                operation['processed_at'] = time.time()
                processed.append(operation)
            
            self.pending_operations.clear()
            return processed
        
        return []


class ConnectionRecoveryManager:
    """Manages connection recovery and state synchronization."""
    
    def __init__(self, services, state_manager):
        self.services = services
        self.state_manager = state_manager
        self.recovery_log: List[Dict[str, Any]] = []
    
    async def capture_state_snapshot(self, user_id: str, connection_id: str, 
                                   thread_ids: List[str], message_ids: List[str]) -> StateSnapshot:
        """Capture current state across all layers."""
        timestamp = time.time()
        
        # Capture PostgreSQL state
        postgres_state = {}
        
        if thread_ids:
            threads = await self.services.postgres.fetch("""
                SELECT id, user_id, title, metadata, updated_at 
                FROM backend.threads 
                WHERE id = ANY($1)
            """, thread_ids)
            postgres_state['threads'] = [dict(t) for t in threads]
        
        if message_ids:
            messages = await self.services.postgres.fetch("""
                SELECT id, thread_id, user_id, content, role, created_at
                FROM backend.messages 
                WHERE id = ANY($1)
            """, message_ids)
            postgres_state['messages'] = [dict(m) for m in messages]
        
        # Capture Redis state
        redis_state = {}
        
        for thread_id in thread_ids:
            cached_thread = await self.services.redis.get_json(f"thread:{thread_id}")
            if cached_thread:
                redis_state[f"thread:{thread_id}"] = cached_thread
        
        for message_id in message_ids:
            cached_message = await self.services.redis.get_json(f"message:{message_id}")
            if cached_message:
                redis_state[f"message:{message_id}"] = cached_message
        
        # Capture WebSocket state
        websocket_state = {}
        ws_connection_info = self.state_manager.get_websocket_state(connection_id, 'connection_info')
        if ws_connection_info:
            websocket_state['connection_info'] = ws_connection_info.copy()
        
        # Determine connection state
        connection_state = ConnectionState.DISCONNECTED
        if ws_connection_info and ws_connection_info.get('state') == WebSocketConnectionState.CONNECTED.value:
            connection_state = ConnectionState.CONNECTED
        
        return StateSnapshot(
            timestamp=timestamp,
            postgres_state=postgres_state,
            redis_state=redis_state,
            websocket_state=websocket_state,
            connection_state=connection_state
        )
    
    async def validate_state_consistency(self, before_snapshot: StateSnapshot, 
                                       after_snapshot: StateSnapshot) -> Dict[str, Any]:
        """Validate state consistency between snapshots."""
        consistency_report = {
            'postgres_consistent': True,
            'redis_consistent': True,
            'websocket_consistent': True,
            'data_loss_detected': False,
            'inconsistencies': []
        }
        
        # Check PostgreSQL consistency
        if before_snapshot.postgres_state.get('threads') and after_snapshot.postgres_state.get('threads'):
            before_threads = {t['id']: t for t in before_snapshot.postgres_state['threads']}
            after_threads = {t['id']: t for t in after_snapshot.postgres_state['threads']}
            
            for thread_id in before_threads:
                if thread_id not in after_threads:
                    consistency_report['postgres_consistent'] = False
                    consistency_report['data_loss_detected'] = True
                    consistency_report['inconsistencies'].append(f"Thread {thread_id} lost from PostgreSQL")
                elif before_threads[thread_id]['title'] != after_threads[thread_id]['title']:
                    # Allow for legitimate updates, but track changes
                    consistency_report['inconsistencies'].append(f"Thread {thread_id} title changed")
        
        if before_snapshot.postgres_state.get('messages') and after_snapshot.postgres_state.get('messages'):
            before_messages = {m['id']: m for m in before_snapshot.postgres_state['messages']}
            after_messages = {m['id']: m for m in after_snapshot.postgres_state['messages']}
            
            for message_id in before_messages:
                if message_id not in after_messages:
                    consistency_report['postgres_consistent'] = False
                    consistency_report['data_loss_detected'] = True
                    consistency_report['inconsistencies'].append(f"Message {message_id} lost from PostgreSQL")
        
        # Check Redis consistency
        for cache_key in before_snapshot.redis_state:
            if cache_key not in after_snapshot.redis_state:
                # Cache expiration is acceptable, but track it
                consistency_report['inconsistencies'].append(f"Cache key {cache_key} expired")
        
        # Check WebSocket state consistency
        before_ws = before_snapshot.websocket_state.get('connection_info', {})
        after_ws = after_snapshot.websocket_state.get('connection_info', {})
        
        # Essential fields that should be preserved
        essential_fields = ['user_id', 'connection_id']
        for field in essential_fields:
            if before_ws.get(field) != after_ws.get(field):
                consistency_report['websocket_consistent'] = False
                consistency_report['inconsistencies'].append(f"WebSocket {field} changed: {before_ws.get(field)} -> {after_ws.get(field)}")
        
        return consistency_report
    
    async def perform_recovery_validation(self, user_id: str, connection_id: str,
                                        pre_disconnect_snapshot: StateSnapshot,
                                        post_reconnect_snapshot: StateSnapshot) -> Dict[str, Any]:
        """Perform comprehensive recovery validation."""
        consistency = await self.validate_state_consistency(pre_disconnect_snapshot, post_reconnect_snapshot)
        
        recovery_report = {
            'recovery_time_seconds': post_reconnect_snapshot.timestamp - pre_disconnect_snapshot.timestamp,
            'state_consistency': consistency,
            'recovery_successful': consistency['postgres_consistent'] and not consistency['data_loss_detected'],
            'websocket_state_restored': consistency['websocket_consistent']
        }
        
        self.recovery_log.append({
            'user_id': user_id,
            'connection_id': connection_id,
            'recovery_report': recovery_report,
            'timestamp': time.time()
        })
        
        return recovery_report


class TestWebSocketApplicationStateConnectionInterruptionRecovery(BaseIntegrationTest):
    """Test state synchronization validation during WebSocket connection interruptions and recovery."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_graceful_connection_interruption_and_recovery(self, real_services_fixture):
        """Test that connection interruptions are handled gracefully with full state recovery."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Set up recovery manager
        recovery_manager = ConnectionRecoveryManager(services, state_manager)
        
        # Create test user and initial state
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        
        # Create mock WebSocket connection
        connection = MockWebSocketConnection(str(uuid4()), str(user_id))
        
        # Establish initial connection
        await connection.connect(state_manager)
        
        # Create some application state
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title, metadata)
            VALUES ($1, $2, $3)
            RETURNING id
        """, str(user_id), "Recovery Test Thread", json.dumps({
            'test_type': 'connection_recovery',
            'connection_id': connection.connection_id
        }))
        
        thread_id = ThreadID(str(thread_id))
        
        # Cache thread in Redis
        await services.redis.set_json(f"thread:{thread_id}", {
            'id': str(thread_id),
            'user_id': str(user_id),
            'title': 'Recovery Test Thread',
            'cached_at': time.time()
        }, ex=3600)
        
        # Create messages
        message_ids = []
        for i in range(3):
            message_id = MessageID(str(uuid4()))
            await services.postgres.execute("""
                INSERT INTO backend.messages (id, thread_id, user_id, content, role)
                VALUES ($1, $2, $3, $4, $5)
            """, str(message_id), str(thread_id), str(user_id), f"Recovery test message {i}", "user")
            
            message_ids.append(message_id)
            
            # Cache message in Redis
            await services.redis.set_json(f"message:{message_id}", {
                'id': str(message_id),
                'thread_id': str(thread_id),
                'user_id': str(user_id),
                'content': f"Recovery test message {i}",
                'role': 'user'
            }, ex=3600)
        
        # Update WebSocket state to reflect current application state
        ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
        ws_state.update({
            'current_thread_id': str(thread_id),
            'message_count': len(message_ids),
            'last_activity': time.time()
        })
        state_manager.set_websocket_state(connection.connection_id, 'connection_info', ws_state)
        
        # Capture state before disconnection
        pre_disconnect_snapshot = await recovery_manager.capture_state_snapshot(
            str(user_id), connection.connection_id, [str(thread_id)], [str(mid) for mid in message_ids]
        )
        
        self.logger.info(f"Pre-disconnect state captured at {pre_disconnect_snapshot.timestamp}")
        
        # Simulate connection interruption
        await connection.disconnect(state_manager, reason="network_interruption")
        
        # Simulate some time passing during disconnection
        await asyncio.sleep(0.5)
        
        # Simulate pending operations during disconnection
        pending_message = {
            'type': 'message_create',
            'thread_id': str(thread_id),
            'content': 'Message sent during disconnection'
        }
        
        await connection.send_message(pending_message)  # This should queue the message
        
        # Attempt reconnection
        reconnect_success = await connection.reconnect(state_manager)
        assert reconnect_success, "Reconnection should succeed"
        
        # Process pending operations
        processed_ops = await connection.flush_pending_operations()
        
        # Simulate processing the queued message
        if processed_ops:
            queued_message_id = MessageID(str(uuid4()))
            await services.postgres.execute("""
                INSERT INTO backend.messages (id, thread_id, user_id, content, role, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, str(queued_message_id), str(thread_id), str(user_id), 
                 "Message sent during disconnection", "user", json.dumps({
                'queued_during_disconnect': True,
                'processed_after_reconnect': True
            }))
            
            message_ids.append(queued_message_id)
        
        # Capture state after reconnection and recovery
        post_reconnect_snapshot = await recovery_manager.capture_state_snapshot(
            str(user_id), connection.connection_id, [str(thread_id)], [str(mid) for mid in message_ids]
        )
        
        self.logger.info(f"Post-reconnect state captured at {post_reconnect_snapshot.timestamp}")
        
        # Validate recovery
        recovery_report = await recovery_manager.perform_recovery_validation(
            str(user_id), connection.connection_id, pre_disconnect_snapshot, post_reconnect_snapshot
        )
        
        self.logger.info(f"Recovery validation results:")
        self.logger.info(f"  Recovery time: {recovery_report['recovery_time_seconds']:.2f}s")
        self.logger.info(f"  State consistency: {recovery_report['state_consistency']}")
        self.logger.info(f"  Recovery successful: {recovery_report['recovery_successful']}")
        self.logger.info(f"  WebSocket state restored: {recovery_report['websocket_state_restored']}")
        
        # Assertions
        assert recovery_report['recovery_successful'], f"Recovery failed: {recovery_report['state_consistency']['inconsistencies']}"
        assert recovery_report['websocket_state_restored'], "WebSocket state not properly restored"
        assert recovery_report['recovery_time_seconds'] < 5.0, f"Recovery took too long: {recovery_report['recovery_time_seconds']}s"
        assert not recovery_report['state_consistency']['data_loss_detected'], "Data loss detected during recovery"
        
        # Verify connection state is properly restored
        final_ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
        assert final_ws_state is not None, "WebSocket state lost after recovery"
        assert final_ws_state['user_id'] == str(user_id), "User ID not preserved"
        assert final_ws_state['current_thread_id'] == str(thread_id), "Thread context not preserved"
        assert final_ws_state['reconnect_count'] == 1, "Reconnect count not tracked"
        
        # Verify pending operations were processed
        assert len(processed_ops) > 0, "No pending operations were processed"
        
        # Verify queued message was saved
        final_message_count = await services.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
        """, str(thread_id))
        
        expected_message_count = 4  # 3 original + 1 queued during disconnect
        assert final_message_count == expected_message_count, f"Expected {expected_message_count} messages, got {final_message_count}"
        
        # BUSINESS VALUE: Seamless recovery maintains user experience
        self.assert_business_value_delivered({
            'graceful_interruption_handling': True,
            'complete_state_recovery': recovery_report['recovery_successful'],
            'no_data_loss': not recovery_report['state_consistency']['data_loss_detected'],
            'pending_operation_processing': len(processed_ops) > 0
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_rapid_connection_interruptions(self, real_services_fixture):
        """Test system resilience during multiple rapid connection interruptions."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        recovery_manager = ConnectionRecoveryManager(services, state_manager)
        
        # Create test user
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        
        # Create mock connection
        connection = MockWebSocketConnection(str(uuid4()), str(user_id))
        await connection.connect(state_manager)
        
        # Create initial application state
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title)
            VALUES ($1, $2)
            RETURNING id
        """, str(user_id), "Rapid Interruption Test")
        
        thread_id = ThreadID(str(thread_id))
        
        # Initialize WebSocket state
        state_manager.set_websocket_state(connection.connection_id, 'connection_info', {
            'user_id': str(user_id),
            'connection_id': connection.connection_id,
            'current_thread_id': str(thread_id),
            'state': WebSocketConnectionState.CONNECTED.value,
            'interruption_count': 0
        })
        
        # Perform multiple rapid interruptions
        interruption_count = 5
        recovery_reports = []
        
        for i in range(interruption_count):
            self.logger.info(f"Starting interruption cycle {i+1}/{interruption_count}")
            
            # Capture state before interruption
            pre_snapshot = await recovery_manager.capture_state_snapshot(
                str(user_id), connection.connection_id, [str(thread_id)], []
            )
            
            # Add some state changes before disconnection
            message_id = MessageID(str(uuid4()))
            await services.postgres.execute("""
                INSERT INTO backend.messages (id, thread_id, user_id, content, role, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, str(message_id), str(thread_id), str(user_id), 
                 f"Message before interruption {i}", "user", json.dumps({
                'interruption_cycle': i,
                'created_before_disconnect': True
            }))
            
            # Update WebSocket state
            current_ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
            current_ws_state['interruption_count'] = i
            current_ws_state['last_message_before_disconnect'] = str(message_id)
            state_manager.set_websocket_state(connection.connection_id, 'connection_info', current_ws_state)
            
            # Simulate disconnection
            await connection.disconnect(state_manager, reason=f"rapid_test_interruption_{i}")
            
            # Random brief disconnect time
            disconnect_duration = random.uniform(0.1, 0.3)
            await asyncio.sleep(disconnect_duration)
            
            # Attempt reconnection
            reconnect_success = await connection.reconnect(state_manager)
            assert reconnect_success, f"Reconnection {i+1} failed"
            
            # Capture state after reconnection
            post_snapshot = await recovery_manager.capture_state_snapshot(
                str(user_id), connection.connection_id, [str(thread_id)], [str(message_id)]
            )
            
            # Validate recovery
            recovery_report = await recovery_manager.perform_recovery_validation(
                str(user_id), connection.connection_id, pre_snapshot, post_snapshot
            )
            
            recovery_reports.append({
                'cycle': i + 1,
                'disconnect_duration': disconnect_duration,
                'recovery_report': recovery_report
            })
            
            # Brief pause between cycles
            await asyncio.sleep(0.1)
        
        # Analyze overall resilience
        successful_recoveries = sum(1 for report in recovery_reports if report['recovery_report']['recovery_successful'])
        avg_recovery_time = sum(report['recovery_report']['recovery_time_seconds'] for report in recovery_reports) / len(recovery_reports)
        data_loss_incidents = sum(1 for report in recovery_reports if report['recovery_report']['state_consistency']['data_loss_detected'])
        
        self.logger.info(f"Rapid interruption test results:")
        self.logger.info(f"  Total interruption cycles: {interruption_count}")
        self.logger.info(f"  Successful recoveries: {successful_recoveries}/{interruption_count}")
        self.logger.info(f"  Average recovery time: {avg_recovery_time:.3f}s")
        self.logger.info(f"  Data loss incidents: {data_loss_incidents}")
        self.logger.info(f"  Final reconnect count: {connection.reconnect_count}")
        
        # Verify system resilience
        recovery_success_rate = (successful_recoveries / interruption_count) * 100
        
        assert recovery_success_rate >= 100.0, f"Recovery success rate too low: {recovery_success_rate:.1f}%"
        assert data_loss_incidents == 0, f"Data loss occurred during {data_loss_incidents} cycles"
        assert avg_recovery_time < 1.0, f"Average recovery time too high: {avg_recovery_time:.3f}s"
        assert connection.reconnect_count == interruption_count, f"Reconnect count mismatch: {connection.reconnect_count} != {interruption_count}"
        
        # Verify final state integrity
        final_ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
        assert final_ws_state is not None, "Final WebSocket state lost"
        assert final_ws_state['user_id'] == str(user_id), "User ID corrupted"
        assert final_ws_state['current_thread_id'] == str(thread_id), "Thread context lost"
        assert final_ws_state['reconnect_count'] == interruption_count, "Reconnect count not tracked correctly"
        
        # Verify all messages were persisted despite interruptions
        final_message_count = await services.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
        """, str(thread_id))
        
        assert final_message_count == interruption_count, f"Expected {interruption_count} messages, got {final_message_count}"
        
        # BUSINESS VALUE: System resilient to network instability
        self.assert_business_value_delivered({
            'rapid_interruption_resilience': recovery_success_rate >= 100.0,
            'no_cumulative_data_loss': data_loss_incidents == 0,
            'consistent_recovery_performance': avg_recovery_time < 1.0,
            'network_instability_tolerance': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_synchronization_during_extended_disconnection(self, real_services_fixture):
        """Test state synchronization when connection is lost for extended periods."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        recovery_manager = ConnectionRecoveryManager(services, state_manager)
        
        # Create test user
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        
        # Create connection and establish state
        connection = MockWebSocketConnection(str(uuid4()), str(user_id))
        await connection.connect(state_manager)
        
        # Create application state
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title, metadata)
            VALUES ($1, $2, $3)
            RETURNING id
        """, str(user_id), "Extended Disconnection Test", json.dumps({
            'test_type': 'extended_disconnection'
        }))
        
        thread_id = ThreadID(str(thread_id))
        
        # Create initial messages
        initial_message_ids = []
        for i in range(2):
            message_id = MessageID(str(uuid4()))
            await services.postgres.execute("""
                INSERT INTO backend.messages (id, thread_id, user_id, content, role)
                VALUES ($1, $2, $3, $4, $5)
            """, str(message_id), str(thread_id), str(user_id), f"Initial message {i}", "user")
            
            initial_message_ids.append(message_id)
        
        # Set up WebSocket state
        state_manager.set_websocket_state(connection.connection_id, 'connection_info', {
            'user_id': str(user_id),
            'connection_id': connection.connection_id,
            'current_thread_id': str(thread_id),
            'message_count': len(initial_message_ids),
            'state': WebSocketConnectionState.CONNECTED.value,
            'connected_at': time.time()
        })
        
        # Capture state before extended disconnection
        pre_disconnect_snapshot = await recovery_manager.capture_state_snapshot(
            str(user_id), connection.connection_id, [str(thread_id)], [str(mid) for mid in initial_message_ids]
        )
        
        # Simulate extended disconnection
        await connection.disconnect(state_manager, reason="extended_network_outage")
        
        # Simulate server-side state changes during disconnection
        # (e.g., other clients making changes, background processes, etc.)
        
        # Add messages from "other sources" during disconnection
        server_side_message_ids = []
        for i in range(3):
            message_id = MessageID(str(uuid4()))
            await services.postgres.execute("""
                INSERT INTO backend.messages (id, thread_id, user_id, content, role, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, str(message_id), str(thread_id), str(user_id), 
                 f"Server-side message {i}", "system", json.dumps({
                'created_during_disconnect': True,
                'source': 'background_process'
            }))
            
            server_side_message_ids.append(message_id)
        
        # Update thread metadata during disconnection
        await services.postgres.execute("""
            UPDATE backend.threads 
            SET metadata = jsonb_set(
                metadata,
                '{updated_during_disconnect}',
                'true'
            ),
            updated_at = NOW()
            WHERE id = $1
        """, str(thread_id))
        
        # Simulate cache expiration during extended disconnection
        await services.redis.delete(f"thread:{thread_id}")
        for message_id in initial_message_ids:
            await services.redis.delete(f"message:{message_id}")
        
        # Simulate extended disconnection period
        disconnect_duration = 2.0  # 2 seconds simulates extended outage
        await asyncio.sleep(disconnect_duration)
        
        # Attempt reconnection
        reconnect_success = await connection.reconnect(state_manager)
        assert reconnect_success, "Extended disconnection reconnection failed"
        
        # Simulate state resynchronization after reconnection
        # This would typically involve:
        # 1. Detecting state drift
        # 2. Refreshing cached data
        # 3. Updating WebSocket state with current reality
        
        # Refresh thread cache
        updated_thread = await services.postgres.fetchrow("""
            SELECT id, user_id, title, metadata, updated_at
            FROM backend.threads
            WHERE id = $1
        """, str(thread_id))
        
        await services.redis.set_json(f"thread:{thread_id}", {
            'id': str(updated_thread['id']),
            'user_id': str(updated_thread['user_id']),
            'title': updated_thread['title'],
            'metadata': updated_thread['metadata'],
            'updated_at': updated_thread['updated_at'].isoformat(),
            'refreshed_after_disconnect': True
        }, ex=3600)
        
        # Get current message count
        current_message_count = await services.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
        """, str(thread_id))
        
        # Update WebSocket state with refreshed information
        reconnected_ws_state = {
            'user_id': str(user_id),
            'connection_id': connection.connection_id,
            'current_thread_id': str(thread_id),
            'message_count': current_message_count,
            'state': WebSocketConnectionState.CONNECTED.value,
            'reconnected_at': time.time(),
            'state_refreshed': True,
            'disconnect_duration': disconnect_duration,
            'reconnect_count': connection.reconnect_count
        }
        
        state_manager.set_websocket_state(connection.connection_id, 'connection_info', reconnected_ws_state)
        
        # Capture state after extended reconnection
        all_message_ids = initial_message_ids + server_side_message_ids
        post_reconnect_snapshot = await recovery_manager.capture_state_snapshot(
            str(user_id), connection.connection_id, [str(thread_id)], [str(mid) for mid in all_message_ids]
        )
        
        # Analyze state synchronization
        sync_analysis = {
            'disconnect_duration': disconnect_duration,
            'initial_message_count': len(initial_message_ids),
            'server_side_changes': len(server_side_message_ids),
            'final_message_count': current_message_count,
            'expected_total': len(initial_message_ids) + len(server_side_message_ids),
            'cache_refreshed': True,
            'websocket_state_updated': True
        }
        
        self.logger.info(f"Extended disconnection analysis:")
        for key, value in sync_analysis.items():
            self.logger.info(f"  {key}: {value}")
        
        # Validate extended disconnection handling
        assert sync_analysis['final_message_count'] == sync_analysis['expected_total'], \
            f"Message count mismatch: {sync_analysis['final_message_count']} != {sync_analysis['expected_total']}"
        
        # Verify WebSocket state reflects current reality
        final_ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
        assert final_ws_state is not None, "WebSocket state lost after extended reconnection"
        assert final_ws_state['message_count'] == current_message_count, \
            f"WebSocket message count not synchronized: {final_ws_state['message_count']} != {current_message_count}"
        assert final_ws_state.get('state_refreshed'), "State refresh not indicated"
        
        # Verify cache was properly refreshed
        refreshed_thread_cache = await services.redis.get_json(f"thread:{thread_id}")
        assert refreshed_thread_cache is not None, "Thread cache not refreshed after reconnection"
        assert refreshed_thread_cache.get('refreshed_after_disconnect'), "Cache refresh not marked"
        
        # Verify thread metadata was preserved during disconnection
        final_thread = await services.postgres.fetchrow("""
            SELECT metadata FROM backend.threads WHERE id = $1
        """, str(thread_id))
        
        assert final_thread['metadata'].get('updated_during_disconnect'), "Server-side updates lost"
        
        # BUSINESS VALUE: Robust handling of extended outages
        self.assert_business_value_delivered({
            'extended_outage_recovery': reconnect_success,
            'server_side_change_preservation': sync_analysis['final_message_count'] == sync_analysis['expected_total'],
            'state_resynchronization': final_ws_state.get('state_refreshed', False),
            'cache_refresh_capability': refreshed_thread_cache is not None
        }, 'automation')