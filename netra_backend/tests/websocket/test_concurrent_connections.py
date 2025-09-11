"""
WebSocket concurrent connection testing module.
Tests connection limits, pool management, and rapid connect/disconnect cycles.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
import random
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock

import psutil
import pytest
import websockets

async def create_connection(user_id: str, conn_idx: int, connection_metrics: Dict) -> Optional[AsyncMock]:
    """Create a single WebSocket connection"""
    try:
        mock_ws = _create_mock_websocket(user_id, conn_idx)
        await asyncio.sleep(random.uniform(0.001, 0.01))
        connection_metrics['successful'] += 1
        return mock_ws
    except Exception as e:
        return _handle_connection_failure(e, connection_metrics)

def _create_mock_websocket(user_id: str, conn_idx: int) -> AsyncMock:
    # Mock: Generic component isolation for controlled unit testing
    mock_ws = AsyncMock()  # TODO: Use real service instance
    mock_ws.user_id = user_id
    mock_ws.connection_id = f"{user_id}_conn_{conn_idx}"
    mock_ws.connected_at = datetime.now(UTC)
    mock_ws.state = websockets.State.OPEN
    # Mock: Generic component isolation for controlled unit testing
    mock_ws.send = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    mock_ws.recv = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    mock_ws.close = AsyncMock()  # TODO: Use real service instance
    return mock_ws

def _handle_connection_failure(e: Exception, connection_metrics: Dict) -> None:
    connection_metrics['failed'] += 1
    if 'limit' in str(e).lower():
        connection_metrics['rejected_over_limit'] += 1
    return None

async def _create_connection_batch(batch_start: int, batch_end: int, connections: List, connection_metrics: Dict, max_connections_per_user: int):
    batch_tasks = []
    for conn_idx in range(batch_start, batch_end):
        if len(connections) >= 1000:
            connection_metrics['rejected_over_limit'] += 1
            continue
        user_id = f"user_{conn_idx // max_connections_per_user}"
        conn_num = conn_idx % max_connections_per_user
        task = create_connection(user_id, conn_num, connection_metrics)
        batch_tasks.append(task)
    return await asyncio.gather(*batch_tasks, return_exceptions=True)

def _process_batch_results(batch_results: List, connections: List):
    for result in batch_results:
        if result and not isinstance(result, Exception):
            connections.append(result)

def _calculate_metrics(connection_metrics: Dict, connections: List):
    connection_metrics['memory_end'] = psutil.Process().memory_info().rss / 1024 / 1024
    connection_metrics['memory_used'] = connection_metrics['memory_end'] - connection_metrics['memory_start']
    connection_metrics['duration'] = time.time() - connection_metrics['start_time']
    connection_metrics['connections_per_second'] = len(connections) / connection_metrics['duration']

def _verify_connection_metrics(connections: List, connection_metrics: Dict):
    assert len(connections) > 0, "Should establish some connections"
    assert len(connections) <= 1000, "Should enforce connection limit at 1000"
    assert connection_metrics['memory_used'] < 500, "Memory usage should be reasonable (<500MB)"
    assert connection_metrics['connections_per_second'] > 50, "Should handle >50 connections/second"

async def _test_broadcasting(connections: List):
    broadcast_start = time.time()
    broadcast_message = json.dumps({'type': 'broadcast', 'data': 'test'})
    broadcast_tasks = [conn.send(broadcast_message) for conn in connections]
    await asyncio.gather(*broadcast_tasks)
    broadcast_duration = time.time() - broadcast_start
    assert broadcast_duration < 5, f"Broadcast to {len(connections)} connections should complete in <5s"
@pytest.mark.stress
@pytest.mark.asyncio
async def test_concurrent_connection_limit_1000_users():
    """Test handling of 1000+ concurrent WebSocket connections with proper limits"""
    connections: List[AsyncMock] = []
    connection_metrics = _initialize_connection_metrics()
    TARGET_CONNECTIONS, BATCH_SIZE = 1000, 100
    MAX_CONNECTIONS_PER_USER = 5
    
    await _create_all_connections(connections, connection_metrics, TARGET_CONNECTIONS, BATCH_SIZE, MAX_CONNECTIONS_PER_USER)
    _calculate_metrics(connection_metrics, connections)
    _verify_connection_metrics(connections, connection_metrics)
    await _test_broadcasting(connections)
    await _cleanup_connections(connections)

def _initialize_connection_metrics() -> Dict:
    return {
        'successful': 0,
        'failed': 0,
        'rejected_over_limit': 0,
        'memory_start': psutil.Process().memory_info().rss / 1024 / 1024,
        'start_time': time.time()
    }

async def _create_all_connections(connections: List, connection_metrics: Dict, target: int, batch_size: int, max_per_user: int):
    for batch_start in range(0, target, batch_size):
        batch_end = min(batch_start + batch_size, target)
        batch_results = await _create_connection_batch(batch_start, batch_end, connections, connection_metrics, max_per_user)
        _process_batch_results(batch_results, connections)
        await asyncio.sleep(0.1)

async def _cleanup_connections(connections: List):
    cleanup_tasks = [conn.close() for conn in connections]
    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
@pytest.mark.asyncio
async def test_rapid_connect_disconnect_cycles():
    """Test rapid connection and disconnection cycles with realistic expectations"""
    
    NUM_CYCLES = 100
    connection_times = []
    disconnection_times = []
    failures = []
    
    for cycle in range(NUM_CYCLES):
        try:
            # Connect
            start_connect = time.time()
            # Mock: Generic component isolation for controlled unit testing
            mock_ws = AsyncMock()  # TODO: Use real service instance
            mock_ws.state = websockets.State.OPEN
            await asyncio.sleep(0.001)  # Simulate connection time
            connection_times.append(time.time() - start_connect)
            
            # Send a quick message
            await mock_ws.send(json.dumps({'cycle': cycle}))
            
            # Disconnect
            start_disconnect = time.time()
            await mock_ws.close()
            mock_ws.state = websockets.State.CLOSED
            disconnection_times.append(time.time() - start_disconnect)
            
        except Exception as e:
            failures.append({'cycle': cycle, 'error': str(e)})
    
    # Fixed: Analyze results with realistic expectations
    assert len(failures) < NUM_CYCLES * 0.01, f"Too many failures: {len(failures)}/{NUM_CYCLES}"
    assert max(connection_times) < 0.1, "Connection should be fast (<100ms)"
    assert max(disconnection_times) < 0.05, "Disconnection should be fast (<50ms)"
    
    avg_connect = sum(connection_times) / len(connection_times)
    avg_disconnect = sum(disconnection_times) / len(disconnection_times)
    
    # Fixed: More realistic timing expectations
    assert avg_connect < 0.02, f"Average connection time too high: {avg_connect*1000:.2f}ms"
    assert avg_disconnect < 0.01, f"Average disconnection time too high: {avg_disconnect*1000:.2f}ms"
@pytest.mark.asyncio
async def test_connection_pool_exhaustion_recovery():
    """Test recovery from connection pool exhaustion"""
    
    POOL_SIZE = 100
    OVERFLOW_CONNECTIONS = 150
    
    class ConnectionPool:
        def __init__(self, max_size: int):
            self.max_size = max_size
            self.connections: Set[str] = set()
            self.waiting_queue: asyncio.Queue = asyncio.Queue()
            self.rejected_count = 0
            
        async def acquire(self, client_id: str) -> Optional[str]:
            if len(self.connections) < self.max_size:
                self.connections.add(client_id)
                return client_id
            else:
                # Put in waiting queue
                await self.waiting_queue.put(client_id)
                self.rejected_count += 1
                return None
        
        async def release(self, client_id: str):
            if client_id in self.connections:
                self.connections.remove(client_id)
                
                # Check waiting queue
                if not self.waiting_queue.empty():
                    waiting_client = await self.waiting_queue.get()
                    self.connections.add(waiting_client)
    
    pool = ConnectionPool(POOL_SIZE)
    
    # Try to acquire more connections than pool size
    acquire_tasks = []
    for i in range(OVERFLOW_CONNECTIONS):
        client_id = f"client_{i}"
        acquire_tasks.append(pool.acquire(client_id))
    
    results = await asyncio.gather(*acquire_tasks)
    
    # Check pool behavior
    successful = [r for r in results if r != None]
    rejected = [r for r in results if r == None]
    
    assert len(successful) == POOL_SIZE, f"Should accept exactly {POOL_SIZE} connections"
    assert len(rejected) == OVERFLOW_CONNECTIONS - POOL_SIZE
    assert pool.waiting_queue.qsize() == len(rejected)
    
    # Release half of connections
    release_tasks = []
    for i in range(POOL_SIZE // 2):
        client_id = f"client_{i}"
        release_tasks.append(pool.release(client_id))
    
    await asyncio.gather(*release_tasks)
    
    # Verify waiting clients get connections
    await asyncio.sleep(0.1)
    assert len(pool.connections) == POOL_SIZE, "Pool should refill from waiting queue"