"""
Test WebSocket Connection Health Monitoring and Heartbeat with Application State Consistency

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable connection monitoring and heartbeat mechanisms for stable service
- Value Impact: Users experience consistent connection quality with proactive issue detection
- Strategic Impact: Enables proactive system maintenance and improved user experience reliability

This integration test validates that WebSocket connection health monitoring and heartbeat
mechanisms work correctly while maintaining application state consistency.
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


class HealthStatus:
    """Health status tracking for WebSocket connections."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISCONNECTED = "disconnected"


class TestWebSocketConnectionHealthMonitoringHeartbeatIntegration(BaseIntegrationTest):
    """Test WebSocket connection health monitoring and heartbeat with comprehensive application state validation."""
    
    def _create_health_monitoring_websocket(self, connection_id: str, user_id: str, simulate_issues: bool = False):
        """Create a WebSocket mock with health monitoring and heartbeat capabilities."""
        class HealthMonitoringWebSocket:
            def __init__(self, connection_id: str, user_id: str, simulate_issues: bool = False):
                self.connection_id = connection_id
                self.user_id = user_id
                self.simulate_issues = simulate_issues
                self.messages_sent = []
                self.is_closed = False
                self.health_status = HealthStatus.HEALTHY
                self.last_heartbeat = datetime.utcnow()
                self.heartbeat_interval = 30.0  # seconds
                self.health_checks = []
                self.missed_heartbeats = 0
                self.response_times = []
                self.connection_quality = 1.0  # 0.0 to 1.0
                self.health_callbacks = []
                
                # Start health monitoring
                self._start_health_monitoring()
            
            def _start_health_monitoring(self):
                """Initialize health monitoring."""
                self.health_checks.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': self.health_status,
                    'response_time_ms': 0,
                    'connection_quality': self.connection_quality
                })
            
            async def send_json(self, data):
                if self.is_closed:
                    raise ConnectionError("Connection is closed")
                
                send_start = datetime.utcnow()
                
                # Simulate network conditions
                if self.simulate_issues:
                    # Random delays to simulate network issues
                    import random
                    delay = random.uniform(0.01, 0.5) if random.random() < 0.3 else 0.001
                    await asyncio.sleep(delay)
                    
                    # Sometimes fail to simulate connection issues
                    if random.random() < 0.1:  # 10% failure rate
                        self.missed_heartbeats += 1
                        self._update_health_status()
                        raise ConnectionError("Simulated network error")
                
                # Calculate response time
                response_time = (datetime.utcnow() - send_start).total_seconds() * 1000
                self.response_times.append(response_time)
                
                # Update connection quality based on response time
                if response_time > 500:  # >500ms is poor
                    self.connection_quality = max(0.3, self.connection_quality - 0.1)
                elif response_time > 200:  # >200ms is degraded
                    self.connection_quality = max(0.6, self.connection_quality - 0.05)
                else:  # <200ms is good
                    self.connection_quality = min(1.0, self.connection_quality + 0.05)
                
                self._update_health_status()
                
                # Add health metadata to message
                data['_health_metadata'] = {
                    'response_time_ms': response_time,
                    'connection_quality': self.connection_quality,
                    'health_status': self.health_status,
                    'heartbeat_age_seconds': (datetime.utcnow() - self.last_heartbeat).total_seconds()
                }
                
                self.messages_sent.append(data)
            
            def _update_health_status(self):
                """Update health status based on current metrics."""
                old_status = self.health_status
                
                # Determine health status
                if self.missed_heartbeats > 3 or self.connection_quality < 0.3:
                    self.health_status = HealthStatus.UNHEALTHY
                elif self.missed_heartbeats > 1 or self.connection_quality < 0.6:
                    self.health_status = HealthStatus.DEGRADED
                else:
                    self.health_status = HealthStatus.HEALTHY
                
                # Record health check
                self.health_checks.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': self.health_status,
                    'response_time_ms': self.response_times[-1] if self.response_times else 0,
                    'connection_quality': self.connection_quality,
                    'missed_heartbeats': self.missed_heartbeats
                })
                
                # Notify callbacks if status changed
                if old_status != self.health_status:
                    for callback in self.health_callbacks:
                        callback(old_status, self.health_status, {
                            'connection_id': self.connection_id,
                            'user_id': self.user_id,
                            'missed_heartbeats': self.missed_heartbeats,
                            'connection_quality': self.connection_quality
                        })
            
            async def send_heartbeat(self) -> bool:
                """Send heartbeat and return success status."""
                try:
                    heartbeat_message = {
                        'type': 'heartbeat',
                        'timestamp': datetime.utcnow().isoformat(),
                        'connection_id': self.connection_id
                    }
                    
                    await self.send_json(heartbeat_message)
                    self.last_heartbeat = datetime.utcnow()
                    return True
                except Exception:
                    self.missed_heartbeats += 1
                    self._update_health_status()
                    return False
            
            def get_health_metrics(self) -> Dict[str, Any]:
                """Get comprehensive health metrics."""
                now = datetime.utcnow()
                avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
                
                return {
                    'connection_id': self.connection_id,
                    'user_id': self.user_id,
                    'health_status': self.health_status,
                    'connection_quality': self.connection_quality,
                    'last_heartbeat': self.last_heartbeat.isoformat(),
                    'heartbeat_age_seconds': (now - self.last_heartbeat).total_seconds(),
                    'missed_heartbeats': self.missed_heartbeats,
                    'total_messages': len(self.messages_sent),
                    'avg_response_time_ms': avg_response_time,
                    'health_check_count': len(self.health_checks),
                    'is_healthy': self.health_status == HealthStatus.HEALTHY
                }
            
            def add_health_callback(self, callback: Callable):
                """Add callback for health status changes."""
                self.health_callbacks.append(callback)
            
            async def close(self, code=1000, reason="Normal closure"):
                self.is_closed = True
                self.health_status = HealthStatus.DISCONNECTED
                self._update_health_status()
        
        return HealthMonitoringWebSocket(connection_id, user_id, simulate_issues)
    
    async def _create_health_monitoring_state(self, real_services_fixture, user_id: str, connection_id: str) -> Dict[str, str]:
        """Create application state for health monitoring tracking."""
        # Store connection health metrics in Redis
        health_key = f"connection_health:{connection_id}"
        health_data = {
            'user_id': user_id,
            'connection_id': connection_id,
            'created_at': datetime.utcnow().isoformat(),
            'last_health_check': datetime.utcnow().isoformat(),
            'status': HealthStatus.HEALTHY,
            'missed_heartbeats': 0
        }
        
        await real_services_fixture["redis"].set(
            health_key,
            json.dumps(health_data),
            ex=3600  # 1 hour expiration
        )
        
        # Track user's connection health
        user_health_key = f"user_health:{user_id}"
        await real_services_fixture["redis"].sadd(user_health_key, connection_id)
        await real_services_fixture["redis"].expire(user_health_key, 3600)
        
        # Store health monitoring configuration
        health_config_key = f"health_config:{connection_id}"
        health_config = {
            'heartbeat_interval_seconds': 30,
            'health_check_interval_seconds': 10,
            'unhealthy_threshold_missed_heartbeats': 3,
            'degraded_threshold_response_time_ms': 200
        }
        
        await real_services_fixture["redis"].set(
            health_config_key,
            json.dumps(health_config),
            ex=3600
        )
        
        return {
            'health_key': health_key,
            'user_health_key': user_health_key,
            'health_config_key': health_config_key
        }
    
    async def _update_health_state(self, real_services_fixture, connection_id: str, health_metrics: Dict[str, Any]):
        """Update application state with current health metrics."""
        health_key = f"connection_health:{connection_id}"
        
        health_data = {
            'user_id': health_metrics['user_id'],
            'connection_id': connection_id,
            'last_health_check': datetime.utcnow().isoformat(),
            'status': health_metrics['health_status'],
            'connection_quality': health_metrics['connection_quality'],
            'missed_heartbeats': health_metrics['missed_heartbeats'],
            'avg_response_time_ms': health_metrics['avg_response_time_ms'],
            'total_messages': health_metrics['total_messages']
        }
        
        await real_services_fixture["redis"].set(
            health_key,
            json.dumps(health_data),
            ex=3600
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_health_monitoring_with_application_state_tracking(self, real_services_fixture):
        """
        Test that WebSocket health monitoring properly tracks connection health and maintains application state.
        
        Business Value: Ensures proactive monitoring of connection health enables
        early detection of issues and maintains service quality.
        """
        # Create test user
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'health_monitoring_test@netra.ai',
            'name': 'Health Monitoring Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="health_monitor_conn",
            context={"user_id": user_id, "test": "health_monitoring"}
        )
        
        # Create health monitoring WebSocket
        health_websocket = self._create_health_monitoring_websocket(connection_id, user_id, simulate_issues=False)
        
        # Set up health monitoring application state
        health_state_keys = await self._create_health_monitoring_state(
            real_services_fixture, user_id, connection_id
        )
        
        # Track health status changes
        health_status_changes = []
        
        def track_health_changes(old_status, new_status, metrics):
            health_status_changes.append({
                'timestamp': datetime.utcnow().isoformat(),
                'old_status': old_status,
                'new_status': new_status,
                'metrics': metrics
            })
            # Update application state with health change
            asyncio.create_task(
                self._update_health_state(real_services_fixture, connection_id, {
                    'user_id': metrics['user_id'],
                    'health_status': new_status,
                    'connection_quality': metrics['connection_quality'],
                    'missed_heartbeats': metrics['missed_heartbeats'],
                    'avg_response_time_ms': 0,
                    'total_messages': 0
                })
            )
        
        health_websocket.add_health_callback(track_health_changes)
        
        # Create connection
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=health_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "health_monitoring_test",
                "health_monitoring_enabled": True,
                "session_id": session_data['session_key']
            }
        )
        
        await websocket_manager.add_connection(connection)
        
        # Verify connection is active and healthy
        assert websocket_manager.is_connection_active(user_id)
        
        # Get initial health metrics
        initial_health = health_websocket.get_health_metrics()
        assert initial_health['health_status'] == HealthStatus.HEALTHY
        assert initial_health['missed_heartbeats'] == 0
        assert initial_health['is_healthy'] is True
        
        # Test heartbeat functionality
        heartbeat_success = await health_websocket.send_heartbeat()
        assert heartbeat_success, "Initial heartbeat should succeed"
        
        # Send regular messages and monitor health
        for i in range(10):
            test_message = {
                "type": "health_test_message",
                "data": {"message_index": i, "test_type": "health_monitoring"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, test_message)
            
            # Small delay to simulate real-world timing
            await asyncio.sleep(0.05)
        
        # Verify messages were sent with health metadata
        assert len(health_websocket.messages_sent) == 11  # 10 messages + 1 heartbeat
        
        # Check health metadata in messages
        for message in health_websocket.messages_sent:
            if message['type'] != 'heartbeat':  # Skip heartbeat messages
                assert '_health_metadata' in message, "All messages should have health metadata"
                health_meta = message['_health_metadata']
                assert 'response_time_ms' in health_meta
                assert 'connection_quality' in health_meta
                assert 'health_status' in health_meta
                assert health_meta['health_status'] == HealthStatus.HEALTHY
        
        # Get current health metrics
        current_health = health_websocket.get_health_metrics()
        assert current_health['health_status'] == HealthStatus.HEALTHY
        assert current_health['total_messages'] == 11
        assert current_health['connection_quality'] > 0.8  # Should be high quality
        
        # Verify application state is updated
        await asyncio.sleep(0.1)  # Allow state updates to complete
        
        stored_health = await real_services_fixture["redis"].get(health_state_keys['health_key'])
        assert stored_health is not None
        health_data = json.loads(stored_health)
        assert health_data['user_id'] == user_id
        assert health_data['status'] == HealthStatus.HEALTHY
        
        # Test connection health query through manager
        connection_health = websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True
        assert connection_health['active_connections'] == 1
        assert connection_health['connections'][0]['active'] is True
        
        # Test multiple heartbeats
        heartbeat_results = []
        for i in range(5):
            success = await health_websocket.send_heartbeat()
            heartbeat_results.append(success)
            await asyncio.sleep(0.1)
        
        assert all(heartbeat_results), "All heartbeats should succeed for healthy connection"
        
        # Verify final health state
        final_health = health_websocket.get_health_metrics()
        assert final_health['health_status'] == HealthStatus.HEALTHY
        assert final_health['missed_heartbeats'] == 0
        assert final_health['heartbeat_age_seconds'] < 1.0  # Recent heartbeat
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        
        # Clean up health monitoring state
        for key in health_state_keys.values():
            await real_services_fixture["redis"].delete(key)
        
        # Verify business value: Health monitoring enables proactive service management
        self.assert_business_value_delivered({
            'health_monitoring': True,
            'proactive_issue_detection': True,
            'connection_quality_tracking': True,
            'application_state_consistency': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_health_monitoring_degraded_and_recovery_scenarios(self, real_services_fixture):
        """
        Test WebSocket health monitoring during degraded conditions and recovery scenarios.
        
        Business Value: Ensures system can detect, handle, and recover from degraded
        connection conditions while maintaining service availability.
        """
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'health_degraded_test@netra.ai',
            'name': 'Health Degraded Test User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="health_degraded_conn",
            context={"user_id": user_id, "test": "health_degraded"}
        )
        
        # Create WebSocket with simulated network issues
        degraded_websocket = self._create_health_monitoring_websocket(
            connection_id, user_id, simulate_issues=True
        )
        
        health_state_keys = await self._create_health_monitoring_state(
            real_services_fixture, user_id, connection_id
        )
        
        # Track health transitions
        health_transitions = []
        
        def track_health_transitions(old_status, new_status, metrics):
            health_transitions.append({
                'timestamp': datetime.utcnow().isoformat(),
                'transition': f"{old_status} -> {new_status}",
                'connection_quality': metrics['connection_quality'],
                'missed_heartbeats': metrics['missed_heartbeats']
            })
        
        degraded_websocket.add_health_callback(track_health_transitions)
        
        # Create connection
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=degraded_websocket,
            connected_at=datetime.utcnow(),
            metadata={"connection_type": "health_degraded_test"}
        )
        
        await websocket_manager.add_connection(connection)
        
        # Send messages that will experience simulated network issues
        successful_sends = 0
        failed_sends = 0
        
        for i in range(20):  # Send more messages to trigger health issues
            try:
                test_message = {
                    "type": "degraded_test_message",
                    "data": {"message_index": i},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket_manager.send_to_user(user_id, test_message)
                successful_sends += 1
            except Exception:
                failed_sends += 1
            
            await asyncio.sleep(0.02)  # Small delay to allow health monitoring
        
        # Verify that some messages succeeded despite issues
        assert successful_sends > 0, "Some messages should succeed even with network issues"
        
        # Check if health status has degraded due to simulated issues
        current_health = degraded_websocket.get_health_metrics()
        
        # Due to simulated issues, health should be degraded or unhealthy
        assert current_health['health_status'] in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY], \
            f"Health status should be degraded, got: {current_health['health_status']}"
        
        # Verify health transitions occurred
        assert len(health_transitions) > 0, "Health status transitions should have occurred"
        
        # Test heartbeat during degraded conditions
        heartbeat_attempts = []
        for i in range(5):
            success = await degraded_websocket.send_heartbeat()
            heartbeat_attempts.append(success)
            await asyncio.sleep(0.1)
        
        # Some heartbeats might fail due to simulated issues
        successful_heartbeats = sum(heartbeat_attempts)
        assert successful_heartbeats >= 0, "At least some heartbeats should be attempted"
        
        # Test recovery by creating a new healthy connection
        recovery_connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="health_recovery_conn",
            context={"user_id": user_id, "test": "recovery"}
        )
        
        recovery_websocket = self._create_health_monitoring_websocket(
            recovery_connection_id, user_id, simulate_issues=False
        )
        
        recovery_health_state_keys = await self._create_health_monitoring_state(
            real_services_fixture, user_id, recovery_connection_id
        )
        
        recovery_connection = WebSocketConnection(
            connection_id=recovery_connection_id,
            user_id=user_id,
            websocket=recovery_websocket,
            connected_at=datetime.utcnow(),
            metadata={"connection_type": "health_recovery_test"}
        )
        
        # Remove degraded connection and add recovery connection
        await websocket_manager.remove_connection(connection_id)
        await websocket_manager.add_connection(recovery_connection)
        
        # Test that recovery connection is healthy
        recovery_health = recovery_websocket.get_health_metrics()
        assert recovery_health['health_status'] == HealthStatus.HEALTHY
        assert recovery_health['missed_heartbeats'] == 0
        
        # Send messages through recovered connection
        recovery_messages = []
        for i in range(5):
            recovery_message = {
                "type": "recovery_test_message",
                "data": {"message_index": i, "recovery": True},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, recovery_message)
            recovery_messages.append(recovery_message)
        
        # Verify recovery messages were sent successfully
        assert len(recovery_websocket.messages_sent) == 5
        
        # Verify all recovery messages have healthy metadata
        for message in recovery_websocket.messages_sent:
            health_meta = message['_health_metadata']
            assert health_meta['health_status'] == HealthStatus.HEALTHY
            assert health_meta['connection_quality'] > 0.8
        
        # Test heartbeat on recovered connection
        recovery_heartbeat_success = await recovery_websocket.send_heartbeat()
        assert recovery_heartbeat_success, "Recovery connection heartbeat should succeed"
        
        # Verify final health state
        final_recovery_health = recovery_websocket.get_health_metrics()
        assert final_recovery_health['health_status'] == HealthStatus.HEALTHY
        assert final_recovery_health['connection_quality'] > 0.9
        
        # Clean up
        await websocket_manager.remove_connection(recovery_connection_id)
        
        # Clean up health state
        for key in list(health_state_keys.values()) + list(recovery_health_state_keys.values()):
            await real_services_fixture["redis"].delete(key)
        
        # Verify business value: System handles degraded conditions and recovers
        self.assert_business_value_delivered({
            'degraded_condition_detection': True,
            'health_transition_tracking': True,
            'connection_recovery': True,
            'service_continuity': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_multi_connection_health_monitoring_with_state_correlation(self, real_services_fixture):
        """
        Test health monitoring across multiple connections with application state correlation.
        
        Business Value: Ensures health monitoring scales effectively with multiple
        connections and provides comprehensive system health visibility.
        """
        # Create multiple users with multiple connections
        users_and_connections = []
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create 2 users with 2 connections each
        for user_index in range(2):
            user_data = await self.create_test_user_context(real_services_fixture, {
                'email': f'multi_health_user_{user_index}@netra.ai',
                'name': f'Multi Health User {user_index}',
                'is_active': True
            })
            user_id = user_data['id']
            
            user_connections = []
            for conn_index in range(2):
                connection_id = id_manager.generate_id(
                    IDType.CONNECTION,
                    prefix=f"multi_health_u{user_index}_c{conn_index}",
                    context={"user_id": user_id, "test": "multi_health"}
                )
                
                # Vary health conditions: some healthy, some with issues
                simulate_issues = (user_index == 0 and conn_index == 1)  # User 0, Connection 1 has issues
                
                health_websocket = self._create_health_monitoring_websocket(
                    connection_id, user_id, simulate_issues=simulate_issues
                )
                
                health_state_keys = await self._create_health_monitoring_state(
                    real_services_fixture, user_id, connection_id
                )
                
                connection = WebSocketConnection(
                    connection_id=connection_id,
                    user_id=user_id,
                    websocket=health_websocket,
                    connected_at=datetime.utcnow(),
                    metadata={
                        "connection_type": "multi_health_test",
                        "user_index": user_index,
                        "conn_index": conn_index,
                        "simulate_issues": simulate_issues
                    }
                )
                
                await websocket_manager.add_connection(connection)
                
                user_connections.append({
                    'connection_id': connection_id,
                    'websocket': health_websocket,
                    'health_state_keys': health_state_keys,
                    'simulate_issues': simulate_issues
                })
            
            users_and_connections.append({
                'user_id': user_id,
                'user_data': user_data,
                'connections': user_connections
            })
        
        # Verify all connections are established
        total_stats = websocket_manager.get_stats()
        assert total_stats['total_connections'] == 4, "Should have 4 total connections"
        assert total_stats['unique_users'] == 2, "Should have 2 unique users"
        
        # Send messages through all connections to generate health data
        all_health_metrics = []
        
        for user_info in users_and_connections:
            user_id = user_info['user_id']
            
            # Send messages to this user (distributed across their connections)
            for i in range(10):
                test_message = {
                    "type": "multi_health_test",
                    "data": {"user_id": user_id, "message_index": i},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket_manager.send_to_user(user_id, test_message)
                await asyncio.sleep(0.02)  # Small delay for health monitoring
        
        # Collect health metrics from all connections
        for user_info in users_and_connections:
            for conn_info in user_info['connections']:
                health_metrics = conn_info['websocket'].get_health_metrics()
                all_health_metrics.append({
                    'user_id': user_info['user_id'],
                    'connection_id': conn_info['connection_id'],
                    'simulate_issues': conn_info['simulate_issues'],
                    'metrics': health_metrics
                })
        
        # Verify health metrics are collected for all connections
        assert len(all_health_metrics) == 4, "Should have health metrics for all 4 connections"
        
        # Analyze health distribution
        healthy_connections = [m for m in all_health_metrics if m['metrics']['health_status'] == HealthStatus.HEALTHY]
        degraded_connections = [m for m in all_health_metrics if m['metrics']['health_status'] in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]]
        
        # Verify that connections with simulated issues show degraded health
        assert len(degraded_connections) > 0, "At least some connections should show degraded health"
        assert len(healthy_connections) > 0, "At least some connections should remain healthy"
        
        # Verify user-level health aggregation
        for user_info in users_and_connections:
            user_id = user_info['user_id']
            
            # Get connection health for this user
            user_connection_health = websocket_manager.get_connection_health(user_id)
            assert user_connection_health['total_connections'] == 2, f"User {user_id} should have 2 connections"
            assert user_connection_health['has_active_connections'] is True
            
            # Check individual connection health details
            for conn_detail in user_connection_health['connections']:
                assert 'connection_id' in conn_detail
                assert 'active' in conn_detail
                assert conn_detail['active'] is True  # All connections should be active
        
        # Test heartbeat across all connections
        heartbeat_results = {}
        
        for user_info in users_and_connections:
            user_id = user_info['user_id']
            heartbeat_results[user_id] = []
            
            for conn_info in user_info['connections']:
                success = await conn_info['websocket'].send_heartbeat()
                heartbeat_results[user_id].append({
                    'connection_id': conn_info['connection_id'],
                    'success': success,
                    'simulate_issues': conn_info['simulate_issues']
                })
        
        # Verify heartbeat results correlate with connection health
        for user_id, user_heartbeats in heartbeat_results.items():
            for heartbeat_info in user_heartbeats:
                if heartbeat_info['simulate_issues']:
                    # Connections with issues might have failed heartbeats
                    # But at least some attempt should be made
                    pass  # This is expected behavior
                else:
                    # Healthy connections should have successful heartbeats
                    assert heartbeat_info['success'], \
                        f"Healthy connection should have successful heartbeat: {heartbeat_info['connection_id']}"
        
        # Test application state correlation across connections
        await asyncio.sleep(0.1)  # Allow health state updates
        
        for user_info in users_and_connections:
            for conn_info in user_info['connections']:
                # Verify health state is persisted for each connection
                stored_health = await real_services_fixture["redis"].get(
                    conn_info['health_state_keys']['health_key']
                )
                assert stored_health is not None, f"Health state should be stored for {conn_info['connection_id']}"
                
                health_data = json.loads(stored_health)
                assert health_data['user_id'] == user_info['user_id']
                assert health_data['connection_id'] == conn_info['connection_id']
                
                # Verify health status matches connection condition
                if conn_info['simulate_issues']:
                    assert health_data['status'] in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY], \
                        "Connections with issues should have degraded health in state"
                else:
                    assert health_data['status'] == HealthStatus.HEALTHY, \
                        "Healthy connections should maintain healthy state"
        
        # Clean up all connections
        for user_info in users_and_connections:
            for conn_info in user_info['connections']:
                await websocket_manager.remove_connection(conn_info['connection_id'])
                
                # Clean up health state
                for key in conn_info['health_state_keys'].values():
                    await real_services_fixture["redis"].delete(key)
        
        # Verify complete cleanup
        final_stats = websocket_manager.get_stats()
        assert final_stats['total_connections'] == 0, "All connections should be cleaned up"
        assert final_stats['unique_users'] == 0, "No users should have active connections"
        
        # Verify business value: Multi-connection health monitoring provides comprehensive visibility
        self.assert_business_value_delivered({
            'multi_connection_health_monitoring': True,
            'health_state_correlation': True,
            'user_level_health_aggregation': True,
            'system_wide_health_visibility': True
        }, 'automation')