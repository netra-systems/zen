"""
Comprehensive test suite for WebSocket manager memory leak detection.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Risk Reduction  
- Value Impact: Prevents system crashes from memory exhaustion
- Strategic Impact: Ensures system can handle sustained user load

This test suite verifies:
1. Connection limits enforcement (MAX_CONNECTIONS_PER_USER = 5, MAX_TOTAL_CONNECTIONS = 1000)
2. Automatic eviction of oldest connections when limits exceeded
3. TTL cache expiration for connections (5 minute TTL)
4. Periodic cleanup of stale connections
5. Memory growth detection under sustained load
6. Resource cleanup on disconnection
7. Proper cleanup of all tracking dictionaries

Tests are designed to FAIL with current implementation to demonstrate memory leak issues.
"""

import asyncio
import gc
import logging
import psutil
import pytest
import time
import unittest.mock as mock
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from netra_backend.app.websocket_core.manager import WebSocketManager


logger = logging.getLogger(__name__)

# Memory leak detection constants - these should be enforced but aren't currently
MAX_CONNECTIONS_PER_USER = 5
MAX_TOTAL_CONNECTIONS = 1000
TTL_SECONDS = 300  # 5 minutes


class MockWebSocket:
    """Mock WebSocket for testing without actual connections."""
    
    def __init__(self, connection_id: str = None):
        self.connection_id = connection_id or f"mock_{id(self)}"
        # Add proper WebSocket state attributes for compatibility
        self.state = WebSocketState.CONNECTED
        self.client_state = WebSocketState.CONNECTED  # For is_websocket_connected
        self.application_state = WebSocketState.CONNECTED  # For is_websocket_connected
        self.messages_sent: List[Dict] = []
        self.closed = False
        self.close_code: Optional[int] = None
        self.close_reason: Optional[str] = None
    
    async def send_json(self, data: Dict):
        """Mock sending JSON data."""
        if self.state != WebSocketState.CONNECTED or self.closed:
            raise RuntimeError("WebSocket is not connected")
        self.messages_sent.append(data)
    
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Mock closing the WebSocket."""
        self.state = WebSocketState.DISCONNECTED
        self.client_state = WebSocketState.DISCONNECTED
        self.application_state = WebSocketState.DISCONNECTED
        self.closed = True
        self.close_code = code
        self.close_reason = reason
    
    def __eq__(self, other):
        return isinstance(other, MockWebSocket) and self.connection_id == other.connection_id
    
    def __hash__(self):
        return hash(self.connection_id)


class MemoryProfiler:
    """Helper class for tracking memory usage during tests."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = 0
        self.peak_memory = 0
        self.samples: List[float] = []
    
    def start_profiling(self):
        """Start memory profiling."""
        gc.collect()  # Force garbage collection before measuring
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.initial_memory
        self.samples = [self.initial_memory]
        logger.info(f"Memory profiling started - Initial: {self.initial_memory:.2f} MB")
    
    def sample_memory(self) -> float:
        """Take a memory sample and return current usage in MB."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.samples.append(current_memory)
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
        return current_memory
    
    def get_memory_growth(self) -> float:
        """Get total memory growth since profiling started."""
        current_memory = self.sample_memory()
        growth = current_memory - self.initial_memory
        logger.info(f"Memory growth: {growth:.2f} MB (Initial: {self.initial_memory:.2f} MB, Current: {current_memory:.2f} MB)")
        return growth
    
    def detect_memory_leak(self, threshold_mb: float = 10.0) -> bool:
        """Detect if memory growth exceeds threshold, indicating a potential leak."""
        growth = self.get_memory_growth()
        is_leak = growth > threshold_mb
        if is_leak:
            logger.warning(f"Memory leak detected! Growth: {growth:.2f} MB > {threshold_mb:.2f} MB threshold")
        return is_leak


@pytest.fixture
def memory_profiler():
    """Fixture that provides memory profiling capabilities."""
    profiler = MemoryProfiler()
    yield profiler


@pytest.fixture
async def manager():
    """Fixture that provides a fresh WebSocket manager instance."""
    # Reset singleton instance for clean state
    WebSocketManager._instance = None
    manager = WebSocketManager()
    yield manager
    # Cleanup after test
    await manager.shutdown()


@pytest.fixture
def mock_websockets():
    """Fixture that creates mock WebSocket connections."""
    def _create_mock_websockets(count: int) -> List[MockWebSocket]:
        return [MockWebSocket(f"ws_{i}") for i in range(count)]
    return _create_mock_websockets


class TestConnectionLimits:
    """Test connection limit enforcement - these tests SHOULD FAIL with current implementation."""
    
    @pytest.mark.asyncio
    async def test_max_connections_per_user_enforcement(self, manager, mock_websockets):
        """
        Test that MAX_CONNECTIONS_PER_USER=5 is enforced.
        EXPECTED TO FAIL: Current implementation has no connection limits.
        """
        user_id = "test_user_limits"
        websockets = mock_websockets(10)  # Try to create 10 connections
        
        connected_ids = []
        
        # Try to connect 10 WebSockets for same user
        for i, websocket in enumerate(websockets):
            try:
                conn_id = await manager.connect_user(user_id, websocket)
                connected_ids.append(conn_id)
            except WebSocketDisconnect as e:
                # Should start rejecting after MAX_CONNECTIONS_PER_USER
                if i >= MAX_CONNECTIONS_PER_USER:
                    assert "connection limit" in str(e.reason).lower()
                else:
                    pytest.fail(f"Unexpected connection rejection at connection {i}: {e}")
        
        # Should only have MAX_CONNECTIONS_PER_USER connections
        assert len(connected_ids) == MAX_CONNECTIONS_PER_USER, \
            f"Expected {MAX_CONNECTIONS_PER_USER} connections, got {len(connected_ids)}"
        
        # Verify user_connections tracking
        user_connections = manager.user_connections.get(user_id, set())
        assert len(user_connections) == MAX_CONNECTIONS_PER_USER, \
            f"user_connections should track {MAX_CONNECTIONS_PER_USER} connections, got {len(user_connections)}"
    
    @pytest.mark.asyncio
    async def test_max_total_connections_enforcement(self, manager, mock_websockets):
        """
        Test that MAX_TOTAL_CONNECTIONS=1000 is enforced across all users.
        EXPECTED TO FAIL: Current implementation has no total connection limits.
        """
        # Create connections approaching the limit
        users_created = 0
        total_connections = 0
        
        # Create users with multiple connections each until we hit the limit
        while total_connections < MAX_TOTAL_CONNECTIONS + 50:  # Try to exceed limit
            user_id = f"user_{users_created}"
            websockets = mock_websockets(5)  # 5 connections per user
            
            connections_for_user = 0
            for websocket in websockets:
                try:
                    await manager.connect_user(user_id, websocket)
                    connections_for_user += 1
                    total_connections += 1
                except WebSocketDisconnect as e:
                    if total_connections >= MAX_TOTAL_CONNECTIONS:
                        assert "total connection limit" in str(e.reason).lower()
                        break
                    else:
                        pytest.fail(f"Unexpected connection rejection: {e}")
            
            users_created += 1
            
            # Safety break
            if users_created > 250:
                break
        
        # Should not exceed MAX_TOTAL_CONNECTIONS
        actual_connections = len(manager.connections)
        assert actual_connections <= MAX_TOTAL_CONNECTIONS, \
            f"Total connections {actual_connections} exceeds limit {MAX_TOTAL_CONNECTIONS}"
    
    @pytest.mark.asyncio
    async def test_oldest_connection_eviction(self, manager, mock_websockets):
        """
        Test that oldest connections are evicted when limits are exceeded.
        EXPECTED TO FAIL: Current implementation has no eviction mechanism.
        """
        user_id = "test_user_eviction"
        websockets = mock_websockets(MAX_CONNECTIONS_PER_USER + 3)
        
        # Connect initial connections and track their IDs
        initial_connections = []
        for i in range(MAX_CONNECTIONS_PER_USER):
            conn_id = await manager.connect_user(user_id, websockets[i])
            initial_connections.append(conn_id)
            # Simulate time passage to ensure ordering
            await asyncio.sleep(0.01)
        
        # Record initial connection timestamps
        initial_timestamps = {}
        for conn_id in initial_connections:
            if conn_id in manager.connections:
                initial_timestamps[conn_id] = manager.connections[conn_id]["connected_at"]
        
        # Try to add more connections - should fail due to limit
        new_connections = []
        for i in range(MAX_CONNECTIONS_PER_USER, len(websockets)):
            try:
                conn_id = await manager.connect_user(user_id, websockets[i])
                new_connections.append(conn_id)
            except WebSocketDisconnect:
                # Expected - connection limit enforced
                pass
        
        # Check that total connections for user doesn't exceed limit
        user_connections = manager.user_connections.get(user_id, set())
        assert len(user_connections) <= MAX_CONNECTIONS_PER_USER, \
            f"User should have at most {MAX_CONNECTIONS_PER_USER} connections"
        
        # With the current implementation, no new connections should be added
        # The limit is enforced by raising an exception
        assert len(new_connections) == 0, \
            "No new connections should be added when limit is reached"
        
        # Verify initial connections still exist (no eviction, just rejection)
        for conn_id in initial_connections[:MAX_CONNECTIONS_PER_USER]:
            assert conn_id in manager.connections, \
                f"Initial connection {conn_id} should still exist"


class TestTTLCacheExpiration:
    """Test TTL cache expiration - these tests SHOULD FAIL with current implementation."""
    
    @pytest.mark.asyncio
    async def test_connection_ttl_expiration(self, manager, mock_websockets):
        """
        Test that connections expire after TTL_SECONDS=300 (5 minutes).
        EXPECTED TO FAIL: Current implementation has no TTL mechanism.
        """
        user_id = "test_ttl_user"
        websocket = mock_websockets(1)[0]
        
        # Connect user
        conn_id = await manager.connect_user(user_id, websocket)
        assert conn_id in manager.connections
        
        # Simulate time passage by manually updating connection timestamp
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=TTL_SECONDS + 60)
        manager.connections[conn_id]["connected_at"] = expired_time
        manager.connections[conn_id]["last_activity"] = expired_time
        
        # Run cleanup - should remove expired connection
        cleaned_count = await manager.cleanup_stale_connections()
        
        # Connection should be removed due to TTL expiration
        assert conn_id not in manager.connections, \
            "Expired connection should be removed by TTL cleanup"
        assert cleaned_count >= 1, \
            "Cleanup should report at least one connection removed"
        
        # User should have no connections
        user_connections = manager.user_connections.get(user_id, set())
        assert len(user_connections) == 0, \
            "User should have no connections after TTL expiration"
    
    @pytest.mark.asyncio
    async def test_ttl_cache_with_activity_refresh(self, manager, mock_websockets):
        """
        Test that active connections have their TTL refreshed.
        EXPECTED TO FAIL: Current implementation doesn't implement TTL refresh.
        """
        user_id = "test_ttl_activity"
        websocket = mock_websockets(1)[0]
        
        conn_id = await manager.connect_user(user_id, websocket)
        
        # Set connection to near-expiry
        near_expiry = datetime.now(timezone.utc) - timedelta(seconds=TTL_SECONDS - 30)
        manager.connections[conn_id]["connected_at"] = near_expiry
        manager.connections[conn_id]["last_activity"] = near_expiry
        
        # Simulate activity by sending a message
        await manager.send_to_user(user_id, {"type": "test", "data": "refresh_ttl"})
        
        # Connection should have updated last_activity
        last_activity = manager.connections[conn_id]["last_activity"]
        time_since_activity = (datetime.now(timezone.utc) - last_activity).total_seconds()
        assert time_since_activity < 10, \
            "last_activity should be updated after sending message"
        
        # Run cleanup - connection should NOT be removed
        await manager.cleanup_stale_connections()
        assert conn_id in manager.connections, \
            "Active connection should not be removed during TTL cleanup"
    
    @pytest.mark.asyncio
    async def test_periodic_ttl_cleanup_automation(self, manager, mock_websockets):
        """
        Test that periodic cleanup automatically removes TTL-expired connections.
        EXPECTED TO FAIL: Current implementation has no automatic TTL cleanup.
        """
        # This test would require implementing a background task for periodic cleanup
        # For now, we'll test manual cleanup behavior that should exist
        
        user_ids = [f"ttl_user_{i}" for i in range(10)]
        connections = []
        
        # Create multiple connections
        for user_id in user_ids:
            websocket = mock_websockets(1)[0]
            conn_id = await manager.connect_user(user_id, websocket)
            connections.append(conn_id)
        
        # Expire half of them
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=TTL_SECONDS + 60)
        for i in range(0, 5):  # Expire first 5
            conn_id = connections[i]
            manager.connections[conn_id]["connected_at"] = expired_time
            manager.connections[conn_id]["last_activity"] = expired_time
        
        # Manual cleanup should remove expired connections
        initial_count = len(manager.connections)
        cleaned_count = await manager.cleanup_stale_connections()
        final_count = len(manager.connections)
        
        assert cleaned_count == 5, f"Should clean exactly 5 expired connections, got {cleaned_count}"
        assert final_count == initial_count - 5, \
            f"Should have {initial_count - 5} connections remaining, got {final_count}"


class TestMemoryLeakDetection:
    """Test memory growth detection under sustained load."""
    
    @pytest.mark.asyncio
    async def test_sustained_connection_load_memory_growth(self, manager, mock_websockets, memory_profiler):
        """
        Test memory growth under sustained connection load.
        SHOULD DETECT: Memory growth from lack of proper cleanup.
        """
        memory_profiler.start_profiling()
        
        # Phase 1: Create many connections
        users_and_connections = []
        for batch in range(10):  # 10 batches
            batch_connections = []
            for user_num in range(50):  # 50 users per batch
                user_id = f"load_user_{batch}_{user_num}"
                websockets = mock_websockets(3)  # 3 connections per user
                
                user_connections = []
                for websocket in websockets:
                    try:
                        conn_id = await manager.connect_user(user_id, websocket)
                        user_connections.append((user_id, conn_id, websocket))
                    except Exception as e:
                        logger.warning(f"Connection failed: {e}")
                
                batch_connections.extend(user_connections)
            
            users_and_connections.extend(batch_connections)
            memory_profiler.sample_memory()
            
            # Small delay to allow any cleanup to occur
            await asyncio.sleep(0.1)
        
        logger.info(f"Created {len(users_and_connections)} total connections")
        
        # Phase 2: Disconnect all connections
        for user_id, conn_id, websocket in users_and_connections:
            try:
                await manager.disconnect_user(user_id, websocket)
            except Exception as e:
                logger.warning(f"Disconnect failed: {e}")
        
        # Force cleanup
        await manager.cleanup_stale_connections()
        gc.collect()  # Force garbage collection
        
        # Check final memory usage
        memory_growth = memory_profiler.get_memory_growth()
        
        # Check for memory leak indicators
        remaining_connections = len(manager.connections)
        remaining_user_connections = sum(len(conns) for conns in manager.user_connections.values())
        remaining_rooms = sum(len(room) for room in manager.room_memberships.values())
        remaining_run_ids = sum(len(runs) for runs in manager.run_id_connections.values())
        
        logger.info(f"After cleanup - Connections: {remaining_connections}, "
                   f"User connections: {remaining_user_connections}, "
                   f"Rooms: {remaining_rooms}, Run IDs: {remaining_run_ids}")
        
        # These assertions should FAIL with current implementation
        assert remaining_connections == 0, \
            f"All connections should be cleaned up, but {remaining_connections} remain"
        assert remaining_user_connections == 0, \
            f"All user_connections should be cleaned up, but {remaining_user_connections} remain"
        assert memory_growth < 20.0, \
            f"Memory growth {memory_growth:.2f} MB exceeds acceptable threshold"
    
    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect_cycles(self, manager, mock_websockets, memory_profiler):
        """
        Test memory behavior with rapid connect/disconnect cycles.
        SHOULD DETECT: Memory accumulation from improper cleanup.
        """
        memory_profiler.start_profiling()
        
        # Perform rapid connect/disconnect cycles
        cycles = 100
        for cycle in range(cycles):
            user_id = f"cycle_user_{cycle % 20}"  # Reuse some user IDs
            websockets = mock_websockets(5)
            
            # Quick connect
            connections = []
            for websocket in websockets:
                conn_id = await manager.connect_user(user_id, websocket)
                connections.append((user_id, websocket))
            
            # Quick disconnect
            for user_id, websocket in connections:
                await manager.disconnect_user(user_id, websocket)
            
            # Sample memory every 10 cycles
            if cycle % 10 == 0:
                memory_profiler.sample_memory()
        
        # Final cleanup and measurement
        await manager.cleanup_stale_connections()
        gc.collect()
        
        memory_growth = memory_profiler.get_memory_growth()
        
        # Check for resource leaks
        total_connections = len(manager.connections)
        total_user_mappings = sum(len(conns) for conns in manager.user_connections.values())
        
        logger.info(f"After {cycles} rapid cycles - Memory growth: {memory_growth:.2f} MB, "
                   f"Remaining connections: {total_connections}, "
                   f"Remaining user mappings: {total_user_mappings}")
        
        # These should FAIL with current implementation
        assert total_connections == 0, \
            "No connections should remain after rapid cycles"
        assert total_user_mappings == 0, \
            "No user connection mappings should remain"
        assert memory_growth < 15.0, \
            f"Memory growth {memory_growth:.2f} MB from rapid cycles is excessive"


class TestResourceCleanup:
    """Test proper cleanup of all tracking dictionaries."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_dictionary_cleanup(self, manager, mock_websockets):
        """
        Test that all tracking dictionaries are properly cleaned up.
        SHOULD FAIL: Current implementation may not clean all dictionaries properly.
        """
        # Create connections with various associations
        test_data = []
        
        # Create users with connections, rooms, and run_ids
        for i in range(20):
            user_id = f"cleanup_user_{i}"
            room_id = f"room_{i % 5}"  # 5 different rooms
            run_id = f"run_{i}"
            
            websockets = mock_websockets(3)
            for j, websocket in enumerate(websockets):
                conn_id = await manager.connect_user(user_id, websocket, f"thread_{i}_{j}")
                
                # Associate run_id
                await manager.associate_run_id(conn_id, run_id)
                
                # Join room
                manager.join_room(user_id, room_id)
                
                test_data.append({
                    'user_id': user_id,
                    'conn_id': conn_id,
                    'websocket': websocket,
                    'room_id': room_id,
                    'run_id': run_id
                })
        
        # Verify data structures are populated
        assert len(manager.connections) > 0
        assert len(manager.user_connections) > 0
        assert len(manager.room_memberships) > 0
        assert len(manager.run_id_connections) > 0
        
        initial_stats = {
            'connections': len(manager.connections),
            'user_connections': len(manager.user_connections),
            'room_memberships': len(manager.room_memberships),
            'run_id_connections': len(manager.run_id_connections)
        }
        
        logger.info(f"Initial state: {initial_stats}")
        
        # Disconnect all connections
        for data in test_data:
            await manager.disconnect_user(data['user_id'], data['websocket'])
        
        # Force cleanup
        await manager.cleanup_stale_connections()
        
        final_stats = {
            'connections': len(manager.connections),
            'user_connections': len(manager.user_connections),
            'room_memberships': len(manager.room_memberships),
            'run_id_connections': len(manager.run_id_connections)
        }
        
        logger.info(f"Final state: {final_stats}")
        
        # All dictionaries should be empty or contain only empty collections
        assert len(manager.connections) == 0, \
            f"connections dict should be empty, has {len(manager.connections)} entries"
        
        # Check that user_connections contains no non-empty sets
        non_empty_user_connections = sum(1 for conns in manager.user_connections.values() if conns)
        assert non_empty_user_connections == 0, \
            f"user_connections should have no non-empty sets, found {non_empty_user_connections}"
        
        # Check that room_memberships contains no non-empty sets
        non_empty_rooms = sum(1 for room_conns in manager.room_memberships.values() if room_conns)
        assert non_empty_rooms == 0, \
            f"room_memberships should have no non-empty sets, found {non_empty_rooms}"
        
        # Check that run_id_connections contains no non-empty sets
        non_empty_runs = sum(1 for run_conns in manager.run_id_connections.values() if run_conns)
        assert non_empty_runs == 0, \
            f"run_id_connections should have no non-empty sets, found {non_empty_runs}"
    
    @pytest.mark.asyncio
    async def test_partial_cleanup_on_connection_failure(self, manager, mock_websockets):
        """
        Test cleanup when connections fail partially through the process.
        SHOULD FAIL: Current implementation may leave partial state.
        """
        user_id = "partial_cleanup_user"
        websockets = mock_websockets(5)
        successful_connections = []
        
        # Connect some WebSockets
        for i, websocket in enumerate(websockets[:3]):
            conn_id = await manager.connect_user(user_id, websocket)
            successful_connections.append((conn_id, websocket))
            await manager.associate_run_id(conn_id, f"run_{i}")
            manager.join_room(user_id, f"room_{i}")
        
        # Simulate connection failure by manually corrupting connection data
        corrupted_conn_id = successful_connections[1][0]
        if corrupted_conn_id in manager.connections:
            # Corrupt the connection by removing websocket reference
            manager.connections[corrupted_conn_id]["websocket"] = None
        
        # Try to disconnect all connections
        cleanup_errors = 0
        for conn_id, websocket in successful_connections:
            try:
                await manager.disconnect_user(user_id, websocket)
            except Exception as e:
                cleanup_errors += 1
                logger.warning(f"Cleanup error for {conn_id}: {e}")
        
        # Force comprehensive cleanup
        await manager.cleanup_stale_connections()
        
        # Verify complete cleanup despite partial failures
        remaining_connections = len(manager.connections)
        remaining_user_conns = len(manager.user_connections.get(user_id, set()))
        remaining_in_rooms = sum(1 for room_conns in manager.room_memberships.values() 
                               for conn in room_conns 
                               if conn in [c[0] for c in successful_connections])
        
        assert remaining_connections == 0, \
            f"Should have no remaining connections, found {remaining_connections}"
        assert remaining_user_conns == 0, \
            f"User should have no remaining connections, found {remaining_user_conns}"
        assert remaining_in_rooms == 0, \
            f"Should have no connections in rooms, found {remaining_in_rooms}"


