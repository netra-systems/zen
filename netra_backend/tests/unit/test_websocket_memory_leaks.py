# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive test suite for WebSocket manager memory leak detection.

# REMOVED_SYNTAX_ERROR: Business Value Justification:
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
    # REMOVED_SYNTAX_ERROR: - Business Goal: Stability & Risk Reduction
    # REMOVED_SYNTAX_ERROR: - Value Impact: Prevents system crashes from memory exhaustion
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Ensures system can handle sustained user load

    # REMOVED_SYNTAX_ERROR: This test suite verifies:
        # REMOVED_SYNTAX_ERROR: 1. Connection limits enforcement (MAX_CONNECTIONS_PER_USER = 5, MAX_TOTAL_CONNECTIONS = 1000)
        # REMOVED_SYNTAX_ERROR: 2. Automatic eviction of oldest connections when limits exceeded
        # REMOVED_SYNTAX_ERROR: 3. TTL cache expiration for connections (5 minute TTL)
        # REMOVED_SYNTAX_ERROR: 4. Periodic cleanup of stale connections
        # REMOVED_SYNTAX_ERROR: 5. Memory growth detection under sustained load
        # REMOVED_SYNTAX_ERROR: 6. Resource cleanup on disconnection
        # REMOVED_SYNTAX_ERROR: 7. Proper cleanup of all tracking dictionaries

        # REMOVED_SYNTAX_ERROR: Tests are designed to FAIL with current implementation to demonstrate memory leak issues.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import gc
        # REMOVED_SYNTAX_ERROR: import logging
        # REMOVED_SYNTAX_ERROR: import psutil
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone, timedelta
        # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Optional, Set
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils.test_redis_manager import TestRedisManager
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Skip all tests in this file as the memory leak detection functionality
        # was part of the old WebSocket manager that has been replaced with UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: pytest.skip("WebSocket memory leak tests obsolete - functionality removed", allow_module_level=True)

        # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket, WebSocketDisconnect
        # REMOVED_SYNTAX_ERROR: from fastapi.websockets import WebSocketState

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
            # REMOVED_SYNTAX_ERROR: except ImportError:
                # REMOVED_SYNTAX_ERROR: pytest.skip("Required modules have been removed or have missing dependencies", allow_module_level=True)


                # REMOVED_SYNTAX_ERROR: logger = logging.getLogger(__name__)

                # Memory leak detection constants - these should be enforced but aren't currently
                # REMOVED_SYNTAX_ERROR: MAX_CONNECTIONS_PER_USER = 5
                # REMOVED_SYNTAX_ERROR: MAX_TOTAL_CONNECTIONS = 1000
                # REMOVED_SYNTAX_ERROR: TTL_SECONDS = 300  # 5 minutes


                # COMMENTED OUT: MockWebSocket class - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
                # However, we still need MockWebSocket for these specific memory leak tests
# REMOVED_SYNTAX_ERROR: class MockWebSocket:
    # REMOVED_SYNTAX_ERROR: """Mock WebSocket for testing without actual connections."""

# REMOVED_SYNTAX_ERROR: def __init__(self, connection_id: str = None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.connection_id = connection_id or "formatted_string"
    # Add proper WebSocket state attributes for compatibility
    # REMOVED_SYNTAX_ERROR: self.state = WebSocketState.CONNECTED
    # REMOVED_SYNTAX_ERROR: self.client_state = WebSocketState.CONNECTED  # For is_websocket_connected
    # REMOVED_SYNTAX_ERROR: self.application_state = WebSocketState.CONNECTED  # For is_websocket_connected
    # REMOVED_SYNTAX_ERROR: self.messages_sent: List[Dict] = []
    # REMOVED_SYNTAX_ERROR: self.closed = False
    # REMOVED_SYNTAX_ERROR: self.close_code: Optional[int] = None
    # REMOVED_SYNTAX_ERROR: self.close_reason: Optional[str] = None

# REMOVED_SYNTAX_ERROR: async def send_json(self, data: Dict):
    # REMOVED_SYNTAX_ERROR: """Mock sending JSON data."""
    # REMOVED_SYNTAX_ERROR: if self.state != WebSocketState.CONNECTED or self.closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is not connected")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(data)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Mock closing the WebSocket."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.state = WebSocketState.DISCONNECTED
    # REMOVED_SYNTAX_ERROR: self.client_state = WebSocketState.DISCONNECTED
    # REMOVED_SYNTAX_ERROR: self.application_state = WebSocketState.DISCONNECTED
    # REMOVED_SYNTAX_ERROR: self.closed = True
    # REMOVED_SYNTAX_ERROR: self.close_code = code
    # REMOVED_SYNTAX_ERROR: self.close_reason = reason

# REMOVED_SYNTAX_ERROR: def __eq__(self, other):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return isinstance(other, MockWebSocket) and self.connection_id == other.connection_id

# REMOVED_SYNTAX_ERROR: def __hash__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return hash(self.connection_id)


# REMOVED_SYNTAX_ERROR: class MemoryProfiler:
    # REMOVED_SYNTAX_ERROR: """Helper class for tracking memory usage during tests."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.process = psutil.Process()
    # REMOVED_SYNTAX_ERROR: self.initial_memory = 0
    # REMOVED_SYNTAX_ERROR: self.peak_memory = 0
    # REMOVED_SYNTAX_ERROR: self.samples: List[float] = []

