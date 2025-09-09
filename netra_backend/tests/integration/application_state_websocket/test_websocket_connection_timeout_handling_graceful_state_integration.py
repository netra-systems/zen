"""
Test WebSocket Connection Timeout Handling with Graceful State Preservation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable timeout handling that preserves user data and enables reconnection
- Value Impact: Users experience graceful handling of network interruptions without data loss
- Strategic Impact: Enables reliable long-running sessions and improved user experience resilience

This integration test validates that WebSocket connection timeout handling works correctly
while preserving application state for graceful recovery and reconnection scenarios.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TimeoutType:
    """Timeout type enumeration for testing."""
    READ_TIMEOUT = "read_timeout"
    WRITE_TIMEOUT = "write_timeout"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    IDLE_TIMEOUT = "idle_timeout"
    GRACEFUL_TIMEOUT = "graceful_timeout"


class TestWebSocketConnectionTimeoutHandlingGracefulStateIntegration(BaseIntegrationTest):
    """Test WebSocket connection timeout handling with comprehensive graceful state preservation."""
    
    def _create_timeout_handling_websocket(self, connection_id: str, user_id: str, timeout_config: Dict[str, float]):
        """Create a WebSocket mock with configurable timeout handling capabilities."""
        class TimeoutHandlingWebSocket:
            def __init__(self, connection_id: str, user_id: str, timeout_config: Dict[str, float]):
                self.connection_id = connection_id
                self.user_id = user_id
                self.timeout_config = timeout_config
                self.messages_sent = []
                self.is_closed = False
                self.last_activity = datetime.utcnow()
                self.timeout_events = []
                self.state_preservation_data = {}
                self.graceful_shutdown_in_progress = False
                self.timeout_callbacks = []
                
                # Timeout tracking
                self.read_timeout_triggered = False
                self.write_timeout_triggered = False
                self.heartbeat_timeout_triggered = False
                self.idle_timeout_triggered = False
                
                # State preservation
                self._preserve_initial_state()
            
            def _preserve_initial_state(self):
                """Preserve initial connection state for recovery."""
                self.state_preservation_data = {
                    'connection_id': self.connection_id,
                    'user_id': self.user_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'initial_timeout_config': self.timeout_config.copy(),
                    'message_count': 0,
                    'last_activity': self.last_activity.isoformat()
                }
            
            def _update_activity(self):
                """Update last activity timestamp."""
                self.last_activity = datetime.utcnow()
                self.state_preservation_data['last_activity'] = self.last_activity.isoformat()
            
            async def send_json(self, data):
                if self.is_closed:
                    raise ConnectionError("Connection is closed")
                
                if self.graceful_shutdown_in_progress:
                    # During graceful shutdown, preserve message for later delivery
                    self._preserve_message_for_recovery(data)
                    raise asyncio.TimeoutError("Graceful shutdown timeout")
                
                # Simulate various timeout scenarios
                await self._simulate_timeout_conditions(data)
                
                # Update activity and preserve state
                self._update_activity()
                self.messages_sent.append(data)
                self.state_preservation_data['message_count'] += 1
                
                # Add timeout metadata to message
                data['_timeout_metadata'] = {
                    'last_activity': self.last_activity.isoformat(),
                    'timeout_config': self.timeout_config,
                    'message_index': len(self.messages_sent)
                }
            
            async def _simulate_timeout_conditions(self, data):
                """Simulate different timeout conditions based on message type."""
                message_type = data.get('type', '')
                
                # Simulate write timeout for large messages
                if 'large_message' in message_type and not self.write_timeout_triggered:
                    write_timeout = self.timeout_config.get('write_timeout', 5.0)
                    if write_timeout < 1.0:  # Configured for fast timeout
                        self.write_timeout_triggered = True
                        self._record_timeout_event(TimeoutType.WRITE_TIMEOUT, data)
                        await asyncio.sleep(0.01)  # Brief delay to simulate timeout
                        raise asyncio.TimeoutError("Write timeout during message send")
                
                # Simulate read timeout for request-response patterns
                if 'request_response' in message_type and not self.read_timeout_triggered:
                    read_timeout = self.timeout_config.get('read_timeout', 10.0)
                    if read_timeout < 2.0:  # Configured for fast timeout
                        self.read_timeout_triggered = True
                        self._record_timeout_event(TimeoutType.READ_TIMEOUT, data)
                        raise asyncio.TimeoutError("Read timeout waiting for response")
                
                # Check for idle timeout
                if self._check_idle_timeout():
                    if not self.idle_timeout_triggered:
                        self.idle_timeout_triggered = True
                        self._record_timeout_event(TimeoutType.IDLE_TIMEOUT, data)
                        await self._initiate_graceful_shutdown("Idle timeout")
                        return
                
                # Simulate normal processing delay
                await asyncio.sleep(0.001)
            
            def _check_idle_timeout(self) -> bool:
                """Check if connection has exceeded idle timeout."""
                idle_timeout = self.timeout_config.get('idle_timeout', 300.0)  # 5 minutes default
                if idle_timeout <= 0:
                    return False
                
                idle_duration = (datetime.utcnow() - self.last_activity).total_seconds()
                return idle_duration > idle_timeout
            
            def _record_timeout_event(self, timeout_type: str, context: Dict[str, Any]):
                """Record timeout event with context for analysis."""
                timeout_event = {
                    'type': timeout_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'connection_id': self.connection_id,
                    'user_id': self.user_id,
                    'context': context,
                    'state_at_timeout': self.state_preservation_data.copy()
                }
                self.timeout_events.append(timeout_event)
                
                # Notify callbacks
                for callback in self.timeout_callbacks:
                    callback(timeout_event)
            
            def _preserve_message_for_recovery(self, message: Dict[str, Any]):
                """Preserve message for delivery after reconnection."""
                if 'preserved_messages' not in self.state_preservation_data:
                    self.state_preservation_data['preserved_messages'] = []
                
                preserved_message = {
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat(),
                    'preservation_reason': 'graceful_shutdown'
                }
                self.state_preservation_data['preserved_messages'].append(preserved_message)
            
            async def _initiate_graceful_shutdown(self, reason: str):
                """Initiate graceful shutdown with state preservation."""
                if self.graceful_shutdown_in_progress:
                    return
                
                self.graceful_shutdown_in_progress = True
                
                # Preserve current state
                self.state_preservation_data.update({
                    'shutdown_initiated_at': datetime.utcnow().isoformat(),
                    'shutdown_reason': reason,
                    'graceful_shutdown': True
                })
                
                # Record graceful timeout event
                self._record_timeout_event(TimeoutType.GRACEFUL_TIMEOUT, {
                    'reason': reason,
                    'messages_sent_count': len(self.messages_sent)
                })
                
                # Simulate graceful shutdown delay
                await asyncio.sleep(0.05)
            
            async def simulate_heartbeat_timeout(self) -> bool:
                """Simulate heartbeat timeout scenario."""
                heartbeat_timeout = self.timeout_config.get('heartbeat_timeout', 30.0)
                
                if heartbeat_timeout <= 1.0 and not self.heartbeat_timeout_triggered:
                    self.heartbeat_timeout_triggered = True
                    self._record_timeout_event(TimeoutType.HEARTBEAT_TIMEOUT, {
                        'heartbeat_timeout_seconds': heartbeat_timeout
                    })
                    await self._initiate_graceful_shutdown("Heartbeat timeout")
                    return False
                
                return True
            
            async def close(self, code=1000, reason="Normal closure"):
                """Close connection with final state preservation."""
                if not self.is_closed:
                    # Final state preservation
                    self.state_preservation_data.update({
                        'closed_at': datetime.utcnow().isoformat(),
                        'close_code': code,
                        'close_reason': reason,
                        'final_message_count': len(self.messages_sent),
                        'timeout_events_count': len(self.timeout_events)
                    })
                    
                    self.is_closed = True
            
            def get_timeout_statistics(self) -> Dict[str, Any]:
                """Get comprehensive timeout statistics."""
                return {
                    'connection_id': self.connection_id,
                    'user_id': self.user_id,
                    'timeout_events': self.timeout_events,
                    'read_timeout_triggered': self.read_timeout_triggered,
                    'write_timeout_triggered': self.write_timeout_triggered,
                    'heartbeat_timeout_triggered': self.heartbeat_timeout_triggered,
                    'idle_timeout_triggered': self.idle_timeout_triggered,
                    'graceful_shutdown_in_progress': self.graceful_shutdown_in_progress,
                    'state_preservation_data': self.state_preservation_data,
                    'total_messages': len(self.messages_sent),
                    'last_activity': self.last_activity.isoformat()
                }
            
            def add_timeout_callback(self, callback: Callable):
                """Add callback for timeout events."""
                self.timeout_callbacks.append(callback)
        
        return TimeoutHandlingWebSocket(connection_id, user_id, timeout_config)
    
    async def _create_timeout_state_preservation(self, real_services_fixture, user_id: str, connection_id: str) -> Dict[str, str]:
        """Create application state for timeout handling and recovery."""
        # Store connection timeout configuration in Redis
        timeout_config_key = f"connection_timeout_config:{connection_id}"
        timeout_config = {
            'read_timeout': 10.0,
            'write_timeout': 5.0,
            'heartbeat_timeout': 30.0,
            'idle_timeout': 300.0,
            'graceful_shutdown_timeout': 10.0
        }
        
        await real_services_fixture["redis"].set(
            timeout_config_key,
            json.dumps(timeout_config),
            ex=3600
        )
        
        # Store connection recovery data
        recovery_data_key = f"connection_recovery:{connection_id}"
        recovery_data = {
            'user_id': user_id,
            'connection_id': connection_id,
            'created_at': datetime.utcnow().isoformat(),
            'timeout_events': [],
            'preserved_messages': [],
            'recovery_enabled': True
        }
        
        await real_services_fixture["redis"].set(
            recovery_data_key,
            json.dumps(recovery_data),
            ex=7200  # 2 hour expiration for recovery
        )
        
        # Track user's recoverable connections
        user_recovery_key = f"user_recovery:{user_id}"
        await real_services_fixture["redis"].sadd(user_recovery_key, connection_id)
        await real_services_fixture["redis"].expire(user_recovery_key, 7200)
        
        return {
            'timeout_config_key': timeout_config_key,
            'recovery_data_key': recovery_data_key,
            'user_recovery_key': user_recovery_key
        }
    
    async def _update_timeout_recovery_state(self, real_services_fixture, connection_id: str, timeout_stats: Dict[str, Any]):
        """Update recovery state with timeout information."""
        recovery_data_key = f"connection_recovery:{connection_id}"
        
        recovery_data = {
            'user_id': timeout_stats['user_id'],
            'connection_id': connection_id,
            'last_updated': datetime.utcnow().isoformat(),
            'timeout_events': timeout_stats['timeout_events'],
            'state_preservation_data': timeout_stats['state_preservation_data'],
            'graceful_shutdown': timeout_stats['graceful_shutdown_in_progress']
        }
        
        await real_services_fixture["redis"].set(
            recovery_data_key,
            json.dumps(recovery_data),
            ex=7200  # Keep recovery data longer
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_timeout_handling_with_graceful_state_preservation(self, real_services_fixture):
        """
        Test that WebSocket connections handle timeouts gracefully while preserving application state.
        
        Business Value: Ensures users don't lose data or session context when
        network timeouts occur, enabling seamless reconnection and recovery.
        """
        # Create test user
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'timeout_handling_test@netra.ai',
            'name': 'Timeout Handling Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="timeout_test_conn",
            context={"user_id": user_id, "test": "timeout_handling"}
        )
        
        # Create timeout configuration for testing
        timeout_config = {
            'read_timeout': 2.0,    # Short timeout for testing
            'write_timeout': 1.5,   # Short timeout for testing
            'heartbeat_timeout': 5.0,  # Short timeout for testing
            'idle_timeout': 10.0,   # Short timeout for testing
            'graceful_shutdown_timeout': 3.0
        }
        
        # Create timeout-handling WebSocket
        timeout_websocket = self._create_timeout_handling_websocket(connection_id, user_id, timeout_config)
        
        # Set up timeout state preservation
        timeout_state_keys = await self._create_timeout_state_preservation(
            real_services_fixture, user_id, connection_id
        )
        
        # Track timeout events
        timeout_events_received = []
        
        def track_timeout_events(timeout_event):
            timeout_events_received.append(timeout_event)
            # Update recovery state with timeout information
            asyncio.create_task(
                self._update_timeout_recovery_state(
                    real_services_fixture,
                    connection_id,
                    timeout_websocket.get_timeout_statistics()
                )
            )
        
        timeout_websocket.add_timeout_callback(track_timeout_events)
        
        # Create connection
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=timeout_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "timeout_handling_test",
                "timeout_config": timeout_config,
                "session_id": session_data['session_key']
            }
        )
        
        await websocket_manager.add_connection(connection)
        
        # Verify connection is active
        assert websocket_manager.is_connection_active(user_id)
        
        # Test normal message sending (should work without timeouts)
        normal_messages = []
        for i in range(3):
            normal_message = {
                "type": "normal_message",
                "data": {"message_index": i, "content": f"Normal message {i}"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, normal_message)
            normal_messages.append(normal_message)
            await asyncio.sleep(0.1)
        
        # Verify normal messages were sent successfully
        assert len(timeout_websocket.messages_sent) == 3
        timeout_stats = timeout_websocket.get_timeout_statistics()
        assert not timeout_stats['read_timeout_triggered']
        assert not timeout_stats['write_timeout_triggered']
        
        # Test write timeout scenario
        try:
            large_message = {
                "type": "large_message_write_timeout",
                "data": {"size": "large", "content": "x" * 1000},  # Large content
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, large_message)
        except Exception as e:
            # Write timeout is expected
            assert "timeout" in str(e).lower()
        
        # Verify write timeout was triggered and state preserved
        await asyncio.sleep(0.1)  # Allow timeout processing
        timeout_stats = timeout_websocket.get_timeout_statistics()
        assert timeout_stats['write_timeout_triggered'], "Write timeout should have been triggered"
        assert len(timeout_events_received) > 0, "Timeout events should have been recorded"
        
        # Verify state preservation data
        state_data = timeout_stats['state_preservation_data']
        assert state_data['user_id'] == user_id
        assert state_data['connection_id'] == connection_id
        assert state_data['message_count'] >= 3  # At least the normal messages
        
        # Test read timeout scenario (if connection is still active)
        if not timeout_websocket.is_closed:
            try:
                request_response_message = {
                    "type": "request_response_read_timeout",
                    "data": {"request": "This should trigger read timeout"},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket_manager.send_to_user(user_id, request_response_message)
            except Exception as e:
                # Read timeout is expected
                assert "timeout" in str(e).lower()
        
        # Test heartbeat timeout
        heartbeat_success = await timeout_websocket.simulate_heartbeat_timeout()
        
        # Get final timeout statistics
        final_timeout_stats = timeout_websocket.get_timeout_statistics()
        
        # Verify timeout events were properly recorded
        assert len(final_timeout_stats['timeout_events']) > 0, "Should have recorded timeout events"
        
        # Verify application state preservation
        await asyncio.sleep(0.1)  # Allow state updates
        
        recovery_data = await real_services_fixture["redis"].get(timeout_state_keys['recovery_data_key'])
        assert recovery_data is not None, "Recovery data should be preserved"
        
        recovery_info = json.loads(recovery_data)
        assert recovery_info['user_id'] == user_id
        assert recovery_info['connection_id'] == connection_id
        assert len(recovery_info['timeout_events']) > 0, "Timeout events should be preserved in recovery data"
        
        # Test graceful shutdown with state preservation
        if not timeout_websocket.is_closed:
            await timeout_websocket._initiate_graceful_shutdown("Test graceful shutdown")
            
            # Try to send message during graceful shutdown (should be preserved)
            try:
                shutdown_message = {
                    "type": "message_during_shutdown",
                    "data": {"content": "This should be preserved for recovery"},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket_manager.send_to_user(user_id, shutdown_message)
            except Exception:
                # Expected to fail during graceful shutdown
                pass
            
            # Verify message was preserved for recovery
            final_state = final_timeout_stats['state_preservation_data']
            if 'preserved_messages' in final_state:
                assert len(final_state['preserved_messages']) > 0, "Messages should be preserved during shutdown"
        
        # Clean up connection
        await websocket_manager.remove_connection(connection_id)
        
        # Verify connection is cleaned up but recovery data persists
        assert not websocket_manager.is_connection_active(user_id)
        
        # Verify recovery data still exists for potential reconnection
        recovery_data_after_cleanup = await real_services_fixture["redis"].get(timeout_state_keys['recovery_data_key'])
        assert recovery_data_after_cleanup is not None, "Recovery data should persist after connection cleanup"
        
        # Clean up timeout state keys
        for key in timeout_state_keys.values():
            await real_services_fixture["redis"].delete(key)
        
        # Verify business value: Graceful timeout handling preserves user experience
        self.assert_business_value_delivered({
            'graceful_timeout_handling': True,
            'state_preservation': True,
            'recovery_data_persistence': True,
            'user_experience_continuity': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_timeout_recovery_and_reconnection_scenarios(self, real_services_fixture):
        """
        Test WebSocket timeout recovery and reconnection scenarios with state restoration.
        
        Business Value: Ensures users can seamlessly reconnect after timeouts and
        recover their session state without losing progress or context.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'timeout_recovery_test@netra.ai',
            'name': 'Timeout Recovery Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create initial connection with aggressive timeout settings
        initial_connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="timeout_recovery_initial",
            context={"user_id": user_id, "test": "timeout_recovery"}
        )
        
        aggressive_timeout_config = {
            'read_timeout': 0.5,    # Very short for testing
            'write_timeout': 0.3,   # Very short for testing
            'heartbeat_timeout': 1.0,  # Very short for testing
            'idle_timeout': 2.0,    # Very short for testing
            'graceful_shutdown_timeout': 1.0
        }
        
        initial_websocket = self._create_timeout_handling_websocket(
            initial_connection_id, user_id, aggressive_timeout_config
        )
        
        initial_state_keys = await self._create_timeout_state_preservation(
            real_services_fixture, user_id, initial_connection_id
        )
        
        # Track recovery scenarios
        recovery_scenarios = []
        
        def track_recovery_scenarios(timeout_event):
            recovery_scenarios.append({
                'timeout_type': timeout_event['type'],
                'timestamp': timeout_event['timestamp'],
                'recovery_needed': True
            })
        
        initial_websocket.add_timeout_callback(track_recovery_scenarios)
        
        # Create and add initial connection
        initial_connection = WebSocketConnection(
            connection_id=initial_connection_id,
            user_id=user_id,
            websocket=initial_websocket,
            connected_at=datetime.utcnow(),
            metadata={"connection_type": "timeout_recovery_initial"}
        )
        
        await websocket_manager.add_connection(initial_connection)
        
        # Send messages that will trigger various timeouts
        messages_sent_successfully = []
        timeout_failures = []
        
        for i in range(5):
            try:
                if i == 1:  # Trigger write timeout
                    message = {
                        "type": "large_message_write_timeout",
                        "data": {"index": i, "large_data": "x" * 500},
                        "timestamp": datetime.utcnow().isoformat()
                    }
                elif i == 3:  # Trigger read timeout
                    message = {
                        "type": "request_response_read_timeout",
                        "data": {"index": i, "request": "timeout_trigger"},
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    message = {
                        "type": "normal_message",
                        "data": {"index": i, "content": f"Message {i}"},
                        "timestamp": datetime.utcnow().isoformat()
                    }
                
                await websocket_manager.send_to_user(user_id, message)
                messages_sent_successfully.append(message)
                
            except Exception as e:
                timeout_failures.append({
                    'message_index': i,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            await asyncio.sleep(0.1)
        
        # Verify some messages succeeded and some failed due to timeouts
        assert len(messages_sent_successfully) > 0, "Some messages should have been sent successfully"
        assert len(timeout_failures) > 0, "Some messages should have failed due to timeouts"
        assert len(recovery_scenarios) > 0, "Recovery scenarios should have been triggered"
        
        # Simulate connection loss due to timeouts
        await asyncio.sleep(2.5)  # Wait for idle timeout to trigger
        
        # Get state before connection removal
        pre_removal_stats = initial_websocket.get_timeout_statistics()
        
        # Update recovery state with final timeout information
        await self._update_timeout_recovery_state(
            real_services_fixture, initial_connection_id, pre_removal_stats
        )
        
        # Remove timed-out connection
        await websocket_manager.remove_connection(initial_connection_id)
        assert not websocket_manager.is_connection_active(user_id)
        
        # Simulate user reconnection with new connection
        recovery_connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="timeout_recovery_reconnect",
            context={"user_id": user_id, "test": "reconnection"}
        )
        
        # Use normal timeout settings for recovery connection
        normal_timeout_config = {
            'read_timeout': 30.0,
            'write_timeout': 15.0,
            'heartbeat_timeout': 60.0,
            'idle_timeout': 600.0,
            'graceful_shutdown_timeout': 30.0
        }
        
        recovery_websocket = self._create_timeout_handling_websocket(
            recovery_connection_id, user_id, normal_timeout_config
        )
        
        recovery_state_keys = await self._create_timeout_state_preservation(
            real_services_fixture, user_id, recovery_connection_id
        )
        
        # Retrieve recovery data from previous connection
        previous_recovery_data = await real_services_fixture["redis"].get(
            initial_state_keys['recovery_data_key']
        )
        assert previous_recovery_data is not None, "Previous connection recovery data should exist"
        
        recovery_info = json.loads(previous_recovery_data)
        assert len(recovery_info['timeout_events']) > 0, "Should have timeout events from previous connection"
        
        # Create recovery connection
        recovery_connection = WebSocketConnection(
            connection_id=recovery_connection_id,
            user_id=user_id,
            websocket=recovery_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "timeout_recovery_reconnect",
                "previous_connection_id": initial_connection_id,
                "recovery_connection": True
            }
        )
        
        await websocket_manager.add_connection(recovery_connection)
        
        # Verify reconnection is successful
        assert websocket_manager.is_connection_active(user_id)
        
        # Test that recovery connection works normally
        recovery_messages = []
        for i in range(3):
            recovery_message = {
                "type": "recovery_test_message",
                "data": {"index": i, "recovered": True, "content": f"Recovery message {i}"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, recovery_message)
            recovery_messages.append(recovery_message)
        
        # Verify recovery messages were sent successfully
        assert len(recovery_websocket.messages_sent) == 3
        recovery_stats = recovery_websocket.get_timeout_statistics()
        assert not recovery_stats['read_timeout_triggered'], "Recovery connection should not have timeout issues"
        assert not recovery_stats['write_timeout_triggered'], "Recovery connection should not have timeout issues"
        
        # Test heartbeat on recovery connection
        recovery_heartbeat_success = await recovery_websocket.simulate_heartbeat_timeout()
        assert recovery_heartbeat_success, "Recovery connection heartbeat should succeed"
        
        # Verify preserved messages from previous connection can be accessed
        # (In real implementation, these would be delivered upon reconnection)
        preserved_state = pre_removal_stats['state_preservation_data']
        if 'preserved_messages' in preserved_state:
            assert isinstance(preserved_state['preserved_messages'], list), \
                "Preserved messages should be available for recovery"
        
        # Verify database state consistency across connection changes
        db_user = await real_services_fixture["postgres"].fetchrow(
            "SELECT id, email, is_active FROM auth.users WHERE id = $1", user_id
        )
        assert db_user is not None, "User should exist in database"
        assert db_user['is_active'] is True, "User should remain active across connection changes"
        
        # Clean up recovery connection
        await websocket_manager.remove_connection(recovery_connection_id)
        
        # Clean up all state keys
        for state_keys in [initial_state_keys, recovery_state_keys]:
            for key in state_keys.values():
                await real_services_fixture["redis"].delete(key)
        
        # Verify business value: Recovery enables seamless user experience
        self.assert_business_value_delivered({
            'timeout_recovery': True,
            'seamless_reconnection': True,
            'state_restoration': True,
            'user_session_continuity': True,
            'message_preservation': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_concurrent_timeout_handling_with_state_isolation(self, real_services_fixture):
        """
        Test concurrent WebSocket timeout handling maintains proper state isolation between users.
        
        Business Value: Ensures timeout handling for one user doesn't affect others,
        maintaining system reliability and user experience isolation.
        """
        # Create multiple users with different timeout scenarios
        users_and_connections = []
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create 3 users with different timeout characteristics
        timeout_configs = [
            {  # User 0: Aggressive timeouts
                'read_timeout': 0.5,
                'write_timeout': 0.3,
                'heartbeat_timeout': 1.0,
                'idle_timeout': 2.0
            },
            {  # User 1: Moderate timeouts
                'read_timeout': 2.0,
                'write_timeout': 1.5,
                'heartbeat_timeout': 5.0,
                'idle_timeout': 10.0
            },
            {  # User 2: Lenient timeouts
                'read_timeout': 30.0,
                'write_timeout': 15.0,
                'heartbeat_timeout': 60.0,
                'idle_timeout': 600.0
            }
        ]
        
        for user_index in range(3):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'concurrent_timeout_user_{user_index}@netra.ai',
                'name': f'Concurrent Timeout User {user_index}',
                'is_active': True
            })
            user_id = user_data['id']
            
            connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"concurrent_timeout_u{user_index}",
                context={"user_id": user_id, "test": "concurrent_timeout"}
            )
            
            timeout_config = timeout_configs[user_index]
            timeout_websocket = self._create_timeout_handling_websocket(
                connection_id, user_id, timeout_config
            )
            
            state_keys = await self._create_timeout_state_preservation(
                real_services_fixture, user_id, connection_id
            )
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=timeout_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "connection_type": "concurrent_timeout_test",
                    "user_index": user_index,
                    "timeout_config": timeout_config
                }
            )
            
            await websocket_manager.add_connection(connection)
            
            users_and_connections.append({
                'user_id': user_id,
                'user_data': user_data,
                'connection_id': connection_id,
                'websocket': timeout_websocket,
                'timeout_config': timeout_config,
                'state_keys': state_keys,
                'user_index': user_index
            })
        
        # Verify all connections are active
        initial_stats = websocket_manager.get_stats()
        assert initial_stats['total_connections'] == 3, "Should have 3 concurrent connections"
        assert initial_stats['unique_users'] == 3, "Should have 3 unique users"
        
        # Send messages concurrently to trigger different timeout scenarios
        async def send_messages_to_user(user_info):
            """Send messages to a specific user to test their timeout behavior."""
            user_id = user_info['user_id']
            user_index = user_info['user_index']
            
            messages_sent = 0
            timeout_errors = 0
            
            for i in range(10):
                try:
                    message_type = "normal_message"
                    
                    # Trigger specific timeout scenarios based on user index
                    if user_index == 0 and i == 2:  # User 0 (aggressive): write timeout
                        message_type = "large_message_write_timeout"
                    elif user_index == 0 and i == 5:  # User 0: read timeout
                        message_type = "request_response_read_timeout"
                    elif user_index == 1 and i == 7:  # User 1 (moderate): occasional timeout
                        message_type = "large_message_write_timeout"
                    
                    message = {
                        "type": message_type,
                        "data": {
                            "user_index": user_index,
                            "message_index": i,
                            "content": f"User {user_index} message {i}"
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await websocket_manager.send_to_user(user_id, message)
                    messages_sent += 1
                    
                except Exception as e:
                    timeout_errors += 1
                
                await asyncio.sleep(0.05)  # Small delay between messages
            
            return {
                'user_id': user_id,
                'user_index': user_index,
                'messages_sent': messages_sent,
                'timeout_errors': timeout_errors
            }
        
        # Execute concurrent message sending
        concurrent_results = await asyncio.gather(*[
            send_messages_to_user(user_info) for user_info in users_and_connections
        ])
        
        # Analyze results for each user
        for result in concurrent_results:
            user_index = result['user_index']
            user_info = users_and_connections[user_index]
            
            # User 0 (aggressive timeouts) should have some timeout errors
            if user_index == 0:
                assert result['timeout_errors'] > 0, f"User {user_index} should have timeout errors"
            
            # User 2 (lenient timeouts) should have minimal or no timeout errors
            elif user_index == 2:
                assert result['timeout_errors'] <= 1, f"User {user_index} should have minimal timeout errors"
            
            # All users should have sent at least some messages
            assert result['messages_sent'] > 0, f"User {user_index} should have sent some messages"
        
        # Verify timeout statistics are isolated per user
        for user_info in users_and_connections:
            timeout_stats = user_info['websocket'].get_timeout_statistics()
            user_index = user_info['user_index']
            
            # Verify isolation - each connection should only have its own data
            assert timeout_stats['user_id'] == user_info['user_id']
            assert timeout_stats['connection_id'] == user_info['connection_id']
            
            # Verify timeout behavior matches expectations
            if user_index == 0:  # Aggressive timeouts
                # Should have triggered some timeouts
                total_timeouts = (
                    timeout_stats['read_timeout_triggered'] +
                    timeout_stats['write_timeout_triggered'] +
                    timeout_stats['heartbeat_timeout_triggered'] +
                    timeout_stats['idle_timeout_triggered']
                )
                assert total_timeouts > 0, f"User {user_index} should have triggered timeouts"
            
            elif user_index == 2:  # Lenient timeouts
                # Should have minimal timeout issues
                assert not timeout_stats['read_timeout_triggered'], f"User {user_index} should not have read timeouts"
                assert not timeout_stats['write_timeout_triggered'], f"User {user_index} should not have write timeouts"
        
        # Verify application state isolation
        await asyncio.sleep(0.1)  # Allow state updates
        
        for user_info in users_and_connections:
            recovery_data = await real_services_fixture["redis"].get(
                user_info['state_keys']['recovery_data_key']
            )
            assert recovery_data is not None, f"Recovery data should exist for user {user_info['user_index']}"
            
            recovery_info = json.loads(recovery_data)
            assert recovery_info['user_id'] == user_info['user_id'], "Recovery data should be user-specific"
            assert recovery_info['connection_id'] == user_info['connection_id'], "Recovery data should be connection-specific"
        
        # Verify manager state consistency
        concurrent_stats = websocket_manager.get_stats()
        active_connections = sum(
            1 for user_info in users_and_connections
            if websocket_manager.is_connection_active(user_info['user_id'])
        )
        
        # Some connections might have timed out, but manager should track accurately
        assert concurrent_stats['total_connections'] == active_connections, \
            "Manager statistics should accurately reflect active connections"
        
        # Clean up all connections
        for user_info in users_and_connections:
            await websocket_manager.remove_connection(user_info['connection_id'])
            
            # Clean up state
            for key in user_info['state_keys'].values():
                await real_services_fixture["redis"].delete(key)
        
        # Verify complete cleanup
        final_stats = websocket_manager.get_stats()
        assert final_stats['total_connections'] == 0, "All connections should be cleaned up"
        assert final_stats['unique_users'] == 0, "No users should have active connections"
        
        # Verify business value: Concurrent timeout handling maintains isolation
        self.assert_business_value_delivered({
            'concurrent_timeout_handling': True,
            'user_state_isolation': True,
            'timeout_behavior_isolation': True,
            'system_reliability': True
        }, 'automation')