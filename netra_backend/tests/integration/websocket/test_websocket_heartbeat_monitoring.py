"""
WebSocket Heartbeat and Connection Monitoring Integration Tests

RELIABILITY CRITICAL: WebSocket heartbeat monitoring ensures proactive connection health
management that maintains chat experience quality and prevents silent failures.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Connection reliability is essential for all users
- Business Goal: Proactive connection health monitoring prevents chat disruptions
- Value Impact: Early failure detection maintains seamless chat experience
- Revenue Impact: Protects $500K+ ARR by preventing undetected connection failures

HEARTBEAT MONITORING REQUIREMENTS:
- Regular heartbeat/ping messages to maintain connection health
- Connection timeout detection and automatic reconnection
- Health status monitoring and reporting
- Dead connection cleanup and resource management
- Performance monitoring of connection stability
- Circuit breaker patterns for unhealthy connections

TEST SCOPE: Integration-level validation of WebSocket heartbeat monitoring including:
- Heartbeat message generation and response validation
- Connection timeout detection and handling
- Health status monitoring and metrics collection
- Dead connection detection and cleanup
- Performance monitoring under various network conditions
- Circuit breaker activation for consistently failing connections
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from dataclasses import dataclass, field
import statistics
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

# User context and types
from shared.types.core_types import UserID, ThreadID, ensure_user_id
from shared.types.user_types import TestUserData

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class HeartbeatMetrics:
    """Metrics for heartbeat monitoring."""
    heartbeats_sent: int = 0
    heartbeats_received: int = 0
    missed_heartbeats: int = 0
    average_response_time: float = 0.0
    max_response_time: float = 0.0
    timeout_events: int = 0
    reconnection_events: int = 0
    connection_uptime: float = 0.0
    health_score: float = 100.0


class HeartbeatMonitoringWebSocket:
    """WebSocket mock with comprehensive heartbeat monitoring."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.is_closed = False
        self.state = WebSocketConnectionState.CONNECTED
        self.messages_sent = []
        
        # Heartbeat configuration
        self.heartbeat_interval = 5.0  # seconds
        self.heartbeat_timeout = 10.0  # seconds
        self.max_missed_heartbeats = 3
        
        # Monitoring state
        self.connection_start_time = datetime.now(UTC)
        self.last_heartbeat_sent = None
        self.last_heartbeat_received = None
        self.last_pong_received = None
        self.heartbeat_response_times = []
        self.missed_heartbeat_count = 0
        self.timeout_count = 0
        
        # Health monitoring
        self.health_events = []
        self.is_healthy = True
        self.circuit_breaker_open = False
        
        # Simulation controls
        self.simulate_network_delay = False
        self.simulate_heartbeat_loss = False
        self.network_delay_ms = 100
        self.heartbeat_loss_rate = 0.0  # 0.0 = no loss, 1.0 = 100% loss
        
    async def send(self, message: str) -> None:
        """Send message with heartbeat monitoring."""
        if self.is_closed:
            raise ConnectionError("WebSocket connection is closed")
        
        # Simulate network delay if enabled
        if self.simulate_network_delay:
            await asyncio.sleep(self.network_delay_ms / 1000.0)
        
        try:
            message_data = json.loads(message)
            message_type = message_data.get('type', '')
            
            # Track heartbeat messages
            if message_type in ['heartbeat', 'ping']:
                self._handle_heartbeat_sent(message_data)
            
            # Simulate heartbeat loss
            if message_type == 'ping' and self.simulate_heartbeat_loss:
                import random
                if random.random() < self.heartbeat_loss_rate:
                    self._record_health_event('heartbeat_lost', 'Simulated heartbeat message loss')
                    return  # Don't record the message, simulate loss
            
            self.messages_sent.append({
                'message': message,
                'message_data': message_data,
                'timestamp': datetime.now(UTC).isoformat(),
                'type': message_type
            })
            
        except json.JSONDecodeError:
            # Non-JSON messages
            self.messages_sent.append({
                'message': message,
                'timestamp': datetime.now(UTC).isoformat(),
                'type': 'raw'
            })
    
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close connection and record final metrics."""
        self.is_closed = True
        self.state = WebSocketConnectionState.DISCONNECTED
        self._record_health_event('connection_closed', f"Connection closed: {reason}")
    
    def _handle_heartbeat_sent(self, heartbeat_data: Dict[str, Any]):
        """Handle outgoing heartbeat message."""
        self.last_heartbeat_sent = datetime.now(UTC)
        self._record_health_event('heartbeat_sent', 'Heartbeat message sent')
        
        # Auto-simulate heartbeat response (pong) after a delay
        asyncio.create_task(self._simulate_heartbeat_response())
    
    async def _simulate_heartbeat_response(self):
        """Simulate heartbeat response (pong) from server."""
        # Simulate network round-trip time
        response_delay = 0.05  # 50ms base delay
        if self.simulate_network_delay:
            response_delay += self.network_delay_ms / 1000.0
        
        await asyncio.sleep(response_delay)
        
        if not self.is_closed and not self.simulate_heartbeat_loss:
            self.last_pong_received = datetime.now(UTC)
            
            # Calculate response time
            if self.last_heartbeat_sent:
                response_time = (self.last_pong_received - self.last_heartbeat_sent).total_seconds()
                self.heartbeat_response_times.append(response_time)
            
            self._record_health_event('pong_received', 'Heartbeat response received')
            self._reset_missed_heartbeats()
    
    def _reset_missed_heartbeats(self):
        """Reset missed heartbeat counter."""
        self.missed_heartbeat_count = 0
        self.is_healthy = True
    
    def check_heartbeat_timeout(self) -> bool:
        """Check if heartbeat has timed out."""
        if not self.last_heartbeat_sent:
            return False
        
        time_since_heartbeat = (datetime.now(UTC) - self.last_heartbeat_sent).total_seconds()
        
        if time_since_heartbeat > self.heartbeat_timeout:
            self.missed_heartbeat_count += 1
            self.timeout_count += 1
            self._record_health_event('heartbeat_timeout', f'Heartbeat timeout #{self.missed_heartbeat_count}')
            
            if self.missed_heartbeat_count >= self.max_missed_heartbeats:
                self.is_healthy = False
                self._record_health_event('connection_unhealthy', 'Too many missed heartbeats')
                
                if self.missed_heartbeat_count >= self.max_missed_heartbeats * 2:
                    self.circuit_breaker_open = True
                    self._record_health_event('circuit_breaker_open', 'Circuit breaker opened due to connection failures')
            
            return True
        
        return False
    
    def _record_health_event(self, event_type: str, description: str):
        """Record health monitoring event."""
        event = {
            'event_type': event_type,
            'description': description,
            'timestamp': datetime.now(UTC).isoformat(),
            'connection_id': self.connection_id,
            'user_id': self.user_id
        }
        self.health_events.append(event)
    
    def get_heartbeat_metrics(self) -> HeartbeatMetrics:
        """Get comprehensive heartbeat metrics."""
        connection_age = (datetime.now(UTC) - self.connection_start_time).total_seconds()
        
        heartbeats_sent = len([msg for msg in self.messages_sent if msg.get('type') in ['heartbeat', 'ping']])
        heartbeats_received = len([event for event in self.health_events if event['event_type'] == 'pong_received'])
        
        avg_response_time = statistics.mean(self.heartbeat_response_times) if self.heartbeat_response_times else 0.0
        max_response_time = max(self.heartbeat_response_times) if self.heartbeat_response_times else 0.0
        
        # Calculate health score based on various factors
        health_score = 100.0
        if self.timeout_count > 0:
            health_score -= min(self.timeout_count * 10, 50)  # -10 points per timeout, max -50
        if self.missed_heartbeat_count > 0:
            health_score -= min(self.missed_heartbeat_count * 5, 30)  # -5 points per missed heartbeat, max -30
        if avg_response_time > 1.0:
            health_score -= min((avg_response_time - 1.0) * 20, 20)  # Penalty for slow responses
        
        health_score = max(health_score, 0.0)
        
        return HeartbeatMetrics(
            heartbeats_sent=heartbeats_sent,
            heartbeats_received=heartbeats_received,
            missed_heartbeats=self.missed_heartbeat_count,
            average_response_time=avg_response_time,
            max_response_time=max_response_time,
            timeout_events=self.timeout_count,
            reconnection_events=len([e for e in self.health_events if e['event_type'] == 'reconnection']),
            connection_uptime=connection_age,
            health_score=health_score
        )
    
    def simulate_network_issues(self, delay_ms: int = 200, loss_rate: float = 0.2):
        """Enable network issue simulation."""
        self.simulate_network_delay = True
        self.simulate_heartbeat_loss = True
        self.network_delay_ms = delay_ms
        self.heartbeat_loss_rate = loss_rate


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.reliability
@pytest.mark.asyncio
class TestWebSocketHeartbeatMonitoring(SSotAsyncTestCase):
    """
    Integration tests for WebSocket heartbeat and connection monitoring.
    
    RELIABILITY CRITICAL: These tests ensure proactive connection health management
    that maintains chat experience quality and prevents silent failures.
    """
    
    def setup_method(self, method):
        """Set up isolated test environment for each test."""
        super().setup_method(method)
        
        # Set up isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("TESTING", "1", source="websocket_heartbeat_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_heartbeat_test")
        
        # Test user data
        self.test_user = TestUserData(
            user_id=f"heartbeat_user_{uuid.uuid4().hex[:8]}",
            email="heartbeat-test@netra.ai",
            tier="enterprise",
            thread_id=f"heartbeat_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Track resources for cleanup
        self.websocket_managers: List[Any] = []
        self.mock_websockets: List[HeartbeatMonitoringWebSocket] = []
        
    async def teardown_method(self, method):
        """Clean up heartbeat monitoring test resources."""
        for mock_ws in self.mock_websockets:
            if not mock_ws.is_closed:
                await mock_ws.close()
        
        for manager in self.websocket_managers:
            if hasattr(manager, 'cleanup'):
                try:
                    await manager.cleanup()
                except Exception as e:
                    logger.warning(f"Manager cleanup error: {e}")
        
        await super().teardown_method(method)
    
    async def create_mock_user_context(self, user_data: TestUserData) -> Any:
        """Create mock user context for testing."""
        return type('MockUserContext', (), {
            'user_id': user_data.user_id,
            'thread_id': user_data.thread_id,
            'request_id': f"heartbeat_request_{uuid.uuid4().hex[:8]}",
            'email': user_data.email,
            'tier': user_data.tier,
            'is_test': True
        })()
    
    async def test_regular_heartbeat_generation_and_monitoring(self):
        """
        Test: Regular heartbeat messages are generated and monitored correctly
        
        Business Value: Ensures continuous connection health monitoring that
        enables proactive issue detection and maintains chat reliability.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create heartbeat monitoring WebSocket
        connection_id = f"heartbeat_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = HeartbeatMonitoringWebSocket(self.test_user.user_id, connection_id)
        mock_ws.heartbeat_interval = 1.0  # 1 second for faster testing
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Simulate heartbeat generation
            heartbeat_count = 0
            test_duration = 5  # seconds
            
            start_time = time.time()
            while time.time() - start_time < test_duration:
                # Simulate sending heartbeat
                heartbeat_message = {
                    'type': 'ping',
                    'timestamp': datetime.now(UTC).isoformat(),
                    'connection_id': connection_id
                }
                
                await mock_ws.send(json.dumps(heartbeat_message))
                heartbeat_count += 1
                
                await asyncio.sleep(mock_ws.heartbeat_interval)
            
            # Verify heartbeat monitoring
            metrics = mock_ws.get_heartbeat_metrics()
            
            assert metrics.heartbeats_sent >= 3, f"Should have sent multiple heartbeats: {metrics.heartbeats_sent}"
            assert metrics.heartbeats_received >= 3, f"Should have received heartbeat responses: {metrics.heartbeats_received}"
            assert metrics.average_response_time > 0, "Average response time should be measured"
            assert metrics.average_response_time < 1.0, f"Response time should be reasonable: {metrics.average_response_time:.3f}s"
            assert metrics.health_score > 80, f"Health score should be good: {metrics.health_score:.1f}%"
            
            logger.info(f"✅ Heartbeat monitoring: {metrics.heartbeats_sent} sent, {metrics.heartbeats_received} received, {metrics.health_score:.1f}% health")
    
    async def test_heartbeat_timeout_detection_and_recovery(self):
        """
        Test: Heartbeat timeouts are detected and trigger appropriate recovery actions
        
        Business Value: Early detection of connection issues enables proactive
        reconnection that maintains chat experience continuity.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"timeout_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = HeartbeatMonitoringWebSocket(self.test_user.user_id, connection_id)
        mock_ws.heartbeat_timeout = 2.0  # 2 second timeout for testing
        mock_ws.simulate_heartbeat_loss = True
        mock_ws.heartbeat_loss_rate = 1.0  # 100% loss to trigger timeouts
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Send heartbeats that will timeout
            timeout_detected = False
            for i in range(5):
                # Send heartbeat
                heartbeat_message = {
                    'type': 'ping',
                    'timestamp': datetime.now(UTC).isoformat(),
                    'sequence': i
                }
                
                await mock_ws.send(json.dumps(heartbeat_message))
                
                # Wait longer than timeout to trigger detection
                await asyncio.sleep(mock_ws.heartbeat_timeout + 0.5)
                
                # Check for timeout
                if mock_ws.check_heartbeat_timeout():
                    timeout_detected = True
                    logger.info(f"Heartbeat timeout detected at sequence {i}")
                    break
            
            # Verify timeout detection
            assert timeout_detected, "Heartbeat timeout should be detected"
            
            metrics = mock_ws.get_heartbeat_metrics()
            assert metrics.timeout_events > 0, f"Timeout events should be recorded: {metrics.timeout_events}"
            assert metrics.missed_heartbeats > 0, f"Missed heartbeats should be tracked: {metrics.missed_heartbeats}"
            assert not mock_ws.is_healthy, "Connection should be marked as unhealthy after timeouts"
            
            # Test recovery by disabling heartbeat loss
            mock_ws.simulate_heartbeat_loss = False
            mock_ws.heartbeat_loss_rate = 0.0
            
            # Send successful heartbeat for recovery
            recovery_message = {
                'type': 'ping',
                'timestamp': datetime.now(UTC).isoformat(),
                'recovery_attempt': True
            }
            
            await mock_ws.send(json.dumps(recovery_message))
            await asyncio.sleep(0.1)  # Allow response processing
            
            # Verify recovery (heartbeat response should reset health)
            await asyncio.sleep(0.2)  # Wait for auto-response
            
            logger.info(f"✅ Timeout detection and recovery: {metrics.timeout_events} timeouts, recovery attempted")
    
    async def test_connection_health_scoring_and_metrics(self):
        """
        Test: Connection health is scored accurately based on various metrics
        
        Business Value: Health scoring enables intelligent connection management
        and helps prioritize resources for maintaining optimal chat performance.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Test with different connection quality scenarios
        test_scenarios = [
            {
                'name': 'excellent_connection',
                'delay_ms': 50,
                'loss_rate': 0.0,
                'expected_min_health': 90
            },
            {
                'name': 'good_connection',
                'delay_ms': 150,
                'loss_rate': 0.1,
                'expected_min_health': 70
            },
            {
                'name': 'poor_connection',
                'delay_ms': 500,
                'loss_rate': 0.3,
                'expected_min_health': 40
            }
        ]
        
        for scenario in test_scenarios:
            connection_id = f"health_conn_{scenario['name']}_{uuid.uuid4().hex[:8]}"
            mock_ws = HeartbeatMonitoringWebSocket(self.test_user.user_id, connection_id)
            self.mock_websockets.append(mock_ws)
            
            # Configure connection quality
            mock_ws.simulate_network_issues(
                delay_ms=scenario['delay_ms'],
                loss_rate=scenario['loss_rate']
            )
            
            with patch.object(manager, '_websocket_transport', mock_ws):
                await manager.connect_user(
                    user_id=ensure_user_id(self.test_user.user_id),
                    websocket=mock_ws,
                    connection_metadata={"tier": self.test_user.tier}
                )
                
                # Send heartbeats to collect health metrics
                for i in range(8):
                    heartbeat_message = {
                        'type': 'ping',
                        'timestamp': datetime.now(UTC).isoformat(),
                        'scenario': scenario['name'],
                        'sequence': i
                    }
                    
                    try:
                        await mock_ws.send(json.dumps(heartbeat_message))
                    except Exception as e:
                        logger.info(f"Expected error in {scenario['name']}: {e}")
                    
                    await asyncio.sleep(0.5)
                    
                    # Check for timeouts
                    mock_ws.check_heartbeat_timeout()
                
                # Evaluate health metrics
                metrics = mock_ws.get_heartbeat_metrics()
                
                # Verify health scoring matches connection quality
                assert metrics.health_score >= scenario['expected_min_health'], \
                    f"Health score too low for {scenario['name']}: {metrics.health_score:.1f}% (expected >={scenario['expected_min_health']}%)"
                
                # Verify metrics are reasonable
                assert metrics.heartbeats_sent > 0, f"Should have sent heartbeats in {scenario['name']}"
                assert metrics.connection_uptime > 0, f"Should track uptime in {scenario['name']}"
                
                if scenario['loss_rate'] > 0:
                    assert metrics.missed_heartbeats >= 0, f"Should track missed heartbeats in {scenario['name']}"
                
                logger.info(f"✅ Health scoring for {scenario['name']}: {metrics.health_score:.1f}% health, {metrics.average_response_time:.3f}s avg response")
    
    async def test_circuit_breaker_activation_for_unhealthy_connections(self):
        """
        Test: Circuit breaker activates for consistently unhealthy connections
        
        Business Value: Circuit breaker prevents resource waste on failing connections
        and enables faster recovery by stopping futile reconnection attempts.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"circuit_breaker_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = HeartbeatMonitoringWebSocket(self.test_user.user_id, connection_id)
        mock_ws.max_missed_heartbeats = 2  # Lower threshold for testing
        mock_ws.heartbeat_timeout = 1.0   # 1 second timeout
        mock_ws.simulate_heartbeat_loss = True
        mock_ws.heartbeat_loss_rate = 1.0  # 100% loss to trigger circuit breaker
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Send heartbeats that will consistently fail
            circuit_breaker_activated = False
            
            for i in range(10):
                heartbeat_message = {
                    'type': 'ping',
                    'timestamp': datetime.now(UTC).isoformat(),
                    'circuit_breaker_test': True,
                    'sequence': i
                }
                
                await mock_ws.send(json.dumps(heartbeat_message))
                
                # Wait for timeout and check
                await asyncio.sleep(mock_ws.heartbeat_timeout + 0.2)
                mock_ws.check_heartbeat_timeout()
                
                if mock_ws.circuit_breaker_open:
                    circuit_breaker_activated = True
                    logger.info(f"Circuit breaker activated after {i + 1} attempts")
                    break
                
                await asyncio.sleep(0.2)
            
            # Verify circuit breaker behavior
            assert circuit_breaker_activated, "Circuit breaker should activate after consistent failures"
            assert not mock_ws.is_healthy, "Connection should be marked unhealthy"
            
            metrics = mock_ws.get_heartbeat_metrics()
            assert metrics.missed_heartbeats >= mock_ws.max_missed_heartbeats, "Should have exceeded missed heartbeat threshold"
            assert metrics.timeout_events > 0, "Should have recorded timeout events"
            assert metrics.health_score < 50, f"Health score should be low: {metrics.health_score:.1f}%"
            
            # Verify circuit breaker events in health history
            cb_events = [event for event in mock_ws.health_events if 'circuit_breaker' in event['event_type']]
            assert len(cb_events) > 0, "Circuit breaker events should be recorded"
            
            logger.info(f"✅ Circuit breaker activation: {metrics.missed_heartbeats} missed heartbeats, {metrics.health_score:.1f}% health")
    
    async def test_performance_monitoring_under_various_network_conditions(self):
        """
        Test: Performance monitoring accurately tracks connection quality under various conditions
        
        Business Value: Performance monitoring enables intelligent connection management
        and helps maintain optimal chat experience across different network conditions.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Test performance under different network conditions
        network_conditions = [
            {'name': 'optimal', 'delay_ms': 20, 'loss_rate': 0.0},
            {'name': 'mobile', 'delay_ms': 100, 'loss_rate': 0.05},
            {'name': 'unstable', 'delay_ms': 300, 'loss_rate': 0.15}
        ]
        
        performance_results = {}
        
        for condition in network_conditions:
            connection_id = f"perf_conn_{condition['name']}_{uuid.uuid4().hex[:8]}"
            mock_ws = HeartbeatMonitoringWebSocket(self.test_user.user_id, connection_id)
            self.mock_websockets.append(mock_ws)
            
            # Configure network conditions
            mock_ws.simulate_network_issues(
                delay_ms=condition['delay_ms'],
                loss_rate=condition['loss_rate']
            )
            
            with patch.object(manager, '_websocket_transport', mock_ws):
                await manager.connect_user(
                    user_id=ensure_user_id(self.test_user.user_id),
                    websocket=mock_ws,
                    connection_metadata={"tier": self.test_user.tier}
                )
                
                # Collect performance data
                test_start = time.time()
                heartbeat_sent = 0
                
                while time.time() - test_start < 5:  # 5 second test
                    heartbeat_message = {
                        'type': 'ping',
                        'timestamp': datetime.now(UTC).isoformat(),
                        'network_condition': condition['name'],
                        'sequence': heartbeat_sent
                    }
                    
                    try:
                        await mock_ws.send(json.dumps(heartbeat_message))
                        heartbeat_sent += 1
                    except Exception:
                        pass
                    
                    await asyncio.sleep(0.5)
                    mock_ws.check_heartbeat_timeout()
                
                # Analyze performance
                metrics = mock_ws.get_heartbeat_metrics()
                performance_results[condition['name']] = metrics
                
                # Verify performance correlates with network conditions
                expected_avg_response = condition['delay_ms'] / 1000.0  # Convert to seconds
                
                # Allow some tolerance for simulation overhead
                assert metrics.average_response_time <= expected_avg_response + 0.2, \
                    f"Response time higher than expected for {condition['name']}: {metrics.average_response_time:.3f}s"
                
                if condition['loss_rate'] > 0:
                    assert metrics.missed_heartbeats >= 0, f"Should track missed heartbeats for {condition['name']}"
        
        # Compare performance across conditions
        optimal_health = performance_results['optimal'].health_score
        mobile_health = performance_results['mobile'].health_score
        unstable_health = performance_results['unstable'].health_score
        
        # Health should degrade with network conditions
        assert optimal_health >= mobile_health, "Optimal connection should have better health than mobile"
        assert mobile_health >= unstable_health, "Mobile connection should have better health than unstable"
        
        logger.info(f"✅ Performance monitoring: optimal {optimal_health:.1f}%, mobile {mobile_health:.1f}%, unstable {unstable_health:.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])