# REMOVED_SYNTAX_ERROR: def start_profiling(self):
    # REMOVED_SYNTAX_ERROR: """Start memory profiling."""
    # REMOVED_SYNTAX_ERROR: gc.collect()  # Force garbage collection before measuring
    # REMOVED_SYNTAX_ERROR: self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
    # REMOVED_SYNTAX_ERROR: self.peak_memory = self.initial_memory
    # REMOVED_SYNTAX_ERROR: self.samples = [self.initial_memory]
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def sample_memory(self) -> float:
    # REMOVED_SYNTAX_ERROR: """Take a memory sample and return current usage in MB."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: current_memory = self.process.memory_info().rss / 1024 / 1024
    # REMOVED_SYNTAX_ERROR: self.samples.append(current_memory)
    # REMOVED_SYNTAX_ERROR: if current_memory > self.peak_memory:
        # REMOVED_SYNTAX_ERROR: self.peak_memory = current_memory
        # REMOVED_SYNTAX_ERROR: return current_memory

# REMOVED_SYNTAX_ERROR: def get_memory_growth(self) -> float:
    # REMOVED_SYNTAX_ERROR: """Get total memory growth since profiling started."""
    # REMOVED_SYNTAX_ERROR: current_memory = self.sample_memory()
    # REMOVED_SYNTAX_ERROR: growth = current_memory - self.initial_memory
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: return growth

# REMOVED_SYNTAX_ERROR: def detect_memory_leak(self, threshold_mb: float = 10.0) -> bool:
    # REMOVED_SYNTAX_ERROR: """Detect if memory growth exceeds threshold, indicating a potential leak."""
    # REMOVED_SYNTAX_ERROR: growth = self.get_memory_growth()
    # REMOVED_SYNTAX_ERROR: is_leak = growth > threshold_mb
    # REMOVED_SYNTAX_ERROR: if is_leak:
        # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")
        # REMOVED_SYNTAX_ERROR: return is_leak


        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def memory_profiler():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Fixture that provides memory profiling capabilities."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: profiler = MemoryProfiler()
    # REMOVED_SYNTAX_ERROR: yield profiler


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def manager():
    # REMOVED_SYNTAX_ERROR: """Fixture that provides a fresh WebSocket manager instance."""
    # Reset singleton instance for clean state
    # REMOVED_SYNTAX_ERROR: WebSocketManager._instance = None
    # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()
    # REMOVED_SYNTAX_ERROR: yield manager
    # Cleanup after test
    # REMOVED_SYNTAX_ERROR: await manager.shutdown()


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websockets():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: """Fixture that creates mock WebSocket connections."""
# REMOVED_SYNTAX_ERROR: def _create_mock_websockets(count: int) -> List[MockWebSocket]:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return [MockWebSocket("formatted_string") for i in range(count)]
    # REMOVED_SYNTAX_ERROR: return _create_mock_websockets


