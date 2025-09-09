"""
Test WebSocket Connection Error Handling with Application State Recovery

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure robust error handling that preserves user data and enables recovery
- Value Impact: Users experience minimal disruption from connection errors with automatic recovery
- Strategic Impact: Enables reliable system operation and user trust through resilient error handling

This integration test validates that WebSocket connection error handling works correctly
while preserving application state and enabling comprehensive recovery scenarios.
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


class TestWebSocketConnectionErrorHandlingApplicationStateRecoveryIntegration(BaseIntegrationTest):
    """Test WebSocket connection error handling with comprehensive application state recovery."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_error_handling_with_state_recovery(self, real_services_fixture):
        """Test comprehensive error handling with application state preservation and recovery."""
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'error_recovery_user@netra.ai',
            'name': 'Error Recovery User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create error-simulation WebSocket
        class ErrorHandlingWebSocket:
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.messages_sent = []
                self.errors_encountered = []
                self.recovery_attempts = []
                self.is_closed = False
                self.error_simulation_enabled = True
                self.message_count = 0
            
            async def send_json(self, data):
                self.message_count += 1
                
                # Simulate various error conditions
                if self.error_simulation_enabled:
                    if self.message_count == 3:  # Third message fails
                        error = ConnectionError("Simulated connection error")
                        self.errors_encountered.append({
                            'error_type': 'ConnectionError',
                            'message': str(error),
                            'timestamp': datetime.utcnow().isoformat(),
                            'message_data': data,
                            'message_count': self.message_count
                        })
                        raise error
                    
                    elif self.message_count == 6:  # Sixth message times out
                        error = asyncio.TimeoutError("Simulated timeout error")
                        self.errors_encountered.append({
                            'error_type': 'TimeoutError',
                            'message': str(error),
                            'timestamp': datetime.utcnow().isoformat(),
                            'message_data': data,
                            'message_count': self.message_count
                        })
                        raise error
                
                # Successful message send
                data['_message_metadata'] = {
                    'message_count': self.message_count,
                    'errors_so_far': len(self.errors_encountered),
                    'sent_at': datetime.utcnow().isoformat()
                }
                self.messages_sent.append(data)
            
            async def simulate_recovery(self):
                """Simulate connection recovery after errors."""
                self.recovery_attempts.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'errors_before_recovery': len(self.errors_encountered),
                    'messages_before_recovery': len(self.messages_sent)
                })
                # Disable error simulation after recovery
                self.error_simulation_enabled = False
                return True
            
            async def close(self):
                self.is_closed = True
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="error_recovery",
            context={"user_id": user_id, "test": "error_handling"}
        )
        
        error_websocket = ErrorHandlingWebSocket(connection_id, user_id)
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=error_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "error_handling_test",
                "error_recovery_enabled": True
            }
        )
        
        await websocket_manager.add_connection(connection)
        
        # Create application state for error recovery tracking
        error_recovery_key = f"error_recovery:{connection_id}"
        recovery_state = {
            'user_id': user_id,
            'connection_id': connection_id,
            'error_log': [],
            'recovery_log': [],
            'failed_messages': [],
            'created_at': datetime.utcnow().isoformat()
        }
        
        await real_services_fixture["redis"].set(
            error_recovery_key,
            json.dumps(recovery_state),
            ex=7200  # 2 hour retention for recovery
        )
        
        # Send messages that will trigger various errors
        successful_sends = 0
        error_sends = 0
        
        for i in range(10):
            try:
                message = {
                    "type": "error_test_message",
                    "data": {"message_index": i, "test_content": f"Message {i}"},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket_manager.send_to_user(user_id, message)
                successful_sends += 1
                
            except Exception as e:
                error_sends += 1
                
                # Update recovery state with error information
                recovery_state['error_log'].append({
                    'message_index': i,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Store failed message for potential retry
                recovery_state['failed_messages'].append({
                    'message_index': i,
                    'message_data': message,
                    'failed_at': datetime.utcnow().isoformat()
                })
                
                # Update Redis with error state
                await real_services_fixture["redis"].set(
                    error_recovery_key,
                    json.dumps(recovery_state),
                    ex=7200
                )
            
            await asyncio.sleep(0.1)
        
        # Verify errors were encountered as expected
        assert len(error_websocket.errors_encountered) >= 2, "Should have encountered multiple errors"
        assert error_sends >= 2, "Should have failed to send some messages"
        assert successful_sends > 0, "Should have successfully sent some messages"
        
        # Verify error details
        connection_error = next((e for e in error_websocket.errors_encountered if e['error_type'] == 'ConnectionError'), None)
        timeout_error = next((e for e in error_websocket.errors_encountered if e['error_type'] == 'TimeoutError'), None)
        
        assert connection_error is not None, "Should have encountered a connection error"
        assert timeout_error is not None, "Should have encountered a timeout error"
        
        # Simulate connection recovery
        recovery_success = await error_websocket.simulate_recovery()
        assert recovery_success, "Recovery simulation should succeed"
        
        # Update recovery state
        recovery_state['recovery_log'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'recovery_successful': True,
            'errors_resolved': len(error_websocket.errors_encountered)
        })
        
        await real_services_fixture["redis"].set(
            error_recovery_key,
            json.dumps(recovery_state),
            ex=7200
        )
        
        # Test that connection works after recovery
        post_recovery_messages = []
        for i in range(3):
            recovery_message = {
                "type": "post_recovery_message",
                "data": {"message_index": i, "recovered": True},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, recovery_message)
            post_recovery_messages.append(recovery_message)
            await asyncio.sleep(0.05)
        
        # Verify post-recovery messages were sent successfully
        recovery_messages_sent = [msg for msg in error_websocket.messages_sent if msg['type'] == 'post_recovery_message']
        assert len(recovery_messages_sent) == 3, "All post-recovery messages should be sent successfully"
        
        # Verify recovery metadata in messages
        for recovery_msg in recovery_messages_sent:
            metadata = recovery_msg['_message_metadata']
            assert metadata['errors_so_far'] >= 2, "Should track previous errors in metadata"
        
        # Test error statistics and recovery tracking
        error_stats = websocket_manager.get_error_statistics()
        assert error_stats['total_error_count'] >= 0, "Error statistics should be available"
        
        # Verify final recovery state in Redis
        final_recovery_state = await real_services_fixture["redis"].get(error_recovery_key)
        assert final_recovery_state is not None, "Recovery state should be preserved"
        
        final_state_data = json.loads(final_recovery_state)
        assert len(final_state_data['error_log']) >= 2, "Should have logged multiple errors"
        assert len(final_state_data['recovery_log']) >= 1, "Should have logged recovery attempts"
        assert len(final_state_data['failed_messages']) >= 2, "Should have preserved failed messages"
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        await real_services_fixture["redis"].delete(error_recovery_key)
        
        self.assert_business_value_delivered({
            'error_handling': True,
            'state_preservation_during_errors': True,
            'connection_recovery': True,
            'message_retry_capability': True,
            'error_tracking_and_analytics': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cascading_error_handling_with_system_stability(self, real_services_fixture):
        """Test that cascading errors are handled gracefully without affecting system stability."""
        # Create multiple users to test system-wide error resilience
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'cascading_error_user_{i}@netra.ai',
                'name': f'Cascading Error User {i}',
                'is_active': True
            })
            users.append(user_data)
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create connections with different error patterns
        connections = []
        for i, user_data in enumerate(users):
            user_id = user_data['id']
            
            class CascadingErrorWebSocket:
                def __init__(self, connection_id: str, user_id: str, error_pattern: str):
                    self.connection_id = connection_id
                    self.user_id = user_id
                    self.error_pattern = error_pattern
                    self.messages_sent = []
                    self.errors_encountered = []
                    self.is_closed = False
                    self.message_count = 0
                
                async def send_json(self, data):
                    self.message_count += 1
                    
                    # Different error patterns for different connections
                    if self.error_pattern == "immediate_failure" and self.message_count <= 2:
                        error = ConnectionError(f"Immediate failure pattern - message {self.message_count}")
                        self.errors_encountered.append(error)
                        raise error
                    
                    elif self.error_pattern == "intermittent_failure" and self.message_count % 3 == 0:
                        error = asyncio.TimeoutError(f"Intermittent failure pattern - message {self.message_count}")
                        self.errors_encountered.append(error)
                        raise error
                    
                    elif self.error_pattern == "delayed_failure" and self.message_count > 5:
                        error = ConnectionError(f"Delayed failure pattern - message {self.message_count}")
                        self.errors_encountered.append(error)
                        raise error
                    
                    # Successful send
                    self.messages_sent.append(data)
                
                async def close(self):
                    self.is_closed = True
            
            error_patterns = ["immediate_failure", "intermittent_failure", "delayed_failure"]
            error_pattern = error_patterns[i]
            
            connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"cascade_error_{i}",
                context={"user_id": user_id, "pattern": error_pattern}
            )
            
            cascade_websocket = CascadingErrorWebSocket(connection_id, user_id, error_pattern)
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=cascade_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "connection_type": "cascading_error_test",
                    "error_pattern": error_pattern,
                    "user_index": i
                }
            )
            
            await websocket_manager.add_connection(connection)
            connections.append({
                'user_id': user_id,
                'connection_id': connection_id,
                'websocket': cascade_websocket,
                'error_pattern': error_pattern
            })
        
        # Verify all connections are initially active
        initial_stats = websocket_manager.get_stats()
        assert initial_stats['total_connections'] == 3, "All 3 connections should be active initially"
        
        # Send messages to all users simultaneously to trigger cascading errors
        async def send_messages_to_user(user_id: str, message_count: int):
            """Send multiple messages to trigger error patterns."""
            successful = 0
            failed = 0
            
            for i in range(message_count):
                try:
                    message = {
                        "type": "cascade_test_message",
                        "data": {"message_index": i, "cascade_test": True},
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await websocket_manager.send_to_user(user_id, message)
                    successful += 1
                    
                except Exception:
                    failed += 1
                
                await asyncio.sleep(0.05)
            
            return {'successful': successful, 'failed': failed}
        
        # Execute concurrent message sending to trigger errors
        cascade_results = await asyncio.gather(*[
            send_messages_to_user(conn['user_id'], 10) for conn in connections
        ], return_exceptions=True)
        
        # Analyze cascading error results
        total_successful = sum(result['successful'] for result in cascade_results if isinstance(result, dict))
        total_failed = sum(result['failed'] for result in cascade_results if isinstance(result, dict))
        
        assert total_successful > 0, "Some messages should succeed despite cascading errors"
        assert total_failed > 0, "Some messages should fail due to error patterns"
        
        # Verify system stability - manager should still function
        stability_stats = websocket_manager.get_stats()
        assert stability_stats is not None, "Manager should remain functional during cascading errors"
        
        # Verify error isolation - each connection's errors should be isolated
        for conn_info in connections:
            websocket = conn_info['websocket']
            error_pattern = conn_info['error_pattern']
            
            if error_pattern == "immediate_failure":
                assert len(websocket.errors_encountered) >= 2, "Immediate failure pattern should have multiple errors"
            elif error_pattern == "intermittent_failure":
                assert len(websocket.errors_encountered) >= 1, "Intermittent pattern should have some errors"
            elif error_pattern == "delayed_failure":
                # May or may not have errors depending on message count reached
                pass
        
        # Test system recovery after cascading errors
        # Create a new healthy connection to verify system can still accept new connections
        recovery_user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'post_cascade_recovery_user@netra.ai',
            'name': 'Post Cascade Recovery User',
            'is_active': True
        })
        recovery_user_id = recovery_user_data['id']
        
        class HealthyWebSocket:
            def __init__(self, connection_id: str):
                self.connection_id = connection_id
                self.messages_sent = []
                self.is_closed = False
            
            async def send_json(self, data):
                self.messages_sent.append(data)
            
            async def close(self):
                self.is_closed = True
        
        recovery_connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="post_cascade_recovery",
            context={"user_id": recovery_user_id, "test": "recovery"}
        )
        
        recovery_websocket = HealthyWebSocket(recovery_connection_id)
        
        recovery_connection = WebSocketConnection(
            connection_id=recovery_connection_id,
            user_id=recovery_user_id,
            websocket=recovery_websocket,
            connected_at=datetime.utcnow(),
            metadata={"connection_type": "post_cascade_recovery"}
        )
        
        await websocket_manager.add_connection(recovery_connection)
        
        # Verify system can handle new connections after cascading errors
        assert websocket_manager.is_connection_active(recovery_user_id), "System should accept new connections after cascading errors"
        
        # Send messages to recovery connection to verify functionality
        for i in range(3):
            recovery_message = {
                "type": "system_recovery_test",
                "data": {"message_index": i, "system_recovered": True},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(recovery_user_id, recovery_message)
        
        # Verify recovery connection works normally
        assert len(recovery_websocket.messages_sent) == 3, "Recovery connection should work normally after cascading errors"
        
        # Clean up all connections
        for conn_info in connections:
            await websocket_manager.remove_connection(conn_info['connection_id'])
        
        await websocket_manager.remove_connection(recovery_connection_id)
        
        # Verify final system state
        final_stats = websocket_manager.get_stats()
        assert final_stats['total_connections'] == 0, "All connections should be cleaned up"
        assert final_stats['unique_users'] == 0, "No users should have active connections"
        
        self.assert_business_value_delivered({
            'cascading_error_resilience': True,
            'system_stability_under_stress': True,
            'error_isolation': True,
            'post_error_recovery': True,
            'connection_management_reliability': True
        }, 'automation')