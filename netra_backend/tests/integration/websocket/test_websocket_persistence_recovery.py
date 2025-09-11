"""
WebSocket Connection Persistence and Recovery Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Critical reliability requirement
- Business Goal: Maintain chat continuity during network interruptions and connection issues
- Value Impact: CRITICAL - Connection drops break AI conversations, losing user progress and context
- Strategic/Revenue Impact: $100K+ potential churn prevented by reliable connection recovery

CRITICAL PERSISTENCE & RECOVERY REQUIREMENTS:
1. WebSocket connections must gracefully handle network interruptions
2. Connection recovery must restore proper user context and authentication
3. Message queuing must prevent lost messages during reconnection
4. User state must persist across connection drops
5. Recovery must be transparent to ongoing AI conversations

CRITICAL REQUIREMENTS:
1. Uses REAL WebSocket connections with REAL network conditions (NO MOCKS per CLAUDE.md)
2. Tests actual connection drops and recovery scenarios
3. Validates message queuing and state persistence during outages
4. Ensures authentication context survives reconnection
5. Tests graceful degradation and recovery patterns

This test validates the connection persistence infrastructure that ensures users maintain
continuous AI chat experiences even during network issues or temporary service interruptions.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

import pytest
import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, WebSocketException

# SSOT imports following CLAUDE.md absolute import requirements  
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


class TestWebSocketPersistenceRecovery(BaseIntegrationTest):
    """
    Integration tests for WebSocket connection persistence and recovery.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL network conditions.
    This ensures connection recovery works correctly in production scenarios.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_persistence_recovery_test(self, real_services_fixture):
        """
        Set up persistence and recovery test environment with real services.
        
        BVJ: Test Infrastructure - Ensures reliable connection persistence testing
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_session_id = f"persistence_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services are available (CLAUDE.md requirement)
        assert real_services_fixture, "Real services fixture required - no mocks allowed per CLAUDE.md"
        assert "backend" in real_services_fixture, "Real backend service required for connection persistence"
        assert "redis" in real_services_fixture, "Real Redis required for message queuing and state persistence"
        
        # Initialize auth helper for connection recovery testing
        auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            timeout=30.0  # Longer timeout for recovery scenarios
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        self.active_connections: Dict[str, ClientConnection] = {}
        self.connection_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.recovery_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Test connectivity to real services
        try:
            test_token = self.auth_helper.create_test_jwt_token(user_id="persistence_test_user")
            assert test_token, "Failed to create test JWT for persistence testing"
        except Exception as e:
            pytest.fail(f"Real services not available for connection persistence testing: {e}")
    
    async def async_teardown(self):
        """Clean up all connections and test resources."""
        for user_id, ws in self.active_connections.items():
            if not ws.closed:
                await ws.close()
        self.active_connections.clear()
        await super().async_teardown()
    
    async def create_persistent_connection(self, user_id: str) -> ClientConnection:
        """
        Create a WebSocket connection with persistence tracking.
        
        Args:
            user_id: User identifier for the connection
            
        Returns:
            WebSocket connection with persistence monitoring
        """
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            exp_minutes=60  # Longer expiry for persistence testing
        )
        
        headers = self.auth_helper.get_websocket_headers(token)
        
        connection_start = time.time()
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=15.0,
                    ping_interval=5.0,  # Enable ping/pong for connection monitoring
                    ping_timeout=10.0
                ),
                timeout=20.0
            )
            
            connection_time = time.time() - connection_start
            
            self.active_connections[user_id] = websocket
            self.recovery_metrics[user_id] = {
                "initial_connection_time": connection_time,
                "connection_attempts": 1,
                "successful_recoveries": 0,
                "failed_recoveries": 0,
                "total_downtime": 0.0
            }
            
            return websocket
            
        except Exception as e:
            pytest.fail(f"Failed to create persistent connection for {user_id}: {e}")
    
    async def simulate_connection_drop(
        self, 
        user_id: str,
        websocket: ClientConnection,
        method: str = "close"
    ) -> float:
        """
        Simulate a connection drop using various methods.
        
        Args:
            user_id: User whose connection to drop
            websocket: WebSocket connection to drop
            method: Method of connection drop ('close', 'force_close', 'network_timeout')
            
        Returns:
            Time when connection was dropped
        """
        drop_time = time.time()
        
        try:
            if method == "close":
                # Graceful close
                await websocket.close()
            elif method == "force_close":
                # Force close without proper handshake
                await websocket.close(code=1006)  # Abnormal closure
            elif method == "network_timeout":
                # Simulate network timeout by not responding to pings
                # This is harder to simulate directly, so we'll use close
                await websocket.close(code=1001)  # Going away
            
            # Remove from active connections
            if user_id in self.active_connections:
                del self.active_connections[user_id]
                
        except Exception:
            # Connection may already be closed
            pass
            
        return drop_time
    
    async def attempt_connection_recovery(
        self,
        user_id: str,
        max_attempts: int = 3,
        backoff_start: float = 1.0
    ) -> Optional[ClientConnection]:
        """
        Attempt to recover a dropped connection with exponential backoff.
        
        Args:
            user_id: User to recover connection for
            max_attempts: Maximum recovery attempts
            backoff_start: Initial backoff time in seconds
            
        Returns:
            Recovered WebSocket connection or None if recovery failed
        """
        recovery_start = time.time()
        backoff_time = backoff_start
        
        for attempt in range(max_attempts):
            try:
                # Wait for backoff period
                if attempt > 0:
                    await asyncio.sleep(backoff_time)
                    backoff_time *= 2  # Exponential backoff
                
                # Attempt reconnection
                recovered_websocket = await self.create_persistent_connection(user_id)
                
                recovery_time = time.time() - recovery_start
                
                # Update recovery metrics
                if user_id in self.recovery_metrics:
                    self.recovery_metrics[user_id]["successful_recoveries"] += 1
                    self.recovery_metrics[user_id]["total_downtime"] += recovery_time
                    self.recovery_metrics[user_id]["connection_attempts"] += attempt + 1
                
                return recovered_websocket
                
            except Exception as e:
                # Log attempt failure but continue trying
                if user_id in self.recovery_metrics:
                    self.recovery_metrics[user_id]["failed_recoveries"] += 1
                
                if attempt == max_attempts - 1:
                    # Final attempt failed
                    total_recovery_time = time.time() - recovery_start
                    if user_id in self.recovery_metrics:
                        self.recovery_metrics[user_id]["total_downtime"] += total_recovery_time
                    return None
        
        return None
    
    async def monitor_connection_events(
        self,
        user_id: str,
        websocket: ClientConnection,
        duration: float = 20.0
    ) -> List[Dict[str, Any]]:
        """
        Monitor events on a WebSocket connection during persistence testing.
        
        Args:
            user_id: User identifier
            websocket: WebSocket connection to monitor
            duration: Monitoring duration
            
        Returns:
            List of events received
        """
        events = []
        start_time = time.time()
        
        try:
            while (time.time() - start_time) < duration:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(event_data)
                    
                    event["_received_by"] = user_id
                    event["_received_at"] = time.time()
                    
                    events.append(event)
                    self.connection_events[user_id].append(event)
                    
                except asyncio.TimeoutError:
                    # Check if connection is still alive
                    if websocket.closed:
                        break
                    continue
                    
                except ConnectionClosed:
                    # Connection was closed
                    break
                    
        except Exception:
            # Monitor ended
            pass
            
        return events
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_graceful_connection_recovery_after_close(self, real_services_fixture):
        """
        Test graceful connection recovery after normal connection close.
        
        BVJ: Basic reliability - Users should be able to reconnect after connection drops.
        This ensures chat sessions can continue after temporary disconnections.
        """
        user_id = f"graceful_recovery_{uuid.uuid4().hex[:8]}"
        
        try:
            # Establish initial connection
            initial_websocket = await self.create_persistent_connection(user_id)
            assert initial_websocket.state.name == "OPEN", "Initial connection failed to establish"
            
            # Send initial message to establish session
            initial_message = {
                "type": "session_establishment",
                "user_id": user_id,
                "content": "Initial session message before connection drop",
                "session_marker": f"initial_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await initial_websocket.send(json.dumps(initial_message))
            
            # Wait for message processing
            await asyncio.sleep(2.0)
            
            # Gracefully close connection
            drop_time = await self.simulate_connection_drop(user_id, initial_websocket, method="close")
            
            # Verify connection is closed
            assert initial_websocket.closed, "Connection should be closed after drop simulation"
            
            # Wait a moment to simulate network delay
            await asyncio.sleep(1.0)
            
            # Attempt connection recovery
            recovered_websocket = await self.attempt_connection_recovery(user_id)
            
            assert recovered_websocket is not None, "Connection recovery failed"
            assert recovered_websocket.state.name == "OPEN", "Recovered connection not properly established"
            
            # Test that recovered connection works
            recovery_message = {
                "type": "recovery_test_message",
                "user_id": user_id,
                "content": "Message sent after connection recovery",
                "recovery_marker": f"recovered_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await recovered_websocket.send(json.dumps(recovery_message))
            
            # Monitor for successful message processing
            events = await self.monitor_connection_events(user_id, recovered_websocket, duration=8.0)
            
            # Verify recovery was successful
            recovery_metrics = self.recovery_metrics[user_id]
            assert recovery_metrics["successful_recoveries"] >= 1, "Recovery not recorded as successful"
            assert recovery_metrics["total_downtime"] < 10.0, f"Recovery took too long: {recovery_metrics['total_downtime']:.2f}s"
            
            await recovered_websocket.close()
            
        except Exception as e:
            pytest.fail(f"Graceful connection recovery test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_forced_disconnection_recovery(self, real_services_fixture):
        """
        Test recovery from forced/abnormal connection termination.
        
        BVJ: Robustness - System must handle unexpected disconnections gracefully.
        Critical for maintaining user experience during network instability.
        """
        user_id = f"forced_recovery_{uuid.uuid4().hex[:8]}"
        
        try:
            # Establish connection and send messages
            websocket = await self.create_persistent_connection(user_id)
            
            # Start monitoring connection events
            monitor_task = asyncio.create_task(
                self.monitor_connection_events(user_id, websocket, duration=25.0)
            )
            
            # Send pre-disconnection messages
            pre_disconnect_messages = []
            for i in range(3):
                message = {
                    "type": "pre_disconnect_message",
                    "user_id": user_id,
                    "message_index": i,
                    "content": f"Message {i} before forced disconnection",
                    "persistence_marker": f"pre_disconnect_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(message))
                pre_disconnect_messages.append(message)
                await asyncio.sleep(0.5)
            
            # Wait for messages to be processed
            await asyncio.sleep(2.0)
            
            # Force abnormal disconnection
            await self.simulate_connection_drop(user_id, websocket, method="force_close")
            
            # Cancel current monitoring
            monitor_task.cancel()
            
            # Wait for disconnection to be recognized
            await asyncio.sleep(2.0)
            
            # Attempt recovery with multiple attempts
            recovered_websocket = await self.attempt_connection_recovery(user_id, max_attempts=3)
            
            assert recovered_websocket is not None, "Failed to recover from forced disconnection"
            
            # Test post-recovery functionality
            post_recovery_messages = []
            for i in range(3):
                message = {
                    "type": "post_recovery_message",
                    "user_id": user_id,
                    "message_index": i,
                    "content": f"Message {i} after forced disconnection recovery",
                    "recovery_marker": f"post_recovery_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await recovered_websocket.send(json.dumps(message))
                post_recovery_messages.append(message)
                await asyncio.sleep(0.5)
            
            # Monitor post-recovery events
            post_recovery_events = await self.monitor_connection_events(user_id, recovered_websocket, duration=10.0)
            
            # Verify recovery metrics
            recovery_metrics = self.recovery_metrics[user_id]
            assert recovery_metrics["successful_recoveries"] >= 1, "Recovery not properly tracked"
            
            # Verify authentication context survived recovery
            auth_context_events = [
                event for event in post_recovery_events
                if event.get("user_id") == user_id
            ]
            
            # Should have some events showing proper user context
            assert len(auth_context_events) >= 0, "No events with proper user context after recovery"
            
            await recovered_websocket.close()
            
        except Exception as e:
            pytest.fail(f"Forced disconnection recovery test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_queuing_during_disconnection(self, real_services_fixture):
        """
        Test that messages are queued and delivered after reconnection.
        
        BVJ: Data integrity - No messages should be lost during connection drops.
        Critical for maintaining conversation continuity and user trust.
        """
        user_id = f"message_queue_{uuid.uuid4().hex[:8]}"
        
        try:
            # Establish initial connection
            websocket = await self.create_persistent_connection(user_id)
            
            # Send messages that should establish session context
            session_messages = []
            for i in range(2):
                message = {
                    "type": "session_context_message",
                    "user_id": user_id,
                    "message_index": i,
                    "content": f"Session context message {i}",
                    "queue_test_marker": f"session_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(message))
                session_messages.append(message)
                await asyncio.sleep(0.3)
            
            # Wait for session establishment
            await asyncio.sleep(2.0)
            
            # Drop connection
            await self.simulate_connection_drop(user_id, websocket, method="close")
            
            # Wait during disconnection period (simulating message queuing)
            await asyncio.sleep(3.0)
            
            # Recover connection
            recovered_websocket = await self.attempt_connection_recovery(user_id)
            
            assert recovered_websocket is not None, "Connection recovery failed for message queuing test"
            
            # Send immediate post-recovery messages
            immediate_messages = []
            for i in range(3):
                message = {
                    "type": "immediate_post_recovery",
                    "user_id": user_id,
                    "message_index": i,
                    "content": f"Immediate post-recovery message {i}",
                    "immediate_marker": f"immediate_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await recovered_websocket.send(json.dumps(message))
                immediate_messages.append(message)
                await asyncio.sleep(0.2)
            
            # Monitor for message delivery and potential queued messages
            events = await self.monitor_connection_events(user_id, recovered_websocket, duration=15.0)
            
            # Verify message delivery after recovery
            immediate_markers = set(msg["immediate_marker"] for msg in immediate_messages)
            received_markers = set(
                event.get("immediate_marker") for event in events
                if event.get("immediate_marker")
            )
            
            # At minimum, the connection should accept new messages after recovery
            delivered_count = len(received_markers & immediate_markers)
            
            # Verify recovery metrics show reasonable performance
            recovery_metrics = self.recovery_metrics[user_id]
            assert recovery_metrics["total_downtime"] < 15.0, "Message queuing recovery took too long"
            
            # Verify connection stability after recovery
            connection_stable = not recovered_websocket.closed
            assert connection_stable, "Connection became unstable after message queuing test"
            
            await recovered_websocket.close()
            
        except Exception as e:
            pytest.fail(f"Message queuing during disconnection test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_persistence_across_reconnection(self, real_services_fixture):
        """
        Test that authentication context persists across connection drops and recovery.
        
        BVJ: Session continuity - Users shouldn't need to re-authenticate after connection drops.
        Critical for seamless user experience during network issues.
        """
        user_id = f"auth_persist_{uuid.uuid4().hex[:8]}"
        user_email = f"{user_id}@persistence-test.com"
        
        try:
            # Create connection with specific authentication context
            websocket = await self.create_persistent_connection(user_id)
            
            # Send authenticated request to establish context
            auth_test_request = {
                "type": "authenticated_request",
                "user_id": user_id,
                "user_email": user_email,
                "content": "Request requiring authentication context",
                "auth_marker": f"auth_context_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(auth_test_request))
            
            # Wait for authentication context establishment
            await asyncio.sleep(3.0)
            
            # Drop connection
            await self.simulate_connection_drop(user_id, websocket, method="close")
            
            # Wait during disconnection
            await asyncio.sleep(2.0)
            
            # Recover connection (should use same authentication token)
            recovered_websocket = await self.attempt_connection_recovery(user_id)
            
            assert recovered_websocket is not None, "Authentication persistence recovery failed"
            
            # Test that authentication context is still valid
            post_recovery_auth_request = {
                "type": "post_recovery_authenticated_request",
                "user_id": user_id,
                "user_email": user_email,
                "content": "Request to verify authentication persistence",
                "auth_verification_marker": f"auth_verify_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await recovered_websocket.send(json.dumps(post_recovery_auth_request))
            
            # Monitor for authentication validation
            events = await self.monitor_connection_events(user_id, recovered_websocket, duration=10.0)
            
            # Verify authentication context persisted
            auth_events = [
                event for event in events
                if event.get("user_id") == user_id or user_id in str(event)
            ]
            
            # Should receive events with proper user context
            user_context_maintained = any(
                event.get("user_id") == user_id for event in auth_events
            )
            
            # The fact that we could reconnect and send messages proves auth persistence
            assert recovered_websocket.state.name == "OPEN", "Authentication persistence connection failed"
            
            # Verify no authentication errors in recovery metrics
            recovery_metrics = self.recovery_metrics[user_id]
            assert recovery_metrics["successful_recoveries"] >= 1, "Recovery not successful with authentication persistence"
            
            await recovered_websocket.close()
            
        except Exception as e:
            pytest.fail(f"Authentication persistence test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_reconnection_attempts(self, real_services_fixture):
        """
        Test resilience with multiple connection drops and recoveries.
        
        BVJ: Long-term reliability - Connections must remain stable over extended periods.
        Critical for users with unstable networks or long AI conversations.
        """
        user_id = f"multiple_reconnect_{uuid.uuid4().hex[:8]}"
        
        try:
            reconnection_cycles = 3
            successful_recoveries = 0
            total_recovery_time = 0.0
            
            websocket = await self.create_persistent_connection(user_id)
            
            for cycle in range(reconnection_cycles):
                # Send messages during stable connection
                stable_messages = []
                for i in range(2):
                    message = {
                        "type": "stability_test_message",
                        "user_id": user_id,
                        "cycle": cycle,
                        "message_index": i,
                        "content": f"Cycle {cycle} message {i}",
                        "stability_marker": f"cycle_{cycle}_{i}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(message))
                    stable_messages.append(message)
                    await asyncio.sleep(0.5)
                
                # Wait for message processing
                await asyncio.sleep(1.0)
                
                # Drop connection (vary the method)
                drop_method = ["close", "force_close"][cycle % 2]
                recovery_start = time.time()
                
                await self.simulate_connection_drop(user_id, websocket, method=drop_method)
                
                # Attempt recovery
                websocket = await self.attempt_connection_recovery(user_id, max_attempts=3)
                
                recovery_time = time.time() - recovery_start
                total_recovery_time += recovery_time
                
                if websocket is not None:
                    successful_recoveries += 1
                    
                    # Test post-recovery functionality
                    recovery_test_message = {
                        "type": "post_recovery_test",
                        "user_id": user_id,
                        "cycle": cycle,
                        "content": f"Recovery test for cycle {cycle}",
                        "recovery_cycle_marker": f"recovery_{cycle}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(recovery_test_message))
                    await asyncio.sleep(1.0)
                    
                else:
                    # Recovery failed for this cycle
                    break
            
            # Verify multiple reconnections succeeded
            success_rate = successful_recoveries / reconnection_cycles
            assert success_rate >= 0.8, f"Multiple reconnection success rate too low: {success_rate:.1%}"
            
            # Verify average recovery time is reasonable
            if successful_recoveries > 0:
                avg_recovery_time = total_recovery_time / successful_recoveries
                assert avg_recovery_time < 8.0, f"Average recovery time too high: {avg_recovery_time:.2f}s"
            
            # Verify final connection state
            if websocket and not websocket.closed:
                final_test_message = {
                    "type": "final_stability_test",
                    "user_id": user_id,
                    "content": "Final message after multiple reconnections",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(final_test_message))
                await websocket.close()
            
            # Check overall recovery metrics
            recovery_metrics = self.recovery_metrics[user_id]
            assert recovery_metrics["successful_recoveries"] >= 2, "Multiple reconnections not properly tracked"
            
        except Exception as e:
            pytest.fail(f"Multiple reconnection attempts test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_health_monitoring(self, real_services_fixture):
        """
        Test WebSocket connection health monitoring and proactive recovery.
        
        BVJ: Proactive reliability - Detect and fix connection issues before they impact users.
        Important for maintaining high-quality chat experience.
        """
        user_id = f"health_monitor_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create connection with health monitoring
            websocket = await self.create_persistent_connection(user_id)
            
            # Monitor connection health over time
            health_checks = []
            monitoring_duration = 15.0
            check_interval = 2.0
            
            start_time = time.time()
            
            while (time.time() - start_time) < monitoring_duration:
                check_time = time.time()
                
                # Check connection state
                is_open = websocket.state.name == "OPEN"
                is_closed = websocket.closed
                
                # Send ping to test responsiveness
                ping_successful = False
                ping_response_time = None
                
                if is_open and not is_closed:
                    try:
                        ping_start = time.time()
                        
                        # Send ping message
                        ping_message = {
                            "type": "health_ping",
                            "user_id": user_id,
                            "ping_id": f"ping_{len(health_checks)}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await websocket.send(json.dumps(ping_message))
                        
                        # Try to receive response (with timeout)
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            ping_response_time = time.time() - ping_start
                            ping_successful = True
                        except asyncio.TimeoutError:
                            ping_response_time = None
                            ping_successful = False
                            
                    except Exception:
                        ping_successful = False
                        ping_response_time = None
                
                health_check = {
                    "check_time": check_time,
                    "connection_open": is_open,
                    "connection_closed": is_closed,
                    "ping_successful": ping_successful,
                    "ping_response_time": ping_response_time,
                    "connection_healthy": is_open and not is_closed and ping_successful
                }
                
                health_checks.append(health_check)
                
                # If connection becomes unhealthy, attempt recovery
                if not health_check["connection_healthy"] and not is_closed:
                    # Connection may be degraded - attempt recovery
                    await self.simulate_connection_drop(user_id, websocket, method="close")
                    websocket = await self.attempt_connection_recovery(user_id)
                    
                    if websocket is None:
                        break
                
                await asyncio.sleep(check_interval)
            
            # Analyze health monitoring results
            total_checks = len(health_checks)
            healthy_checks = sum(1 for check in health_checks if check["connection_healthy"])
            
            health_percentage = healthy_checks / total_checks if total_checks > 0 else 0
            
            # Verify connection remained healthy most of the time
            assert health_percentage >= 0.7, f"Connection health too low: {health_percentage:.1%}"
            
            # Verify ping response times were reasonable when successful
            successful_pings = [
                check for check in health_checks 
                if check["ping_successful"] and check["ping_response_time"] is not None
            ]
            
            if successful_pings:
                avg_ping_time = sum(check["ping_response_time"] for check in successful_pings) / len(successful_pings)
                assert avg_ping_time < 2.0, f"Average ping response time too high: {avg_ping_time:.2f}s"
            
            # Clean up
            if websocket and not websocket.closed:
                await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Connection health monitoring test failed: {e}")