# REMOVED_SYNTAX_ERROR: class TestConnectionLimits:
    # REMOVED_SYNTAX_ERROR: """Test connection limit enforcement - these tests SHOULD FAIL with current implementation."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_max_connections_per_user_enforcement(self, manager, mock_websockets):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test that MAX_CONNECTIONS_PER_USER=5 is enforced.
        # REMOVED_SYNTAX_ERROR: EXPECTED TO FAIL: Current implementation has no connection limits.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: user_id = "test_user_limits"
        # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(10)  # Try to create 10 connections

        # REMOVED_SYNTAX_ERROR: connected_ids = []

        # Try to connect 10 WebSockets for same user
        # REMOVED_SYNTAX_ERROR: for i, websocket in enumerate(websockets):
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)
                # REMOVED_SYNTAX_ERROR: connected_ids.append(conn_id)
                # REMOVED_SYNTAX_ERROR: except WebSocketDisconnect as e:
                    # Should start rejecting after MAX_CONNECTIONS_PER_USER
                    # REMOVED_SYNTAX_ERROR: if i >= MAX_CONNECTIONS_PER_USER:
                        # REMOVED_SYNTAX_ERROR: assert "connection limit" in str(e.reason).lower()
                        # REMOVED_SYNTAX_ERROR: else:
                            # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                            # Should only have MAX_CONNECTIONS_PER_USER connections
                            # REMOVED_SYNTAX_ERROR: assert len(connected_ids) == MAX_CONNECTIONS_PER_USER, \
                            # REMOVED_SYNTAX_ERROR: "formatted_string"

                            # Verify user_connections tracking
                            # REMOVED_SYNTAX_ERROR: user_connections = manager.user_connections.get(user_id, set())
                            # REMOVED_SYNTAX_ERROR: assert len(user_connections) == MAX_CONNECTIONS_PER_USER, \
                            # REMOVED_SYNTAX_ERROR: "formatted_string"

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_max_total_connections_enforcement(self, manager, mock_websockets):
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: Test that MAX_TOTAL_CONNECTIONS=1000 is enforced across all users.
                                # REMOVED_SYNTAX_ERROR: EXPECTED TO FAIL: Current implementation has no total connection limits.
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: pass
                                # Create connections approaching the limit
                                # REMOVED_SYNTAX_ERROR: users_created = 0
                                # REMOVED_SYNTAX_ERROR: total_connections = 0

                                # Create users with multiple connections each until we hit the limit
                                # REMOVED_SYNTAX_ERROR: while total_connections < MAX_TOTAL_CONNECTIONS + 50:  # Try to exceed limit
                                # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                                # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(5)  # 5 connections per user

                                # REMOVED_SYNTAX_ERROR: connections_for_user = 0
                                # REMOVED_SYNTAX_ERROR: for websocket in websockets:
                                    # REMOVED_SYNTAX_ERROR: try:
                                        # REMOVED_SYNTAX_ERROR: await manager.connect_user(user_id, websocket)
                                        # REMOVED_SYNTAX_ERROR: connections_for_user += 1
                                        # REMOVED_SYNTAX_ERROR: total_connections += 1
                                        # REMOVED_SYNTAX_ERROR: except WebSocketDisconnect as e:
                                            # REMOVED_SYNTAX_ERROR: if total_connections >= MAX_TOTAL_CONNECTIONS:
                                                # REMOVED_SYNTAX_ERROR: assert "total connection limit" in str(e.reason).lower()
                                                # REMOVED_SYNTAX_ERROR: break
                                                # REMOVED_SYNTAX_ERROR: else:
                                                    # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                                                    # REMOVED_SYNTAX_ERROR: users_created += 1

                                                    # Safety break
                                                    # REMOVED_SYNTAX_ERROR: if users_created > 250:
                                                        # REMOVED_SYNTAX_ERROR: break

                                                        # Should not exceed MAX_TOTAL_CONNECTIONS
                                                        # REMOVED_SYNTAX_ERROR: actual_connections = len(manager.connections)
                                                        # REMOVED_SYNTAX_ERROR: assert actual_connections <= MAX_TOTAL_CONNECTIONS, \
                                                        # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_oldest_connection_eviction(self, manager, mock_websockets):
                                                            # REMOVED_SYNTAX_ERROR: '''
                                                            # REMOVED_SYNTAX_ERROR: Test that oldest connections are evicted when limits are exceeded.
                                                            # REMOVED_SYNTAX_ERROR: EXPECTED TO FAIL: Current implementation has no eviction mechanism.
                                                            # REMOVED_SYNTAX_ERROR: '''
                                                            # REMOVED_SYNTAX_ERROR: pass
                                                            # REMOVED_SYNTAX_ERROR: user_id = "test_user_eviction"
                                                            # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(MAX_CONNECTIONS_PER_USER + 3)

                                                            # Connect initial connections and track their IDs
                                                            # REMOVED_SYNTAX_ERROR: initial_connections = []
                                                            # REMOVED_SYNTAX_ERROR: for i in range(MAX_CONNECTIONS_PER_USER):
                                                                # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websockets[i])
                                                                # REMOVED_SYNTAX_ERROR: initial_connections.append(conn_id)
                                                                # Simulate time passage to ensure ordering
                                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)

                                                                # Record initial connection timestamps
                                                                # REMOVED_SYNTAX_ERROR: initial_timestamps = {}
                                                                # REMOVED_SYNTAX_ERROR: for conn_id in initial_connections:
                                                                    # REMOVED_SYNTAX_ERROR: if conn_id in manager.connections:
                                                                        # REMOVED_SYNTAX_ERROR: initial_timestamps[conn_id] = manager.connections[conn_id]["connected_at"]

                                                                        # Try to add more connections - should fail due to limit
                                                                        # REMOVED_SYNTAX_ERROR: new_connections = []
                                                                        # REMOVED_SYNTAX_ERROR: for i in range(MAX_CONNECTIONS_PER_USER, len(websockets)):
                                                                            # REMOVED_SYNTAX_ERROR: try:
                                                                                # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websockets[i])
                                                                                # REMOVED_SYNTAX_ERROR: new_connections.append(conn_id)
                                                                                # REMOVED_SYNTAX_ERROR: except WebSocketDisconnect:
                                                                                    # Expected - connection limit enforced
                                                                                    # REMOVED_SYNTAX_ERROR: pass

                                                                                    # Check that total connections for user doesn't exceed limit
                                                                                    # REMOVED_SYNTAX_ERROR: user_connections = manager.user_connections.get(user_id, set())
                                                                                    # REMOVED_SYNTAX_ERROR: assert len(user_connections) <= MAX_CONNECTIONS_PER_USER, \
                                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                                    # With the current implementation, no new connections should be added
                                                                                    # The limit is enforced by raising an exception
                                                                                    # REMOVED_SYNTAX_ERROR: assert len(new_connections) == 0, \
                                                                                    # REMOVED_SYNTAX_ERROR: "No new connections should be added when limit is reached"

                                                                                    # Verify initial connections still exist (no eviction, just rejection)
                                                                                    # REMOVED_SYNTAX_ERROR: for conn_id in initial_connections[:MAX_CONNECTIONS_PER_USER]:
                                                                                        # REMOVED_SYNTAX_ERROR: assert conn_id in manager.connections, \
                                                                                        # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestTTLCacheExpiration:
    # REMOVED_SYNTAX_ERROR: """Test TTL cache expiration - these tests SHOULD FAIL with current implementation."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_connection_ttl_expiration(self, manager, mock_websockets):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test that connections expire after TTL_SECONDS=300 (5 minutes).
        # REMOVED_SYNTAX_ERROR: EXPECTED TO FAIL: Current implementation has no TTL mechanism.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: user_id = "test_ttl_user"
        # REMOVED_SYNTAX_ERROR: websocket = mock_websockets(1)[0]

        # Connect user
        # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)
        # REMOVED_SYNTAX_ERROR: assert conn_id in manager.connections

        # Simulate time passage by manually updating connection timestamp
        # REMOVED_SYNTAX_ERROR: expired_time = datetime.now(timezone.utc) - timedelta(seconds=TTL_SECONDS + 60)
        # REMOVED_SYNTAX_ERROR: manager.connections[conn_id]["connected_at"] = expired_time
        # REMOVED_SYNTAX_ERROR: manager.connections[conn_id]["last_activity"] = expired_time

        # Run cleanup - should remove expired connection
        # REMOVED_SYNTAX_ERROR: cleaned_count = await manager.cleanup_stale_connections()

        # Connection should be removed due to TTL expiration
        # REMOVED_SYNTAX_ERROR: assert conn_id not in manager.connections, \
        # REMOVED_SYNTAX_ERROR: "Expired connection should be removed by TTL cleanup"
        # REMOVED_SYNTAX_ERROR: assert cleaned_count >= 1, \
        # REMOVED_SYNTAX_ERROR: "Cleanup should report at least one connection removed"

        # User should have no connections
        # REMOVED_SYNTAX_ERROR: user_connections = manager.user_connections.get(user_id, set())
        # REMOVED_SYNTAX_ERROR: assert len(user_connections) == 0, \
        # REMOVED_SYNTAX_ERROR: "User should have no connections after TTL expiration"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_ttl_cache_with_activity_refresh(self, manager, mock_websockets):
            # REMOVED_SYNTAX_ERROR: '''
            # REMOVED_SYNTAX_ERROR: Test that active connections have their TTL refreshed.
            # REMOVED_SYNTAX_ERROR: EXPECTED TO FAIL: Current implementation doesn"t implement TTL refresh.
            # REMOVED_SYNTAX_ERROR: '''
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_id = "test_ttl_activity"
            # REMOVED_SYNTAX_ERROR: websocket = mock_websockets(1)[0]

            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)

            # Set connection to near-expiry
            # REMOVED_SYNTAX_ERROR: near_expiry = datetime.now(timezone.utc) - timedelta(seconds=TTL_SECONDS - 30)
            # REMOVED_SYNTAX_ERROR: manager.connections[conn_id]["connected_at"] = near_expiry
            # REMOVED_SYNTAX_ERROR: manager.connections[conn_id]["last_activity"] = near_expiry

            # Simulate activity by sending a message
            # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, {"type": "test", "data": "refresh_ttl"})

            # Connection should have updated last_activity
            # REMOVED_SYNTAX_ERROR: last_activity = manager.connections[conn_id]["last_activity"]
            # REMOVED_SYNTAX_ERROR: time_since_activity = (datetime.now(timezone.utc) - last_activity).total_seconds()
            # REMOVED_SYNTAX_ERROR: assert time_since_activity < 10, \
            # REMOVED_SYNTAX_ERROR: "last_activity should be updated after sending message"

            # Run cleanup - connection should NOT be removed
            # REMOVED_SYNTAX_ERROR: await manager.cleanup_stale_connections()
            # REMOVED_SYNTAX_ERROR: assert conn_id in manager.connections, \
            # REMOVED_SYNTAX_ERROR: "Active connection should not be removed during TTL cleanup"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_periodic_ttl_cleanup_automation(self, manager, mock_websockets):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: Test that periodic cleanup automatically removes TTL-expired connections.
                # REMOVED_SYNTAX_ERROR: EXPECTED TO FAIL: Current implementation has no automatic TTL cleanup.
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: pass
                # This test would require implementing a background task for periodic cleanup
                # For now, we'll test manual cleanup behavior that should exist

                # REMOVED_SYNTAX_ERROR: user_ids = ["formatted_string" for i in range(10)]
                # REMOVED_SYNTAX_ERROR: connections = []

                # Create multiple connections
                # REMOVED_SYNTAX_ERROR: for user_id in user_ids:
                    # REMOVED_SYNTAX_ERROR: websocket = mock_websockets(1)[0]
                    # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)
                    # REMOVED_SYNTAX_ERROR: connections.append(conn_id)

                    # Expire half of them
                    # REMOVED_SYNTAX_ERROR: expired_time = datetime.now(timezone.utc) - timedelta(seconds=TTL_SECONDS + 60)
                    # REMOVED_SYNTAX_ERROR: for i in range(0, 5):  # Expire first 5
                    # REMOVED_SYNTAX_ERROR: conn_id = connections[i]
                    # REMOVED_SYNTAX_ERROR: manager.connections[conn_id]["connected_at"] = expired_time
                    # REMOVED_SYNTAX_ERROR: manager.connections[conn_id]["last_activity"] = expired_time

                    # Manual cleanup should remove expired connections
                    # REMOVED_SYNTAX_ERROR: initial_count = len(manager.connections)
                    # REMOVED_SYNTAX_ERROR: cleaned_count = await manager.cleanup_stale_connections()
                    # REMOVED_SYNTAX_ERROR: final_count = len(manager.connections)

                    # REMOVED_SYNTAX_ERROR: assert cleaned_count == 5, "formatted_string"
                    # REMOVED_SYNTAX_ERROR: assert final_count == initial_count - 5, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestMemoryLeakDetection:
    # REMOVED_SYNTAX_ERROR: """Test memory growth detection under sustained load."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_sustained_connection_load_memory_growth(self, manager, mock_websockets, memory_profiler):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test memory growth under sustained connection load.
        # REMOVED_SYNTAX_ERROR: SHOULD DETECT: Memory growth from lack of proper cleanup.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: memory_profiler.start_profiling()

        # Phase 1: Create many connections
        # REMOVED_SYNTAX_ERROR: users_and_connections = []
        # REMOVED_SYNTAX_ERROR: for batch in range(10):  # 10 batches
        # REMOVED_SYNTAX_ERROR: batch_connections = []
        # REMOVED_SYNTAX_ERROR: for user_num in range(50):  # 50 users per batch
        # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
        # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(3)  # 3 connections per user

        # REMOVED_SYNTAX_ERROR: user_connections = []
        # REMOVED_SYNTAX_ERROR: for websocket in websockets:
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)
                # REMOVED_SYNTAX_ERROR: user_connections.append((user_id, conn_id, websocket))
                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                    # REMOVED_SYNTAX_ERROR: batch_connections.extend(user_connections)

                    # REMOVED_SYNTAX_ERROR: users_and_connections.extend(batch_connections)
                    # REMOVED_SYNTAX_ERROR: memory_profiler.sample_memory()

                    # Small delay to allow any cleanup to occur
                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                    # Phase 2: Disconnect all connections
                    # REMOVED_SYNTAX_ERROR: for user_id, conn_id, websocket in users_and_connections:
                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: await manager.disconnect_user(user_id, websocket)
                            # REMOVED_SYNTAX_ERROR: except Exception as e:
                                # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                                # Force cleanup
                                # REMOVED_SYNTAX_ERROR: await manager.cleanup_stale_connections()
                                # REMOVED_SYNTAX_ERROR: gc.collect()  # Force garbage collection

                                # Check final memory usage
                                # REMOVED_SYNTAX_ERROR: memory_growth = memory_profiler.get_memory_growth()

                                # Check for memory leak indicators
                                # REMOVED_SYNTAX_ERROR: remaining_connections = len(manager.connections)
                                # REMOVED_SYNTAX_ERROR: remaining_user_connections = sum(len(conns) for conns in manager.user_connections.values())
                                # REMOVED_SYNTAX_ERROR: remaining_rooms = sum(len(room) for room in manager.room_memberships.values())
                                # REMOVED_SYNTAX_ERROR: remaining_run_ids = sum(len(runs) for runs in manager.run_id_connections.values())

                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string" )
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                # REMOVED_SYNTAX_ERROR: "formatted_string")

                                # These assertions should FAIL with current implementation
                                # REMOVED_SYNTAX_ERROR: assert remaining_connections == 0, \
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                # REMOVED_SYNTAX_ERROR: assert remaining_user_connections == 0, \
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                # REMOVED_SYNTAX_ERROR: assert memory_growth < 20.0, \
                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_rapid_connect_disconnect_cycles(self, manager, mock_websockets, memory_profiler):
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: Test memory behavior with rapid connect/disconnect cycles.
                                    # REMOVED_SYNTAX_ERROR: SHOULD DETECT: Memory accumulation from improper cleanup.
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # REMOVED_SYNTAX_ERROR: memory_profiler.start_profiling()

                                    # Perform rapid connect/disconnect cycles
                                    # REMOVED_SYNTAX_ERROR: cycles = 100
                                    # REMOVED_SYNTAX_ERROR: for cycle in range(cycles):
                                        # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"  # Reuse some user IDs
                                        # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(5)

                                        # Quick connect
                                        # REMOVED_SYNTAX_ERROR: connections = []
                                        # REMOVED_SYNTAX_ERROR: for websocket in websockets:
                                            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)
                                            # REMOVED_SYNTAX_ERROR: connections.append((user_id, websocket))

                                            # Quick disconnect
                                            # REMOVED_SYNTAX_ERROR: for user_id, websocket in connections:
                                                # REMOVED_SYNTAX_ERROR: await manager.disconnect_user(user_id, websocket)

                                                # Sample memory every 10 cycles
                                                # REMOVED_SYNTAX_ERROR: if cycle % 10 == 0:
                                                    # REMOVED_SYNTAX_ERROR: memory_profiler.sample_memory()

                                                    # Final cleanup and measurement
                                                    # REMOVED_SYNTAX_ERROR: await manager.cleanup_stale_connections()
                                                    # REMOVED_SYNTAX_ERROR: gc.collect()

                                                    # REMOVED_SYNTAX_ERROR: memory_growth = memory_profiler.get_memory_growth()

                                                    # Check for resource leaks
                                                    # REMOVED_SYNTAX_ERROR: total_connections = len(manager.connections)
                                                    # REMOVED_SYNTAX_ERROR: total_user_mappings = sum(len(conns) for conns in manager.user_connections.values())

                                                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string" )
                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                    # REMOVED_SYNTAX_ERROR: "formatted_string")

                                                    # These should FAIL with current implementation
                                                    # REMOVED_SYNTAX_ERROR: assert total_connections == 0, \
                                                    # REMOVED_SYNTAX_ERROR: "No connections should remain after rapid cycles"
                                                    # REMOVED_SYNTAX_ERROR: assert total_user_mappings == 0, \
                                                    # REMOVED_SYNTAX_ERROR: "No user connection mappings should remain"
                                                    # REMOVED_SYNTAX_ERROR: assert memory_growth < 15.0, \
                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestResourceCleanup:
    # REMOVED_SYNTAX_ERROR: """Test proper cleanup of all tracking dictionaries."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_comprehensive_dictionary_cleanup(self, manager, mock_websockets):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test that all tracking dictionaries are properly cleaned up.
        # REMOVED_SYNTAX_ERROR: SHOULD FAIL: Current implementation may not clean all dictionaries properly.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # Create connections with various associations
        # REMOVED_SYNTAX_ERROR: test_data = []

        # Create users with connections, rooms, and run_ids
        # REMOVED_SYNTAX_ERROR: for i in range(20):
            # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
            # REMOVED_SYNTAX_ERROR: room_id = "formatted_string"  # 5 different rooms
            # REMOVED_SYNTAX_ERROR: run_id = "formatted_string"

            # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(3)
            # REMOVED_SYNTAX_ERROR: for j, websocket in enumerate(websockets):
                # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket, "formatted_string")

                # Associate run_id
                # REMOVED_SYNTAX_ERROR: await manager.associate_run_id(conn_id, run_id)

                # Join room
                # REMOVED_SYNTAX_ERROR: manager.join_room(user_id, room_id)

                # REMOVED_SYNTAX_ERROR: test_data.append({ ))
                # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                # REMOVED_SYNTAX_ERROR: 'conn_id': conn_id,
                # REMOVED_SYNTAX_ERROR: 'websocket': websocket,
                # REMOVED_SYNTAX_ERROR: 'room_id': room_id,
                # REMOVED_SYNTAX_ERROR: 'run_id': run_id
                

                # Verify data structures are populated
                # REMOVED_SYNTAX_ERROR: assert len(manager.connections) > 0
                # REMOVED_SYNTAX_ERROR: assert len(manager.user_connections) > 0
                # REMOVED_SYNTAX_ERROR: assert len(manager.room_memberships) > 0
                # REMOVED_SYNTAX_ERROR: assert len(manager.run_id_connections) > 0

                # REMOVED_SYNTAX_ERROR: initial_stats = { )
                # REMOVED_SYNTAX_ERROR: 'connections': len(manager.connections),
                # REMOVED_SYNTAX_ERROR: 'user_connections': len(manager.user_connections),
                # REMOVED_SYNTAX_ERROR: 'room_memberships': len(manager.room_memberships),
                # REMOVED_SYNTAX_ERROR: 'run_id_connections': len(manager.run_id_connections)
                

                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                # Disconnect all connections
                # REMOVED_SYNTAX_ERROR: for data in test_data:
                    # REMOVED_SYNTAX_ERROR: await manager.disconnect_user(data['user_id'], data['websocket'])

                    # Force cleanup
                    # REMOVED_SYNTAX_ERROR: await manager.cleanup_stale_connections()

                    # REMOVED_SYNTAX_ERROR: final_stats = { )
                    # REMOVED_SYNTAX_ERROR: 'connections': len(manager.connections),
                    # REMOVED_SYNTAX_ERROR: 'user_connections': len(manager.user_connections),
                    # REMOVED_SYNTAX_ERROR: 'room_memberships': len(manager.room_memberships),
                    # REMOVED_SYNTAX_ERROR: 'run_id_connections': len(manager.run_id_connections)
                    

                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                    # All dictionaries should be empty or contain only empty collections
                    # REMOVED_SYNTAX_ERROR: assert len(manager.connections) == 0, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # Check that user_connections contains no non-empty sets
                    # REMOVED_SYNTAX_ERROR: non_empty_user_connections = sum(1 for conns in manager.user_connections.values() if conns)
                    # REMOVED_SYNTAX_ERROR: assert non_empty_user_connections == 0, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # Check that room_memberships contains no non-empty sets
                    # REMOVED_SYNTAX_ERROR: non_empty_rooms = sum(1 for room_conns in manager.room_memberships.values() if room_conns)
                    # REMOVED_SYNTAX_ERROR: assert non_empty_rooms == 0, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # Check that run_id_connections contains no non-empty sets
                    # REMOVED_SYNTAX_ERROR: non_empty_runs = sum(1 for run_conns in manager.run_id_connections.values() if run_conns)
                    # REMOVED_SYNTAX_ERROR: assert non_empty_runs == 0, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_partial_cleanup_on_connection_failure(self, manager, mock_websockets):
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: Test cleanup when connections fail partially through the process.
                        # REMOVED_SYNTAX_ERROR: SHOULD FAIL: Current implementation may leave partial state.
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: user_id = "partial_cleanup_user"
                        # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(5)
                        # REMOVED_SYNTAX_ERROR: successful_connections = []

                        # Connect some WebSockets
                        # REMOVED_SYNTAX_ERROR: for i, websocket in enumerate(websockets[:3]):
                            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)
                            # REMOVED_SYNTAX_ERROR: successful_connections.append((conn_id, websocket))
                            # REMOVED_SYNTAX_ERROR: await manager.associate_run_id(conn_id, "formatted_string")
                            # REMOVED_SYNTAX_ERROR: manager.join_room(user_id, "formatted_string")

                            # Simulate connection failure by manually corrupting connection data
                            # REMOVED_SYNTAX_ERROR: corrupted_conn_id = successful_connections[1][0]
                            # REMOVED_SYNTAX_ERROR: if corrupted_conn_id in manager.connections:
                                # Corrupt the connection by removing websocket reference
                                # REMOVED_SYNTAX_ERROR: manager.connections[corrupted_conn_id]["websocket"] = None

                                # Try to disconnect all connections
                                # REMOVED_SYNTAX_ERROR: cleanup_errors = 0
                                # REMOVED_SYNTAX_ERROR: for conn_id, websocket in successful_connections:
                                    # REMOVED_SYNTAX_ERROR: try:
                                        # REMOVED_SYNTAX_ERROR: await manager.disconnect_user(user_id, websocket)
                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                            # REMOVED_SYNTAX_ERROR: cleanup_errors += 1
                                            # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                                            # Force comprehensive cleanup
                                            # REMOVED_SYNTAX_ERROR: await manager.cleanup_stale_connections()

                                            # Verify complete cleanup despite partial failures
                                            # REMOVED_SYNTAX_ERROR: remaining_connections = len(manager.connections)
                                            # REMOVED_SYNTAX_ERROR: remaining_user_conns = len(manager.user_connections.get(user_id, set()))
                                            # REMOVED_SYNTAX_ERROR: remaining_in_rooms = sum(1 for room_conns in manager.room_memberships.values() )
                                            # REMOVED_SYNTAX_ERROR: for conn in room_conns
                                            # REMOVED_SYNTAX_ERROR: if conn in [c[0] for c in successful_connections])

                                            # REMOVED_SYNTAX_ERROR: assert remaining_connections == 0, \
                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                            # REMOVED_SYNTAX_ERROR: assert remaining_user_conns == 0, \
                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                            # REMOVED_SYNTAX_ERROR: assert remaining_in_rooms == 0, \
                                            # REMOVED_SYNTAX_ERROR: "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestStressAndEdgeCases:
    # REMOVED_SYNTAX_ERROR: """Stress tests and edge cases for memory leak detection."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_concurrent_connection_operations(self, manager, mock_websockets, memory_profiler):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test concurrent connection operations for race conditions and memory leaks.
        # REMOVED_SYNTAX_ERROR: SHOULD DETECT: Race conditions causing incomplete cleanup.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: memory_profiler.start_profiling()