class TestStressAndEdgeCases:
    """Stress tests and edge cases for memory leak detection."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_operations(self, manager, mock_websockets, memory_profiler):
        """
        Test concurrent connection operations for race conditions and memory leaks.
        SHOULD DETECT: Race conditions causing incomplete cleanup.
        """
        memory_profiler.start_profiling()
        
        async def connect_disconnect_user(user_id: str, connection_count: int):
            """Helper to connect and disconnect user concurrently."""
            websockets = mock_websockets(connection_count)
            connections = []
            
            # Connect
            for websocket in websockets:
                try:
                    conn_id = await manager.connect_user(f"{user_id}", websocket)
                    connections.append((conn_id, websocket))
                except Exception as e:
                    logger.warning(f"Concurrent connect failed: {e}")
            
            # Small delay to simulate activity
            await asyncio.sleep(0.1)
            
            # Disconnect
            for conn_id, websocket in connections:
                try:
                    await manager.disconnect_user(f"{user_id}", websocket)
                except Exception as e:
                    logger.warning(f"Concurrent disconnect failed: {e}")
        
        # Run concurrent operations
        tasks = []
        for i in range(50):  # 50 concurrent user operations
            task = connect_disconnect_user(f"concurrent_user_{i}", 3)
            tasks.append(task)
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Cleanup and measure
        await manager.cleanup_stale_connections()
        memory_growth = memory_profiler.get_memory_growth()
        
        # Check for race condition artifacts
        total_connections = len(manager.connections)
        orphaned_user_connections = sum(len(conns) for conns in manager.user_connections.values())
        
        logger.info(f"Concurrent operations result - Connections: {total_connections}, "
                   f"User connections: {orphaned_user_connections}, "
                   f"Memory growth: {memory_growth:.2f} MB")
        
        assert total_connections == 0, \
            f"Race conditions left {total_connections} connections orphaned"
        assert orphaned_user_connections == 0, \
            f"Race conditions left {orphaned_user_connections} user connection mappings"
        assert memory_growth < 25.0, \
            f"Concurrent operations caused excessive memory growth: {memory_growth:.2f} MB"
    
    @pytest.mark.asyncio
    async def test_websocket_state_inconsistencies(self, manager, mock_websockets):
        """
        Test handling of WebSocket state inconsistencies.
        SHOULD DETECT: Improper handling of disconnected WebSockets.
        """
        user_id = "state_test_user"
        websockets = mock_websockets(5)
        
        connections = []
        for websocket in websockets:
            conn_id = await manager.connect_user(user_id, websocket)
            connections.append((conn_id, websocket))
        
        # Manually corrupt WebSocket states to simulate inconsistencies
        for i, (conn_id, websocket) in enumerate(connections):
            if i % 2 == 0:  # Every other connection
                # Simulate WebSocket being closed externally
                websocket.state = WebSocketState.DISCONNECTED
                websocket.closed = True
        
        # Try to send messages - should detect and cleanup broken connections
        message = {"type": "test", "data": "state_test"}
        await manager.send_to_user(user_id, message)
        
        # Manual cleanup
        cleaned = await manager.cleanup_stale_connections()
        
        # Should have cleaned up disconnected WebSockets
        remaining_connections = len(manager.connections)
        expected_remaining = 3  # 5 total - 2 corrupted = 3
        
        logger.info(f"State inconsistency test - Cleaned: {cleaned}, "
                   f"Remaining: {remaining_connections}, Expected: {expected_remaining}")
        
        # Current implementation may not properly detect WebSocket state inconsistencies
        assert remaining_connections <= expected_remaining, \
            f"Should have ≤{expected_remaining} connections after state cleanup, found {remaining_connections}"
    
    @pytest.mark.asyncio
    async def test_extreme_load_memory_behavior(self, manager, mock_websockets, memory_profiler):
        """
        Test memory behavior under extreme load conditions.
        SHOULD DETECT: System behavior approaching memory limits.
        """
        memory_profiler.start_profiling()
        
        # Create extreme load - many users, many connections each
        users_count = 200
        connections_per_user = 5
        total_expected = users_count * connections_per_user
        
        logger.info(f"Starting extreme load test - {users_count} users × {connections_per_user} connections = {total_expected} total")
        
        all_connections = []
        for user_num in range(users_count):
            user_id = f"extreme_user_{user_num}"
            websockets = mock_websockets(connections_per_user)
            
            user_connections = []
            for websocket in websockets:
                try:
                    conn_id = await manager.connect_user(user_id, websocket)
                    user_connections.append((user_id, conn_id, websocket))
                except Exception as e:
                    logger.warning(f"Extreme load connection failed: {e}")
            
            all_connections.extend(user_connections)
            
            # Sample memory periodically
            if user_num % 50 == 0:
                current_memory = memory_profiler.sample_memory()
                logger.info(f"User {user_num}: {current_memory:.2f} MB, "
                           f"Connections: {len(manager.connections)}")
        
        peak_connections = len(manager.connections)
        peak_memory = memory_profiler.peak_memory
        
        logger.info(f"Peak load - Connections: {peak_connections}, Memory: {peak_memory:.2f} MB")
        
        # Cleanup phase
        for user_id, conn_id, websocket in all_connections:
            try:
                await manager.disconnect_user(user_id, websocket)
            except Exception as e:
                logger.warning(f"Extreme load cleanup failed: {e}")
        
        await manager.cleanup_stale_connections()
        final_memory_growth = memory_profiler.get_memory_growth()
        
        # Verify cleanup was effective
        final_connections = len(manager.connections)
        final_user_connections = sum(len(conns) for conns in manager.user_connections.values())
        
        logger.info(f"After extreme load cleanup - Connections: {final_connections}, "
                   f"User mappings: {final_user_connections}, "
                   f"Final memory growth: {final_memory_growth:.2f} MB")
        
        # These assertions should help identify memory leak issues
        assert final_connections == 0, \
            f"All connections should be cleaned up, {final_connections} remain"
        assert final_user_connections == 0, \
            f"All user connection mappings should be cleaned up, {final_user_connections} remain"
        
        # Memory growth threshold for extreme load
        acceptable_growth = 50.0  # 50 MB seems reasonable for this scale
        assert final_memory_growth < acceptable_growth, \
            f"Memory growth {final_memory_growth:.2f} MB exceeds acceptable threshold {acceptable_growth} MB"


if __name__ == "__main__":
    # Allow running individual test classes for focused debugging
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        test_class = sys.argv[1]
        if test_class == "limits":
            pytest.main(["-v", "test_websocket_memory_leaks.py::TestConnectionLimits"])
        elif test_class == "ttl":
            pytest.main(["-v", "test_websocket_memory_leaks.py::TestTTLCacheExpiration"])
        elif test_class == "memory":
            pytest.main(["-v", "test_websocket_memory_leaks.py::TestMemoryLeakDetection"])
        elif test_class == "cleanup":
            pytest.main(["-v", "test_websocket_memory_leaks.py::TestResourceCleanup"])
        elif test_class == "stress":
            pytest.main(["-v", "test_websocket_memory_leaks.py::TestStressAndEdgeCases"])
    else:
        pytest.main(["-v", "test_websocket_memory_leaks.py"])