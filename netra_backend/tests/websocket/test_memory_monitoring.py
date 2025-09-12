"""
WebSocket memory monitoring and performance testing module.
Tests memory leaks, long-running connections, and resource management.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import gc
import random
import time
import uuid
from typing import Any, Dict, List

import psutil
import pytest

async def _create_test_connections(num_connections: int) -> List:
    """Create test connections for memory monitoring (<=8 lines)"""
    connections = []
    for i in range(num_connections):
        conn = MemoryMonitoredWebSocket(f"conn_{i}")
        connections.append(conn)
        conn.record_memory_checkpoint()
    return connections

async def _simulate_message_traffic(connections: List, test_duration: int, messages_per_sec: int):
    """Simulate message traffic for memory monitoring (<=8 lines)"""
    start_time = time.time()
    while time.time() - start_time < test_duration:
        tasks = []
        for conn in connections:
            message = _create_test_message(0)
            tasks.append(conn.process_message(message))
        await asyncio.gather(*tasks)
        await asyncio.sleep(1.0 / messages_per_sec)

def _validate_memory_trends(connections: List):
    """Validate memory growth trends (<=8 lines)"""
    for conn in connections:
        checkpoints = conn.memory_checkpoints
        if len(checkpoints) >= 2:
            first, last = checkpoints[0], checkpoints[-1]
            time_delta = last['timestamp'] - first['timestamp']
            if time_delta > 0:
                growth_rate = (last['rss_mb'] - first['rss_mb']) / time_delta
                assert growth_rate < 1.0, f"Memory growing too fast: {growth_rate:.2f} MB/s"

class MemoryMonitoredWebSocket:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.created_at = time.time()
        self.message_buffer: List[Dict] = []
        self.max_buffer_size = 1000
        self.total_messages_processed = 0
        self.memory_checkpoints: List[Dict] = []
        
    async def process_message(self, message: Dict):
        """Process message with buffer management (<=8 lines)"""
        self.total_messages_processed += 1
        self.message_buffer.append(message)
        if len(self.message_buffer) > self.max_buffer_size:
            self.message_buffer = self.message_buffer[-self.max_buffer_size:]
        await asyncio.sleep(0.001)
        
    def get_memory_usage(self) -> Dict:
        """Get current memory usage metrics (<=8 lines)"""
        process = psutil.Process()
        return {
            'rss_mb': process.memory_info().rss / 1024 / 1024,
            'vms_mb': process.memory_info().vms / 1024 / 1024,
            'connections': 1,
            'buffer_size': len(self.message_buffer),
            'total_processed': self.total_messages_processed,
            'uptime_seconds': time.time() - self.created_at
        }
    
    def record_memory_checkpoint(self):
        """Record memory usage checkpoint (<=8 lines)"""
        checkpoint = self.get_memory_usage()
        checkpoint['timestamp'] = time.time()
        self.memory_checkpoints.append(checkpoint)
@pytest.mark.slow
@pytest.mark.asyncio
async def test_memory_leak_detection_long_connections():
    """Test for memory leaks in long-running WebSocket connections (<=8 lines)"""
    NUM_CONNECTIONS, MESSAGES_PER_SECOND, TEST_DURATION_SECONDS = 10, 10, 3
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    connections = await _create_test_connections(NUM_CONNECTIONS)
    await _simulate_message_traffic(connections, TEST_DURATION_SECONDS, MESSAGES_PER_SECOND)
    await _finalize_memory_test(connections, initial_memory, NUM_CONNECTIONS, MESSAGES_PER_SECOND, TEST_DURATION_SECONDS)

async def _finalize_memory_test(connections: List, initial_memory: float, num_conn: int, msgs_per_sec: int, duration: int):
    """Finalize memory test with validation (<=8 lines)"""
    for conn in connections:
        conn.record_memory_checkpoint()
    gc.collect()
    await asyncio.sleep(0.5)
    _validate_memory_trends(connections)
    await _validate_cleanup_and_processing(connections, initial_memory, num_conn, msgs_per_sec, duration)

async def _validate_cleanup_and_processing(connections: List, initial_memory: float, num_conn: int, msgs_per_sec: int, duration: int):
    """Validate cleanup and message processing (<=8 lines)"""
    final_memory = psutil.Process().memory_info().rss / 1024 / 1024
    total_processed = sum(conn.total_messages_processed for conn in connections)
    expected_messages = num_conn * msgs_per_sec * duration
    assert total_processed >= expected_messages * 0.7, f"Should process  >= 70% messages: {total_processed} >= {expected_messages * 0.7}"
    connections.clear()
    gc.collect()
    await _validate_memory_cleanup(initial_memory, final_memory)

async def _validate_memory_cleanup(initial_memory: float, final_memory: float):
    """Validate memory cleanup after test (<=8 lines)"""
    await asyncio.sleep(0.5)
    cleanup_memory = psutil.Process().memory_info().rss / 1024 / 1024
    memory_growth = final_memory - initial_memory
    memory_released = final_memory - cleanup_memory
    if memory_growth > 1.0:
        release_ratio = memory_released / memory_growth
        assert release_ratio > 0.1, f"Should release >10% memory: {release_ratio:.1%}"

def _create_test_message(msg_id: int) -> Dict[str, Any]:
    """Helper function to create test message (<=8 lines)"""
    return {
        'id': str(uuid.uuid4()),
        'sequence': msg_id,
        'timestamp': time.time(),
        'data': 'x' * random.randint(100, 500),
        'type': 'test_message'
    }

def _calculate_memory_metrics(initial_mb: float, final_mb: float, duration: float) -> Dict[str, float]:
    """Helper function to calculate memory metrics (<=8 lines)"""
    growth = final_mb - initial_mb
    growth_rate = growth / duration if duration > 0 else 0.0
    return {
        'growth_mb': growth,
        'growth_rate_mb_per_sec': growth_rate,
        'growth_percentage': (growth / initial_mb * 100) if initial_mb > 0 else 0.0
    }

def _validate_memory_checkpoint(checkpoint: Dict[str, Any], max_buffer_size: int) -> bool:
    """Helper function to validate memory checkpoint (<=8 lines)"""
    required_fields = ['rss_mb', 'buffer_size', 'total_processed', 'timestamp']
    if not all(field in checkpoint for field in required_fields):
        return False
    
    if checkpoint['buffer_size'] > max_buffer_size:
        return False
    
    return checkpoint['rss_mb'] > 0 and checkpoint['total_processed'] >= 0

async def _process_message_batch(connections: List, batch_size: int, message_factory) -> int:
    """Helper function to process message batch (<=8 lines)"""
    tasks = []
    for i in range(batch_size):
        for conn in connections:
            message = message_factory(i)
            tasks.append(conn.process_message(message))
    
    await asyncio.gather(*tasks)
    return len(tasks)