# REMOVED_SYNTAX_ERROR: async def connect_disconnect_user(user_id: str, connection_count: int):
    # REMOVED_SYNTAX_ERROR: """Helper to connect and disconnect user concurrently."""
    # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(connection_count)
    # REMOVED_SYNTAX_ERROR: connections = []

    # Connect
    # REMOVED_SYNTAX_ERROR: for websocket in websockets:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("formatted_string", websocket)
            # REMOVED_SYNTAX_ERROR: connections.append((conn_id, websocket))
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                # Small delay to simulate activity
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                # Disconnect
                # REMOVED_SYNTAX_ERROR: for conn_id, websocket in connections:
                    # REMOVED_SYNTAX_ERROR: try:
                        # REMOVED_SYNTAX_ERROR: await manager.disconnect_user("formatted_string", websocket)
                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                            # Run concurrent operations
                            # REMOVED_SYNTAX_ERROR: tasks = []
                            # REMOVED_SYNTAX_ERROR: for i in range(50):  # 50 concurrent user operations
                            # REMOVED_SYNTAX_ERROR: task = connect_disconnect_user("formatted_string", 3)
                            # REMOVED_SYNTAX_ERROR: tasks.append(task)

                            # Execute all tasks concurrently
                            # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks, return_exceptions=True)

                            # Cleanup and measure
                            # REMOVED_SYNTAX_ERROR: await manager.cleanup_stale_connections()
                            # REMOVED_SYNTAX_ERROR: memory_growth = memory_profiler.get_memory_growth()

                            # Check for race condition artifacts
                            # REMOVED_SYNTAX_ERROR: total_connections = len(manager.connections)
                            # REMOVED_SYNTAX_ERROR: orphaned_user_connections = sum(len(conns) for conns in manager.user_connections.values())

                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string" )
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: "formatted_string")

                            # REMOVED_SYNTAX_ERROR: assert total_connections == 0, \
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: assert orphaned_user_connections == 0, \
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: assert memory_growth < 25.0, \
                            # REMOVED_SYNTAX_ERROR: "formatted_string"

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_websocket_state_inconsistencies(self, manager, mock_websockets):
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: pass
                                # REMOVED_SYNTAX_ERROR: Test handling of WebSocket state inconsistencies.
                                # REMOVED_SYNTAX_ERROR: SHOULD DETECT: Improper handling of disconnected WebSockets.
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: user_id = "state_test_user"
                                # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(5)

                                # REMOVED_SYNTAX_ERROR: connections = []
                                # REMOVED_SYNTAX_ERROR: for websocket in websockets:
                                    # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)
                                    # REMOVED_SYNTAX_ERROR: connections.append((conn_id, websocket))

                                    # Manually corrupt WebSocket states to simulate inconsistencies
                                    # REMOVED_SYNTAX_ERROR: for i, (conn_id, websocket) in enumerate(connections):
                                        # REMOVED_SYNTAX_ERROR: if i % 2 == 0:  # Every other connection
                                        # Simulate WebSocket being closed externally
                                        # REMOVED_SYNTAX_ERROR: websocket.state = WebSocketState.DISCONNECTED
                                        # REMOVED_SYNTAX_ERROR: websocket.closed = True

                                        # Try to send messages - should detect and cleanup broken connections
                                        # REMOVED_SYNTAX_ERROR: message = {"type": "test", "data": "state_test"}
                                        # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, message)

                                        # Manual cleanup
                                        # REMOVED_SYNTAX_ERROR: cleaned = await manager.cleanup_stale_connections()

                                        # Should have cleaned up disconnected WebSockets
                                        # REMOVED_SYNTAX_ERROR: remaining_connections = len(manager.connections)
                                        # REMOVED_SYNTAX_ERROR: expected_remaining = 3  # 5 total - 2 corrupted = 3

                                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string" )
                                        # REMOVED_SYNTAX_ERROR: "formatted_string")

                                        # Current implementation may not properly detect WebSocket state inconsistencies
                                        # REMOVED_SYNTAX_ERROR: assert remaining_connections <= expected_remaining, \
                                        # REMOVED_SYNTAX_ERROR: "formatted_string"

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_extreme_load_memory_behavior(self, manager, mock_websockets, memory_profiler):
                                            # REMOVED_SYNTAX_ERROR: '''
                                            # REMOVED_SYNTAX_ERROR: Test memory behavior under extreme load conditions.
                                            # REMOVED_SYNTAX_ERROR: SHOULD DETECT: System behavior approaching memory limits.
                                            # REMOVED_SYNTAX_ERROR: '''
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: memory_profiler.start_profiling()

                                            # Create extreme load - many users, many connections each
                                            # REMOVED_SYNTAX_ERROR: users_count = 200
                                            # REMOVED_SYNTAX_ERROR: connections_per_user = 5
                                            # REMOVED_SYNTAX_ERROR: total_expected = users_count * connections_per_user

                                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                            # REMOVED_SYNTAX_ERROR: all_connections = []
                                            # REMOVED_SYNTAX_ERROR: for user_num in range(users_count):
                                                # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                                                # REMOVED_SYNTAX_ERROR: websockets = mock_websockets(connections_per_user)

                                                # REMOVED_SYNTAX_ERROR: user_connections = []
                                                # REMOVED_SYNTAX_ERROR: for websocket in websockets:
                                                    # REMOVED_SYNTAX_ERROR: try:
                                                        # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket)
                                                        # REMOVED_SYNTAX_ERROR: user_connections.append((user_id, conn_id, websocket))
                                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                            # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                                                            # REMOVED_SYNTAX_ERROR: all_connections.extend(user_connections)

                                                            # Sample memory periodically
                                                            # REMOVED_SYNTAX_ERROR: if user_num % 50 == 0:
                                                                # REMOVED_SYNTAX_ERROR: current_memory = memory_profiler.sample_memory()
                                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string" )
                                                                # REMOVED_SYNTAX_ERROR: "formatted_string")

                                                                # REMOVED_SYNTAX_ERROR: peak_connections = len(manager.connections)
                                                                # REMOVED_SYNTAX_ERROR: peak_memory = memory_profiler.peak_memory

                                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                                                # Cleanup phase
                                                                # REMOVED_SYNTAX_ERROR: for user_id, conn_id, websocket in all_connections:
                                                                    # REMOVED_SYNTAX_ERROR: try:
                                                                        # REMOVED_SYNTAX_ERROR: await manager.disconnect_user(user_id, websocket)
                                                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                            # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                                                                            # REMOVED_SYNTAX_ERROR: await manager.cleanup_stale_connections()
                                                                            # REMOVED_SYNTAX_ERROR: final_memory_growth = memory_profiler.get_memory_growth()

                                                                            # Verify cleanup was effective
                                                                            # REMOVED_SYNTAX_ERROR: final_connections = len(manager.connections)
                                                                            # REMOVED_SYNTAX_ERROR: final_user_connections = sum(len(conns) for conns in manager.user_connections.values())

                                                                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string" )
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string")

                                                                            # These assertions should help identify memory leak issues
                                                                            # REMOVED_SYNTAX_ERROR: assert final_connections == 0, \
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                            # REMOVED_SYNTAX_ERROR: assert final_user_connections == 0, \
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                            # Memory growth threshold for extreme load
                                                                            # REMOVED_SYNTAX_ERROR: acceptable_growth = 50.0  # 50 MB seems reasonable for this scale
                                                                            # REMOVED_SYNTAX_ERROR: assert final_memory_growth < acceptable_growth, \
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"


                                                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                                # Allow running individual test classes for focused debugging
                                                                                # REMOVED_SYNTAX_ERROR: import sys

                                                                                # REMOVED_SYNTAX_ERROR: logging.basicConfig(level=logging.INFO)

                                                                                # REMOVED_SYNTAX_ERROR: if len(sys.argv) > 1:
                                                                                    # REMOVED_SYNTAX_ERROR: test_class = sys.argv[1]
                                                                                    # REMOVED_SYNTAX_ERROR: if test_class == "limits":
                                                                                        # REMOVED_SYNTAX_ERROR: pytest.main(["-v", "test_websocket_memory_leaks.py::TestConnectionLimits"])
                                                                                        # REMOVED_SYNTAX_ERROR: elif test_class == "ttl":
                                                                                            # REMOVED_SYNTAX_ERROR: pytest.main(["-v", "test_websocket_memory_leaks.py::TestTTLCacheExpiration"])
                                                                                            # REMOVED_SYNTAX_ERROR: elif test_class == "memory":
                                                                                                # REMOVED_SYNTAX_ERROR: pytest.main(["-v", "test_websocket_memory_leaks.py::TestMemoryLeakDetection"])
                                                                                                # REMOVED_SYNTAX_ERROR: elif test_class == "cleanup":
                                                                                                    # REMOVED_SYNTAX_ERROR: pytest.main(["-v", "test_websocket_memory_leaks.py::TestResourceCleanup"])
                                                                                                    # REMOVED_SYNTAX_ERROR: elif test_class == "stress":
                                                                                                        # REMOVED_SYNTAX_ERROR: pytest.main(["-v", "test_websocket_memory_leaks.py::TestStressAndEdgeCases"])
                                                                                                        # REMOVED_SYNTAX_ERROR: else:
                                                                                                            # REMOVED_SYNTAX_ERROR: pytest.main(["-v", "test_websocket_memory_leaks.py"])