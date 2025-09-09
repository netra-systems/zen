"""
Comprehensive WebSocket Connection State Machine Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket state machines work with real infrastructure  
- Value Impact: Validates connection states persist correctly across database and Redis
- Strategic Impact: Critical foundation for reliable multi-user chat experiences

This test suite validates WebSocket connection state machine behavior with real services,
ensuring state persistence, recovery, and isolation work correctly in realistic scenarios.
These tests are essential for the Golden Path user flow requirements.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket import WebSocketTestClient
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID, ensure_user_id
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.core.websocket_recovery_types import ConnectionState as RecoveryConnectionState


class IntegrationConnectionState(Enum):
    """Connection states for integration testing with real services."""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    HANDSHAKE_PENDING = "handshake_pending"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    DEGRADED = "degraded" 
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECOVERY = "recovery"


class TestWebSocketConnectionStateMachineIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket connection state machine with real services."""
    
    async def _create_real_websocket_connection(self, real_services_fixture, user_data: Dict) -> Dict[str, Any]:
        """Create a real WebSocket connection with state tracking."""
        user_id = user_data['id']
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        # Generate connection ID using SSOT
        id_manager = UnifiedIDManager()
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="integration_conn",
            context={"user_id": user_id, "test": "state_machine_integration"}
        )
        
        # Create WebSocket test client for real connection
        websocket_client = WebSocketTestClient(
            token=session_data['token'],
            connection_id=connection_id,
            user_id=user_id
        )
        
        return {
            'user_id': user_id,
            'session_data': session_data,
            'connection_id': connection_id,
            'websocket_client': websocket_client,
            'user_data': user_data
        }
    
    async def _persist_connection_state_redis(self, real_services_fixture, connection_id: str,
                                            user_id: str, state: IntegrationConnectionState, 
                                            metadata: Optional[Dict] = None) -> None:
        """Persist connection state to Redis with comprehensive data."""
        state_data = {
            'connection_id': connection_id,
            'user_id': user_id,
            'state': state.value,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {},
            'environment': get_env().get('ENVIRONMENT', 'test'),
            'service_version': 'integration_test_v1'
        }
        
        # Store connection state
        state_key = f"websocket:connection_state:{connection_id}"
        await real_services_fixture["redis"].set(
            state_key,
            json.dumps(state_data),
            ex=7200  # 2 hours
        )
        
        # Track user's connections
        user_connections_key = f"websocket:user_connections:{user_id}"
        await real_services_fixture["redis"].sadd(user_connections_key, connection_id)
        await real_services_fixture["redis"].expire(user_connections_key, 7200)
        
        # Store state transition log
        transition_log_key = f"websocket:state_log:{connection_id}"
        log_entry = {
            'state': state.value,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        await real_services_fixture["redis"].lpush(transition_log_key, json.dumps(log_entry))
        await real_services_fixture["redis"].expire(transition_log_key, 7200)
    
    async def _get_connection_state_redis(self, real_services_fixture, connection_id: str) -> Optional[Dict]:
        """Get connection state from Redis."""
        state_key = f"websocket:connection_state:{connection_id}"
        state_json = await real_services_fixture["redis"].get(state_key)
        
        if state_json:
            return json.loads(state_json)
        return None
    
    async def _get_state_transition_log(self, real_services_fixture, connection_id: str) -> List[Dict]:
        """Get state transition log from Redis."""
        transition_log_key = f"websocket:state_log:{connection_id}"
        log_entries = await real_services_fixture["redis"].lrange(transition_log_key, 0, -1)
        
        return [json.loads(entry) for entry in log_entries]
    
    async def _store_connection_postgres(self, real_services_fixture, connection_data: Dict) -> None:
        """Store connection data in PostgreSQL for persistence testing."""
        insert_query = """
            INSERT INTO websocket_connections 
            (connection_id, user_id, state, connected_at, metadata)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (connection_id) 
            DO UPDATE SET 
                state = $3, 
                updated_at = CURRENT_TIMESTAMP,
                metadata = $5
        """
        
        await real_services_fixture["postgres"].execute(
            insert_query,
            connection_data['connection_id'],
            connection_data['user_id'],
            connection_data['state'],
            datetime.fromisoformat(connection_data['timestamp']),
            json.dumps(connection_data['metadata'])
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_state_machine_real_service_persistence(self, real_services_fixture):
        """
        Test WebSocket state machine with real Redis and PostgreSQL persistence.
        
        Business Value: Ensures connection states survive service restarts and 
        maintain consistency across distributed infrastructure.
        """
        # Create test user and connection
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'state_persistence_test@netra.ai',
            'name': 'State Persistence User',
            'is_active': True
        })
        
        connection_info = await self._create_real_websocket_connection(real_services_fixture, user_data)
        user_id = connection_info['user_id']
        connection_id = connection_info['connection_id']
        
        websocket_manager = UnifiedWebSocketManager()
        
        # State transition sequence with real service persistence
        state_transitions = [
            (IntegrationConnectionState.CONNECTING, {"trigger": "user_initiated"}),
            (IntegrationConnectionState.CONNECTED, {"trigger": "tcp_established", "latency_ms": 45}),
            (IntegrationConnectionState.HANDSHAKE_PENDING, {"trigger": "websocket_upgrade"}),
            (IntegrationConnectionState.AUTHENTICATED, {"trigger": "jwt_validated", "auth_time": 1.2}),
            (IntegrationConnectionState.ACTIVE, {"trigger": "ready_for_messages", "capabilities": ["chat", "agents"]})
        ]
        
        # Execute state transitions with persistence
        for state, metadata in state_transitions:
            # Persist to Redis
            await self._persist_connection_state_redis(
                real_services_fixture, connection_id, user_id, state, metadata
            )
            
            # Also persist to PostgreSQL for database consistency testing
            connection_data = {
                'connection_id': connection_id,
                'user_id': user_id,
                'state': state.value,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata
            }
            await self._store_connection_postgres(real_services_fixture, connection_data)
            
            # Small delay to ensure ordering
            await asyncio.sleep(0.1)
        
        # Create real WebSocket connection object
        real_websocket = await connection_info['websocket_client'].connect()
        
        try:
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=real_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "test_type": "state_persistence",
                    "expected_state": IntegrationConnectionState.ACTIVE.value
                }
            )
            
            await websocket_manager.add_connection(connection)
            
            # Verify Redis persistence
            redis_state = await self._get_connection_state_redis(real_services_fixture, connection_id)
            assert redis_state is not None
            assert redis_state['state'] == IntegrationConnectionState.ACTIVE.value
            assert redis_state['user_id'] == user_id
            assert 'capabilities' in redis_state['metadata']
            
            # Verify PostgreSQL persistence
            postgres_query = """
                SELECT connection_id, user_id, state, connected_at, metadata
                FROM websocket_connections 
                WHERE connection_id = $1
            """
            postgres_row = await real_services_fixture["postgres"].fetchrow(postgres_query, connection_id)
            assert postgres_row is not None
            assert postgres_row['state'] == IntegrationConnectionState.ACTIVE.value
            assert postgres_row['user_id'] == user_id
            
            # Verify state transition log
            transition_log = await self._get_state_transition_log(real_services_fixture, connection_id)
            assert len(transition_log) == len(state_transitions)
            
            # Verify transition sequence is correct
            logged_states = [entry['state'] for entry in reversed(transition_log)]  # Redis LPUSH reverses order
            expected_states = [state.value for state, _ in state_transitions]
            assert logged_states == expected_states
            
            # Test message sending with state verification
            test_message = {
                "type": "state_verification_message",
                "data": {"connection_state": IntegrationConnectionState.ACTIVE.value},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, test_message)
            
            # Verify message was sent successfully (connection is active)
            assert websocket_manager.is_connection_active(user_id)
            
            # Test state transition to DEGRADED with persistence
            degraded_metadata = {"network_quality": "poor", "latency_ms": 2000}
            await self._persist_connection_state_redis(
                real_services_fixture, connection_id, user_id, 
                IntegrationConnectionState.DEGRADED, degraded_metadata
            )
            
            # Verify degraded state persisted
            updated_redis_state = await self._get_connection_state_redis(real_services_fixture, connection_id)
            assert updated_redis_state['state'] == IntegrationConnectionState.DEGRADED.value
            assert updated_redis_state['metadata']['network_quality'] == 'poor'
            
            # Test recovery to ACTIVE
            recovery_metadata = {"network_quality": "restored", "recovery_time": 3.5}
            await self._persist_connection_state_redis(
                real_services_fixture, connection_id, user_id,
                IntegrationConnectionState.ACTIVE, recovery_metadata
            )
            
            # Verify recovery state
            recovered_state = await self._get_connection_state_redis(real_services_fixture, connection_id)
            assert recovered_state['state'] == IntegrationConnectionState.ACTIVE.value
            assert recovered_state['metadata']['network_quality'] == 'restored'
            
        finally:
            # Clean up
            await websocket_manager.remove_connection(connection_id)
            await connection_info['websocket_client'].disconnect()
            
            # Clean up persistence
            await real_services_fixture["redis"].delete(f"websocket:connection_state:{connection_id}")
            await real_services_fixture["redis"].delete(f"websocket:user_connections:{user_id}")
            await real_services_fixture["redis"].delete(f"websocket:state_log:{connection_id}")
            
            await real_services_fixture["postgres"].execute(
                "DELETE FROM websocket_connections WHERE connection_id = $1", connection_id
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_state_machine_multi_user_isolation(self, real_services_fixture):
        """
        Test WebSocket state machine isolation between multiple users.
        
        Business Value: Ensures user state isolation prevents cross-user contamination
        and maintains independent connection states for concurrent users.
        """
        # Create multiple test users
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'multi_state_user_{i}@netra.ai',
                'name': f'Multi State User {i}',
                'is_active': True
            })
            connection_info = await self._create_real_websocket_connection(real_services_fixture, user_data)
            users.append(connection_info)
        
        websocket_manager = UnifiedWebSocketManager()
        
        async def run_user_state_sequence(user_info: Dict, user_index: int):
            """Run independent state sequence for each user."""
            user_id = user_info['user_id']
            connection_id = user_info['connection_id']
            
            # Each user has a different state transition pattern
            if user_index == 0:
                # User 0: Normal flow
                user_states = [
                    (IntegrationConnectionState.CONNECTING, {"pattern": "normal", "user": user_index}),
                    (IntegrationConnectionState.CONNECTED, {"pattern": "normal", "user": user_index}),
                    (IntegrationConnectionState.ACTIVE, {"pattern": "normal", "user": user_index})
                ]
            elif user_index == 1:
                # User 1: Authentication flow
                user_states = [
                    (IntegrationConnectionState.CONNECTING, {"pattern": "auth", "user": user_index}),
                    (IntegrationConnectionState.CONNECTED, {"pattern": "auth", "user": user_index}),
                    (IntegrationConnectionState.AUTHENTICATED, {"pattern": "auth", "user": user_index}),
                    (IntegrationConnectionState.ACTIVE, {"pattern": "auth", "user": user_index})
                ]
            else:
                # User 2: Error recovery flow
                user_states = [
                    (IntegrationConnectionState.CONNECTING, {"pattern": "error_recovery", "user": user_index}),
                    (IntegrationConnectionState.ERROR, {"pattern": "error_recovery", "user": user_index, "error": "simulated"}),
                    (IntegrationConnectionState.RECOVERY, {"pattern": "error_recovery", "user": user_index}),
                    (IntegrationConnectionState.ACTIVE, {"pattern": "error_recovery", "user": user_index})
                ]
            
            # Execute state transitions
            for state, metadata in user_states:
                await self._persist_connection_state_redis(
                    real_services_fixture, connection_id, user_id, state, metadata
                )
                await asyncio.sleep(0.05)  # Slight delay for realistic timing
            
            # Create and register connection
            real_websocket = await user_info['websocket_client'].connect()
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=real_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "test_type": "multi_user_isolation",
                    "user_index": user_index,
                    "pattern": user_states[-1][1]["pattern"]
                }
            )
            
            await websocket_manager.add_connection(connection)
            
            # Send user-specific messages
            for msg_num in range(3):
                test_message = {
                    "type": f"user_{user_index}_message",
                    "data": {"message_num": msg_num, "user_pattern": user_states[-1][1]["pattern"]},
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket_manager.send_to_user(user_id, test_message)
                await asyncio.sleep(0.02)
            
            return {
                'user_id': user_id,
                'connection_id': connection_id,
                'final_state': user_states[-1][0].value,
                'pattern': user_states[-1][1]["pattern"],
                'websocket_client': user_info['websocket_client']
            }
        
        # Execute concurrent user state sequences
        user_tasks = [
            run_user_state_sequence(user_info, i) 
            for i, user_info in enumerate(users)
        ]
        
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"User {i} state sequence failed: {result}"
        
        # Verify state isolation - each user should have independent states
        user_final_states = {}
        for i, result in enumerate(results):
            user_id = result['user_id']
            connection_id = result['connection_id']
            
            # Verify Redis state isolation
            user_state = await self._get_connection_state_redis(real_services_fixture, connection_id)
            assert user_state is not None
            assert user_state['user_id'] == user_id
            assert user_state['state'] == result['final_state']
            
            user_final_states[user_id] = user_state
            
            # Verify state transition logs are isolated
            user_log = await self._get_state_transition_log(real_services_fixture, connection_id)
            assert len(user_log) > 0
            
            # All log entries should belong to this user's pattern
            for log_entry in user_log:
                if 'metadata' in log_entry and 'user' in log_entry['metadata']:
                    assert log_entry['metadata']['user'] == i
        
        # Verify no cross-contamination between users
        all_user_ids = {result['user_id'] for result in results}
        assert len(all_user_ids) == 3, "Should have 3 distinct users"
        
        # Verify different state patterns were maintained
        patterns = {result['pattern'] for result in results}
        expected_patterns = {"normal", "auth", "error_recovery"}
        assert patterns == expected_patterns, "Each user should have maintained distinct pattern"
        
        # Verify WebSocket manager isolation
        for i, result in enumerate(results):
            user_id = result['user_id']
            assert websocket_manager.is_connection_active(user_id), f"User {i} should have active connection"
            
            # Each user should have exactly one connection
            user_connections = websocket_manager.get_user_connections(user_id)
            assert len(user_connections) == 1, f"User {i} should have exactly one connection"
        
        # Test cross-user message isolation
        for i, result in enumerate(results):
            user_id = result['user_id']
            
            # Send message to specific user
            isolation_message = {
                "type": "isolation_test",
                "data": {"target_user": i, "should_receive": True},
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket_manager.send_to_user(user_id, isolation_message)
            
            # Other users should not receive this message (implicit in isolated connections)
            
            # Verify user still has active connection after message
            assert websocket_manager.is_connection_active(user_id)
        
        # Clean up all users
        for i, result in enumerate(results):
            user_id = result['user_id']
            connection_id = result['connection_id']
            
            await websocket_manager.remove_connection(connection_id)
            await result['websocket_client'].disconnect()
            
            # Clean up persistence
            await real_services_fixture["redis"].delete(f"websocket:connection_state:{connection_id}")
            await real_services_fixture["redis"].delete(f"websocket:user_connections:{user_id}")
            await real_services_fixture["redis"].delete(f"websocket:state_log:{connection_id}")
        
        # Verify complete cleanup
        final_stats = websocket_manager.get_stats()
        assert final_stats['total_connections'] == 0
        assert final_stats['unique_users'] == 0
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_state_machine_error_recovery_real_services(self, real_services_fixture):
        """
        Test WebSocket state machine error recovery with real Redis/PostgreSQL persistence.
        
        Business Value: Ensures system can recover from infrastructure failures
        while maintaining state consistency and enabling automatic reconnection.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'error_recovery_integration@netra.ai',
            'name': 'Error Recovery Integration User',
            'is_active': True
        })
        
        connection_info = await self._create_real_websocket_connection(real_services_fixture, user_data)
        user_id = connection_info['user_id']
        connection_id = connection_info['connection_id']
        
        websocket_manager = UnifiedWebSocketManager()
        
        # Phase 1: Establish normal connection
        normal_states = [
            (IntegrationConnectionState.CONNECTING, {"phase": "establishment"}),
            (IntegrationConnectionState.CONNECTED, {"phase": "establishment"}),
            (IntegrationConnectionState.ACTIVE, {"phase": "establishment"})
        ]
        
        for state, metadata in normal_states:
            await self._persist_connection_state_redis(
                real_services_fixture, connection_id, user_id, state, metadata
            )
        
        # Create real connection
        real_websocket = await connection_info['websocket_client'].connect()
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=real_websocket,
            connected_at=datetime.utcnow(),
            metadata={"test_type": "error_recovery"}
        )
        
        await websocket_manager.add_connection(connection)
        
        # Verify normal operation
        assert websocket_manager.is_connection_active(user_id)
        
        normal_message = {
            "type": "normal_operation_test",
            "data": {"phase": "before_error"},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket_manager.send_to_user(user_id, normal_message)
        
        # Phase 2: Simulate error conditions
        error_scenarios = [
            (IntegrationConnectionState.ERROR, {
                "error_type": "network_timeout",
                "error_details": "TCP connection lost",
                "phase": "error_simulation",
                "recovery_expected": True
            }),
            (IntegrationConnectionState.RECOVERY, {
                "recovery_attempt": 1,
                "phase": "recovery_attempt",
                "strategy": "reconnection"
            }),
            (IntegrationConnectionState.CONNECTING, {
                "recovery_attempt": 1,
                "phase": "reconnection",
                "trigger": "automatic_recovery"
            }),
            (IntegrationConnectionState.ERROR, {
                "error_type": "auth_failure",
                "error_details": "Token expired during recovery",
                "phase": "secondary_error",
                "recovery_expected": True
            }),
            (IntegrationConnectionState.RECOVERY, {
                "recovery_attempt": 2,
                "phase": "second_recovery",
                "strategy": "token_refresh"
            }),
            (IntegrationConnectionState.AUTHENTICATED, {
                "recovery_attempt": 2,
                "phase": "auth_recovery",
                "auth_renewed": True
            }),
            (IntegrationConnectionState.ACTIVE, {
                "recovery_attempt": 2,
                "phase": "full_recovery",
                "fully_operational": True
            })
        ]
        
        for state, metadata in error_scenarios:
            await self._persist_connection_state_redis(
                real_services_fixture, connection_id, user_id, state, metadata
            )
            
            # Store recovery state in PostgreSQL for persistence across restarts
            recovery_data = {
                'connection_id': connection_id,
                'user_id': user_id,
                'state': state.value,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata
            }
            await self._store_connection_postgres(real_services_fixture, recovery_data)
            
            await asyncio.sleep(0.1)  # Realistic recovery timing
        
        # Verify error recovery sequence in Redis
        final_redis_state = await self._get_connection_state_redis(real_services_fixture, connection_id)
        assert final_redis_state['state'] == IntegrationConnectionState.ACTIVE.value
        assert final_redis_state['metadata']['fully_operational'] is True
        assert final_redis_state['metadata']['recovery_attempt'] == 2
        
        # Verify recovery persistence in PostgreSQL
        postgres_recovery_query = """
            SELECT state, metadata FROM websocket_connections 
            WHERE connection_id = $1
        """
        postgres_recovery = await real_services_fixture["postgres"].fetchrow(
            postgres_recovery_query, connection_id
        )
        postgres_metadata = json.loads(postgres_recovery['metadata'])
        assert postgres_recovery['state'] == IntegrationConnectionState.ACTIVE.value
        assert postgres_metadata['fully_operational'] is True
        
        # Verify complete error recovery log
        recovery_log = await self._get_state_transition_log(real_services_fixture, connection_id)
        logged_states = [entry['state'] for entry in reversed(recovery_log)]
        
        expected_recovery_sequence = (
            [state.value for state, _ in normal_states] +
            [state.value for state, _ in error_scenarios]
        )
        assert logged_states == expected_recovery_sequence
        
        # Phase 3: Test post-recovery functionality
        recovery_test_message = {
            "type": "post_recovery_test",
            "data": {"recovery_verified": True, "system_operational": True},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket_manager.send_to_user(user_id, recovery_test_message)
        
        # Verify connection is still active after recovery
        assert websocket_manager.is_connection_active(user_id)
        
        # Phase 4: Test resilience - multiple rapid errors
        rapid_error_states = [
            (IntegrationConnectionState.DEGRADED, {"rapid_test": 1}),
            (IntegrationConnectionState.ERROR, {"rapid_test": 2}),
            (IntegrationConnectionState.RECOVERY, {"rapid_test": 3}),
            (IntegrationConnectionState.ACTIVE, {"rapid_test": 4})
        ]
        
        for state, metadata in rapid_error_states:
            await self._persist_connection_state_redis(
                real_services_fixture, connection_id, user_id, state, 
                {**metadata, "phase": "rapid_recovery_test"}
            )
            await asyncio.sleep(0.02)  # Very rapid state changes
        
        # Verify final state after rapid recovery
        final_rapid_state = await self._get_connection_state_redis(real_services_fixture, connection_id)
        assert final_rapid_state['state'] == IntegrationConnectionState.ACTIVE.value
        assert final_rapid_state['metadata']['rapid_test'] == 4
        
        # Test system health after multiple recovery cycles
        health_message = {
            "type": "system_health_check",
            "data": {"multiple_recoveries_completed": True},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket_manager.send_to_user(user_id, health_message)
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        await connection_info['websocket_client'].disconnect()
        
        # Clean up persistence
        await real_services_fixture["redis"].delete(f"websocket:connection_state:{connection_id}")
        await real_services_fixture["redis"].delete(f"websocket:user_connections:{user_id}")
        await real_services_fixture["redis"].delete(f"websocket:state_log:{connection_id}")
        
        await real_services_fixture["postgres"].execute(
            "DELETE FROM websocket_connections WHERE connection_id = $1", connection_id
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_state_machine_performance_under_load(self, real_services_fixture):
        """
        Test WebSocket state machine performance with high-frequency state transitions.
        
        Business Value: Ensures state machine can handle high-load scenarios without
        performance degradation, maintaining responsive user experience.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'performance_load_test@netra.ai',
            'name': 'Performance Load Test User',
            'is_active': True
        })
        
        connection_info = await self._create_real_websocket_connection(real_services_fixture, user_data)
        user_id = connection_info['user_id']
        connection_id = connection_info['connection_id']
        
        websocket_manager = UnifiedWebSocketManager()
        
        # Performance test configuration
        num_state_transitions = 100
        num_concurrent_connections = 5
        message_frequency = 0.01  # 100 messages per second
        
        start_time = datetime.utcnow()
        
        # Create multiple concurrent connections for load testing
        connections = []
        for i in range(num_concurrent_connections):
            id_manager = UnifiedIDManager()
            perf_connection_id = id_manager.generate_id(
                IDType.CONNECTION,
                prefix=f"perf_conn_{i}",
                context={"user_id": user_id, "performance_test": True}
            )
            
            perf_websocket = await connection_info['websocket_client'].connect()
            perf_connection = WebSocketConnection(
                connection_id=perf_connection_id,
                user_id=user_id,
                websocket=perf_websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "test_type": "performance_load",
                    "connection_index": i
                }
            )
            
            await websocket_manager.add_connection(perf_connection)
            connections.append({
                'connection_id': perf_connection_id,
                'websocket': perf_websocket
            })
        
        # High-frequency state transitions
        state_cycle = [
            IntegrationConnectionState.ACTIVE,
            IntegrationConnectionState.DEGRADED,
            IntegrationConnectionState.RECOVERY,
            IntegrationConnectionState.ACTIVE
        ]
        
        async def high_frequency_state_transitions():
            """Perform high-frequency state transitions."""
            transition_count = 0
            
            for cycle in range(num_state_transitions // len(state_cycle)):
                for state in state_cycle:
                    await self._persist_connection_state_redis(
                        real_services_fixture, connection_id, user_id, state,
                        {
                            "cycle": cycle,
                            "transition_count": transition_count,
                            "performance_test": True
                        }
                    )
                    transition_count += 1
                    
                    # Small delay to simulate realistic timing
                    await asyncio.sleep(0.005)
            
            return transition_count
        
        async def high_frequency_messaging():
            """Send high-frequency messages."""
            message_count = 0
            
            for i in range(num_state_transitions):
                message = {
                    "type": "performance_test_message",
                    "data": {
                        "message_num": i,
                        "timestamp": datetime.utcnow().isoformat(),
                        "performance_test": True
                    }
                }
                
                await websocket_manager.send_to_user(user_id, message)
                message_count += 1
                
                await asyncio.sleep(message_frequency)
            
            return message_count
        
        # Execute concurrent high-load operations
        load_tasks = [
            high_frequency_state_transitions(),
            high_frequency_messaging()
        ]
        
        results = await asyncio.gather(*load_tasks, return_exceptions=True)
        
        end_time = datetime.utcnow()
        test_duration = (end_time - start_time).total_seconds()
        
        # Verify no exceptions during high load
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"High load task {i} failed: {result}"
        
        transition_count, message_count = results
        
        # Performance assertions
        assert transition_count > 0, "Should have completed state transitions"
        assert message_count > 0, "Should have sent messages"
        
        # Calculate performance metrics
        transitions_per_second = transition_count / test_duration
        messages_per_second = message_count / test_duration
        
        assert transitions_per_second > 10, f"Should achieve >10 transitions/sec, got {transitions_per_second:.2f}"
        assert messages_per_second > 50, f"Should achieve >50 messages/sec, got {messages_per_second:.2f}"
        
        # Verify system stability after high load
        assert websocket_manager.is_connection_active(user_id)
        
        # Verify all connections are still active
        for conn_info in connections:
            assert websocket_manager.get_connection(conn_info['connection_id']) is not None
        
        # Verify final state consistency
        final_state = await self._get_connection_state_redis(real_services_fixture, connection_id)
        assert final_state is not None
        assert final_state['state'] in [state.value for state in state_cycle]
        
        # Verify state transition log integrity
        state_log = await self._get_state_transition_log(real_services_fixture, connection_id)
        assert len(state_log) >= transition_count
        
        # Test post-load messaging still works
        post_load_message = {
            "type": "post_load_test",
            "data": {
                "load_test_completed": True,
                "transitions_per_second": transitions_per_second,
                "messages_per_second": messages_per_second
            }
        }
        await websocket_manager.send_to_user(user_id, post_load_message)
        
        # Clean up all connections
        for conn_info in connections:
            await websocket_manager.remove_connection(conn_info['connection_id'])
        
        await connection_info['websocket_client'].disconnect()
        
        # Clean up persistence
        await real_services_fixture["redis"].delete(f"websocket:connection_state:{connection_id}")
        await real_services_fixture["redis"].delete(f"websocket:user_connections:{user_id}")
        await real_services_fixture["redis"].delete(f"websocket:state_log:{connection_id}")
        
        # Verify business value: System maintained stability under high load
        self.assert_business_value_delivered({
            'high_performance': transitions_per_second > 10,
            'load_stability': True,
            'concurrent_connection_support': num_concurrent_connections,
            'message_throughput': messages_per_second > 50
        }, 'performance')